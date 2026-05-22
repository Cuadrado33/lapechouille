"""
Stockage des fichiers — Supabase Storage.
Toutes les photos sont uploadées dans le bucket 'photos' de Supabase.
Retourne une URL publique accessible depuis n'importe où.
"""
from __future__ import annotations

import re
import requests
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from core.database import PHOTOS_DIR, MATERIEL_DIR, MULTIMEDIA_DIR, SPOTS_DIR
from core.supabase_client import SUPABASE_URL, get_headers


def _safe_prefix(prefix: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", prefix).strip("_") or "photo"


def _upload_to_supabase(uploaded_file: Any, folder: str, prefix: str) -> Optional[str]:
    """Upload un fichier vers Supabase Storage. Retourne l'URL publique."""
    if uploaded_file is None:
        return None

    suffix = Path(getattr(uploaded_file, "name", "photo.jpg")).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".jpg"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    filename  = f"{_safe_prefix(prefix)}_{timestamp}{suffix}"
    dest_path = f"{folder}/{filename}"

    mime = "image/jpeg" if suffix in (".jpg", ".jpeg") else f"image/{suffix.lstrip('.')}"

    hdrs = {
        "apikey":        get_headers()["apikey"],
        "Authorization": get_headers()["Authorization"],
        "Content-Type":  mime,
    }

    try:
        data = uploaded_file.getbuffer()
        url  = f"{SUPABASE_URL}/storage/v1/object/photos/{dest_path}"
        r    = requests.post(url, headers=hdrs, data=bytes(data), timeout=30)
        if r.status_code in (200, 201):
            return f"{SUPABASE_URL}/storage/v1/object/public/photos/{dest_path}"
        else:
            import streamlit as st
            st.error(f"❌ Upload photo échoué : {r.status_code} — {r.text[:200]}")
            return None
    except Exception as e:
        import streamlit as st
        st.error(f"❌ Erreur upload photo : {e}")
        return None


def _save_local(uploaded_file: Any, folder: str, filename: str) -> Optional[str]:
    """Fallback : sauvegarde locale."""
    try:
        p = Path(folder)
        p.mkdir(parents=True, exist_ok=True)
        file_path = p / filename
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return str(file_path)
    except Exception:
        return None


# ── Fonctions publiques ──────────────────────────────────────────
def save_capture_photo(uploaded_file: Any, capture_id: Optional[int] = None) -> Optional[str]:
    prefix = f"capture_{capture_id}" if capture_id is not None else "capture"
    return _upload_to_supabase(uploaded_file, "captures", prefix)


def save_materiel_photo(uploaded_file: Any, materiel_id: Optional[int], kind: str = "materiel") -> Optional[str]:
    prefix = f"{kind}_{materiel_id}" if materiel_id is not None else kind
    return _upload_to_supabase(uploaded_file, "materiel", prefix)


def save_multimedia_photo(uploaded_file: Any, prefix: str = "multimedia") -> Optional[str]:
    return _upload_to_supabase(uploaded_file, "multimedia", prefix)


def save_spot_photo(uploaded_file: Any, spot_id: Optional[int] = None) -> Optional[str]:
    prefix = f"spot_{spot_id}" if spot_id is not None else "spot"
    return _upload_to_supabase(uploaded_file, "spots", prefix)


def save_uploaded_file(uploaded_file: Any, target_dir: Path, prefix: str) -> Optional[str]:
    """Compatibilité ancienne API — redirige vers Supabase Storage."""
    folder = str(target_dir).replace("\\", "/")
    return _upload_to_supabase(uploaded_file, folder, prefix)
