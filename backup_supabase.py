"""
Backup automatique Supabase → fichier JSON local.
Lance manuellement : py backup_supabase.py
Ou automatiquement via la tâche planifiée Windows.
"""
import json, requests, os
from datetime import datetime
from pathlib import Path

SUPABASE_URL = "https://popejsluexmcicjmfcwc.supabase.co"
SERVICE_KEY  = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBvcGVqc2x1ZXhtY2ljam1mY3djIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3OTM4MTgzNiwiZXhwIjoyMDk0OTU3ODM2fQ.ars30R6Rq1Ulzkv80i47_yMf4qbZ2jMm_Y0VGKJElBI"

HEADERS = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
}

TABLES = ["profils", "sessions", "captures", "spots", "bait_spots",
          "materiel", "multimedia", "posts", "likes", "commentaires",
          "amis", "messages"]

def fetch_table(table: str) -> list:
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=HEADERS,
        params={"select": "*", "limit": "10000"},
        timeout=30,
    )
    if r.status_code == 200:
        return r.json()
    print(f"  ⚠️ {table}: {r.status_code}")
    return []

def backup():
    # Dossier backups
    backup_dir = Path(__file__).parent / "backups_supabase"
    backup_dir.mkdir(exist_ok=True)

    # Garder seulement les 30 derniers backups
    existing = sorted(backup_dir.glob("backup_*.json"))
    for old in existing[:-29]:
        old.unlink()

    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = backup_dir / f"backup_{ts}.json"

    print(f"🔄 Backup Supabase → {dest.name}")
    data = {}
    total = 0
    for table in TABLES:
        rows = fetch_table(table)
        data[table] = rows
        total += len(rows)
        print(f"  ✅ {table}: {len(rows)} lignes")

    dest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    size = dest.stat().st_size / 1024
    print(f"\n🎉 Backup terminé — {total} lignes — {size:.1f} KB")
    print(f"   Fichier : {dest}")

if __name__ == "__main__":
    backup()
