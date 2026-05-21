"""Point d'entrée du Réseau de la Péchouille."""
from __future__ import annotations
import streamlit as st
from modules.reseau_auth import render_auth
from modules.reseau_fil  import render_fil
from modules.reseau_amis import render_amis

def render() -> None:
    # Header
    st.markdown(
        '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        'color:#fff;padding:14px 20px;border-radius:8px;margin:8px 0 18px;">'
        '<span style="font-size:18px;font-weight:800;">🌊 Réseau de la Péchouille</span>'
        '<div style="font-size:12px;opacity:.85;margin-top:3px;">'
        'Partage tes prises, retrouve tes potes, compare vos records.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Auth obligatoire
    if not render_auth():
        return

    user = st.session_state.get("reseau_user")

    # Barre utilisateur connecté
    c1, c2 = st.columns([4, 1])
    c1.markdown(
        f'<div style="background:#E8F5E9;border-left:3px solid #2E7D32;'
        f'padding:8px 14px;border-radius:0 8px 8px 0;font-size:13px;">'
        f'🎣 Connecté en tant que <strong>{user["pseudo"]}</strong>'
        f'{"  ·  📍 " + user.get("localisation","") if user.get("localisation") else ""}'
        f'</div>',
        unsafe_allow_html=True,
    )
    if c2.button("🚪 Déconnexion", key="reseau_logout", use_container_width=True):
        st.session_state.pop("reseau_user", None)
        st.rerun()

    st.markdown("")

    # Onglets
    tab_fil, tab_amis = st.tabs(["📰 Fil d'actualité", "👥 Amis & Classement"])
    with tab_fil:
        render_fil()
    with tab_amis:
        render_amis()
