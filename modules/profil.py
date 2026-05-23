"""Page Mon profil — version 2 complète et fonctionnelle."""
from __future__ import annotations
from datetime import datetime
import io
import streamlit as st
import streamlit.components.v1 as _comp

from core.database import load_profil, save_profil, load_sessions, load_captures
from core.utils import safe_str
from ui.components import section

NIVEAUX = ["Débutant", "Intermédiaire", "Confirmé", "Expert", "Compétiteur"]
ZONES   = ["Atlantique Sud-Ouest", "Atlantique Centre-Ouest", "Bretagne",
           "Manche / Normandie", "Manche Est", "Méditerranée", "Plusieurs zones"]
ESPECES = ["Bar / Loup", "Daurade royale", "Maigre", "Sole", "Raie",
           "Lieu jaune", "Tacaud", "Maquereau", "Congre", "Autre"]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _photo_html(url: str, size: int = 100) -> str:
    """Rendu HTML d'une photo de profil ronde."""
    if url and url.startswith("http"):
        return (
            f'<img src="{url}" style="width:{size}px;height:{size}px;'
            f'border-radius:50%;object-fit:cover;border:3px solid #1565C0;">'
        )
    return (
        f'<div style="width:{size}px;height:{size}px;border-radius:50%;'
        f'background:#E3F2FD;border:3px dashed #1565C0;display:flex;'
        f'align-items:center;justify-content:center;font-size:{size//2}px;">🎣</div>'
    )


def _upload_photo(key_prefix: str) -> str | None:
    """
    Widget d'upload photo simplifié.
    Stocke les bytes dans session_state[key_prefix + '_bytes'].
    Retourne l'URL Supabase si l'upload réussit, None sinon.
    """
    upl = st.file_uploader(
        "Choisir une photo (JPG, PNG, WEBP)",
        type=["jpg", "jpeg", "png", "webp"],
        key=f"{key_prefix}_uploader",
    )
    if upl is not None:
        st.session_state[f"{key_prefix}_bytes"] = upl.getvalue()
        st.session_state[f"{key_prefix}_name"]  = upl.name

    b = st.session_state.get(f"{key_prefix}_bytes")
    if not b:
        return None

    # Aperçu + crop
    import base64 as _b64
    name = st.session_state.get(f"{key_prefix}_name", "photo.jpg")
    ext  = name.rsplit(".", 1)[-1].lower()
    mime = "image/jpeg" if ext in ("jpg","jpeg") else f"image/{ext}"
    b64  = _b64.b64encode(b).decode()

    cv = st.slider("↕️ Vertical",   0, 100, st.session_state.get(f"{key_prefix}_cv", 50), key=f"{key_prefix}_cv_slider")
    ch = st.slider("↔️ Horizontal", 0, 100, st.session_state.get(f"{key_prefix}_ch", 50), key=f"{key_prefix}_ch_slider")
    st.session_state[f"{key_prefix}_cv"] = cv
    st.session_state[f"{key_prefix}_ch"] = ch

    mt = -(cv * 0.4)
    ml = -(ch * 0.4)
    _comp.html(
        f'<div style="width:110px;height:110px;border-radius:50%;overflow:hidden;'
        f'border:3px solid #1565C0;margin:8px auto;">'
        f'<img src="data:{mime};base64,{b64}" '
        f'style="width:140%;height:140%;object-fit:cover;'
        f'margin-left:{ml}%;margin-top:{mt}%;"></div>',
        height=130, scrolling=False,
    )

    if st.button("❌ Annuler", key=f"{key_prefix}_cancel"):
        st.session_state.pop(f"{key_prefix}_bytes", None)
        st.session_state.pop(f"{key_prefix}_name", None)
        st.rerun()

    return None  # L'URL sera uploadée au submit


def _do_upload(key_prefix: str, dest_name: str) -> str | None:
    """Upload les bytes stockés vers Supabase Storage. Retourne l'URL ou None."""
    b = st.session_state.get(f"{key_prefix}_bytes")
    if not b:
        return None
    try:
        from core.supabase_client import SUPABASE_URL, get_headers
        import requests as _r
        name = st.session_state.get(f"{key_prefix}_name", "photo.jpg")
        ext  = name.rsplit(".", 1)[-1].lower()
        mime = "image/jpeg" if ext in ("jpg","jpeg") else f"image/{ext}"
        ts   = int(datetime.now().timestamp())
        path = f"profil/{dest_name}_{ts}.{ext}"
        hdrs = {
            "apikey": get_headers()["apikey"],
            "Authorization": get_headers()["Authorization"],
            "Content-Type": mime,
        }
        r = _r.post(f"{SUPABASE_URL}/storage/v1/object/photos/{path}",
                    headers=hdrs, data=b, timeout=30)
        if r.status_code in (200, 201):
            url = f"{SUPABASE_URL}/storage/v1/object/public/photos/{path}"
            st.session_state.pop(f"{key_prefix}_bytes", None)
            st.session_state.pop(f"{key_prefix}_name", None)
            return url
        else:
            st.error(f"❌ Échec upload photo : {r.status_code} — {r.text[:200]}")
            return None
    except Exception as e:
        st.error(f"❌ Erreur upload : {e}")
        return None


# ── Page principale ───────────────────────────────────────────────────────────

def render() -> None:
    if not st.session_state.get("reseau_user"):
        section("Mon profil", icon="👤")
        st.warning("⚠️ Connecte-toi pour accéder à ton profil.")
        if st.button("🔑 Se connecter", type="primary"):
            st.session_state["sidebar_login_open"] = True
            st.rerun()
        return

    profil = load_profil() or {}

    # Stats rapides
    sessions_df = load_sessions()
    captures_df = load_captures()
    nb_sessions = len(sessions_df) if not sessions_df.empty else 0
    nb_captures = len(captures_df) if not captures_df.empty else 0

    user    = st.session_state["reseau_user"]
    pseudo  = safe_str(profil.get("pseudo")) or user.get("pseudo","Pêcheur")
    photo   = safe_str(profil.get("photo_path")) or ""

    # ── Onglets directement sans répéter le bandeau ───────────────────
    tab_info, tab_photo, tab_social, tab_secu = st.tabs([
        "👤 Mes infos", "📸 Ma photo", "🌐 Réseaux", "🔒 Sécurité"
    ])

    with tab_info:
        _render_info_form(profil, photo)

    with tab_photo:
        _render_photo_tab(profil, photo)

    with tab_social:
        _render_social_form(profil, photo)

    with tab_secu:
        _render_security_form()


# ── Onglet Sécurité ───────────────────────────────────────────────────────────

def _render_security_form() -> None:
    """Changement de mot de passe."""
    import hashlib
    from core.supabase_client import supabase_get, supabase_patch

    user = st.session_state.get("reseau_user")
    if not user:
        st.warning("Connecte-toi pour modifier ton mot de passe.")
        return

    st.markdown(
        '<div style="background:#f5f7fa;border-left:3px solid #1565C0;'
        'padding:10px 14px;border-radius:6px;margin-bottom:14px;">'
        '<div style="font-size:13px;color:#0c2340;font-weight:700;">🔒 Changer mon mot de passe</div>'
        '<div style="font-size:11px;color:#546E7A;margin-top:3px;">'
        'Pour ta sécurité, on te demande ton mot de passe actuel.</div></div>',
        unsafe_allow_html=True,
    )

    with st.form("change_pwd_form"):
        old_pwd = st.text_input("Mot de passe actuel", type="password",
                                 key="pwd_old")
        new_pwd = st.text_input("Nouveau mot de passe", type="password",
                                 key="pwd_new",
                                 help="6 caractères minimum")
        new_pwd2 = st.text_input("Confirmer le nouveau mot de passe",
                                  type="password", key="pwd_new2")

        submit = st.form_submit_button("🔐 Changer mon mot de passe",
                                         use_container_width=True, type="primary")

    if submit:
        if not all([old_pwd, new_pwd, new_pwd2]):
            st.error("Remplis tous les champs.")
            return
        if new_pwd != new_pwd2:
            st.error("Les nouveaux mots de passe ne correspondent pas.")
            return
        if len(new_pwd) < 6:
            st.error("Le mot de passe doit faire au moins 6 caractères.")
            return
        if new_pwd == old_pwd:
            st.warning("Le nouveau mot de passe est identique à l'ancien.")
            return

        # Vérifier l'ancien mot de passe
        h_old = hashlib.sha256(old_pwd.encode()).hexdigest()
        check = supabase_get("profils", {
            "id":           f"eq.{user['id']}",
            "mot_de_passe": f"eq.{h_old}",
            "select":       "id",
        })
        if not check:
            st.error("❌ Mot de passe actuel incorrect.")
            return

        # Mettre à jour
        h_new = hashlib.sha256(new_pwd.encode()).hexdigest()
        ok = supabase_patch("profils", user["id"], {"mot_de_passe": h_new})
        if ok:
            st.success("✅ Mot de passe modifié avec succès !")
            from ui.components import fish_animation
            fish_animation()
        else:
            st.error("Erreur lors de la mise à jour. Réessaie.")


# ── Onglet Infos ──────────────────────────────────────────────────────────────

def _render_info_form(profil: dict, photo: str) -> None:
    with st.form("profil_info_form"):
        c1, c2, c3 = st.columns(3)
        prenom = c1.text_input("Prénom",  value=safe_str(profil.get("prenom")))
        nom    = c2.text_input("Nom",     value=safe_str(profil.get("nom")))
        pseudo = c3.text_input("Pseudo ✱", value=safe_str(profil.get("pseudo")))

        c1, c2, c3 = st.columns(3)
        niveau = c1.selectbox("Niveau", [""] + NIVEAUX,
                               index=(NIVEAUX.index(safe_str(profil.get("niveau"))) + 1
                                      if safe_str(profil.get("niveau")) in NIVEAUX else 0))
        annees = c2.number_input("Années de pêche", 0, 60,
                                  int(float(profil.get("annees_peche") or 0)))
        zone   = c3.selectbox("Zone principale", [""] + ZONES,
                               index=(ZONES.index(safe_str(profil.get("zone_peche_principale"))) + 1
                                      if safe_str(profil.get("zone_peche_principale")) in ZONES else 0))

        c1, c2, c3 = st.columns(3)
        esp  = c1.selectbox("Espèce préférée", [""] + ESPECES,
                             index=(ESPECES.index(safe_str(profil.get("espece_preferee"))) + 1
                                    if safe_str(profil.get("espece_preferee")) in ESPECES else 0))
        canne  = c2.text_input("Canne préférée",  value=safe_str(profil.get("canne_preferee")))
        appat  = c3.text_input("Appât préféré",   value=safe_str(profil.get("appat_prefere")))

        bio  = st.text_area("Bio / présentation", value=safe_str(profil.get("bio")), height=80)
        obs  = st.text_area("Observations",       value=safe_str(profil.get("observations")), height=60)

        if st.form_submit_button("💾 Sauvegarder", use_container_width=True, type="primary"):
            data = {
                "prenom": prenom, "nom": nom, "pseudo": pseudo,
                "niveau": niveau or None, "annees_peche": annees or None,
                "zone_peche_principale": zone or None,
                "espece_preferee": esp or None,
                "canne_preferee": canne or None,
                "appat_prefere": appat or None,
                "bio": bio or None, "observations": obs or None,
                "photo_path": photo or None,
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }
            if save_profil(data):
                st.success("✅ Profil sauvegardé !")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("❌ Erreur lors de la sauvegarde.")


# ── Onglet Photo ──────────────────────────────────────────────────────────────

def _render_photo_tab(profil: dict, photo: str) -> None:
    section("Photo de profil", icon="📸")

    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown("**Photo actuelle :**")
        _comp.html(
            f'<div style="margin:8px 0;">{_photo_html(photo, 110)}</div>',
            height=130, scrolling=False,
        )

    with c2:
        st.markdown("**Nouvelle photo :**")
        _upload_photo("pf_photo")

    if st.session_state.get("pf_photo_bytes"):
        if st.button("💾 Enregistrer cette photo", type="primary",
                      use_container_width=True, key="pf_save_photo"):
            url = _do_upload("pf_photo", "profil")
            if url:
                data = dict(profil)
                data["photo_path"] = url
                data["updated_at"] = datetime.now().isoformat(timespec="seconds")
                # Mettre à jour aussi le session_state reseau_user
                if save_profil(data):
                    st.session_state["reseau_user"]["avatar_url"] = url
                    st.cache_data.clear()
                    st.success("✅ Photo de profil mise à jour !")
                    st.rerun()


# ── Onglet Réseaux sociaux ────────────────────────────────────────────────────

def _render_social_form(profil: dict, photo: str) -> None:
    section("Réseaux sociaux", icon="🌐")
    with st.form("profil_social_form"):
        ig  = st.text_input("Instagram", value=safe_str(profil.get("social_instagram")),
                             placeholder="https://instagram.com/monpseudo")
        fb  = st.text_input("Facebook",  value=safe_str(profil.get("social_facebook")),
                             placeholder="https://facebook.com/monprofil")
        yt  = st.text_input("YouTube",   value=safe_str(profil.get("social_youtube")),
                             placeholder="https://youtube.com/@machaîne")
        tt  = st.text_input("TikTok",    value=safe_str(profil.get("social_tiktok")),
                             placeholder="https://tiktok.com/@monpseudo")

        if st.form_submit_button("💾 Sauvegarder", use_container_width=True, type="primary"):
            data = dict(profil)
            data.update({
                "social_instagram": ig or None,
                "social_facebook":  fb or None,
                "social_youtube":   yt or None,
                "social_tiktok":    tt or None,
                "photo_path": photo or None,
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            })
            if save_profil(data):
                st.success("✅ Réseaux sociaux sauvegardés !")
                st.cache_data.clear()
            else:
                st.error("❌ Erreur lors de la sauvegarde.")
