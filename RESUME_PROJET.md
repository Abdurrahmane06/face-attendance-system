# FaceAttend — Résumé du projet

---

## 1. Présentation générale

**Nom du projet :** FaceAttend

**Description :** Système de gestion des présences par reconnaissance faciale, orchestré via Docker Compose.

**Objectif fonctionnel :** Permettre aux employés de pointer leur arrivée et leur départ via une webcam (ou manuellement), et donner aux administrateurs une vue en temps réel des présences, des retards et des absences, avec des rapports exportables en CSV.

---

## 2. Architecture

### Services Docker

| Service      | Technologie          | Version     | Port exposé |
|--------------|----------------------|-------------|-------------|
| `db`         | PostgreSQL           | 15-alpine   | 5432        |
| `backend`    | FastAPI (Python)     | 3.11-slim   | 8000        |
| `frontend`   | React + Vite (Node)  | node:20     | 5173        |
| `pgadmin`    | pgAdmin 4            | latest      | 5050        |

### Communication entre services

```
Navigateur (5173)
    │
    ├── [HTTP/REST] → backend:8000  (API FastAPI)
    │                     │
    │                     └── [asyncpg] → db:5432  (PostgreSQL)
    │
    └── [HTTP/80] → pgadmin:5050  (interface admin DB)
                        │
                        └── [psql] → db:5432
```

- Le **frontend** communique avec le backend via `VITE_API_URL=http://localhost:8000/api/v1`.
- Le **backend** utilise `asyncpg` pour les requêtes applicatives et `psycopg2` (sync) pour les migrations Alembic.
- Les migrations s'exécutent automatiquement au démarrage du conteneur backend, avant le lancement d'uvicorn.
- Le backend attend que la base soit `healthy` (via `depends_on` + `healthcheck`) avant de démarrer.

---

## 3. Stack technique

### Backend (`backend/`)

| Composant           | Technologie / Version              |
|---------------------|------------------------------------|
| Langage             | Python 3.11                        |
| Framework           | FastAPI ≥ 0.104                    |
| Serveur ASGI        | Uvicorn (avec `uvloop`, `watchfiles`) |
| ORM                 | SQLAlchemy 2.0 (mode async)        |
| Driver DB (app)     | asyncpg ≥ 0.29                     |
| Driver DB (Alembic) | psycopg2-binary (sync, installé au démarrage) |
| Migrations          | Alembic ≥ 1.13                     |
| Validation          | Pydantic v2 + pydantic-settings    |
| Authentification    | python-jose (JWT HS256)            |
| Hachage mot de passe | bcrypt ≥ 4.0 (direct, sans passlib) |
| Reconnaissance faciale | face_recognition 1.3 (dlib backend) |
| Traitement image    | OpenCV (headless) + Pillow         |
| Calcul vectoriel    | NumPy < 2.0 (numpy 2.x incompatible dlib) |

### Frontend (`frontend/`)

| Composant        | Technologie / Version     |
|------------------|---------------------------|
| Framework UI     | React 18.2                |
| Build tool       | Vite 5.0                  |
| Routing          | react-router-dom 6.30     |
| Appels HTTP      | axios 1.6                 |
| Graphiques       | recharts 2.15             |
| CSS              | Tailwind CSS 3.3          |

### Base de données

| Aspect             | Détail                                                 |
|--------------------|--------------------------------------------------------|
| Moteur             | PostgreSQL 15                                          |
| Clés primaires     | UUID v4 (stockés en `VARCHAR`, non `uuid` natif)       |
| Suppression        | Soft-delete via colonne `deleted_at TIMESTAMPTZ NULL`  |
| Horodatage         | `TIMESTAMPTZ` pour toutes les colonnes temporelles     |
| Types ENUM         | 3 types Postgres : `user_role`, `attendance_status`, `recognition_method` |
| Contrainte unicité | `UNIQUE(user_id, date)` sur `attendances`              |

---

## 4. Fonctionnalités principales

### 4.1 Authentification (JWT avec refresh token)

Fichiers : `backend/app/services/auth_service.py`, `backend/app/core/security.py`

- **Connexion** (`POST /api/v1/auth/login`) : vérifie email + mot de passe hashé en bcrypt, retourne un access token (HS256, 30 min) et un refresh token (7 jours).
- **Renouvellement** (`POST /api/v1/auth/refresh`) : échange un refresh token valide et non révoqué contre un nouvel access token.
- **Déconnexion** (`POST /api/v1/auth/logout`) : marque le refresh token comme révoqué en base (`is_revoked = true`).
- **Profil courant** (`GET /api/v1/auth/me`) : retourne les informations de l'utilisateur authentifié.
- **Bootstrap admin** (`POST /api/v1/auth/seed-admin`) : crée le tout premier compte ADMIN ; échoue avec 409 si un admin existe déjà. Endpoint public sans authentification.
- **Création de compte** (`POST /api/v1/auth/register`) : réservé aux admins (requiert un JWT admin). Toujours crée un compte avec rôle USER.
- Les refresh tokens sont persistés en base (`refresh_tokens`) pour permettre la révocation.
- Le frontend stocke les tokens dans `localStorage` et les envoie via l'en-tête `Authorization: Bearer <token>`.

### 4.2 Gestion des utilisateurs (admin uniquement)

Fichiers : `backend/app/routers/users.py`, `backend/app/services/user_service.py`

- **Lister** (`GET /api/v1/users`) : liste paginée (20/page) avec filtres par nom/email et département.
- **Créer** (`POST /api/v1/users`) : création d'un compte avec email, nom, mot de passe, rôle, département optionnel.
- **Lire** (`GET /api/v1/users/{id}`) : détail complet d'un utilisateur avec ses encodages faciaux.
- **Modifier** (`PUT /api/v1/users/{id}`) : mise à jour des champs email, nom, département, rôle, mot de passe, work_schedule.
- **Désactiver** (`DELETE /api/v1/users/{id}`) : soft-delete (pose `deleted_at`), le compte n'est plus accessible.
- **Photo de profil** (`POST /api/v1/users/{id}/photo`) : upload d'une image JPEG/PNG, stockée dans `./uploads/`, URL enregistrée dans `photo_url`.

### 4.3 Reconnaissance faciale

Fichiers : `backend/app/routers/face.py`, `backend/app/services/face_service.py`

- **Upload d'un encodage (propre)** (`POST /api/v1/face/upload`) : l'utilisateur connecté envoie une photo. Le service détecte exactement 1 visage, calcule un vecteur 128-D via `face_recognition.face_encodings()`, le sérialise en JSON et le persiste en base.
- **Upload pour un autre utilisateur** (`POST /api/v1/face/upload/{user_id}`) : même processus, réservé aux admins.
- **Reconnaissance** (`POST /api/v1/face/recognize`) : envoie une capture webcam. Le backend extrait le vecteur 128-D de l'image, le compare à tous les encodages actifs en base via distance euclidienne (`face_recognition.face_distance()`). Si la distance minimale ≤ `FACE_TOLERANCE` (défaut 0.6), retourne `recognized=true` avec l'identité et `confidence = 1 - distance`.
- **Lister les encodages** (`GET /api/v1/face/encodings/{user_id}`) : retourne tous les encodages actifs (non supprimés) d'un utilisateur.
- **Supprimer un encodage** (`DELETE /api/v1/face/encodings/{encoding_id}`) : soft-delete de l'encodage (pose `deleted_at`).
- La validation des images impose JPEG/PNG et une taille ≤ `MAX_UPLOAD_SIZE_MB` (défaut 10 Mo).

### 4.4 Pointage (check-in / check-out)

Fichiers : `backend/app/routers/attendance.py`, `backend/app/services/attendance_service.py`

- **Entrée** (`POST /api/v1/attendance/check-in`) : crée un enregistrement de présence pour la date du jour. Si l'heure dépasse `expected_start_time + grace_period_minutes` du planning de travail de l'utilisateur, le statut est `late` (avec le nombre de minutes de retard). Sinon `present`. Retourne 409 si déjà pointé.
- **Sortie** (`POST /api/v1/attendance/check-out`) : enregistre l'heure de départ en mettant à jour `check_out`.
- **Méthode de reconnaissance** : `FACE` (via webcam) ou `MANUAL` (sans reconnaissance).
- La logique de retard utilise un fuseau horaire UTC. En l'absence de planning assigné, le seuil par défaut est 09:00 UTC sans marge.
- Un seul enregistrement par utilisateur et par jour (contrainte `UNIQUE(user_id, date)`).

### 4.5 Historique des pointages

- **Lister** (`GET /api/v1/attendance`) : liste paginée filtrée par utilisateur, plage de dates, statut.
- **Détail** (`GET /api/v1/attendance/{id}`) : un enregistrement par UUID.
- **Corriger** (`PUT /api/v1/attendance/{id}`) : admin uniquement — permet de modifier check_in, check_out, statut, notes.

### 4.6 Rapports

Fichiers : `backend/app/routers/attendance.py`, `backend/app/services/attendance_service.py`

- **Rapport journalier** (`GET /api/v1/attendance/report/daily`) : pour une date donnée, retourne les compteurs présents/retards/absents et les listes de noms.
- **Rapport mensuel** (`GET /api/v1/attendance/report/monthly`) : pour un mois/année, retourne les statistiques par jour (présents, absents, retards, taux de présence) et le taux moyen mensuel.
- **Export CSV** (`GET /api/v1/attendance/report/export`) : génère un fichier CSV (UTF-8 BOM pour compatibilité Excel) avec les colonnes Date, Nom, Arrivée, Départ, Statut, Retard (min), Méthode.

### 4.7 Tableau de bord temps réel

Fichier : `backend/app/routers/dashboard.py`

- **Statistiques** (`GET /api/v1/dashboard/stats`) : retourne en une seule requête :
  - Nombre total d'utilisateurs actifs
  - Présents / Absents / Retards du jour
  - Taux de présence du jour (en %)
  - Taux de présence sur 7 jours glissants
  - Données de présence par jour sur les 7 derniers jours
  - 10 derniers pointages du jour avec heure et statut
- Le frontend interroge cet endpoint toutes les 30 secondes via `setInterval`.

### 4.8 Plannings de travail (work schedules)

Fichier : `backend/app/models/work_schedule.py`

- Table `work_schedules` avec heure de début attendue (`expected_start_time`) et marge de tolérance (`grace_period_minutes`).
- Chaque utilisateur peut se voir assigner un planning (FK nullable).
- Utilisé par le service de pointage pour calculer si un employé est en retard.

---

## 5. Rôles et permissions

Deux rôles définis par l'ENUM PostgreSQL `user_role` :

| Rôle    | Ce qu'il peut faire                                                                                       |
|---------|-----------------------------------------------------------------------------------------------------------|
| `ADMIN` | Tout : gérer les utilisateurs, consulter/corriger tous les pointages, accéder au tableau de bord et aux rapports, uploader les visages pour n'importe quel utilisateur, créer des comptes via `/auth/register` |
| `USER`  | Pointer sa présence (check-in/check-out) via la page Pointage ; uploader son propre encodage facial (`/face/upload`) ; consulter ses propres données via `/auth/me` |

**Restriction frontend :** les items de navigation `Dashboard`, `Pointages`, `Rapports`, `Employés` sont masqués pour les utilisateurs avec le rôle `USER` (`frontend/src/layouts/MainLayout.jsx`). Les routes admin (`/dashboard`, `/employees`, `/attendance`, `/reports`) sont protégées par `<ProtectedRoute requiredRole="ADMIN">`.

**Restriction backend :** toutes les routes de gestion utilisateurs (`/api/v1/users`) et la correction des pointages (`PUT /api/v1/attendance/{id}`) vérifient la dépendance `require_admin` qui retourne `403 Forbidden` si l'utilisateur n'est pas admin.

---

## 6. Pages de l'application

| Route              | Accès               | Description                                                                 |
|--------------------|---------------------|-----------------------------------------------------------------------------|
| `/login`           | Public              | Formulaire de connexion email/mot de passe. Redirige vers `/dashboard` (admin) ou `/pointage` (user). |
| `/`                | Tout utilisateur connecté | Redirige automatiquement vers `/dashboard` ou `/pointage` selon le rôle. |
| `/pointage`        | Tout utilisateur connecté | Reconnaissance faciale via webcam + boutons Entrée/Sortie. Affiche le résultat et le statut du pointage. |
| `/dashboard`       | ADMIN uniquement    | KPIs (total utilisateurs, présents, absents, retards), graphique 7 jours, donut de répartition, liste des derniers pointages. Rafraîchissement auto toutes les 30 s. |
| `/employees`       | ADMIN uniquement    | Liste paginée des employés avec recherche. Bouton de création d'un nouvel employé (modal `UserForm`). |
| `/employees/:id`   | ADMIN uniquement    | Détail d'un employé : informations de profil, liste des encodages faciaux avec suppression, upload d'une nouvelle photo de visage, bouton de désactivation du compte. |
| `/attendance`      | ADMIN uniquement    | Historique des pointages avec filtres par date et statut, paginé.           |
| `/reports`         | ADMIN uniquement    | Rapport mensuel (sélecteur mois/année), taux moyen, tableau jour par jour, bouton d'export CSV. |
| `/register`        | Existant mais injoignable | Page d'inscription présente dans le routeur mais sans lien d'accès. L'endpoint backend requiert un token admin. |
| `/404`             | Tous                | Page "Not found".                                                           |
| `*`                | Tous                | Toute URL inconnue redirige vers `/404`.                                    |

---

## 7. API

Base URL : `http://localhost:8000/api/v1`

Documentation interactive disponible sur `http://localhost:8000/docs` (Swagger UI).

### Authentification (`/auth`)

| Méthode | Chemin                  | Accès              | Description                                              |
|---------|-------------------------|--------------------|----------------------------------------------------------|
| POST    | `/auth/login`           | Public             | Connexion, retourne `access_token` + `refresh_token`     |
| POST    | `/auth/refresh`         | Public             | Échange un refresh token contre un nouveau access token  |
| POST    | `/auth/logout`          | Authentifié        | Révoque le refresh token (déconnexion)                   |
| GET     | `/auth/me`              | Authentifié        | Retourne le profil de l'utilisateur courant              |
| POST    | `/auth/register`        | Admin uniquement   | Crée un compte USER (rôle toujours USER)                 |
| POST    | `/auth/seed-admin`      | Public (une fois)  | Crée le premier compte ADMIN ; 409 si admin déjà existant |

### Utilisateurs (`/users`)

| Méthode | Chemin                   | Accès            | Description                                    |
|---------|--------------------------|------------------|------------------------------------------------|
| GET     | `/users`                 | Admin uniquement | Liste paginée, filtrée par nom/email/département |
| POST    | `/users`                 | Admin uniquement | Crée un utilisateur avec rôle configurable     |
| GET     | `/users/{id}`            | Admin uniquement | Détail d'un utilisateur + ses encodages        |
| PUT     | `/users/{id}`            | Admin uniquement | Met à jour les champs d'un utilisateur         |
| DELETE  | `/users/{id}`            | Admin uniquement | Soft-delete (désactivation du compte)          |
| POST    | `/users/{id}/photo`      | Admin uniquement | Upload de la photo de profil (JPEG/PNG ≤ 10 Mo) |

### Reconnaissance faciale (`/face`)

| Méthode | Chemin                        | Accès            | Description                                                  |
|---------|-------------------------------|------------------|--------------------------------------------------------------|
| POST    | `/face/upload`                | Authentifié      | Upload et enregistre l'encodage facial de l'utilisateur courant |
| POST    | `/face/upload/{user_id}`      | Admin uniquement | Upload et enregistre l'encodage d'un autre utilisateur       |
| POST    | `/face/recognize`             | Authentifié      | Compare une image aux encodages stockés, retourne l'identité |
| GET     | `/face/encodings/{user_id}`   | Authentifié      | Liste les encodages actifs d'un utilisateur                  |
| DELETE  | `/face/encodings/{encoding_id}` | Authentifié   | Soft-delete d'un encodage facial                             |

### Pointage (`/attendance`)

| Méthode | Chemin                           | Accès            | Description                                              |
|---------|----------------------------------|------------------|----------------------------------------------------------|
| POST    | `/attendance/check-in`           | Authentifié      | Enregistre l'arrivée du jour (statut `present` ou `late`) |
| POST    | `/attendance/check-out`          | Authentifié      | Enregistre le départ du jour                             |
| GET     | `/attendance`                    | Authentifié      | Liste paginée avec filtres (user, date, statut)          |
| GET     | `/attendance/{id}`               | Authentifié      | Détail d'un enregistrement par UUID                      |
| PUT     | `/attendance/{id}`               | Admin uniquement | Correction d'un enregistrement (heure, statut, notes)    |
| GET     | `/attendance/report/daily`       | Authentifié      | Résumé présents/absents/retards pour une date            |
| GET     | `/attendance/report/monthly`     | Authentifié      | Statistiques par jour pour un mois/année                 |
| GET     | `/attendance/report/export`      | Authentifié      | Téléchargement CSV du mois (UTF-8 BOM)                   |

### Tableau de bord (`/dashboard`)

| Méthode | Chemin             | Accès       | Description                                                        |
|---------|--------------------|-------------|--------------------------------------------------------------------|
| GET     | `/dashboard/stats` | Authentifié | KPIs du jour, tendance 7 jours, 10 derniers pointages              |

---

## 8. Base de données

### Tables

| Table              | Rôle                                                             | Colonnes principales                                                                                  |
|--------------------|------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------|
| `work_schedules`   | Plannings de travail nommés                                      | `id` (UUID), `name`, `expected_start_time` (TIME), `grace_period_minutes` (INT), `deleted_at`        |
| `users`            | Comptes utilisateurs (employés et admins)                        | `id` (UUID), `email` (UNIQUE), `full_name`, `hashed_password`, `role` (ENUM), `department`, `photo_url`, `work_schedule_id` (FK nullable), `deleted_at`, `created_at`, `updated_at` |
| `face_encodings`   | Vecteurs 128-D de reconnaissance faciale                         | `id` (UUID), `user_id` (FK), `encoding` (TEXT/JSON), `image_path`, `deleted_at`, `created_at`       |
| `absence_types`    | Types d'absences justifiables (structure, non utilisée en UI)    | `id` (UUID), `name`, `description`, `requires_justification` (BOOL), `deleted_at`                    |
| `attendances`      | Enregistrements journaliers de présence                          | `id` (UUID), `user_id` (FK), `date` (DATE), `check_in` (TIMESTAMPTZ), `check_out` (TIMESTAMPTZ), `status` (ENUM), `late_minutes`, `recognized_by` (ENUM), `notes`, `deleted_at` |
| `justifications`   | Justificatifs d'absence (structure, non utilisée en UI)          | `id` (UUID), `attendance_id` (FK), `absence_type_id` (FK), `comment`, `document_url`, `approved_by` (FK), `approved_at`, `deleted_at` |
| `refresh_tokens`   | Tokens JWT refresh persistés pour révocation                     | `id` (UUID), `user_id` (FK), `token` (UNIQUE), `expires_at`, `is_revoked` (BOOL), `created_at`      |

### Types ENUM PostgreSQL

| Nom                   | Valeurs                          |
|-----------------------|----------------------------------|
| `user_role`           | `ADMIN`, `USER`                  |
| `attendance_status`   | `present`, `late`, `absent`      |
| `recognition_method`  | `FACE`, `MANUAL`                 |

### Diagramme des relations

```
work_schedules
    │
    │ (0..1) work_schedule_id
    ▼
users ──────────────────────────────────────────┐
    │                                           │
    │ (1..N) user_id                            │ (0..N) approved_by
    ├────────────────┐                          │
    ▼                ▼                          │
face_encodings    attendances                   │
                      │                         │
                      │ (0..N) attendance_id    │
                      ▼                         │
                  justifications ───────────────┘
                      │
                      │ (N..1) absence_type_id
                      ▼
                  absence_types

users
    │
    │ (1..N) user_id
    ▼
refresh_tokens
```

**Clés :**
- `ON DELETE CASCADE` : `face_encodings`, `attendances`, `refresh_tokens` sont supprimés si l'utilisateur est supprimé.
- `ON DELETE SET NULL` : `work_schedule_id` est mis à NULL si le planning est supprimé.
- `ON DELETE RESTRICT` : `absence_type_id` dans `justifications` (le type ne peut être supprimé si des justificatifs y font référence).

---

## 9. Comment lancer le projet

### Prérequis

- Docker Desktop (ou Docker Engine + Docker Compose v2)
- Ports disponibles : `5432`, `8000`, `5173`, `5050`

### Étapes

**1. Cloner et préparer l'environnement :**

```bash
git clone <URL-du-dépôt>
cd face-attendance-system

# Copier et renseigner les variables d'environnement
cp .env.example .env

# Générer une clé secrète sécurisée pour SECRET_KEY dans .env :
python -c "import secrets; print(secrets.token_hex(32))"
```

**2. Lancer tous les services :**

```bash
docker compose up --build
```

Au démarrage, le backend :
- installe `psycopg2-binary`
- exécute les migrations Alembic (crée les 7 tables et les 3 ENUMs)
- lance uvicorn en mode `--reload`

**3. Créer le premier compte administrateur :**

```bash
curl -X POST http://localhost:8000/api/v1/auth/seed-admin \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "VotreMotDePasse123",
    "full_name": "Administrateur"
  }'
```

L'endpoint retourne un access token et un refresh token utilisables immédiatement.

**4. Se connecter via l'interface web :**

Se rendre sur `http://localhost:5173` et s'authentifier avec les identifiants du seed-admin.

### URLs d'accès

| Service          | URL                          | Identifiants (défaut .env.example)     |
|------------------|------------------------------|----------------------------------------|
| Application web  | `http://localhost:5173`      | Compte créé via seed-admin             |
| API (Swagger UI) | `http://localhost:8000/docs` | —                                      |
| API (ReDoc)      | `http://localhost:8000/redoc`| —                                      |
| PgAdmin          | `http://localhost:5050`      | `admin@faceattend.io` / voir `.env`    |
| PostgreSQL       | `localhost:5432`             | Voir variables `POSTGRES_*` dans `.env`|

### Arrêt et nettoyage

```bash
# Arrêter les services
docker compose down

# Arrêter et supprimer les volumes (efface la base de données)
docker compose down -v
```

### Fichiers de configuration

| Fichier            | Rôle                                                         |
|--------------------|--------------------------------------------------------------|
| `.env.example`     | Modèle de toutes les variables d'environnement (à copier en `.env`) |
| `.env`             | Variables effectives (non versionné)                         |
| `docker-compose.yml` | Définition des 4 services Docker                           |
| `backend/alembic.ini` | Configuration Alembic (URL résolue dynamiquement)         |
| `backend/alembic/env.py` | Utilise psycopg2 (sync) pour les migrations         |
