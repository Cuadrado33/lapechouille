"""
Page « Export » — export CSV complet, trophées, sauvegarde.
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st

from core.database import load_sessions, load_captures, load_materiel, load_multimedia
from core.utils import safe_str, safe_float, format_weight_display
from ui.components import hero, section, metric_grid


def render() -> None:
    hero("Axe 4 · Divers", "Exports & données", "Sauvegarde tes données, exporte en CSV.")

    tab_csv, tab_trophees, tab_info = st.tabs(["📥 Export CSV", "🏆 Poissons trophées", "ℹ️ Info base"])

    with tab_csv:
        _render_export_csv()
    with tab_trophees:
        _render_trophees()
    with tab_info:
        _render_db_info()


def _render_export_csv() -> None:
    section("Export CSV", icon="📥")
    st.caption("Chaque bouton génère un fichier CSV à télécharger.")

    sessions = load_sessions()
    captures = load_captures()
    materiel = load_materiel()

    col1, col2, col3 = st.columns(3)

    with col1:
        with st.container(border=True):
            st.metric("Sessions", len(sessions))
            if not sessions.empty:
                st.download_button(
                    "📥 Sessions",
                    sessions.to_csv(index=False).encode("utf-8-sig"),
                    f"sessions_{datetime.now():%Y%m%d}.csv",
                    "text/csv",
                    use_container_width=True,
                )
    with col2:
        with st.container(border=True):
            st.metric("Captures", len(captures))
            if not captures.empty:
                st.download_button(
                    "📥 Captures",
                    captures.to_csv(index=False).encode("utf-8-sig"),
                    f"captures_{datetime.now():%Y%m%d}.csv",
                    "text/csv",
                    use_container_width=True,
                )
    with col3:
        with st.container(border=True):
            st.metric("Matériel", len(materiel))
            if not materiel.empty:
                st.download_button(
                    "📥 Matériel",
                    materiel.to_csv(index=False).encode("utf-8-sig"),
                    f"materiel_{datetime.now():%Y%m%d}.csv",
                    "text/csv",
                    use_container_width=True,
                )

    # Export global
    section("Export combiné", icon="📦")
    if st.button("📥 Export global (toutes tables)", use_container_width=True):
        buf = BytesIO()
        import zipfile
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            if not sessions.empty:
                zf.writestr("sessions.csv", sessions.to_csv(index=False))
            if not captures.empty:
                zf.writestr("captures.csv", captures.to_csv(index=False))
            if not materiel.empty:
                zf.writestr("materiel.csv", materiel.to_csv(index=False))
        buf.seek(0)
        st.download_button(
            "💾 Télécharger le ZIP",
            buf.getvalue(),
            f"surfcasting_export_{datetime.now():%Y%m%d}.zip",
            "application/zip",
            use_container_width=True,
        )


def _render_trophees() -> None:
    section("Poissons trophées", icon="🏆")
    captures = load_captures()

    if captures.empty:
        st.info("Aucune capture.")
        return

    trophees = pd.DataFrame()
    if "poisson_trophee" in captures.columns:
        trophees = captures[captures["poisson_trophee"].fillna(0).astype(int) == 1]
    if "poisson_trophe" in captures.columns and trophees.empty:
        trophees = captures[captures["poisson_trophe"].fillna(0).astype(int) == 1]

    if trophees.empty:
        st.info("Aucun poisson trophée marqué. Coche « Trophée » sur tes meilleures prises.")
        return

    for _, row in trophees.iterrows():
        espece = safe_str(row.get("espece")) or "—"
        taille = safe_float(row.get("taille_cm"))
        poids_txt = format_weight_display(row)
        lieu = safe_str(row.get("lieu")) or "—"
        date_txt = format_date_fr(row.get("date_session"))

        with st.container(border=True):
            st.markdown(f"### 🏆 {espece}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Taille", f"{taille:.0f} cm" if taille else "—")
            c2.metric("Poids", poids_txt)
            c3.metric("Lieu", lieu)
            c4.metric("Date", date_txt or "—")


def _render_db_info() -> None:
    section("Info base de données", icon="ℹ️")
    sessions = load_sessions()
    captures = load_captures()
    materiel = load_materiel()

    metric_grid([
        {"icon": "📅", "label": "Sessions", "value": str(len(sessions)), "sub": "Enregistrées"},
        {"icon": "🎣", "label": "Captures", "value": str(len(captures)), "sub": "Total"},
        {"icon": "🎒", "label": "Matériel", "value": str(len(materiel)), "sub": "Articles"},
    ])

    st.markdown("**Fichier base** : `surfcasting.db` (SQLite local)")
    st.caption("Fais une copie régulière de ce fichier pour sauvegarde.")
