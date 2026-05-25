"""Fil d'actualité — posts, likes, commentaires."""
from __future__ import annotations
import streamlit as st
from datetime import datetime
from core.supabase_client import supabase_get, supabase_post, supabase_delete, supabase_patch

def _fmt_date(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z",""))
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return iso or "—"

def _type_badge(t: str) -> str:
    return {"capture": "🐟", "session": "📓", "spot": "📍", "texte": "💬"}.get(t, "📢")

def render_fil() -> None:
    user = st.session_state.get("reseau_user")

    # ── Nouveau post ───────────────────────────────────────────
    st.markdown(
        '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        'color:#fff;padding:10px 14px;border-radius:8px;margin-bottom:12px;">'
        '<span style="font-size:14px;font-weight:800;">📢 Partager une prise ou un moment</span>'
        '</div>', unsafe_allow_html=True,
    )

    with st.container(border=True):
        type_post = st.selectbox("Type de post", ["capture", "session", "spot", "texte"],
                                  format_func=lambda t: {"capture":"🐟 Capture","session":"📓 Session",
                                                          "spot":"📍 Spot","texte":"💬 Message"}[t],
                                  key="fil_type")
        contenu = st.text_area("Ton message", placeholder="Qu'as-tu pêché ? Raconte...", key="fil_contenu")

        c1, c2, c3 = st.columns(3)
        espece  = c1.text_input("Espèce",     key="fil_espece")   if type_post == "capture" else ""
        taille  = c2.number_input("Taille cm", 0.0, key="fil_taille", step=1.0) if type_post == "capture" else 0
        lieu    = c3.text_input("Lieu",        key="fil_lieu")

        photo   = st.file_uploader("📸 Photo", type=["jpg","jpeg","png"], key="fil_photo")
        photo_url = ""
        if photo:
            # Upload vers Supabase Storage
            from core.storage import save_multimedia_photo
            photo_url = save_multimedia_photo(photo, "post") or ""

        if st.button("📤 Publier", key="fil_publish", use_container_width=True, type="primary"):
            if not contenu.strip() and not photo_url:
                st.warning("Écris quelque chose ou ajoute une photo.")
            else:
                data = {
                    "user_id":  user["id"],
                    "type":     type_post,
                    "contenu":  contenu.strip(),
                    "lieu":     lieu.strip() or None,
                    "photo_url": photo_url or None,
                    "espece":   espece.strip() or None,
                    "taille_cm": float(taille) if taille > 0 else None,
                }
                result = supabase_post("posts", data)
                if result:
                    st.success("Post publié ! 🎣")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Erreur lors de la publication.")

    st.markdown("---")

    # ── Fil ───────────────────────────────────────────────────
    st.markdown(
        '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        'color:#fff;padding:10px 14px;border-radius:8px;margin-bottom:12px;">'
        '<span style="font-size:14px;font-weight:800;">📰 Fil d\'actualité</span>'
        '</div>', unsafe_allow_html=True,
    )

    posts = supabase_get("posts", {
        "select": "id,user_id,type,contenu,photo_url,espece,taille_cm,lieu,nb_likes,created_at",
        "order":  "created_at.desc",
        "limit":  "30",
    })

    if not posts:
        st.info("Aucun post pour l'instant. Sois le premier à publier ! 🎣")
        return

    for post in posts:
        pid    = post["id"]
        uid    = post.get("user_id","")
        badge  = _type_badge(post.get("type",""))
        lieu_p = post.get("lieu") or ""
        esp    = post.get("espece") or ""
        tail   = post.get("taille_cm")
        contenu_p = post.get("contenu") or ""
        photo_p   = post.get("photo_url") or ""

        # Récupérer pseudo
        auteur_rows = supabase_get("profils", {"id": f"eq.{uid}", "select": "pseudo"})
        pseudo = auteur_rows[0]["pseudo"] if auteur_rows else "Pêcheur anonyme"

        # Likes
        user_liked = False
        if user:
            lk = supabase_get("likes", {"post_id": f"eq.{pid}", "user_id": f"eq.{user['id']}", "select": "id"})
            user_liked = bool(lk)
        nb_likes = post.get("nb_likes", 0)

        # Commentaires
        coms = supabase_get("commentaires", {
            "post_id": f"eq.{pid}",
            "select":  "id,user_id,contenu,created_at",
            "order":   "created_at.asc",
        })

        with st.container(border=True):
            # En-tête
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'margin-bottom:6px;">'
                f'<div><span style="font-weight:800;color:#0c2340;">{badge} {pseudo}</span>'
                f'{"  ·  <em>" + lieu_p + "</em>" if lieu_p else ""}</div>'
                f'<div style="font-size:11px;color:#546E7A;">{_fmt_date(post.get("created_at",""))}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Badges & infos depuis metadata
            meta_p = post.get("metadata") or {}
            if isinstance(meta_p, str):
                try:
                    import json as _json
                    meta_p = _json.loads(meta_p)
                except Exception:
                    meta_p = {}

            # Pour rétro-compatibilité : esp/tail anciens posts
            if not meta_p:
                if esp:  meta_p["espece"]    = esp
                if tail: meta_p["taille_cm"] = tail

            # Mapping label/icone par clé
            FIELD_DISPLAY = {
                "espece":    ("🐟", "Espèce",       "#E3F2FD", "#1565C0"),
                "taille_cm": ("📏", "Taille",       "#FFF3E0", "#E65100"),
                "poids_g":   ("⚖️", "Poids",        "#FFF3E0", "#E65100"),
                "lieu":      ("📍", "Lieu",         "#E8F5E9", "#2E7D32"),
                "heure":     ("🕐", "Heure",        "#F3E5F5", "#6A1B9A"),
                "appat":     ("🪱", "Appât",        "#FFF8E1", "#F57F17"),
                "montage":   ("🧵", "Montage",      "#E0F7FA", "#006064"),
                "canne":     ("🎯", "Canne",        "#ECEFF1", "#37474F"),
                "moulinet":  ("⚙️", "Moulinet",     "#ECEFF1", "#37474F"),
                "hamecon":   ("🪝", "Hameçon",      "#ECEFF1", "#37474F"),
                "distance":  ("📐", "Distance",     "#F3E5F5", "#6A1B9A"),
                "date":      ("📅", "Date",         "#E8F5E9", "#2E7D32"),
                "type":      ("🎯", "Type",         "#ECEFF1", "#37474F"),
                "nb_caps":   ("🐟", "Captures",     "#E3F2FD", "#1565C0"),
                "best":      ("📏", "Meilleure",    "#FFF3E0", "#E65100"),
                "meteo":     ("🌦️", "Météo",        "#E0F7FA", "#006064"),
                "maree":     ("🌊", "Marée",        "#E3F2FD", "#1565C0"),
                "marque":    ("🏷️", "Marque",       "#ECEFF1", "#37474F"),
                "modele":    ("📋", "Modèle",       "#ECEFF1", "#37474F"),
                "longueur":  ("📏", "Longueur",     "#FFF3E0", "#E65100"),
                "puissance": ("⚡", "Puissance",    "#FFF3E0", "#E65100"),
                "etat":      ("✨", "État",         "#E8F5E9", "#2E7D32"),
                "nom":       ("📍", "Nom",          "#E8F5E9", "#2E7D32"),
                "type_spot": ("🏖️", "Type",         "#E0F7FA", "#006064"),
            }

            badges_parts = []
            for fk, val in meta_p.items():
                # Filtrer seulement les valeurs vraiment vides — garder les 0 valides
                if val is None or val == "":
                    continue
                # 0 est valide pour nb_caps (zéro prise) ou taille (poisson minuscule)
                # mais False/booléen non
                if isinstance(val, bool) and not val:
                    continue
                icn, lbl, bg, fg = FIELD_DISPLAY.get(fk, ("•", fk, "#ECEFF1", "#37474F"))
                # Formatage de la valeur
                if fk == "taille_cm":  vstr = f"{int(float(val))} cm"
                elif fk == "poids_g":
                    v = float(val)
                    vstr = f"{v/1000:.2f} kg" if v >= 1000 else f"{int(v)} g"
                elif fk == "distance": vstr = f"{int(float(val))} m"
                elif fk == "best":     vstr = f"{int(float(val))} cm"
                else:                  vstr = str(val)
                badges_parts.append(
                    f'<span style="background:{bg};color:{fg};font-size:11px;'
                    f'font-weight:700;padding:3px 9px;border-radius:8px;'
                    f'display:inline-block;margin:2px 3px;">'
                    f'{icn} {vstr}</span>'
                )

            if badges_parts:
                st.markdown(
                    '<div style="margin:6px 0 8px;">' + "".join(badges_parts) + '</div>',
                    unsafe_allow_html=True,
                )

            # Photo
            # Photo du post
            if photo_p and (photo_p.startswith("http") or photo_p.startswith("data:")):
                st.markdown(
                    f'<img src="{photo_p}" style="width:100%;max-height:400px;'
                    f'object-fit:contain;border-radius:8px;margin:6px 0;">',
                    unsafe_allow_html=True,
                )

            # Contenu
            if contenu_p:
                st.markdown(contenu_p)

            # Actions
            col_like, col_com, col_del = st.columns([1, 2, 1])
            heart = "❤️" if user_liked else "🤍"
            if col_like.button(f"{heart} {nb_likes}", key=f"like_{pid}", use_container_width=True):
                if user:
                    if user_liked:
                        lk_rows = supabase_get("likes", {"post_id": f"eq.{pid}", "user_id": f"eq.{user['id']}", "select": "id"})
                        if lk_rows:
                            supabase_delete("likes", lk_rows[0]["id"])
                            supabase_patch("posts", pid, {"nb_likes": max(0, nb_likes - 1)})
                    else:
                        supabase_post("likes", {"post_id": pid, "user_id": user["id"]})
                        supabase_patch("posts", pid, {"nb_likes": nb_likes + 1})
                    st.rerun()

            # Commentaires
            com_key = f"show_coms_{pid}"
            if col_com.button(f"💬 {len(coms)} commentaire(s)", key=f"com_btn_{pid}", use_container_width=True):
                st.session_state[com_key] = not st.session_state.get(com_key, False)

            if user and uid == user["id"]:
                if col_del.button("🗑️ Supprimer", key=f"del_post_{pid}", use_container_width=True):
                    supabase_delete("posts", pid)
                    st.rerun()

            if st.session_state.get(com_key):
                for c in coms:
                    c_auteur = supabase_get("profils", {"id": f"eq.{c['user_id']}", "select": "pseudo"})
                    c_pseudo = c_auteur[0]["pseudo"] if c_auteur else "?"
                    st.markdown(
                        f'<div style="background:#F5F7FA;padding:6px 12px;border-radius:6px;'
                        f'margin:3px 0;font-size:12px;">'
                        f'<strong>{c_pseudo}</strong>  {c["contenu"]}'
                        f'<span style="color:#546E7A;font-size:10px;margin-left:8px;">'
                        f'{_fmt_date(c.get("created_at",""))}</span></div>',
                        unsafe_allow_html=True,
                    )
                if user:
                    new_com = st.text_input("Ton commentaire", key=f"new_com_{pid}",
                                             placeholder="Ajoute un commentaire...")
                    if st.button("Envoyer", key=f"send_com_{pid}"):
                        if new_com.strip():
                            supabase_post("commentaires", {
                                "post_id": pid, "user_id": user["id"], "contenu": new_com.strip()
                            })
                            st.rerun()
