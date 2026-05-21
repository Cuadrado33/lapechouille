"""
Application Carnet Surfcasting — version restructurée v4
Lancement : py -m streamlit run app.py
"""
from __future__ import annotations

# truststore : optionnel, améliore la gestion SSL Windows si installé
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

import streamlit as st
from core.database import init_db
from ui.styles import inject_global_styles
from ui.navigation import render_sidebar_navigation, get_active_page

from modules import (
    accueil, conditions, sessions, captures,
    competition, analyse, export_data, reseau,
    materiel_cannes, materiel_moulinets, materiel_montages,
    materiel_divers, materiel_tableaux,
    identification, photos, webcams, services, alertes,
    mes_spots, spots_appats, profil,
)


def _inject_pwa() -> None:
    """Injecte le manifest PWA et le service worker pour Android."""
    st.markdown("""
    <link rel="manifest" href="/app/static/manifest.json">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Surfcasting">
    <meta name="theme-color" content="#0c2340">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
    <script>
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', function() {
            navigator.serviceWorker.register('/app/static/sw.js')
                .then(r => console.log('SW enregistré:', r.scope))
                .catch(e => console.log('SW erreur:', e));
        });
    }
    </script>
    """, unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(
        page_title="Carnet Surfcasting",
        page_icon="🎣",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_db()
    inject_global_styles()
    _inject_pwa()
    render_sidebar_navigation()
    active_page = get_active_page()

    PAGE_ROUTER = {
        "accueil": accueil.render,
        "profil": profil.render,
        "conditions": conditions.render,
        "sessions": sessions.render,
        "captures": captures.render,
        "competition": competition.render,
        "analyse": analyse.render,
        "mat_cannes": materiel_cannes.render,
        "mat_moulinets": materiel_moulinets.render,
        "mat_montages": materiel_montages.render,
        "mat_divers": materiel_divers.render,
        "mat_tableaux": materiel_tableaux.render,
        "mes_spots": mes_spots.render,
        "spots_appats": spots_appats.render,
        "identification": identification.render,
        "photos": photos.render,
        "webcams": webcams.render,
        "services": services.render,
        "alertes":  alertes.render,
        "export":   export_data.render,
        "reseau":   reseau.render,
    }

    render_fn = PAGE_ROUTER.get(active_page, accueil.render)
    try:
        render_fn()
    except Exception as exc:
        st.error(f"Erreur lors du rendu de la page : {exc}")
        with st.expander("Détails techniques (debug)"):
            import traceback
            st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
