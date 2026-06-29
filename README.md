# FaceAttend — Système de Pointage par Reconnaissance Faciale

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green?logo=fastapi)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)

**FaceAttend** est un système complet de gestion de présence basé sur la reconnaissance faciale. Il combine un backend FastAPI asynchrone, une base PostgreSQL 15, une interface React moderne et des algorithmes de vision par ordinateur (face_recognition / dlib) pour identifier les employés et enregistrer leurs arrivées et départs automatiquement.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        Docker Compose                        │
│                                                              │
│  ┌─────────────┐    ┌─────────────────┐    ┌─────────────┐  │
│  │  React/Vite │    │    FastAPI       │    │ PostgreSQL  │  │
│  │  :5173      │───▶│    :8000         │───▶│    :5432    │  │
│  │             │    │  (asyncpg +      │    │             │  │
│  │ Tailwind CSS│    │   SQLAlchemy 2)  │    │  Alembic    │  │
│  └─────────────┘    └─────────────────┘    └─────────────┘  │
│                              │                               │
│                    ┌─────────────────┐                       │
│                    │    PgAdmin 4    │                       │
│                    │     :5050       │                       │
│                    └─────────────────┘                       │
└──────────────────────────────────────────────────────────────┘
```

**Flux de pointage :**
`Webcam → capture JPEG → POST /face/recognize → match dlib 128-D → check-in/check-out`

---

## Prérequis

| Outil | Version minimum |
|-------|----------------|
| Docker | 24+ |
| Docker Compose | v2+ (intégré à Docker Desktop) |
| Python | 3.11+ (dev local uniquement) |
| Node.js | 18+ (dev local uniquement) |

---

## Démarrage rapide (Docker)

### 1. Cloner le dépôt

```bash
git clone https://github.com/your-org/faceattend.git
cd faceattend
```

### 2. Configurer l'environnement

```bash
cp .env.example .env
```

Éditer `.env` — au minimum changer :

```env
POSTGRES_PASSWORD=un_mot_de_passe_fort
SECRET_KEY=<sortie de : python -c "import secrets; print(secrets.token_hex(32))">
PGADMIN_PASSWORD=un_autre_mdp
```

### 3. Construire et démarrer

```bash
docker compose up --build -d
```

Le premier démarrage compile dlib (≈ 10-15 min selon la machine). Les démarrages suivants utilisent le cache Docker.

L'ordre de démarrage est automatique :
1. **db** — PostgreSQL attend le healthcheck
2. **backend** — exécute `alembic upgrade head` puis uvicorn
3. **frontend** — Vite en mode dev HMR
4. **pgadmin** — interface web PostgreSQL

### 4. Accès

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| API REST | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| PgAdmin | http://localhost:5050 |

### 5. Créer le premier compte administrateur

**Option A — Endpoint REST (recommandé) :**

```bash
curl -X POST http://localhost:8000/api/v1/auth/seed-admin \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@faceattend.com", "password": "Admin@1234!", "full_name": "Administrateur"}'
```

Cet endpoint échoue si un admin existe déjà (protection idempotente).

**Option B — Script interactif :**

```bash
docker exec -it faceattend-backend python scripts/create_admin.py
```

### 6. Se connecter

Ouvrir http://localhost:5173 → formulaire de connexion → entrer les identifiants créés à l'étape 5.

- **Admin** → redirigé vers `/dashboard`
- **Employé** → redirigé vers `/pointage`

---

## Variables d'environnement

Toutes les variables sont dans le fichier `.env` racine (chargé par docker-compose).

| Variable | Défaut | Description |
|----------|--------|-------------|
| `POSTGRES_USER` | `faceattend` | Utilisateur PostgreSQL |
| `POSTGRES_PASSWORD` | *(obligatoire)* | Mot de passe PostgreSQL |
| `POSTGRES_DB` | `faceattend` | Nom de la base |
| `SECRET_KEY` | *(obligatoire)* | Clé de signature JWT — hex 64 chars |
| `ALGORITHM` | `HS256` | Algorithme JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Durée de vie du token d'accès |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Durée de vie du refresh token |
| `FACE_TOLERANCE` | `0.6` | Seuil de distance dlib (0=strict, 1=permissif) |
| `UPLOAD_DIR` | `./uploads` | Répertoire des photos uploadées |
| `MAX_UPLOAD_SIZE_MB` | `10` | Taille max d'un upload image |
| `ALLOWED_ORIGINS` | `http://localhost:5173,...` | CORS origins autorisées |
| `ENVIRONMENT` | `development` | `development` ou `production` |
| `LOG_LEVEL` | `INFO` | Niveau de log Python |
| `PGADMIN_EMAIL` | `admin@faceattend.io` | Email de connexion PgAdmin |
| `PGADMIN_PASSWORD` | *(obligatoire)* | Mot de passe PgAdmin |

---

## Pages Frontend

| Route | Accès | Description |
|-------|-------|-------------|
| `/login` | Public | Connexion email + mot de passe |
| `/pointage` | Tout utilisateur auth. | Webcam → reconnaissance → Entrée / Sortie |
| `/dashboard` | Admin | KPIs, graphiques, derniers pointages |
| `/employees` | Admin | Liste des employés, création, encodage facial |
| `/employees/:id` | Admin | Détail employé + gestion des encodages faciaux |
| `/attendance` | Admin | Historique paginé avec filtres |
| `/reports` | Admin | Rapport mensuel + export CSV |

---

## API — Endpoints principaux

### Authentification

| Méthode | Endpoint | Accès | Description |
|---------|----------|-------|-------------|
| `POST` | `/api/v1/auth/register` | Admin | Créer un compte USER (réservé aux admins) |
| `POST` | `/api/v1/auth/login` | Public | Connexion → tokens JWT |
| `POST` | `/api/v1/auth/refresh` | Public | Renouveler l'access token |
| `POST` | `/api/v1/auth/logout` | Auth | Révoquer le refresh token |
| `GET` | `/api/v1/auth/me` | Auth | Profil de l'utilisateur connecté |
| `POST` | `/api/v1/auth/seed-admin` | Public* | Créer le premier admin (*bloqué si déjà existant) |

### Utilisateurs

| Méthode | Endpoint | Accès | Description |
|---------|----------|-------|-------------|
| `GET` | `/api/v1/users` | Admin | Liste paginée (search, department) |
| `POST` | `/api/v1/users` | Admin | Créer un utilisateur (rôle au choix) |
| `GET` | `/api/v1/users/{id}` | Admin | Détail utilisateur |
| `PUT` | `/api/v1/users/{id}` | Admin | Modifier un utilisateur |
| `DELETE` | `/api/v1/users/{id}` | Admin | Désactivation logique (soft-delete) |
| `POST` | `/api/v1/users/{id}/photo` | Admin | Upload photo de profil |

### Reconnaissance faciale

| Méthode | Endpoint | Accès | Description |
|---------|----------|-------|-------------|
| `POST` | `/api/v1/face/upload` | Auth | Enregistrer son propre encodage facial |
| `POST` | `/api/v1/face/upload/{user_id}` | Admin | Enregistrer l'encodage d'un autre utilisateur |
| `POST` | `/api/v1/face/recognize` | Auth | Identifier un visage (retourne `user_id` + `confidence`) |
| `GET` | `/api/v1/face/encodings/{user_id}` | Auth | Lister les encodages actifs d'un utilisateur |
| `DELETE` | `/api/v1/face/encodings/{id}` | Auth | Supprimer un encodage (soft-delete) |

### Pointage

| Méthode | Endpoint | Accès | Description |
|---------|----------|-------|-------------|
| `POST` | `/api/v1/attendance/check-in` | Auth | Enregistrer une arrivée |
| `POST` | `/api/v1/attendance/check-out` | Auth | Enregistrer un départ |
| `GET` | `/api/v1/attendance` | Auth | Historique paginé (filtres : user_id, dates, statut) |
| `GET` | `/api/v1/attendance/{id}` | Auth | Détail d'un pointage |
| `PUT` | `/api/v1/attendance/{id}` | Admin | Corriger un pointage |
| `GET` | `/api/v1/attendance/report/daily` | Auth | Rapport journalier (présents/retards/absents) |
| `GET` | `/api/v1/attendance/report/monthly` | Auth | Rapport mensuel (stats par jour) |
| `GET` | `/api/v1/attendance/report/export` | Auth | Export CSV du mois (UTF-8 BOM, compatible Excel) |

### Dashboard

| Méthode | Endpoint | Accès | Description |
|---------|----------|-------|-------------|
| `GET` | `/api/v1/dashboard/stats` | Auth | KPIs + graphiques 7 jours + derniers pointages |

---

## Structure du projet

```
faceattend/
├── .env.example              ← Copier en .env
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       └── 0001_initial_schema.py   ← Migration complète
│   ├── scripts/
│   │   └── create_admin.py              ← CLI seed admin
│   └── app/
│       ├── main.py
│       ├── database.py                  ← AsyncSession SQLAlchemy
│       ├── core/
│       │   ├── config.py               ← Settings Pydantic
│       │   ├── security.py             ← JWT + bcrypt
│       │   └── dependencies.py         ← get_db, get_current_user, require_admin
│       ├── models/                      ← ORM SQLAlchemy 2.0
│       │   ├── user.py                 ← soft-delete via deleted_at + hybrid is_active
│       │   ├── attendance.py
│       │   ├── face_encoding.py
│       │   ├── work_schedule.py
│       │   ├── absence_type.py
│       │   ├── justification.py
│       │   └── refresh_token.py
│       ├── schemas/                     ← Pydantic v2
│       ├── services/                    ← Logique métier
│       │   ├── auth_service.py
│       │   ├── user_service.py
│       │   ├── face_service.py          ← dlib, io.BytesIO, joinedload
│       │   └── attendance_service.py    ← Détection retard via WorkSchedule
│       └── routers/
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    └── src/
        ├── contexts/AuthContext.jsx     ← État global auth
        ├── hooks/
        │   ├── useAuth.js
        │   ├── useFaceCamera.js         ← getUserMedia + capture + recognize
        │   └── useAttendance.js
        ├── services/                    ← Axios + intercepteur JWT auto-refresh
        │   ├── api.js
        │   ├── authService.js
        │   ├── faceService.js
        │   ├── attendanceService.js
        │   └── userService.js
        ├── router/index.jsx             ← Routes protégées par rôle
        ├── layouts/
        ├── pages/
        │   ├── Login.jsx
        │   ├── FaceRecognition.jsx      ← /pointage
        │   ├── Dashboard.jsx            ← Admin
        │   ├── Users.jsx                ← /employees (Admin)
        │   ├── UserDetail.jsx           ← /employees/:id + encodages faciaux
        │   ├── Attendance.jsx
        │   └── Reports.jsx
        └── components/
            ├── FaceCamera.jsx           ← Entrée + Sortie après reconnaissance
            └── UserForm.jsx             ← Création + upload photo optionnel
```

---

## Développement local (sans Docker)

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# PostgreSQL via Docker (si pas installé localement)
docker run -d --name pg15 \
  -e POSTGRES_USER=faceattend -e POSTGRES_PASSWORD=password -e POSTGRES_DB=faceattend \
  -p 5432:5432 postgres:15

# Copier et ajuster les variables
cp .env.example .env

# Appliquer les migrations
alembic upgrade head

# Lancer l'API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

---

## Commandes utiles

```bash
# Logs en temps réel
docker compose logs -f backend
docker compose logs -f frontend

# Appliquer de nouvelles migrations
docker exec faceattend-backend alembic upgrade head

# Créer un admin (interactif)
docker exec -it faceattend-backend python scripts/create_admin.py

# Redémarrer un service
docker compose restart backend

# Arrêter tout (conserver les données)
docker compose down

# Arrêter et supprimer les volumes (reset complet)
docker compose down -v
```

---

## Modèle de données

```
work_schedules ──┐
                 │  (FK optionnelle)
users ───────────┼────── face_encodings
  │              │       refresh_tokens
  │              └────── attendances ── justifications
  │                           │
  │                      absence_types
  └──── (soft-delete via deleted_at)
```

Tous les modèles utilisent :
- **UUID** comme clé primaire
- **`created_at` / `deleted_at`** en `TIMESTAMPTZ`
- **Soft-delete** — les lignes ne sont jamais supprimées physiquement

---

## Licence

MIT
