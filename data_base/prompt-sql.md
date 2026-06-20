# PROMPT — Génération du script PostgreSQL complet (Système de pointage par reconnaissance faciale)

## Contexte

Tu es un expert PostgreSQL (DBA + architecte de données). Tu dois générer le script SQL **complet, exécutable de bout en bout** d'une base de données PostgreSQL pour un système de **gestion du pointage et de la présence par reconnaissance faciale**.

Le système est **mono-organisation** (zéro multi-tenant) et **sans hiérarchie organisationnelle** (zéro `organizations`, zéro `organizational_units`). Il couvre 9 tables : `users`, `groups`, `user_groups`, `sessions`, `face_images`, `face_encodings`, `attendance_records`, `audit_logs`, `refresh_tokens`.

Le script doit être **directement exécutable** sur une base PostgreSQL 14+ (idéalement 15/16), sans erreur, dans l'ordre de création respectant les dépendances de clés étrangères.

---

## Exigences techniques générales

1. **Extensions** : active `pgcrypto` (ou `uuid-ossp`) pour la génération d'UUID, et tente d'activer `vector` (pgvector) pour `face_encodings.encoding`, avec un `DO $$ ... $$` ou un commentaire clair indiquant que c'est optionnel si l'extension n'est pas disponible sur l'hôte.
2. **Types ENUM** : crée des types PostgreSQL natifs (`CREATE TYPE ... AS ENUM`) pour :
   - `profile_type` : `student`, `employee`, `teacher`, `admin`
   - `auth_role` : `admin`, `manager`, `user`
   - `attendance_method` : `FACE`, `MANUAL`, `CARD`, `QR`
3. **Clés primaires** : toutes en `UUID`, générées par défaut via `gen_random_uuid()` (pgcrypto) — pas de `SERIAL`/`BIGSERIAL`.
4. **Horodatage** : utilise `TIMESTAMPTZ` partout (jamais `TIMESTAMP` sans fuseau), avec `DEFAULT now()`.
5. **Nommage** : tables en `snake_case` au pluriel, colonnes en `snake_case`, contraintes nommées explicitement (`fk_...`, `uq_...`, `chk_...`, `idx_...`) pour faciliter la maintenance et le debug.
6. **Commentaires** : ajoute des `COMMENT ON TABLE` et `COMMENT ON COLUMN` pour les champs non triviaux (ex : `confidence_score`, `encoding_json`, `is_primary`), en français, repris du dictionnaire de données ci-dessous.
7. **Ordre de création** : respecte les dépendances FK — `users` et `groups` d'abord, puis `user_groups`, `sessions`, `face_images`, puis `face_encodings` et `attendance_records`, puis `audit_logs` et `refresh_tokens`.
8. **Idempotence** : utilise `DROP TYPE IF EXISTS ... CASCADE` / `DROP TABLE IF EXISTS ... CASCADE` en en-tête (section clairement délimitée et optionnelle) pour permettre de relancer le script proprement en environnement de développement.
9. **Triggers `updated_at`** : pour `users` (seule table avec `updated_at`), crée une fonction `trigger_set_updated_at()` réutilisable + un trigger `BEFORE UPDATE`.
10. **Vues utilitaires (bonus)** : propose 2-3 vues SQL pratiques, par exemple :
    - `v_active_sessions_today` (sessions du jour en cours)
    - `v_user_last_attendance` (dernier pointage par utilisateur)
    - `v_daily_attendance_summary` (nombre de présents par jour)
11. **Données de test (seed) optionnelles** : à la fin, fournis un bloc `INSERT` minimal mais réaliste (2-3 groupes, 5-6 utilisateurs avec différents `profile_type`/`auth_role`, 2 sessions, quelques pointages) pour valider le schéma rapidement, dans une section clairement séparée (`-- ============ SEED DATA (optionnel) ============`).

---

## Dictionnaire de données détaillé à respecter strictement

### `users`
| Champ | Type | Contraintes |
|---|---|---|
| id | UUID | PK, DEFAULT gen_random_uuid() |
| email | VARCHAR(255) | NOT NULL, UNIQUE |
| password_hash | VARCHAR(255) | NOT NULL |
| full_name | VARCHAR(255) | NOT NULL |
| profile_type | ENUM profile_type | NOT NULL |
| auth_role | ENUM auth_role | NOT NULL |
| identifier | VARCHAR(20) | NULLABLE, UNIQUE |
| phone | VARCHAR(20) | NULLABLE |
| is_active | BOOLEAN | DEFAULT true |
| created_at | TIMESTAMPTZ | DEFAULT now() |
| updated_at | TIMESTAMPTZ | DEFAULT now(), maintenu par trigger |

### `groups`
| Champ | Type | Contraintes |
|---|---|---|
| id | UUID | PK |
| name | VARCHAR(255) | NOT NULL, UNIQUE |
| description | TEXT | NULLABLE |
| created_at | TIMESTAMPTZ | DEFAULT now() |

### `user_groups` (table de jonction, PK composite, pas de colonne id)
| Champ | Type | Contraintes |
|---|---|---|
| user_id | UUID | FK → users.id ON DELETE CASCADE |
| group_id | UUID | FK → groups.id ON DELETE CASCADE |
| PK | — | (user_id, group_id) |

### `sessions`
| Champ | Type | Contraintes |
|---|---|---|
| id | UUID | PK |
| group_id | UUID | FK → groups.id ON DELETE SET NULL, NULLABLE |
| title | VARCHAR(255) | NOT NULL |
| start_time | TIMESTAMPTZ | NOT NULL |
| end_time | TIMESTAMPTZ | NOT NULL, CHECK(end_time > start_time) |
| notes | TEXT | NULLABLE |
| created_at | TIMESTAMPTZ | DEFAULT now() |

### `face_images`
| Champ | Type | Contraintes |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → users.id ON DELETE CASCADE, NOT NULL |
| image_path | VARCHAR(500) | NOT NULL |
| is_primary | BOOLEAN | DEFAULT false |
| created_at | TIMESTAMPTZ | DEFAULT now() |

### `face_encodings`
| Champ | Type | Contraintes |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → users.id ON DELETE CASCADE, NOT NULL |
| image_id | UUID | FK → face_images.id ON DELETE SET NULL, NULLABLE |
| encoding | VECTOR(128) | NULLABLE (nécessite pgvector) |
| encoding_json | TEXT | NULLABLE (fallback si pgvector absent) |
| confidence | FLOAT | NULLABLE |
| created_at | TIMESTAMPTZ | DEFAULT now() |
| **Contrainte CHECK** | — | au moins un de `encoding` / `encoding_json` doit être renseigné (`encoding IS NOT NULL OR encoding_json IS NOT NULL`) |

### `attendance_records` (table centrale)
| Champ | Type | Contraintes |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → users.id ON DELETE CASCADE, NOT NULL |
| session_id | UUID | FK → sessions.id, NULLABLE |
| record_date | DATE | NOT NULL |
| check_in | TIMESTAMPTZ | NOT NULL |
| check_out | TIMESTAMPTZ | NULLABLE |
| confidence_score | FLOAT | NULLABLE |
| method | ENUM attendance_method | NOT NULL |
| notes | TEXT | NULLABLE |
| created_at | TIMESTAMPTZ | DEFAULT now() |

**Contraintes obligatoires :**
- `UNIQUE(user_id, session_id)` — pas de double pointage par session
- `UNIQUE(user_id, record_date) WHERE session_id IS NULL` — un seul pointage libre par jour (index unique partiel)
- `CHECK(check_out IS NULL OR check_out > check_in)`

### `audit_logs` (écriture seule, immuable)
| Champ | Type | Contraintes |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → users.id ON DELETE SET NULL, NULLABLE |
| action | VARCHAR(50) | NOT NULL |
| entity_type | VARCHAR(50) | NULLABLE |
| entity_id | UUID | NULLABLE |
| details | JSONB | NULLABLE |
| ip_address | VARCHAR(45) | NULLABLE |
| created_at | TIMESTAMPTZ | DEFAULT now() |

### `refresh_tokens`
| Champ | Type | Contraintes |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → users.id ON DELETE CASCADE, NOT NULL |
| token_hash | VARCHAR(255) | NOT NULL, UNIQUE |
| expires_at | TIMESTAMPTZ | NOT NULL |
| is_revoked | BOOLEAN | DEFAULT false |
| created_at | TIMESTAMPTZ | DEFAULT now() |

---

## Index obligatoires à créer

```sql
-- Attendance
CREATE INDEX idx_attendance_date ON attendance_records(record_date);
CREATE INDEX idx_attendance_user_date ON attendance_records(user_id, record_date);
CREATE INDEX idx_attendance_session ON attendance_records(session_id);

-- Sessions
CREATE INDEX idx_sessions_time ON sessions(start_time, end_time);
CREATE INDEX idx_sessions_group ON sessions(group_id);

-- Groups / jonction
CREATE INDEX idx_user_groups_group ON user_groups(group_id);

-- Face
CREATE INDEX idx_face_user ON face_encodings(user_id);
CREATE INDEX idx_face_image ON face_encodings(image_id);
CREATE INDEX idx_face_images_user ON face_images(user_id, is_primary);

-- Audit
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_date ON audit_logs(created_at);

-- Refresh tokens
CREATE INDEX idx_refresh_user ON refresh_tokens(user_id);
```

Ajoute également, si `pgvector` est disponible, un index approprié pour la recherche de similarité sur `face_encodings.encoding` (ex: `ivfflat` avec `vector_cosine_ops` ou `vector_l2_ops`), avec un commentaire expliquant le choix de l'opérateur (`<->` distance euclidienne vs `<=>` cosinus) selon l'algorithme de reconnaissance faciale utilisé en amont (ex: face_recognition / dlib utilise une distance euclidienne).

---

## Règles métier à encoder en contraintes SQL (pas seulement en commentaire)

1. Un utilisateur ne peut pas avoir deux pointages pour la même session → `UNIQUE(user_id, session_id)`.
2. Un utilisateur ne peut avoir qu'un seul pointage "libre" (sans session) par jour → index unique partiel sur `(user_id, record_date) WHERE session_id IS NULL`.
3. `check_out` doit toujours être postérieur à `check_in` quand il est renseigné.
4. `end_time` d'une session doit toujours être postérieur à `start_time`.
5. Un encodage facial doit avoir au moins une des deux représentations (`encoding` vecteur ou `encoding_json`) non nulle.
6. `email` et `identifier` (matricule) doivent être uniques dans `users` (l'unicité de `identifier` ne s'applique qu'aux valeurs non nulles — comportement standard PostgreSQL).

---

## Structure attendue de la réponse

Produis le script dans cet ordre, avec des sections clairement délimitées par des commentaires `-- ====== NOM DE SECTION ======` :

1. Extensions (`pgcrypto`, tentative `vector`)
2. Nettoyage optionnel (DROP CASCADE, commenté/désactivable)
3. Types ENUM
4. Fonction + trigger générique `updated_at`
5. Création des tables dans l'ordre des dépendances (avec contraintes inline et `COMMENT ON`)
6. Index de performance
7. Contraintes d'intégrité supplémentaires (si non inline)
8. Vues utilitaires
9. Données de test (seed) — section optionnelle clairement isolée
10. Un court résumé en commentaire final listant les vérifications post-déploiement recommandées (ex: `\d+ attendance_records`, test d'insertion d'un doublon pour valider les contraintes)

Le script final doit être **un seul bloc SQL valide**, copiable-collable tel quel dans `psql` ou un client comme DBeaver/pgAdmin, sans placeholder à compléter.
