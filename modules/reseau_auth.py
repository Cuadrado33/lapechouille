"""Authentification simple — inscription / connexion via Supabase."""
from __future__ import annotations
import hashlib, streamlit as st
from core.supabase_client import supabase_get, supabase_post

def _hash(pwd: str) -> str:
    return hashlib.sha256(pwd.encode()).hexdigest()

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
            email  = st.text_input("Email",       key="login_email")
            pwd    = st.text_input("Mot de passe", type="password", key="login_pwd")
            submit = st.form_submit_button("✅ Se connecter", use_container_width=True, type="primary")
        if submit:
            if not email or not pwd:
                st.error("Remplis tous les champs.")
            else:
                rows = supabase_get("profils", {
                    "email": f"eq.{email.lower().strip()}",
                    "select": "id,pseudo,email,avatar_url,bio,localisation",
                })
                if rows:
                    user = rows[0]
                    # Vérification mdp (stocké hashé)
                    pwd_check = supabase_get("profils", {
                        "id": f"eq.{user['id']}",
                        "mot_de_passe": f"eq.{_hash(pwd)}",
                        "select": "id",
                    })
                    if pwd_check:
                        st.session_state["reseau_user"] = user
                        st.success(f"Bienvenue {user['pseudo']} ! 🎣")
                        st.rerun()
                    else:
                        st.error("Mot de passe incorrect.")
                else:
                    st.error("Compte introuvable.")

    with tab_register:
        with st.form("register_form"):
            r_email  = st.text_input("Email",        key="reg_email")
            r_pseudo = st.text_input("Pseudo",        key="reg_pseudo", placeholder="Ex: JeromeCapFerret")
            r_pwd    = st.text_input("Mot de passe", type="password", key="reg_pwd")
            r_pwd2   = st.text_input("Confirmer",    type="password", key="reg_pwd2")
            r_loc    = st.text_input("Ta région",    key="reg_loc",    placeholder="Ex: Bassin d'Arcachon")
            r_submit = st.form_submit_button("🎣 Créer mon compte", use_container_width=True, type="primary")
        if r_submit:
            if not all([r_email, r_pseudo, r_pwd, r_pwd2]):
                st.error("Remplis tous les champs obligatoires.")
            elif r_pwd != r_pwd2:
                st.error("Les mots de passe ne correspondent pas.")
            elif len(r_pwd) < 6:
                st.error("Mot de passe trop court (6 caractères min).")
            else:
                # Vérifier unicité
                exists = supabase_get("profils", {"email": f"eq.{r_email.lower().strip()}", "select": "id"})
                pseudo_exists = supabase_get("profils", {"pseudo": f"eq.{r_pseudo.strip()}", "select": "id"})
                if exists:
                    st.error("Un compte existe déjà avec cet email.")
                elif pseudo_exists:
                    st.error("Ce pseudo est déjà pris.")
                else:
                    new_user = supabase_post("profils", {
                        "email":         r_email.lower().strip(),
                        "pseudo":        r_pseudo.strip(),
                        "mot_de_passe":  _hash(r_pwd),
                        "localisation":  r_loc.strip(),
                    })
                    if new_user:
                        st.session_state["reseau_user"] = new_user
                        st.success(f"Compte créé ! Bienvenue {r_pseudo} 🎣")
                        st.rerun()
                    else:
                        st.error("Erreur lors de la création du compte. Réessaie.")
    return False
