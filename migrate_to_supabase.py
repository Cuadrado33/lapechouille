"""
Script de migration SQLite → Supabase.
Lance depuis le dossier Surfcasting_J2 :
  python migrate_to_supabase.py
"""
import sqlite3, requests, json, os, sys
from pathlib import Path

SUPABASE_URL = "https://popejsluexmcicjmfcwc.supabase.co"
SERVICE_KEY  = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBvcGVqc2x1ZXhtY2ljam1mY3djIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3OTM4MTgzNiwiZXhwIjoyMDk0OTU3ODM2fQ.ars30R6Rq1Ulzkv80i47_yMf4qbZ2jMm_Y0VGKJElBI"

HEADERS = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

def supa_post(table, data):
    r = requests.post(f"{SUPABASE_URL}/rest/v1/{table}",
                      headers=HEADERS, json=data, timeout=15)
    if r.status_code not in (200, 201):
        print(f"  ❌ Erreur {table}: {r.status_code} {r.text[:200]}")
        return None
    result = r.json()
    return result[0] if isinstance(result, list) and result else result

def upload_photo(local_path: str, dest_path: str) -> str | None:
    """Upload une photo vers Supabase Storage. Retourne l'URL publique."""
    p = Path(local_path)
    if not p.exists():
        return None
    ext  = p.suffix.lower().lstrip(".")
    mime = "image/jpeg" if ext in ("jpg","jpeg") else f"image/{ext}"
    url  = f"{SUPABASE_URL}/storage/v1/object/photos/{dest_path}"
    hdrs = {**HEADERS, "Content-Type": mime}
    hdrs.pop("Prefer", None)
    try:
        with open(p, "rb") as f:
            r = requests.post(url, headers=hdrs, data=f.read(), timeout=30)
        if r.status_code in (200, 201):
            return f"{SUPABASE_URL}/storage/v1/object/public/photos/{dest_path}"
        else:
            print(f"  ⚠️ Photo {p.name}: {r.status_code}")
            return None
    except Exception as e:
        print(f"  ⚠️ Photo {p.name}: {e}")
        return None

def migrate():
    db_path = "surfcasting.db"
    if not Path(db_path).exists():
        print(f"❌ {db_path} introuvable — lance depuis le dossier Surfcasting_J2")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # ── Récupérer le user_id depuis Supabase (premier profil)
    r = requests.get(f"{SUPABASE_URL}/rest/v1/profils?select=id&limit=1",
                     headers=HEADERS, timeout=10)
    profils = r.json()
    if not profils:
        print("❌ Aucun profil dans Supabase. Crée d'abord ton compte dans l'app.")
        sys.exit(1)
    user_id = profils[0]["id"]
    print(f"✅ User ID : {user_id}")

    # ── ID mapping local → Supabase
    session_map = {}
    capture_map = {}
    spot_map    = {}

    # ── Sessions ────────────────────────────────────────────────
    print("\n📓 Migration sessions...")
    sessions = conn.execute("SELECT * FROM sessions").fetchall()
    for s in sessions:
        d = dict(s)
        old_id = d.pop("id")
        d["user_id"] = user_id
        result = supa_post("sessions", d)
        if result:
            session_map[old_id] = result["id"]
            print(f"  ✅ Session #{old_id} → #{result['id']}")

    # ── Spots ────────────────────────────────────────────────────
    print("\n📍 Migration spots...")
    spots = conn.execute("SELECT * FROM spots").fetchall()
    for s in spots:
        d = dict(s)
        old_id = d.pop("id")
        d["user_id"] = user_id
        # Upload photo si présente
        if d.get("photo_path") and Path(d["photo_path"]).exists():
            fname = Path(d["photo_path"]).name
            url = upload_photo(d["photo_path"], f"spots/{fname}")
            d["photo_path"] = url or d["photo_path"]
        result = supa_post("spots", d)
        if result:
            spot_map[old_id] = result["id"]
            print(f"  ✅ Spot #{old_id} {d.get('nom','')} → #{result['id']}")

    # ── Captures ─────────────────────────────────────────────────
    print("\n🐟 Migration captures...")
    captures = conn.execute("SELECT * FROM captures").fetchall()
    for c in captures:
        d = dict(c)
        old_id = d.pop("id")
        old_sess = d.get("session_id")
        d["user_id"]   = user_id
        d["session_id"] = session_map.get(old_sess) if old_sess else None
        # Upload photo si présente
        if d.get("photo_path") and Path(d["photo_path"]).exists():
            fname = Path(d["photo_path"]).name
            url = upload_photo(d["photo_path"], f"captures/{fname}")
            d["photo_path"] = url or d["photo_path"]
        result = supa_post("captures", d)
        if result:
            capture_map[old_id] = result["id"]
            print(f"  ✅ Capture #{old_id} {d.get('espece','')} → #{result['id']}")

    # ── Matériel ──────────────────────────────────────────────────
    print("\n🎯 Migration matériel...")
    materiels = conn.execute("SELECT * FROM materiel").fetchall()
    for m in materiels:
        d = dict(m)
        d.pop("id")
        d["user_id"] = user_id
        if d.get("photo_path") and Path(d["photo_path"]).exists():
            fname = Path(d["photo_path"]).name
            url = upload_photo(d["photo_path"], f"materiel/{fname}")
            d["photo_path"] = url or d["photo_path"]
        result = supa_post("materiel", d)
        if result:
            print(f"  ✅ Matériel {d.get('categorie','')} {d.get('marque','')} {d.get('modele','')}")

    # ── Bait spots ────────────────────────────────────────────────
    print("\n🪱 Migration spots appâts...")
    bait = conn.execute("SELECT * FROM bait_spots").fetchall()
    for b in bait:
        d = dict(b)
        d.pop("id")
        d["user_id"] = user_id
        result = supa_post("bait_spots", d)
        if result:
            print(f"  ✅ Spot appât {d.get('nom','')}")

    # ── Multimedia ────────────────────────────────────────────────
    print("\n📸 Migration photos multimedia...")
    medias = conn.execute("SELECT * FROM multimedia").fetchall()
    for m in medias:
        d = dict(m)
        d.pop("id")
        old_sess = d.get("session_id")
        old_cap  = d.get("capture_id")
        d["user_id"]   = user_id
        d["session_id"] = session_map.get(old_sess) if old_sess else None
        d["capture_id"] = capture_map.get(old_cap)  if old_cap  else None
        if d.get("photo_path") and Path(d["photo_path"].replace("\\","/")).exists():
            p = d["photo_path"].replace("\\","/")
            fname = Path(p).name
            url = upload_photo(p, f"multimedia/{fname}")
            d["photo_path"] = url or d["photo_path"]
        result = supa_post("multimedia", d)
        if result:
            print(f"  ✅ Photo {d.get('titre','')}")

    conn.close()
    print("\n🎉 Migration terminée !")
    print(f"   Sessions  : {len(session_map)}")
    print(f"   Spots     : {len(spot_map)}")
    print(f"   Captures  : {len(capture_map)}")

if __name__ == "__main__":
    migrate()
