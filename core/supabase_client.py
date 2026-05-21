"""
Client Supabase pour La Péchouille.
Lit les credentials depuis st.secrets (Streamlit Cloud)
ou depuis les variables d'environnement (local).
"""
from __future__ import annotations
import os
import streamlit as st

# ── Credentials ────────────────────────────────────────────────
def _get_creds() -> tuple[str, str]:
    """Retourne (url, anon_key) depuis secrets ou env."""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_ANON_KEY"]
        return url, key
    except Exception:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_ANON_KEY", "")
        return url, key

SUPABASE_URL     = "https://popejsluexmcicjmfcwc.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBvcGVqc2x1ZXhtY2ljam1mY3djIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzkzODE4MzYsImV4cCI6MjA5NDk1NzgzNn0.5c7JW91xPFRbvAO7zi9-pfwj_m0cUQQCGs0fzU6I7I0"

def get_headers() -> dict:
    return {
        "apikey":        SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "return=representation",
    }

def supabase_get(table: str, params: dict = None) -> list:
    """GET sur une table Supabase."""
    import requests
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    try:
        r = requests.get(url, headers=get_headers(), params=params, timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return []

def supabase_post(table: str, data: dict) -> dict | None:
    """INSERT dans une table Supabase."""
    import requests
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    try:
        r = requests.post(url, headers=get_headers(), json=data, timeout=8)
        r.raise_for_status()
        result = r.json()
        return result[0] if isinstance(result, list) and result else result
    except Exception as e:
        return None

def supabase_patch(table: str, row_id: str, data: dict) -> bool:
    """UPDATE sur une ligne Supabase."""
    import requests
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    try:
        r = requests.patch(url, headers=get_headers(),
                           params={"id": f"eq.{row_id}"}, json=data, timeout=8)
        r.raise_for_status()
        return True
    except Exception:
        return False

def supabase_delete(table: str, row_id: str) -> bool:
    """DELETE sur une ligne Supabase."""
    import requests
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    try:
        r = requests.delete(url, headers=get_headers(),
                            params={"id": f"eq.{row_id}"}, timeout=8)
        r.raise_for_status()
        return True
    except Exception:
        return False

def supabase_rpc(function_name: str, params: dict = None) -> any:
    """Appel d'une fonction RPC Supabase."""
    import requests
    url = f"{SUPABASE_URL}/rest/v1/rpc/{function_name}"
    try:
        r = requests.post(url, headers=get_headers(), json=params or {}, timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None
