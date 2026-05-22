"""Authentification — inscription / connexion via core.auth."""
from __future__ import annotations
import streamlit as st
from core.auth import login as auth_login, register as auth_register


def render_auth() -> bool:
    """Affiche login/register. Retourne True si connecté."""
    if st.session_state.get("reseau_user"):
        return True

    st.markdown(
        '<div style="background:linear-gradient(135deg,#1565C0,#0c2340);'
        'color:#fff;padding:14px 20px;border-radius:8px;margin-bottom:20px;">'
        '<span style="font-size:18px;font-weight:800;">🎣 Réseau de la Péchouille</span>'
        '<div style="font-size:12px;opacity:.85;margin-top:3px;">'
        'Connecte-toi pour rejoindre la communauté.</div></div>',
        unsafe_allow_html=True,
    )

    tab_login, tab_register = st.tabs(["🔑 Se connecter", "📝 Créer un compte"])

    with tab_login:
        with st.form("login_form"):
            email  = st.text_input("Email",        key="login_email")
            pwd    = st.text_input("Mot de passe", type="password", key="login_pwd")
            submit = st.form_submit_button("✅ Se connecter", use_container_width=True, type="primary")
        if submit:
            if not email or not pwd:
                st.error("Remplis tous les champs.")
            else:
                user = auth_login(email, pwd)
                if user:
                    st.success(f"Bienvenue {user['pseudo']} ! 🎣")
                    st.rerun()
                else:
                    st.error("Email ou mot de passe incorrect.")

    with tab_register:
        with st.form("register_form"):
            r_email  = st.text_input("Email",         key="reg_email")
            r_pseudo = st.text_input("Pseudo",         key="reg_pseudo", placeholder="Ex: JeromeCapFerret")
            r_pwd    = st.text_input("Mot de passe",  type="password", key="reg_pwd")
            r_pwd2   = st.text_input("Confirmer",     type="password", key="reg_pwd2")
            r_loc    = st.text_input("Ta région",     key="reg_loc", placeholder="Ex: Bassin d'Arcachon")
            r_submit = st.form_submit_button("🎣 Créer mon compte", use_container_width=True, type="primary")
        if r_submit:
            if not all([r_email, r_pseudo, r_pwd, r_pwd2]):
                st.error("Remplis tous les champs obligatoires.")
            elif r_pwd != r_pwd2:
                st.error("Les mots de passe ne correspondent pas.")
            elif len(r_pwd) < 6:
                st.error("Mot de passe trop court (6 caractères min).")
            else:
                result = auth_register(r_email, r_pseudo, r_pwd, r_loc)
                if result and "error" not in result:
                    st.success(f"Compte créé ! Bienvenue {r_pseudo} 🎣")
                    st.rerun()
                elif result and result.get("error") == "email_exists":
                    st.error("Un compte existe déjà avec cet email.")
                elif result and result.get("error") == "pseudo_exists":
                    st.error("Ce pseudo est déjà pris.")
                else:
                    st.error("Erreur lors de la création du compte.")
    return False
