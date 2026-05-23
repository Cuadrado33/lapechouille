"""
Page « Mes sessions » — création, vue détail (modifier + captures + photos), liste.
"""
from __future__ import annotations
from datetime import date, datetime, time
from pathlib import Path
from typing import Dict, Any

import pandas as pd
import streamlit as st

from core.database import (
    load_sessions, load_captures, load_captures_for_session,
    insert_row, update_row, delete_session, delete_capture, next_capture_number,
    load_spots, load_materiel,
)
from core.external_apis import estimate_tide, fetch_weather, fetch_marine, mean_between_hours
from core.storage import save_capture_photo, save_multimedia_photo
from core.utils import (
    safe_str, safe_float, format_date_fr, parse_date_safe,
    parse_time_safe, compute_duration_hours, list_index,
    estimate_fish_weight_g, format_weight_display,
)
from data.constants import (
    TYPES_SESSION, PHASES_MAREE, CLARTE_EAU, ESPECES, APPATS, MONTAGES,
    MARQUES_HAMECONS, TYPES_HAMECONS, MODELES_HAMECONS, TAILLES_HAMECONS,
)
from data.emojis import APPAT, MER, icon_box
from data.fish_data import FISH_SVG, FISH_EMOJI_FALLBACK
import streamlit.components.v1 as _comp

APPAT_SVG_MAP = {
    "Arénicole":      APPAT.get("arenicole", ""),
    "Néréide":        APPAT.get("nereide", ""),
    "Bibi":           APPAT.get("bibi", ""),
    "Couteau / Clam": APPAT.get("couteau_clam", ""),
    "Crabe":          APPAT.get("crabe", ""),
    "Crevette":       APPAT.get("crevette", ""),
    "Seiche":         APPAT.get("seiche", ""),
    "Lançon":         APPAT.get("lancon", ""),
    "Sardine":        APPAT.get("sardine", ""),
    "Moule":          APPAT.get("moule", ""),
}
from ui.components import (
    hero, section, confirm_destructive, terrestrial_map,
    location_picker, photo_inputs, photo_placeholder,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _session_icon(type_session: str) -> str:
    if type_session == "Compétition": return "🏆"
    if type_session == "Entraînement": return "🎯"
    return "🎣"

def _session_title(row) -> str:
    type_s = safe_str(row.get("type_session")) or "Loisir"
    lieu   = safe_str(row.get("lieu")) or "Sans lieu"
    d      = format_date_fr(row.get("date_session")) or "—"
    return f"{type_s} · {lieu} · {d}"

def _spot_quickselect(prefix: str) -> None:
    try:
        spots_df = load_spots()
    except Exception:
        return
    if spots_df.empty:
        return
    names = ["— Choisir un spot enregistré —"] + spots_df["nom"].tolist()
    chosen = st.selectbox("⭐ Spot enregistré", names, key=f"{prefix}_spot_qs")
    if chosen != "— Choisir un spot enregistré —":
        row = spots_df[spots_df["nom"] == chosen].iloc[0]
        st.session_state["active_spot_lat"] = float(row["latitude"])
        st.session_state["active_spot_lon"] = float(row["longitude"])
        st.session_state["active_spot_nom"] = chosen
        st.success(f"📍 **{chosen}**")


def _get_user_montages() -> list[str]:
    """Récupère les montages enregistrés dans Matériel (catégorie 'Montage'),
    et complète avec les montages classiques s'il n'y en a pas assez."""
    user_montages = []
    try:
        df = load_materiel("Montage")
        if not df.empty:
            # Préférer montage_nom, sinon modele
            for _, r in df.iterrows():
                nom = safe_str(r.get("montage_nom")) or safe_str(r.get("modele"))
                if nom and nom not in user_montages:
                    user_montages.append(nom)
    except Exception:
        pass

    # Combine : montages perso en premier, puis liste constants sans doublons
    combined = ["— Choisir —"] + user_montages
    if user_montages:
        combined.append("──────────")
    for m in MONTAGES:
        if m not in user_montages:
            combined.append(m)
    return combined


# ─────────────────────────────────────────────────────────────────────────────
# Point d'entrée
# ─────────────────────────────────────────────────────────────────────────────

def render() -> None:
    # Vue détail si une session est sélectionnée
    detail_id = st.session_state.get("ss_detail_id")
    if detail_id:
        sessions = load_sessions()
        if not sessions.empty and detail_id in sessions["id"].values:
            row = sessions[sessions["id"] == detail_id].iloc[0]
            _render_session_detail(row, detail_id)
            return
        else:
            st.session_state.pop("ss_detail_id", None)

    # Bandeau bleu marine pleine largeur
    st.markdown(
        '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        'color:#fff;padding:14px 20px;border-radius:8px;margin:8px 0 18px;">'
        '<span style="font-size:18px;font-weight:800;">📓 Mes sessions</span>'
        '<div style="font-size:12px;opacity:.85;margin-top:3px;">'
        'Crée et suis tes sorties de pêche — captures, météo, conditions.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    tab_new, tab_current, tab_past = st.tabs([
        "➕ Nouvelle session", "🔴 En cours", "📚 Passées",
    ])
    with tab_new:
        _render_new_session()
    with tab_current:
        _render_sessions_list(terminee=False)
    with tab_past:
        # Sous-onglets par type de session
        s_all, s_loisir, s_entrain, s_compet = st.tabs([
            "📋 Toutes", "🎣 Loisir", "🎯 Entraînement", "🏆 Compétition",
        ])
        with s_all:
            _render_sessions_list(terminee=True)
        with s_loisir:
            _render_sessions_list(terminee=True, type_filter="loisir")
        with s_entrain:
            _render_sessions_list(terminee=True, type_filter="entrain")
        with s_compet:
            _render_sessions_list(terminee=True, type_filter="competition")


# ─────────────────────────────────────────────────────────────────────────────
# Création
# ─────────────────────────────────────────────────────────────────────────────

def _render_new_session() -> None:
    section("Créer une session", icon="📝")

    col1, col2 = st.columns(2)
    with col1:
        type_session = st.selectbox("Type", TYPES_SESSION, key="ns_type")
        date_session = st.date_input("Date", value=date.today(), format="DD/MM/YYYY", key="ns_date")
    with col2:
        heure_debut = st.time_input("Heure début", value=time(20, 0), key="ns_debut")
        heure_fin   = st.time_input("Heure fin",   value=time(0,  0), key="ns_fin")

    section("Localisation", icon="📍")

    # ── 2 onglets : spot enregistré OU saisir une localisation ─────────
    tab_spot, tab_saisir = st.tabs(["⭐ Spot enregistré", "🗺️ Saisir une localisation"])

    latitude  = st.session_state.get("ns_loc_lat", None)
    longitude = st.session_state.get("ns_loc_lon", None)

    with tab_spot:
        try:
            spots_df = load_spots()
        except Exception:
            spots_df = None
        if spots_df is None or spots_df.empty:
            st.info("Aucun spot enregistré. Crée-en un dans **Mes spots** ou utilise l'autre onglet.")
        else:
            # Liste avec favoris en premier
            spots_df = spots_df.sort_values(["favori", "nom"], ascending=[False, True])
            names = ["— Choisir un spot —"] + [
                f"{'⭐ ' if bool(r.get('favori')) else ''}{safe_str(r['nom'])}"
                for _, r in spots_df.iterrows()
            ]
            choice = st.selectbox("Spot enregistré", names, key="ns_spot_choice")
            if choice != "— Choisir un spot —":
                clean_name = choice.replace("⭐ ", "", 1)
                row_match = spots_df[spots_df["nom"] == clean_name]
                if not row_match.empty:
                    sp = row_match.iloc[0]
                    latitude  = safe_float(sp.get("latitude"))
                    longitude = safe_float(sp.get("longitude"))
                    st.session_state["ns_loc_lat"] = latitude
                    st.session_state["ns_loc_lon"] = longitude
                    st.session_state["ns_loc_nom"] = clean_name
                    # Affiche les infos du spot
                    info_bits = []
                    for lbl, k in [("Fond", "type_fond"), ("Prof.", "profondeur"),
                                    ("Accès", "acces"), ("Espèces", "especes_cibles")]:
                        v = safe_str(sp.get(k))
                        if v:
                            info_bits.append(f"**{lbl}** : {v}")
                    if info_bits:
                        st.caption(" · ".join(info_bits))
                    st.success(f"✅ Spot « {clean_name} » sélectionné — {latitude:.5f}, {longitude:.5f}")
            else:
                # Aucun spot choisi → vider la mémoire
                st.session_state.pop("ns_loc_nom", None)

    with tab_saisir:
        lat_input, lon_input = location_picker("ns_session", spots_shortcut=False)
        if lat_input is not None and lon_input is not None:
            latitude  = lat_input
            longitude = lon_input
            st.session_state["ns_loc_lat"] = latitude
            st.session_state["ns_loc_lon"] = longitude

    # Fallback si rien n'a été choisi
    if latitude is None or longitude is None:
        latitude  = st.session_state.get("active_spot_lat", 44.656588)
        longitude = st.session_state.get("active_spot_lon", -1.196303)
        st.caption("📌 Position par défaut — utilise l'un des onglets ci-dessus pour la changer.")

    # Nom du lieu : auto-rempli depuis le spot sélectionné OU saisi à la main
    spot_nom = st.session_state.get("ns_loc_nom", "")
    if spot_nom:
        # Un spot enregistré est sélectionné → utilisé automatiquement
        lieu = spot_nom
        st.markdown(
            f'<div style="background:#E8F5E9;border-left:4px solid #2E7D32;'
            f'padding:8px 14px;border-radius:0 6px 6px 0;margin:8px 0;">'
            f'<strong>📍 Lieu de la session :</strong> {lieu}</div>',
            unsafe_allow_html=True,
        )
    else:
        # Pas de spot pré-enregistré → champ texte libre
        lieu = st.text_input(
            "Nom du spot / lieu",
            placeholder="Ex : Plage de la Salie, La Teste-de-Buch...",
            key="ns_lieu",
        )

    with st.expander("🗺️ Voir la carte du spot", expanded=False):
        terrestrial_map(latitude, longitude)

    section("Marée & conditions", icon="🌊")

    # ── Badge contexte temporel + bouton unifié ──────────────────────
    now_dt   = datetime.now()
    sess_dt  = datetime.combine(date_session, heure_debut)
    delta_h  = (sess_dt - now_dt).total_seconds() / 3600

    if delta_h < -1:
        time_badge = (
            f'<span style="background:#ECEFF1;color:#546E7A;padding:3px 10px;'
            f'border-radius:12px;font-size:11px;font-weight:700;">'
            f'📅 SESSION PASSÉE</span>'
        )
    elif delta_h > 1:
        time_badge = (
            f'<span style="background:#E3F2FD;color:#1565C0;padding:3px 10px;'
            f'border-radius:12px;font-size:11px;font-weight:700;">'
            f'🔮 SESSION FUTURE — dans {delta_h:.0f} h</span>'
        )
    else:
        time_badge = (
            f'<span style="background:#FFF3E0;color:#E65100;padding:3px 10px;'
            f'border-radius:12px;font-size:11px;font-weight:700;'
            f'animation:pulse 1.5s infinite;">🔴 SESSION EN COURS</span>'
            f'<style>@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.7}}}}</style>'
        )
    btn_label = "🔄 Récupérer les conditions de la session"

    st.markdown(time_badge, unsafe_allow_html=True)

    # Clé d'invalidation : si date/heure/position ont changé, on vide
    current_key = f"{date_session.isoformat()}_{heure_debut.strftime('%H:%M')}_" \
                  f"{heure_fin.strftime('%H:%M')}_{latitude:.4f}_{longitude:.4f}"
    if st.session_state.get("ns_auto_key") != current_key:
        st.session_state.pop("ns_auto_values", None)
        st.session_state.pop("ns_tide_values", None)
        st.session_state.pop("ns_auto_key", None)

    # ── Bouton unifié : récupère marée + météo en une fois ───────────
    if st.button(btn_label, key="ns_auto", use_container_width=True, type="secondary"):
        st.cache_data.clear()
        target = date_session.isoformat()
        sh = heure_debut.strftime("%H:%M")
        eh = heure_fin.strftime("%H:%M")
        with st.spinner(f"Récupération marée + météo pour le "
                          f"{date_session.strftime('%d/%m/%Y')} ({sh}–{eh})…"):
            # Marée (calculée localement, dépend de la date + position)
            tide_new = estimate_tide(date_session, heure_debut, latitude, longitude)
            st.session_state["ns_tide_values"] = {
                "coefficient": tide_new["coefficient"],
                "phase":       tide_new["phase"],
                "pleine_mer":  tide_new["pleine_mer"].strftime("%H:%M"),
                "basse_mer":   tide_new["basse_mer"].strftime("%H:%M"),
            }
            # Météo / mer (Open-Meteo)
            w_df = fetch_weather(latitude, longitude, target)
            m_df = fetch_marine(latitude, longitude, target)
            auto_values = {**mean_between_hours(w_df, sh, eh),
                            **mean_between_hours(m_df, sh, eh)}
            st.session_state["ns_auto_values"] = auto_values
        st.session_state["ns_auto_key"] = current_key
        if auto_values:
            st.success(f"✅ Conditions récupérées pour le {date_session.strftime('%d/%m/%Y')} "
                        f"({sh}–{eh}).")
        else:
            st.warning("Données météo indisponibles, mais marée mise à jour. "
                        "Vérifie que la date n'est pas trop loin dans le passé/futur.")
        st.rerun()

    # ── Widgets marée — valeurs récupérées si dispo, sinon calcul local ──
    tide_stored = st.session_state.get("ns_tide_values")
    if tide_stored:
        coef_default  = int(tide_stored["coefficient"])
        phase_default = tide_stored["phase"]
        pm_default    = datetime.strptime(tide_stored["pleine_mer"], "%H:%M").time()
        bm_default    = datetime.strptime(tide_stored["basse_mer"], "%H:%M").time()
    else:
        tide_default  = estimate_tide(date_session, heure_debut, latitude, longitude)
        coef_default  = tide_default["coefficient"]
        phase_default = tide_default["phase"]
        pm_default    = tide_default["pleine_mer"]
        bm_default    = tide_default["basse_mer"]

    col3, col4, col5 = st.columns(3)
    with col3:
        coefficient = st.number_input("Coefficient", 20, 120,
                                        value=coef_default, key=f"ns_coef_{current_key}")
        phase       = st.selectbox("Phase de marée", PHASES_MAREE,
                                     index=list_index(PHASES_MAREE, phase_default),
                                     key=f"ns_phase_{current_key}")
    with col4:
        maree_haute = st.time_input("Pleine mer", value=pm_default,
                                      key=f"ns_pm_{current_key}")
        maree_basse = st.time_input("Basse mer",  value=bm_default,
                                      key=f"ns_bm_{current_key}")
    with col5:
        clarte = st.selectbox("Clarté de l'eau", CLARTE_EAU, key="ns_clarte")

    commentaire = st.text_area("Commentaire", placeholder="Courant, algues, stratégie...", key="ns_comment")

    auto_values = st.session_state.get("ns_auto_values", {})
    if auto_values:
        st.caption(f"📊 Météo récupérée pour le **{date_session.strftime('%d/%m/%Y')}** "
                    f"de **{heure_debut.strftime('%H:%M')}** à **{heure_fin.strftime('%H:%M')}**")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Temp. air", f"{auto_values.get('temperature_2m','—')} °C")
        c2.metric("Temp. eau", f"{auto_values.get('sea_surface_temperature','—')} °C")
        c3.metric("Vent",      f"{auto_values.get('wind_speed_10m','—')} km/h")
        c4.metric("Vagues",    f"{auto_values.get('wave_height','—')} m")

    if st.button("💾 Enregistrer la session", type="primary", key="ns_save", use_container_width=True):
        if not lieu.strip():
            st.warning("Renseigne au moins un lieu.")
            return

        # Détecter automatiquement si la session est déjà terminée
        # (date passée OU date d'aujourd'hui avec heure de fin passée)
        now_dt    = datetime.now()
        end_dt    = datetime.combine(date_session, heure_fin)
        is_past   = end_dt < now_dt
        # Cas où heure_fin = 00:00 (placeholder) → on regarde la date seule
        if heure_fin == time(0, 0) and date_session < now_dt.date():
            is_past = True

        data = {
            "type_session": type_session,
            "session_terminee": 1 if is_past else 0,
            "date_session": date_session.isoformat(), "lieu": lieu.strip(),
            "latitude": latitude, "longitude": longitude,
            "heure_debut": heure_debut.strftime("%H:%M"),
            "heure_fin":   heure_fin.strftime("%H:%M"),
            "duree_heures": compute_duration_hours(heure_debut, heure_fin),
            "coefficient_maree": coefficient,
            "maree_haute": maree_haute.strftime("%H:%M"),
            "maree_basse": maree_basse.strftime("%H:%M"),
            "phase_maree": phase, "clarte_eau": clarte,
            "temperature_air":       auto_values.get("temperature_2m"),
            "temperature_eau":       auto_values.get("sea_surface_temperature"),
            "humidite":              auto_values.get("relative_humidity_2m"),
            "pression":              auto_values.get("pressure_msl"),
            "couverture_nuageuse":   auto_values.get("cloud_cover"),
            "vent_vitesse":          auto_values.get("wind_speed_10m"),
            "vent_direction":        auto_values.get("wind_direction_10m"),
            "rafales":               auto_values.get("wind_gusts_10m"),
            "vague_hauteur":         auto_values.get("wave_height"),
            "vague_direction":       auto_values.get("wave_direction"),
            "vague_periode":         auto_values.get("wave_period"),
            "commentaire": commentaire,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        sid = insert_row("sessions", data)
        st.session_state.pop("ns_auto_values", None)
        st.cache_data.clear()
        if is_past:
            st.success(f"✅ Session passée enregistrée (terminée) !")
        else:
            st.success(f"✅ Session démarrée !")
        # Ouvrir directement la vue détail
        st.session_state["ss_detail_id"] = sid
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Liste des sessions (En cours / Passées)
# ─────────────────────────────────────────────────────────────────────────────

def _render_sessions_list(terminee: bool, type_filter: str | None = None) -> None:
    sessions = load_sessions()
    if sessions.empty:
        st.info("Aucune session enregistrée." if terminee else "Aucune session en cours.")
        return

    if "session_terminee" not in sessions.columns:
        sessions["session_terminee"] = 0
    sessions["session_terminee"] = sessions["session_terminee"].fillna(0).astype(int)

    filtered = sessions[sessions["session_terminee"] == (1 if terminee else 0)]

    # Filtre par type
    if type_filter and "type_session" in filtered.columns:
        ts = filtered["type_session"].fillna("").str.lower()
        if type_filter == "competition":
            filtered = filtered[ts.str.contains("ompétition|oncours|hallenge", regex=True, na=False)]
        elif type_filter == "entrain":
            filtered = filtered[ts.str.contains("ntraî|ntrain", regex=True, na=False)]
        elif type_filter == "loisir":
            # Loisir = ni compétition ni entraînement
            filtered = filtered[
                ~ts.str.contains("ompétition|oncours|hallenge|ntraî|ntrain", regex=True, na=False)
            ]

    if filtered.empty:
        st.info("Aucune session dans cette catégorie.")
        return

    search_key = f"ss_search_{terminee}_{type_filter or 'all'}"
    search = st.text_input("Rechercher", placeholder="Lieu, date...", key=search_key)
    if search:
        s = search.lower()
        mask = pd.Series(False, index=filtered.index)
        for col in ["lieu", "date_session", "commentaire", "type_session"]:
            if col in filtered.columns:
                mask |= filtered[col].astype(str).str.lower().str.contains(s, na=False)
        filtered = filtered[mask]

    captures = load_captures()

    # Charger multimedia pour récupérer les photos d'ambiance des sessions
    try:
        from core.database import load_multimedia
        all_mm = load_multimedia()
    except Exception:
        all_mm = pd.DataFrame()

    tf_key = (type_filter or "all").replace(" ", "_")

    for row_idx, (_, row) in enumerate(filtered.iterrows()):
        sid    = int(row["id"])
        type_s = safe_str(row.get("type_session")) or "Loisir"
        lieu   = safe_str(row.get("lieu")) or "—"
        d      = format_date_fr(row.get("date_session")) or "—"
        debut  = safe_str(row.get("heure_debut")) or "—"
        fin    = safe_str(row.get("heure_fin")) or "—"

        sess_caps = captures[captures["session_id"] == sid] \
                    if not captures.empty and "session_id" in captures.columns \
                    else pd.DataFrame()
        nb_cap = len(sess_caps)

        especes_uniq = []
        best_taille  = None
        poids_total  = 0.0
        if not sess_caps.empty:
            if "espece" in sess_caps.columns:
                especes_uniq = sorted({safe_str(x) for x in sess_caps["espece"] if safe_str(x)})
            if "taille_cm" in sess_caps.columns:
                tt = pd.to_numeric(sess_caps["taille_cm"], errors="coerce").dropna()
                tt = tt[tt > 0]
                if not tt.empty:
                    best_taille = float(tt.max())
            if "poids_g" in sess_caps.columns:
                pp_s = pd.to_numeric(sess_caps["poids_g"], errors="coerce").dropna()
                poids_total = float(pp_s.sum())

        type_color = "#C62828" if "ompétition" in type_s \
                     else ("#EF6C00" if "ntra" in type_s else "#2E7D32")
        type_icon  = "🏆" if "ompétition" in type_s \
                     else ("🎯" if "ntra" in type_s else "🎣")

        with st.expander(f"{type_icon} **{lieu}** · {d}", expanded=False):
            coef_s = safe_str(row.get("coefficient_maree"))
            coef_txt = f" · 🌊 Coef {int(float(coef_s))}" if coef_s and coef_s.replace('.','').isdigit() else ""
            st.markdown(
                f'<div style="background:linear-gradient(135deg,{type_color}cc,{type_color}88);'
                f'color:#fff;padding:6px 10px;border-radius:6px;margin-bottom:8px;">'
                f'<span style="font-size:13px;font-weight:800;">{type_icon} {type_s}</span><br>'
                f'<span style="font-size:11px;">📅 {d} · 🕒 {debut}→{fin}{coef_txt}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Photos
            photos_sess = []
            if not sess_caps.empty and "photo_path" in sess_caps.columns:
                for _, cr in sess_caps.iterrows():
                    p = safe_str(cr.get("photo_path"))
                    if p and str(p).startswith("http"):
                        photos_sess.append(p)
            if photos_sess:
                for ph in photos_sess[:3]:
                    _comp.html(
                        f'<img src="{ph}" style="width:100%;max-height:160px;'
                        f'object-fit:cover;border-radius:6px;margin-bottom:4px;">',
                        height=170, scrolling=False,
                    )

            # Stats
            st.markdown(
                f'<div style="margin:6px 0;">'
                f'<span style="background:#E8F5E9;color:#2E7D32;font-size:11px;font-weight:700;padding:2px 8px;border-radius:8px;margin-right:4px;">🐟 {nb_cap} prise(s)</span>'
                + (f'<span style="background:#FFF3E0;color:#E65100;font-size:11px;font-weight:700;padding:2px 8px;border-radius:8px;margin-right:4px;">📏 {best_taille:.0f} cm</span>' if best_taille else '')
                + (f'<span style="background:#E3F2FD;color:#1565C0;font-size:11px;font-weight:700;padding:2px 8px;border-radius:8px;">⚖️ {poids_total/1000:.2f} kg</span>' if poids_total >= 1000 else (f'<span style="background:#E3F2FD;color:#1565C0;font-size:11px;font-weight:700;padding:2px 8px;border-radius:8px;">⚖️ {poids_total:.0f} g</span>' if poids_total > 0 else ''))
                + '</div>',
                unsafe_allow_html=True,
            )

            if especes_uniq:
                st.caption("🐟 " + " · ".join(especes_uniq[:4]))

            meteo_parts = []
            if safe_str(row.get("vent_vitesse")): meteo_parts.append(f"💨 {float(row['vent_vitesse']):.0f} km/h")
            if safe_str(row.get("vague_hauteur")): meteo_parts.append(f"🌊 {float(row['vague_hauteur']):.1f}m")
            if safe_str(row.get("temperature_air")): meteo_parts.append(f"🌡️ {float(row['temperature_air']):.0f}°C")
            if meteo_parts:
                st.caption(" · ".join(meteo_parts))

            mat_parts = []
            if safe_str(row.get("canne")): mat_parts.append(f"🎯 {row['canne']}")
            if safe_str(row.get("moulinet")): mat_parts.append(f"⚙️ {row['moulinet']}")
            if mat_parts:
                st.caption(" · ".join(mat_parts))

            if safe_str(row.get("commentaire")):
                st.caption(f"💬 {safe_str(row.get('commentaire'))}")

            # Boutons — clé unique par tf_key + sid + row_idx
            ca, cb, cc = st.columns(3)
            uk = f"{tf_key}_{sid}_{row_idx}"
            edit_key = f"sess_edit_{uk}"
            if ca.button("✏️ Modifier", key=f"sess_edit_btn_{uk}", use_container_width=True):
                st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                st.rerun()
            share_key = f"sess_share_{uk}"
            if cb.button("📤 Partager", key=f"sess_share_btn_{uk}", use_container_width=True):
                st.session_state[share_key] = not st.session_state.get(share_key, False)
                st.rerun()
            if cc.button("🗑️ Supprimer", key=f"sess_del_btn_{uk}", use_container_width=True):
                st.session_state[f"confirm_sess_{uk}"] = True

            if st.session_state.get(share_key):
                from ui.components import share_button
                txt = (f"🎣 La Péchouille — Ma session de pêche\n\n"
                       f"📍 {lieu}\n"
                       f"📅 {d} · 🕒 {debut}→{fin}\n"
                       f"🐟 {nb_cap} prise(s)\n"
                       + (f"📏 Meilleure : {best_taille:.0f} cm\n" if best_taille else "")
                       + (f"🐟 Espèces : {', '.join(especes_uniq[:4])}\n" if especes_uniq else "")
                       + "\nApp : https://lapechouille.fr")
                share_button(txt, share_key)

            if st.session_state.get(f"confirm_sess_{uk}"):
                if confirm_destructive(f"sess_{uk}", f"Supprimer session {lieu} ?"):
                    delete_session(sid)
                    st.session_state[f"confirm_sess_{uk}"] = False
                    st.cache_data.clear()
                    st.rerun()

            if st.session_state.get(edit_key):
                _render_edit_session(row, sid)


# ─────────────────────────────────────────────────────────────────────────────
# VUE DÉTAIL SESSION — modifier + captures + photos
# ─────────────────────────────────────────────────────────────────────────────

def _render_session_detail(row, sid: int) -> None:
    terminee = bool(int(safe_float(row.get("session_terminee")) or 0))
    type_s   = safe_str(row.get("type_session")) or "Loisir"
    lieu     = safe_str(row.get("lieu")) or "—"
    debut    = safe_str(row.get("heure_debut")) or "—"
    fin_h    = safe_str(row.get("heure_fin")) or "—"
    d        = format_date_fr(row.get("date_session")) or "—"

    # Code couleur par type
    if "ompétition" in type_s:
        type_color, type_icon = "#C62828", "🏆"
    elif "ntra" in type_s:
        type_color, type_icon = "#EF6C00", "🎯"
    else:
        type_color, type_icon = "#1565C0", "🎣"

    status_badge = ('<span style="background:rgba(255,255,255,.25);font-size:10px;'
                    'font-weight:700;padding:2px 8px;border-radius:8px;margin-left:8px;">'
                    '🔴 EN COURS</span>') if not terminee else \
                   ('<span style="background:rgba(255,255,255,.25);font-size:10px;'
                    'font-weight:700;padding:2px 8px;border-radius:8px;margin-left:8px;">'
                    '✅ Terminée</span>')

    st.markdown(
        f'<div style="background:linear-gradient(135deg,{type_color}dd,{type_color}99);'
        f'color:#fff;padding:12px 16px;border-radius:8px;margin:4px 0 12px;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'flex-wrap:wrap;gap:8px;">'
        f'<div><span style="font-size:18px;font-weight:800;">{type_icon} {lieu}</span>'
        f'{status_badge}</div>'
        f'<div style="font-size:12px;opacity:.95;">📅 {d} · 🕒 {debut} → {fin_h}</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # ── Barre de navigation ──────────────────────────────────────────
    col_back, col_end, col_del = st.columns([2, 1.5, 1])
    with col_back:
        if st.button("← Retour à la liste",
                      key="ss_back",
                      use_container_width=True,
                      type="primary"):
            st.session_state.pop("ss_detail_id", None)
            st.rerun()
    with col_end:
        if not terminee:
            if st.button("🛑 Terminer la session", key="ss_end_detail", type="primary",
                          use_container_width=True):
                now_t   = datetime.now().time().replace(second=0, microsecond=0)
                start_t = parse_time_safe(row.get("heure_debut"), time(20, 0))
                update_row("sessions", sid, {
                    "session_terminee": 1,
                    "heure_fin":        now_t.strftime("%H:%M"),
                    "duree_heures":     compute_duration_hours(start_t, now_t),
                })
                st.cache_data.clear()
                st.success("Session terminée.")
                st.rerun()
    with col_del:
        if st.button("🗑️ Supprimer", key=f"ss_del_detail_{sid}",
                      use_container_width=True, help="Supprimer cette session"):
            st.session_state[f"confirm_ss_detail_{sid}"] = True

    # Confirmation suppression
    if st.session_state.get(f"confirm_ss_detail_{sid}"):
        if confirm_destructive(f"ss_detail_{sid}",
                               "⚠️ Supprimer cette session ainsi que toutes ses captures et photos ?"):
            delete_session(sid)
            st.session_state.pop(f"confirm_ss_detail_{sid}", None)
            st.session_state.pop("ss_detail_id", None)
            st.cache_data.clear()
            st.success("Session supprimée.")
            st.rerun()

    # ── Onglets de la vue détail ─────────────────────────────────────
    tab_caps, tab_photos, tab_edit = st.tabs([
        "🐟 Captures", "📸 Photos de session", "✏️ Modifier la session"
    ])

    with tab_caps:
        _render_session_captures(sid, terminee)

    with tab_photos:
        _render_session_photos(sid)

    with tab_edit:
        _render_edit_session(row, sid)


# ─────────────────────────────────────────────────────────────────────────────
# Captures de la session
# ─────────────────────────────────────────────────────────────────────────────

def _render_session_captures(sid: int, terminee: bool) -> None:
    caps = load_captures_for_session(sid)
    nb   = len(caps)

    # ── Résumé rapide ────────────────────────────────────────────────
    col_nb, col_best, col_add = st.columns([1, 2, 1.5])
    col_nb.metric("Total captures", nb)
    if not caps.empty and "taille_cm" in caps.columns:
        best = caps["taille_cm"].max()
        col_best.metric("Meilleure taille", f"{best:.0f} cm" if best else "—")
    col_add.markdown("")

    # ── Bouton Ajouter une capture ───────────────────────────────────
    add_key = f"cap_add_open_{sid}"
    lbl_add = "✕ Fermer" if st.session_state.get(add_key) else "➕ Ajouter une capture"
    if col_add.button(lbl_add, key=f"cap_add_btn_{sid}",
                      use_container_width=True, type="primary"):
        st.session_state[add_key] = not st.session_state.get(add_key, False)
        st.rerun()

    if st.session_state.get(add_key):
        _render_add_capture_inline(sid)

    st.divider()

    if caps.empty:
        st.info("Aucune capture pour cette session. Clique sur « Ajouter une capture ».")
        return

    # ── Analyse technique détaillée ─────────────────────────────────
    if terminee and not caps.empty:
        st.markdown(
            '<div style="background:linear-gradient(135deg,#263238,#1a2327);'
            'color:#fff;padding:10px 14px;border-radius:8px;margin-bottom:12px;">'
            '<span style="font-size:13px;font-weight:800;letter-spacing:1px;">'
            '📊 ANALYSE TECHNIQUE DE LA SESSION</span></div>',
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            # Espèces
            if "espece" in caps.columns:
                esp_counts = caps["espece"].fillna("—").value_counts()
                badges = "".join(
                    f'<span style="background:#E3F2FD;color:#1565C0;font-size:11px;'
                    f'font-weight:700;padding:3px 10px;border-radius:10px;'
                    f'margin:2px 4px 2px 0;display:inline-block;">'
                    f'🐟 {e} ×{n}</span>'
                    for e, n in esp_counts.items()
                )
                st.markdown(
                    '<div style="font-size:10px;font-weight:700;color:#546E7A;'
                    'letter-spacing:1px;text-transform:uppercase;margin-bottom:4px;">Espèces capturées</div>'
                    f'<div>{badges}</div>',
                    unsafe_allow_html=True,
                )

            a1, a2 = st.columns(2)
            with a1:
                # Appâts
                if "appat" in caps.columns:
                    ap = caps["appat"].dropna()
                    ap = ap[ap.astype(str).str.strip() != ""]
                    if not ap.empty:
                        ap_counts = ap.value_counts()
                        badges_ap = "".join(
                            f'<span style="background:#FFF3E0;color:#E65100;font-size:11px;'
                            f'font-weight:700;padding:3px 10px;border-radius:10px;'
                            f'margin:2px 4px 2px 0;display:inline-block;">'
                            f'🪱 {a} ×{n}</span>'
                            for a, n in ap_counts.items()
                        )
                        st.markdown(
                            '<div style="font-size:10px;font-weight:700;color:#546E7A;'
                            'letter-spacing:1px;text-transform:uppercase;margin:8px 0 4px;">Appâts</div>'
                            f'<div>{badges_ap}</div>',
                            unsafe_allow_html=True,
                        )
                # Montages
                if "montage" in caps.columns:
                    mo = caps["montage"].dropna()
                    mo = mo[mo.astype(str).str.strip().str.len() > 1]
                    if not mo.empty:
                        mo_counts = mo.value_counts()
                        badges_mo = "".join(
                            f'<span style="background:#F3E5F5;color:#6A1B9A;font-size:11px;'
                            f'font-weight:700;padding:3px 10px;border-radius:10px;'
                            f'margin:2px 4px 2px 0;display:inline-block;">'
                            f'🧵 {m} ×{n}</span>'
                            for m, n in mo_counts.items()
                        )
                        st.markdown(
                            '<div style="font-size:10px;font-weight:700;color:#546E7A;'
                            'letter-spacing:1px;text-transform:uppercase;margin:8px 0 4px;">Montages</div>'
                            f'<div>{badges_mo}</div>',
                            unsafe_allow_html=True,
                        )

            with a2:
                # Matériel
                mat_lines = []
                if "canne" in caps.columns:
                    cannes = {safe_str(x) for x in caps["canne"] if safe_str(x)}
                    for c in cannes:
                        mat_lines.append(f"🎯 {c}")
                if "moulinet" in caps.columns:
                    moulinets = {safe_str(x) for x in caps["moulinet"] if safe_str(x)}
                    for m in moulinets:
                        mat_lines.append(f"⚙️ {m}")
                if "bobine_moulinet" in caps.columns:
                    bobines = {safe_str(x) for x in caps["bobine_moulinet"] if safe_str(x)}
                    for b in bobines:
                        mat_lines.append(f"🧵 {b}")
                if mat_lines:
                    badges_mat = "".join(
                        f'<span style="background:#E8F5E9;color:#2E7D32;font-size:11px;'
                        f'font-weight:700;padding:3px 10px;border-radius:10px;'
                        f'margin:2px 4px 2px 0;display:inline-block;">{l}</span>'
                        for l in mat_lines
                    )
                    st.markdown(
                        '<div style="font-size:10px;font-weight:700;color:#546E7A;'
                        'letter-spacing:1px;text-transform:uppercase;margin:0 0 4px;">Matériel utilisé</div>'
                        f'<div>{badges_mat}</div>',
                        unsafe_allow_html=True,
                    )

                # Hameçons
                if "marque_hamecon" in caps.columns or "taille_hamecon" in caps.columns:
                    ham_set = set()
                    for _, c in caps.iterrows():
                        parts = []
                        if safe_str(c.get("marque_hamecon")): parts.append(safe_str(c["marque_hamecon"]))
                        if safe_str(c.get("modele_hamecon")): parts.append(safe_str(c["modele_hamecon"]))
                        if safe_str(c.get("taille_hamecon")): parts.append(f"#{c['taille_hamecon']}")
                        h = " ".join(parts).strip()
                        if h:
                            ham_set.add(h)
                    if ham_set:
                        badges_h = "".join(
                            f'<span style="background:#FFF8E1;color:#F57F17;font-size:11px;'
                            f'font-weight:700;padding:3px 10px;border-radius:10px;'
                            f'margin:2px 4px 2px 0;display:inline-block;">🪝 {h}</span>'
                            for h in ham_set
                        )
                        st.markdown(
                            '<div style="font-size:10px;font-weight:700;color:#546E7A;'
                            'letter-spacing:1px;text-transform:uppercase;margin:8px 0 4px;">Hameçons</div>'
                            f'<div>{badges_h}</div>',
                            unsafe_allow_html=True,
                        )

            # Taux de relâche + distance moyenne
            row_stats = []
            if "relache" in caps.columns:
                nb_rel = int(caps["relache"].fillna(0).astype(int).sum())
                row_stats.append(f"↩️ Relâchées : **{nb_rel}/{nb}** ({nb_rel*100//nb if nb else 0}%)")
            if "distance_lancer_m" in caps.columns:
                dists = pd.to_numeric(caps["distance_lancer_m"], errors="coerce").dropna()
                dists = dists[dists > 0]
                if not dists.empty:
                    row_stats.append(f"🎯 Distance moy. : **{dists.mean():.0f} m** (max {dists.max():.0f} m)")
            if row_stats:
                st.markdown(" · ".join(row_stats))

        st.markdown("")

    st.caption(f"**{nb} capture(s)** · Clique sur ✏️ pour modifier")

    # Charger toutes les captures pour records par espèce
    from core.database import load_captures, load_sessions
    all_caps = load_captures()
    all_sess = load_sessions()

    for i, (_, cap) in enumerate(caps.iterrows()):
        cap_id      = int(cap["id"])
        espece      = safe_str(cap.get("espece")) or "—"
        taille      = safe_float(cap.get("taille_cm"))
        poids_g     = safe_float(cap.get("poids_g"))
        poids_est   = safe_float(cap.get("poids_estime_g"))
        poids_aff   = poids_g or poids_est
        poids_txt   = format_weight_display(cap)
        heure       = safe_str(cap.get("heure_capture")) or "—"
        photo_path  = safe_str(cap.get("photo_path"))
        relache     = bool(cap.get("relache"))
        trophee     = bool(cap.get("poisson_trophee") or cap.get("poisson_trophe"))
        appat       = safe_str(cap.get("appat")) or ""
        montage     = safe_str(cap.get("montage")) or ""
        canne       = safe_str(cap.get("canne")) or ""
        moulinet    = safe_str(cap.get("moulinet")) or ""
        bobine      = safe_str(cap.get("bobine_moulinet")) or ""
        fil         = safe_str(cap.get("fil_corps_de_ligne")) or safe_str(cap.get("fil")) or ""
        taille_fil  = safe_str(cap.get("taille_corps_de_ligne")) or ""
        empile      = safe_str(cap.get("fil_empile")) or ""
        taille_emp  = safe_str(cap.get("taille_empile")) or ""
        dist        = safe_float(cap.get("distance_lancer_m"))
        commentaire = safe_str(cap.get("commentaire")) or ""
        ham_marque  = safe_str(cap.get("marque_hamecon")) or ""
        ham_type    = safe_str(cap.get("type_hamecon")) or ""
        ham_modele  = safe_str(cap.get("modele_hamecon")) or ""
        ham_taille  = safe_str(cap.get("taille_hamecon")) or ""

        # Lieu depuis la session
        lieu = "—"
        sid_cap = cap.get("session_id")
        if sid_cap and not all_sess.empty and "id" in all_sess.columns:
            sr = all_sess[all_sess["id"] == sid_cap]
            if not sr.empty:
                lieu = safe_str(sr.iloc[0].get("lieu")) or "—"

        # Record perso
        record_esp = None
        if not all_caps.empty and "espece" in all_caps.columns and "taille_cm" in all_caps.columns:
            esp_caps = all_caps[all_caps["espece"] == espece]
            if not esp_caps.empty:
                tt = pd.to_numeric(esp_caps["taille_cm"], errors="coerce").dropna()
                if not tt.empty:
                    record_esp = float(tt.max())

        is_record = taille and record_esp and taille >= record_esp

        # Photo lightbox
        lb_id = f"lb_sess_cap_{cap_id}"
        photo_block = ""
        if photo_path and str(photo_path).startswith("http"):
            photo_block = f"""
<img src="{photo_path}" onclick="document.getElementById('{lb_id}').style.display='flex'"
  style="width:100%;height:280px;object-fit:cover;border-radius:8px;
  margin:8px 0;cursor:pointer;background:#f0f4f8;display:block;">
<div id="{lb_id}" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.92);
  z-index:9999;align-items:center;justify-content:center;flex-direction:column;">
  <img src="{photo_path}" style="max-width:90vw;max-height:85vh;object-fit:contain;border-radius:8px;">
  <button onclick="document.getElementById('{lb_id}').style.display='none'"
    style="margin-top:14px;background:rgba(255,255,255,.2);color:#fff;border:none;
    padding:10px 24px;border-radius:8px;font-size:14px;cursor:pointer;">Fermer</button>
</div>"""

        # Badges
        badges = []
        if trophee:   badges.append('<span style="background:#FFD54F;color:#5d3a00;font-size:10px;font-weight:800;padding:3px 8px;border-radius:6px;">TROPHEE</span>')
        if is_record: badges.append('<span style="background:#E8F5E9;color:#1B5E20;font-size:10px;font-weight:800;padding:3px 8px;border-radius:6px;">RECORD PERSO</span>')
        badges.append(f'<span style="background:{"#E8F5E9" if not relache else "#FFF3E0"};color:{"#2E7D32" if not relache else "#E65100"};font-size:10px;font-weight:700;padding:3px 8px;border-radius:6px;">{"GARDE" if not relache else "RELACHE"}</span>')
        badges_html = " ".join(badges)

        # Section Capture
        poisson_rows = []
        if taille:    poisson_rows.append(f'<div class="lp-row"><span class="lp-lbl">Taille</span><span class="lp-val lp-blue">{taille:.0f} cm</span></div>')
        if poids_aff: poisson_rows.append(f'<div class="lp-row"><span class="lp-lbl">Poids</span><span class="lp-val lp-orange">{poids_txt}</span></div>')
        if record_esp and taille:
            diff = taille - record_esp
            diff_txt = f"+{diff:.0f} cm" if diff > 0 else (f"Record !" if diff == 0 else f"{diff:.0f} cm du record")
            poisson_rows.append(f'<div class="lp-row"><span class="lp-lbl">Record perso {espece}</span><span class="lp-val" style="color:#2E7D32;">{record_esp:.0f} cm &nbsp;({diff_txt})</span></div>')
        poisson_rows.append(f'<div class="lp-row"><span class="lp-lbl">Lieu</span><span class="lp-val">{lieu}</span></div>')
        poisson_rows.append(f'<div class="lp-row"><span class="lp-lbl">Heure</span><span class="lp-val">{heure}</span></div>')
        if dist:      poisson_rows.append(f'<div class="lp-row"><span class="lp-lbl">Distance lancer</span><span class="lp-val">{dist:.0f} m</span></div>')

        # Section Technique
        tech_rows = []
        if appat:     tech_rows.append(f'<div class="lp-row"><span class="lp-lbl">Appat</span><span class="lp-val">{appat}</span></div>')
        if montage:   tech_rows.append(f'<div class="lp-row"><span class="lp-lbl">Montage</span><span class="lp-val">{montage}</span></div>')
        if canne:     tech_rows.append(f'<div class="lp-row"><span class="lp-lbl">Canne</span><span class="lp-val">{canne}</span></div>')
        if moulinet:  tech_rows.append(f'<div class="lp-row"><span class="lp-lbl">Moulinet</span><span class="lp-val">{moulinet}</span></div>')
        if bobine:    tech_rows.append(f'<div class="lp-row"><span class="lp-lbl">Bobine</span><span class="lp-val">{bobine}</span></div>')
        if fil:
            fil_txt = fil + (f" {taille_fil}" if taille_fil else "")
            tech_rows.append(f'<div class="lp-row"><span class="lp-lbl">Corps de ligne</span><span class="lp-val">{fil_txt}</span></div>')
        if empile:
            emp_txt = empile + (f" {taille_emp}" if taille_emp else "")
            tech_rows.append(f'<div class="lp-row"><span class="lp-lbl">Empile</span><span class="lp-val">{emp_txt}</span></div>')
        ham = " ".join(filter(None, [ham_marque, ham_type, ham_modele, f"#{ham_taille}" if ham_taille else ""]))
        if ham:       tech_rows.append(f'<div class="lp-row"><span class="lp-lbl">Hamecon</span><span class="lp-val">{ham}</span></div>')

        poisson_html = "".join(poisson_rows)
        tech_html    = "".join(tech_rows)
        tech_section = f'<div class="lp-section-title">Technique</div>{tech_html}' if tech_html else ""
        comment_section = f'<div style="background:#f8f9fa;border-left:3px solid #1565C0;padding:8px 12px;border-radius:4px;font-size:12px;color:#546E7A;font-style:italic;margin-top:8px;">{commentaire}</div>' if commentaire else ""

        # Hauteur dynamique
        h_base   = 80
        h_rows   = (len(poisson_rows) + len(tech_rows)) * 28
        h_titles = 30 + (30 if tech_html else 0)
        h_photo  = 290 if photo_block else 0
        h_com    = 50  if commentaire else 0
        h_total  = h_base + h_rows + h_titles + h_photo + h_com + 30

        with st.container(border=True):
            _comp.html(f"""
<style>
.lp-card {{ font-family:system-ui,sans-serif;color:#1a2332; }}
.lp-header {{ background:linear-gradient(135deg,#0c2340,#1565C0);color:#fff;
  padding:10px 14px;border-radius:10px;margin-bottom:10px; }}
.lp-species {{ font-size:17px;font-weight:900;letter-spacing:.3px; }}
.lp-badges {{ margin-top:5px;display:flex;gap:6px;flex-wrap:wrap; }}
.lp-section-title {{ font-size:9px;font-weight:800;letter-spacing:1.5px;
  text-transform:uppercase;color:#90A4AE;margin:10px 0 4px; }}
.lp-row {{ display:flex;justify-content:space-between;align-items:center;
  padding:4px 0;border-bottom:1px solid #f0f4f8; }}
.lp-lbl {{ font-size:11px;color:#78909C;font-weight:500; }}
.lp-val {{ font-size:12px;font-weight:700;color:#1a2332; }}
.lp-blue {{ background:#E3F2FD;color:#1565C0;padding:1px 7px;border-radius:6px; }}
.lp-orange {{ background:#FFF3E0;color:#E65100;padding:1px 7px;border-radius:6px; }}
</style>
<div class="lp-card">
  <div class="lp-header">
    <div class="lp-species">🐟 {espece}</div>
    <div class="lp-badges">{badges_html}</div>
  </div>
  {photo_block}
  <div class="lp-section-title">Capture</div>
  {poisson_html}
  {tech_section}
  {comment_section}
</div>
""", height=h_total, scrolling=False)

            # Boutons actions
            ca, cb, cc = st.columns(3)
            edit_cap_key = f"cap_edit_open_{cap_id}"
            if ca.button("✏️ Modifier", key=f"cap_edit_btn_{cap_id}",
                          use_container_width=True):
                st.session_state[edit_cap_key] = not st.session_state.get(edit_cap_key, False)
                st.rerun()
            if cb.button("📋 Copier", key=f"cap_copy_{cap_id}",
                          use_container_width=True):
                _duplicate_capture(cap, sid)
                st.rerun()
            if cc.button("🗑️ Suppr.", key=f"cap_del_{cap_id}",
                          use_container_width=True):
                st.session_state[f"confirm_cap_{cap_id}"] = True

            if st.session_state.get(f"confirm_cap_{cap_id}"):
                if confirm_destructive(f"cap_{cap_id}", f"Supprimer cette capture ({espece}) ?"):
                    delete_capture(cap_id)
                    st.session_state[f"confirm_cap_{cap_id}"] = False
                    st.cache_data.clear()
                    st.rerun()

            if st.session_state.get(edit_cap_key):
                _render_edit_capture_inline(cap, cap_id)


def _duplicate_capture(cap, sid: int) -> None:
    """Crée une nouvelle capture identique avec un nouveau numéro et l'heure courante.
    Ne copie pas la photo (numéro auto incrémenté, heure = maintenant)."""
    new_num = next_capture_number(sid)
    now_t   = datetime.now()
    # Champs à copier (tout sauf id, photo, numéro, heure, date de création)
    copy_fields = [
        "espece", "taille_cm", "poids_g", "poids_estime_g", "poisson_trophee",
        "appat", "montage", "marque_hamecon", "type_hamecon",
        "modele_hamecon", "taille_hamecon", "hamecon",
        "canne", "moulinet", "bobine_moulinet",
        "fil", "fil_corps_de_ligne", "taille_corps_de_ligne",
        "fil_empile", "taille_empile",
        "distance_lancer_m", "relache", "commentaire",
    ]
    new_data = {
        "session_id":     sid,
        "capture_num":    new_num,
        "capture_label":  f"Capture {new_num}",
        "heure_capture":  now_t.strftime("%H:%M"),
        "created_at":     now_t.isoformat(timespec="seconds"),
    }
    for f in copy_fields:
        try:
            v = cap.get(f) if hasattr(cap, "get") else None
            if v is not None and not (isinstance(v, float) and pd.isna(v)):
                new_data[f] = v
        except Exception:
            continue
    insert_row("captures", new_data)
    st.cache_data.clear()
    espece = safe_str(cap.get("espece")) if hasattr(cap, "get") else "—"
    st.success(f"✅ Capture copiée — nouvelle « {espece} » créée à {now_t.strftime('%H:%M')}")


def _render_add_capture_inline(sid: int) -> None:
    """Formulaire d'ajout de capture — photo HORS form."""
    with st.container(border=True):
        st.markdown("**➕ Nouvelle capture**")

        # Photo HORS formulaire (incompatible avec st.form)
        with st.container(border=True):
            st.markdown("**📸 Photo de la capture**")
            col_cam, col_up = st.columns(2)
            with col_cam:
                cam = st.camera_input("Appareil photo", key=f"nc_cam_{sid}")
            with col_up:
                upl = st.file_uploader("Importer", type=["jpg","jpeg","png","webp"],
                                        key=f"nc_upl_{sid}")
            new_photo = upl if upl is not None else cam

        # ── Matériel HORS form pour que le changement de moulinet déclenche un rerun ──
        with st.expander("🎒 Matériel utilisé (canne / moulinet / bobine)"):
            cannes_opts = ["— Aucune —"]
            try:
                df_c = load_materiel("canne")
                if not df_c.empty:
                    for _, r in df_c.iterrows():
                        lbl = f"{safe_str(r.get('marque'))} {safe_str(r.get('modele'))}".strip()
                        if lbl and lbl not in cannes_opts:
                            cannes_opts.append(lbl)
            except Exception:
                pass

            moulinets_opts = ["— Aucun —"]
            moulinets_bobines = {}
            try:
                import json as _json
                df_m = load_materiel("moulinet")
                if not df_m.empty:
                    for _, r in df_m.iterrows():
                        lbl = f"{safe_str(r.get('marque'))} {safe_str(r.get('modele'))}".strip()
                        if not lbl or lbl in moulinets_opts:
                            continue
                        moulinets_opts.append(lbl)
                        bobs = []
                        try:
                            bj = safe_str(r.get("bobines_json"))
                            if bj:
                                for i, b in enumerate(_json.loads(bj), start=1):
                                    bobs.append(
                                        f"Bobine {i} — {b.get('type_fil','')} {b.get('diametre','')}".strip()
                                    )
                        except Exception:
                            pass
                        moulinets_bobines[lbl] = bobs
            except Exception:
                pass

            mc1, mc2 = st.columns(2)
            canne_sel    = mc1.selectbox("🎯 Canne",    cannes_opts,
                                            key=f"nc_canne_{sid}")
            moulinet_sel = mc2.selectbox("⚙️ Moulinet", moulinets_opts,
                                            key=f"nc_moul_{sid}")

            # Liste des bobines dynamique selon le moulinet choisi
            bobines_opts = ["— Aucune —"]
            if moulinet_sel and moulinet_sel != "— Aucun —":
                bobines_opts.extend(moulinets_bobines.get(moulinet_sel, []))
            bobine_sel = st.selectbox("🧵 Bobine utilisée", bobines_opts,
                                        key=f"nc_bob_{sid}",
                                        help="Bobines du moulinet sélectionné ci-dessus")

        with st.form(f"add_cap_{sid}", clear_on_submit=True):
            cap_num = next_capture_number(sid)
            st.caption(f"Capture n°{cap_num} · Session #{sid}")

            c1, c2, c3 = st.columns(3)
            with c1:
                espece = st.selectbox("Espèce", ESPECES, key=f"nc_esp_{sid}")
                taille = st.number_input("Taille (cm)", 0.0, step=1.0, key=f"nc_t_{sid}")
            with c2:
                poids  = st.number_input("Poids mesuré (g)", 0.0, step=10.0, key=f"nc_p_{sid}")
                heure  = st.time_input("Heure", value=datetime.now().time().replace(second=0, microsecond=0),
                                        key=f"nc_h_{sid}")
            with c3:
                appat   = st.selectbox("Appât",   APPATS,   key=f"nc_a_{sid}")
                montage_opts = _get_user_montages()
                montage = st.selectbox("Montage", montage_opts, key=f"nc_m_{sid}",
                                         help="Tes montages enregistrés en haut, classiques en dessous")
                # Ignorer les séparateurs et "— Choisir —"
                if montage in ("— Choisir —", "──────────"):
                    montage = None

            c4, c5 = st.columns(2)
            relache = c4.checkbox("↩️ Relâché", value=True,  key=f"nc_r_{sid}")
            trophee = c5.checkbox("🏅 Trophée", value=False, key=f"nc_tr_{sid}")

            with st.expander("🪝 Détails hameçon"):
                h1, h2, h3, h4 = st.columns(4)
                marque_h = h1.selectbox("Marque",  MARQUES_HAMECONS, key=f"nc_mh_{sid}")
                type_h   = h2.selectbox("Type",    TYPES_HAMECONS,   key=f"nc_th_{sid}")
                modele_h = h3.selectbox("Modèle",  MODELES_HAMECONS, key=f"nc_mdh_{sid}")
                taille_h = h4.selectbox("Taille",  TAILLES_HAMECONS, key=f"nc_tlh_{sid}")

            distance    = st.number_input("Distance lancer (m)", 0.0, step=5.0, key=f"nc_d_{sid}")
            commentaire = st.text_area("Commentaire", key=f"nc_com_{sid}")

            if st.form_submit_button("🎣 Enregistrer la capture",
                                      use_container_width=True, type="primary"):
                # Récupérer les valeurs matériel depuis session_state (sélectionnées hors form)
                canne    = st.session_state.get(f"nc_canne_{sid}", "— Aucune —")
                moulinet = st.session_state.get(f"nc_moul_{sid}",  "— Aucun —")
                bobine   = st.session_state.get(f"nc_bob_{sid}",   "— Aucune —")

                poids_est = estimate_fish_weight_g(espece, taille) if poids <= 0 else None
                data = {
                    "session_id": sid, "capture_num": cap_num,
                    "capture_label": f"Capture {cap_num}", "espece": espece,
                    "taille_cm": taille or None, "poids_g": poids or None,
                    "poids_estime_g": poids_est, "poisson_trophee": int(trophee),
                    "heure_capture": heure.strftime("%H:%M"),
                    "appat":   appat   if appat   != "Non renseigné" else None,
                    "montage": montage,
                    "marque_hamecon": marque_h, "type_hamecon": type_h,
                    "modele_hamecon": modele_h, "taille_hamecon": taille_h,
                    "hamecon": f"{marque_h} | {type_h} | {modele_h} | {taille_h}",
                    "canne":           canne    if canne    not in ("— Aucune —", "") else None,
                    "moulinet":        moulinet if moulinet not in ("— Aucun —", "")  else None,
                    "bobine_moulinet": bobine   if bobine   not in ("— Aucune —", "") else None,
                    "distance_lancer_m": distance or None,
                    "relache": int(relache), "commentaire": commentaire,
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                }
                cap_id = insert_row("captures", data)
                if new_photo:
                    pp = save_capture_photo(new_photo, cap_id)
                    if pp:
                        update_row("captures", cap_id, {"photo_path": pp})
                st.cache_data.clear()
                st.session_state[f"cap_add_open_{sid}"] = False
                st.success(f"✅ Capture {cap_num} enregistrée !")
                st.rerun()


def _render_edit_capture_inline(cap, cap_id: int) -> None:
    """Modification inline d'une capture — photo + matériel HORS form."""
    with st.container(border=True):
        st.markdown(f"**✏️ Modifier cette capture**")

        with st.container(border=True):
            st.markdown("**📸 Changer la photo**")
            col_cam, col_up = st.columns(2)
            with col_cam:
                cam = st.camera_input("Appareil", key=f"ec_cam_{cap_id}")
            with col_up:
                upl = st.file_uploader("Importer", type=["jpg","jpeg","png","webp"],
                                        key=f"ec_upl_{cap_id}")
            new_photo = upl if upl is not None else cam

        # ── Matériel HORS form pour que les bobines s'actualisent ──
        with st.expander("🎒 Matériel utilisé (canne / moulinet / bobine)"):
            cannes_opts = ["— Aucune —"]
            try:
                df_c = load_materiel("canne")
                if not df_c.empty:
                    for _, r in df_c.iterrows():
                        lbl = f"{safe_str(r.get('marque'))} {safe_str(r.get('modele'))}".strip()
                        if lbl and lbl not in cannes_opts:
                            cannes_opts.append(lbl)
            except Exception:
                pass
            cur_canne = safe_str(cap.get("canne"))
            if cur_canne and cur_canne not in cannes_opts:
                cannes_opts.append(cur_canne)

            moulinets_opts = ["— Aucun —"]
            moulinets_bobines = {}
            try:
                import json as _json
                df_m = load_materiel("moulinet")
                if not df_m.empty:
                    for _, r in df_m.iterrows():
                        lbl = f"{safe_str(r.get('marque'))} {safe_str(r.get('modele'))}".strip()
                        if not lbl or lbl in moulinets_opts:
                            continue
                        moulinets_opts.append(lbl)
                        bobs = []
                        try:
                            bj = safe_str(r.get("bobines_json"))
                            if bj:
                                for i, b in enumerate(_json.loads(bj), start=1):
                                    bobs.append(
                                        f"Bobine {i} — {b.get('type_fil','')} {b.get('diametre','')}".strip()
                                    )
                        except Exception:
                            pass
                        moulinets_bobines[lbl] = bobs
            except Exception:
                pass
            cur_moulinet = safe_str(cap.get("moulinet"))
            if cur_moulinet and cur_moulinet not in moulinets_opts:
                moulinets_opts.append(cur_moulinet)

            mc1, mc2 = st.columns(2)
            # Index initial : si la clé existe déjà dans session_state, on laisse Streamlit gérer
            canne_idx_init    = cannes_opts.index(cur_canne)       if cur_canne    in cannes_opts    else 0
            moulinet_idx_init = moulinets_opts.index(cur_moulinet) if cur_moulinet in moulinets_opts else 0
            # On utilise la clé pour stocker, et on l'initialise si pas encore définie
            if f"ec_canne_{cap_id}" not in st.session_state:
                st.session_state[f"ec_canne_{cap_id}"] = cannes_opts[canne_idx_init]
            if f"ec_moul_{cap_id}" not in st.session_state:
                st.session_state[f"ec_moul_{cap_id}"] = moulinets_opts[moulinet_idx_init]

            canne_sel    = mc1.selectbox("🎯 Canne", cannes_opts,
                                            key=f"ec_canne_{cap_id}")
            moulinet_sel = mc2.selectbox("⚙️ Moulinet", moulinets_opts,
                                            key=f"ec_moul_{cap_id}")

            # Liste dynamique des bobines du moulinet sélectionné
            bobines_opts = ["— Aucune —"]
            if moulinet_sel and moulinet_sel != "— Aucun —":
                bobines_opts.extend(moulinets_bobines.get(moulinet_sel, []))
            cur_bobine = safe_str(cap.get("bobine_moulinet"))
            if cur_bobine and cur_bobine not in bobines_opts:
                bobines_opts.append(cur_bobine)
            # Si la valeur en session_state n'est plus dans la liste, la réinitialiser
            current_bob_key = f"ec_bob_{cap_id}"
            if current_bob_key in st.session_state and \
               st.session_state[current_bob_key] not in bobines_opts:
                st.session_state[current_bob_key] = bobines_opts[0]
            elif current_bob_key not in st.session_state:
                bob_idx = bobines_opts.index(cur_bobine) if cur_bobine in bobines_opts else 0
                st.session_state[current_bob_key] = bobines_opts[bob_idx]
            bobine_sel = st.selectbox("🧵 Bobine utilisée", bobines_opts,
                                        key=current_bob_key)

        with st.form(f"edit_cap_{cap_id}"):
            c1, c2, c3 = st.columns(3)
            with c1:
                espece = st.selectbox("Espèce", ESPECES,
                                       index=list_index(ESPECES, cap.get("espece")),
                                       key=f"ec_esp_{cap_id}")
                taille = st.number_input("Taille (cm)", 0.0,
                                          value=safe_float(cap.get("taille_cm")),
                                          step=1.0, key=f"ec_t_{cap_id}")
            with c2:
                poids  = st.number_input("Poids (g)", 0.0,
                                          value=safe_float(cap.get("poids_g")),
                                          step=10.0, key=f"ec_p_{cap_id}")
                appat  = st.selectbox("Appât", APPATS,
                                       index=list_index(APPATS, cap.get("appat")),
                                       key=f"ec_a_{cap_id}")
            with c3:
                relache = st.checkbox("↩️ Relâché",
                                       value=bool(cap.get("relache")),
                                       key=f"ec_r_{cap_id}")
                trophee = st.checkbox("🏅 Trophée",
                                       value=bool(cap.get("poisson_trophee") or cap.get("poisson_trophe")),
                                       key=f"ec_tr_{cap_id}")

            # ── Montage ──
            montage_opts = _get_user_montages()
            cur_montage = safe_str(cap.get("montage")) or "— Choisir —"
            montage = st.selectbox("🧵 Montage",
                                     montage_opts,
                                     index=list_index(montage_opts, cur_montage),
                                     key=f"ec_montage_{cap_id}")
            if montage in ("— Choisir —", "──────────"):
                montage = None

            # ── Hameçon ──
            with st.expander("🪝 Hameçon"):
                h1, h2, h3, h4 = st.columns(4)
                marque_h = h1.selectbox("Marque",  MARQUES_HAMECONS,
                                          index=list_index(MARQUES_HAMECONS, cap.get("marque_hamecon")),
                                          key=f"ec_mh_{cap_id}")
                type_h   = h2.selectbox("Type",    TYPES_HAMECONS,
                                          index=list_index(TYPES_HAMECONS, cap.get("type_hamecon")),
                                          key=f"ec_th_{cap_id}")
                modele_h = h3.selectbox("Modèle",  MODELES_HAMECONS,
                                          index=list_index(MODELES_HAMECONS, cap.get("modele_hamecon")),
                                          key=f"ec_mdh_{cap_id}")
                taille_h = h4.selectbox("Taille",  TAILLES_HAMECONS,
                                          index=list_index(TAILLES_HAMECONS, cap.get("taille_hamecon")),
                                          key=f"ec_tlh_{cap_id}")

            # ── Heure + distance ──
            heure_cap = safe_str(cap.get("heure_capture")) or ""
            h_val = time(int(heure_cap[:2]), int(heure_cap[3:5])) if len(heure_cap) == 5 else \
                    datetime.now().time().replace(second=0, microsecond=0)
            hc1, hc2 = st.columns(2)
            heure_edit = hc1.time_input("Heure de capture", value=h_val, key=f"ec_heure_{cap_id}")
            distance   = hc2.number_input("Distance lancer (m)", 0.0, step=5.0,
                                            value=safe_float(cap.get("distance_lancer_m")),
                                            key=f"ec_dist_{cap_id}")

            commentaire = st.text_area("Commentaire",
                                        value=safe_str(cap.get("commentaire")),
                                        key=f"ec_com_{cap_id}")

            if st.form_submit_button("💾 Enregistrer", use_container_width=True, type="primary"):
                # Récupérer les valeurs matériel depuis session_state
                canne_sel    = st.session_state.get(f"ec_canne_{cap_id}", "— Aucune —")
                moulinet_sel = st.session_state.get(f"ec_moul_{cap_id}",  "— Aucun —")
                bobine_sel   = st.session_state.get(f"ec_bob_{cap_id}",   "— Aucune —")

                poids_est = estimate_fish_weight_g(espece, taille) if poids <= 0 else None
                data = {
                    "espece": espece, "taille_cm": taille or None,
                    "poids_g": poids or None, "poids_estime_g": poids_est,
                    "appat": appat if appat != "Non renseigné" else None,
                    "montage": montage,
                    "marque_hamecon": marque_h, "type_hamecon": type_h,
                    "modele_hamecon": modele_h, "taille_hamecon": taille_h,
                    "hamecon": f"{marque_h} | {type_h} | {modele_h} | {taille_h}",
                    "heure_capture": heure_edit.strftime("%H:%M"),
                    "distance_lancer_m": distance or None,
                    "relache": int(relache), "poisson_trophee": int(trophee),
                    "commentaire": commentaire,
                    "canne":           canne_sel    if canne_sel    not in ("— Aucune —", "") else None,
                    "moulinet":        moulinet_sel if moulinet_sel not in ("— Aucun —", "")  else None,
                    "bobine_moulinet": bobine_sel   if bobine_sel   not in ("— Aucune —", "") else None,
                    "updated_at": datetime.now().isoformat(timespec="seconds"),
                }
                update_row("captures", cap_id, data)
                if new_photo:
                    pp = save_capture_photo(new_photo, cap_id)
                    if pp:
                        update_row("captures", cap_id, {"photo_path": pp})
                st.cache_data.clear()
                st.session_state[f"cap_edit_open_{cap_id}"] = False
                st.success("✅ Capture modifiée !")
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Photos de session
# ─────────────────────────────────────────────────────────────────────────────

def _render_session_photos(sid: int) -> None:
    """Photos libres liées à la session — ambiance, paysage, équipe."""
    from core.database import load_multimedia

    section("Photos de session", icon="📸")
    st.caption("Photos de contexte : paysage, setup, ambiance — distinctes des photos de captures.")

    # Upload HORS form
    with st.container(border=True):
        st.markdown("**📷 Ajouter des photos**")
        col_cam, col_up = st.columns(2)
        with col_cam:
            cam = st.camera_input("Prendre une photo", key=f"sp_cam_{sid}")
        with col_up:
            upl = st.file_uploader("Importer (plusieurs possibles)",
                                    type=["jpg","jpeg","png","webp"],
                                    accept_multiple_files=True,
                                    key=f"sp_upl_{sid}")
        titre = st.text_input("Titre / légende", placeholder="Lever de soleil, setup, coucher...",
                               key=f"sp_titre_{sid}")
        all_files = list(upl or [])
        if cam:
            all_files.insert(0, cam)
        if st.button(f"💾 Enregistrer {len(all_files)} photo(s)",
                      key=f"sp_save_{sid}", disabled=len(all_files) == 0,
                      type="primary", use_container_width=True):
            saved = 0
            for f in all_files:
                pp = save_multimedia_photo(f, f"session_{sid}")
                if pp:
                    insert_row("multimedia", {
                        "categorie": "Session",
                        "titre": titre or f"Session #{sid}",
                        "photo_path": pp,
                        "session_id": sid,
                        "favori": 0,
                        "created_at": datetime.now().isoformat(timespec="seconds"),
                    })
                    saved += 1
            if saved:
                st.cache_data.clear()
                st.success(f"✅ {saved} photo(s) ajoutée(s) !")
                st.rerun()

    # Affichage des photos existantes
    try:
        mm = load_multimedia()
        if not mm.empty and "session_id" in mm.columns:
            sess_photos = mm[mm["session_id"] == sid]
            if not sess_photos.empty:
                st.markdown(f"**{len(sess_photos)} photo(s) de cette session**")
                cols = st.columns(3)
                for j, (_, p) in enumerate(sess_photos.iterrows()):
                    pp = safe_str(p.get("photo_path"))
                    if pp and str(pp).startswith("http"):
                        with cols[j % 3]:
                            st.image(pp, caption=safe_str(p.get("titre")),
                                     use_container_width=True)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Modification de la session
# ─────────────────────────────────────────────────────────────────────────────

def _render_edit_session(row, sid: int) -> None:
    section("Modifier la session", icon="✏️")

    with st.form(f"edit_session_{sid}"):
        c1, c2 = st.columns(2)
        with c1:
            type_s = st.selectbox("Type", TYPES_SESSION,
                                   index=list_index(TYPES_SESSION, row.get("type_session")),
                                   key=f"ed_type_{sid}")
            lieu   = st.text_input("Lieu", value=safe_str(row.get("lieu")), key=f"ed_lieu_{sid}")
            date_s = st.date_input("Date",
                                    value=parse_date_safe(row.get("date_session")),
                                    format="DD/MM/YYYY", key=f"ed_date_{sid}")
        with c2:
            coef   = st.number_input("Coefficient", 20, 120,
                                      value=int(safe_float(row.get("coefficient_maree")) or 70),
                                      key=f"ed_coef_{sid}")
            phase  = st.selectbox("Phase marée", PHASES_MAREE,
                                   index=list_index(PHASES_MAREE, row.get("phase_maree")),
                                   key=f"ed_phase_{sid}")
            clarte = st.selectbox("Clarté eau", CLARTE_EAU,
                                   index=list_index(CLARTE_EAU, row.get("clarte_eau")),
                                   key=f"ed_clarte_{sid}")

        comment = st.text_area("Commentaire",
                                value=safe_str(row.get("commentaire")),
                                key=f"ed_com_{sid}")

        if st.form_submit_button("💾 Enregistrer les modifications",
                                  use_container_width=True, type="primary"):
            update_row("sessions", sid, {
                "type_session": type_s, "lieu": lieu,
                "date_session": date_s.isoformat(),
                "coefficient_maree": coef, "phase_maree": phase,
                "clarte_eau": clarte, "commentaire": comment,
            })
            st.cache_data.clear()
            st.success("✅ Session modifiée.")
            st.rerun()
