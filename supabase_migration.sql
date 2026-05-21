-- ═══════════════════════════════════════════════════════════════
-- La Péchouille — Migration complète vers Supabase
-- Copie-colle dans Supabase → SQL Editor → Run
-- ═══════════════════════════════════════════════════════════════

-- ── Sessions ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sessions (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             UUID REFERENCES profils(id) ON DELETE CASCADE,
    type_session        TEXT,
    session_terminee    INTEGER DEFAULT 0,
    date_session        TEXT,
    lieu                TEXT,
    latitude            NUMERIC,
    longitude           NUMERIC,
    heure_debut         TEXT,
    heure_fin           TEXT,
    duree_heures        NUMERIC,
    temperature_air     NUMERIC,
    temperature_eau     NUMERIC,
    humidite            NUMERIC,
    pression            NUMERIC,
    couverture_nuageuse NUMERIC,
    vent_vitesse        NUMERIC,
    vent_direction      NUMERIC,
    rafales             NUMERIC,
    vague_hauteur       NUMERIC,
    vague_direction     NUMERIC,
    vague_periode       NUMERIC,
    coefficient_maree   INTEGER,
    maree_haute         TEXT,
    maree_basse         TEXT,
    phase_maree         TEXT,
    clarte_eau          TEXT,
    canne               TEXT,
    moulinet            TEXT,
    bobine_moulinet     TEXT,
    fil_bobine          TEXT,
    taille_fil_bobine   TEXT,
    commentaire         TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ── Captures ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS captures (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             UUID REFERENCES profils(id) ON DELETE CASCADE,
    session_id          BIGINT REFERENCES sessions(id) ON DELETE CASCADE,
    capture_num         INTEGER,
    capture_label       TEXT,
    espece              TEXT,
    taille_cm           NUMERIC,
    poids_g             NUMERIC,
    poids_estime_g      NUMERIC,
    poisson_trophee     INTEGER DEFAULT 0,
    poisson_trophe      INTEGER DEFAULT 0,
    heure_capture       TEXT,
    appat               TEXT,
    montage             TEXT,
    marque_hamecon      TEXT,
    type_hamecon        TEXT,
    modele_hamecon      TEXT,
    taille_hamecon      TEXT,
    hamecon             TEXT,
    canne               TEXT,
    moulinet            TEXT,
    bobine_moulinet     TEXT,
    fil_bobine          TEXT,
    taille_fil_bobine   TEXT,
    fil                 TEXT,
    fil_corps_de_ligne  TEXT,
    taille_corps_de_ligne TEXT,
    fil_empile          TEXT,
    taille_empile       TEXT,
    distance_lancer_m   NUMERIC,
    photo_path          TEXT,
    relache             INTEGER DEFAULT 0,
    commentaire         TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ── Spots ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS spots (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID REFERENCES profils(id) ON DELETE CASCADE,
    nom             TEXT,
    latitude        NUMERIC,
    longitude       NUMERIC,
    type_fond       TEXT,
    profondeur      TEXT,
    acces           TEXT,
    especes_cibles  TEXT,
    commentaire     TEXT,
    photo_path      TEXT,
    favori          INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Spots appâts ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bait_spots (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             UUID REFERENCES profils(id) ON DELETE CASCADE,
    nom                 TEXT,
    latitude            NUMERIC,
    longitude           NUMERIC,
    type_appat          TEXT,
    categorie           TEXT,
    maree_ideale        TEXT,
    profondeur          TEXT,
    type_fond           TEXT,
    acces               TEXT,
    autorisation_outils TEXT,
    periode             TEXT,
    commentaire         TEXT,
    photo_path          TEXT,
    favori              INTEGER DEFAULT 0,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ── Matériel ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS materiel (
    id                      BIGSERIAL PRIMARY KEY,
    user_id                 UUID REFERENCES profils(id) ON DELETE CASCADE,
    categorie               TEXT,
    marque                  TEXT,
    modele                  TEXT,
    reference               TEXT,
    longueur_canne          TEXT,
    puissance_canne         TEXT,
    type_scion              TEXT,
    action_canne            TEXT,
    type_moulinet           TEXT,
    taille_moulinet         TEXT,
    ratio_moulinet          TEXT,
    recuperation_cm         TEXT,
    frein_kg                TEXT,
    roulements              TEXT,
    poids_moulinet_g        TEXT,
    capacite_bobine         TEXT,
    bobines_json            TEXT,
    type_fil                TEXT,
    diametre_fil            TEXT,
    resistance_fil          TEXT,
    longueur_fil_m          TEXT,
    type_plomb              TEXT,
    grammage_plomb          TEXT,
    type_hamecon            TEXT,
    taille_hamecon          TEXT,
    montage_nom             TEXT,
    montage_longueur_totale TEXT,
    montage_type_corps      TEXT,
    montage_diametre_corps  TEXT,
    montage_longueur_corps  TEXT,
    montage_nb_empiles      INTEGER,
    montage_plomb           TEXT,
    montage_cible           TEXT,
    montage_accessoires     TEXT,
    empiles_json            TEXT,
    etat                    TEXT,
    date_achat              TEXT,
    prix                    NUMERIC,
    lieu_stockage           TEXT,
    utilise_competition     INTEGER DEFAULT 0,
    photo_path              TEXT,
    commentaire             TEXT,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

-- ── Multimedia ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS multimedia (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID REFERENCES profils(id) ON DELETE CASCADE,
    session_id  BIGINT REFERENCES sessions(id) ON DELETE SET NULL,
    capture_id  BIGINT REFERENCES captures(id) ON DELETE SET NULL,
    categorie   TEXT,
    espece      TEXT,
    titre       TEXT,
    photo_path  TEXT,
    commentaire TEXT,
    favori      INTEGER DEFAULT 0,
    lieu        TEXT,
    date_photo  TEXT,
    photos_json TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── RLS (Row Level Security) ────────────────────────────────────
ALTER TABLE sessions      ENABLE ROW LEVEL SECURITY;
ALTER TABLE captures      ENABLE ROW LEVEL SECURITY;
ALTER TABLE spots         ENABLE ROW LEVEL SECURITY;
ALTER TABLE bait_spots    ENABLE ROW LEVEL SECURITY;
ALTER TABLE materiel      ENABLE ROW LEVEL SECURITY;
ALTER TABLE multimedia    ENABLE ROW LEVEL SECURITY;

-- Lecture publique + écriture par propriétaire
DO $$ 
DECLARE tables TEXT[] := ARRAY['sessions','captures','spots','bait_spots','materiel','multimedia'];
       t TEXT;
BEGIN
  FOREACH t IN ARRAY tables LOOP
    EXECUTE format('CREATE POLICY "Lecture %s" ON %s FOR SELECT USING (true)', t, t);
    EXECUTE format('CREATE POLICY "Insert %s" ON %s FOR INSERT WITH CHECK (true)', t, t);
    EXECUTE format('CREATE POLICY "Update %s" ON %s FOR UPDATE USING (true)', t, t);
    EXECUTE format('CREATE POLICY "Delete %s" ON %s FOR DELETE USING (true)', t, t);
  END LOOP;
END $$;

-- ── Bucket Storage pour les photos ──────────────────────────────
INSERT INTO storage.buckets (id, name, public)
VALUES ('photos', 'photos', true)
ON CONFLICT (id) DO NOTHING;

CREATE POLICY "Photos publiques" ON storage.objects
FOR SELECT USING (bucket_id = 'photos');

CREATE POLICY "Upload photos" ON storage.objects
FOR INSERT WITH CHECK (bucket_id = 'photos');

CREATE POLICY "Delete photos" ON storage.objects
FOR DELETE USING (bucket_id = 'photos');
