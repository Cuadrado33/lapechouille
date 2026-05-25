"""
Page « Mode compétition » — démarrage rapide, compétitions en cours et passées.
"""
from __future__ import annotations
from datetime import datetime, date, time, timedelta

import pandas as pd
import streamlit as st

from core.database import (
    load_sessions, load_captures_for_session,
    insert_row, update_row, next_capture_number, delete_session,
)
from core.storage import save_capture_photo
from core.utils import (
    safe_str, safe_float, format_date_fr, list_index,
    estimate_fish_weight_g, parse_time_safe, compute_duration_hours,
)
from data.constants import ESPECES, APPATS
from ui.components import (
    hero, section, metric_grid, photo_inputs,
    confirm_destructive, location_picker,
)

TYPES_COMPETITION = [
    "Compétition club",
    "Compétition régionale",
    "Compétition nationale",
    "Concours libre",
    "Challenge perso",
]


# ─────────────────────────────────────────────────────────────────────────────
# Point d'entrée
# ─────────────────────────────────────────────────────────────────────────────

def render() -> None:
    # Bandeau bleu marine pleine largeur
    st.markdown(
        '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        'color:#fff;padding:14px 20px;border-radius:8px;margin:8px 0 18px;">'
        '<span style="font-size:18px;font-weight:800;">🏆 Mode compétition</span>'
        '<div style="font-size:12px;opacity:.85;margin-top:3px;">'
        'Compteur temps réel, classement par espèce, saisie rapide.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    tab_new, tab_current, tab_past = st.tabs([
        "🚀 Démarrer", "🔴 En cours", "📚 Passées",
    ])

    with tab_new:
        _render_new_competition()
    with tab_current:
        _render_competition_list(terminee=False)
    with tab_past:
        _render_competition_list(terminee=True)


# ─────────────────────────────────────────────────────────────────────────────
# ONGLET 1 — Démarrer une compétition
# ─────────────────────────────────────────────────────────────────────────────

def _render_new_competition() -> None:
    st.markdown(
        '<div style="background:#FFF3E0;border-left:4px solid #E65100;'
        'padding:10px 14px;border-radius:0 6px 6px 0;margin-bottom:14px;">'
        '<strong>⚡ Démarrage rapide</strong><br>'
        '<span style="font-size:12px;color:#5d3a14;">Remplis les infos puis '
        'clique sur <strong>START</strong> — la session démarre immédiatement.</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        # ── Saisie rapide ────────────────────────────────────────────
        c1, c2 = st.columns(2)
        with c1:
            type_comp = st.selectbox("Type", TYPES_COMPETITION, key="cn_type")
            nom_comp  = st.text_input("Nom de la compétition",
                                       placeholder="Ex : Trophée d'Arcachon 2026",
                                       key="cn_nom")
        with c2:
            # Mode chrono ou timer
            mode = st.radio(
                "Mode de mesure",
                ["⏱️ Chronomètre (compte le temps écoulé)",
                 "⏳ Timer (compte à rebours)"],
                key="cn_mode", horizontal=False,
                help="Chrono : compte à partir de 0 sans limite — Timer : compte à rebours jusqu'à 0"
            )
            is_timer = mode.startswith("⏳")

            if is_timer:
                duree_min = st.number_input("Durée du timer (minutes)",
                                              min_value=5, max_value=720,
                                              value=180, step=5, key="cn_duree",
                                              help="Le timer démarrera à cette durée puis décompte jusqu'à 0")
                st.caption(f"⏳ Compte à rebours de {duree_min // 60}h{duree_min % 60:02d}")
            else:
                duree_renseignee = st.checkbox("Définir une durée prévue",
                                                  value=False, key="cn_duree_check",
                                                  help="Décoche pour un chrono sans heure de fin estimée")
                if duree_renseignee:
                    duree_min = st.number_input("Durée prévue (en minutes)",
                                                  min_value=15, max_value=720,
                                                  value=180, step=15, key="cn_duree",
                                                  help="Indicatif — le chrono compte sans limite")
                    st.caption(f"⏱️ Chrono — durée prévue {duree_min // 60}h{duree_min % 60:02d}")
                else:
                    duree_min = None
                    st.caption("⏱️ Chrono — pas d'heure de fin prévue, tu finiras quand tu voudras")

        # ── Localisation rapide ──────────────────────────────────────
        st.markdown("**📍 Localisation**")
        col_geo, col_coords = st.columns([1, 2])
        with col_geo:
            if st.button("📡 Me géolocaliser", key="cn_geoloc",
                          use_container_width=True,
                          help="Récupère ta position GPS actuelle"):
                st.session_state["cn_use_gps"] = True
                st.rerun()

        # Récupération GPS si demandée
        if st.session_state.get("cn_use_gps"):
            lat, lon = location_picker("cn_loc", spots_shortcut=False)
            if lat is not None and lon is not None:
                st.session_state["cn_lat"] = lat
                st.session_state["cn_lon"] = lon
        else:
            lat = st.session_state.get("cn_lat")
            lon = st.session_state.get("cn_lon")

        with col_coords:
            if lat and lon:
                st.markdown(
                    f'<div style="background:#E8F5E9;border-left:4px solid #2E7D32;'
                    f'padding:8px 12px;border-radius:0 6px 6px 0;">'
                    f'<strong>📍 Position GPS :</strong> '
                    f'<code>{lat:.5f}, {lon:.5f}</code></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.caption("Aucune position définie — clique sur « Me géolocaliser ».")

        # Lieu texte libre
        lieu = st.text_input("Lieu / nom du spot",
                              placeholder="Ex : Plage de la Salie",
                              key="cn_lieu")

        st.divider()

        # ── Bouton START ─────────────────────────────────────────────
        if st.button("🚀 START — Démarrer la compétition",
                      key="cn_start", use_container_width=True,
                      type="primary"):
            errors = []
            if not nom_comp.strip():
                errors.append("Nom de la compétition obligatoire.")
            if not (lat and lon):
                lat = 44.656588
                lon = -1.196303
            if not lieu.strip():
                lieu = nom_comp.strip()

            if errors:
                for e in errors:
                    st.error(e)
            else:
                now_t = datetime.now()
                heure_fin_prev = (now_t + timedelta(minutes=duree_min)).time() if duree_min else None
                # Tag le mode dans le commentaire pour le retrouver après rerun
                mode_tag = "[TIMER]" if is_timer else "[CHRONO]"
                sid = insert_row("sessions", {
                    "type_session":     type_comp,
                    "session_terminee": 0,
                    "date_session":     now_t.date().isoformat(),
                    "lieu":             lieu.strip(),
                    "latitude":         lat,
                    "longitude":        lon,
                    "heure_debut":      now_t.strftime("%H:%M"),
                    "heure_fin":        heure_fin_prev.strftime("%H:%M") if heure_fin_prev else None,
                    "duree_heures":     round(duree_min / 60, 2) if duree_min else None,
                    "commentaire":      f"{mode_tag} 🏆 {nom_comp.strip()} — "
                                          f"{'compte à rebours' if is_timer else 'chrono'}"
                                          + (f" {duree_min} min" if duree_min else " (sans durée prévue)"),
                    "created_at":       now_t.isoformat(timespec="seconds"),
                })
                # Nettoyer le state
                for k in ("cn_use_gps", "cn_lat", "cn_lon"):
                    st.session_state.pop(k, None)
                st.cache_data.clear()
                st.session_state["comp_current_id"] = sid
                st.success(f"✅ Compétition « {nom_comp} » démarrée à {now_t.strftime('%H:%M')} !")
                from ui.components import fish_animation
                fish_animation()
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# ONGLET 2 / 3 — Liste compétitions
# ─────────────────────────────────────────────────────────────────────────────

def _render_competition_list(terminee: bool) -> None:
    sessions = load_sessions()
    if sessions.empty:
        st.info("Aucune compétition.")
        return

    # Filtrer sur sessions de type compétition
    mask_type  = sessions["type_session"].fillna("").str.contains("ompétition|oncours|hallenge",
                                                                     regex=True, na=False)
    mask_state = sessions["session_terminee"].fillna(0).astype(int) == (1 if terminee else 0)
    comps = sessions[mask_type & mask_state]

    if comps.empty:
        st.info("Aucune compétition " + ("passée." if terminee else "en cours."))
        return

    st.caption(f"{len(comps)} compétition(s)")

    # Si une compétition est sélectionnée comme "en cours" → vue compteur
    selected_id = st.session_state.get("comp_current_id") if not terminee else None
    if selected_id and selected_id in comps["id"].values:
        row = comps[comps["id"] == selected_id].iloc[0]
        _render_competition_counter(row, int(selected_id))
        st.divider()

    # Liste des autres compétitions
    for _, row in comps.iterrows():
        sid    = int(row["id"])
        if sid == selected_id:
            continue
        nom    = safe_str(row.get("lieu")) or "—"
        d      = format_date_fr(row.get("date_session"))
        debut  = safe_str(row.get("heure_debut"))
        fin    = safe_str(row.get("heure_fin"))
        type_s = safe_str(row.get("type_session"))
        com    = safe_str(row.get("commentaire"))

        with st.container(border=True):
            col_info, col_act, col_del = st.columns([4, 1.2, 0.8])
            with col_info:
                st.markdown(f"**🏆 {nom}**")
                st.caption(f"{type_s} · {d} · {debut}{' → ' + fin if fin else ''}")
                if com:
                    st.caption(f"💬 {com}")
            with col_act:
                if not terminee:
                    if st.button("👁️ Suivre", key=f"comp_view_{sid}",
                                  use_container_width=True, type="primary"):
                        st.session_state["comp_current_id"] = sid
                        st.rerun()
                else:
                    if st.button("📊 Voir", key=f"comp_detail_{sid}",
                                  use_container_width=True):
                        st.session_state["ss_detail_id"] = sid
                        st.session_state["nav_page"]  = "sessions"
                        st.rerun()
            with col_del:
                if st.button("🗑️ Supprimer", key=f"comp_del_{sid}",
                              use_container_width=True, help="Supprimer"):
                    st.session_state[f"comp_confirm_del_{sid}"] = True

            if st.session_state.get(f"comp_confirm_del_{sid}"):
                if confirm_destructive(f"comp_{sid}",
                                       f"⚠️ Supprimer la compétition « {nom} » avec ses captures et photos ?"):
                    delete_session(sid)
                    st.session_state.pop(f"comp_confirm_del_{sid}", None)
                    st.cache_data.clear()
                    st.success("Compétition supprimée.")
                    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Vue compteur d'une compétition en cours
# ─────────────────────────────────────────────────────────────────────────────

def _render_competition_counter(row, sid: int) -> None:
    nom = safe_str(row.get("lieu")) or "Compétition en cours"
    com = safe_str(row.get("commentaire"))

    # ── En-tête ──────────────────────────────────────────────────────
    with st.container(border=True):
        col_t, col_btn = st.columns([3, 1])
        with col_t:
            st.markdown(f"### 🔴 {nom}")
            if com:
                st.caption(com)
        with col_btn:
            if st.button("🛑 Terminer", key=f"comp_end_{sid}",
                          use_container_width=True, type="primary"):
                now_t   = datetime.now().time().replace(second=0, microsecond=0)
                start_t = parse_time_safe(row.get("heure_debut"), time(8, 0))
                update_row("sessions", sid, {
                    "session_terminee": 1,
                    "heure_fin":        now_t.strftime("%H:%M"),
                    "duree_heures":     compute_duration_hours(start_t, now_t),
                })
                st.session_state.pop("comp_current_id", None)
                st.cache_data.clear()
                st.success("Compétition terminée.")
                st.rerun()

    # ── Compteur LIVE en grand (chrono ou timer) ─────────────────────
    com = safe_str(row.get("commentaire"))
    is_timer  = "[TIMER]" in com
    start_t   = parse_time_safe(row.get("heure_debut"))
    start_dt  = datetime.combine(datetime.now().date(), start_t)
    duree_h   = safe_float(row.get("duree_heures")) or 3.0
    end_dt    = start_dt + timedelta(hours=duree_h)

    # JS pour compteur live (s'actualise toutes les secondes côté client)
    start_iso = start_dt.isoformat()
    end_iso   = end_dt.isoformat()
    mode_str  = "timer" if is_timer else "chrono"
    label     = "⏳ TEMPS RESTANT" if is_timer else "⏱️ TEMPS ÉCOULÉ"
    bg        = "linear-gradient(135deg,#C62828,#7B1538)" if is_timer \
                else "linear-gradient(135deg,#1565C0,#0c2340)"

    import streamlit.components.v1 as _comp
    counter_html = f"""
<div id="comp-counter-{sid}" style="background:{bg};color:#fff;
    border-radius:14px;padding:24px;margin:14px 0;text-align:center;
    box-shadow:0 4px 16px rgba(0,0,0,.18);font-family:system-ui,sans-serif;">
  <div style="font-size:13px;font-weight:700;letter-spacing:3px;
              opacity:.85;margin-bottom:8px;">{label}</div>
  <div id="counter-display-{sid}"
       style="font-size:72px;font-weight:900;letter-spacing:2px;
              font-variant-numeric:tabular-nums;line-height:1;">--:--:--</div>
  <div id="counter-sub-{sid}" style="font-size:14px;opacity:.85;
              margin-top:8px;font-weight:500;"></div>
</div>
<script>
(function() {{
  const start = new Date("{start_iso}").getTime();
  const end   = new Date("{end_iso}").getTime();
  const mode  = "{mode_str}";
  const disp  = document.getElementById("counter-display-{sid}");
  const sub   = document.getElementById("counter-sub-{sid}");
  if (!disp) return;
  function pad(n) {{ return String(n).padStart(2, '0'); }}
  function format(ms) {{
    const totalSec = Math.max(0, Math.floor(ms / 1000));
    const h = Math.floor(totalSec / 3600);
    const m = Math.floor((totalSec % 3600) / 60);
    const s = totalSec % 60;
    return pad(h) + ":" + pad(m) + ":" + pad(s);
  }}
  function tick() {{
    const now = Date.now();
    if (mode === "timer") {{
      const remaining = end - now;
      if (remaining <= 0) {{
        disp.innerText = "00:00:00";
        disp.style.color = "#FFEB3B";
        sub.innerText = "⛔ TEMPS ÉCOULÉ !";
      }} else {{
        disp.innerText = format(remaining);
        sub.innerText  = "Sur " + format(end - start) + " total";
      }}
    }} else {{
      const elapsed = now - start;
      disp.innerText = format(elapsed);
      sub.innerText  = "Démarré à {start_t.strftime("%H:%M")}";
    }}
  }}
  tick();
  setInterval(tick, 1000);
}})();
</script>
"""
    _comp.html(counter_html, height=180)

    section("Compteur compétition", icon="🏆")
    caps = load_captures_for_session(sid)
    nb_prises = len(caps)
    poids_total = float(caps["poids_g"].fillna(0).sum()) \
                  if not caps.empty and "poids_g" in caps.columns else 0.0

    metric_grid([
        {"icon": "🐟", "label": "Prises", "value": str(nb_prises), "sub": "Total"},
        {"icon": "⚖️", "label": "Poids", "value": f"{poids_total:.0f} g", "sub": "Cumul"},
        {"icon": "🎯", "label": "Objectif", "value": f"{duree_h:.1f}h",
         "sub": "Durée prévue"},
    ])

    # Détail par espèce
    if not caps.empty and "espece" in caps.columns:
        counts = caps["espece"].fillna("—").value_counts().reset_index()
        counts.columns = ["Espèce", "Nombre"]
        st.dataframe(counts, use_container_width=True, hide_index=True)

    # ── Saisie rapide de capture ─────────────────────────────────────
    section("Saisie rapide d'une capture", icon="⚡")
    with st.form(f"cap_form_{sid}", clear_on_submit=True):
        cap_num = next_capture_number(sid)
        st.info(f"Capture {cap_num}")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            espece = st.selectbox("Poisson", ESPECES, key=f"cf_esp_{sid}")
        with c2:
            taille = st.number_input("Taille (cm)", 0.0, step=1.0, key=f"cf_t_{sid}")
        with c3:
            poids = st.number_input("Poids (g)", 0.0, step=10.0, key=f"cf_p_{sid}")
        with c4:
            heure = st.time_input("Heure",
                                    value=datetime.now().time().replace(second=0, microsecond=0),
                                    key=f"cf_h_{sid}")
        relache = st.checkbox("Relâché", value=True, key=f"cf_rel_{sid}")
        photo = photo_inputs(f"cf_{sid}")
        submitted = st.form_submit_button("🎣 Enregistrer", use_container_width=True,
                                            type="primary")
    if submitted:
        poids_est = estimate_fish_weight_g(espece, taille) if poids <= 0 else None
        data = {
            "session_id":   sid,
            "capture_num":  cap_num,
            "capture_label": f"Capture {cap_num}",
            "espece":       espece,
            "taille_cm":    taille or None,
            "poids_g":      poids or None,
            "poids_estime_g": poids_est,
            "heure_capture": heure.strftime("%H:%M"),
            "relache":      int(relache),
            "created_at":   datetime.now().isoformat(timespec="seconds"),
        }
        cap_id = insert_row("captures", data)
        if photo:
            pp = save_capture_photo(photo, cap_id)
            if pp:
                update_row("captures", cap_id, {"photo_path": pp})
        st.cache_data.clear()
        st.success(f"Capture {cap_num} enregistrée.")
        st.rerun()
