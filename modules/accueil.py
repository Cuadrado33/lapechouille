"""Tableau de bord — Vue en temps réel de la session en cours et conditions."""
from __future__ import annotations
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as _comp

from core.database import (
    load_sessions, load_captures, load_captures_for_session,
    insert_row, update_row, next_capture_number,
)
from core.external_apis import fetch_weather, fetch_marine, mean_between_hours
from core.storage import save_capture_photo
from core.utils import (
    safe_str, safe_float, format_date_fr, parse_time_safe,
    estimate_fish_weight_g, wind_direction_cardinal,
)
from data.constants import ESPECES, APPATS
from data.fish_data import FISH_SVG


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fish_svg_inline(espece: str, size: int = 40) -> str:
    """Renvoie le SVG du poisson (priorité) ou emoji unicode en fallback."""
    from data.fish_data import FISH_META, FISH_EMOJI_FALLBACK
    from modules.identification import _capture_matches_fish
    svg = ""
    fish_id = None
    for f in FISH_META:
        if _capture_matches_fish(espece, f):
            fish_id = f["id"]
            svg = FISH_SVG.get(fish_id, "")
            break
    if svg:
        return (f'<div style="width:{size}px;height:{size}px;display:flex;'
                f'align-items:center;justify-content:center;overflow:hidden;">'
                f'<div style="width:{size + 10}px;">{svg}</div></div>')
    emoji = FISH_EMOJI_FALLBACK.get(fish_id or "", "🐟")
    return (f'<div style="width:{size}px;height:{size}px;background:#E3F2FD;'
            f'border-radius:6px;display:flex;align-items:center;justify-content:center;'
            f'font-size:{size // 2}px;">{emoji}</div>')


# ─────────────────────────────────────────────────────────────────────────────
# Point d'entrée
# ─────────────────────────────────────────────────────────────────────────────

def render() -> None:
    # ── Bandeau ─────────────────────────────────────────────────────
    st.markdown(
        '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        'color:#fff;padding:14px 20px;border-radius:8px;margin:8px 0 18px;">'
        '<span style="font-size:18px;font-weight:800;">📊 Tableau de bord</span>'
        '<div style="font-size:12px;opacity:.85;margin-top:3px;">'
        'Vue en temps réel de ta sortie de pêche.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    sessions = load_sessions()
    captures = load_captures()
    today_d  = date.today()
    today_s  = today_d.isoformat()

    # ── Détection session en cours ─────────────────────────────────
    session_active = None
    if not sessions.empty and "date_session" in sessions.columns:
        mask = (
            (sessions["date_session"] == today_s) &
            (sessions.get("session_terminee",
                            pd.Series(0, index=sessions.index))
                       .fillna(0).astype(int) == 0)
        )
        if mask.any():
            session_active = sessions[mask].iloc[0]

    # ── Affichage principal ─────────────────────────────────────────
    if session_active is not None:
        _render_live_dashboard(session_active)
    else:
        _render_no_session(sessions, captures)

    # ── Sessions récentes ───────────────────────────────────────────
    st.markdown("---")
    _render_recent_sessions(sessions, captures)


# ─────────────────────────────────────────────────────────────────────────────
# Vue session en cours
# ─────────────────────────────────────────────────────────────────────────────

def _render_live_dashboard(session) -> None:
    sid    = int(session["id"])
    lieu   = safe_str(session.get("lieu")) or "Spot inconnu"
    type_s = safe_str(session.get("type_session")) or "Loisir"
    debut  = safe_str(session.get("heure_debut")) or "—"
    lat    = safe_float(session.get("latitude")) or 44.656
    lon    = safe_float(session.get("longitude")) or -1.196

    # ── BANDEAU ROUGE LIVE + chrono ─────────────────────────────────
    start_t  = parse_time_safe(session.get("heure_debut"), time(8, 0))
    start_dt = datetime.combine(date.today(), start_t)
    start_iso = start_dt.isoformat()

    live_html = f"""
<div style="background:linear-gradient(135deg,#C62828,#7B1538);color:#fff;
    border-radius:14px;padding:20px 24px;margin-bottom:14px;
    box-shadow:0 4px 16px rgba(0,0,0,.18);font-family:system-ui,sans-serif;">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;">
    <div>
      <div style="font-size:11px;letter-spacing:2px;font-weight:700;opacity:.9;">
        🔴 SESSION EN COURS
      </div>
      <div style="font-size:22px;font-weight:800;margin-top:4px;">{lieu}</div>
      <div style="font-size:12px;opacity:.85;margin-top:2px;">
        {type_s} · démarrée à {debut}
      </div>
    </div>
    <div style="text-align:right;">
      <div style="font-size:10px;letter-spacing:1px;font-weight:600;opacity:.85;">
        TEMPS DE PÊCHE
      </div>
      <div id="dash-chrono" style="font-size:38px;font-weight:900;
              font-variant-numeric:tabular-nums;line-height:1;margin-top:2px;">
        --:--:--
      </div>
    </div>
  </div>
</div>
<script>
(function() {{
  const start = new Date("{start_iso}").getTime();
  const el = document.getElementById("dash-chrono");
  if (!el) return;
  function pad(n) {{ return String(n).padStart(2, '0'); }}
  function tick() {{
    const ms = Date.now() - start;
    if (ms < 0) {{ el.innerText = "00:00:00"; return; }}
    const s = Math.floor(ms / 1000);
    el.innerText = pad(Math.floor(s / 3600)) + ":"
                   + pad(Math.floor((s % 3600) / 60)) + ":"
                   + pad(s % 60);
  }}
  tick();
  setInterval(tick, 1000);
}})();
</script>
"""
    _comp.html(live_html, height=130)

    # ── Boutons d'action principaux ─────────────────────────────────
    bcol1, bcol2, bcol3 = st.columns(3)
    if bcol1.button("🎣 Ajouter une capture", key="dash_btn_cap",
                      use_container_width=True, type="primary"):
        st.session_state[f"dash_add_cap_{sid}"] = True
        st.rerun()
    if bcol2.button("📋 Voir le détail", key="dash_btn_detail",
                      use_container_width=True):
        st.session_state["ss_detail_id"] = sid
        st.session_state["nav_page"]  = "sessions"
        st.rerun()
    if bcol3.button("🛑 Terminer la session", key="dash_btn_end",
                      use_container_width=True):
        now_t = datetime.now().time().replace(second=0, microsecond=0)
        update_row("sessions", sid, {
            "session_terminee": 1,
            "heure_fin":        now_t.strftime("%H:%M"),
        })
        st.cache_data.clear()
        st.success("Session terminée.")
        st.rerun()

    # ── Capture rapide inline (si déclenchée) ──────────────────────
    if st.session_state.get(f"dash_add_cap_{sid}"):
        _render_quick_capture(sid)

    # ── Stats live de la session ────────────────────────────────────
    caps = load_captures_for_session(sid)
    nb_caps  = len(caps)
    best_t   = "—"
    poids_tot = 0.0
    if not caps.empty:
        if "taille_cm" in caps.columns:
            tt = caps["taille_cm"].dropna()
            if len(tt):
                best_t = f"{tt.max():.0f} cm"
        if "poids_g" in caps.columns:
            poids_tot = float(caps["poids_g"].fillna(0).sum())

    st.markdown(
        '<div style="font-size:11px;font-weight:700;color:#546E7A;'
        'letter-spacing:1.2px;text-transform:uppercase;margin:14px 0 6px;">'
        '📊 MA SESSION EN DIRECT</div>',
        unsafe_allow_html=True,
    )
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Captures",    str(nb_caps))
    m2.metric("Record",      best_t)
    m3.metric("Poids cumul", f"{poids_tot:.0f} g" if poids_tot > 0 else "—")
    m4.metric("Heure début", debut)

    # ── Conditions live ─────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:11px;font-weight:700;color:#546E7A;'
        'letter-spacing:1.2px;text-transform:uppercase;margin:18px 0 6px;">'
        '🌦️ CONDITIONS ACTUELLES SUR LE SPOT</div>',
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        col_btn, col_info = st.columns([1, 3])
        if col_btn.button("🔄 Actualiser", key="dash_refresh_meteo",
                            use_container_width=True):
            st.cache_data.clear()
            st.session_state.pop("dash_weather", None)
            st.rerun()
        col_info.caption(f"📍 {lieu} · {lat:.4f}, {lon:.4f}")

        weather = st.session_state.get("dash_weather")
        if not weather:
            with st.spinner("Récupération des conditions…"):
                now_dt = datetime.now()
                target = now_dt.date().isoformat()
                w_df = fetch_weather(lat, lon, target)
                m_df = fetch_marine(lat, lon, target)
                # Moyenne sur 1h glissante (maintenant -30min / +30min)
                sh = (now_dt - timedelta(minutes=30)).strftime("%H:%M")
                eh = (now_dt + timedelta(minutes=30)).strftime("%H:%M")
                weather = {**mean_between_hours(w_df, sh, eh),
                            **mean_between_hours(m_df, sh, eh)}
                st.session_state["dash_weather"] = weather

        if weather:
            mc1, mc2, mc3, mc4 = st.columns(4)
            t_air = weather.get("temperature_2m")
            t_eau = weather.get("sea_surface_temperature")
            wind  = weather.get("wind_speed_10m")
            gusts = weather.get("wind_gusts_10m")
            wd    = weather.get("wind_direction_10m")
            wave  = weather.get("wave_height")
            mc1.metric("🌡️ Air",  f"{t_air:.0f} °C" if t_air else "—")
            mc2.metric("🌊 Eau",  f"{t_eau:.0f} °C" if t_eau else "—")
            mc3.metric("💨 Vent",
                        f"{wind:.0f} km/h" if wind else "—",
                        delta=wind_direction_cardinal(wd) if wd else None)
            mc4.metric("🌊 Vagues",
                        f"{wave:.1f} m" if wave else "—",
                        delta=f"Raf. {gusts:.0f} km/h" if gusts else None)
        else:
            st.info("Conditions indisponibles — vérifie ta connexion.")

    # ── Liste des captures de la session ───────────────────────────
    if nb_caps > 0:
        st.markdown(
            '<div style="font-size:11px;font-weight:700;color:#546E7A;'
            'letter-spacing:1.2px;text-transform:uppercase;margin:18px 0 6px;">'
            '🐟 CAPTURES DE LA SESSION</div>',
            unsafe_allow_html=True,
        )
        for i, (_, cap) in enumerate(caps.iterrows()):
            esp     = safe_str(cap.get("espece")) or "—"
            t       = safe_float(cap.get("taille_cm"))
            heure_c = safe_str(cap.get("heure_capture")) or "—"
            relache = bool(cap.get("relache"))
            photo   = safe_str(cap.get("photo_path"))

            with st.container(border=True):
                col_img, col_main, col_t = st.columns([0.6, 3, 1])
                with col_img:
                    if photo and Path(photo).exists():
                        st.image(photo, width=50)
                    else:
                        _comp.html(_fish_svg_inline(esp, 50), height=54)
                with col_main:
                    rel_badge = ('<span style="background:#E8F5E9;color:#2E7D32;'
                                 'font-size:9px;font-weight:700;padding:2px 7px;'
                                 'border-radius:8px;">↩️ Relâché</span>') if relache else \
                                ('<span style="background:#E3F2FD;color:#1565C0;'
                                 'font-size:9px;font-weight:700;padding:2px 7px;'
                                 'border-radius:8px;">📦 Gardé</span>')
                    st.markdown(
                        f'<strong>{esp}</strong> &nbsp;{rel_badge}'
                        f'<br><span style="color:#546E7A;font-size:11px;">🕐 {heure_c}</span>',
                        unsafe_allow_html=True,
                    )
                with col_t:
                    st.markdown(
                        f'<div style="text-align:right;font-size:18px;'
                        f'font-weight:700;">{f"{t:.0f} cm" if t else "—"}</div>',
                        unsafe_allow_html=True,
                    )


# ─────────────────────────────────────────────────────────────────────────────
# Capture rapide inline
# ─────────────────────────────────────────────────────────────────────────────

def _render_quick_capture(sid: int) -> None:
    with st.container(border=True):
        col_t, col_x = st.columns([5, 1])
        col_t.markdown("**⚡ Capture rapide**")
        if col_x.button("✕", key="dash_close_cap", use_container_width=True):
            st.session_state[f"dash_add_cap_{sid}"] = False
            st.rerun()

        # Photo hors form
        col_cam, col_up = st.columns(2)
        cam = col_cam.camera_input("📷 Photo", key=f"dash_cam_{sid}",
                                     label_visibility="collapsed")
        upl = col_up.file_uploader("Importer", type=["jpg", "jpeg", "png"],
                                     key=f"dash_upl_{sid}",
                                     label_visibility="collapsed")
        new_photo = upl if upl is not None else cam

        with st.form(f"dash_cap_form_{sid}", clear_on_submit=True):
            r1c1, r1c2, r1c3 = st.columns(3)
            espece = r1c1.selectbox("Espèce", ESPECES, key=f"dc_esp_{sid}")
            taille = r1c2.number_input("Taille (cm)", 0.0, step=1.0,
                                         key=f"dc_t_{sid}")
            appat  = r1c3.selectbox("Appât", APPATS, key=f"dc_a_{sid}")
            r2c1, r2c2, r2c3 = st.columns(3)
            heure  = r2c1.time_input("Heure",
                                       value=datetime.now().time().replace(second=0, microsecond=0),
                                       key=f"dc_h_{sid}")
            relach = r2c2.checkbox("↩️ Relâché", value=True, key=f"dc_r_{sid}")
            troph  = r2c3.checkbox("🏅 Trophée", value=False, key=f"dc_tr_{sid}")

            if st.form_submit_button("🎣 Enregistrer la capture",
                                      use_container_width=True, type="primary"):
                cap_num = next_capture_number(sid)
                poids_est = estimate_fish_weight_g(espece, taille) if taille else None
                data = {
                    "session_id":     sid,
                    "capture_num":    cap_num,
                    "capture_label":  f"Capture {cap_num}",
                    "espece":         espece,
                    "taille_cm":      taille or None,
                    "poids_estime_g": poids_est,
                    "heure_capture":  heure.strftime("%H:%M"),
                    "appat":          appat if appat != "Non renseigné" else None,
                    "relache":        int(relach),
                    "poisson_trophee": int(troph),
                    "created_at":     datetime.now().isoformat(timespec="seconds"),
                }
                cap_id = insert_row("captures", data)
                if new_photo:
                    pp = save_capture_photo(new_photo, cap_id)
                    if pp:
                        update_row("captures", cap_id, {"photo_path": pp})
                st.cache_data.clear()
                st.session_state[f"dash_add_cap_{sid}"] = False
                st.success(f"✅ {espece} {taille:.0f} cm enregistré !")
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Vue sans session active
# ─────────────────────────────────────────────────────────────────────────────

def _render_no_session(sessions, captures) -> None:
    st.markdown(
        '<div style="background:#E8F5E9;border-left:4px solid #2E7D32;'
        'padding:12px 16px;border-radius:0 8px 8px 0;margin-bottom:14px;">'
        '<strong style="font-size:15px;">🎣 Aucune session en cours</strong>'
        '<div style="font-size:12px;color:#1b5e20;margin-top:4px;">'
        'Démarre une nouvelle session pour commencer à enregistrer tes captures.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    bcol1, bcol2 = st.columns(2)
    if bcol1.button("🚀 Démarrer maintenant", key="dash_btn_quick",
                      use_container_width=True, type="primary",
                      help="Crée immédiatement une session avec valeurs par défaut"):
        now_t = datetime.now()
        lat   = st.session_state.get("active_spot_lat", 44.656588)
        lon   = st.session_state.get("active_spot_lon", -1.196303)
        lieu  = st.session_state.get("active_spot_nom", "Session rapide")
        sid = insert_row("sessions", {
            "type_session":     "Loisir",
            "session_terminee": 0,
            "date_session":     now_t.date().isoformat(),
            "lieu":             lieu,
            "latitude":         lat,
            "longitude":        lon,
            "heure_debut":      now_t.strftime("%H:%M"),
            "heure_fin":        "",
            "created_at":       now_t.isoformat(timespec="seconds"),
        })
        st.cache_data.clear()
        st.success(f"✅ Session démarrée à {now_t.strftime('%H:%M')} !")
        st.rerun()

    if bcol2.button("📝 Formulaire complet", key="dash_btn_full",
                      use_container_width=True,
                      help="Saisir tous les détails avant de démarrer"):
        st.session_state.pop("ss_detail_id", None)
        st.session_state["nav_page"] = "sessions"
        st.rerun()

    # ── Métriques globales saison ────────────────────────────────────
    st.markdown("---")
    st.markdown(
        '<div style="font-size:11px;font-weight:700;color:#546E7A;'
        'letter-spacing:1.2px;text-transform:uppercase;margin:14px 0 6px;">'
        '📈 STATISTIQUES SAISON</div>',
        unsafe_allow_html=True,
    )

    nb_sessions = len(sessions)
    nb_captures = len(captures)
    nb_especes  = captures["espece"].nunique() \
                  if not captures.empty and "espece" in captures.columns else 0
    record_txt  = "—"
    if not captures.empty and "taille_cm" in captures.columns:
        best = captures["taille_cm"].replace(0, pd.NA).dropna()
        if len(best):
            best_val = best.max()
            best_row = captures.loc[best.idxmax()]
            record_txt = f"{best_val:.0f} cm · {safe_str(best_row.get('espece', ''))}"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sessions",     nb_sessions)
    c2.metric("Captures",     nb_captures)
    c3.metric("Espèces",      nb_especes)
    c4.metric("Record taille", record_txt)


# ─────────────────────────────────────────────────────────────────────────────
# Sessions récentes
# ─────────────────────────────────────────────────────────────────────────────

def _render_recent_sessions(sessions, captures) -> None:
    st.markdown(
        '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        'color:#fff;padding:10px 16px;border-radius:8px;margin:8px 0 10px;">'
        '<span style="font-size:14px;font-weight:800;">📓 SESSIONS RÉCENTES</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    if sessions.empty:
        st.caption("Aucune session enregistrée.")
        return

    import base64
    from data.fish_data import get_fish_visual

    for i, (_, row) in enumerate(sessions.head(5).iterrows()):
        sid    = int(row["id"])
        lieu   = safe_str(row.get("lieu")) or "Sans lieu"
        d      = format_date_fr(row.get("date_session")) or "—"
        type_s = safe_str(row.get("type_session")) or "Loisir"
        debut  = safe_str(row.get("heure_debut")) or ""
        fin_h  = safe_str(row.get("heure_fin")) or ""
        coef   = safe_float(row.get("coefficient_maree")) or 0

        # Code couleur type
        if "ompétition" in type_s:
            tc, ti = "#C62828", "🏆"
        elif "ntra" in type_s:
            tc, ti = "#EF6C00", "🎯"
        else:
            tc, ti = "#1565C0", "🎣"

        # Captures de la session
        sess_caps = captures[captures["session_id"] == sid] \
                    if not captures.empty and "session_id" in captures.columns \
                    else pd.DataFrame()
        nb = len(sess_caps)

        # Espèces (max 3 micro-badges)
        especes_badges = ""
        best_t = None
        if not sess_caps.empty:
            if "espece" in sess_caps.columns:
                esp_u = sess_caps["espece"].dropna().unique().tolist()[:3]
                especes_badges = "".join(
                    f'<span style="background:{tc}18;color:{tc};font-size:9px;'
                    f'font-weight:700;padding:1px 6px;border-radius:6px;margin-right:3px;">'
                    f'{e}</span>'
                    for e in esp_u if e
                )
            if "taille_cm" in sess_caps.columns:
                tt = pd.to_numeric(sess_caps["taille_cm"], errors="coerce").dropna()
                tt = tt[tt > 0]
                if not tt.empty:
                    best_t = f"📏 {tt.max():.0f} cm"

        # Vignette photo/SVG/emoji
        thumb_html = ""
        if not sess_caps.empty:
            with_photo = sess_caps[sess_caps["photo_path"].astype(str).str.len() > 0] \
                         if "photo_path" in sess_caps.columns else pd.DataFrame()
            if not with_photo.empty:
                p = safe_str(with_photo.iloc[0].get("photo_path"))
                if p and Path(p).exists():
                    try:
                        ext = Path(p).suffix.lower().lstrip(".")
                        mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
                        b64 = base64.b64encode(Path(p).read_bytes()).decode()
                        thumb_html = (
                            f'<img src="data:{mime};base64,{b64}" '
                            f'style="width:56px;height:56px;border-radius:6px;'
                            f'object-fit:cover;border:2px solid {tc};">'
                        )
                    except Exception:
                        pass
            if not thumb_html and "espece" in sess_caps.columns:
                esp = safe_str(sess_caps.iloc[0].get("espece"))
                if esp:
                    vis = get_fish_visual(esp, size=56)
                    thumb_html = f'<div style="width:56px;height:56px;border:2px solid {tc};border-radius:6px;overflow:hidden;">{vis}</div>'

        if not thumb_html:
            thumb_html = (
                f'<div style="width:56px;height:56px;background:{tc}18;'
                f'border:2px solid {tc};border-radius:6px;display:flex;'
                f'align-items:center;justify-content:center;font-size:26px;">{ti}</div>'
            )

        # Infos horaires + coef
        detail_bits = []
        if debut:
            detail_bits.append(f"🕒 {debut}{'→'+fin_h if fin_h else ''}")
        if coef > 0:
            detail_bits.append(f"🌊 Coef {int(coef)}")
        if best_t:
            detail_bits.append(best_t)
        detail_str = " · ".join(detail_bits)

        # L'encadré entier en HTML inline pour rester compact
        card_html = f"""
<div style="display:flex;align-items:center;gap:10px;padding:4px 0;">
  <div>{thumb_html}</div>
  <div style="flex:1;min-width:0;">
    <div style="display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;">
      <span style="font-size:14px;font-weight:800;color:#0c2340;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:200px;">{lieu}</span>
      <span style="background:{tc}22;color:{tc};font-size:9px;font-weight:700;padding:1px 7px;border-radius:6px;white-space:nowrap;">{ti} {type_s}</span>
      <span style="font-size:10px;color:#546E7A;white-space:nowrap;">📅 {d}</span>
    </div>
    <div style="margin-top:3px;display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
      <span style="background:#E3F2FD;color:#1565C0;font-size:10px;font-weight:700;padding:1px 8px;border-radius:8px;">🐟 {nb} prise(s)</span>
      {especes_badges}
      {'<span style="font-size:10px;color:#546E7A;">' + detail_str + '</span>' if detail_str else ''}
    </div>
  </div>
</div>
"""
        with st.container(border=True):
            col_card, col_btn = st.columns([5, 1])
            with col_card:
                _comp.html(card_html, height=72, scrolling=False)
            with col_btn:
                if st.button("📋 Voir", key=f"dash_recent_{sid}",
                              use_container_width=True):
                    st.session_state["ss_detail_id"] = sid
                    st.session_state["nav_page"] = "sessions"
                    st.rerun()
