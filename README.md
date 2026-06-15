# FaceAttend — Reconnaissance Faciale pour le Pointage

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green?logo=fastapi)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)

**FaceAttend** est un système complet de gestion de pointage et de présence basé sur la reconnaissance faciale. Il combine un backend FastAPI avec une base PostgreSQL, une interface React moderne, et des algorithmes de vision par ordinateur (face_recognition / dlib) pour identifier les utilisateurs et enregistrer leurs présences automatiquement.

---

## Prérequis

- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/install/) (v2+)
- Python 3.11+ (pour développement local)
- Node.js 18+ (pour développement local)

## Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/your-org/faceattend.git
cd faceattend
```

### 2. Configurer l'environnement

```bash
cp .env.example .env
# Éditer .env avec vos valeurs (clé secrète, mots de passe, etc.)
```

### 3. Lancer avec Docker Compose

```bash
docker compose up -d
```

Accès :
- Frontend : http://localhost:5173
- API : http://localhost:8000
- Swagger UI : http://localhost:8000/docs
- ReDoc : http://localhost:8000/redoc
- PgAdmin : http://localhost:5050

### 4. Développement local sans Docker

**Backend :**

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Démarrer PostgreSQL (via Docker)
docker run -d --name faceattend-pg -e POSTGRES_USER=faceattend \
  -e POSTGRES_PASSWORD=password -e POSTGRES_DB=faceattend \
  -p 5432:5432 postgres:15

# Appliquer les migrations
alembic upgrade head

# Lancer l'API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend :**

```bash
cd frontend
npm install
npm run dev
```

---

## Structure du Projet

```
faceattend/
├── .env.example              # Variables d'environnement
├── docker-compose.yml        # Orchestration Docker
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/         # Migrations Alembic
│   └── app/
│       ├── main.py           # Point d'entrée FastAPI
│       ├── database.py       # Session asynchrone SQLAlchemy
│       ├── core/
│       │   ├── config.py     # Configuration Pydantic
│       │   ├── security.py   # JWT, hash, verify
│       │   └── dependencies.py
│       ├── models/           # ORM SQLAlchemy
│       ├── schemas/          # Pydantic v2
│       ├── services/         # Logique métier
│       └── routers/          # Endpoints API
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── router/
        ├── contexts/
        ├── hooks/
        ├── services/         # Appels API Axios
        ├── layouts/
        ├── pages/
        └── components/
```

---

## Endpoints API Résumés

| Méthode | Endpoint | Description | Accès |
|---------|----------|-------------|-------|
| POST | /api/v1/auth/register | Inscription | Public |
| POST | /api/v1/auth/login | Connexion | Public |
| POST | /api/v1/auth/refresh | Rafraîchir token | Public |
| POST | /api/v1/auth/logout | Déconnexion | Auth |
| GET | /api/v1/auth/me | Profil connecté | Auth |
| GET | /api/v1/users | Liste utilisateurs | Admin |
| POST | /api/v1/users | Créer utilisateur | Admin |
| GET | /api/v1/users/{id} | Détail utilisateur | Admin |
| PUT | /api/v1/users/{id} | Modifier utilisateur | Admin |
| DELETE | /api/v1/users/{id} | Supprimer (logique) | Admin |
| POST | /api/v1/users/{id}/photo | Upload photo | Admin |
| POST | /api/v1/face/upload | Enregistrer encodage facial | Auth |
| POST | /api/v1/face/recognize | Reconnaître visage | Auth |
| GET | /api/v1/face/encodings/{user_id} | Encodages d'un utilisateur | Auth |
| DELETE | /api/v1/face/encodings/{id} | Supprimer encodage | Auth |
| POST | /api/v1/attendance/check-in | Pointer arrivée | Auth |
| POST | /api/v1/attendance/check-out | Pointer départ | Auth |
| GET | /api/v1/attendance | Historique pointages | Auth |
| GET | /api/v1/attendance/{id} | Détail pointage | Auth |
| PUT | /api/v1/attendance/{id} | Corriger pointage | Admin |
| GET | /api/v1/attendance/report/daily | Rapport journalier | Auth |
| GET | /api/v1/attendance/report/monthly | Rapport mensuel | Auth |
| GET | /api/v1/attendance/report/export | Export CSV | Auth |
| GET | /api/v1/dashboard/stats | Statistiques tableau de bord | Auth |

---

## Captures d'écran

*(À venir)*

---

## Licence

MIT
