"""
Base de données — Supabase uniquement.
Toutes les fonctions load_*/insert_row/update_row/delete_row
passent par l'API REST Supabase.
"""
from __future__ import annotations
import pandas as pd
import streamlit as st
from core.supabase_client import supabase_get, supabase_post, supabase_patch, supabase_delete

# ── Helpers user_id ──────────────────────────────────────────────
def _uid() -> str | None:
    """Retourne le UUID Supabase de l'utilisateur connecté."""
    user = st.session_state.get("reseau_user")
    return user["id"] if user else None

def _uid_filter() -> dict:
    uid = _uid()
    return {"user_id": f"eq.{uid}"} if uid else {}

# ── Fonctions de chargement ──────────────────────────────────────
@st.cache_data(ttl=30, show_spinner=False)
def load_sessions() -> pd.DataFrame:
    uid = _uid()
    if not uid: return pd.DataFrame()
    rows = supabase_get("sessions", {"user_id": f"eq.{uid}", "order": "date_session.desc"})
    return pd.DataFrame(rows) if rows else pd.DataFrame()

@st.cache_data(ttl=30, show_spinner=False)
def load_captures() -> pd.DataFrame:
    uid = _uid()
    if not uid: return pd.DataFrame()
    rows = supabase_get("captures", {"user_id": f"eq.{uid}", "order": "created_at.desc"})
    return pd.DataFrame(rows) if rows else pd.DataFrame()

def load_captures_for_session(session_id: int) -> pd.DataFrame:
    rows = supabase_get("captures", {
        "session_id": f"eq.{session_id}",
        "order": "capture_num.asc",
    })
    return pd.DataFrame(rows) if rows else pd.DataFrame()

@st.cache_data(ttl=30, show_spinner=False)
def load_spots() -> pd.DataFrame:
    uid = _uid()
    if not uid: return pd.DataFrame()
    rows = supabase_get("spots", {"user_id": f"eq.{uid}", "order": "created_at.desc"})
    return pd.DataFrame(rows) if rows else pd.DataFrame()

@st.cache_data(ttl=30, show_spinner=False)
def load_bait_spots() -> pd.DataFrame:
    uid = _uid()
    if not uid: return pd.DataFrame()
    rows = supabase_get("bait_spots", {"user_id": f"eq.{uid}", "order": "created_at.desc"})
    return pd.DataFrame(rows) if rows else pd.DataFrame()

@st.cache_data(ttl=30, show_spinner=False)
def load_materiel() -> pd.DataFrame:
    uid = _uid()
    if not uid: return pd.DataFrame()
    rows = supabase_get("materiel", {"user_id": f"eq.{uid}", "order": "created_at.desc"})
    return pd.DataFrame(rows) if rows else pd.DataFrame()

@st.cache_data(ttl=30, show_spinner=False)
def load_multimedia() -> pd.DataFrame:
    uid = _uid()
    if not uid: return pd.DataFrame()
    rows = supabase_get("multimedia", {"user_id": f"eq.{uid}", "order": "created_at.desc"})
    return pd.DataFrame(rows) if rows else pd.DataFrame()

@st.cache_data(ttl=60, show_spinner=False)
def load_profil() -> dict:
    uid = _uid()
    if not uid: return {}
    rows = supabase_get("profils", {"id": f"eq.{uid}", "limit": "1"})
    return rows[0] if rows else {}

# ── Fonctions d'écriture ─────────────────────────────────────────
def insert_row(table: str, data: dict) -> int | None:
    uid = _uid()
    if uid and "user_id" not in data:
        data["user_id"] = uid
    result = supabase_post(table, data)
    st.cache_data.clear()
    return result["id"] if result and "id" in result else None

def update_row(table: str, row_id: int, data: dict) -> bool:
    import requests
    from core.supabase_client import SUPABASE_URL, get_headers
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    r = requests.patch(url, headers=get_headers(),
                       params={"id": f"eq.{row_id}"}, json=data, timeout=10)
    st.cache_data.clear()
    return r.status_code in (200, 204)

def delete_row(table: str, row_id: int) -> bool:
    import requests
    from core.supabase_client import SUPABASE_URL, get_headers
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    r = requests.delete(url, headers=get_headers(),
                        params={"id": f"eq.{row_id}"}, timeout=10)
    st.cache_data.clear()
    return r.status_code in (200, 204)

def delete_capture(cap_id: int) -> bool:
    return delete_row("captures", cap_id)

def delete_session(sess_id: int) -> bool:
    return delete_row("sessions", sess_id)

# ── Init DB (no-op pour Supabase) ────────────────────────────────
def init_db() -> None:
    """Supabase : tables créées via SQL Editor. Rien à faire ici."""
    pass
