-- ======================================================================
-- SCRIPT SQL COMPLET — Système de pointage par reconnaissance faciale
-- PostgreSQL 14+ (recommandé 15/16)
-- ======================================================================

-- ============================
-- 1. EXTENSIONS
-- ============================
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Extension pgvector (optionnelle) : décommentez si l'extension est installée
-- CREATE EXTENSION IF NOT EXISTS vector;

-- ============================
-- 2. NETTOYAGE OPTIONNEL (environnement de développement)
-- ============================
DROP TYPE IF EXISTS attendance_method CASCADE;
DROP TYPE IF EXISTS auth_role CASCADE;
DROP TYPE IF EXISTS profile_type CASCADE;
DROP TABLE IF EXISTS refresh_tokens CASCADE;
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS attendance_records CASCADE;
DROP TABLE IF EXISTS face_encodings CASCADE;
DROP TABLE IF EXISTS face_images CASCADE;
DROP TABLE IF EXISTS sessions CASCADE;
DROP TABLE IF EXISTS user_groups CASCADE;
DROP TABLE IF EXISTS groups CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP FUNCTION IF EXISTS trigger_set_updated_at CASCADE;

-- ============================
-- 3. TYPES ENUM
-- ============================
CREATE TYPE profile_type AS ENUM ('student', 'employee', 'teacher', 'admin');

CREATE TYPE auth_role AS ENUM ('admin', 'manager', 'user');

CREATE TYPE attendance_method AS ENUM ('FACE', 'MANUAL', 'CARD', 'QR');

-- ============================
-- 4. FONCTION + TRIGGER updated_at
-- ============================
CREATE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = clock_timestamp();
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION trigger_set_updated_at() IS
    'Fonction générique pour mettre à jour automatiquement le champ updated_at avant chaque UPDATE';

-- ============================
-- 5. CRÉATION DES TABLES
-- ============================

-- 5.1 users
CREATE TABLE users (
    id            UUID           DEFAULT gen_random_uuid() PRIMARY KEY,
    email         VARCHAR(255)   NOT NULL,
    password_hash VARCHAR(255)   NOT NULL,
    full_name     VARCHAR(255)   NOT NULL,
    profile_type  profile_type   NOT NULL,
    auth_role     auth_role      NOT NULL,
    identifier    VARCHAR(20)    UNIQUE,
    phone         VARCHAR(20),
    is_active     BOOLEAN        DEFAULT true,
    created_at    TIMESTAMPTZ    DEFAULT now(),
    updated_at    TIMESTAMPTZ    DEFAULT now()
);

CREATE UNIQUE INDEX uq_users_email ON users(email);

COMMENT ON TABLE users IS
    'Table centrale des utilisateurs (étudiants, employés, enseignants, administrateurs)';

COMMENT ON COLUMN users.email IS 'Email de connexion';
COMMENT ON COLUMN users.password_hash IS 'Hash bcrypt du mot de passe';
COMMENT ON COLUMN users.full_name IS 'Nom complet';
COMMENT ON COLUMN users.profile_type IS 'Nature de la personne : student, employee, teacher, admin';
COMMENT ON COLUMN users.auth_role IS 'Permission : admin (tout accès), manager (gestion), user (pointage)';
COMMENT ON COLUMN users.identifier IS 'Matricule étudiant / employé (unique, nullable)';
COMMENT ON COLUMN users.phone IS 'Numéro de téléphone';
COMMENT ON COLUMN users.is_active IS 'Soft-delete : false si l utilisateur est désactivé';
COMMENT ON COLUMN users.created_at IS 'Date de création du compte';
COMMENT ON COLUMN users.updated_at IS 'Date de dernière modification, maintenu automatiquement par trigger';

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();

-- 5.2 groups
CREATE TABLE groups (
    id          UUID           DEFAULT gen_random_uuid() PRIMARY KEY,
    name        VARCHAR(255)   NOT NULL UNIQUE,
    description TEXT,
    created_at  TIMESTAMPTZ    DEFAULT now()
);

COMMENT ON TABLE groups IS 'Groupes logiques d utilisateurs (classe, équipe, département)';
COMMENT ON COLUMN groups.name IS 'Nom du groupe (ex : Groupe A, Équipe Marketing)';
COMMENT ON COLUMN groups.description IS 'Description optionnelle du groupe';

-- 5.3 user_groups (table de jonction)
CREATE TABLE user_groups (
    user_id  UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    group_id UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, group_id)
);

COMMENT ON TABLE user_groups IS 'Relation many-to-many entre utilisateurs et groupes';

-- 5.4 sessions
CREATE TABLE sessions (
    id         UUID           DEFAULT gen_random_uuid() PRIMARY KEY,
    group_id   UUID           REFERENCES groups(id) ON DELETE SET NULL,
    title      VARCHAR(255)   NOT NULL,
    start_time TIMESTAMPTZ    NOT NULL,
    end_time   TIMESTAMPTZ    NOT NULL,
    notes      TEXT,
    created_at TIMESTAMPTZ    DEFAULT now(),
    CONSTRAINT chk_sessions_end_time CHECK (end_time > start_time)
);

COMMENT ON TABLE sessions IS 'Événements planifiés (cours, réunion, shift) auxquels les utilisateurs peuvent pointer';
COMMENT ON COLUMN sessions.group_id IS 'Groupe restreint pouvant pointer à cette session (NULL = tout le monde)';
COMMENT ON COLUMN sessions.title IS 'Intitulé de la session (ex : Cours Algèbre, Réunion d équipe)';
COMMENT ON COLUMN sessions.start_time IS 'Début de la session';
COMMENT ON COLUMN sessions.end_time IS 'Fin de la session (doit être postérieure à start_time)';
COMMENT ON COLUMN sessions.notes IS 'Description ou information complémentaire (ex : salle)';

-- 5.5 face_images
CREATE TABLE face_images (
    id          UUID           DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id     UUID           NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    image_path  VARCHAR(500)   NOT NULL,
    is_primary  BOOLEAN        DEFAULT false,
    created_at  TIMESTAMPTZ    DEFAULT now()
);

COMMENT ON TABLE face_images IS 'Photos originales des utilisateurs, utilisées pour générer les encodages faciaux';
COMMENT ON COLUMN face_images.image_path IS 'Chemin du fichier image sur le disque ou object storage';
COMMENT ON COLUMN face_images.is_primary IS 'Image principale utilisée comme avatar (une seule par utilisateur recommandée)';

-- 5.6 face_encodings
CREATE TABLE face_encodings (
    id            UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id       UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    image_id      UUID        REFERENCES face_images(id) ON DELETE SET NULL,
    encoding_json TEXT,
    confidence    FLOAT,
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- Ajout conditionnel de la colonne encoding (VECTOR si pgvector, sinon TEXT)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        EXECUTE 'ALTER TABLE face_encodings ADD COLUMN encoding VECTOR(128)';
    ELSE
        EXECUTE 'ALTER TABLE face_encodings ADD COLUMN encoding TEXT';
    END IF;
    EXECUTE 'COMMENT ON COLUMN face_encodings.encoding IS ''Vecteur pgvector 128 dimensions (ou TEXT fallback si pgvector absent) pour recherche de similarité native''';
END;
$$;

ALTER TABLE face_encodings
    ADD CONSTRAINT chk_face_encodings_has_data
    CHECK (encoding IS NOT NULL OR encoding_json IS NOT NULL);

COMMENT ON TABLE face_encodings IS 'Vecteurs biométriques extraits des photos pour la reconnaissance faciale';
COMMENT ON COLUMN face_encodings.image_id IS 'Image source dont est issu cet encodage (NULL si l image a été supprimée)';
COMMENT ON COLUMN face_encodings.encoding_json IS 'Fallback JSON pour les bases sans pgvector';
COMMENT ON COLUMN face_encodings.confidence IS 'Score de confiance de l extraction (0-1)';

-- 5.7 attendance_records (table centrale)
CREATE TABLE attendance_records (
    id               UUID               DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id          UUID               NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id       UUID               REFERENCES sessions(id),
    record_date      DATE               NOT NULL,
    check_in         TIMESTAMPTZ        NOT NULL,
    check_out        TIMESTAMPTZ,
    confidence_score FLOAT,
    method           attendance_method  NOT NULL,
    notes            TEXT,
    created_at       TIMESTAMPTZ        DEFAULT now(),
    CONSTRAINT chk_attendance_check_out CHECK (check_out IS NULL OR check_out > check_in)
);

COMMENT ON TABLE attendance_records IS 'Table centrale des pointages (présence détectée par reconnaissance faciale ou autre méthode)';
COMMENT ON COLUMN attendance_records.session_id IS 'NULL = pointage libre, renseigné = présence à un événement planifié. FK sans ON DELETE CASCADE : la suppression d une session est bloquée si des pointages y sont liés (protection des données)';
COMMENT ON COLUMN attendance_records.record_date IS 'Date du pointage (dénormalisée pour les rapports)';
COMMENT ON COLUMN attendance_records.check_in IS 'Heure d arrivée';
COMMENT ON COLUMN attendance_records.check_out IS 'Heure de départ (NULL si encore présent)';
COMMENT ON COLUMN attendance_records.confidence_score IS 'Score de confiance de la reconnaissance faciale (0-1)';
COMMENT ON COLUMN attendance_records.method IS 'Méthode de pointage : FACE, MANUAL, CARD ou QR';

-- 5.8 audit_logs
CREATE TABLE audit_logs (
    id          UUID           DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id     UUID           REFERENCES users(id) ON DELETE SET NULL,
    action      VARCHAR(50)    NOT NULL,
    entity_type VARCHAR(50),
    entity_id   UUID,
    details     JSONB,
    ip_address  VARCHAR(45),
    created_at  TIMESTAMPTZ    DEFAULT now()
);

COMMENT ON TABLE audit_logs IS 'Journal d audit immuable traçant toutes les actions importantes (connexion, CRUD, modifications de pointage)';
COMMENT ON COLUMN audit_logs.user_id IS 'NULL si action système (ex : nettoyage automatique)';
COMMENT ON COLUMN audit_logs.action IS 'Type d action (LOGIN, CREATE_USER, DELETE_ATTENDANCE, etc.)';
COMMENT ON COLUMN audit_logs.entity_type IS 'Table concernée (user, session, attendance_record, etc.)';
COMMENT ON COLUMN audit_logs.entity_id IS 'ID de l entité concernée';
COMMENT ON COLUMN audit_logs.details IS 'Anciennes/nouvelles valeurs ou informations contextuelles au format JSONB';
COMMENT ON COLUMN audit_logs.ip_address IS 'Adresse IP de l auteur de l action';

-- 5.9 refresh_tokens
CREATE TABLE refresh_tokens (
    id          UUID           DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id     UUID           NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  VARCHAR(255)   NOT NULL,
    expires_at  TIMESTAMPTZ    NOT NULL,
    is_revoked  BOOLEAN        DEFAULT false,
    created_at  TIMESTAMPTZ    DEFAULT now()
);

CREATE UNIQUE INDEX uq_refresh_tokens_token_hash ON refresh_tokens(token_hash);

COMMENT ON TABLE refresh_tokens IS 'Gestion des sessions API JWT (refresh tokens hashés)';
COMMENT ON COLUMN refresh_tokens.token_hash IS 'Hash du refresh token (ne jamais stocker le token en clair)';
COMMENT ON COLUMN refresh_tokens.expires_at IS 'Date d expiration du token';
COMMENT ON COLUMN refresh_tokens.is_revoked IS 'Révoqué manuellement (déconnexion, changement de mot de passe)';

-- ============================
-- 6. INDEX DE PERFORMANCE
-- ============================

-- Attendance
CREATE INDEX idx_attendance_date      ON attendance_records(record_date);
CREATE INDEX idx_attendance_user_date ON attendance_records(user_id, record_date);
CREATE INDEX idx_attendance_session   ON attendance_records(session_id);

-- Sessions
CREATE INDEX idx_sessions_time  ON sessions(start_time, end_time);
CREATE INDEX idx_sessions_group ON sessions(group_id);

-- Groups / jonction
CREATE INDEX idx_user_groups_group ON user_groups(group_id);

-- Face
CREATE INDEX idx_face_user       ON face_encodings(user_id);
CREATE INDEX idx_face_image      ON face_encodings(image_id);
CREATE INDEX idx_face_images_user ON face_images(user_id, is_primary);

-- Audit
CREATE INDEX idx_audit_user   ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_date   ON audit_logs(created_at);

-- Refresh tokens
CREATE INDEX idx_refresh_user ON refresh_tokens(user_id);

-- Index pgvector pour recherche de similarité (décommentez si pgvector est activé)
-- L opérateur <-> (distance euclidienne L2) est recommandé pour face_recognition/dlib
-- CREATE INDEX idx_face_encoding_l2 ON face_encodings USING ivfflat (encoding vector_l2_ops) WITH (lists = 100);

-- ============================
-- 7. CONTRAINTES D'INTÉGRITÉ SUPPLÉMENTAIRES
-- ============================

-- Unicité pointage par session
CREATE UNIQUE INDEX uq_attendance_user_session ON attendance_records(user_id, session_id);

-- Un seul pointage libre par jour
CREATE UNIQUE INDEX uq_attendance_user_date_free
    ON attendance_records(user_id, record_date)
    WHERE session_id IS NULL;

-- ============================
-- 8. VUES UTILITAIRES
-- ============================

-- 8.1 Sessions actives aujourd'hui
CREATE OR REPLACE VIEW v_active_sessions_today AS
SELECT
    s.id,
    s.title,
    s.start_time,
    s.end_time,
    g.name AS group_name,
    s.notes
FROM sessions s
LEFT JOIN groups g ON g.id = s.group_id
WHERE s.start_time::date = CURRENT_DATE
   OR (s.start_time <= now() AND s.end_time >= now());

COMMENT ON VIEW v_active_sessions_today IS 'Sessions du jour en cours ou actives maintenant';

-- 8.2 Dernier pointage par utilisateur
CREATE OR REPLACE VIEW v_user_last_attendance AS
SELECT DISTINCT ON (u.id)
    u.id       AS user_id,
    u.full_name,
    u.profile_type,
    a.record_date,
    a.check_in,
    a.check_out,
    a.method,
    a.confidence_score,
    s.title    AS session_title
FROM users u
LEFT JOIN attendance_records a ON a.user_id = u.id
LEFT JOIN sessions s ON s.id = a.session_id
ORDER BY u.id, a.created_at DESC;

COMMENT ON VIEW v_user_last_attendance IS 'Dernier pointage enregistré pour chaque utilisateur';

-- 8.3 Résumé quotidien des présences
CREATE OR REPLACE VIEW v_daily_attendance_summary AS
SELECT
    a.record_date,
    COUNT(DISTINCT a.user_id)                                         AS total_presents,
    COUNT(DISTINCT a.user_id) FILTER (WHERE a.method = 'FACE')       AS face_count,
    COUNT(DISTINCT a.user_id) FILTER (WHERE a.method = 'MANUAL')     AS manual_count,
    COUNT(DISTINCT a.user_id) FILTER (WHERE a.method = 'CARD')       AS card_count,
    COUNT(DISTINCT a.user_id) FILTER (WHERE a.method = 'QR')         AS qr_count,
    COUNT(DISTINCT a.user_id) FILTER (WHERE a.check_out IS NULL)     AS still_present
FROM attendance_records a
GROUP BY a.record_date
ORDER BY a.record_date DESC;

COMMENT ON VIEW v_daily_attendance_summary IS 'Nombre de présents par jour, détaillé par méthode de pointage';

-- ============================
-- 9. DONNÉES DE TEST (SEED) — optionnel
-- ============================

INSERT INTO users (email, password_hash, full_name, profile_type, auth_role, identifier, phone) VALUES
    ('admin@example.com',    '$2b$12$LJ3m4ys3Lk0TSwHnbfOMiOXPm1Qm1Qm1Qm1Qm1Qm1Qm1Qm1Qm1Qm1', 'Admin Système',      'admin',    'admin',   'ADM001', '+221 77 000 00 01'),
    ('jean.dupont@example.com', '$2b$12$LJ3m4ys3Lk0TSwHnbfOMiOXPm1Qm1Qm1Qm1Qm1Qm1Qm1Qm1Qm1Qm1', 'Jean Dupont',         'student',  'user',    'STU001', '+221 77 000 00 02'),
    ('marie.diouf@example.com', '$2b$12$LJ3m4ys3Lk0TSwHnbfOMiOXPm1Qm1Qm1Qm1Qm1Qm1Qm1Qm1Qm1Qm1', 'Marie Diouf',         'student',  'user',    'STU002', '+221 77 000 00 03'),
    ('ali.fall@example.com',    '$2b$12$LJ3m4ys3Lk0TSwHnbfOMiOXPm1Qm1Qm1Qm1Qm1Qm1Qm1Qm1Qm1Qm1', 'Ali Fall',            'employee', 'user',    'EMP001', '+221 77 000 00 04'),
    ('sophie.ndiaye@example.com', '$2b$12$LJ3m4ys3Lk0TSwHnbfOMiOXPm1Qm1Qm1Qm1Qm1Qm1Qm1Qm1Qm1Qm1', 'Sophie Ndiaye',       'teacher',  'manager', 'TCH001', '+221 77 000 00 05'),
    ('pierre.sow@example.com',  '$2b$12$LJ3m4ys3Lk0TSwHnbfOMiOXPm1Qm1Qm1Qm1Qm1Qm1Qm1Qm1Qm1Qm1', 'Pierre Sow',          'student',  'admin',   'STU003', '+221 77 000 00 06');

INSERT INTO groups (name, description) VALUES
    ('Groupe A',    'Classe de Licence 1 informatique — Groupe A'),
    ('Équipe Technique', 'Équipe technique du laboratoire'),
    ('Shift Matin', 'Équipe du shift matin (06h-14h)');

INSERT INTO user_groups (user_id, group_id) VALUES
    ((SELECT id FROM users WHERE email = 'jean.dupont@example.com'),     (SELECT id FROM groups WHERE name = 'Groupe A')),
    ((SELECT id FROM users WHERE email = 'marie.diouf@example.com'),     (SELECT id FROM groups WHERE name = 'Groupe A')),
    ((SELECT id FROM users WHERE email = 'ali.fall@example.com'),        (SELECT id FROM groups WHERE name = 'Équipe Technique')),
    ((SELECT id FROM users WHERE email = 'pierre.sow@example.com'),      (SELECT id FROM groups WHERE name = 'Groupe A')),
    ((SELECT id FROM users WHERE email = 'pierre.sow@example.com'),      (SELECT id FROM groups WHERE name = 'Équipe Technique'));

INSERT INTO sessions (group_id, title, start_time, end_time) VALUES
    ((SELECT id FROM groups WHERE name = 'Groupe A'),
     'Cours Algèbre S2',
     CURRENT_DATE + TIME '08:00',
     CURRENT_DATE + TIME '10:00'),
    ((SELECT id FROM groups WHERE name = 'Équipe Technique'),
     'Réunion sprint hebdo',
     CURRENT_DATE + TIME '14:00',
     CURRENT_DATE + TIME '15:00');

INSERT INTO attendance_records (user_id, session_id, record_date, check_in, check_out, method) VALUES
    ((SELECT id FROM users WHERE email = 'jean.dupont@example.com'),
     (SELECT id FROM sessions WHERE title = 'Cours Algèbre S2'),
     CURRENT_DATE,
     CURRENT_DATE + TIME '07:55',
     CURRENT_DATE + TIME '10:05',
     'FACE'),
    ((SELECT id FROM users WHERE email = 'marie.diouf@example.com'),
     (SELECT id FROM sessions WHERE title = 'Cours Algèbre S2'),
     CURRENT_DATE,
     CURRENT_DATE + TIME '08:02',
     CURRENT_DATE + TIME '09:58',
     'FACE'),
    ((SELECT id FROM users WHERE email = 'pierre.sow@example.com'),
     (SELECT id FROM sessions WHERE title = 'Cours Algèbre S2'),
     CURRENT_DATE,
     CURRENT_DATE + TIME '08:00',
     NULL,
     'QR');

-- ======================================================================
-- RÉSUMÉ — VÉRIFICATIONS POST-DÉPLOIEMENT RECOMMANDÉES
-- ======================================================================
-- 1. Vérifier la structure des tables :
--    \d+ users
--    \d+ attendance_records
--    \d+ face_encodings
--
-- 2. Tester les contraintes d unicité :
--    INSERT INTO attendance_records (user_id, session_id, record_date, check_in, method)
--    VALUES ((SELECT id FROM users LIMIT 1), NULL, CURRENT_DATE, now(), 'FACE');
--    → Doit réussir (1er pointage libre du jour)
--    → Ré-exécuter : doit échouer (UNIQUE partiel)
--
-- 3. Tester le CHECK temporel :
--    INSERT INTO sessions (title, start_time, end_time)
--    VALUES ('Test', now(), now() - INTERVAL '1 hour');
--    → Doit échouer (end_time < start_time)
--
-- 4. Tester l idempotence : exécuter le script deux fois de suite
--    (la section DROP CASCADE au début nettoie tout en dev)
--
-- 5. Tester les vues :
--    SELECT * FROM v_active_sessions_today;
--    SELECT * FROM v_user_last_attendance;
--    SELECT * FROM v_daily_attendance_summary;
-- ======================================================================
