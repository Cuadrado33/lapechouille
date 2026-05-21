"""
Utilitaires généraux : conversion sûre, formatage de dates, calculs.
"""

from __future__ import annotations

import math
import re
from datetime import date, datetime, time, timedelta
from typing import Any, Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Conversions sûres
# ---------------------------------------------------------------------------

def safe_float(value: Any, default: float = 0.0) -> float:
    """Convertit une valeur en float sans crasher sur NaN/None."""
    try:
        if value is None:
            return default
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Convertit une valeur en int sans crasher."""
    try:
        if value is None:
            return default
        if pd.isna(value):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def safe_str(value: Any, default: str = "") -> str:
    """Convertit une valeur en str, en gérant NaN."""
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass
    return str(value)


def list_index(options: list, value: Any, default: int = 0) -> int:
    """Retourne l'index sûr d'une valeur dans une liste pour st.selectbox."""
    if value in options:
        return options.index(value)
    return default


# ---------------------------------------------------------------------------
# Formatage de dates
# ---------------------------------------------------------------------------

def format_date_fr(value: Any) -> str:
    """Affiche une date en JJ/MM/AAAA, quel que soit le format stocké."""
    raw = safe_str(value)
    if not raw:
        return ""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw[:19], fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    try:
        parsed = pd.to_datetime(raw, errors="coerce")
        if pd.notna(parsed):
            return parsed.strftime("%d/%m/%Y")
    except Exception:
        pass
    return raw


def parse_date_safe(value: Any, default: Optional[date] = None) -> date:
    """Convertit une valeur en date, retourne aujourd'hui par défaut."""
    if default is None:
        default = date.today()
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    raw = safe_str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw[:10], fmt).date()
        except ValueError:
            continue
    return default


def parse_time_safe(value: Any, default: Optional[time] = None) -> time:
    """Convertit une valeur HH:MM en time, retourne le default sinon."""
    if default is None:
        default = time(0, 0)
    if isinstance(value, time):
        return value
    raw = safe_str(value).strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(raw[:8], fmt).time()
        except ValueError:
            continue
    return default


def format_dataframe_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Convertit toutes les colonnes contenant 'date' en JJ/MM/AAAA pour l'affichage."""
    if df is None or df.empty:
        return df
    display_df = df.copy()
    for col in display_df.columns:
        col_lower = col.lower()
        if "date" in col_lower and "updated" not in col_lower and "created" not in col_lower:
            display_df[col] = display_df[col].apply(format_date_fr)
    return display_df


def compute_duration_hours(start: time, end: time) -> float:
    """Calcule une durée en heures entre deux time. Gère le passage à minuit."""
    start_dt = datetime.combine(date.today(), start)
    end_dt = datetime.combine(date.today(), end)
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)
    return round((end_dt - start_dt).total_seconds() / 3600, 2)


def format_duration(total_seconds: float) -> str:
    """Formate une durée en secondes : '3h45'."""
    try:
        total_seconds = max(0, int(total_seconds))
    except (TypeError, ValueError):
        return "—"
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours}h{minutes:02d}"


# ---------------------------------------------------------------------------
# Calculs géographiques et physiques
# ---------------------------------------------------------------------------

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance orthodromique en km entre deux points GPS."""
    radius_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_km * c


def wind_direction_cardinal(degrees: Any) -> str:
    """Convertit un cap en degrés en libellé cardinal lisible."""
    try:
        deg = float(degrees) % 360
    except (TypeError, ValueError):
        return "—"
    directions = [
        "Nord", "Nord-Nord-Est", "Nord-Est", "Est-Nord-Est",
        "Est", "Est-Sud-Est", "Sud-Est", "Sud-Sud-Est",
        "Sud", "Sud-Sud-Ouest", "Sud-Ouest", "Ouest-Sud-Ouest",
        "Ouest", "Ouest-Nord-Ouest", "Nord-Ouest", "Nord-Nord-Ouest",
    ]
    index = int((deg + 11.25) // 22.5) % 16
    return f"{directions[index]} ({deg:.0f}°)"


# ---------------------------------------------------------------------------
# Estimations halieutiques
# ---------------------------------------------------------------------------

def estimate_fish_weight_g(espece: Any, taille_cm: Any) -> Optional[float]:
    """
    Estime un poids indicatif d'un poisson à partir de son espèce et de sa taille.

    Formule : W(g) ≈ K × L(cm)^3 / 100.
    Les coefficients sont indicatifs : utile uniquement pour pré-remplir
    une capture non pesée.
    """
    length = safe_float(taille_cm)
    if length <= 0:
        return None

    name = safe_str(espece).lower()
    coefficients = [
        (["bar", "loup", "lieu", "maigre", "bonite", "pélamide", "pelamide",
          "maquereau", "chinchard", "orphie"], 1.05),
        (["daurade", "dorade", "sar", "marbré", "marbre", "oblade", "saupe", "bogue"], 1.45),
        (["mulet", "muge"], 1.25),
        (["sole", "plie", "flet", "limande", "turbot", "barbue"], 0.85),
        (["congre", "murène", "murene", "anguille"], 0.18),
        (["raie", "torpille"], 2.10),
        (["rouget", "grondin", "rascasse", "serran", "tacaud", "merlan", "mostelle"], 1.20),
        (["requin", "roussette", "émissole", "emissole", "aiguillat"], 0.75),
        (["baliste"], 1.65),
    ]

    k_value = 1.0
    for keywords, coefficient in coefficients:
        if any(kw in name for kw in keywords):
            k_value = coefficient
            break

    return round(k_value * (length ** 3) / 100, 0)


def format_weight_display(row_or_dict: Any) -> str:
    """Affiche un poids : mesuré si présent, estimé sinon."""
    try:
        get = row_or_dict.get
    except AttributeError:
        def get(k, d=None):
            return getattr(row_or_dict, k, d)

    measured = safe_float(get("poids_g"))
    estimated = safe_float(get("poids_estime_g"))
    espece = get("espece")
    taille = get("taille_cm")

    if measured > 0:
        if measured >= 1000:
            return f"{measured/1000:.2f} kg"
        return f"{measured:.0f} g"
    if estimated <= 0:
        estimated = safe_float(estimate_fish_weight_g(espece, taille))
    if estimated > 0:
        if estimated >= 1000:
            return f"≈ {estimated/1000:.2f} kg estimé"
        return f"≈ {estimated:.0f} g estimé"
    return "—"


# ---------------------------------------------------------------------------
# Résistance des fils (indicatif)
# ---------------------------------------------------------------------------

RESISTANCE_NYLON_KG = {
    6: 0.7, 7: 0.9, 8: 1.1, 9: 1.3, 10: 1.5, 11: 1.8, 12: 2.0, 13: 2.3, 14: 2.6,
    15: 3.0, 16: 3.3, 17: 3.6, 18: 4.0, 19: 4.4, 20: 4.8, 22: 5.7, 24: 6.7,
    25: 7.2, 26: 7.8, 28: 8.9, 30: 10.0, 32: 11.2, 35: 13.0, 40: 16.5, 45: 20.5,
    50: 25.0, 55: 30.0, 60: 35.0, 70: 46.0, 80: 58.0, 90: 70.0, 100: 82.0,
}

RESISTANCE_TRESSE_KG = {
    6: 4.0, 8: 6.0, 10: 8.0, 12: 10.0, 14: 12.0, 16: 15.0, 18: 18.0, 20: 21.0,
    22: 24.0, 24: 27.0, 25: 29.0, 28: 35.0, 30: 39.0, 35: 50.0, 40: 60.0,
    45: 68.0, 50: 75.0, 60: 92.0, 70: 110.0, 80: 130.0, 100: 170.0,
}


def extract_diameter_centiemes(value: Any) -> Optional[int]:
    """Extrait le diamètre en centièmes depuis '30/100' ou '0.30 mm'."""
    text = safe_str(value).strip().lower().replace(" ", "")
    if not text or text == "autre":
        return None
    if "/100" in text:
        text = text.split("/100")[0]
    elif "mm" in text and "." in text:
        try:
            return int(round(float(text.replace("mm", "")) * 100))
        except ValueError:
            pass
    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def _interpolate_table(table: dict, diameter: int) -> Optional[float]:
    """Interpole entre deux clés connues d'une table de résistance."""
    if diameter in table:
        return table[diameter]
    keys = sorted(table.keys())
    if not keys or diameter < keys[0] or diameter > keys[-1]:
        return None
    lower = max(k for k in keys if k < diameter)
    upper = min(k for k in keys if k > diameter)
    ratio = (diameter - lower) / (upper - lower)
    return round(table[lower] + (table[upper] - table[lower]) * ratio, 1)


def estimate_line_resistance_kg(type_fil: Any, diametre: Any) -> Optional[float]:
    """Renvoie la résistance moyenne en kg selon type et diamètre."""
    diameter = extract_diameter_centiemes(diametre)
    if diameter is None:
        return None
    type_text = safe_str(type_fil).strip().lower()
    if "tresse" in type_text:
        return _interpolate_table(RESISTANCE_TRESSE_KG, diameter)
    if "fluoro" in type_text:
        # Fluorocarbone : ~90% de la résistance nylon à diamètre égal
        base = _interpolate_table(RESISTANCE_NYLON_KG, diameter)
        return round(base * 0.90, 2) if base else None
    if any(kw in type_text for kw in ["nylon", "mono"]):
        return _interpolate_table(RESISTANCE_NYLON_KG, diameter)
    return None


def line_resistance_interval(type_fil: Any, diametre: Any) -> Optional[tuple[float, float]]:
    """Retourne un intervalle indicatif de résistance ±15% (nylon/fluoro) ou ±20% (tresse)."""
    average = estimate_line_resistance_kg(type_fil, diametre)
    if average is None:
        return None
    type_text = safe_str(type_fil).strip().lower()
    spread = 0.20 if "tresse" in type_text else 0.15
    return (round(max(0.1, average * (1 - spread)), 1), round(average * (1 + spread), 1))


def format_resistance(type_fil: Any, diametre: Any) -> str:
    interval = line_resistance_interval(type_fil, diametre)
    if interval is None:
        return "—"
    low, high = interval
    return f"{low:.1f} à {high:.1f} kg"


# ---------------------------------------------------------------------------
# Slug & sanitization
# ---------------------------------------------------------------------------

def slugify(value: str, max_length: int = 60) -> str:
    """Transforme une chaîne en identifiant simple, sans caractères spéciaux."""
    text = safe_str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = text.strip("_")
    return text[:max_length] or "item"
