"""Page Analyse des conditions — graphiques séparés par thème, encadrés nets."""
from __future__ import annotations
from datetime import date, datetime, timedelta
import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.external_apis import (
    reverse_geocode, fetch_weather_range, fetch_marine_range,
    calculate_moon_phase, fetch_sun_events, estimate_tide,
    closest_to_now, generate_tide_curve,
)
from core.utils import safe_str, wind_direction_cardinal
from data.regulations import estimate_region, get_minimum_sizes_table, get_regulation_sources
from ui.components import (
    hero, section, location_picker,
    terrestrial_map, maritime_map, scroll_to_anchor,
    share_location_widget,
)
from ui.navigation import get_active_anchor

# Palette commune
C_BLUE   = "#1565C0"
C_CYAN   = "#00897B"
C_ORANGE = "#E65100"
C_RED    = "#C62828"
C_YELLOW = "#F9A825"
C_PURPLE = "#6A1B9A"
C_GREY   = "#546E7A"

CHART_H = 300


def _ts(dt: datetime) -> int:
    """Convertit un datetime en timestamp millisecondes pour Plotly."""
    return int(dt.timestamp() * 1000)


def _now_vline(fig: go.Figure, label: str = "Maintenant") -> None:
    """Ligne verticale 'Maintenant' — uniquement si la figure a au moins une trace."""
    if not fig.data:
        return
    fig.add_vline(
        x=_ts(datetime.now()),
        line=dict(color=C_RED, width=1.8, dash="dot"),
        annotation_text=label,
        annotation_position="top right",
        annotation_font=dict(color=C_RED, size=10),
    )


def _base_layout(fig: go.Figure, h: int = CHART_H) -> None:
    fig.update_layout(
        height=h,
        margin=dict(l=10, r=10, t=16, b=10),
        plot_bgcolor="#fafbfc",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.3, font_size=11),
        xaxis=dict(
            type="date",
            tickformat="%H:%M",
            gridcolor="#eeeeee",
            showgrid=True,
        ),
        yaxis=dict(gridcolor="#eeeeee", showgrid=True),
    )


# ─────────────────────────────────────────────────────────────────────────────
# MARÉE
# ─────────────────────────────────────────────────────────────────────────────

def _render_maree(latitude: float, longitude: float, analysis_date: date | None = None) -> None:
    if analysis_date is None:
        analysis_date = date.today()
    section("Marée", icon="🌊", anchor_id="maree")
    with st.container(border=True):
        # ── 1. Tentative depuis la base de marées Supabase ────────
        try:
            from core.tides_db import get_tides_for_spot, format_time_fr

            tide_data = get_tides_for_spot(latitude, longitude, analysis_date.isoformat())

            if tide_data and tide_data.get("events"):
                port = tide_data["port"]
                today_pm = tide_data["today_pm"]
                today_bm = tide_data["today_bm"]
                coef_max = tide_data["coef_max"]

                # En-tête : port de référence
                st.markdown(
                    f'<div style="background:linear-gradient(135deg,#0c2340,#1565C0);'
                    f'color:#fff;padding:10px 14px;border-radius:8px;margin-bottom:10px;'
                    f'display:flex;justify-content:space-between;align-items:center;">'
                    f'<span style="font-size:13px;font-weight:800;">'
                    f'📍 Port de référence : {port["nom"]}</span>'
                    f'<span style="font-size:11px;opacity:.85;">'
                    f'à {port["distance_km"]} km · marnage {port["marnage_ref_m"]:.1f} m</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                # Métriques principales
                col1, col2, col3 = st.columns(3)
                col1.metric("Coefficient (max jour)", coef_max if coef_max else "—",
                              help="20-45 : mortes-eaux · 70-95 : vives-eaux · >100 : grandes marées")
                col2.metric("Pleines mers",
                              " · ".join(format_time_fr(p["datetime_utc"]) for p in today_pm) or "—")
                col3.metric("Basses mers",
                              " · ".join(format_time_fr(b["datetime_utc"]) for b in today_bm) or "—")

                # Tableau détaillé du jour
                st.markdown("**🌊 Détail du jour**")
                rows_html = ""
                all_today = sorted(today_pm + today_bm, key=lambda x: x["datetime_utc"])
                for e in all_today:
                    is_pm = e["type"] == "PM"
                    icon  = "⬆️" if is_pm else "⬇️"
                    color = "#1565C0" if is_pm else "#E65100"
                    bg    = "#E3F2FD" if is_pm else "#FFF3E0"
                    label = "Pleine mer" if is_pm else "Basse mer"
                    coef_txt = f"<br><span style=\"font-size:10px;color:#90A4AE;\">Coef {e['coefficient']}</span>" if e.get("coefficient") else ""
                    rows_html += (
                        f'<div style="display:flex;justify-content:space-between;align-items:center;'
                        f'padding:8px 12px;background:{bg};border-radius:6px;margin-bottom:4px;">'
                        f'<span style="font-weight:700;color:{color};">{icon} {label}</span>'
                        f'<div style="text-align:right;">'
                        f'<span style="font-size:14px;font-weight:800;color:{color};">'
                        f'{format_time_fr(e["datetime_utc"])}</span><br>'
                        f'<span style="font-size:11px;color:#546E7A;">{e["hauteur_m"]:.2f} m{coef_txt}</span>'
                        f'</div></div>'
                    )
                st.markdown(rows_html, unsafe_allow_html=True)

                # Courbe de marée — interpolation cosinusoïdale entre PM/BM
                events_dt = []
                for e in tide_data["events"]:
                    try:
                        dt_local = datetime.fromisoformat(e["datetime_utc"].replace("Z","+00:00"))
                        m = dt_local.month
                        offset_h = 2 if 4 <= m <= 10 else 1
                        dt_local += timedelta(hours=offset_h)
                        dt_local = dt_local.replace(tzinfo=None)
                        events_dt.append((dt_local, e["hauteur_m"], e["type"]))
                    except Exception:
                        pass

                if len(events_dt) >= 2:
                    # Génère une courbe cosinusoïdale entre chaque paire PM/BM
                    times   = []
                    heights = []
                    for i in range(len(events_dt) - 1):
                        t0, h0, _ = events_dt[i]
                        t1, h1, _ = events_dt[i+1]
                        # 60 points entre 2 extrema
                        steps = 60
                        for s in range(steps):
                            frac = s / steps
                            # Cosinus pour transition douce PM ↔ BM
                            phase = (1 - math.cos(math.pi * frac)) / 2
                            h     = h0 + (h1 - h0) * phase
                            t     = t0 + (t1 - t0) * frac
                            times.append(t)
                            heights.append(h)
                    times.append(events_dt[-1][0])
                    heights.append(events_dt[-1][1])

                    # Niveau moyen pour zone sable/eau
                    h_min = min(heights)
                    h_max = max(heights)
                    h_mid = (h_min + h_max) / 2

                    fig = go.Figure()
                    # Zone haute (au dessus du niveau moyen)
                    fig.add_trace(go.Scatter(
                        x=times, y=heights,
                        fill="tozeroy", mode="lines", name="Hauteur",
                        fillcolor="rgba(21,101,192,0.15)",
                        line=dict(color="#1565C0", width=2.5),
                        hovertemplate="%{x|%a %d/%m %H:%M}<br><b>%{y:.2f} m</b><extra></extra>",
                    ))
                    # Points PM/BM
                    pm_x = [e[0] for e in events_dt if e[2] == "PM"]
                    pm_y = [e[1] for e in events_dt if e[2] == "PM"]
                    bm_x = [e[0] for e in events_dt if e[2] == "BM"]
                    bm_y = [e[1] for e in events_dt if e[2] == "BM"]
                    fig.add_trace(go.Scatter(
                        x=pm_x, y=pm_y, mode="markers+text",
                        marker=dict(color="#1565C0", size=10),
                        text=["PM"] * len(pm_x), textposition="top center",
                        textfont=dict(size=10, color="#1565C0"),
                        hovertemplate="<b>PM</b> %{x|%H:%M}<br>%{y:.2f} m<extra></extra>",
                        showlegend=False,
                    ))
                    fig.add_trace(go.Scatter(
                        x=bm_x, y=bm_y, mode="markers+text",
                        marker=dict(color="#E65100", size=10),
                        text=["BM"] * len(bm_x), textposition="bottom center",
                        textfont=dict(size=10, color="#E65100"),
                        hovertemplate="<b>BM</b> %{x|%H:%M}<br>%{y:.2f} m<extra></extra>",
                        showlegend=False,
                    ))

                    _now_vline(fig)
                    fig.add_hline(y=h_mid, line=dict(color="#bbb", width=1, dash="dot"),
                                   annotation_text="Niveau moyen", annotation_position="right",
                                   annotation_font=dict(size=9, color="#888"))
                    fig.update_layout(
                        height=CHART_H,
                        margin=dict(l=10, r=10, t=16, b=10),
                        plot_bgcolor="#f0f4f8",
                        paper_bgcolor="rgba(0,0,0,0)",
                        showlegend=False,
                        xaxis=dict(type="date", tickformat="%a %H:%M", nticks=10,
                                   gridcolor="#dde"),
                        yaxis=dict(title="Hauteur (m)", gridcolor="#dde", zeroline=False),
                    )
                    st.plotly_chart(fig, use_container_width=True)

                # Conseil pêche selon coef
                if coef_max:
                    if coef_max >= 95:
                        conseil = "🌊 **Vives-eaux** — Bon moment pour le surfcasting, courants forts, bonne activité halieutique."
                    elif coef_max >= 70:
                        conseil = "🌊 **Marées moyennes** — Conditions correctes, activité variable selon les spots."
                    elif coef_max >= 45:
                        conseil = "💤 **Marées faibles** — Activité réduite, privilégier les heures de mouvement (1-2h avant/après PM)."
                    else:
                        conseil = "💤 **Mortes-eaux** — Faible activité, mais peut être bon pour certaines espèces sédentaires."
                    st.info(conseil)

                # ── Graphique des coefficients sur 15 jours (par jour) ────────────
                from core.supabase_client import supabase_get
                d0 = (analysis_date - timedelta(days=7)).isoformat() + "T00:00:00Z"
                d1 = (analysis_date + timedelta(days=8)).isoformat() + "T00:00:00Z"
                month_events = supabase_get("tide_events", {
                    "port_id":      f"eq.{port['id']}",
                    "type":         "eq.PM",
                    "datetime_utc": f"gte.{d0}",
                    "order":        "datetime_utc.asc",
                    "limit":        "60",
                }) or []
                month_events = [e for e in month_events if e["datetime_utc"] < d1 and e.get("coefficient")]

                if len(month_events) >= 2:
                    # Agréger par jour : on garde le COEF MAX de la journée
                    daily_coef = {}  # date -> coef max
                    for e in month_events:
                        try:
                            dt_local = datetime.fromisoformat(e["datetime_utc"].replace("Z","+00:00"))
                            m = dt_local.month
                            offset_h = 2 if 4 <= m <= 10 else 1
                            dt_local += timedelta(hours=offset_h)
                            day_key = dt_local.date()
                            c = int(e["coefficient"])
                            if day_key not in daily_coef or c > daily_coef[day_key]:
                                daily_coef[day_key] = c
                        except Exception:
                            pass

                    if daily_coef:
                        st.markdown(f"**📊 Coefficients par jour — 15 jours autour du {analysis_date.strftime('%d/%m')}**")

                        sorted_days = sorted(daily_coef.keys())
                        dates_x = [datetime.combine(d, datetime.min.time()) for d in sorted_days]
                        coefs   = [daily_coef[d] for d in sorted_days]
                        labels  = [d.strftime("%a %d/%m") for d in sorted_days]

                        # Couleur selon le coef
                        bar_colors = []
                        for c in coefs:
                            if c >= 95:   bar_colors.append("#C62828")   # vives-eaux fortes
                            elif c >= 70: bar_colors.append("#1565C0")   # moyennes
                            elif c >= 45: bar_colors.append("#FB8C00")   # faibles
                            else:         bar_colors.append("#90A4AE")   # mortes-eaux

                        # Coef du jour analysé pour mise en évidence
                        analysis_coef = daily_coef.get(analysis_date, None)

                        fig_coef = go.Figure()
                        fig_coef.add_trace(go.Bar(
                            x=labels, y=coefs,
                            marker=dict(
                                color=bar_colors,
                                line=dict(
                                    color=["#0c2340" if d == analysis_date else "rgba(0,0,0,0)" for d in sorted_days],
                                    width=[3 if d == analysis_date else 0 for d in sorted_days],
                                ),
                            ),
                            text=[str(c) for c in coefs],
                            textposition="outside",
                            textfont=dict(size=11, color="#0c2340", family="system-ui"),
                            hovertemplate="<b>%{x}</b><br>Coefficient <b>%{y}</b><extra></extra>",
                            showlegend=False,
                        ))
                        # Lignes de référence
                        fig_coef.add_hline(y=95, line=dict(color="#C62828", width=1, dash="dot"),
                                            annotation_text="Vives-eaux fortes (≥95)", annotation_position="right",
                                            annotation_font=dict(size=9, color="#C62828"))
                        fig_coef.add_hline(y=70, line=dict(color="#1565C0", width=1, dash="dot"),
                                            annotation_text="Moyennes (≥70)", annotation_position="right",
                                            annotation_font=dict(size=9, color="#1565C0"))
                        fig_coef.add_hline(y=45, line=dict(color="#FB8C00", width=1, dash="dot"),
                                            annotation_text="Mortes-eaux (<45)", annotation_position="right",
                                            annotation_font=dict(size=9, color="#FB8C00"))

                        fig_coef.update_layout(
                            height=300,
                            margin=dict(l=10, r=140, t=40, b=50),
                            plot_bgcolor="#f0f4f8",
                            paper_bgcolor="rgba(0,0,0,0)",
                            xaxis=dict(tickangle=-45, gridcolor="#dde"),
                            yaxis=dict(title="Coefficient", range=[0, 130], gridcolor="#dde"),
                            bargap=0.2,
                        )
                        st.plotly_chart(fig_coef, use_container_width=True)

                        # Légende couleurs
                        st.markdown(
                            '<div style="display:flex;gap:14px;font-size:11px;justify-content:center;margin-top:-12px;">'
                            '<span><span style="color:#C62828;font-size:18px;">■</span> Vives-eaux ≥95</span>'
                            '<span><span style="color:#1565C0;font-size:18px;">■</span> Moyennes 70-94</span>'
                            '<span><span style="color:#FB8C00;font-size:18px;">■</span> Faibles 45-69</span>'
                            '<span><span style="color:#90A4AE;font-size:18px;">■</span> Mortes-eaux &lt;45</span>'
                            '</div>',
                            unsafe_allow_html=True,
                        )

                        if analysis_coef:
                            st.caption(f"📍 Coefficient max du {analysis_date.strftime('%d/%m')} : **{analysis_coef}** (barre encadrée en bleu marine)")

                st.caption(f"📊 Données calculées par algorithme harmonique (4 constantes : M2, S2, N2, K1) "
                            f"depuis le port de {port['nom']}. Précision ±15 min.")
                # Sortir du try
                return_after_tide = True
            else:
                raise ValueError("Pas de données dans la base")

        # ── 2. Fallback ancien système si la base n'a pas de données ──
        except Exception:
            try:
                tide_df, tide = generate_tide_curve(analysis_date, latitude, longitude, hours=48)

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Coefficient",    tide["coefficient"])
                c2.metric("Phase actuelle", tide["phase"])
                c3.metric("Prochaine PM",   tide["pleine_mer"].strftime("%H:%M"))
                c4.metric("Prochaine BM",   tide["basse_mer"].strftime("%H:%M"))

                times   = tide_df["Heure"].tolist()
                heights = tide_df["hauteur_m"].tolist()

                fig = go.Figure()
                fig.add_trace(go.Scatter(x=times, y=[max(h, 0) for h in heights],
                    fill="tozeroy", mode="none", fillcolor="rgba(21,101,192,0.18)", showlegend=False))
                fig.add_trace(go.Scatter(x=times, y=[min(h, 0) for h in heights],
                    fill="tozeroy", mode="none", fillcolor="rgba(210,180,120,0.22)", showlegend=False))
                fig.add_trace(go.Scatter(x=times, y=heights, mode="lines",
                    line=dict(color=C_BLUE, width=2.5),
                    hovertemplate="%{x|%d/%m %H:%M} — <b>%{y:.2f} m</b><extra></extra>"))

                _now_vline(fig)
                fig.add_hline(y=0, line=dict(color="#aaaaaa", width=1))
                fig.update_layout(height=CHART_H, margin=dict(l=10, r=10, t=16, b=10),
                    plot_bgcolor="#f0f4f8", paper_bgcolor="rgba(0,0,0,0)", showlegend=False,
                    xaxis=dict(type="date", tickformat="%a %H:%M", nticks=14, gridcolor="#dde"),
                    yaxis=dict(title="Hauteur (m)", gridcolor="#dde", zeroline=False))
                st.plotly_chart(fig, use_container_width=True)
                st.caption("⚠️ Estimation lunaire — la base de marées officielle n'est pas encore chargée.")
            except Exception:
                tide = estimate_tide(analysis_date,
                                      datetime.now().time().replace(second=0, microsecond=0),
                                      latitude, longitude)
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Coefficient", tide["coefficient"])
                c2.metric("Phase",       tide["phase"])
                c3.metric("Pleine mer",  tide["pleine_mer"].strftime("%H:%M"))
                c4.metric("Basse mer",   tide["basse_mer"].strftime("%H:%M"))
                st.caption("⚠️ Estimation indicative non officielle.")


# ─────────────────────────────────────────────────────────────────────────────
# VENT
# ─────────────────────────────────────────────────────────────────────────────

def _render_vent(w: pd.DataFrame, current: dict) -> None:
    section("Vent & rafales", icon="💨", anchor_id="meteo")
    with st.container(border=True):
        dir_val = current.get("wind_direction_10m")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Vent actuel", f"{current.get('wind_speed_10m', '—')} km/h")
        c2.metric("Rafales",     f"{current.get('wind_gusts_10m', '—')} km/h")
        c3.metric("Direction",   wind_direction_cardinal(dir_val) if dir_val else "—")
        c4.metric("Temp. air",   f"{current.get('temperature_2m', '—')} °C")

        fig = go.Figure()
        if "wind_speed_10m" in w.columns:
            fig.add_trace(go.Scatter(
                x=w["Heure"], y=w["wind_speed_10m"],
                mode="lines", name="Vent moy. (km/h)",
                line=dict(color=C_BLUE, width=2.5),
                fill="tozeroy", fillcolor="rgba(21,101,192,0.10)",
                hovertemplate="%{x|%H:%M} — <b>%{y} km/h</b><extra></extra>",
            ))
        if "wind_gusts_10m" in w.columns:
            fig.add_trace(go.Scatter(
                x=w["Heure"], y=w["wind_gusts_10m"],
                mode="lines", name="Rafales (km/h)",
                line=dict(color=C_RED, width=1.5, dash="dot"),
                hovertemplate="%{x|%H:%M} — rafales <b>%{y} km/h</b><extra></extra>",
            ))

        for seuil, lbl, col in [(20, "Brise légère", "#43A047"),
                                  (40, "Vent fort",   "#FB8C00"),
                                  (60, "Tempête",     "#E53935")]:
            fig.add_hline(y=seuil,
                          line=dict(color=col, width=1, dash="dash"),
                          annotation_text=lbl,
                          annotation_position="right",
                          annotation_font=dict(color=col, size=9))

        _now_vline(fig)
        _base_layout(fig)
        fig.update_yaxes(title="km/h")
        st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# PLUIE & NUAGES  (2 graphiques séparés — évite les conflits d'axes)
# ─────────────────────────────────────────────────────────────────────────────

def _render_pluie_nuages(w_default: pd.DataFrame, current: dict,
                          latitude: float, longitude: float,
                          marine_df_default=None) -> None:
    section("Météo générale", icon="🌦️", anchor_id="meteo_gen")
    with st.container(border=True):
        # ── Sélecteur de durée (1 à 5 jours) ──────────────────────────
        col_sel, col_info = st.columns([2, 3])
        nb_jours = col_sel.slider(
            "Plage de prévision",
            min_value=1, max_value=5, value=2, step=1,
            help="Nombre de jours à afficher (heure par heure)",
            key="meteo_gen_days",
        )
        col_info.caption(f"📅 Affichage horaire sur **{nb_jours} jour(s)** "
                          f"(soit {nb_jours * 24} h)")

        # ── Récupération des données selon nb_jours ──────────────────
        today    = date.today()
        end_date = (today + timedelta(days=nb_jours - 1)).isoformat()
        if nb_jours == 2:
            w = w_default
            marine_df = marine_df_default
        else:
            w_raw     = fetch_weather_range(latitude, longitude,
                                              today.isoformat(), end_date)
            marine_df = fetch_marine_range(latitude, longitude,
                                              today.isoformat(), end_date)
            if w_raw is None or w_raw.empty:
                st.warning("Données indisponibles pour cette plage.")
                return
            w = w_raw.copy()
            w["Heure"] = pd.to_datetime(w["time"])
            if marine_df is not None and not marine_df.empty \
                and "sea_surface_temperature" in marine_df.columns:
                m_merge = marine_df[["time", "sea_surface_temperature"]].copy()
                m_merge["time"] = pd.to_datetime(m_merge["time"])
                w_time = w[["time"]].copy()
                w_time["time"] = pd.to_datetime(w_time["time"])
                w["sea_surface_temperature"] = w_time["time"].map(
                    m_merge.set_index("time")["sea_surface_temperature"]
                )

        # Métriques actuelles : 5 valeurs en ligne
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Temp. air",   f"{current.get('temperature_2m', '—')} °C")
        c2.metric("Temp. eau",   f"{current.get('sea_surface_temperature', '—')} °C")
        c3.metric("Prob. pluie", f"{current.get('precipitation_probability', '—')} %")
        c4.metric("Nuages",      f"{current.get('cloud_cover', '—')} %")
        c5.metric("Humidité",    f"{current.get('relative_humidity_2m', '—')} %")

        # ── 0. Frise météo heure par heure ────────────────────────────
        if "weather_code" in w.columns:
            st.markdown(f"**🌤️ Conditions heure par heure ({nb_jours} jour(s))**")
            _render_weather_frise(w, hours=nb_jours * 24)

        # ── 1. Températures ───────────────────────────────────────────
        temp_cols = [c for c in ("temperature_2m",
                                  "apparent_temperature",
                                  "sea_surface_temperature")
                     if c in w.columns]
        if temp_cols:
            st.markdown(f"**🌡️ Températures heure par heure ({nb_jours} jour(s))**")
            figt = go.Figure()
            color_map = {
                "temperature_2m":          ("#E65100", "Temp. air"),
                "apparent_temperature":    ("#FFB300", "Ressentie"),
                "sea_surface_temperature": ("#1565C0", "Temp. eau"),
            }
            for col in temp_cols:
                col_color, col_label = color_map.get(col, ("#888", col))
                figt.add_trace(go.Scatter(
                    x=w["Heure"], y=w[col],
                    mode="lines", name=col_label,
                    line=dict(color=col_color, width=2.2),
                    hovertemplate="%{x|%a %d %H:%M} — <b>%{y:.1f} °C</b><extra>"
                                  + col_label + "</extra>",
                ))
            _now_vline(figt)
            _base_layout(figt, h=240)
            figt.update_yaxes(title="°C", gridcolor="#eee")
            st.plotly_chart(figt, use_container_width=True)

        # ── 2. Vent & rafales ─────────────────────────────────────────
        if "wind_speed_10m" in w.columns:
            st.markdown(f"**💨 Vent & rafales ({nb_jours} jour(s))**")
            dir_val = current.get("wind_direction_10m")
            col_v1, col_v2, col_v3 = st.columns(3)
            col_v1.metric("Vent actuel", f"{current.get('wind_speed_10m', '—')} km/h")
            col_v2.metric("Rafales",     f"{current.get('wind_gusts_10m', '—')} km/h")
            col_v3.metric("Direction",   wind_direction_cardinal(dir_val) if dir_val else "—")

            figv = go.Figure()
            figv.add_trace(go.Scatter(
                x=w["Heure"], y=w["wind_speed_10m"],
                mode="lines", name="Vent moy. (km/h)",
                line=dict(color=C_BLUE, width=2.5),
                fill="tozeroy", fillcolor="rgba(21,101,192,0.10)",
                hovertemplate="%{x|%a %d %H:%M} — <b>%{y} km/h</b><extra></extra>",
            ))
            if "wind_gusts_10m" in w.columns:
                figv.add_trace(go.Scatter(
                    x=w["Heure"], y=w["wind_gusts_10m"],
                    mode="lines", name="Rafales (km/h)",
                    line=dict(color=C_RED, width=1.5, dash="dot"),
                    hovertemplate="%{x|%a %d %H:%M} — rafales <b>%{y} km/h</b><extra></extra>",
                ))
            for seuil, lbl, col in [(20, "Brise légère", "#43A047"),
                                      (40, "Vent fort",   "#FB8C00"),
                                      (60, "Tempête",     "#E53935")]:
                figv.add_hline(y=seuil,
                              line=dict(color=col, width=1, dash="dash"),
                              annotation_text=lbl, annotation_position="right",
                              annotation_font=dict(color=col, size=9))
            _now_vline(figv)
            _base_layout(figv, h=220)
            figv.update_yaxes(title="km/h")
            st.plotly_chart(figv, use_container_width=True)

        # ── 3. Couverture nuageuse ────────────────────────────────────
        if "cloud_cover" in w.columns:
            st.markdown(f"**☁️ Couverture nuageuse ({nb_jours} jour(s))**")
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=w["Heure"], y=w["cloud_cover"],
                mode="lines", name="Nuages (%)",
                line=dict(color=C_GREY, width=2),
                fill="tozeroy", fillcolor="rgba(84,110,122,0.18)",
                hovertemplate="%{x|%a %d %H:%M} — <b>%{y} %</b><extra></extra>",
            ))
            _now_vline(fig2)
            _base_layout(fig2, h=200)
            fig2.update_yaxes(title="Nuages (%)", range=[0, 105])
            st.plotly_chart(fig2, use_container_width=True)

        # ── 4. Probabilité de pluie (axe Y plafonné à 50 mm) ──────────
        if "precipitation_probability" in w.columns:
            st.markdown(f"**🌧️ Probabilité de pluie ({nb_jours} jour(s))**")
            fig1 = go.Figure()
            fig1.add_trace(go.Bar(
                x=w["Heure"], y=w["precipitation_probability"],
                name="Prob. pluie (%)",
                marker_color="rgba(30,136,229,0.65)",
                hovertemplate="%{x|%a %d %H:%M} — <b>%{y} %</b><extra></extra>",
            ))
            if "precipitation" in w.columns:
                fig1.add_trace(go.Bar(
                    x=w["Heure"], y=w["precipitation"],
                    name="Précip. (mm)",
                    marker_color="rgba(0,70,160,0.85)",
                    hovertemplate="%{x|%a %d %H:%M} — <b>%{y} mm</b><extra></extra>",
                ))
            _now_vline(fig1)
            _base_layout(fig1, h=220)
            fig1.update_layout(barmode="overlay",
                               yaxis=dict(title="% / mm", gridcolor="#eee",
                                          range=[0, 50]))
            st.plotly_chart(fig1, use_container_width=True)

        # ── 5. Humidité ───────────────────────────────────────────────
        if "relative_humidity_2m" in w.columns:
            st.markdown(f"**💧 Humidité relative ({nb_jours} jour(s))**")
            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(
                x=w["Heure"], y=w["relative_humidity_2m"],
                mode="lines", name="Humidité (%)",
                line=dict(color="#0097A7", width=2),
                fill="tozeroy", fillcolor="rgba(0,151,167,0.15)",
                hovertemplate="%{x|%a %d %H:%M} — <b>%{y} %</b><extra></extra>",
            ))
            _now_vline(fig3)
            _base_layout(fig3, h=200)
            fig3.update_yaxes(title="Humidité (%)", range=[0, 105])
            st.plotly_chart(fig3, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# Frise météo heure par heure (icônes)
# ─────────────────────────────────────────────────────────────────────────────

# Codes WMO Open-Meteo → emoji
WMO_ICONS = {
    0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
    45: "🌫️", 48: "🌫️",
    51: "🌦️", 53: "🌦️", 55: "🌦️", 56: "🌧️", 57: "🌧️",
    61: "🌧️", 63: "🌧️", 65: "🌧️", 66: "🌧️", 67: "🌧️",
    71: "🌨️", 73: "🌨️", 75: "🌨️", 77: "🌨️",
    80: "🌦️", 81: "🌧️", 82: "🌧️",
    85: "🌨️", 86: "🌨️",
    95: "⛈️", 96: "⛈️", 99: "⛈️",
}
WMO_DESC = {
    0: "Ciel clair", 1: "Peu nuageux", 2: "Partiellement nuageux", 3: "Couvert",
    45: "Brouillard", 48: "Brouillard givrant",
    51: "Bruine", 53: "Bruine", 55: "Bruine dense",
    61: "Pluie faible", 63: "Pluie", 65: "Pluie forte",
    80: "Averses", 81: "Averses fortes", 82: "Averses violentes",
    95: "Orage", 96: "Orage + grêle", 99: "Orage violent",
}


def _render_weather_frise(w: pd.DataFrame, hours: int = 24) -> None:
    """Frise horizontale heure-par-heure avec icônes météo."""
    from datetime import datetime as _dt
    now_t = _dt.now()
    # Filtrer les heures à partir de maintenant
    future = w[w["Heure"] >= now_t].head(hours)
    if future.empty:
        future = w.head(hours)

    # Construire le HTML de la frise avec séparateur de jour
    cells_html = ""
    last_day = None
    for _, r in future.iterrows():
        h     = r["Heure"]
        code  = int(r.get("weather_code") or 0)
        icon  = WMO_ICONS.get(code, "❔")
        desc  = WMO_DESC.get(code, "—")
        temp  = r.get("temperature_2m")
        temp_txt = f"{temp:.0f}°" if pd.notna(temp) else ""
        # Séparateur de jour
        day = h.date()
        if last_day is None or day != last_day:
            day_label = h.strftime("%a %d/%m").capitalize()
            cells_html += (
                f'<div style="display:inline-flex;flex-direction:column;'
                f'align-items:center;justify-content:center;min-width:60px;'
                f'padding:6px 4px;background:#1565C0;color:#fff;border-radius:6px;'
                f'margin-right:4px;font-weight:700;font-size:11px;">'
                f'{day_label}</div>'
            )
            last_day = day
        # Couleur de fond selon orage ou non
        bg = "#FFEBEE" if code in (95, 96, 99) else "#F5F9FC"
        cells_html += (
            f'<div style="display:inline-flex;flex-direction:column;align-items:center;'
            f'min-width:54px;padding:6px 4px;background:{bg};border-radius:6px;'
            f'margin-right:4px;border:1px solid #e0e6eb;" title="{desc}">'
            f'<span style="font-size:10px;color:#666;font-weight:600;">{h.strftime("%Hh")}</span>'
            f'<span style="font-size:22px;line-height:1.3;">{icon}</span>'
            f'<span style="font-size:11px;color:#333;font-weight:600;">{temp_txt}</span>'
            f'</div>'
        )
    st.markdown(
        f'<div style="overflow-x:auto;white-space:nowrap;padding:8px 4px;'
        f'background:#fafbfc;border-radius:8px;">{cells_html}</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# ASTRO (Soleil + Lune fusionnés)
# ─────────────────────────────────────────────────────────────────────────────

def _render_astro(latitude: float, longitude: float,
                  today: date, now_dt: datetime, moon: dict) -> None:
    section("Astro — Soleil & Lune", icon="🌗", anchor_id="astro")
    with st.container(border=True):
        st.markdown("**☀️ Éphéméride solaire**")
        _render_solaire_inner(latitude, longitude, today, now_dt)
        st.markdown("---")
        st.markdown("**🌙 Cycle lunaire**")
        _render_lunaire_inner(moon, now_dt)


def _render_solaire_inner(latitude: float, longitude: float,
                          today: date, now_dt: datetime) -> None:
    """Variante sans titre de section (utilisée dans _render_astro)."""
    sun_df = fetch_sun_events(
        latitude, longitude,
        (today - timedelta(days=3)).isoformat(),
        (today + timedelta(days=12)).isoformat(),
    )
    if sun_df.empty:
        st.info("Données solaires non disponibles.")
        return

    today_sun = sun_df[sun_df["date"] == today]
    if not today_sun.empty:
        row_s = today_sun.iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("🌅 Lever",         row_s["lever"])
        c2.metric("🌇 Coucher",       row_s["coucher"])
        c3.metric("☀️ Durée du jour",  row_s["duree"])

    plot_df = sun_df.copy()
    plot_df["Jour"]        = pd.to_datetime(plot_df["date"])
    plot_df["Lever (h)"]   = (plot_df["lever_dt"].dt.hour
                               + plot_df["lever_dt"].dt.minute / 60)
    plot_df["Coucher (h)"] = (plot_df["coucher_dt"].dt.hour
                               + plot_df["coucher_dt"].dt.minute / 60)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=plot_df["Jour"], y=plot_df["Lever (h)"],
        mode="lines+markers", name="Lever",
        line=dict(color=C_ORANGE, width=2),
        marker=dict(size=5), fill="none",
    ))
    fig.add_trace(go.Scatter(
        x=plot_df["Jour"], y=plot_df["Coucher (h)"],
        mode="lines+markers", name="Coucher",
        line=dict(color=C_PURPLE, width=2),
        marker=dict(size=5), fill="tonexty",
        fillcolor="rgba(249,168,37,0.10)",
    ))
    fig.add_vline(
        x=_ts(datetime.combine(today, datetime.min.time())),
        line=dict(color=C_RED, width=1.5, dash="dot"),
        annotation_text="Aujourd'hui",
        annotation_font=dict(color=C_RED, size=10),
    )
    fig.update_layout(
        height=CHART_H, margin=dict(l=10, r=10, t=16, b=10),
        plot_bgcolor="#fafbfc", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.3),
        xaxis=dict(type="date", tickformat="%d %b", gridcolor="#eee"),
        yaxis=dict(
            title="Heure", tickmode="array",
            tickvals=list(range(4, 23, 2)),
            ticktext=[f"{h:02d}:00" for h in range(4, 23, 2)],
            gridcolor="#eee",
        ),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_lunaire_inner(moon: dict, now_dt: datetime) -> None:
    """Variante sans titre de section."""
    c1, c2, c3 = st.columns(3)
    c1.metric("Phase",         f"{moon['icon']} {moon['label']}")
    c2.metric("Illumination",  f"{moon['illumination']} %")
    c3.metric("Âge",           f"{moon['age']:.1f} j")

    days = []
    for delta in range(-15, 16):
        dt = now_dt + timedelta(days=delta)
        m  = calculate_moon_phase(dt)
        days.append({
            "date": dt, "illum": m["illumination"], "icon": m["icon"],
            "label": m["label"], "age": m["age"],
        })
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[d["date"] for d in days],
        y=[d["illum"] for d in days],
        mode="lines+markers+text",
        name="Illumination (%)",
        line=dict(color=C_YELLOW, width=2.5),
        fill="tozeroy", fillcolor="rgba(249,168,37,0.12)",
        marker=dict(
            size=9,
            color=[f"rgba(255,{int(200 * d['illum'] / 100)},"
                   f"{int(50 * d['illum'] / 100)},0.9)" for d in days],
        ),
        text=[d["icon"] for d in days],
        textposition="top center", textfont=dict(size=14),
        customdata=[(d["label"], d["age"]) for d in days],
        hovertemplate=("<b>%{x|%d %b}</b><br>"
                       "Phase : %{customdata[0]}<br>"
                       "Illumination : %{y} %<br>"
                       "Âge : %{customdata[1]:.1f} j<extra></extra>"),
    ))
    fig.add_vline(
        x=_ts(now_dt),
        line=dict(color=C_RED, width=1.8, dash="dash"),
        annotation_text="Aujourd'hui",
        annotation_font=dict(color=C_RED, size=10),
    )
    fig.add_hrect(y0=85, y1=100, fillcolor="rgba(255,213,79,0.10)", line_width=0,
                  annotation_text="🌕 Pleine lune", annotation_position="right",
                  annotation_font=dict(size=9))
    fig.add_hrect(y0=0, y1=8, fillcolor="rgba(80,80,120,0.10)", line_width=0,
                  annotation_text="🌑 Nouvelle lune", annotation_position="right",
                  annotation_font=dict(size=9))
    fig.update_layout(
        height=CHART_H, margin=dict(l=10, r=60, t=16, b=10),
        plot_bgcolor="rgba(10,10,30,0.03)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(type="date", tickformat="%d %b", gridcolor="#eee"),
        yaxis=dict(title="Illumination (%)", range=[0, 110], gridcolor="#eee"),
    )
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# ÉPHÉMÉRIDE SOLAIRE (ancienne, conservée pour compat)
# ─────────────────────────────────────────────────────────────────────────────

def _render_solaire(latitude: float, longitude: float,
                    today: date, now_dt: datetime) -> None:
    section("Éphéméride solaire", icon="☀️", anchor_id="astro")
    sun_df = fetch_sun_events(
        latitude, longitude,
        (today - timedelta(days=3)).isoformat(),
        (today + timedelta(days=12)).isoformat(),
    )
    with st.container(border=True):
        if sun_df.empty:
            st.info("Données solaires non disponibles.")
            return

        today_sun = sun_df[sun_df["date"] == today]
        if not today_sun.empty:
            row_s = today_sun.iloc[0]
            c1, c2, c3 = st.columns(3)
            c1.metric("🌅 Lever",         row_s["lever"])
            c2.metric("🌇 Coucher",       row_s["coucher"])
            c3.metric("☀️ Durée du jour",  row_s["duree"])

        plot_df = sun_df.copy()
        plot_df["Jour"]        = pd.to_datetime(plot_df["date"])
        plot_df["Lever (h)"]   = (plot_df["lever_dt"].dt.hour
                                   + plot_df["lever_dt"].dt.minute / 60)
        plot_df["Coucher (h)"] = (plot_df["coucher_dt"].dt.hour
                                   + plot_df["coucher_dt"].dt.minute / 60)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=plot_df["Jour"], y=plot_df["Lever (h)"],
            mode="lines+markers", name="Lever",
            line=dict(color=C_ORANGE, width=2),
            marker=dict(size=5),
            fill="none",   # ← string, pas None
        ))
        fig.add_trace(go.Scatter(
            x=plot_df["Jour"], y=plot_df["Coucher (h)"],
            mode="lines+markers", name="Coucher",
            line=dict(color=C_PURPLE, width=2),
            marker=dict(size=5),
            fill="tonexty",
            fillcolor="rgba(249,168,37,0.10)",
        ))
        # Ligne aujourd'hui — timestamp ms
        fig.add_vline(
            x=_ts(datetime.combine(today, datetime.min.time())),
            line=dict(color=C_RED, width=1.5, dash="dot"),
            annotation_text="Aujourd'hui",
            annotation_font=dict(color=C_RED, size=10),
        )
        fig.update_layout(
            height=CHART_H,
            margin=dict(l=10, r=10, t=16, b=10),
            plot_bgcolor="#fafbfc",
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=-0.3),
            xaxis=dict(type="date", tickformat="%d %b", gridcolor="#eee"),
            yaxis=dict(
                title="Heure",
                tickmode="array",
                tickvals=list(range(4, 23, 2)),
                ticktext=[f"{h:02d}:00" for h in range(4, 23, 2)],
                gridcolor="#eee",
            ),
        )
        st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# CYCLE LUNAIRE
# ─────────────────────────────────────────────────────────────────────────────

def _render_lunaire(moon: dict, now_dt: datetime) -> None:
    section("Cycle lunaire", icon="🌙", anchor_id="lune")
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        c1.metric("Phase",         f"{moon['icon']} {moon['label']}")
        c2.metric("Illumination",  f"{moon['illumination']} %")
        c3.metric("Âge",           f"{moon['age']:.1f} j")

        days = []
        for delta in range(-15, 16):
            dt = now_dt + timedelta(days=delta)
            m  = calculate_moon_phase(dt)
            days.append({
                "date":  dt,
                "illum": m["illumination"],
                "icon":  m["icon"],
                "label": m["label"],
                "age":   m["age"],
            })

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[d["date"] for d in days],
            y=[d["illum"] for d in days],
            mode="lines+markers+text",
            name="Illumination (%)",
            line=dict(color=C_YELLOW, width=2.5),
            fill="tozeroy",
            fillcolor="rgba(249,168,37,0.12)",
            marker=dict(
                size=9,
                color=[
                    f"rgba(255,{int(200 * d['illum'] / 100)},"
                    f"{int(50 * d['illum'] / 100)},0.9)"
                    for d in days
                ],
            ),
            text=[d["icon"] for d in days],
            textposition="top center",
            textfont=dict(size=14),
            customdata=[(d["label"], d["age"]) for d in days],
            hovertemplate=(
                "<b>%{x|%d %b}</b><br>"
                "Phase : %{customdata[0]}<br>"
                "Illumination : %{y} %<br>"
                "Âge : %{customdata[1]:.1f} j<extra></extra>"
            ),
        ))

        # Ligne aujourd'hui — timestamp ms
        fig.add_vline(
            x=_ts(now_dt),
            line=dict(color=C_RED, width=1.8, dash="dash"),
            annotation_text="Aujourd'hui",
            annotation_font=dict(color=C_RED, size=10),
        )
        fig.add_hrect(y0=85, y1=100,
                      fillcolor="rgba(255,213,79,0.10)", line_width=0,
                      annotation_text="🌕 Pleine lune",
                      annotation_position="right",
                      annotation_font=dict(size=9))
        fig.add_hrect(y0=0, y1=8,
                      fillcolor="rgba(80,80,120,0.10)", line_width=0,
                      annotation_text="🌑 Nouvelle lune",
                      annotation_position="right",
                      annotation_font=dict(size=9))

        fig.update_layout(
            height=CHART_H,
            margin=dict(l=10, r=60, t=16, b=10),
            plot_bgcolor="rgba(10,10,30,0.03)",
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            xaxis=dict(type="date", tickformat="%d %b", gridcolor="#eee"),
            yaxis=dict(title="Illumination (%)", range=[0, 115], gridcolor="#eee"),
        )
        st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# POINT D'ENTRÉE
# ─────────────────────────────────────────────────────────────────────────────

def render() -> None:
    hero("Axe 1 · Analyse des conditions", "Mon spot & conditions",
         "Marée · Vent · Pluie · Solaire · Lunaire — données en temps réel.")

    col_h, col_r = st.columns([5, 1])
    with col_r:
        if st.button("🔄 Actualiser", use_container_width=True, key="cond_refresh"):
            st.cache_data.clear()
            st.rerun()

    section("Localisation du spot", icon="📍", anchor_id="spot")
    with st.container(border=True):
        # Si le spot actif a changé depuis la dernière fois, vider les coords mémorisées
        active_nom = st.session_state.get("active_spot_nom")
        last_nom   = st.session_state.get("cond_last_spot_nom")
        if active_nom != last_nom:
            st.session_state.pop("cond_last_lat", None)
            st.session_state.pop("cond_last_lon", None)
            st.session_state[f"cond_lat_stored"] = None
            st.session_state[f"cond_lon_stored"] = None
            st.session_state["cond_last_spot_nom"] = active_nom
        latitude, longitude = location_picker("cond")

    if latitude is not None and longitude is not None:
        st.session_state["cond_last_lat"] = latitude
        st.session_state["cond_last_lon"] = longitude
    else:
        latitude  = st.session_state.get("cond_last_lat")
        longitude = st.session_state.get("cond_last_lon")

    if latitude is None or longitude is None:
        st.info("Choisis un mode de localisation pour charger les conditions.")
        if anchor := get_active_anchor():
            scroll_to_anchor(anchor)
        return

    # ── Choix de la date d'analyse ────────────────────────────────────
    with st.container(border=True):
        cm1, cm2, cm3 = st.columns([1.2, 2, 2])
        with cm1:
            mode_date = st.radio(
                "📅 Date d'analyse",
                ["Aujourd'hui", "Jour choisi"],
                key="cond_mode_date",
                horizontal=False,
            )
        with cm2:
            if mode_date == "Aujourd'hui":
                analysis_date = date.today()
                st.markdown(
                    f'<div style="background:#E3F2FD;border-left:3px solid #1565C0;'
                    f'padding:8px 12px;border-radius:0 6px 6px 0;margin-top:24px;">'
                    f'<strong>📅 {analysis_date.strftime("%A %d/%m/%Y")}</strong>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                analysis_date = st.date_input(
                    "Choisis un jour",
                    value=date.today(),
                    min_value=date.today() - timedelta(days=730),
                    max_value=date.today() + timedelta(days=14),
                    format="DD/MM/YYYY",
                    key="cond_chosen_date",
                    help="Marées : jusqu'à 2 ans en arrière et 14 jours dans le futur. Météo : 7 jours en avant.",
                )
        with cm3:
            # Indication selon la date
            delta = (analysis_date - date.today()).days
            if delta == 0:
                lbl = "🕐 Conditions actuelles"
            elif delta > 0:
                lbl = f"🔮 Prévision dans {delta} jour(s)"
            else:
                lbl = f"⏪ Historique ({abs(delta)} jour(s))"
            st.markdown(
                f'<div style="background:#FFF3E0;border-left:3px solid #E65100;'
                f'padding:8px 12px;border-radius:0 6px 6px 0;margin-top:24px;">'
                f'<strong>{lbl}</strong></div>',
                unsafe_allow_html=True,
            )

    # ── Pêcheurs autour de moi (à développer) ─────────────────────────
    section("Pêcheurs autour de moi", icon="👥", anchor_id="pecheurs_autour")
    with st.container(border=True):
        st.markdown(
            '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
            'color:#fff;padding:14px 18px;border-radius:10px;text-align:center;">'
            '<div style="font-size:32px;margin-bottom:6px;">🗺️ 👥 🎣</div>'
            '<div style="font-size:15px;font-weight:800;margin-bottom:4px;">'
            'Bientôt disponible</div>'
            '<div style="font-size:12px;opacity:.85;line-height:1.5;">'
            'Découvre les pêcheurs autour de toi en mode <b>Snap</b> :<br>'
            '• Carte temps réel avec position des pêcheurs<br>'
            '• Captures partagées en direct<br>'
            '• Spots populaires à proximité<br>'
            '• Tchat de zone</div>'
            '<div style="font-size:11px;opacity:.7;margin-top:10px;">'
            '🚧 Fonctionnalité en cours de développement</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    today  = analysis_date
    now_dt = datetime.now() if analysis_date == date.today() else datetime.combine(analysis_date, datetime.min.time())
    end_2d = (today + timedelta(days=1)).isoformat()

    # ── Adresse reverse geocoding ─────────────────────────────────────
    # Toujours recalculée avec les coordonnées actuelles
    geo_data   = reverse_geocode(latitude, longitude)
    address    = geo_data.get("address", {})

    # Construire une adresse courte et lisible
    addr       = geo_data.get("address", {})
    parts = []
    place = (addr.get("beach") or addr.get("natural") or addr.get("amenity")
             or addr.get("village") or addr.get("hamlet") or addr.get("suburb"))
    if place:  parts.append(place)
    if addr.get("road"): parts.append(addr["road"])
    city = addr.get("town") or addr.get("city") or addr.get("municipality")
    if city and city not in parts: parts.append(city)
    if addr.get("postcode"): parts.append(addr["postcode"])
    if addr.get("country"): parts.append(addr["country"])
    display_nm = ", ".join(p for p in parts if p) or geo_data.get("display_name", "—")

    with st.container(border=True):
        st.markdown(
            f'<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
            f'color:#fff;padding:8px 14px;border-radius:8px;margin-bottom:8px;">'
            f'<span style="font-size:13px;font-weight:700;">🛰️ Coordonnées GPS</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        c1.metric("Latitude",  f"{latitude:.6f}")
        c2.metric("Longitude", f"{longitude:.6f}")

    section("Cartographie", icon="🗺️", anchor_id="carto")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**📤 Partager ce spot**")
            share_location_widget(latitude, longitude, nom=display_nm)
        with c2:
            st.markdown("**🌊 Carte maritime**")
            maritime_map(latitude, longitude)

    # Données API
    weather_df = fetch_weather_range(latitude, longitude, today.isoformat(), end_2d)
    marine_df  = fetch_marine_range(latitude, longitude, today.isoformat(), end_2d)
    current_w  = closest_to_now(weather_df)
    current_m  = closest_to_now(marine_df)
    current    = {**current_w, **current_m}
    moon       = calculate_moon_phase(now_dt)

    # ── Sections ─────────────────────────────────────────────────────
    _render_maree(latitude, longitude, analysis_date)

    if weather_df is not None and not weather_df.empty:
        w = weather_df.copy()
        w["Heure"] = pd.to_datetime(w["time"])

        # Fusionner la température eau (marine_df) sur le DataFrame météo
        if marine_df is not None and not marine_df.empty and "sea_surface_temperature" in marine_df.columns:
            m_merge = marine_df[["time", "sea_surface_temperature"]].copy()
            m_merge["time"] = pd.to_datetime(m_merge["time"])
            w_time = w[["time"]].copy()
            w_time["time"] = pd.to_datetime(w_time["time"])
            w["sea_surface_temperature"] = w_time["time"].map(
                m_merge.set_index("time")["sea_surface_temperature"]
            )

        # ── Détection orage dans les 2 prochaines heures ─────────────
        st.session_state["storm_alert_2h"] = False
        if "weather_code" in w.columns:
            now_t  = datetime.now()
            limit  = now_t + timedelta(hours=2)
            mask   = (w["Heure"] >= now_t) & (w["Heure"] <= limit)
            future = w[mask]
            if not future.empty:
                storm_codes = {95, 96, 99}
                if future["weather_code"].dropna().astype(int).isin(storm_codes).any():
                    st.session_state["storm_alert_2h"] = True
                    st.error("⛈️ **ALERTE ORAGE** — orage prévu dans les 2 prochaines heures !")

        _render_pluie_nuages(w, current, latitude, longitude, marine_df)
    else:
        st.warning("Données météo Open-Meteo non disponibles pour ce point.")

    _render_astro(latitude, longitude, today, now_dt, moon)

    section("Réglementation locale", icon="⚖️", anchor_id="regle")
    region_info = estimate_region(address)
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        c1.metric("Région",      region_info["region"])
        c2.metric("Façade",      region_info["zone"])
        c3.metric("Département", region_info["county"])
        st.caption(f"Espèces probables : {region_info['profil']}")
    st.markdown("**Tailles minimales indicatives**")
    sizes_df = get_minimum_sizes_table(region_info["zone"])
    srch = st.text_input("Filtrer par espèce", key="cond_species_search")
    if srch:
        sizes_df = sizes_df[
            sizes_df["Espèce"].str.lower().str.contains(srch.lower(), na=False)
        ]
    st.dataframe(sizes_df, use_container_width=True, hide_index=True)
    st.markdown("**Sources réglementaires**")
    for _, row in get_regulation_sources().iterrows():
        st.markdown(f"- [{row['Source']}]({row['Lien']}) — {row['Vérifier']}")

    if anchor := get_active_anchor():
        scroll_to_anchor(anchor)
