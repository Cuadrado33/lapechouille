"""
Intégrations API externes :
- Open-Meteo (météo et marine)
- Nominatim (géocodage OpenStreetMap)
- Overpass (POI à proximité)

Toutes les requêtes incluent timeout et user-agent.
"""

from __future__ import annotations

import math
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, Optional

import pandas as pd
import requests
import streamlit as st

from core.utils import safe_float, safe_str, haversine_km


USER_AGENT = "CarnetSurfcasting/2.0"
DEFAULT_TIMEOUT = 15

# Fix Windows PermissionError(13) : requests tente d'écrire un fichier
# temporaire pour le cache SSL → on désactive la vérification SSL
# (les données météo publiques ne nécessitent pas de vérification stricte)
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
_SSL_VERIFY = False


# ---------------------------------------------------------------------------
# Helper API générique
# ---------------------------------------------------------------------------

def _api_get(url: str, params: Dict[str, Any], timeout: int = DEFAULT_TIMEOUT,
              max_retries: int = 3) -> Optional[Dict[str, Any]]:
    """Appel GET JSON sécurisé avec timeout, headers anti-cache, fix SSL Windows
    et retry automatique sur erreurs 5xx serveur."""
    import time
    last_exc = None
    for attempt in range(max_retries):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=timeout,
                verify=_SSL_VERIFY,
                headers={
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                    "User-Agent": USER_AGENT,
                },
            )
            # Retry sur les erreurs serveur (502, 503, 504...)
            if 500 <= response.status_code < 600:
                last_exc = f"Serveur {response.status_code}"
                if attempt < max_retries - 1:
                    time.sleep(1.5 * (attempt + 1))  # backoff : 1.5s, 3s
                    continue
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                time.sleep(1.5 * (attempt + 1))
                continue

    # Message clair selon le type d'erreur
    msg = str(last_exc)
    if "502" in msg or "503" in msg or "504" in msg:
        st.info("🌐 Service météo temporairement indisponible (serveur en surcharge). "
                 "Réessaie dans quelques minutes.")
    elif "timeout" in msg.lower() or "connection" in msg.lower():
        st.info("🌐 Pas de connexion au service météo. Vérifie ta connexion internet.")
    else:
        st.info(f"🌐 Données météo indisponibles ({msg[:80]}).")
    return None


# ---------------------------------------------------------------------------
# Géocodage : Nominatim
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def reverse_geocode(latitude: float, longitude: float) -> Dict[str, Any]:
    """Retourne l'adresse approximative d'un point GPS."""
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": latitude,
        "lon": longitude,
        "format": "json",
        "addressdetails": 1,
        "zoom": 16,
    }
    try:
        response = requests.get(
            url, params=params, headers={"User-Agent": USER_AGENT},
            timeout=DEFAULT_TIMEOUT, verify=_SSL_VERIFY
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return {}


@st.cache_data(ttl=3600, show_spinner=False)
def geocode_address(address_query: str) -> Optional[Dict[str, Any]]:
    """Géocode une adresse → premier résultat."""
    query = safe_str(address_query).strip()
    if len(query) < 3:
        return None
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": query, "format": "json", "addressdetails": 1, "limit": 1}
    try:
        response = requests.get(
            url, params=params, headers={"User-Agent": USER_AGENT},
            timeout=DEFAULT_TIMEOUT, verify=_SSL_VERIFY
        )
        response.raise_for_status()
        results = response.json()
    except requests.RequestException:
        return None
    if not results:
        return None
    r = results[0]
    return {
        "latitude": float(r["lat"]),
        "longitude": float(r["lon"]),
        "display_name": r.get("display_name", query),
        "address": r.get("address", {}),
    }


@st.cache_data(ttl=3600, show_spinner=False)
def geocode_candidates(address_query: str, limit: int = 5) -> list[Dict[str, Any]]:
    """Renvoie plusieurs adresses candidates."""
    query = safe_str(address_query).strip()
    if len(query) < 4:
        return []
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": query, "format": "json", "addressdetails": 1, "limit": int(limit)}
    try:
        response = requests.get(
            url, params=params, headers={"User-Agent": USER_AGENT},
            timeout=DEFAULT_TIMEOUT, verify=_SSL_VERIFY
        )
        response.raise_for_status()
        results = response.json()
    except requests.RequestException:
        return []
    out = []
    for r in results:
        try:
            out.append({
                "latitude": float(r["lat"]),
                "longitude": float(r["lon"]),
                "display_name": r.get("display_name", query),
                "address": r.get("address", {}),
            })
        except (KeyError, TypeError, ValueError):
            continue
    return out


# ---------------------------------------------------------------------------
# POI Overpass : magasins de pêche
# ---------------------------------------------------------------------------

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_fishing_shops(latitude: float, longitude: float, radius_m: int = 20000) -> pd.DataFrame:
    """Trouve les magasins de pêche autour d'un point GPS via Overpass."""
    url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json][timeout:25];
    (
      node["shop"="fishing"](around:{radius_m},{latitude},{longitude});
      way["shop"="fishing"](around:{radius_m},{latitude},{longitude});
      node["name"~"pêche|peche|fishing|pesc", i](around:{radius_m},{latitude},{longitude});
    );
    out center tags;
    """
    try:
        response = requests.post(url, data={"data": query}, timeout=30, verify=_SSL_VERIFY)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return pd.DataFrame()

    shops = []
    for element in data.get("elements", []):
        tags = element.get("tags", {})
        lat = element.get("lat") or element.get("center", {}).get("lat")
        lon = element.get("lon") or element.get("center", {}).get("lon")
        if lat is None or lon is None:
            continue
        addr_parts = [
            tags.get("addr:housenumber"),
            tags.get("addr:street"),
            tags.get("addr:postcode"),
            tags.get("addr:city"),
        ]
        shops.append({
            "Nom": tags.get("name", "Magasin de pêche"),
            "Distance km": round(haversine_km(latitude, longitude, lat, lon), 2),
            "Adresse": " ".join([p for p in addr_parts if p]) or "Adresse non renseignée",
            "Latitude": lat,
            "Longitude": lon,
        })
    if not shops:
        return pd.DataFrame()
    return (
        pd.DataFrame(shops)
        .drop_duplicates(subset=["Nom", "Latitude", "Longitude"])
        .sort_values("Distance km")
        .head(15)
    )


# ---------------------------------------------------------------------------
# Open-Meteo : météo et marine
# ---------------------------------------------------------------------------

def _within_forecast_window(target: date) -> bool:
    """Open-Meteo forecast accepte une fenêtre courte autour d'aujourd'hui."""
    today = date.today()
    return today - timedelta(days=92) <= target <= today + timedelta(days=15)


@st.cache_data(ttl=600, show_spinner=False)
def fetch_weather(
    latitude: float,
    longitude: float,
    target_date: str,
) -> Optional[pd.DataFrame]:
    """Météo horaire pour une date donnée. Utilise l'API archive pour dates anciennes."""
    try:
        target = datetime.strptime(target_date, "%Y-%m-%d").date()
    except ValueError:
        return None

    today = date.today()
    # Si date trop ancienne (>92 jours), utiliser l'API archive
    if target < today - timedelta(days=92):
        url = "https://archive-api.open-meteo.com/v1/archive"
    elif target > today + timedelta(days=15):
        # Date trop loin dans le futur, hors fenêtre prévision
        return None
    else:
        url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": (
            "temperature_2m,apparent_temperature,relative_humidity_2m,pressure_msl,cloud_cover,weather_code,"
            "precipitation,rain,"
            "wind_speed_10m,wind_direction_10m,wind_gusts_10m"
        ),
        "start_date": target_date,
        "end_date": target_date,
        "timezone": "auto",
    }
    # precipitation_probability n'existe pas dans l'API archive
    if "forecast" in url:
        params["hourly"] = params["hourly"].replace(
            "precipitation,rain,", "precipitation_probability,precipitation,rain,"
        )
    data = _api_get(url, params)
    if not data or "hourly" not in data:
        return None
    return pd.DataFrame(data["hourly"])


@st.cache_data(ttl=600, show_spinner=False)
def fetch_weather_range(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
) -> Optional[pd.DataFrame]:
    """Météo horaire sur une plage."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": (
            "temperature_2m,apparent_temperature,relative_humidity_2m,pressure_msl,cloud_cover,weather_code,"
            "precipitation_probability,precipitation,rain,"
            "wind_speed_10m,wind_direction_10m,wind_gusts_10m"
        ),
        "start_date": start_date,
        "end_date": end_date,
        "timezone": "auto",
    }
    data = _api_get(url, params)
    if not data or "hourly" not in data:
        return None
    return pd.DataFrame(data["hourly"])


@st.cache_data(ttl=600, show_spinner=False)
def fetch_marine(
    latitude: float,
    longitude: float,
    target_date: str,
) -> Optional[pd.DataFrame]:
    """Données marines horaires pour une date."""
    try:
        target = datetime.strptime(target_date, "%Y-%m-%d").date()
    except ValueError:
        return None
    # L'API marine ne couvre pas les archives anciennes
    today = date.today()
    if target < today - timedelta(days=92) or target > today + timedelta(days=15):
        return None

    url = "https://marine-api.open-meteo.com/v1/marine"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "wave_height,wave_direction,wave_period,sea_surface_temperature",
        "start_date": target_date,
        "end_date": target_date,
        "timezone": "auto",
    }
    data = _api_get(url, params)
    if not data or "hourly" not in data:
        return None
    return pd.DataFrame(data["hourly"])


@st.cache_data(ttl=600, show_spinner=False)
def fetch_marine_range(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
) -> Optional[pd.DataFrame]:
    url = "https://marine-api.open-meteo.com/v1/marine"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "wave_height,wave_direction,wave_period,sea_surface_temperature",
        "start_date": start_date,
        "end_date": end_date,
        "timezone": "auto",
    }
    data = _api_get(url, params)
    if not data or "hourly" not in data:
        return None
    return pd.DataFrame(data["hourly"])


# ---------------------------------------------------------------------------
# Calculs astronomiques (lune, soleil)
# ---------------------------------------------------------------------------

def calculate_moon_phase(target_dt: datetime) -> Dict[str, Any]:
    """Phase lunaire approximative (algorithme âge moyen)."""
    known_new_moon = datetime(2000, 1, 6, 18, 14)
    synodic = 29.53058867
    days_since = (target_dt - known_new_moon).total_seconds() / 86400
    moon_age = days_since % synodic
    illumination = round((1 - math.cos(2 * math.pi * moon_age / synodic)) / 2 * 100, 1)

    phases = [
        (1.84566, "Nouvelle lune", "🌑"),
        (5.53699, "Premier croissant", "🌒"),
        (9.22831, "Premier quartier", "🌓"),
        (12.91963, "Lune gibbeuse croissante", "🌔"),
        (16.61096, "Pleine lune", "🌕"),
        (20.30228, "Lune gibbeuse décroissante", "🌖"),
        (23.99361, "Dernier quartier", "🌗"),
        (27.68493, "Dernier croissant", "🌘"),
        (synodic, "Nouvelle lune", "🌑"),
    ]
    for limit, label, icon in phases:
        if moon_age < limit:
            return {"label": label, "icon": icon, "age": round(moon_age, 1), "illumination": illumination}
    return {"label": "Nouvelle lune", "icon": "🌑", "age": round(moon_age, 1), "illumination": illumination}


def _solar_event_utc_hours(latitude: float, longitude: float, day: date, event: str) -> Optional[float]:
    """Calcule l'heure UTC d'un lever/coucher de soleil (algorithme NOAA simplifié)."""
    zenith = 90.833
    n = day.timetuple().tm_yday
    lng_hour = longitude / 15.0
    t = n + ((6 if event == "sunrise" else 18) - lng_hour) / 24

    mean_anomaly = (0.9856 * t) - 3.289
    true_long = (
        mean_anomaly
        + 1.916 * math.sin(math.radians(mean_anomaly))
        + 0.020 * math.sin(math.radians(2 * mean_anomaly))
        + 282.634
    ) % 360
    ra = math.degrees(math.atan(0.91764 * math.tan(math.radians(true_long)))) % 360
    l_quad = math.floor(true_long / 90) * 90
    ra_quad = math.floor(ra / 90) * 90
    ra = (ra + (l_quad - ra_quad)) / 15

    sin_dec = 0.39782 * math.sin(math.radians(true_long))
    cos_dec = math.cos(math.asin(sin_dec))
    cos_h = (math.cos(math.radians(zenith)) - sin_dec * math.sin(math.radians(latitude))) / (
        cos_dec * math.cos(math.radians(latitude))
    )
    if cos_h > 1 or cos_h < -1:
        return None

    if event == "sunrise":
        h = 360 - math.degrees(math.acos(cos_h))
    else:
        h = math.degrees(math.acos(cos_h))
    h /= 15
    local_mean = h + ra - (0.06571 * t) - 6.622
    return (local_mean - lng_hour) % 24


def _last_sunday(year: int, month: int) -> date:
    d = date(year, month, 31)
    while d.weekday() != 6:
        d -= timedelta(days=1)
    return d


def estimate_timezone_offset(latitude: float, longitude: float, day: date) -> int:
    """Estime le décalage horaire en heures (Europe : DST automatique)."""
    if -12 <= longitude <= 35 and 34 <= latitude <= 72:
        dst_start = _last_sunday(day.year, 3)
        dst_end = _last_sunday(day.year, 10)
        return 2 if dst_start <= day < dst_end else 1
    return int(round(longitude / 15.0))


def fetch_sun_events(latitude: float, longitude: float, start_date: str, end_date: str) -> pd.DataFrame:
    """Calcule lever/coucher du soleil sur une plage de dates."""
    try:
        start = datetime.fromisoformat(start_date).date()
        end = datetime.fromisoformat(end_date).date()
    except ValueError:
        return pd.DataFrame()

    rows = []
    cur = start
    while cur <= end:
        offset = estimate_timezone_offset(latitude, longitude, cur)
        sr = _solar_event_utc_hours(latitude, longitude, cur, "sunrise")
        ss = _solar_event_utc_hours(latitude, longitude, cur, "sunset")
        if sr is None or ss is None:
            cur += timedelta(days=1)
            continue

        sr_min = int(round(sr * 60)) + offset * 60
        ss_min = int(round(ss * 60)) + offset * 60
        sr_day = cur + timedelta(days=sr_min // (24 * 60))
        ss_day = cur + timedelta(days=ss_min // (24 * 60))
        sr_dt = datetime.combine(sr_day, time((sr_min % (24 * 60)) // 60, (sr_min % (24 * 60)) % 60))
        ss_dt = datetime.combine(ss_day, time((ss_min % (24 * 60)) // 60, (ss_min % (24 * 60)) % 60))
        if ss_dt <= sr_dt:
            ss_dt += timedelta(days=1)

        delta = ss_dt - sr_dt
        h = int(delta.total_seconds()) // 3600
        m = (int(delta.total_seconds()) % 3600) // 60
        rows.append({
            "date": cur,
            "lever_dt": sr_dt,
            "coucher_dt": ss_dt,
            "lever": sr_dt.strftime("%H:%M"),
            "coucher": ss_dt.strftime("%H:%M"),
            "duree": f"{h}h{m:02d}",
            "duree_h": round(delta.total_seconds() / 3600, 2),
        })
        cur += timedelta(days=1)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Estimation marée indicative (sans API officielle)
# ---------------------------------------------------------------------------

def estimate_tide(
    tide_date: date,
    reference_time: time,
    latitude: float,
    longitude: float,
) -> Dict[str, Any]:
    """
    Pré-saisie indicative de marée à défaut d'API SHOM.

    Approximation semi-diurne basée sur :
    - le cycle lunaire (coefficient lié à l'âge de la lune) ;
    - une correction de longitude basique.

    À considérer comme un brouillon, à confirmer par les marégrammes officiels.
    """
    current_dt = datetime.combine(tide_date, reference_time)
    known_new_moon = datetime(2000, 1, 6, 18, 14)
    synodic = 29.53058867
    tide_cycle = timedelta(hours=12, minutes=25)

    days_since = (current_dt - known_new_moon).total_seconds() / 86400
    moon_age = days_since % synodic
    spring_neap = abs(math.cos(2 * math.pi * moon_age / synodic))
    coefficient = max(20, min(120, int(round(38 + 62 * spring_neap))))

    # Heure de référence de pleine mer (approximative)
    reference_high = datetime(2026, 1, 1, 6, 0)
    longitude_correction = int(round((longitude + 1.2) * 4))
    reference_high += timedelta(minutes=longitude_correction)

    elapsed = (current_dt - reference_high).total_seconds()
    cycles = round(elapsed / tide_cycle.total_seconds())
    nearest_high = reference_high + cycles * tide_cycle

    candidates_high = [nearest_high + i * tide_cycle for i in range(-2, 3)]
    high_dt = min(candidates_high, key=lambda dt: abs((dt - current_dt).total_seconds()))
    low_dt = high_dt + timedelta(hours=6, minutes=12)
    candidates_low = [low_dt + i * tide_cycle for i in range(-2, 3)]
    low_dt = min(candidates_low, key=lambda dt: abs((dt - current_dt).total_seconds()))

    # Phase à l'instant donné
    if abs((current_dt - high_dt).total_seconds()) < 1800:
        phase = "Étale haute"
    elif abs((current_dt - low_dt).total_seconds()) < 1800:
        phase = "Étale basse"
    elif low_dt < current_dt < high_dt or low_dt < current_dt + tide_cycle < high_dt:
        phase = "Montante"
    else:
        phase = "Descendante"

    return {
        "coefficient": coefficient,
        "pleine_mer": high_dt.time().replace(second=0, microsecond=0),
        "basse_mer": low_dt.time().replace(second=0, microsecond=0),
        "phase": phase,
        "source": "Estimation indicative locale",
    }


# ---------------------------------------------------------------------------
# Helpers : agrégation des données horaires
# ---------------------------------------------------------------------------

def mean_between_hours(df: Optional[pd.DataFrame], start_hour: str, end_hour: str) -> Dict[str, float]:
    """Moyenne numérique entre deux heures de la même journée."""
    if df is None or df.empty or "time" not in df.columns:
        return {}
    temp = df.copy()
    temp["dt"] = pd.to_datetime(temp["time"])
    first_day = temp["dt"].dt.date.iloc[0]
    start_t = pd.to_datetime(f"{first_day} {start_hour}")
    end_t = pd.to_datetime(f"{first_day} {end_hour}")
    if end_t <= start_t:
        selected = temp[temp["dt"] >= start_t]
    else:
        selected = temp[(temp["dt"] >= start_t) & (temp["dt"] <= end_t)]
    if selected.empty:
        selected = temp
    results: Dict[str, float] = {}
    for col in selected.columns:
        if col not in {"time", "dt"} and pd.api.types.is_numeric_dtype(selected[col]):
            val = selected[col].mean()
            if pd.notna(val):
                results[col] = round(float(val), 2)
    return results


def closest_to_now(df: Optional[pd.DataFrame]) -> Dict[str, Any]:
    """Retourne les valeurs les plus proches de maintenant."""
    if df is None or df.empty or "time" not in df.columns:
        return {}
    temp = df.copy()
    temp["dt"] = pd.to_datetime(temp["time"])
    now = pd.Timestamp.now()
    idx = (temp["dt"] - now).abs().idxmin()
    row = temp.loc[idx]
    result = {}
    for col in temp.columns:
        if col in {"time", "dt"}:
            continue
        val = row.get(col)
        if val is not None and pd.notna(val):
            try:
                result[col] = round(float(val), 2)
            except (TypeError, ValueError):
                result[col] = safe_str(val)
    return result


# ---------------------------------------------------------------------------
# POI Overpass générique
# ---------------------------------------------------------------------------

_OVERPASS_QUERIES = {
    "peche": '["shop"="fishing"]',
    "essence": '["amenity"="fuel"]',
    "wc": '["amenity"="toilets"]',
    "logement": '["tourism"~"hotel|hostel|camp_site|caravan_site|guest_house"]',
    "poubelle": '["amenity"~"recycling|waste_disposal|waste_basket"]',
    "restaurant": '["amenity"~"restaurant|fast_food|cafe|snack_bar"]',
}

_OVERPASS_LABELS = {
    "peche": "Magasin de pêche",
    "essence": "Station essence",
    "wc": "WC publics",
    "logement": "Logement / camping",
    "poubelle": "Déchets / poubelle",
    "restaurant": "Restaurant / snack",
}


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_overpass_pois(category: str, latitude: float, longitude: float, radius_m: int = 20000) -> pd.DataFrame:
    """Retourne les POI d'une catégorie via Overpass."""
    filter_tag = _OVERPASS_QUERIES.get(category)
    if not filter_tag:
        return pd.DataFrame()
    url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json][timeout:25];
    (
      node{filter_tag}(around:{radius_m},{latitude},{longitude});
      way{filter_tag}(around:{radius_m},{latitude},{longitude});
    );
    out center tags;
    """
    try:
        response = requests.post(url, data={"data": query}, timeout=30, verify=_SSL_VERIFY)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return pd.DataFrame()

    default_label = _OVERPASS_LABELS.get(category, category)
    pois = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        if lat is None or lon is None:
            continue
        name = tags.get("name") or default_label
        addr_parts = [tags.get("addr:housenumber"), tags.get("addr:street"),
                      tags.get("addr:postcode"), tags.get("addr:city")]
        addr = " ".join(p for p in addr_parts if p) or "—"
        pois.append({
            "Nom": name,
            "Adresse": addr,
            "Distance km": round(haversine_km(latitude, longitude, lat, lon), 2),
            "Latitude": lat,
            "Longitude": lon,
        })
    if not pois:
        return pd.DataFrame()
    return (pd.DataFrame(pois).drop_duplicates(subset=["Nom", "Latitude", "Longitude"])
            .sort_values("Distance km").head(20))


# ---------------------------------------------------------------------------
# Courbe de marée synthétique (sinusoïde, mise à jour en temps réel)
# ---------------------------------------------------------------------------

def generate_tide_curve(
    tide_date: date,
    latitude: float,
    longitude: float,
    hours: int = 48,
) -> pd.DataFrame:
    """
    Génère une courbe de hauteur de marée sur `hours` heures
    en utilisant une approximation sinusoïdale semi-diurne.

    Formule : h(t) = (coef/120) * A * cos(2π·(t - t_haute)/T) + msl
      - A     = amplitude max (≈ 2.0 m pour la façade atlantique)
      - T     = 12h25 (période semi-diurne)
      - msl   = niveau moyen estimé (0 m de référence)
      - coef  = coefficient de marée (20–120)
    """
    from core.utils import safe_float

    now_dt = datetime.now()
    tide   = estimate_tide(tide_date, now_dt.time().replace(second=0, microsecond=0),
                           latitude, longitude)

    coef     = tide["coefficient"]
    T_sec    = 12 * 3600 + 25 * 60          # période en secondes
    # Amplitude : ~2.0 m pour coef 95, proportionnel
    A        = 2.0 * coef / 95.0
    # t_haute = heure de pleine mer la plus proche dans le passé proche
    high_t   = datetime.combine(tide_date, tide["pleine_mer"])
    # S'assurer que high_t est dans un intervalle raisonnable autour de now
    while high_t > now_dt + timedelta(hours=6):
        high_t -= timedelta(seconds=T_sec)
    while high_t < now_dt - timedelta(hours=6):
        high_t += timedelta(seconds=T_sec)

    # Générer un point toutes les 15 minutes
    times  = [now_dt - timedelta(hours=2) + timedelta(minutes=15*i)
               for i in range(hours * 4 + 8)]
    heights = []
    for t in times:
        dt_sec = (t - high_t).total_seconds()
        h = A * math.cos(2 * math.pi * dt_sec / T_sec)
        heights.append(round(h, 3))

    df = pd.DataFrame({"time": times, "hauteur_m": heights})
    df["Heure"] = df["time"]
    return df, tide
