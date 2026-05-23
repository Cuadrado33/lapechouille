"""
La Péchouille — Génération de la base de marées annuelle.
Calcule les marées harmoniques pour 25 ports français
et insère les données dans Supabase.

Usage :
    py generate_tides.py [annee]
    
    Sans argument : génère pour l'année en cours + suivante.
"""
import math
import sys
import json
import requests
from datetime import datetime, timedelta, timezone

# ── Config Supabase ─────────────────────────────────────────────
SUPABASE_URL = "https://popejsluexmcicjmfcwc.supabase.co"
SERVICE_KEY  = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBvcGVqc2x1ZXhtY2ljam1mY3djIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3OTM4MTgzNiwiZXhwIjoyMDk0OTU3ODM2fQ.ars30R6Rq1Ulzkv80i47_yMf4qbZ2jMm_Y0VGKJElBI"
HEADERS = {
    "apikey":        SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type":  "application/json",
}

# ── Ports de référence ──────────────────────────────────────────
# Format : (nom, lat, lon, region, decalage_min_vs_brest, marnage_m)
# Décalages issus des annuaires SHOM (heure pleine mer vs Brest)
PORTS = [
    # ── Manche ─────────────────────────────────────────
    ("Calais",                 50.9581,  1.8508,  "manche",     +540, 6.5),
    ("Boulogne-sur-Mer",       50.7264,  1.5947,  "manche",     +510, 7.5),
    ("Dieppe",                 49.9234,  1.0850,  "manche",     +475, 7.5),
    ("Le Havre",               49.4944,  0.1079,  "manche",     +445, 7.0),
    ("Cherbourg",              49.6486, -1.6336,  "manche",     +360, 5.5),
    ("Granville",              48.8369, -1.6033,  "manche",     +400, 11.5),
    ("Saint-Malo",             48.6493, -2.0257,  "manche",     +395, 12.0),
    # ── Atlantique Nord ────────────────────────────────
    ("Brest",                  48.3905, -4.4860,  "atlantique",   0,  6.5),
    ("Le Conquet",             48.3597, -4.7700,  "atlantique",  -10, 6.5),
    ("Concarneau",             47.8732, -3.9162,  "atlantique",  +20, 5.0),
    ("Lorient",                47.7482, -3.3700,  "atlantique",  +30, 4.8),
    ("Le Croisic",             47.2925, -2.5197,  "atlantique",  +25, 5.2),
    ("Saint-Nazaire",          47.2733, -2.2138,  "atlantique",  +30, 5.5),
    ("Les Sables-d'Olonne",    46.4960, -1.7950,  "atlantique",  +20, 4.8),
    ("La Rochelle",            46.1583, -1.1517,  "atlantique",  +25, 5.5),
    ("Royan",                  45.6234, -1.0286,  "atlantique",  +30, 5.5),
    ("Bordeaux",               44.8378, -0.5792,  "atlantique", +185, 5.0),
    # ── Bassin d'Arcachon & Côte landaise ───────────────
    ("Cap Ferret",             44.6300, -1.2541,  "atlantique",  +35, 4.0),
    ("Arcachon",               44.6611, -1.1668,  "atlantique",  +50, 4.0),
    ("Soorts-Hossegor",        43.6700, -1.4400,  "atlantique",  +25, 4.0),
    ("Capbreton",              43.6480, -1.4476,  "atlantique",  +25, 4.0),
    ("Bayonne",                43.4837, -1.4754,  "atlantique",  +20, 4.0),
    ("Saint-Jean-de-Luz",      43.3870, -1.6610,  "atlantique",  +15, 4.0),
    # ── Sud ────────────────────────────────────────────
    ("Port-Vendres",           42.5189,  3.1064,  "mediterranee", 0,  0.4),
    ("Marseille",              43.2965,  5.3698,  "mediterranee", 0,  0.4),
]


# ── Algorithme harmonique simplifié ─────────────────────────────
# On utilise les 4 constantes harmoniques principales :
#   M2 (lunaire semi-diurne, période 12h25min)
#   S2 (solaire semi-diurne, période 12h)
#   N2 (lunaire elliptique, période 12h39min)
#   K1 (lunaire+solaire diurne, période 23h56min)

# Constantes M2, S2, N2, K1 — vitesse angulaire en degrés/heure
SPEEDS = {
    "M2": 28.984104,
    "S2": 30.000000,
    "N2": 28.439730,
    "K1": 15.041069,
}

# Phases moyennes pour Brest au 1er janvier 2000 (en degrés)
# Ces valeurs ont été calibrées pour matcher les annuaires SHOM
BREST_PHASES = {
    "M2": 117.0,
    "S2": 153.0,
    "N2":  97.0,
    "K1":  74.0,
}

# Amplitudes en mètres (port de Brest, ajustées par port via marnage_ref)
BREST_AMPLITUDES = {
    "M2": 2.18,
    "S2": 0.78,
    "N2": 0.43,
    "K1": 0.07,
}

# Niveau moyen mer (NM) en m
MEAN_LEVEL = 4.20


def hours_since_2000(dt: datetime) -> float:
    """Heures écoulées depuis le 1er janvier 2000, 00h UTC."""
    ref = datetime(2000, 1, 1, tzinfo=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (dt - ref).total_seconds() / 3600


def tide_height_brest(dt: datetime) -> float:
    """Hauteur d'eau à Brest à l'instant dt, calculée par somme harmonique."""
    t = hours_since_2000(dt)
    h = MEAN_LEVEL
    for k in SPEEDS:
        speed_rad = math.radians(SPEEDS[k])
        phase_rad = math.radians(BREST_PHASES[k])
        h += BREST_AMPLITUDES[k] * math.cos(speed_rad * t - phase_rad)
    return h


def tide_height_port(dt: datetime, marnage_ratio: float, decalage_min: int) -> float:
    """Hauteur d'eau pour un port donné."""
    # Décaler en arrière pour calculer la hauteur Brest "équivalente"
    dt_brest = dt - timedelta(minutes=decalage_min)
    h_brest = tide_height_brest(dt_brest)
    # Mise à l'échelle par le ratio de marnage
    return MEAN_LEVEL + (h_brest - MEAN_LEVEL) * marnage_ratio


def find_extrema(year: int, port: dict):
    """
    Trouve toutes les pleines/basses mers de l'année pour un port.
    Retourne liste de (datetime_utc, type, hauteur_m).
    """
    marnage_ratio = port["marnage_m"] / 6.5  # 6.5 = marnage Brest
    decalage = port["decalage_min"]

    start = datetime(year, 1, 1, tzinfo=timezone.utc)
    end   = datetime(year + 1, 1, 1, tzinfo=timezone.utc)

    # Calcul de la hauteur toutes les 10 minutes
    step = timedelta(minutes=10)
    heights = []
    cur = start
    while cur < end:
        h = tide_height_port(cur, marnage_ratio, decalage)
        heights.append((cur, h))
        cur += step

    # Détecter les maxima/minima locaux
    events = []
    for i in range(1, len(heights) - 1):
        prev_h = heights[i - 1][1]
        cur_h  = heights[i][1]
        next_h = heights[i + 1][1]
        if cur_h > prev_h and cur_h > next_h:
            events.append((heights[i][0], "PM", round(cur_h, 2)))
        elif cur_h < prev_h and cur_h < next_h:
            events.append((heights[i][0], "BM", round(cur_h, 2)))

    return events


def coefficient_marnee(h_pm: float, h_bm_prev: float, h_bm_next: float, marnage_ref: float) -> int:
    """Calcule le coefficient (45 à 120) à partir du marnage de cette marée."""
    h_bm_avg = (h_bm_prev + h_bm_next) / 2 if h_bm_prev and h_bm_next else (h_bm_prev or h_bm_next or 0)
    marnage = h_pm - h_bm_avg
    # Coefficient = 100 * marnage / marnage_de_référence_vives_eaux
    # Pour Brest, marnage VE = 6.0m donc 100 = marnage 6m
    ref_ve = marnage_ref * 0.95  # marnage VE = ~95% du marnage théorique max
    coef = int(round(100 * marnage / ref_ve))
    return max(20, min(120, coef))


# ── Insertion Supabase ──────────────────────────────────────────

def upsert_ports():
    """Insère les ports dans Supabase (idempotent)."""
    print("📍 Insertion des ports...")
    for nom, lat, lon, region, decalage, marnage in PORTS:
        # Cherche si le port existe déjà
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/tide_ports",
            headers=HEADERS,
            params={"nom": f"eq.{nom}", "select": "id"},
            timeout=10,
        )
        existing = r.json() if r.status_code == 200 else []
        data = {
            "nom":           nom,
            "latitude":      lat,
            "longitude":     lon,
            "region":        region,
            "decalage_min":  decalage,
            "marnage_ref_m": marnage,
        }
        if existing:
            pid = existing[0]["id"]
            requests.patch(
                f"{SUPABASE_URL}/rest/v1/tide_ports",
                headers=HEADERS,
                params={"id": f"eq.{pid}"},
                json=data,
                timeout=10,
            )
            print(f"  ↻ {nom} (id={pid})")
        else:
            requests.post(
                f"{SUPABASE_URL}/rest/v1/tide_ports",
                headers=HEADERS,
                json=data,
                timeout=10,
            )
            print(f"  ✅ {nom}")


def get_ports() -> list:
    """Récupère les ports depuis Supabase avec leurs id."""
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/tide_ports",
        headers=HEADERS,
        params={"select": "id,nom,latitude,longitude,region,decalage_min,marnage_ref_m"},
        timeout=10,
    )
    return r.json() if r.status_code == 200 else []


def insert_events_batch(events: list):
    """Insert par lots de 500."""
    BATCH = 500
    for i in range(0, len(events), BATCH):
        batch = events[i:i + BATCH]
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/tide_events",
            headers={**HEADERS, "Prefer": "return=minimal"},
            json=batch,
            timeout=30,
        )
        if r.status_code not in (200, 201, 204):
            print(f"  ⚠️ Erreur insert : {r.status_code} {r.text[:150]}")
        else:
            print(f"  ✅ {len(batch)} événements insérés ({i + len(batch)}/{len(events)})")


def delete_year(port_id: int, year: int):
    """Supprime les événements d'une année pour ce port."""
    start = f"{year}-01-01T00:00:00Z"
    end   = f"{year + 1}-01-01T00:00:00Z"
    requests.delete(
        f"{SUPABASE_URL}/rest/v1/tide_events",
        headers=HEADERS,
        params={
            "port_id":     f"eq.{port_id}",
            "datetime_utc": f"gte.{start}",
        },
        timeout=20,
    )


def generate_year(year: int):
    print(f"\n🌊 Génération marées pour {year}\n" + "=" * 50)
    ports = get_ports()
    print(f"   {len(ports)} ports à traiter")

    for p in ports:
        # Méditerranée : on saute (marnage trop faible, calcul peu fiable)
        if p.get("region") == "mediterranee":
            print(f"\n⏭  {p['nom']} (méditerranée, skipping)")
            continue

        port_dict = {
            "marnage_m":    p["marnage_ref_m"],
            "decalage_min": p["decalage_min"],
        }
        print(f"\n🏖️  {p['nom']} (id={p['id']})")
        print(f"   Suppression données existantes...")
        delete_year(p["id"], year)

        print(f"   Calcul des extrema...")
        events = find_extrema(year, port_dict)
        print(f"   {len(events)} marées trouvées")

        # Calculer les coefficients pour les PM
        rows_to_insert = []
        for i, (dt, t, h) in enumerate(events):
            row = {
                "port_id":      p["id"],
                "datetime_utc": dt.isoformat(),
                "type":         t,
                "hauteur_m":    h,
            }
            if t == "PM":
                # Trouver BM précédente et suivante
                h_bm_prev = None
                h_bm_next = None
                for j in range(i - 1, -1, -1):
                    if events[j][1] == "BM":
                        h_bm_prev = events[j][2]
                        break
                for j in range(i + 1, len(events)):
                    if events[j][1] == "BM":
                        h_bm_next = events[j][2]
                        break
                coef = coefficient_marnee(h, h_bm_prev, h_bm_next, p["marnage_ref_m"])
                row["coefficient"] = coef
            rows_to_insert.append(row)

        print(f"   Insertion Supabase...")
        insert_events_batch(rows_to_insert)


if __name__ == "__main__":
    args = sys.argv[1:]
    years = [int(a) for a in args] if args else [datetime.now().year, datetime.now().year + 1]
    upsert_ports()
    for year in years:
        generate_year(year)
    print(f"\n🎣 Terminé !")
