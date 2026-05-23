"""
Mes spots — deux onglets : Nouveau spot | Mes spots
Photos persistantes via session_state (survivent aux reruns Streamlit).
"""
from __future__ import annotations
import io
from datetime import datetime
from pathlib import Path

import streamlit as st
import pandas as pd

from core.database import load_spots, load_multimedia, load_captures, load_sessions, insert_row, update_row, delete_row
from core.external_apis import reverse_geocode
from core.storage import save_spot_photo
from core.utils import safe_str, safe_float
from ui.components import (
    hero, section, confirm_destructive,
    location_picker, share_location_widget, terrestrial_map,
)

TYPES_FOND  = ["Sable", "Sable + roche", "Roche", "Vase", "Mixte", "Inconnu"]
ACCES       = ["Plage", "Jetée / digue", "Falaise", "Rochers", "Port", "Estuaire", "Autre"]
PROFONDEURS = ["0–2 m", "0–4 m", "2–5 m", "3–8 m", "5–10 m",
                "8–15 m", "10–20 m", "15–30 m", "20–50 m",
                "> 50 m", "Variable", "Inconnu"]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers photo (session_state pour survivre aux reruns)
# ─────────────────────────────────────────────────────────────────────────────

def _photo_pick(key_cam: str, key_upl: str, ss_key: str) -> bytes | None:
    """Affiche camera + file_uploader, stocke les bytes dans session_state."""
    col_cam, col_up = st.columns(2)
    with col_cam:
        cam = st.camera_input("📷 Prendre une photo", key=key_cam)
    with col_up:
        upl = st.file_uploader("🖼️ Importer", type=["jpg","jpeg","png","webp"],
                                key=key_upl)
    raw = upl if upl is not None else cam
    if raw is not None:
        st.session_state[ss_key]           = raw.getvalue()
        st.session_state[ss_key + "_name"] = getattr(raw, "name", "photo.jpg")
    return st.session_state.get(ss_key)


def _photo_preview(ss_key: str, clear_key: str) -> None:
    """Affiche l'aperçu + bouton supprimer."""
    b = st.session_state.get(ss_key)
    if b:
        st.image(b, caption="✅ Photo prête", width=260)
        if st.button("🗑️ Retirer cette photo", key=clear_key):
            st.session_state.pop(ss_key, None)
            st.session_state.pop(ss_key + "_name", None)
            st.rerun()


def _save_photo_from_ss(ss_key: str, spot_id: int, titre: str) -> None:
    """Sauvegarde la photo stockée en session_state."""
    b = st.session_state.get(ss_key)
    if not b:
        return
    fname     = st.session_state.get(ss_key + "_name", "photo.jpg")
    fake_file = io.BytesIO(b)
    fake_file.name = fname
    pp = save_spot_photo(fake_file, spot_id)
    if pp:
        # Photo principale du spot si pas encore définie
        df_s = load_spots()
        if not df_s.empty:
            sr = df_s[df_s["id"] == spot_id]
            if not sr.empty and not safe_str(sr.iloc[0].get("photo_path")):
                update_row("spots", spot_id, {"photo_path": pp})
        insert_row("multimedia", {
            "categorie":  "Spot",
            "titre":      titre,
            "photo_path": pp,
            "espece":     f"spot_{spot_id}",
            "favori":     0,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        })
    st.session_state.pop(ss_key, None)
    st.session_state.pop(ss_key + "_name", None)


# ─────────────────────────────────────────────────────────────────────────────
# Point d'entrée
# ─────────────────────────────────────────────────────────────────────────────

def render() -> None:
    hero("Mes spots", "Gère tes spots favoris",
         "Crée, consulte et gère tes spots de pêche avec photos.")

    tab_new, tab_list = st.tabs(["📍 Nouveau spot", "📚 Mes spots"])

    with tab_new:
        _render_add()
    with tab_list:
        _render_list()


# ─────────────────────────────────────────────────────────────────────────────
# ONGLET 1 — Nouveau spot
# ─────────────────────────────────────────────────────────────────────────────

def _render_add() -> None:
    st.markdown(
        '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        'color:#fff;padding:14px 20px;border-radius:8px;margin:8px 0 18px;">'
        '<span style="font-size:18px;font-weight:800;">📍 Nouveau spot</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # 1. Localisation
    st.markdown(
        '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        'color:#fff;padding:8px 14px;border-radius:8px;margin:8px 0 6px;">'
        '<span style="font-size:13px;font-weight:700;">1️⃣ Localisation</span>'
        '</div>', unsafe_allow_html=True,
    )
    with st.container(border=True):
        latitude, longitude = location_picker("spot_loc", spots_shortcut=False)
    if latitude is None or longitude is None:
        latitude, longitude = 44.656588, -1.196303

    # 2. Informations
    st.markdown(
        '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        'color:#fff;padding:8px 14px;border-radius:8px;margin:8px 0 6px;">'
        '<span style="font-size:13px;font-weight:700;">2️⃣ Informations</span>'
        '</div>', unsafe_allow_html=True,
    )
    nom = st.text_input("Nom du spot *", placeholder="Ex : Plage de la Salie sud",
                         key="spot_nom")
    c1, c2 = st.columns(2)
    with c1:
        type_fond  = st.selectbox("Type de fond", TYPES_FOND, key="spot_fond")
        profondeur = st.selectbox("Profondeur",   PROFONDEURS, key="spot_prof")
    with c2:
        acces   = st.selectbox("Accès", ACCES, key="spot_acces")
        especes = st.text_input("Espèces cibles",
                                 placeholder="Bar, daurade, sole...", key="spot_especes")
    commentaire = st.text_area("Notes / conseils",
                                placeholder="Courant fort à marée descendante...",
                                key="spot_com")
    favori = st.checkbox("⭐ Spot favori", key="spot_fav")

    st.markdown(
        '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        'color:#fff;padding:8px 14px;border-radius:8px;margin:12px 0 6px;">'
        '<span style="font-size:13px;font-weight:700;">3️⃣ 📸 Photos du spot</span>'
        '<span style="font-size:11px;opacity:.8;margin-left:8px;">optionnel</span>'
        '</div>', unsafe_allow_html=True,
    )

    col_cam, col_up = st.columns(2)
    with col_cam:
        cam = st.camera_input("📷 Prendre une photo maintenant",
                                key="spot_add_cam_direct")
    with col_up:
        upl = st.file_uploader("🖼️ Importer une photo existante",
                                type=["jpg", "jpeg", "png", "webp"],
                                key="spot_add_upl_direct")

    # Stocker en session_state pour persister
    raw_photo = upl if upl is not None else cam
    if raw_photo is not None:
        st.session_state["spot_add_photo"]      = raw_photo.getvalue()
        st.session_state["spot_add_photo_name"] = getattr(raw_photo, "name", "photo.jpg")

    # Aperçu
    if st.session_state.get("spot_add_photo"):
        st.image(st.session_state["spot_add_photo"],
                  caption="✅ Photo prête à être enregistrée", width=280)
        if st.button("🗑️ Retirer cette photo", key="spot_clear_photo_btn"):
            st.session_state.pop("spot_add_photo", None)
            st.session_state.pop("spot_add_photo_name", None)
            st.rerun()

    st.divider()

    # 4. Enregistrement
    if st.button("💾 Enregistrer le spot", use_container_width=True,
                  type="primary", key="spot_save"):
        if not nom.strip():
            st.error("Le nom du spot est obligatoire.")
            return
        spot_id = insert_row("spots", {
            "nom":            nom.strip(),
            "latitude":       latitude,
            "longitude":      longitude,
            "type_fond":      type_fond,
            "profondeur":     profondeur,
            "acces":          acces,
            "especes_cibles": especes,
            "commentaire":    commentaire,
            "favori":         int(favori),
            "created_at":     datetime.now().isoformat(timespec="seconds"),
        })
        _save_photo_from_ss("spot_add_photo", spot_id, nom.strip())
        st.cache_data.clear()
        st.session_state.pop("_spot_add_active", None)
        st.success(f"✅ Spot « {nom} » enregistré.")
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# ONGLET 2 — Mes spots
# ─────────────────────────────────────────────────────────────────────────────

def _render_list() -> None:
    st.markdown(
        '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        'color:#fff;padding:14px 20px;border-radius:8px;margin:8px 0 18px;">'
        '<span style="font-size:18px;font-weight:800;">📚 Mes spots enregistrés</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    df = load_spots()
    if df.empty:
        st.info("Aucun spot enregistré. Utilise l'onglet « Nouveau spot ».")
        return

    # Charger captures + sessions pour l'analyse par spot
    all_captures = load_captures()
    all_sessions = load_sessions()

    # Filtres
    c1, c2 = st.columns(2)
    search   = c1.text_input("🔍 Rechercher",
                               placeholder="Nom, espèce, fond...", key="spot_search")
    fav_only = c2.checkbox("⭐ Favoris uniquement", key="spot_fav_only")

    if search:
        s = search.lower()
        df = df[df.astype(str).apply(
            lambda c: c.str.lower().str.contains(s, na=False)).any(axis=1)]
    if fav_only:
        df = df[df["favori"].fillna(0).astype(int) == 1]

    if df.empty:
        st.info("Aucun résultat.")
        return

    st.caption(f"{len(df)} spot(s) — clique sur un spot pour déplier")
    st.markdown("")  # espace

    for i, (_, row) in enumerate(df.iterrows()):
        spot_id    = int(row["id"])
        nom        = safe_str(row.get("nom")) or "—"
        lat        = safe_float(row.get("latitude"))
        lon        = safe_float(row.get("longitude"))
        is_fav     = bool(row.get("favori"))
        photo_path = safe_str(row.get("photo_path")) if "photo_path" in row.index else ""
        fond       = safe_str(row.get("type_fond")) or "—"
        prof       = safe_str(row.get("profondeur")) or "—"
        esp        = safe_str(row.get("especes_cibles")) or "—"
        comment    = safe_str(row.get("commentaire"))

        # État déplié / replié
        open_key = f"spot_open_{spot_id}"
        is_open  = st.session_state.get(open_key, False)
        arrow    = "🔽" if is_open else "▶️"

        with st.container(border=True):
            # En-tête : un seul bouton pleine largeur (toggle) stylé en bleu marine
            star = "⭐ " if is_fav else ""

            # CSS pour donner au bouton l'apparence d'un bandeau bleu marine
            st.markdown(f"""
            <style>
            .stApp [class*="st-key-spot_tog_{spot_id}"] button {{
                background: linear-gradient(135deg,#1565C0,#0c2340) !important;
                color: white !important;
                border: none !important;
                padding: 12px 16px !important;
                font-weight: 700 !important;
                font-size: 16px !important;
                text-align: left !important;
                justify-content: flex-start !important;
            }}
            .stApp [class*="st-key-spot_tog_{spot_id}"] button:hover {{
                background: linear-gradient(135deg,#1976D2,#102d52) !important;
            }}
            .stApp [class*="st-key-spot_tog_{spot_id}"] button p {{
                font-size: 15px !important;
                font-weight: 700 !important;
            }}
            </style>
            """, unsafe_allow_html=True)

            btn_label = f"{arrow}  {star}{nom}    📌 {lat:.5f}, {lon:.5f}"
            if st.button(btn_label, key=f"spot_tog_{spot_id}",
                          use_container_width=True):
                st.session_state[open_key] = not is_open
                st.rerun()

            # Contenu déplié uniquement si ouvert
            if not is_open:
                continue

            st.markdown("")  # espace

            # ── 3 colonnes : photo │ carte │ descriptif ───────────────
            col_photo, col_map, col_desc = st.columns([1.2, 1.2, 2])

            with col_photo:
                if photo_path and str(photo_path).startswith("http"):
                    import streamlit.components.v1 as _cv
                    _cv.html(
                        f'<img src="{photo_path}" style="width:100%;max-height:180px;'
                        f'object-fit:cover;border-radius:8px;">',
                        height=188, scrolling=False,
                    )
                else:
                    st.markdown(
                        '<div style="aspect-ratio:4/3;background:#e8f0f8;'
                        'border-radius:8px;display:flex;align-items:center;'
                        'justify-content:center;font-size:48px;color:#90a4b8;">'
                        '📷</div>',
                        unsafe_allow_html=True,
                    )
                st.caption("Photo principale")

            with col_map:
                # Mini-carte GPS via iframe OpenStreetMap
                bbox = f"{lon-0.01},{lat-0.008},{lon+0.01},{lat+0.008}"
                map_url = (f"https://www.openstreetmap.org/export/embed.html?"
                           f"bbox={bbox}&layer=mapnik&marker={lat},{lon}")
                st.markdown(
                    f'<iframe src="{map_url}" '
                    f'style="width:100%;aspect-ratio:4/3;border:1px solid #dde;'
                    f'border-radius:8px;" loading="lazy"></iframe>',
                    unsafe_allow_html=True,
                )

                # Reverse geocoding
                addr_text = ""
                try:
                    geo = reverse_geocode(lat, lon) or {}
                    addr = geo.get("address") or {}
                    parts = []
                    place_name = (addr.get("amenity") or addr.get("attraction")
                                    or addr.get("natural") or addr.get("beach")
                                    or addr.get("village") or addr.get("hamlet")
                                    or addr.get("suburb") or addr.get("neighbourhood"))
                    if place_name:  parts.append(place_name)
                    if addr.get("road"):  parts.append(addr["road"])
                    city = (addr.get("town") or addr.get("city") or
                            addr.get("municipality") or addr.get("village"))
                    if city and city not in parts: parts.append(city)
                    if addr.get("postcode"): parts.append(addr["postcode"])
                    if addr.get("country"):  parts.append(addr["country"])
                    addr_text = ", ".join(p for p in parts if p) or safe_str(geo.get("display_name"))
                except Exception:
                    addr_text = ""

                if addr_text:
                    st.markdown(
                        f'<div style="background:#E3F2FD;border-left:3px solid #1565C0;'
                        f'padding:5px 10px;border-radius:0 6px 6px 0;font-size:11px;'
                        f'color:#0c2340;margin-top:4px;">'
                        f'📍 <strong>{addr_text}</strong></div>',
                        unsafe_allow_html=True,
                    )
                st.caption(f"🛰️ {lat:.5f}, {lon:.5f}")

                # ── Partager fusionné ──────────────────────────────
                share_open = st.session_state.get(f"sp_share_{spot_id}", False)
                if st.button("✕ Fermer partage" if share_open else "📤 Partager ce spot",
                               key=f"sp_share_btn_{spot_id}",
                               use_container_width=True):
                    st.session_state[f"sp_share_{spot_id}"] = not share_open
                    st.rerun()
                if share_open:
                    from ui.components import share_button_v2
                    txt = (f"🎣 La Péchouille — Spot de pêche\n\n"
                           f"📍 {nom}\n"
                           + (f"🏖️ {fond}\n" if fond != "—" else "")
                           + (f"📏 Profondeur : {prof}\n" if prof != "—" else "")
                           + (f"📍 {lat:.5f}, {lon:.5f}\n" if lat and lon else "")
                           + "\nApp : https://lapechouille.fr")
                    meta = {
                        "nom":         nom,
                        "type_spot":   fond if fond != "—" else "",
                        "commentaire": safe_str(row.get("commentaire")) or "",
                    }
                    share_button_v2(
                        item_type="spot",
                        item_id=spot_id,
                        item_label=nom,
                        text_external=txt,
                        metadata=meta,
                        photo_url=safe_str(row.get("photo_path")) if str(row.get("photo_path","")).startswith("http") else "",
                        key=f"spot_{spot_id}",
                        is_spot=True,
                    )

            with col_desc:
                # Badges fond / profondeur
                badges_html = ""
                if fond != "—":
                    badges_html += (
                        f'<span style="background:#E3F2FD;color:#1565C0;'
                        f'font-size:11px;font-weight:600;padding:3px 10px;'
                        f'border-radius:10px;margin-right:4px;display:inline-block;'
                        f'margin-bottom:4px;">🏖️ {fond}</span>'
                    )
                if prof != "—":
                    badges_html += (
                        f'<span style="background:#E8F5E9;color:#2E7D32;'
                        f'font-size:11px;font-weight:600;padding:3px 10px;'
                        f'border-radius:10px;margin-right:4px;display:inline-block;'
                        f'margin-bottom:4px;">📏 {prof}</span>'
                    )
                ac_val = safe_str(row.get("acces"))
                if ac_val:
                    badges_html += (
                        f'<span style="background:#FFF3E0;color:#E65100;'
                        f'font-size:11px;font-weight:600;padding:3px 10px;'
                        f'border-radius:10px;margin-right:4px;display:inline-block;'
                        f'margin-bottom:4px;">🚶 {ac_val}</span>'
                    )
                if badges_html:
                    st.markdown(badges_html, unsafe_allow_html=True)

                # ── Analyse captures faites sur ce spot ────────────
                # Un spot = un lieu, donc on matche par lieu+lat/lon proche
                # (les sessions stockent le lieu en texte ; on filtre par nom)
                spot_caps = pd.DataFrame()
                if not all_sessions.empty and not all_captures.empty:
                    # Sessions qui ont le même lieu OU coordonnées GPS proches
                    sess_match = all_sessions[
                        (all_sessions["lieu"].fillna("").str.lower() == nom.lower())
                    ]
                    if sess_match.empty:
                        # Match par GPS approchant (± 200 m soit ~0.002°)
                        sess_match = all_sessions[
                            (abs(all_sessions["latitude"].fillna(0) - lat) < 0.002) &
                            (abs(all_sessions["longitude"].fillna(0) - lon) < 0.002)
                        ]
                    if not sess_match.empty:
                        sids = sess_match["id"].astype(int).tolist()
                        spot_caps = all_captures[all_captures["session_id"].isin(sids)]

                if not spot_caps.empty:
                    nb_caps   = len(spot_caps)
                    nb_sess   = spot_caps["session_id"].nunique()
                    # Comptage par espèce
                    if "espece" in spot_caps.columns:
                        esp_counts = (spot_caps["espece"].fillna("—")
                                                          .value_counts().head(6))
                        esp_html = ""
                        for esp_name, cnt in esp_counts.items():
                            esp_html += (
                                f'<span style="background:#fff;color:#1565C0;'
                                f'font-size:11px;font-weight:600;padding:2px 8px;'
                                f'border:1px solid #1565C0;border-radius:10px;'
                                f'margin:2px;display:inline-block;">'
                                f'🐟 {esp_name} ×{int(cnt)}</span>'
                            )
                    else:
                        esp_html = ""

                    # Record taille sur ce spot
                    best_t = ""
                    if "taille_cm" in spot_caps.columns:
                        tt = pd.to_numeric(spot_caps["taille_cm"], errors="coerce").dropna()
                        tt = tt[tt > 0]
                        if not tt.empty:
                            best_t = f" · 📏 record {tt.max():.0f} cm"

                    st.markdown(
                        f'<div style="margin-top:10px;background:#E3F2FD;'
                        f'border-left:3px solid #1565C0;padding:8px 12px;'
                        f'border-radius:0 6px 6px 0;">'
                        f'<div style="font-size:11px;font-weight:700;color:#0c2340;'
                        f'letter-spacing:1px;text-transform:uppercase;margin-bottom:6px;">'
                        f'📊 Mon historique ici</div>'
                        f'<div style="font-size:12px;color:#0c2340;margin-bottom:6px;">'
                        f'🎣 <strong>{nb_caps}</strong> prise(s) sur '
                        f'<strong>{nb_sess}</strong> session(s){best_t}</div>'
                        f'<div>{esp_html}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                # Espèces cibles (config du spot, pas captures)
                if esp != "—":
                    st.markdown(
                        f'<div style="margin-top:8px;font-size:13px;">'
                        f'<strong>🎯 Espèces ciblées :</strong> {esp}</div>',
                        unsafe_allow_html=True,
                    )

                # Commentaire
                if comment:
                    st.markdown(
                        f'<div style="margin-top:6px;background:#fffbea;'
                        f'border-left:3px solid #f0c84a;padding:6px 10px;'
                        f'border-radius:0 6px 6px 0;font-size:12px;color:#5d4f1a;'
                        f'font-style:italic;">💬 {comment}</div>',
                        unsafe_allow_html=True,
                    )

            st.markdown("")  # espace avant boutons

            # ── Boutons d'action ──────────────────────────────────────
            c_use, c_fav, c_edit, c_photos, c_del = st.columns(5)

            if c_use.button("📍 Utiliser", key=f"sp_use_{spot_id}",
                             use_container_width=True, type="primary"):
                st.session_state["active_spot_lat"] = lat
                st.session_state["active_spot_lon"] = lon
                st.session_state["active_spot_nom"] = nom
                # Vider les coords mémorisées de conditions pour forcer le rechargement
                st.session_state.pop("cond_last_lat", None)
                st.session_state.pop("cond_last_lon", None)
                st.session_state.pop("cond_last_spot_nom", None)
                st.session_state.pop("cond_lat_stored", None)
                st.session_state.pop("cond_lon_stored", None)
                st.cache_data.clear()
                st.success(f"Spot « {nom} » actif — conditions actualisées.")

            if c_fav.button("💛 Favori" if is_fav else "☆ Favori",
                             key=f"sp_fav_{spot_id}", use_container_width=True):
                update_row("spots", spot_id, {"favori": 0 if is_fav else 1})
                st.cache_data.clear()
                st.rerun()

            edit_open = st.session_state.get(f"sp_edit_{spot_id}", False)
            if c_edit.button("✕ Fermer" if edit_open else "✏️ Éditer",
                              key=f"sp_edit_btn_{spot_id}", use_container_width=True):
                st.session_state[f"sp_edit_{spot_id}"] = not edit_open
                st.rerun()

            photos_open = st.session_state.get(f"sp_photos_{spot_id}", False)
            if c_photos.button("✕ Photos" if photos_open else "📸 Photos",
                                key=f"sp_photos_btn_{spot_id}",
                                use_container_width=True):
                st.session_state[f"sp_photos_{spot_id}"] = not photos_open
                st.rerun()

            if c_del.button("🗑️ Supprimer", key=f"sp_del_{spot_id}",
                             use_container_width=True):
                st.session_state[f"sp_confirm_{spot_id}"] = True

            if edit_open:
                _render_edit_spot(spot_id, row)

            if photos_open:
                _render_spot_photos(spot_id, nom)

            if st.session_state.get(f"sp_confirm_{spot_id}"):
                if confirm_destructive(f"spot_{spot_id}",
                                       f"Supprimer le spot « {nom} » ?"):
                    delete_row("spots", spot_id)
                    st.session_state.pop(f"sp_confirm_{spot_id}", None)
                    st.cache_data.clear()
                    st.success("Spot supprimé.")
                    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Modification d'un spot
# ─────────────────────────────────────────────────────────────────────────────

def _render_edit_spot(spot_id: int, row) -> None:
    with st.container(border=True):
        col_title, col_close = st.columns([4, 1])
        col_title.markdown("**✏️ Modifier ce spot**")
        if col_close.button("✕ Fermer", key=f"sp_close_edit_{spot_id}",
                             use_container_width=True):
            st.session_state[f"sp_edit_{spot_id}"] = False
            st.rerun()

        lat_cur = safe_float(row.get("latitude"))
        lon_cur = safe_float(row.get("longitude"))

        # ── Position GPS : afficher l'actuelle, modifier seulement si demandé ──
        st.markdown(
            f'<div style="background:#E3F2FD;border-left:4px solid #1565C0;'
            f'padding:8px 12px;border-radius:0 6px 6px 0;margin-bottom:8px;">'
            f'<strong>📍 Position GPS actuelle :</strong> '
            f'<code>{lat_cur:.6f}, {lon_cur:.6f}</code></div>',
            unsafe_allow_html=True,
        )

        change_pos_key = f"es_change_pos_{spot_id}"
        if st.checkbox("📌 Modifier la position GPS", key=change_pos_key):
            st.caption("Saisis les nouvelles coordonnées (copie depuis Google Maps : clic droit → coordonnées).")
            c1, c2 = st.columns(2)
            new_lat = c1.number_input("Latitude",  value=float(lat_cur), format="%.6f",
                                       step=0.0001, key=f"es_lat_{spot_id}")
            new_lon = c2.number_input("Longitude", value=float(lon_cur), format="%.6f",
                                       step=0.0001, key=f"es_lon_{spot_id}")
            st.markdown(f"[🗺️ Vérifier sur Google Maps](https://www.google.com/maps?q={new_lat},{new_lon}&z=14)")
        else:
            new_lat, new_lon = lat_cur, lon_cur

        with st.form(f"edit_spot_{spot_id}"):
            nom = st.text_input("Nom *", value=safe_str(row.get("nom")),
                                  key=f"es_nom_{spot_id}")
            c1, c2 = st.columns(2)
            with c1:
                tf_idx = TYPES_FOND.index(row["type_fond"]) \
                         if row.get("type_fond") in TYPES_FOND else 0
                fond = st.selectbox("Type de fond", TYPES_FOND, index=tf_idx,
                                      key=f"es_fond_{spot_id}")
                pr_idx = PROFONDEURS.index(row["profondeur"]) \
                         if row.get("profondeur") in PROFONDEURS else 0
                prof = st.selectbox("Profondeur", PROFONDEURS, index=pr_idx,
                                      key=f"es_prof_{spot_id}")
            with c2:
                ac_idx = ACCES.index(row["acces"]) \
                         if row.get("acces") in ACCES else 0
                acces  = st.selectbox("Accès", ACCES, index=ac_idx,
                                        key=f"es_acces_{spot_id}")
                esp    = st.text_input("Espèces cibles",
                                        value=safe_str(row.get("especes_cibles")),
                                        key=f"es_esp_{spot_id}")
            comment = st.text_area("Commentaire",
                                    value=safe_str(row.get("commentaire")),
                                    key=f"es_com_{spot_id}")
            favori  = st.checkbox("⭐ Favori", value=bool(row.get("favori")),
                                    key=f"es_fav_{spot_id}")

            if st.form_submit_button("💾 Sauvegarder",
                                      use_container_width=True, type="primary"):
                if not nom.strip():
                    st.error("Le nom est obligatoire.")
                else:
                    update_row("spots", spot_id, {
                        "nom":            nom.strip(),
                        "latitude":       new_lat,
                        "longitude":      new_lon,
                        "type_fond":      fond,
                        "profondeur":     prof,
                        "acces":          acces,
                        "especes_cibles": esp,
                        "commentaire":    comment,
                        "favori":         int(favori),
                        "updated_at":     datetime.now().isoformat(timespec="seconds"),
                    })
                    st.cache_data.clear()
                    st.session_state[f"sp_edit_{spot_id}"] = False
                    st.success("✅ Spot mis à jour.")
                    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Gestion des photos d'un spot existant
# ─────────────────────────────────────────────────────────────────────────────

def _render_spot_photos(spot_id: int, nom: str) -> None:
    with st.container(border=True):
        # Bouton fermer en haut
        col_title, col_close = st.columns([4, 1])
        col_title.markdown(f"**📸 Photos du spot — {nom}**")
        if col_close.button("✕ Fermer", key=f"sp_close_ph_{spot_id}",
                             use_container_width=True):
            st.session_state[f"sp_photos_{spot_id}"] = False
            st.rerun()

        # Photo principale actuelle (pour comparaison)
        df_spot = load_spots()
        current_main = ""
        if not df_spot.empty:
            sr = df_spot[df_spot["id"] == spot_id]
            if not sr.empty:
                current_main = safe_str(sr.iloc[0].get("photo_path"))

        # Photos existantes
        try:
            mm  = load_multimedia()
            tag = f"spot_{spot_id}"
            photos = mm[mm["espece"].astype(str) == tag] \
                     if not mm.empty and "espece" in mm.columns else None
        except Exception:
            photos = None

        if photos is not None and not photos.empty:
            st.caption(f"{len(photos)} photo(s) · ⭐ pour photo principale · 🗑️ pour supprimer")
            cols = st.columns(min(len(photos), 4))
            for j, (_, p) in enumerate(photos.iterrows()):
                pp    = safe_str(p.get("photo_path"))
                pid   = int(p.get("id", 0))
                titre = safe_str(p.get("titre")) or f"Photo {j + 1}"
                is_main = (pp == current_main and pp != "")

                with cols[j % 4]:
                    with st.container(border=True):
                        if pp and str(pp).startswith("http"):
                            import streamlit.components.v1 as _cv
                            _cv.html(
                                f'<img src="{pp}" style="width:100%;height:120px;'
                                f'object-fit:cover;border-radius:6px;">',
                                height=128, scrolling=False,
                            )
                        else:
                            st.caption("📷 Pas encore de photo")
                        # Caption avec marqueur si photo principale
                        if is_main:
                            st.markdown(f"⭐ **{titre}**")
                        else:
                            st.caption(titre)

                        # Boutons ⭐ et 🗑️ côte à côte
                        b_star, b_del = st.columns(2)
                        if is_main:
                            b_star.button("⭐ Principale", key=f"main_act_{pid}_{spot_id}",
                                           use_container_width=True, disabled=True)
                        else:
                            if b_star.button("☆", key=f"set_main_{pid}_{spot_id}",
                                              use_container_width=True,
                                              help="Définir comme photo principale"):
                                update_row("spots", spot_id, {"photo_path": pp})
                                st.cache_data.clear()
                                st.success("Photo principale mise à jour.")
                                st.rerun()
                        if b_del.button("🗑️", key=f"del_sph_{pid}_{spot_id}",
                                         use_container_width=True,
                                         help="Supprimer cette photo"):
                            delete_row("multimedia", pid)
                            # Vider photo principale si c'était celle-là
                            if pp == current_main:
                                update_row("spots", spot_id, {"photo_path": ""})
                            st.cache_data.clear()
                            st.rerun()
        else:
            st.caption("Aucune photo pour ce spot.")

        st.markdown("---")
        st.markdown("**➕ Ajouter une photo**")

        ss_key = f"spot_photo_{spot_id}"
        with st.container(border=True):
            _photo_pick(f"sp_cam_{spot_id}", f"sp_upl_{spot_id}", ss_key)
            _photo_preview(ss_key, f"sp_clear_{spot_id}")

        titre_ph = st.text_input("Titre / légende",
                                  placeholder="Ex : Vue générale, Setup, Coucher...",
                                  key=f"sp_titre_{spot_id}")

        if st.session_state.get(ss_key):
            if st.button("💾 Enregistrer la photo",
                          key=f"sp_save_ph_{spot_id}",
                          type="primary", use_container_width=True):
                _save_photo_from_ss(ss_key, spot_id, titre_ph or nom)
                st.cache_data.clear()
                st.success("✅ Photo ajoutée !")
                st.rerun()
