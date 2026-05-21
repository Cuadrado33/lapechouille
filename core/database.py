"""
Couche d'accès aux données : SQLite + migrations automatiques.

Tables :
- sessions       : sorties de pêche
- captures       : poissons pris pendant une session
- materiel       : inventaire (cannes, moulinets, montages, etc.)
- multimedia     : photos souvenir liées à une session ou capture
- photos_associees : galeries photos secondaires pour un objet
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Iterable

import pandas as pd


# ---------------------------------------------------------------------------
# Configuration des chemins
# ---------------------------------------------------------------------------

DB_PATH = Path("surfcasting.db")
PHOTOS_DIR = Path("photos_captures")
MATERIEL_DIR = Path("photos_materiel")
MULTIMEDIA_DIR = Path("photos_multimedia")
SPOTS_DIR = Path("photos_spots")

for directory in (PHOTOS_DIR, MATERIEL_DIR, MULTIMEDIA_DIR, SPOTS_DIR):
    directory.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Connexion
# ---------------------------------------------------------------------------

def get_connection() -> sqlite3.Connection:
    """Connexion SQLite avec row_factory dict-like."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _column_exists(table: str, column: str) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    cols = [row["name"] for row in cur.fetchall()]
    conn.close()
    return column in cols


def _add_column_if_missing(table: str, column: str, sqltype: str) -> None:
    if not _column_exists(table, column):
        conn = get_connection()
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {sqltype}")
        conn.commit()
        conn.close()


# ---------------------------------------------------------------------------
# Initialisation du schéma
# ---------------------------------------------------------------------------

SCHEMA = {
    "sessions": """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type_session TEXT DEFAULT 'Loisir',
            session_terminee INTEGER DEFAULT 0,
            date_session TEXT NOT NULL,
            lieu TEXT,
            latitude REAL,
            longitude REAL,
            heure_debut TEXT,
            heure_fin TEXT,
            duree_heures REAL,
            temperature_air REAL,
            temperature_eau REAL,
            humidite REAL,
            pression REAL,
            couverture_nuageuse REAL,
            vent_vitesse REAL,
            vent_direction REAL,
            rafales REAL,
            vague_hauteur REAL,
            vague_direction REAL,
            vague_periode REAL,
            coefficient_maree INTEGER,
            maree_haute TEXT,
            maree_basse TEXT,
            phase_maree TEXT,
            clarte_eau TEXT,
            canne TEXT,
            moulinet TEXT,
            bobine_moulinet TEXT,
            fil_bobine TEXT,
            taille_fil_bobine TEXT,
            commentaire TEXT,
            created_at TEXT NOT NULL
        )
    """,
    "captures": """
        CREATE TABLE IF NOT EXISTS captures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            capture_num INTEGER,
            capture_label TEXT,
            espece TEXT,
            taille_cm REAL,
            poids_g REAL,
            poids_estime_g REAL,
            poisson_trophee INTEGER DEFAULT 0,
            heure_capture TEXT,
            appat TEXT,
            montage TEXT,
            marque_hamecon TEXT,
            type_hamecon TEXT,
            modele_hamecon TEXT,
            taille_hamecon TEXT,
            hamecon TEXT,
            canne TEXT,
            moulinet TEXT,
            bobine_moulinet TEXT,
            fil_bobine TEXT,
            taille_fil_bobine TEXT,
            distance_lancer_m REAL,
            photo_path TEXT,
            relache INTEGER DEFAULT 0,
            commentaire TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            FOREIGN KEY(session_id) REFERENCES sessions(id)
        )
    """,
    "materiel": """
        CREATE TABLE IF NOT EXISTS materiel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            categorie TEXT,
            marque TEXT,
            modele TEXT,
            reference TEXT,
            -- Canne
            longueur_canne TEXT,
            puissance_canne TEXT,
            type_scion TEXT,
            action_canne TEXT,
            -- Moulinet
            type_moulinet TEXT,
            taille_moulinet TEXT,
            ratio_moulinet TEXT,
            recuperation_cm TEXT,
            frein_kg TEXT,
            roulements TEXT,
            poids_moulinet_g TEXT,
            capacite_bobine TEXT,
            -- Bobines (jusqu'à 10) stockées en JSON
            bobines_json TEXT,
            -- Fil
            type_fil TEXT,
            diametre_fil TEXT,
            resistance_fil TEXT,
            longueur_fil_m TEXT,
            -- Plomb
            type_plomb TEXT,
            grammage_plomb TEXT,
            -- Hameçon
            type_hamecon TEXT,
            taille_hamecon TEXT,
            -- Montage (détails JSON pour empiles)
            montage_nom TEXT,
            montage_longueur_totale TEXT,
            montage_type_corps TEXT,
            montage_diametre_corps TEXT,
            montage_longueur_corps TEXT,
            montage_nb_empiles INTEGER,
            montage_plomb TEXT,
            montage_cible TEXT,
            montage_accessoires TEXT,
            empiles_json TEXT,
            -- Commun
            etat TEXT,
            date_achat TEXT,
            prix REAL,
            lieu_stockage TEXT,
            utilise_competition INTEGER DEFAULT 0,
            photo_path TEXT,
            commentaire TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT
        )
    """,
    "multimedia": """
        CREATE TABLE IF NOT EXISTS multimedia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            capture_id INTEGER,
            categorie TEXT,
            espece TEXT,
            titre TEXT,
            photo_path TEXT NOT NULL,
            commentaire TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            FOREIGN KEY(session_id) REFERENCES sessions(id),
            FOREIGN KEY(capture_id) REFERENCES captures(id)
        )
    """,
    "photos_associees": """
        CREATE TABLE IF NOT EXISTS photos_associees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type_objet TEXT NOT NULL,
            objet_id INTEGER NOT NULL,
            photo_path TEXT NOT NULL,
            legende TEXT,
            photo_principale INTEGER DEFAULT 0,
            ordre_affichage INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT
        )
    """,
    "spots": """
        CREATE TABLE IF NOT EXISTS spots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            type_fond TEXT,
            profondeur TEXT,
            acces TEXT,
            especes_cibles TEXT,
            commentaire TEXT,
            photo_path TEXT,
            favori INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT
        )
    """,
    "profil": """
        CREATE TABLE IF NOT EXISTS profil (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prenom TEXT,
            nom TEXT,
            pseudo TEXT,
            date_naissance TEXT,
            niveau TEXT,
            annees_peche INTEGER,
            zone_peche_principale TEXT,
            espece_preferee TEXT,
            canne_preferee TEXT,
            appat_prefere TEXT,
            bio TEXT,
            photo_path TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT
        )
    """,
    "bait_spots": """
        CREATE TABLE IF NOT EXISTS bait_spots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            type_appat TEXT,
            categorie TEXT,
            maree_ideale TEXT,
            profondeur TEXT,
            type_fond TEXT,
            acces TEXT,
            autorisation_outils TEXT,
            periode TEXT,
            commentaire TEXT,
            photo_path TEXT,
            favori INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT
        )
    """,
}


# Anciennes colonnes individuelles converties en JSON (compat migrations)
LEGACY_MIGRATIONS = [
    # Sessions : compatibilité ancienne app
    ("sessions", "type_session", "TEXT DEFAULT 'Loisir'"),
    ("sessions", "session_terminee", "INTEGER DEFAULT 0"),
    # Captures : compat anciens noms
    ("captures", "poisson_trophe", "INTEGER DEFAULT 0"),  # ancien nom
    ("captures", "poisson_trophee", "INTEGER DEFAULT 0"),  # nouveau nom
    ("captures", "fil", "TEXT"),
    ("captures", "fil_corps_de_ligne", "TEXT"),
    ("captures", "taille_corps_de_ligne", "TEXT"),
    ("captures", "fil_empile", "TEXT"),
    ("captures", "taille_empile", "TEXT"),
    # Matériel : JSON bobines et empiles
    ("materiel", "bobines_json", "TEXT"),
    ("materiel", "empiles_json", "TEXT"),
    ("materiel", "montage_nom", "TEXT"),
    ("materiel", "type_fil", "TEXT"),
    ("materiel", "type_hamecon", "TEXT"),
    ("materiel", "taille_hamecon", "TEXT"),
    # Multimedia : favoris + lieu + date + photos multiples
    ("multimedia", "favori",      "INTEGER DEFAULT 0"),
    ("multimedia", "lieu",        "TEXT"),
    ("multimedia", "date_photo",  "TEXT"),
    ("multimedia", "photos_json", "TEXT"),   # JSON list de chemins supplémentaires
    # Profil : observations libres + observations par espèce + réseaux sociaux
    ("profil", "observations",      "TEXT"),
    ("profil", "fish_observations", "TEXT"),
    ("profil", "social_facebook",   "TEXT"),
    ("profil", "social_instagram",  "TEXT"),
    ("profil", "social_youtube",    "TEXT"),
    ("profil", "social_tiktok",     "TEXT"),
]


def init_db() -> None:
    """Crée les tables si absentes et applique les migrations."""
    conn = get_connection()
    cur = conn.cursor()
    for ddl in SCHEMA.values():
        cur.execute(ddl)
    conn.commit()
    conn.close()

    for table, column, sqltype in LEGACY_MIGRATIONS:
        try:
            _add_column_if_missing(table, column, sqltype)
        except sqlite3.OperationalError:
            pass


# ---------------------------------------------------------------------------
# Opérations CRUD génériques
# ---------------------------------------------------------------------------

def insert_row(table: str, data: Dict[str, Any]) -> int:
    """Insère une ligne et renvoie l'id généré."""
    if not data:
        raise ValueError("Aucune donnée à insérer.")
    # Garde uniquement les colonnes existantes
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    existing_cols = {row["name"] for row in cur.fetchall()}
    filtered = {k: v for k, v in data.items() if k in existing_cols}
    if not filtered:
        conn.close()
        raise ValueError(f"Aucune colonne valide pour la table {table}.")
    columns = ", ".join(filtered.keys())
    placeholders = ", ".join(["?"] * len(filtered))
    cur.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", list(filtered.values()))
    row_id = int(cur.lastrowid)
    conn.commit()
    conn.close()
    return row_id


def update_row(table: str, row_id: int, data: Dict[str, Any]) -> None:
    """Met à jour une ligne par son id, en ignorant les colonnes inconnues."""
    if not data:
        return
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    existing_cols = {row["name"] for row in cur.fetchall()}
    filtered = {k: v for k, v in data.items() if k in existing_cols}
    if not filtered:
        conn.close()
        return
    assignments = ", ".join([f"{col} = ?" for col in filtered.keys()])
    cur.execute(
        f"UPDATE {table} SET {assignments} WHERE id = ?",
        list(filtered.values()) + [row_id],
    )
    conn.commit()
    conn.close()


def delete_row(table: str, row_id: int) -> None:
    """Supprime une ligne par son id."""
    conn = get_connection()
    conn.execute(f"DELETE FROM {table} WHERE id = ?", (row_id,))
    conn.commit()
    conn.close()


def fetch_one(query: str, params: Iterable = ()) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, tuple(params))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def fetch_df(query: str, params: Iterable = ()) -> pd.DataFrame:
    """Exécute une requête SQL et retourne un DataFrame."""
    conn = get_connection()
    df = pd.read_sql_query(query, conn, params=tuple(params))
    conn.close()
    return df


# ---------------------------------------------------------------------------
# Helpers métier
# ---------------------------------------------------------------------------

def load_sessions() -> pd.DataFrame:
    return fetch_df("SELECT * FROM sessions ORDER BY date_session DESC, id DESC")


def load_captures() -> pd.DataFrame:
    return fetch_df("""
        SELECT c.*,
               s.date_session, s.lieu, s.phase_maree, s.coefficient_maree,
               s.vent_vitesse, s.vague_hauteur, s.temperature_eau, s.type_session
        FROM captures c
        LEFT JOIN sessions s ON c.session_id = s.id
        ORDER BY c.created_at DESC, c.id DESC
    """)


def load_captures_for_session(session_id: int) -> pd.DataFrame:
    return fetch_df(
        "SELECT * FROM captures WHERE session_id = ? ORDER BY COALESCE(capture_num, id), id",
        (session_id,),
    )


def load_materiel(categorie: Optional[str] = None) -> pd.DataFrame:
    if categorie:
        return fetch_df(
            "SELECT * FROM materiel WHERE LOWER(categorie) LIKE ? ORDER BY marque, modele",
            (f"%{categorie.lower()}%",),
        )
    return fetch_df("SELECT * FROM materiel ORDER BY categorie, marque, modele")


def load_multimedia() -> pd.DataFrame:
    return fetch_df("""
        SELECT m.*, s.date_session, s.lieu, c.espece AS capture_espece
        FROM multimedia m
        LEFT JOIN sessions s ON m.session_id = s.id
        LEFT JOIN captures c ON m.capture_id = c.id
        ORDER BY m.created_at DESC, m.id DESC
    """)


def next_capture_number(session_id: int) -> int:
    row = fetch_one(
        "SELECT MAX(COALESCE(capture_num, 0)) AS max_num FROM captures WHERE session_id = ?",
        (session_id,),
    )
    return int(row["max_num"] or 0) + 1 if row else 1


def delete_capture(capture_id: int, delete_photo: bool = True) -> None:
    row = fetch_one("SELECT photo_path FROM captures WHERE id = ?", (capture_id,))
    delete_row("captures", capture_id)
    if delete_photo and row and row.get("photo_path"):
        try:
            p = Path(row["photo_path"])
            if p.exists():
                p.unlink()
        except OSError:
            pass


def delete_session(session_id: int, delete_photos: bool = True) -> None:
    """Supprime une session et toutes ses captures."""
    captures_df = load_captures_for_session(session_id)
    if not captures_df.empty:
        for cap_id in captures_df["id"].tolist():
            delete_capture(int(cap_id), delete_photo=delete_photos)
    delete_row("sessions", session_id)


# ---------------------------------------------------------------------------
# Galerie photos associées
# ---------------------------------------------------------------------------

def add_associated_photo(
    type_objet: str,
    objet_id: int,
    photo_path: str,
    legende: str = "",
    photo_principale: bool = False,
) -> int:
    """Ajoute une photo liée à un objet."""
    conn = get_connection()
    cur = conn.cursor()
    if photo_principale:
        cur.execute(
            "UPDATE photos_associees SET photo_principale = 0 WHERE type_objet = ? AND objet_id = ?",
            (type_objet, objet_id),
        )
    cur.execute(
        """INSERT INTO photos_associees
            (type_objet, objet_id, photo_path, legende, photo_principale, ordre_affichage, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            type_objet, objet_id, photo_path, legende,
            int(photo_principale), 0,
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    photo_id = int(cur.lastrowid)
    conn.commit()
    conn.close()
    return photo_id


def load_associated_photos(type_objet: str, objet_id: int) -> pd.DataFrame:
    return fetch_df(
        """SELECT * FROM photos_associees
           WHERE type_objet = ? AND objet_id = ?
           ORDER BY photo_principale DESC, ordre_affichage ASC, id ASC""",
        (type_objet, objet_id),
    )


def delete_associated_photo(photo_id: int, delete_file: bool = False) -> None:
    row = fetch_one("SELECT photo_path FROM photos_associees WHERE id = ?", (photo_id,))
    delete_row("photos_associees", photo_id)
    if delete_file and row and row.get("photo_path"):
        try:
            p = Path(row["photo_path"])
            if p.exists():
                p.unlink()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Spots pré-enregistrés
# ---------------------------------------------------------------------------

def load_spots() -> pd.DataFrame:
    return fetch_df("SELECT * FROM spots ORDER BY favori DESC, nom")


def get_spot(spot_id: int) -> Optional[Dict[str, Any]]:
    return fetch_one("SELECT * FROM spots WHERE id = ?", (spot_id,))


def load_bait_spots() -> pd.DataFrame:
    """Spots à appâts (récolte + pêche aux pièges)."""
    return fetch_df("SELECT * FROM bait_spots ORDER BY favori DESC, nom")


def get_bait_spot(spot_id: int) -> Optional[Dict[str, Any]]:
    return fetch_one("SELECT * FROM bait_spots WHERE id = ?", (spot_id,))


# ---------------------------------------------------------------------------
# Profil pêcheur
# ---------------------------------------------------------------------------

def load_profil() -> Optional[Dict[str, Any]]:
    """Retourne l'unique profil ou None."""
    return fetch_one("SELECT * FROM profil ORDER BY id LIMIT 1")


def save_profil(data: Dict[str, Any]) -> None:
    """Crée ou met à jour le profil unique."""
    existing = load_profil()
    if existing:
        update_row("profil", int(existing["id"]), data)
    else:
        data["created_at"] = __import__("datetime").datetime.now().isoformat(timespec="seconds")
        insert_row("profil", data)
