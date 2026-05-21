"""
Page « Analyse de performance » — statistiques, trophées, records.
"""
from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

from core.database import load_sessions, load_captures
from core.utils import safe_float, safe_str, format_date_fr
from data.fish_data import FISH_SVG, FISH_META, FISH_EMOJI_FALLBACK, get_fish_visual
from data.fish_records import get_official_record
from modules.identification import _capture_matches_fish
from ui.components import section, metric_grid


def render() -> None:
    # ── Bandeau bleu marine ──────────────────────────────────────────
    st.markdown(
        '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        'color:#fff;padding:14px 20px;border-radius:8px;margin:8px 0 18px;">'
        '<span style="font-size:18px;font-weight:800;">📈 Analyse de performance</span>'
        '<div style="font-size:12px;opacity:.85;margin-top:3px;">'
        'Statistiques, trophées et records personnels de pêche.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    captures = load_captures()
    sessions = load_sessions()

    if captures.empty:
        st.info("Aucune capture enregistrée.")
        return

    # Métriques globales
    nb_captures = len(captures)
    nb_especes  = captures["espece"].nunique() if "espece" in captures.columns else 0
    poids_total = captures["poids_g"].fillna(0).sum() if "poids_g" in captures.columns else 0
    nb_sessions = captures["session_id"].nunique() if "session_id" in captures.columns else 0

    metric_grid([
        {"icon": "🎣", "label": "Captures",    "value": str(nb_captures), "sub": "Total enregistré"},
        {"icon": "🐟", "label": "Espèces",     "value": str(nb_especes),  "sub": "Espèces différentes"},
        {"icon": "⚖️", "label": "Poids total", "value": f"{poids_total/1000:.2f} kg" if poids_total >= 1000 else f"{poids_total:.0f} g", "sub": "Cumul pesé"},
        {"icon": "📅", "label": "Sessions",    "value": str(nb_sessions), "sub": "Avec prises"},
    ])

    tab_espece, tab_appat, tab_montage, tab_conditions, tab_trophees = st.tabs([
        "🐟 Par espèce", "🪱 Par appât", "🧵 Par montage",
        "🌊 Par conditions", "🏆 Mes trophées",
    ])

    with tab_espece:
        section("Captures par espèce", icon="🐟")
        if "espece" in captures.columns:
            df = captures.groupby("espece", as_index=False).agg(
                captures=("id", "count"),
                poids_total_g=("poids_g", "sum"),
                taille_moyenne_cm=("taille_cm", "mean"),
            ).sort_values("captures", ascending=False)
            df["poids_total_g"]       = df["poids_total_g"].fillna(0).round(0)
            df["taille_moyenne_cm"]   = df["taille_moyenne_cm"].round(1)
            st.dataframe(df, use_container_width=True, hide_index=True)
            fig = px.bar(df.head(15), x="espece", y="captures", text="captures", color="captures")
            fig.update_traces(textposition="outside")
            fig.update_layout(height=400, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)

    with tab_appat:
        section("Par appât", icon="🪱")
        if "appat" in captures.columns:
            df = captures.groupby("appat", as_index=False).agg(
                captures=("id", "count"),
                poids_moyen=("poids_g", "mean"),
            ).sort_values("captures", ascending=False)
            df["poids_moyen"] = df["poids_moyen"].fillna(0).round(0)
            st.dataframe(df, use_container_width=True, hide_index=True)
            fig = px.bar(df.head(12), x="appat", y="captures", text="captures")
            fig.update_traces(textposition="outside")
            fig.update_layout(height=380, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)

    with tab_montage:
        section("Par montage", icon="🧵")
        if "montage" in captures.columns:
            df = captures.groupby("montage", as_index=False).agg(
                captures=("id", "count"),
                taille_moy=("taille_cm", "mean"),
            ).sort_values("captures", ascending=False)
            df["taille_moy"] = df["taille_moy"].fillna(0).round(1)
            st.dataframe(df, use_container_width=True, hide_index=True)
            fig = px.bar(df.head(10), x="montage", y="captures", text="captures")
            fig.update_traces(textposition="outside")
            fig.update_layout(height=360, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)

    with tab_conditions:
        section("Par conditions", icon="🌊")
        cond_cols = [c for c in ["phase_maree", "coefficient_maree", "vent_vitesse",
                                   "vague_hauteur", "temperature_eau"] if c in captures.columns]
        display = ["date_session", "lieu", "espece", "taille_cm", "poids_g"] + cond_cols
        display = [c for c in display if c in captures.columns]
        st.dataframe(captures[display].head(100), use_container_width=True, hide_index=True)
        if "phase_maree" in captures.columns:
            df = captures.groupby("phase_maree", as_index=False).size().rename(columns={"size": "captures"})
            fig = px.bar(df, x="phase_maree", y="captures", text="captures")
            fig.update_traces(textposition="outside")
            fig.update_layout(height=340, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)

    with tab_trophees:
        _render_trophees(captures, sessions)


# ─────────────────────────────────────────────────────────────────────────────
# Onglet Mes trophées
# ─────────────────────────────────────────────────────────────────────────────

def _render_trophees(captures: pd.DataFrame, sessions: pd.DataFrame) -> None:
    # Bandeau
    st.markdown(
        '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        'color:#fff;padding:10px 14px;border-radius:8px;margin-bottom:14px;">'
        '<span style="font-size:15px;font-weight:800;">🏆 Mes records & trophées</span>'
        '<div style="font-size:11px;opacity:.85;margin-top:2px;">'
        'Meilleures prises par espèce — comparées aux records officiels.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Index session → date/lieu
    sess_idx: dict = {}
    if not sessions.empty:
        for _, s in sessions.iterrows():
            sess_idx[int(s["id"])] = s

    # Nettoyage captures
    cap = captures.copy()
    if "espece" not in cap.columns:
        st.warning("Données incomplètes.")
        return
    cap["espece"] = cap["espece"].fillna("").astype(str)
    cap = cap[cap["espece"].str.strip() != ""]
    if cap.empty:
        st.info("Aucune capture avec espèce identifiée.")
        return

    for col in ["taille_cm", "poids_g", "poids_estime_g"]:
        if col in cap.columns:
            cap[col] = pd.to_numeric(cap[col], errors="coerce")

    def _meta(row):
        if row is None:
            return "—", "—"
        sid = row.get("session_id")
        if pd.notna(sid) and int(sid) in sess_idx:
            s = sess_idx[int(sid)]
            return (format_date_fr(s.get("date_session")) or "—",
                    safe_str(s.get("lieu")) or "—")
        return "—", "—"

    # ── Construire les records ──────────────────────────────────────
    records = []
    for espece, group in cap.groupby("espece"):
        nb_total = len(group)

        # Record taille
        best_t_row = None
        if "taille_cm" in group.columns:
            vt = group.dropna(subset=["taille_cm"])
            vt = vt[vt["taille_cm"] > 0]
            if not vt.empty:
                best_t_row = vt.loc[vt["taille_cm"].idxmax()]

        # Record poids (mesuré ou estimé en fallback)
        best_p_row, poids_est_flag = None, False
        if "poids_g" in group.columns:
            vp = group.dropna(subset=["poids_g"])
            vp = vp[vp["poids_g"] > 0]
            if not vp.empty:
                best_p_row = vp.loc[vp["poids_g"].idxmax()]
        if best_p_row is None and "poids_estime_g" in group.columns:
            ve = group.dropna(subset=["poids_estime_g"])
            ve = ve[ve["poids_estime_g"] > 0]
            if not ve.empty:
                best_p_row = ve.loc[ve["poids_estime_g"].idxmax()]
                poids_est_flag = True

        date_t, lieu_t = _meta(best_t_row)
        date_p, lieu_p = _meta(best_p_row)

        # Photo (trophée > record taille > n'importe quelle photo)
        photo_path, has_trophy = "", False
        if "poisson_trophee" in group.columns:
            tr = group[group["poisson_trophee"].fillna(0).astype(int) == 1]
            if not tr.empty:
                has_trophy = True
                if "photo_path" in tr.columns:
                    tr_p = tr[tr["photo_path"].astype(str).str.len() > 0]
                    if not tr_p.empty:
                        p = safe_str(tr_p.iloc[0].get("photo_path"))
                        if p and Path(p).exists():
                            photo_path = p
        if not photo_path and best_t_row is not None:
            p = safe_str(best_t_row.get("photo_path"))
            if p and Path(p).exists():
                photo_path = p
        if not photo_path and "photo_path" in group.columns:
            wp = group[group["photo_path"].astype(str).str.len() > 0]
            if not wp.empty:
                p = safe_str(wp.iloc[0].get("photo_path"))
                if p and Path(p).exists():
                    photo_path = p

        # Fiche poisson + record officiel
        fish_match = next((f for f in FISH_META if _capture_matches_fish(espece, f)), None)
        official = get_official_record(fish_match["id"]) if fish_match else None

        poids_value = None
        if best_p_row is not None:
            poids_value = float(best_p_row["poids_estime_g"] if poids_est_flag
                                 else best_p_row["poids_g"])

        records.append({
            "espece": espece, "fish": fish_match, "nb": nb_total,
            "taille": float(best_t_row["taille_cm"]) if best_t_row is not None else None,
            "date_t": date_t, "lieu_t": lieu_t,
            "poids": poids_value, "poids_est": poids_est_flag,
            "date_p": date_p, "lieu_p": lieu_p,
            "photo": photo_path, "trophy": has_trophy,
            "official": official,
        })

    records.sort(key=lambda r: -(r["taille"] or 0))

    st.markdown(f"**{len(records)} espèce(s)** · {len(cap)} prises totales")
    st.markdown("---")

    for r in records:
        espece = r["espece"]
        fish   = r["fish"]
        photo  = r["photo"]
        official = r["official"]

        # SVG via helper centralisé
        vis_html = get_fish_visual(espece, size=100, bg="#f5f7f9")

        # Photo personnelle
        photo_html = ""
        if photo:
            try:
                ext  = Path(photo).suffix.lower().lstrip(".")
                mime = "image/jpeg" if ext in ("jpg","jpeg") else f"image/{ext}"
                b64  = base64.b64encode(Path(photo).read_bytes()).decode()
                tag  = "🏆" if r["trophy"] else "📸"
                photo_html = (
                    f'<div style="position:relative;width:100%;height:100%;">'
                    f'<img src="data:{mime};base64,{b64}" '
                    f'style="width:100%;height:100%;object-fit:cover;'
                    f'border-radius:8px;border:2px solid #FFB300;">'
                    f'<div style="position:absolute;top:4px;right:4px;'
                    f'background:#FFB300;color:#fff;font-size:10px;font-weight:700;'
                    f'padding:2px 6px;border-radius:6px;">{tag}</div>'
                    f'</div>'
                )
            except Exception:
                pass

        def _fmt_p(p, suffix=""):
            if p is None: return "—"
            return (f"{p/1000:.2f} kg" if p >= 1000 else f"{p:.0f} g") + suffix

        taille_txt   = f"{r['taille']:.0f} cm" if r["taille"] else "—"
        poids_txt    = _fmt_p(r["poids"], " (est.)" if r["poids_est"] else "")
        poids_no_suf = _fmt_p(r["poids"])

        with st.container(border=True):
            # Bandeau titre bleu marine
            trophy_badge = ('<span style="background:rgba(255,255,255,.2);'
                             'font-size:10px;font-weight:700;padding:2px 8px;'
                             'border-radius:8px;margin-left:8px;">🏆 TROPHÉE</span>'
                             ) if r["trophy"] else ""
            st.markdown(
                f'<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
                f'color:#fff;padding:10px 14px;border-radius:8px;margin-bottom:10px;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                f'<span style="font-size:17px;font-weight:800;">{espece}{trophy_badge}</span>'
                f'<span style="font-size:11px;opacity:.85;">🎣 {r["nb"]} prise(s)</span>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

            # 4 colonnes : photo perso │ SVG │ record taille │ record poids
            col_photo, col_svg, col_t, col_p = st.columns([1, 0.8, 1.3, 1.3])

            with col_photo:
                if photo_html:
                    components.html(
                        f'<div style="height:110px;">{photo_html}</div>',
                        height=118, scrolling=False,
                    )
                else:
                    st.markdown(
                        '<div style="height:110px;background:#f5f7f9;border:2px dashed #ccc;'
                        'border-radius:8px;display:flex;align-items:center;justify-content:center;'
                        'color:#aaa;font-size:11px;text-align:center;">Aucune<br>photo</div>',
                        unsafe_allow_html=True,
                    )

            with col_svg:
                components.html(
                    f'<div style="height:110px;display:flex;align-items:center;'
                    f'justify-content:center;">{vis_html}</div>',
                    height=118, scrolling=False,
                )

            with col_t:
                st.markdown(
                    f'<div style="background:linear-gradient(135deg,#FFB300,#E65100);'
                    f'color:#fff;border-radius:8px;padding:10px 12px;text-align:center;'
                    f'height:110px;display:flex;flex-direction:column;justify-content:center;">'
                    f'<div style="font-size:9px;font-weight:700;letter-spacing:1px;'
                    f'opacity:.9;">📏 MA TAILLE MAX</div>'
                    f'<div style="font-size:26px;font-weight:900;line-height:1;margin:4px 0;">'
                    f'{taille_txt}</div>'
                    f'<div style="font-size:10px;opacity:.9;">{r["date_t"]}</div>'
                    f'<div style="font-size:10px;opacity:.9;">📍 {r["lieu_t"][:20]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            with col_p:
                est_tag = ('<span style="background:rgba(255,255,255,.2);font-size:8px;'
                            'font-weight:700;padding:1px 5px;border-radius:4px;'
                            'margin-left:4px;">EST.</span>') if r["poids_est"] else ""
                st.markdown(
                    f'<div style="background:linear-gradient(135deg,#42A5F5,#1565C0);'
                    f'color:#fff;border-radius:8px;padding:10px 12px;text-align:center;'
                    f'height:110px;display:flex;flex-direction:column;justify-content:center;">'
                    f'<div style="font-size:9px;font-weight:700;letter-spacing:1px;'
                    f'opacity:.9;">⚖️ MON POIDS MAX{est_tag}</div>'
                    f'<div style="font-size:26px;font-weight:900;line-height:1;margin:4px 0;">'
                    f'{poids_no_suf}</div>'
                    f'<div style="font-size:10px;opacity:.9;">{r["date_p"]}</div>'
                    f'<div style="font-size:10px;opacity:.9;">📍 {r["lieu_p"][:20]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # Bandeau record officiel
            if official:
                off_t    = official.get("taille_cm")
                off_p    = official.get("poids_g")
                off_lieu = official.get("lieu") or "—"
                off_an   = official.get("annee") or ""
                off_t_txt = f"{off_t:.0f} cm" if off_t else "—"
                off_p_txt = (f"{off_p/1000:.1f} kg" if off_p and off_p >= 1000
                               else (f"{off_p:.0f} g" if off_p else "—"))
                pct = (r["taille"] / off_t * 100) if (r["taille"] and off_t) else 0
                pct_color = "#2E7D32" if pct >= 80 else ("#E65100" if pct >= 50 else "#9E9E9E")

                st.markdown(
                    f'<div style="background:linear-gradient(135deg,#0c2340,#1565C0);'
                    f'color:#fff;border-radius:8px;padding:8px 14px;margin-top:8px;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;'
                    f'flex-wrap:wrap;gap:6px;">'
                    f'<span style="font-size:10px;font-weight:700;opacity:.9;'
                    f'letter-spacing:1px;">🌍 RECORD OFFICIEL CONNU'
                    f'{"  📅 " + off_an if off_an else ""}</span>'
                    f'<div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;">'
                    f'<strong>📏 {off_t_txt}</strong>'
                    f'<strong>⚖️ {off_p_txt}</strong>'
                    f'<span style="opacity:.9;font-size:11px;">📍 {off_lieu}</span>'
                    + (f'<span style="background:{pct_color};font-size:10px;font-weight:700;'
                        f'padding:2px 9px;border-radius:8px;">'
                        f'Mon score : {pct:.0f}%</span>' if pct > 0 else "") +
                    f'</div></div></div>',
                    unsafe_allow_html=True,
                )

    # Export CSV
    st.markdown("---")
    df_exp = pd.DataFrame([{
        "Espèce": r["espece"], "Nb prises": r["nb"],
        "Taille max (cm)": r["taille"], "Date taille": r["date_t"], "Lieu taille": r["lieu_t"],
        "Poids max (g)": r["poids"], "Poids estimé": "oui" if r["poids_est"] else "non",
        "Date poids": r["date_p"], "Lieu poids": r["lieu_p"],
        "Trophée": "oui" if r["trophy"] else "non",
        "Record off. cm": r["official"].get("taille_cm") if r["official"] else None,
        "Record off. g":  r["official"].get("poids_g")   if r["official"] else None,
        "Record off. lieu": r["official"].get("lieu")    if r["official"] else None,
    } for r in records])
    st.download_button("📥 Exporter mes records (CSV)",
                        df_exp.to_csv(index=False).encode("utf-8-sig"),
                        "mes_records.csv", "text/csv")
