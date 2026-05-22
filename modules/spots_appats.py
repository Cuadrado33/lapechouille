"""
Spots à appâts — récolte (vers, palourdes) + pêche aux pièges (mendoles, crénilabres).
Structure identique à Mes spots avec champs spécifiques aux appâts.
"""
from __future__ import annotations
import io
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from core.database import (
    load_bait_spots, load_multimedia, insert_row, update_row, delete_row,
)
from core.storage import save_spot_photo
from core.utils import safe_str, safe_float
from ui.components import (
    section, confirm_destructive,
    location_picker, share_location_widget, terrestrial_map,
)

# ── Constantes spécifiques ───────────────────────────────────────────────────
CATEGORIES_APPAT = [
    "🪱 Récolte d'appâts vivants",
    "🐟 Pêche aux pièges (carrelet, balance)",
    "Mixte",
]

TYPES_APPAT_RECOLTE = [
    "Arénicole (ver de plage)", "Néréis (gravette)", "Couteaux",
    "Palourdes", "Vers de chalut", "Vers de roche", "Vers américains",
    "Crabes verts", "Crevettes", "Bibis", "Autre",
]

TYPES_APPAT_PIEGE = [
    "Mendoles", "Crénilabres", "Athérines", "Sprats", "Petits maquereaux",
    "Lançons", "Anguilles", "Autre",
]

MAREES_IDEALES = [
    "Basse mer (BM ± 1h)", "Mi-marée descendante", "Basse mer vive",
    "Pleine mer (PM ± 1h)", "Mi-marée montante", "Toute marée",
    "Coefficients > 90", "Coefficients < 50", "Variable",
]

TYPES_FOND_APPAT = [
    "Sable", "Sable vaseux", "Vase", "Sable + roche", "Roche",
    "Estran rocheux", "Estuaire", "Herbiers", "Mixte", "Inconnu",
]

PROFONDEURS_APPAT = [
    "Estran (à pied)", "0–1 m", "1–3 m", "3–5 m", "5–10 m",
    "10–20 m", "> 20 m", "Variable",
]

ACCES_APPAT = [
    "Plage / estran", "Jetée / digue", "Rocher / falaise", "Port",
    "Estuaire", "Bateau requis", "Sentier difficile", "Autre",
]

AUTORISATIONS_OUTILS = [
    "✅ Tous outils autorisés",
    "🪣 Seau et fourche autorisés",
    "❌ Pompe à vers interdite",
    "❌ Bêchage interdit",
    "⚠️ Quota strict imposé",
    "⚠️ Période de récolte limitée",
    "📋 Vérifier arrêté préfectoral",
    "Inconnu",
]

PERIODES_ANNEE = [
    "Toute l'année", "Janvier-Mars", "Mars-Mai", "Mai-Juillet",
    "Juillet-Septembre", "Septembre-Novembre", "Novembre-Janvier",
    "Printemps", "Été", "Automne", "Hiver",
    "Marées d'équinoxe", "Vives-eaux uniquement",
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers photo (session_state pour survivre aux reruns)
# ─────────────────────────────────────────────────────────────────────────────

def _photo_pick(key_cam: str, key_upl: str, ss_key: str) -> bytes | None:
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
    b = st.session_state.get(ss_key)
    if b:
        st.image(b, caption="✅ Photo prête", width=260)
        if st.button("🗑️ Retirer cette photo", key=clear_key):
            st.session_state.pop(ss_key, None)
            st.session_state.pop(ss_key + "_name", None)
            st.rerun()


def _save_photo_from_ss(ss_key: str, spot_id: int, titre: str) -> None:
    b = st.session_state.get(ss_key)
    if not b:
        return
    fname     = st.session_state.get(ss_key + "_name", "photo.jpg")
    fake_file = io.BytesIO(b)
    fake_file.name = fname
    pp = save_spot_photo(fake_file, spot_id)
    if pp:
        # Photo principale du spot si pas encore définie
        df_s = load_bait_spots()
        if not df_s.empty:
            sr = df_s[df_s["id"] == spot_id]
            if not sr.empty and not safe_str(sr.iloc[0].get("photo_path")):
                update_row("bait_spots", spot_id, {"photo_path": pp})
        insert_row("multimedia", {
            "categorie":  "SpotAppat",
            "titre":      titre,
            "photo_path": pp,
            "espece":     f"baitspot_{spot_id}",
            "favori":     0,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        })
    st.session_state.pop(ss_key, None)
    st.session_state.pop(ss_key + "_name", None)


# ─────────────────────────────────────────────────────────────────────────────
# Point d'entrée
# ─────────────────────────────────────────────────────────────────────────────

def render() -> None:
    # Bandeau bleu marine
    st.markdown(
        '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        'color:#fff;padding:14px 20px;border-radius:8px;margin:8px 0 18px;">'
        '<span style="font-size:18px;font-weight:800;">🪱 Spots appâts</span>'
        '<div style="font-size:12px;opacity:.85;margin-top:3px;">'
        'Tes spots de récolte d\'appâts vivants et de pêche aux pièges.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    tab_new, tab_list = st.tabs(["📍 Nouveau spot appât", "📚 Mes spots appâts"])
    with tab_new:
        _render_add()
    with tab_list:
        _render_list()


# ─────────────────────────────────────────────────────────────────────────────
# ONGLET 1 — Nouveau spot appât
# ─────────────────────────────────────────────────────────────────────────────

def _render_add() -> None:
    section("Nouveau spot appât", icon="📍")

    # Vider les clés GPS résiduelles
    for _k in ("ba_loc_final_lat", "ba_loc_final_lon", "ba_loc_change_pos"):
        st.session_state.pop(_k, None)

    # 1. Localisation
    with st.container(border=True):
        st.markdown("**1️⃣ Localisation**")
        latitude, longitude = location_picker("ba_loc", spots_shortcut=False)
    if latitude is None or longitude is None:
        latitude, longitude = 44.656588, -1.196303

    # 2. Type & catégorie
    st.markdown("**2️⃣ Type d'appât**")
    c1, c2 = st.columns(2)
    with c1:
        categorie = st.selectbox("Catégorie", CATEGORIES_APPAT, key="ba_cat")
    with c2:
        # Choix multiple selon catégorie
        if categorie.startswith("🪱"):
            types_appats = st.multiselect("Appâts récoltés",
                                            TYPES_APPAT_RECOLTE,
                                            key="ba_type_r",
                                            help="Tu peux en sélectionner plusieurs")
        elif categorie.startswith("🐟"):
            types_appats = st.multiselect("Appâts (piège)",
                                            TYPES_APPAT_PIEGE,
                                            key="ba_type_p",
                                            help="Tu peux en sélectionner plusieurs")
        else:
            # Mixte : combiner les deux listes
            types_appats = st.multiselect("Appâts",
                                            TYPES_APPAT_RECOLTE + TYPES_APPAT_PIEGE,
                                            key="ba_type_m",
                                            help="Tu peux en sélectionner plusieurs")
    type_appat = ", ".join(types_appats) if types_appats else ""

    nom = st.text_input("Nom du spot *",
                          placeholder="Ex : Estran de Mimizan, Plage des Mouettes…",
                          key="ba_nom")

    # 3. Conditions
    st.markdown("**3️⃣ Conditions de récolte**")
    c3, c4 = st.columns(2)
    with c3:
        maree    = st.selectbox("Marée idéale", MAREES_IDEALES, key="ba_maree")
        type_fond = st.selectbox("Type de fond", TYPES_FOND_APPAT, key="ba_fond")
        profondeur = st.selectbox("Profondeur", PROFONDEURS_APPAT, key="ba_prof")
    with c4:
        acces    = st.selectbox("Accès", ACCES_APPAT, key="ba_acces")
        autorisation = st.selectbox("Autorisation / réglementation",
                                       AUTORISATIONS_OUTILS, key="ba_auto",
                                       help="Pompe à vers, bêchage, quotas…")
        periode  = st.selectbox("Période idéale", PERIODES_ANNEE, key="ba_periode")

    commentaire = st.text_area("Commentaire libre",
                                placeholder="Notes : technique, rendement, dangers, conseils…",
                                key="ba_com")
    favori = st.checkbox("⭐ Spot favori", key="ba_fav")

    # 4. Photos
    st.markdown("**4️⃣ 📸 Photos du spot** *(optionnel)*")
    with st.container(border=True):
        _photo_pick("ba_cam", "ba_upl", "ba_photo")
        _photo_preview("ba_photo", "ba_clear_photo")

    st.divider()

    # 5. Enregistrement
    if st.button("💾 Enregistrer le spot appât", use_container_width=True,
                  type="primary", key="ba_save"):
        if not nom.strip():
            st.error("Le nom du spot est obligatoire.")
            return
        spot_id = insert_row("bait_spots", {
            "nom":                  nom.strip(),
            "latitude":             latitude,
            "longitude":            longitude,
            "type_appat":           type_appat,
            "categorie":            categorie,
            "maree_ideale":         maree,
            "profondeur":           profondeur,
            "type_fond":            type_fond,
            "acces":                acces,
            "autorisation_outils":  autorisation,
            "periode":              periode,
            "commentaire":          commentaire,
            "favori":               int(favori),
            "created_at":           datetime.now().isoformat(timespec="seconds"),
        })
        _save_photo_from_ss("ba_photo", spot_id, nom.strip())
        st.cache_data.clear()
        st.success(f"✅ Spot appât « {nom} » enregistré.")
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# ONGLET 2 — Mes spots appâts
# ─────────────────────────────────────────────────────────────────────────────

def _render_list() -> None:
    df = load_bait_spots()
    if df.empty:
        st.info("Aucun spot appât enregistré. Utilise l'onglet « Nouveau spot appât ».")
        return

    # Filtres
    c1, c2 = st.columns(2)
    search   = c1.text_input("🔍 Rechercher",
                               placeholder="Nom, appât, fond…", key="ba_search")
    fav_only = c2.checkbox("⭐ Favoris uniquement", key="ba_fav_only")

    if search:
        s = search.lower()
        df = df[df.astype(str).apply(
            lambda c: c.str.lower().str.contains(s, na=False)).any(axis=1)]
    if fav_only:
        df = df[df["favori"].fillna(0).astype(int) == 1]
    if df.empty:
        st.info("Aucun résultat.")
        return

    st.caption(f"{len(df)} spot(s) appât")

    for _, row in df.iterrows():
        spot_id    = int(row["id"])
        nom        = safe_str(row.get("nom")) or "—"
        lat        = safe_float(row.get("latitude"))
        lon        = safe_float(row.get("longitude"))
        is_fav     = bool(row.get("favori"))
        photo_path = safe_str(row.get("photo_path")) if "photo_path" in row.index else ""
        type_appat = safe_str(row.get("type_appat")) or "—"
        categorie  = safe_str(row.get("categorie")) or "—"
        maree      = safe_str(row.get("maree_ideale")) or "—"
        fond       = safe_str(row.get("type_fond")) or "—"
        prof       = safe_str(row.get("profondeur")) or "—"
        acces      = safe_str(row.get("acces")) or "—"
        autor      = safe_str(row.get("autorisation_outils")) or ""
        periode    = safe_str(row.get("periode")) or "—"
        comment    = safe_str(row.get("commentaire"))

        # État déplié / replié
        open_key = f"ba_open_{spot_id}"
        is_open  = st.session_state.get(open_key, False)
        arrow    = "🔽" if is_open else "▶️"

        with st.container(border=True):
            star = "⭐ " if is_fav else ""
            st.markdown(f"""
            <style>
            .stApp [class*="st-key-ba_tog_{spot_id}"] button {{
                background: linear-gradient(135deg,#1565C0,#0c2340) !important;
                color: white !important;
                border: none !important;
                padding: 12px 16px !important;
                font-weight: 700 !important;
                font-size: 16px !important;
                text-align: left !important;
                justify-content: flex-start !important;
            }}
            .stApp [class*="st-key-ba_tog_{spot_id}"] button:hover {{
                background: linear-gradient(135deg,#1976D2,#102d52) !important;
            }}
            </style>
            """, unsafe_allow_html=True)

            btn_label = f"{arrow}  🪱 {star}{nom}    📌 {lat:.5f}, {lon:.5f}"
            if st.button(btn_label, key=f"ba_tog_{spot_id}",
                          use_container_width=True):
                st.session_state[open_key] = not is_open
                st.rerun()

            if not is_open:
                continue

            st.markdown("")

            # 3 colonnes : photo │ carte │ descriptif
            col_photo, col_map, col_desc = st.columns([1.2, 1.2, 2])

            with col_photo:
                if photo_path and str(photo_path).startswith("http"):
                    import streamlit.components.v1 as _cv
                    _cv.html(
                        f'<img src="{photo_path}" style="width:100%;max-height:200px;'
                        f'object-fit:cover;border-radius:8px;">',
                        height=208, scrolling=False,
                    )
                else:
                    st.markdown(
                        '<div style="aspect-ratio:4/3;background:#e8f0f8;'
                        'border-radius:8px;display:flex;align-items:center;'
                        'justify-content:center;font-size:48px;color:#90a4b8;">'
                        '🪱</div>',
                        unsafe_allow_html=True,
                    )

            with col_map:
                bbox = f"{lon-0.01},{lat-0.008},{lon+0.01},{lat+0.008}"
                map_url = (f"https://www.openstreetmap.org/export/embed.html?"
                           f"bbox={bbox}&layer=mapnik&marker={lat},{lon}")
                st.markdown(
                    f'<iframe src="{map_url}" '
                    f'style="width:100%;aspect-ratio:4/3;border:1px solid #dde;'
                    f'border-radius:8px;" loading="lazy"></iframe>',
                    unsafe_allow_html=True,
                )

            with col_desc:
                badges = (
                    f'<span style="background:#E8F5E9;color:#2E7D32;font-size:11px;'
                    f'font-weight:600;padding:3px 10px;border-radius:10px;'
                    f'margin-right:4px;display:inline-block;margin-bottom:4px;">'
                    f'🪱 {type_appat}</span>'
                    f'<span style="background:#E3F2FD;color:#1565C0;font-size:11px;'
                    f'font-weight:600;padding:3px 10px;border-radius:10px;'
                    f'margin-right:4px;display:inline-block;margin-bottom:4px;">'
                    f'🌊 {maree}</span>'
                    f'<span style="background:#FFF3E0;color:#E65100;font-size:11px;'
                    f'font-weight:600;padding:3px 10px;border-radius:10px;'
                    f'margin-right:4px;display:inline-block;margin-bottom:4px;">'
                    f'📅 {periode}</span>'
                )
                st.markdown(badges, unsafe_allow_html=True)

                lines = []
                if fond != "—":    lines.append(f"**🏖️ Fond** : {fond}")
                if prof != "—":    lines.append(f"**📏 Profondeur** : {prof}")
                if acces != "—":   lines.append(f"**🚶 Accès** : {acces}")
                if lines:
                    st.markdown('<div style="margin-top:8px;font-size:13px;">' +
                                '<br>'.join(lines) + '</div>',
                                unsafe_allow_html=True)

                if autor and autor != "Inconnu":
                    bg = "#FFEBEE" if "❌" in autor or "⚠️" in autor else "#E8F5E9"
                    color = "#B71C1C" if "❌" in autor else \
                             ("#E65100" if "⚠️" in autor else "#2E7D32")
                    st.markdown(
                        f'<div style="margin-top:8px;background:{bg};border-left:3px solid {color};'
                        f'padding:6px 10px;border-radius:0 6px 6px 0;font-size:12px;'
                        f'color:{color};font-weight:600;">'
                        f'{autor}</div>',
                        unsafe_allow_html=True,
                    )

                if comment:
                    st.markdown(
                        f'<div style="margin-top:6px;background:#fffbea;'
                        f'border-left:3px solid #f0c84a;padding:6px 10px;'
                        f'border-radius:0 6px 6px 0;font-size:12px;color:#5d4f1a;'
                        f'font-style:italic;">💬 {comment}</div>',
                        unsafe_allow_html=True,
                    )

            st.markdown("")  # espace
            # ── Boutons d'action ──────────────────────────────────────
            c_fav, c_edit, c_photos, c_share, c_del = st.columns(5)

            if c_fav.button("💛 Favori" if is_fav else "☆ Favori",
                             key=f"ba_fav_{spot_id}", use_container_width=True):
                update_row("bait_spots", spot_id, {"favori": 0 if is_fav else 1})
                st.cache_data.clear()
                st.rerun()

            edit_open = st.session_state.get(f"ba_edit_{spot_id}", False)
            if c_edit.button("✕ Fermer" if edit_open else "✏️ Éditer",
                              key=f"ba_edit_btn_{spot_id}", use_container_width=True):
                st.session_state[f"ba_edit_{spot_id}"] = not edit_open
                st.rerun()

            photos_open = st.session_state.get(f"ba_photos_{spot_id}", False)
            if c_photos.button("✕ Photos" if photos_open else "📸 Photos",
                                key=f"ba_photos_btn_{spot_id}", use_container_width=True):
                st.session_state[f"ba_photos_{spot_id}"] = not photos_open
                st.rerun()

            share_open = st.session_state.get(f"ba_share_{spot_id}", False)
            if c_share.button("✕" if share_open else "📤 Partager",
                               key=f"ba_share_btn_{spot_id}", use_container_width=True):
                st.session_state[f"ba_share_{spot_id}"] = not share_open
                st.rerun()

            if c_del.button("🗑️ Supprimer", key=f"ba_del_{spot_id}",
                             use_container_width=True):
                st.session_state[f"ba_confirm_{spot_id}"] = True

            if share_open:
                share_location_widget(lat, lon, nom=nom)
            if edit_open:
                _render_edit(spot_id, row)
            if photos_open:
                _render_spot_photos(spot_id, nom)

            if st.session_state.get(f"ba_confirm_{spot_id}"):
                if confirm_destructive(f"ba_{spot_id}",
                                       f"Supprimer le spot appât « {nom} » ?"):
                    delete_row("bait_spots", spot_id)
                    st.session_state.pop(f"ba_confirm_{spot_id}", None)
                    st.cache_data.clear()
                    st.success("Spot appât supprimé.")
                    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Édition
# ─────────────────────────────────────────────────────────────────────────────

def _render_edit(spot_id: int, row) -> None:
    with st.container(border=True):
        col_title, col_close = st.columns([4, 1])
        col_title.markdown("**✏️ Modifier ce spot appât**")
        if col_close.button("✕ Fermer", key=f"ba_close_edit_{spot_id}",
                             use_container_width=True):
            st.session_state[f"ba_edit_{spot_id}"] = False
            st.rerun()

        lat_cur = safe_float(row.get("latitude"))
        lon_cur = safe_float(row.get("longitude"))

        # Position : affichée, modifiable via case à cocher
        st.markdown(
            f'<div style="background:#E3F2FD;border-left:4px solid #1565C0;'
            f'padding:8px 12px;border-radius:0 6px 6px 0;margin-bottom:8px;">'
            f'<strong>📍 Position GPS actuelle :</strong> '
            f'<code>{lat_cur:.6f}, {lon_cur:.6f}</code></div>',
            unsafe_allow_html=True,
        )
        if st.checkbox("📌 Modifier la position GPS", key=f"ba_change_pos_{spot_id}"):
            st.caption("Saisis les nouvelles coordonnées (copie depuis Google Maps).")
            c1, c2 = st.columns(2)
            new_lat = c1.number_input("Latitude",  value=float(lat_cur), format="%.6f",
                                       step=0.0001, key=f"ba_lat_{spot_id}")
            new_lon = c2.number_input("Longitude", value=float(lon_cur), format="%.6f",
                                       step=0.0001, key=f"ba_lon_{spot_id}")
            st.markdown(f"[🗺️ Vérifier sur Google Maps](https://www.google.com/maps?q={new_lat},{new_lon}&z=14)")
        else:
            new_lat, new_lon = lat_cur, lon_cur

        with st.form(f"ba_edit_form_{spot_id}"):
            nom = st.text_input("Nom *", value=safe_str(row.get("nom")),
                                  key=f"ba_e_nom_{spot_id}")
            c1, c2 = st.columns(2)
            with c1:
                cat_idx = CATEGORIES_APPAT.index(row["categorie"]) \
                          if row.get("categorie") in CATEGORIES_APPAT else 0
                categorie = st.selectbox("Catégorie", CATEGORIES_APPAT, index=cat_idx,
                                            key=f"ba_e_cat_{spot_id}")
                # Type d'appât : multi-select pré-rempli depuis la chaîne
                current_str = safe_str(row.get("type_appat"))
                current_list = [x.strip() for x in current_str.split(",")] if current_str else []
                all_types = TYPES_APPAT_RECOLTE + TYPES_APPAT_PIEGE
                # Garder uniquement ceux qui existent dans les listes
                pre_sel = [t for t in current_list if t in all_types]
                types_appats = st.multiselect("Appâts",
                                                all_types,
                                                default=pre_sel,
                                                key=f"ba_e_type_{spot_id}",
                                                help="Tu peux en sélectionner plusieurs")
                type_appat = ", ".join(types_appats) if types_appats else current_str
                m_idx = MAREES_IDEALES.index(row["maree_ideale"]) \
                        if row.get("maree_ideale") in MAREES_IDEALES else 0
                maree = st.selectbox("Marée idéale", MAREES_IDEALES, index=m_idx,
                                       key=f"ba_e_maree_{spot_id}")
                f_idx = TYPES_FOND_APPAT.index(row["type_fond"]) \
                        if row.get("type_fond") in TYPES_FOND_APPAT else 0
                fond  = st.selectbox("Fond", TYPES_FOND_APPAT, index=f_idx,
                                       key=f"ba_e_fond_{spot_id}")
            with c2:
                p_idx = PROFONDEURS_APPAT.index(row["profondeur"]) \
                        if row.get("profondeur") in PROFONDEURS_APPAT else 0
                prof  = st.selectbox("Profondeur", PROFONDEURS_APPAT, index=p_idx,
                                       key=f"ba_e_prof_{spot_id}")
                a_idx = ACCES_APPAT.index(row["acces"]) \
                        if row.get("acces") in ACCES_APPAT else 0
                acces = st.selectbox("Accès", ACCES_APPAT, index=a_idx,
                                       key=f"ba_e_acces_{spot_id}")
                au_idx = AUTORISATIONS_OUTILS.index(row["autorisation_outils"]) \
                         if row.get("autorisation_outils") in AUTORISATIONS_OUTILS else 0
                autor = st.selectbox("Autorisation / outils", AUTORISATIONS_OUTILS,
                                       index=au_idx, key=f"ba_e_auto_{spot_id}")
                per_idx = PERIODES_ANNEE.index(row["periode"]) \
                          if row.get("periode") in PERIODES_ANNEE else 0
                periode = st.selectbox("Période", PERIODES_ANNEE, index=per_idx,
                                          key=f"ba_e_per_{spot_id}")

            comment = st.text_area("Commentaire",
                                     value=safe_str(row.get("commentaire")),
                                     key=f"ba_e_com_{spot_id}")
            favori = st.checkbox("⭐ Favori", value=bool(row.get("favori")),
                                   key=f"ba_e_fav_{spot_id}")

            if st.form_submit_button("💾 Sauvegarder",
                                      use_container_width=True, type="primary"):
                if not nom.strip():
                    st.error("Le nom est obligatoire.")
                else:
                    update_row("bait_spots", spot_id, {
                        "nom":                 nom.strip(),
                        "latitude":            new_lat,
                        "longitude":           new_lon,
                        "type_appat":          type_appat,
                        "categorie":           categorie,
                        "maree_ideale":        maree,
                        "type_fond":           fond,
                        "profondeur":          prof,
                        "acces":               acces,
                        "autorisation_outils": autor,
                        "periode":             periode,
                        "commentaire":         comment,
                        "favori":              int(favori),
                        "updated_at":          datetime.now().isoformat(timespec="seconds"),
                    })
                    st.cache_data.clear()
                    st.session_state[f"ba_edit_{spot_id}"] = False
                    st.success("✅ Spot appât mis à jour.")
                    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Gestion photos
# ─────────────────────────────────────────────────────────────────────────────

def _render_spot_photos(spot_id: int, nom: str) -> None:
    with st.container(border=True):
        col_title, col_close = st.columns([4, 1])
        col_title.markdown(f"**📸 Photos — {nom}**")
        if col_close.button("✕ Fermer", key=f"ba_close_ph_{spot_id}",
                             use_container_width=True):
            st.session_state[f"ba_photos_{spot_id}"] = False
            st.rerun()

        # Photo principale actuelle
        df_spot = load_bait_spots()
        current_main = ""
        if not df_spot.empty:
            sr = df_spot[df_spot["id"] == spot_id]
            if not sr.empty:
                current_main = safe_str(sr.iloc[0].get("photo_path"))

        try:
            mm  = load_multimedia()
            tag = f"baitspot_{spot_id}"
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
                                f'<img src="{pp}" style="width:100%;height:110px;'
                                f'object-fit:cover;border-radius:6px;">',
                                height=118, scrolling=False,
                            )
                        else:
                            st.caption("📷 Pas de photo")
                        if is_main:
                            st.markdown(f"⭐ **{titre}**")
                        else:
                            st.caption(titre)
                        b_star, b_del = st.columns(2)
                        if is_main:
                            b_star.button("⭐ Principale",
                                           key=f"ba_main_act_{pid}_{spot_id}",
                                           use_container_width=True, disabled=True)
                        else:
                            if b_star.button("☆", key=f"ba_set_main_{pid}_{spot_id}",
                                               use_container_width=True,
                                               help="Définir comme principale"):
                                update_row("bait_spots", spot_id, {"photo_path": pp})
                                st.cache_data.clear()
                                st.success("Photo principale mise à jour.")
                                st.rerun()
                        if b_del.button("🗑️", key=f"ba_del_ph_{pid}_{spot_id}",
                                          use_container_width=True):
                            delete_row("multimedia", pid)
                            if pp == current_main:
                                update_row("bait_spots", spot_id, {"photo_path": ""})
                            st.cache_data.clear()
                            st.rerun()
        else:
            st.caption("Aucune photo pour ce spot.")

        st.markdown("---")
        st.markdown("**➕ Ajouter une photo**")
        ss_key = f"ba_photo_{spot_id}"
        with st.container(border=True):
            _photo_pick(f"ba_cam_{spot_id}", f"ba_upl_{spot_id}", ss_key)
            _photo_preview(ss_key, f"ba_clear_{spot_id}")

        titre_ph = st.text_input("Titre / légende",
                                   placeholder="Ex : Vue d'ensemble, Détail estran…",
                                   key=f"ba_titre_{spot_id}")
        if st.session_state.get(ss_key):
            if st.button("💾 Enregistrer la photo",
                          key=f"ba_save_ph_{spot_id}",
                          type="primary", use_container_width=True):
                _save_photo_from_ss(ss_key, spot_id, titre_ph or nom)
                st.cache_data.clear()
                st.success("✅ Photo ajoutée !")
                st.rerun()
