"""Application La Péchouille — Surfcasting"""
from __future__ import annotations

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

import json
import streamlit as st
from core.database import init_db
from ui.styles import inject_global_styles
from ui.navigation import render_sidebar_navigation, get_active_page

from modules import (
    accueil, conditions, sessions, captures,
    competition, analyse, export_data, reseau, reseau_class, reseau_amis_page, reseau_messages,
    materiel_cannes, materiel_moulinets, materiel_montages,
    materiel_divers, materiel_tableaux,
    identification, photos, webcams, services, alertes,
    mes_spots, spots_appats, profil,
)


def _persist_session() -> None:
    """Restaure la session depuis le token URL."""
    from core.auth import restore_session
    restore_session()


def _session_js() -> None:
    """Sauvegarde le token dans l'URL si connecté."""
    token = st.session_state.get("auth_token")
    if token and st.query_params.get("token") != token:
        st.query_params["token"] = token


def main() -> None:
    st.set_page_config(
        page_title="La Péchouille",
        page_icon="🎣",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_db()
    inject_global_styles()
    _persist_session()
    _session_js()
    render_sidebar_navigation()
    active_page = get_active_page()

    PAGE_ROUTER = {
        "accueil":       accueil.render,
        "profil":        profil.render,
        "conditions":    conditions.render,
        "sessions":      sessions.render,
        "captures":      captures.render,
        "competition":   competition.render,
        "analyse":       analyse.render,
        "mat_cannes":    materiel_cannes.render,
        "mat_moulinets": materiel_moulinets.render,
        "mat_montages":  materiel_montages.render,
        "mat_divers":    materiel_divers.render,
        "mat_tableaux":  materiel_tableaux.render,
        "mes_spots":     mes_spots.render,
        "spots_appats":  spots_appats.render,
        "identification":identification.render,
        "photos":        photos.render,
        "webcams":       webcams.render,
        "services":      services.render,
        "alertes":       alertes.render,
        "export":        export_data.render,
        "reseau":          reseau.render,
        "reseau_amis":     reseau_amis_page.render,
        "reseau_class":    reseau_class.render,
        "reseau_messages": reseau_messages.render,
    }

    render_fn = PAGE_ROUTER.get(active_page, accueil.render)
    try:
        from ui.components import render_profile_banner
        render_profile_banner()
        render_fn()
    except Exception as exc:
        st.error(f"Erreur : {exc}")
        import traceback
        st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
