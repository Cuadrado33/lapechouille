"""
Base de données — Supabase uniquement.
Toutes les fonctions load_*/insert_row/update_row/delete_row
passent par l'API REST Supabase.
"""
from __future__ import annotations
import pandas as pd
import requests
import streamlit as st
from pathlib import Path
from core.supabase_client import supabase_get, supabase_post, SUPABASE_URL, get_headers

# ── Dossiers photos locaux (compatibilité storage.py) ────────────
PHOTOS_DIR     = Path("photos_captures")
MATERIEL_DIR   = Path("photos_materiel")
MULTIMEDIA_DIR = Path("photos_multimedia")
SPOTS_DIR      = Path("photos_spots")
for _d in (PHOTOS_DIR, MATERIEL_DIR, MULTIMEDIA_DIR, SPOTS_DIR):
    _d.mkdir(exist_ok=True)

# ── Helper user_id ───────────────────────────────────────────────
def _uid() -> str | None:
    user = st.session_state.get("reseau_user")
    return user["id"] if user else None

# ── Chargement ───────────────────────────────────────────────────
@st.cache_data(ttl=30, show_spinner=False)
def _load_sessions_cached(uid: str) -> pd.DataFrame:
    rows = supabase_get("sessions", {"user_id": f"eq.{uid}", "order": "date_session.desc"})
    return pd.DataFrame(rows) if rows else pd.DataFrame()

def load_sessions() -> pd.DataFrame:
    uid = _uid()
    if not uid: return pd.DataFrame()
    return _load_sessions_cached(uid)

@st.cache_data(ttl=30, show_spinner=False)
def _load_captures_cached(uid: str) -> pd.DataFrame:
    rows = supabase_get("captures", {"user_id": f"eq.{uid}", "order": "created_at.desc"})
    return pd.DataFrame(rows) if rows else pd.DataFrame()

def load_captures() -> pd.DataFrame:
    uid = _uid()
    if not uid: return pd.DataFrame()
    return _load_captures_cached(uid)

def load_captures_for_session(session_id: int) -> pd.DataFrame:
    rows = supabase_get("captures", {
        "session_id": f"eq.{session_id}",
        "order": "capture_num.asc",
    })
    return pd.DataFrame(rows) if rows else pd.DataFrame()

@st.cache_data(ttl=30, show_spinner=False)
def _load_spots_cached(uid: str) -> pd.DataFrame:
    rows = supabase_get("spots", {"user_id": f"eq.{uid}", "order": "created_at.desc"})
    return pd.DataFrame(rows) if rows else pd.DataFrame()

def load_spots() -> pd.DataFrame:
    uid = _uid()
    if not uid: return pd.DataFrame()
    return _load_spots_cached(uid)

@st.cache_data(ttl=30, show_spinner=False)
def _load_bait_spots_cached(uid: str) -> pd.DataFrame:
    rows = supabase_get("bait_spots", {"user_id": f"eq.{uid}", "order": "created_at.desc"})
    return pd.DataFrame(rows) if rows else pd.DataFrame()

def load_bait_spots() -> pd.DataFrame:
    uid = _uid()
    if not uid: return pd.DataFrame()
    return _load_bait_spots_cached(uid)

@st.cache_data(ttl=30, show_spinner=False)
def load_materiel(categorie: str = None) -> pd.DataFrame:
    uid = _uid()
    if not uid: return pd.DataFrame()
    params = {"user_id": f"eq.{uid}", "order": "created_at.desc"}
    if categorie:
        params["categorie"] = f"ilike.*{categorie}*"
    rows = supabase_get("materiel", params)
    return pd.DataFrame(rows) if rows else pd.DataFrame()

@st.cache_data(ttl=30, show_spinner=False)
def _load_multimedia_cached(uid: str) -> pd.DataFrame:
    rows = supabase_get("multimedia", {"user_id": f"eq.{uid}", "order": "created_at.desc"})
    return pd.DataFrame(rows) if rows else pd.DataFrame()

def load_multimedia() -> pd.DataFrame:
    uid = _uid()
    if not uid: return pd.DataFrame()
    return _load_multimedia_cached(uid)

@st.cache_data(ttl=60, show_spinner=False)
def load_profil() -> dict:
    uid = _uid()
    if not uid: return {}
    rows = supabase_get("profils", {"id": f"eq.{uid}", "limit": "1"})
    return rows[0] if rows else {}

# ── Écriture ─────────────────────────────────────────────────────
def insert_row(table: str, data: dict) -> int | None:
    uid = _uid()
    if uid and "user_id" not in data:
        data["user_id"] = uid
    result = supabase_post(table, data)
    st.cache_data.clear()
    return result["id"] if result and "id" in result else None

def update_row(table: str, row_id: int, data: dict) -> bool:
    r = requests.patch(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=get_headers(),
        params={"id": f"eq.{row_id}"},
        json=data, timeout=10,
    )
    st.cache_data.clear()
    return r.status_code in (200, 204)

def delete_row(table: str, row_id: int) -> bool:
    r = requests.delete(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=get_headers(),
        params={"id": f"eq.{row_id}"},
        timeout=10,
    )
    st.cache_data.clear()
    return r.status_code in (200, 204)

def delete_capture(cap_id: int) -> bool:
    return delete_row("captures", cap_id)

def delete_session(sess_id: int) -> bool:
    return delete_row("sessions", sess_id)

def save_profil(data: dict) -> bool:
    uid = _uid()
    if not uid: return False
    # Utiliser PATCH pour mettre à jour sans conflit sur email/pseudo uniques
    data.pop("id", None)
    data.pop("email", None)      # Ne jamais modifier l'email via ce formulaire
    data.pop("mot_de_passe", None)  # Ne jamais modifier le mot de passe ici
    r = requests.patch(
        f"{SUPABASE_URL}/rest/v1/profils",
        headers={**get_headers(), "Prefer": "return=representation"},
        params={"id": f"eq.{uid}"},
        json=data,
        timeout=10,
    )
    if r.status_code not in (200, 204):
        import streamlit as _st
        _st.error(f"Erreur Supabase {r.status_code} : {r.text[:300]}")
        return False
    st.cache_data.clear()
    return True

def next_capture_number(session_id: int) -> int:
    rows = supabase_get("captures", {
        "session_id": f"eq.{session_id}",
        "select": "capture_num",
        "order": "capture_num.desc",
        "limit": "1",
    })
    if rows and rows[0].get("capture_num"):
        return int(rows[0]["capture_num"]) + 1
    return 1

def init_db() -> None:
    """Supabase : tables créées via SQL Editor. Rien à faire ici."""
    pass
