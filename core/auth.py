"""
Authentification avec token persistant.
Le token est stocké dans Supabase et dans l'URL (?token=xxx).
Survit aux fermetures/réouvertures du navigateur tant que l'URL est bookmarkée.
"""
from __future__ import annotations
import hashlib, secrets, streamlit as st
from core.supabase_client import supabase_get, supabase_post


def _hash(pwd: str) -> str:
    return hashlib.sha256(pwd.encode()).hexdigest()


def _gen_token() -> str:
    return secrets.token_urlsafe(32)


def login(email: str, pwd: str) -> dict | None:
    """Vérifie les credentials et crée un token. Retourne le profil ou None."""
    rows = supabase_get("profils", {
        "email":        f"eq.{email.lower().strip()}",
        "mot_de_passe": f"eq.{_hash(pwd)}",
        "select":       "id,pseudo,email,avatar_url,bio,localisation,photo_path",
    })
    if not rows:
        return None
    user = rows[0]
    # Créer un token
    token = _gen_token()
    supabase_post("sessions_auth", {
        "token":   token,
        "user_id": user["id"],
    })
    # Stocker dans URL et session_state
    st.query_params["token"] = token
    st.session_state["reseau_user"]  = user
    st.session_state["auth_token"]   = token
    return user


def logout() -> None:
    """Supprime le token et la session."""
    token = st.session_state.get("auth_token")
    if token:
        from core.supabase_client import SUPABASE_URL, get_headers
        import requests
        requests.delete(
            f"{SUPABASE_URL}/rest/v1/sessions_auth",
            headers=get_headers(),
            params={"token": f"eq.{token}"},
            timeout=5,
        )
    st.session_state.pop("reseau_user", None)
    st.session_state.pop("auth_token", None)
    st.query_params.clear()


def restore_session() -> bool:
    """
    Restaure la session depuis le token dans l'URL.
    Appelé à chaque chargement de page.
    Retourne True si session restaurée.
    """
    # Déjà connecté
    if st.session_state.get("reseau_user"):
        return True

    token = st.query_params.get("token")
    if not token:
        return False

    # Vérifier le token dans Supabase
    rows = supabase_get("sessions_auth", {
        "token":  f"eq.{token}",
        "select": "user_id,expires_at",
        "limit":  "1",
    })
    if not rows:
        st.query_params.clear()
        return False

    sess = rows[0]
    # Vérifier expiration
    from datetime import datetime, timezone
    try:
        exp = datetime.fromisoformat(sess["expires_at"].replace("Z", "+00:00"))
        if exp < datetime.now(timezone.utc):
            st.query_params.clear()
            return False
    except Exception:
        pass

    # Charger le profil
    uid = sess["user_id"]
    profil = supabase_get("profils", {
        "id":     f"eq.{uid}",
        "select": "id,pseudo,email,avatar_url,bio,localisation,photo_path",
        "limit":  "1",
    })
    if not profil:
        return False

    st.session_state["reseau_user"] = profil[0]
    st.session_state["auth_token"]  = token
    return True


def register(email: str, pseudo: str, pwd: str, localisation: str = "") -> dict | None:
    """Crée un compte et retourne le profil ou None si erreur."""
    # Vérifier unicité
    if supabase_get("profils", {"email":  f"eq.{email.lower()}", "select": "id"}):
        return {"error": "email_exists"}
    if supabase_get("profils", {"pseudo": f"eq.{pseudo}",        "select": "id"}):
        return {"error": "pseudo_exists"}

    result = supabase_post("profils", {
        "email":        email.lower().strip(),
        "pseudo":       pseudo.strip(),
        "mot_de_passe": _hash(pwd),
        "localisation": localisation.strip() or None,
    })
    if not result:
        return None

    # Auto-login après inscription
    return login(email, pwd)
