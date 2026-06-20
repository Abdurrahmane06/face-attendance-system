# Guide d'installation et d'exécution du projet

Système de pointage par reconnaissance faciale — Base de données PostgreSQL

---

## Table des matières

1. [Arborescence du projet](#1-arborescence-du-projet)
2. [Prérequis](#2-prérequis)
3. [Installation par OS](#3-installation-par-os)
   - [Ubuntu / Debian](#31-ubuntu--debian)
   - [Fedora / RHEL](#32-fedora--rhel)
   - [Arch Linux](#33-arch-linux)
   - [Windows](#34-windows)
4. [Initialisation de la base](#4-initialisation-de-la-base)
5. [Exécution des tests](#5-exécution-des-tests)
6. [Commandes utiles](#6-commandes-utiles)
7. [Dépannage](#7-dépannage)

---

## 1. Arborescence du projet

```
data_base/
├── init.sql           # Script SQL principal — crée toute la base
├── test_schema.pg     # Tests pgTAP (221 tests) — valide le schéma
├── run_pgtap.sh       # Script bash — installe pgTAP + lance les tests
├── prompt-sql.md      # Prompt original utilisé pour générer init.sql
├── schema.md          # Documentation détaillée du modèle de données
└── GUIDE.md           # Ce fichier — guide d'installation
```

### Rôle de chaque fichier

| Fichier | Rôle | Obligatoire ? |
|---|---|---|
| `init.sql` | Crée toute la structure (tables, index, vues, contraintes) et insère des données de test. C'est le cœur du projet. | Oui |
| `test_schema.pg` | Script de tests unitaires pgTAP qui vérifie que le schéma est correct (types, colonnes, contraintes, index, vues, données). | Tests uniquement |
| `run_pgtap.sh` | Automatise l'installation de pgTAP et l'exécution des tests. Utile mais non indispensable. | Optionnel |
| `schema.md` | Documentation du modèle : dictionnaire des 9 tables, relations, index, contraintes. À lire pour comprendre la structure. | Lecture uniquement |
| `prompt-sql.md` | Prompt qui a servi à générer `init.sql`. Gardé pour traçabilité. | Lecture uniquement |

---

## 2. Prérequis

- **PostgreSQL 14+** (recommandé 15/16/17/18)
- **psql** (client PostgreSQL en ligne de commande)
- **pgTAP** (uniquement pour les tests)

Vérifier la version de PostgreSQL :
```bash
psql --version
pg_isready
```

---

## 3. Installation par OS

### 3.1 Ubuntu / Debian

```bash
# Mettre à jour les paquets
sudo apt update

# Installer PostgreSQL
sudo apt install -y postgresql postgresql-client

# Démarrer le service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Passer à l'utilisateur postgres
sudo -i -u postgres

# Créer l'utilisateur et la base
createuser --createdb --pwprompt faceattend
createdb -O faceattend faceattend

# Quitter l'utilisateur postgres
exit

# Installer pgTAP (pour les tests)
sudo apt install -y postgresql-16-pgtap
# Adapter le numéro à votre version (15, 14, etc.)
```

### 3.2 Fedora / RHEL

```bash
# Installer PostgreSQL
sudo dnf install -y postgresql-server postgresql-contrib

# Initialiser et démarrer
sudo postgresql-setup --initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Créer l'utilisateur et la base
sudo -i -u postgres
createuser --createdb --pwprompt faceattend
createdb -O faceattend faceattend
exit

# Installer pgTAP
sudo dnf install -y pgtap
```

### 3.3 Arch Linux

```bash
# Installer PostgreSQL
sudo pacman -S postgresql

# Initialiser le cluster (si première installation)
sudo -i -u postgres initdb --locale en_US.UTF-8 -D /var/lib/postgres/data

# Démarrer le service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Créer l'utilisateur et la base
sudo -i -u postgres
createuser --createdb --pwprompt faceattend
createdb -O faceattend faceattend
exit

# Installer pgTAP (depuis AUR)
# Avec yay :
yay -S pgtap

# Avec paru :
paru -S pgtap
```

### 3.4 Windows

#### Option 1 : Installation native

1. Télécharger PostgreSQL depuis [https://www.postgresql.org/download/windows/](https://www.postgresql.org/download/windows/)
2. Lancer l'installateur, noter le mot de passe défini pour `postgres`
3. Ajouter `C:\Program Files\PostgreSQL\<version>\bin` au PATH
4. Ouvrir **PowerShell** ou **cmd** en administrateur :

```powershell
# Créer la base (depuis PowerShell/cmd)
createdb -U postgres faceattend
```

#### Option 2 : Docker (recommandé sur Windows)

```powershell
# Démarrer PostgreSQL dans un conteneur
docker run -d `
  --name faceattend-db `
  -e POSTGRES_USER=faceattend `
  -e POSTGRES_PASSWORD=password `
  -e POSTGRES_DB=faceattend `
  -p 5432:5432 `
  postgres:16

# Installer pgTAP dans le conteneur
docker exec faceattend-db bash -c "
  apt-get update && \
  apt-get install -y postgresql-16-pgtap
"
```

---

## 4. Initialisation de la base

Une fois PostgreSQL installé et la base `faceattend` créée, exécuter le script principal.

### Linux (Ubuntu / Fedora / Arch)

```bash
# Se placer dans le dossier du projet
cd /chemin/vers/data_base

# Exécuter le script SQL
psql -d faceattend -f init.sql
```

### Windows (PowerShell)

```powershell
cd C:\chemin\vers\data_base
psql -U faceattend -d faceattend -f init.sql
```

### Windows (Docker)

```powershell
docker cp init.sql faceattend-db:/tmp/
docker exec faceattend-db psql -U faceattend -d faceattend -f /tmp/init.sql
```

### Que fait `init.sql` ?

1. **Active pgcrypto** — pour la génération d'UUID
2. **Nettoie** les tables existantes (DROP IF EXISTS — sans risque en dev)
3. **Crée 3 types ENUM** : `profile_type`, `auth_role`, `attendance_method`
4. **Crée 9 tables** : `users`, `groups`, `user_groups`, `sessions`, `face_images`, `face_encodings`, `attendance_records`, `audit_logs`, `refresh_tokens`
5. **Ajoute les index** : 15 index de performance + 2 index d'unicité
6. **Crée 3 vues** : sessions actives, dernier pointage, résumé quotidien
7. **Insère des données de test** : 6 utilisateurs, 3 groupes, 2 sessions, 3 pointages

---

## 5. Exécution des tests

Les tests utilisent **pgTAP** (221 tests) pour valider la structure du schéma.

### Activer pgTAP dans la base

```bash
# Tous les OS
psql -d faceattend -c "CREATE EXTENSION IF NOT EXISTS pgtap"
```

### Lancer les tests

```bash
# Linux
psql -d faceattend -f test_schema.pg

# Windows (PowerShell)
psql -U faceattend -d faceattend -f test_schema.pg

# Windows (Docker)
docker cp test_schema.pg faceattend-db:/tmp/
docker exec faceattend-db psql -U faceattend -d faceattend -f /tmp/test_schema.pg
```

### Utiliser le script automatisé

```bash
# Linux uniquement
./run_pgtap.sh
```

### Résultat attendu

Si tout est OK, la sortie se termine par :
```
221..221
ok 221 - ...
# All 221 tests passed.
ROLLBACK
```

> Les tests sont dans une transaction `ROLLBACK` : ils ne modifient pas les données.

### Ce que testent les 221 tests

| Catégorie | Nombre de tests |
|---|---|
| Extensions et types ENUM | 6 |
| Trigger function | 3 |
| Table users (colonnes, types, PK, defaults, index, trigger) | ~30 |
| Table groups | ~10 |
| Table user_groups (PK composite, FK) | 6 |
| Table sessions (colonnes, CHECK) | ~15 |
| Table face_images | ~10 |
| Table face_encodings (CHECK, type VECTOR/TEXT) | ~15 |
| Table attendance_records (colonnes, CHECK, index uniques) | ~35 |
| Table audit_logs | ~12 |
| Table refresh_tokens | ~12 |
| Index de performance | 14 |
| Vues | 3 |
| Données seed (intégrité) | 8 |
| Tests comportementaux (contraintes, trigger) | ~10 |

---

## 6. Commandes utiles

### Vérifier la structure

```bash
# Lister les tables
psql -d faceattend -c "\dt"

# Voir les détails d'une table
psql -d faceattend -c "\d+ attendance_records"

# Voir les vues
psql -d faceattend -c "\dv"

# Voir les indexes
psql -d faceattend -c "\di"
```

### Interroger les vues

```bash
# Sessions actives aujourd'hui
psql -d faceattend -c "SELECT * FROM v_active_sessions_today;"

# Dernier pointage par utilisateur
psql -d faceattend -c "SELECT * FROM v_user_last_attendance;"

# Résumé quotidien
psql -d faceattend -c "SELECT * FROM v_daily_attendance_summary;"
```

### Réinitialiser la base

```bash
# Supprimer et recréer
dropdb faceattend
createdb faceattend
psql -d faceattend -f init.sql
```

---

## 7. Dépannage

### `psql: command not found`

Le client PostgreSQL n'est pas installé ou pas dans le PATH.

```bash
# Ubuntu/Debian
sudo apt install postgresql-client

# Fedora
sudo dnf install postgresql

# Arch
sudo pacman -S postgresql

# Windows
Ajouter C:\Program Files\PostgreSQL\16\bin au PATH
```

### `database "faceattend" already exists`

La base existe déjà. Utiliser `dropdb` d'abord ou ignorer l'erreur.

### `FATAL: password authentication failed`

Définir le mot de passe avec la variable d'environnement :
```bash
export PGPASSWORD="votre_mot_de_passe"
```

Ou utiliser le fichier `.pgpass` :
```bash
echo "localhost:5432:faceattend:faceattend:password" >> ~/.pgpass
chmod 600 ~/.pgpass
```

### `permission denied to create extension "pgtap"`

Se connecter avec un superutilisateur (ex: `postgres`) :
```bash
psql -U postgres -d faceattend -c "CREATE EXTENSION IF NOT EXISTS pgtap"
```

### pgTAP non trouvé par `CREATE EXTENSION`

L'extension n'est pas installée sur le système. Voir la section [Installation par OS](#3-installation-par-os) pour votre distribution.
