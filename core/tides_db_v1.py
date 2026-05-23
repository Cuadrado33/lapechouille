"""
Lecture des marées depuis la base de données Supabase.
Trouve le port le plus proche du spot et retourne les marées du jour.
"""
from __future__ import annotations
import math
from datetime import datetime, date, timedelta, timezone
import streamlit as st
from core.supabase_client import supabase_get


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance grand-cercle entre 2 points en km."""
    R = 6371
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlat   = math.radians(lat2 - lat1)
    dlon   = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))


@st.cache_data(ttl=86400, show_spinner=False)
def get_ports() -> list[dict]:
    """Charge tous les ports (en cache 24h)."""
    return supabase_get("tide_ports", {"select": "*", "order": "nom.asc"}) or []


def find_nearest_port(latitude: float, longitude: float) -> dict | None:
    """Retourne le port le plus proche d'un spot."""
    ports = get_ports()
    if not ports:
        return None
    nearest = None
    best_dist = float("inf")
    for p in ports:
        try:
            d = _haversine_km(latitude, longitude, p["latitude"], p["longitude"])
        except Exception:
            continue
        if d < best_dist:
            best_dist = d
            nearest = p
    if nearest:
        nearest["distance_km"] = round(best_dist, 1)
    return nearest


@st.cache_data(ttl=3600, show_spinner=False)
def get_tides_for_day(port_id: int, target_date: str) -> list[dict]:
    """Marées du jour pour un port (et marées de la veille/lendemain pour continuité)."""
    try:
        d = datetime.fromisoformat(target_date).date()
    except Exception:
        return []
    start = (d - timedelta(days=1)).isoformat() + "T00:00:00Z"
    end   = (d + timedelta(days=2)).isoformat() + "T00:00:00Z"
    rows = supabase_get("tide_events", {
        "port_id":      f"eq.{port_id}",
        "datetime_utc": f"gte.{start}",
        "order":        "datetime_utc.asc",
        "limit":        "20",
    }) or []
    # Filtrer ceux avant end
    filtered = [r for r in rows if r["datetime_utc"] < end]
    return filtered


def get_tides_for_spot(latitude: float, longitude: float,
                        target_date: str | None = None) -> dict | None:
    """
    Renvoie un dict complet pour l'affichage :
    { port: {...}, events: [...], today_pm: [...], today_bm: [...], coef_max: int }
    """
    if target_date is None:
        target_date = date.today().isoformat()

    port = find_nearest_port(latitude, longitude)
    if not port:
        return None

    events = get_tides_for_day(port["id"], target_date)
    if not events:
        return None

    # Séparer PM / BM du jour J
    today_str = target_date
    today_pm = []
    today_bm = []
    coef_max = 0
    for e in events:
        dt_str = e["datetime_utc"]
        if dt_str.startswith(today_str):
            if e["type"] == "PM":
                today_pm.append(e)
                if e.get("coefficient"):
                    coef_max = max(coef_max, int(e["coefficient"]))
            elif e["type"] == "BM":
                today_bm.append(e)

    return {
        "port":      port,
        "events":    events,
        "today_pm":  today_pm,
        "today_bm":  today_bm,
        "coef_max":  coef_max,
        "date":      target_date,
    }


def format_time_fr(iso: str) -> str:
    """ISO UTC → 'HH:MM' en heure locale Europe/Paris."""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        # Conversion en heure locale France (UTC+1 hiver / UTC+2 été)
        # Approximation : été = avril-octobre
        m = dt.month
        offset_h = 2 if 4 <= m <= 10 else 1
        local = dt + timedelta(hours=offset_h)
        return local.strftime("%H:%M")
    except Exception:
        return "—"
