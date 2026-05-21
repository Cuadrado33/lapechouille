"""Page Amis standalone."""
from __future__ import annotations
import streamlit as st
from modules.reseau_auth import render_auth
from modules.reseau_amis import render_amis

def render() -> None:
    st.markdown(
        '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        'color:#fff;padding:14px 20px;border-radius:8px;margin:8px 0 18px;">'
        '<span style="font-size:18px;font-weight:800;">👥 Amis</span>'
        '<div style="font-size:12px;opacity:.85;margin-top:3px;">'
        'Trouve des pêcheurs, envoie des demandes d\'amis.</div></div>',
        unsafe_allow_html=True,
    )
    if not render_auth():
        return
    user = st.session_state.get("reseau_user")
    col_back, col_logout = st.columns([4, 1])
    col_back.markdown(f'🎣 Connecté : **{user["pseudo"]}**')
    if col_logout.button("🚪 Déconnexion", key="amis_logout"):
        st.session_state.pop("reseau_user", None)
        st.rerun()
    render_amis()
