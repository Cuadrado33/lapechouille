"""
Stockage des fichiers : photos de captures, matériel, multimédia.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from core.database import PHOTOS_DIR, MATERIEL_DIR, MULTIMEDIA_DIR, SPOTS_DIR


def _safe_filename_prefix(prefix: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", prefix).strip("_")
    return cleaned or "photo"


def save_uploaded_file(
    uploaded_file: Any,
    target_dir: Path,
    prefix: str,
) -> Optional[str]:
    """Enregistre un fichier image (camera_input ou file_uploader) sur disque."""
    if uploaded_file is None:
        return None

    suffix = Path(getattr(uploaded_file, "name", "photo.jpg")).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".jpg"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    safe_prefix = _safe_filename_prefix(prefix)
    target_dir.mkdir(parents=True, exist_ok=True)
    file_path = target_dir / f"{safe_prefix}_{timestamp}{suffix}"

    try:
        with open(file_path, "wb") as fh:
            fh.write(uploaded_file.getbuffer())
    except Exception:
        return None
    return str(file_path)


def save_capture_photo(uploaded_file: Any, capture_id: Optional[int] = None) -> Optional[str]:
    prefix = f"capture_{capture_id}" if capture_id is not None else "capture"
    return save_uploaded_file(uploaded_file, PHOTOS_DIR, prefix)


def save_materiel_photo(uploaded_file: Any, materiel_id: Optional[int], kind: str = "materiel") -> Optional[str]:
    prefix = f"{kind}_{materiel_id}" if materiel_id is not None else kind
    return save_uploaded_file(uploaded_file, MATERIEL_DIR, prefix)


def save_multimedia_photo(uploaded_file: Any, prefix: str = "multimedia") -> Optional[str]:
    return save_uploaded_file(uploaded_file, MULTIMEDIA_DIR, prefix)


def save_spot_photo(uploaded_file: Any, spot_id: Optional[int] = None) -> Optional[str]:
    prefix = f"spot_{spot_id}" if spot_id is not None else "spot"
    return save_uploaded_file(uploaded_file, SPOTS_DIR, prefix)
