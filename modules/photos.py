"""Page Photos & souvenirs — multi-photos, lieu, session/date, partage réseaux."""
from __future__ import annotations

import base64
import json
from datetime import datetime, date
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from core.database import (
    load_sessions, load_captures, load_multimedia,
    insert_row, update_row, delete_row, load_spots,
)
from core.storage import save_multimedia_photo
from core.utils import safe_str, format_date_fr
from ui.components import hero, section, location_picker


CATEGORIES = [
    "Souvenir de session", "Poisson trophée", "Spot / paysage",
    "Montage / appât", "Matériel", "Ambiance / nature", "Autre",
]


# ---------------------------------------------------------------------------
# Partage réseaux sociaux pour une photo
# ---------------------------------------------------------------------------

def _share_photo_widget(titre: str, lieu: str, date_str: str, photo_path: str, key: str) -> None:
    """Boutons de partage réseaux sociaux pour une photo."""
    from urllib.parse import quote as _q

    caption_txt = titre or "Photo de pêche"
    if lieu:
        caption_txt += f" · {lieu}"
    if date_str:
        caption_txt += f" · {date_str}"
    caption_txt += " — #surfcasting #peche"

    fb_url  = f"https://www.facebook.com/sharer/sharer.php?u=https://surfcasting.app&quote={_q(caption_txt)}"
    wa_url  = f"https://wa.me/?text={_q(caption_txt)}"
    tw_url  = f"https://twitter.com/intent/tweet?text={_q(caption_txt)}"
    insta   = "https://www.instagram.com/"  # Instagram n'a pas d'API de partage URL directe

    components.html(f"""
    <style>
      .photo-share {{ display:flex; flex-wrap:wrap; gap:7px; margin:6px 0; }}
      .ps-btn {{
        display:inline-flex; align-items:center; gap:6px;
        padding:7px 13px; border-radius:8px; font-size:12px; font-weight:700;
        text-decoration:none; cursor:pointer; border:none;
        transition:opacity .15s;
      }}
      .ps-btn:hover {{ opacity:.85; }}
      .ps-copy {{ background:#1565C0; color:#fff; cursor:pointer; }}
      .ps-wa   {{ background:#25D366; color:#fff; }}
      .ps-fb   {{ background:#1877F2; color:#fff; }}
      .ps-tw   {{ background:#1DA1F2; color:#fff; }}
      .ps-ig   {{ background:linear-gradient(45deg,#f09433,#e6683c,#dc2743,#cc2366,#bc1888); color:#fff; }}
      .ps-ok   {{ color:#4CAF50; font-size:11px; display:none; margin-left:4px; }}
    </style>
    <div class="photo-share">
      <button class="ps-btn ps-copy" onclick="copyCaption_{key}()">
        📋 Copier légende <span class="ps-ok" id="ok_{key}">✓</span>
      </button>
      <a class="ps-btn ps-wa"  href="{wa_url}" target="_blank">💬 WhatsApp</a>
      <a class="ps-btn ps-fb"  href="{fb_url}" target="_blank">👥 Facebook</a>
      <a class="ps-btn ps-tw"  href="{tw_url}" target="_blank">🐦 Twitter/X</a>
      <a class="ps-btn ps-ig"  href="{insta}"  target="_blank">📸 Instagram</a>
    </div>
    <script>
    function copyCaption_{key}() {{
        var txt = {json.dumps(caption_txt)};
        if (navigator.clipboard) {{
            navigator.clipboard.writeText(txt).then(function() {{
                var el = document.getElementById('ok_{key}');
                if (el) {{ el.style.display='inline'; setTimeout(()=>el.style.display='none',2000); }}
            }});
        }}
    }}
    </script>
    """, height=60, scrolling=False)


# ---------------------------------------------------------------------------
# Ajout de photos (plusieurs à la fois)
# ---------------------------------------------------------------------------

def _render_add() -> None:
    section("Ajouter des photos", icon="➕")

    sessions_df = load_sessions()

    # ── Métadonnées ─────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("**Informations**")
        c1, c2 = st.columns(2)
        with c1:
            categorie = st.selectbox("Catégorie", CATEGORIES, key="mp_cat")
            titre = st.text_input("Titre du lot", placeholder="Soirée pêche, gros bar…", key="mp_titre")
        with c2:
            date_photo = st.date_input("Date", value=date.today(), format="DD/MM/YYYY", key="mp_date")
            favori = st.checkbox("⭐ Marquer comme favori", key="mp_fav")
        commentaire = st.text_area("Commentaire", placeholder="Contexte, anecdote…", key="mp_com")

    # ── Lieu ─────────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("**Lieu**")
        # Raccourci spot
        lieu_txt = ""
        spots_df = load_spots()
        if not spots_df.empty:
            names = ["— Choisir un spot enregistré —"] + spots_df["nom"].tolist()
            chosen = st.selectbox("⭐ Spot enregistré", names, key="mp_spot_qs")
            if chosen != "— Choisir un spot enregistré —":
                lieu_txt = chosen
        # Saisie libre en complément
        lieu_manuel = st.text_input("Ou saisir un lieu manuellement",
                                     value=lieu_txt,
                                     placeholder="Plage de la Salie, Cap Ferret…",
                                     key="mp_lieu")
        lieu = lieu_manuel or lieu_txt

    # ── Session liée ─────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("**Session associée (optionnel)**")
        session_id = None
        if not sessions_df.empty:
            opts = {"— Aucune session liée —": None}
            for _, s in sessions_df.iterrows():
                d = format_date_fr(s.get("date_session", "")) or "—"
                l = safe_str(s.get("lieu")) or "Sans lieu"
                opts[f"{d} — {l}"] = int(s["id"])
            sel = st.selectbox("Session", list(opts.keys()), key="mp_session")
            session_id = opts[sel]
        else:
            st.caption("Aucune session enregistrée.")

    # ── Upload multi-photos ──────────────────────────────────────────
    with st.container(border=True):
        st.markdown("**Photos** — sélectionne une ou plusieurs images")
        uploaded_files = st.file_uploader(
            "📁 Importer des photos",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            key="mp_files",
        )
        camera_photo = st.camera_input("📸 Ou prendre une photo", key="mp_camera")

    # ── Enregistrement ───────────────────────────────────────────────
    all_files = list(uploaded_files or [])
    if camera_photo:
        all_files.insert(0, camera_photo)

    if st.button("💾 Enregistrer toutes les photos", key="mp_save",
                 use_container_width=True, type="primary"):
        if not all_files:
            st.error("Sélectionne au moins une photo avant d'enregistrer.")
        else:
            saved = 0
            first_path = None
            extra_paths = []

            for i, f in enumerate(all_files):
                pp = save_multimedia_photo(f, "souvenir")
                if pp:
                    if i == 0:
                        first_path = pp
                    else:
                        extra_paths.append(pp)
                    saved += 1

            if first_path:
                insert_row("multimedia", {
                    "categorie": categorie,
                    "titre": titre,
                    "photo_path": first_path,
                    "photos_json": json.dumps(extra_paths) if extra_paths else None,
                    "commentaire": commentaire,
                    "favori": int(favori),
                    "lieu": lieu or None,
                    "date_photo": date_photo.isoformat(),
                    "session_id": session_id,
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                })
                st.cache_data.clear()
                st.success(f"✅ {saved} photo(s) enregistrée(s) !")
                st.rerun()
            else:
                st.error("Erreur lors de la sauvegarde.")


# ---------------------------------------------------------------------------
# Galerie
# ---------------------------------------------------------------------------

def _render_gallery() -> None:
    captures = load_captures()
    multimedia = load_multimedia()

    # Photos de captures
    cap_rows = []
    if not captures.empty and "photo_path" in captures.columns:
        for _, c in captures.dropna(subset=["photo_path"]).iterrows():
            cap_rows.append({
                "id": None,
                "photo_path": c["photo_path"],
                "photos_json": None,
                "titre": safe_str(c.get("espece")) or "Capture",
                "categorie": "Poisson trophée",
                "commentaire": "",
                "favori": 0,
                "lieu": safe_str(c.get("lieu")),
                "date_photo": safe_str(c.get("date_session")),
                "source": "capture",
            })

    # Photos multimédia
    multi_rows = []
    if not multimedia.empty:
        for _, m in multimedia.iterrows():
            pp = safe_str(m.get("photo_path"))
            if not pp:
                continue
            # Catégorie enrichie selon le tag espece (utilisé comme tag de référence)
            cat_orig = safe_str(m.get("categorie")) or "—"
            tag      = safe_str(m.get("espece"))
            if tag.startswith("spot_"):
                cat = "📍 Spot"
            elif tag.startswith("baitspot_"):
                cat = "🪱 Spot appât"
            elif tag.startswith("fish_"):
                cat = "🐟 Identification"
            elif tag.startswith("session_"):
                cat = "📓 Session"
            else:
                cat = cat_orig
            multi_rows.append({
                "id": m.get("id"),
                "photo_path": pp,
                "photos_json": safe_str(m.get("photos_json")),
                "titre": safe_str(m.get("titre")) or "Photo",
                "categorie": cat,
                "commentaire": safe_str(m.get("commentaire")),
                "favori": int(m.get("favori") or 0),
                "lieu": safe_str(m.get("lieu")),
                "date_photo": safe_str(m.get("date_photo")),
                "source": "multimedia",
            })

    all_photos = cap_rows + multi_rows

    if not all_photos:
        st.info("Aucune photo disponible. Ajoute tes premières photos dans l'onglet ➕ Ajouter.")
        return

    # ── Filtres ──────────────────────────────────────────────────────
    with st.container(border=True):
        cf1, cf2, cf3 = st.columns(3)
        with cf1:
            show_fav = st.checkbox("⭐ Favoris seulement", key="gal_fav")
        with cf2:
            cats = ["Toutes"] + sorted({p["categorie"] for p in all_photos if p["categorie"] and p["categorie"] != "—"})
            cat_filter = st.selectbox("Catégorie", cats, key="gal_cat")
        with cf3:
            search = st.text_input("Rechercher", placeholder="Lieu, titre…", key="gal_search")

    if show_fav:
        all_photos = [p for p in all_photos if p["favori"]]
    if cat_filter != "Toutes":
        all_photos = [p for p in all_photos if p["categorie"] == cat_filter]
    if search:
        s = search.lower()
        all_photos = [p for p in all_photos
                      if s in (p["titre"] or "").lower()
                      or s in (p["lieu"] or "").lower()
                      or s in (p["commentaire"] or "").lower()]

    if not all_photos:
        st.info("Aucune photo correspond aux filtres.")
        return

    st.caption(f"{len(all_photos)} photo(s)")

    # ── Grille 3 colonnes ─────────────────────────────────────────────
    cols = st.columns(3)
    for idx, photo in enumerate(all_photos):
        pp = photo["photo_path"]
        if not pp or not Path(pp).exists():
            continue

        # Toutes les photos de ce lot (principale + extras)
        lot_paths = [pp]
        if photo["photos_json"]:
            try:
                extras = json.loads(photo["photos_json"])
                lot_paths += [p for p in extras if Path(p).exists()]
            except Exception:
                pass

        with cols[idx % 3]:
            with st.container(border=True):
                # ── Image(s) ────────────────────────────────────────
                if len(lot_paths) == 1:
                    st.image(pp, use_container_width=True)
                else:
                    # Mini carrousel dans la carte
                    _mini_carousel(lot_paths, f"gal_{idx}")

                # ── Infos ────────────────────────────────────────────
                titre = photo["titre"]
                st.markdown(f"**{titre}**")

                meta = []
                if photo["categorie"] and photo["categorie"] != "—":
                    meta.append(photo["categorie"])
                if photo["lieu"]:
                    meta.append(f"📍 {photo['lieu']}")
                if photo["date_photo"]:
                    meta.append(f"📅 {photo['date_photo']}")
                if meta:
                    st.caption(" · ".join(meta))
                if photo["commentaire"]:
                    st.caption(photo["commentaire"])

                if len(lot_paths) > 1:
                    st.caption(f"📂 {len(lot_paths)} photos dans ce lot")

                # ── Actions ──────────────────────────────────────────
                c1, c2 = st.columns(2)
                is_fav = bool(photo["favori"])

                # Favori (seulement pour multimédia)
                if photo["source"] == "multimedia" and photo["id"]:
                    fav_lbl = "💛 Favori" if is_fav else "☆ Favori"
                    if c1.button(fav_lbl, key=f"fav_{idx}", use_container_width=True):
                        update_row("multimedia", int(photo["id"]), {"favori": 0 if is_fav else 1})
                        st.cache_data.clear()
                        st.rerun()

                # Supprimer
                if photo["source"] == "multimedia" and photo["id"]:
                    if c2.button("🗑️ Supprimer", key=f"del_{idx}", use_container_width=True):
                        delete_row("multimedia", int(photo["id"]))
                        # Supprimer aussi les fichiers
                        for p in lot_paths:
                            try:
                                Path(p).unlink(missing_ok=True)
                            except Exception:
                                pass
                        st.cache_data.clear()
                        st.rerun()

                # ── Partage réseaux ──────────────────────────────────
                with st.expander("📤 Partager", expanded=False):
                    _share_photo_widget(
                        titre=titre,
                        lieu=photo["lieu"] or "",
                        date_str=photo["date_photo"] or "",
                        photo_path=pp,
                        key=f"sh_{idx}",
                    )


def _mini_carousel(paths: list[str], cid: str) -> None:
    """Mini carrousel pour un lot de plusieurs photos dans la grille."""
    slides = ""
    for i, p in enumerate(paths):
        try:
            b64 = base64.b64encode(Path(p).read_bytes()).decode()
            ext = Path(p).suffix.lower().lstrip(".")
            mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
            src = f"data:{mime};base64,{b64}"
        except Exception:
            continue
        active = "display:block" if i == 0 else "display:none"
        slides += f'<img id="sl_{cid}_{i}" src="{src}" style="width:100%;border-radius:8px;{active}"/>'

    nb = len(paths)
    components.html(f"""
    <div style="position:relative;">
      {slides}
      <div style="position:absolute;bottom:6px;right:8px;
                  background:rgba(0,0,0,.55);color:#fff;
                  font-size:11px;padding:2px 8px;border-radius:12px;" id="ctr_{cid}">
        1/{nb}
      </div>
      <button onclick="prev_{cid}()" style="position:absolute;left:4px;top:50%;transform:translateY(-50%);
              background:rgba(0,0,0,.45);color:#fff;border:none;border-radius:5px;
              padding:4px 10px;cursor:pointer;font-size:18px;">&#8249;</button>
      <button onclick="next_{cid}()" style="position:absolute;right:4px;top:50%;transform:translateY(-50%);
              background:rgba(0,0,0,.45);color:#fff;border:none;border-radius:5px;
              padding:4px 10px;cursor:pointer;font-size:18px;">&#8250;</button>
    </div>
    <script>
    (function(){{
      var idx=0, nb={nb};
      function show(n){{
        idx=(n+nb)%nb;
        for(var i=0;i<nb;i++){{
          var el=document.getElementById('sl_{cid}_'+i);
          if(el) el.style.display=(i===idx)?'block':'none';
        }}
        var ctr=document.getElementById('ctr_{cid}');
        if(ctr) ctr.textContent=(idx+1)+'/'+nb;
      }}
      window['prev_{cid}']=function(){{show(idx-1);}};
      window['next_{cid}']=function(){{show(idx+1);}};
    }})();
    </script>
    """, height=220, scrolling=False)


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def _render_gallery_by_session() -> None:
    """Galerie organisée par session : photos de la session + photos des captures."""
    sessions = load_sessions()
    captures = load_captures()
    multimedia = load_multimedia()

    if sessions.empty:
        st.info("Aucune session enregistrée.")
        return

    # Filtre rapide
    fav_only = st.checkbox("⭐ Sessions avec au moins 1 photo favori",
                              key="sess_gal_fav")

    nb_displayed = 0
    for _, sess in sessions.iterrows():
        sid    = int(sess["id"])
        lieu   = safe_str(sess.get("lieu")) or "Sans lieu"
        d      = format_date_fr(sess.get("date_session")) or "—"
        type_s = safe_str(sess.get("type_session")) or "Loisir"

        # Photos de capture
        sess_caps = captures[captures["session_id"] == sid] \
                    if not captures.empty and "session_id" in captures.columns \
                    else pd.DataFrame()
        cap_photos = []
        if not sess_caps.empty and "photo_path" in sess_caps.columns:
            for _, c in sess_caps.iterrows():
                pp = safe_str(c.get("photo_path"))
                if pp and Path(pp).exists():
                    cap_photos.append({
                        "path":  pp,
                        "titre": safe_str(c.get("espece")) or "Capture",
                        "tag":   "🐟",
                    })

        # Photos de session (multimedia tagué session_X)
        sess_photos = []
        if not multimedia.empty:
            tag = f"session_{sid}"
            mm  = multimedia[multimedia["espece"].astype(str) == tag] \
                  if "espece" in multimedia.columns else pd.DataFrame()
            for _, p in mm.iterrows():
                pp = safe_str(p.get("photo_path"))
                if pp and Path(pp).exists():
                    sess_photos.append({
                        "path":  pp,
                        "titre": safe_str(p.get("titre")) or "Photo",
                        "tag":   "📓",
                    })

        total_photos = len(cap_photos) + len(sess_photos)
        if total_photos == 0:
            continue

        # Filtre favoris : skipper si aucune photo favori
        if fav_only and multimedia.empty:
            continue  # Pas d'info favori sur les photos de captures

        nb_displayed += 1

        # ── Code couleur : loisir vert · entraînement orange · compétition rouge ──
        if "ompétition" in type_s:
            type_color = "#C62828"  # rouge
            type_icon  = "🏆"
        elif "ntra" in type_s:
            type_color = "#EF6C00"  # orange
            type_icon  = "🎯"
        else:
            type_color = "#2E7D32"  # vert (loisir)
            type_icon  = "🎣"

        # Helper pour convertir une image locale en base64 (vignette taille fixe)
        def _img_thumb(path: str, border_color: str, badge: str) -> str:
            try:
                ext  = Path(path).suffix.lower().lstrip(".")
                mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
                b64  = base64.b64encode(Path(path).read_bytes()).decode()
                return (
                    f'<div style="position:relative;width:100%;aspect-ratio:1;'
                    f'border-radius:8px;overflow:hidden;border:2px solid {border_color};">'
                    f'<img src="data:{mime};base64,{b64}" '
                    f'style="width:100%;height:100%;object-fit:cover;display:block;"/>'
                    f'<div style="position:absolute;bottom:2px;left:2px;'
                    f'background:{border_color};color:#fff;font-size:9px;font-weight:700;'
                    f'padding:1px 5px;border-radius:4px;line-height:1.3;">{badge}</div>'
                    f'</div>'
                )
            except Exception:
                return ""

        with st.container(border=True):
            # En-tête compact avec gradient du type
            st.markdown(
                f'<div style="background:linear-gradient(135deg,{type_color}dd,{type_color}99);'
                f'color:#fff;padding:8px 14px;border-radius:8px;margin-bottom:10px;'
                f'display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">'
                f'<div>'
                f'<span style="font-size:15px;font-weight:800;">{type_icon} {lieu}</span>'
                f'<span style="background:rgba(255,255,255,.25);font-size:10px;font-weight:700;'
                f'padding:2px 7px;border-radius:8px;margin-left:8px;">{type_s}</span>'
                f'</div>'
                f'<div style="font-size:11px;opacity:.95;">📅 {d} · '
                f'🐟 {len(cap_photos)} · 📓 {len(sess_photos)}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Grille compacte 6 colonnes — toutes les photos d'un coup (captures + ambiance)
            all_thumbs = []
            for ph in cap_photos:
                html = _img_thumb(ph["path"], type_color, f"🐟 {ph['titre'][:12]}")
                if html:
                    all_thumbs.append(html)
            for ph in sess_photos:
                html = _img_thumb(ph["path"], "#546E7A", f"📓 {ph['titre'][:12]}")
                if html:
                    all_thumbs.append(html)

            if all_thumbs:
                # Mosaïque CSS Grid : 6 colonnes desktop, responsive
                grid_html = (
                    '<div style="display:grid;'
                    'grid-template-columns:repeat(auto-fill,minmax(95px,1fr));'
                    'gap:6px;margin:4px 0 8px;">'
                    + "".join(all_thumbs) +
                    '</div>'
                )
                components.html(grid_html,
                                  height=int(110 * ((len(all_thumbs) // 6) + 1)),
                                  scrolling=False)

            # Bouton Voir la session (compact)
            if st.button(f"📋 Voir la session", key=f"gal_sess_{sid}",
                          use_container_width=True):
                st.session_state["ss_detail_id"] = sid
                st.session_state["nav_page"]     = "sessions"
                st.rerun()

    if nb_displayed == 0:
        st.info("Aucune session ne contient de photos pour le moment. Ajoute des photos depuis Mes sessions ou Mes captures.")


def render() -> None:
    # Bandeau bleu marine
    st.markdown(
        '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        'color:#fff;padding:14px 20px;border-radius:8px;margin:8px 0 18px;">'
        '<span style="font-size:18px;font-weight:800;">📸 Photos & souvenirs</span>'
        '<div style="font-size:12px;opacity:.85;margin-top:3px;">'
        'Galerie complète de tes photos de pêche — par session ou en vue d\'ensemble.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    tab_add, tab_gallery, tab_session = st.tabs([
        "➕ Ajouter", "🖼️ Galerie globale", "📓 Par session",
    ])
    with tab_add:
        _render_add()
    with tab_gallery:
        _render_gallery()
    with tab_session:
        _render_gallery_by_session()
