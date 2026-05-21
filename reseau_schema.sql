-- ═══════════════════════════════════════════════════════════════
-- La Péchouille — Schéma Supabase S02
-- À exécuter dans Supabase → SQL Editor
-- ═══════════════════════════════════════════════════════════════

-- Activer les extensions nécessaires
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Profils utilisateurs ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS profils (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email       TEXT UNIQUE NOT NULL,
    pseudo      TEXT UNIQUE NOT NULL,
    avatar_url  TEXT,
    bio         TEXT,
    localisation TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── Posts (fil d'actualité) ──────────────────────────────────
CREATE TABLE IF NOT EXISTS posts (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID REFERENCES profils(id) ON DELETE CASCADE,
    type        TEXT NOT NULL, -- 'capture', 'session', 'spot', 'texte'
    contenu     TEXT,
    photo_url   TEXT,
    espece      TEXT,
    taille_cm   NUMERIC,
    poids_g     NUMERIC,
    lieu        TEXT,
    latitude    NUMERIC,
    longitude   NUMERIC,
    nb_likes    INTEGER DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── Likes ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS likes (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id     UUID REFERENCES posts(id) ON DELETE CASCADE,
    user_id     UUID REFERENCES profils(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(post_id, user_id)
);

-- ── Commentaires ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS commentaires (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id     UUID REFERENCES posts(id) ON DELETE CASCADE,
    user_id     UUID REFERENCES profils(id) ON DELETE CASCADE,
    contenu     TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── Amis ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS amis (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    demandeur_id  UUID REFERENCES profils(id) ON DELETE CASCADE,
    recepteur_id  UUID REFERENCES profils(id) ON DELETE CASCADE,
    statut        TEXT DEFAULT 'en_attente', -- 'en_attente', 'accepte', 'refuse'
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(demandeur_id, recepteur_id)
);

-- ── Classements ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS classements (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID REFERENCES profils(id) ON DELETE CASCADE,
    annee       INTEGER,
    mois        INTEGER,
    nb_captures INTEGER DEFAULT 0,
    nb_sessions INTEGER DEFAULT 0,
    taille_max  NUMERIC DEFAULT 0,
    poids_total NUMERIC DEFAULT 0,
    points      INTEGER DEFAULT 0,
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── Row Level Security (RLS) ─────────────────────────────────
ALTER TABLE profils      ENABLE ROW LEVEL SECURITY;
ALTER TABLE posts        ENABLE ROW LEVEL SECURITY;
ALTER TABLE likes        ENABLE ROW LEVEL SECURITY;
ALTER TABLE commentaires ENABLE ROW LEVEL SECURITY;
ALTER TABLE amis         ENABLE ROW LEVEL SECURITY;
ALTER TABLE classements  ENABLE ROW LEVEL SECURITY;

-- Politiques : lecture publique, écriture par l'auteur
CREATE POLICY "Lecture publique profils"  ON profils      FOR SELECT USING (true);
CREATE POLICY "Lecture publique posts"    ON posts        FOR SELECT USING (true);
CREATE POLICY "Lecture publique likes"    ON likes        FOR SELECT USING (true);
CREATE POLICY "Lecture publique coms"     ON commentaires FOR SELECT USING (true);
CREATE POLICY "Lecture publique amis"     ON amis         FOR SELECT USING (true);
CREATE POLICY "Lecture publique class"    ON classements  FOR SELECT USING (true);

CREATE POLICY "Insert profil"  ON profils      FOR INSERT WITH CHECK (true);
CREATE POLICY "Insert post"    ON posts        FOR INSERT WITH CHECK (true);
CREATE POLICY "Insert like"    ON likes        FOR INSERT WITH CHECK (true);
CREATE POLICY "Insert com"     ON commentaires FOR INSERT WITH CHECK (true);
CREATE POLICY "Insert ami"     ON amis         FOR INSERT WITH CHECK (true);
CREATE POLICY "Upsert class"   ON classements  FOR ALL    USING (true);

CREATE POLICY "Update profil"  ON profils      FOR UPDATE USING (true);
CREATE POLICY "Update ami"     ON amis         FOR UPDATE USING (true);
CREATE POLICY "Delete like"    ON likes        FOR DELETE USING (true);
CREATE POLICY "Delete post"    ON posts        FOR DELETE USING (true);
CREATE POLICY "Delete com"     ON commentaires FOR DELETE USING (true);
