# Guide de configuration Supabase

> Mise en place de la base de données PostgreSQL pour le système de reconnaissance faciale — Gestion des présences

---

## Table des matières

1. [Créer un projet Supabase](#1-créer-un-projet-supabase)
2. [Récupérer les identifiants de connexion](#2-récupérer-les-identifiants-de-connexion)
3. [Exécuter le schéma SQL](#3-exécuter-le-schéma-sql)
4. [Configurer l'authentification (Auth)](#4-configurer-lauthentification-auth)
5. [Configurer le stockage (Storage)](#5-configurer-le-stockage-storage)
6. [Configurer les politiques de sécurité (RLS)](#6-configurer-les-politiques-de-sécurité-rls)
7. [Connecter le backend FastAPI](#7-connecter-le-backend-fastapi)
8. [Gestion des justificatifs d'absence](#8-gestion-des-justificatifs-dabsence)

---

## 1. Créer un projet Supabase

1. Rendez-vous sur [https://supabase.com](https://supabase.com) et connectez-vous.
2. Cliquez sur **New project**.
3. Remplissez les champs :
   - **Name** : `face-attendance` (ou le nom de votre choix)
   - **Database Password** : générez un mot de passe fort et conservez-le précieusement
   - **Region** : choisissez la région la plus proche de vos utilisateurs (ex. `Europe West`)
   - **Pricing Plan** : Free Tier (suffisant pour le développement)
4. Cliquez sur **Create new project**.
5. Attendez quelques minutes que la base de données soit provisionnée.

---

## 2. Récupérer les identifiants de connexion

Une fois le projet créé, allez dans **Project Settings > Database** :

```
URI de connexion (PostgreSQL) :
postgresql://postgres:[VOTRE-MOT-DE-PASSE]@db.[REF-PROJET].supabase.co:5432/postgres

URI de connexion (Pooler) :
postgresql://postgres:[VOTRE-MOT-DE-PASSE]@db.[REF-PROJET].supabase.co:6543/postgres?pgbouncer=true

Host :
db.[REF-PROJET].supabase.co
```

> **Note** : l'URI avec `pgbouncer=true` (port 6543) est recommandée pour les connexions depuis un environnement serverless ou une application externe. Pour FastAPI, utilisez cette URI.

Dans **Project Settings > API** vous trouverez :

```
Project URL      : https://[REF-PROJET].supabase.co
anon public key  : eyJhbGciOiJIUzI1NiIsInR5cCI6Ik... (clé publique)
service_role key : eyJhbGciOiJIUzI1NiIsInR5cCI6Ik... (clé secrète — à ne JAMAIS exposer côté client)
```

> **Important** : la `service_role key` permet de bypasser les RLS. Elle ne doit être utilisée que côté serveur (backend Python), jamais dans le navigateur ou l'application mobile.

---

## 3. Exécuter le schéma SQL

### 3.1 Accéder au SQL Editor

- Dans le dashboard Supabase, cliquez sur **SQL Editor** dans le menu de gauche.
- Cliquez sur **New Query**.

### 3.2 Coller et exécuter

1. Ouvrez le fichier [`schema.sql`](./schema.sql).
2. Copiez son contenu dans l'éditeur SQL.
3. Cliquez sur **Run** (ou `Cmd+Enter`).

### 3.3 Vérifier les tables

Après exécution, allez dans **Table Editor** pour vérifier que les 6 tables ont bien été créées :

- `profiles`
- `work_schedules`
- `employees`
- `attendance`
- `absence_types`
- `justifications`

Ouvrez chaque table pour confirmer la présence des données de test.

> **En cas d'erreur** : le message d'erreur le plus fréquent est `relation "auth.users" does not exist`. Cela signifie que la table `auth.users` n'existe pas encore car aucun utilisateur n'a été créé. Pour le développement, vous pouvez commenter temporairement la contrainte `REFERENCES auth.users(id)` sur `profiles.id`, exécuter le script, puis la rétablir après avoir créé vos utilisateurs. Solution alternative : exécutez d'abord l'étape 4 (créer des utilisateurs Auth), puis le schéma SQL.

---

## 4. Configurer l'authentification (Auth)

### 4.1 Activer la méthode de connexion

1. Allez dans **Authentication > Providers**.
2. Assurez-vous que **Email** est activé (c'est le cas par défaut).
3. Désactivez **Confirm email** si vous voulez que les utilisateurs soient actifs immédiatement (optionnel — déconseillé en production).

### 4.2 Créer les utilisateurs de test

Via la console Supabase :

1. Allez dans **Authentication > Users**.
2. Cliquez sur **Add User**.
3. Créez l'utilisateur admin :
   - **Email** : `admin@company.com`
   - **Password** : `password123` (changez pour la production)
   - Cliquez sur **Create user**.
4. Répétez pour l'utilisateur employee :
   - **Email** : `employee@company.com`
   - **Password** : `password123`

### 4.3 Récupérer les UUID

1. Allez dans **Authentication > Users**.
2. Notez les UUID des deux utilisateurs créés (colonne **ID**).
3. Si les UUID ne correspondent pas à ceux du script SQL (`a0eebc99-...` et `b0eebc99-...`), mettez à jour la table `profiles` :

```sql
-- Exemple : remplacer par les vrais UUID
UPDATE profiles SET id = 'UUID-REEL-DUP-ADMIN' WHERE display_name = 'Ahmed Benali';
UPDATE profiles SET id = 'UUID-REEL-DE-L-EMPLOYE' WHERE display_name = 'Sara Dupont';
UPDATE employees SET user_id = 'UUID-REEL-DUP-ADMIN' WHERE first_name = 'Ahmed';
UPDATE employees SET user_id = 'UUID-REEL-DE-L-EMPLOYE' WHERE first_name = 'Sara';
```

> **Alternative** : supprimez les données de test et réinsérez-les avec les bons UUID.

---

## 5. Configurer le stockage (Storage)

### 5.1 Créer le bucket

1. Allez dans **Storage**.
2. Cliquez sur **Create bucket**.
3. **Name** : `attendance-photos`
4. **Public bucket** : décochez pour un accès sécurisé (recommandé), cochez pour simplifier le développement.
5. Cliquez sur **Create bucket**.

### 5.2 Politiques de stockage

Si le bucket est privé, créez les politiques suivantes :

Via **Storage > attendance-photos > Policies** :

```sql
-- Lecture : tout utilisateur authentifié peut lire les photos
CREATE POLICY "Les utilisateurs authentifiés peuvent lire les photos"
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = 'attendance-photos');

-- Écriture : seuls les admins peuvent uploader
CREATE POLICY "Les admins peuvent uploader des photos"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'attendance-photos'
    AND (SELECT role FROM profiles WHERE id = auth.uid()) = 'admin'
);
```

### 5.3 Bucket pour les justificatifs

Créez un deuxième bucket pour stocker les scans des justificatifs d'absence :

1. Allez dans **Storage**.
2. Cliquez sur **Create bucket**.
3. **Name** : `absence-justificatifs`
4. **Public bucket** : décochez (privé — recommandé).
5. Cliquez sur **Create bucket**.

Politique pour le bucket `absence-justificatifs` :

```sql
-- Lecture : seuls les admins peuvent voir les justificatifs
CREATE POLICY "Les admins peuvent lire les justificatifs"
ON storage.objects FOR SELECT
TO authenticated
USING (
    bucket_id = 'absence-justificatifs'
    AND (SELECT role FROM profiles WHERE id = auth.uid()) = 'admin'
);

-- Écriture : seuls les admins peuvent uploader
CREATE POLICY "Les admins peuvent uploader les justificatifs"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'absence-justificatifs'
    AND (SELECT role FROM profiles WHERE id = auth.uid()) = 'admin'
);
```

### 5.4 URL de stockage

Les photos seront accessibles via l'URL :

```
https://[REF-PROJET].supabase.co/storage/v1/object/public/attendance-photos/[nom-fichier]
```

Pour un bucket privé, l'URL doit inclure un token d'authentification :

```
https://[REF-PROJET].supabase.co/storage/v1/object/authenticated/attendance-photos/[nom-fichier]
```

---

## 6. Configurer les politiques de sécurité (RLS)

### 6.1 Activer RLS sur chaque table

Pour chaque table (`profiles`, `work_schedules`, `employees`, `attendance`, `absence_types`, `justifications`) :

1. Allez dans **Table Editor**.
2. Sélectionnez la table.
3. Cliquez sur l'icône **RLS** dans la barre d'outils (bouclier) pour activer Row Level Security.

### 6.2 Créer les politiques

Exécutez ces commandes dans le SQL Editor :

```sql
-- ========================
-- Profiles
-- ========================
-- Lecture : un utilisateur peut voir son propre profil ; les admins voient tout
CREATE POLICY "Lecture profil"
ON profiles FOR SELECT
TO authenticated
USING (
    id = auth.uid()
    OR (SELECT role FROM profiles WHERE id = auth.uid()) = 'admin'
);

-- Modification : seul l'utilisateur concerné ou un admin peut modifier
CREATE POLICY "Modification profil"
ON profiles FOR UPDATE
TO authenticated
USING (
    id = auth.uid()
    OR (SELECT role FROM profiles WHERE id = auth.uid()) = 'admin'
);

-- ========================
-- Employees
-- ========================
-- Lecture : un employé voit sa propre fiche ; les admins voient tout
CREATE POLICY "Lecture employés"
ON employees FOR SELECT
TO authenticated
USING (
    user_id = auth.uid()
    OR (SELECT role FROM profiles WHERE id = auth.uid()) = 'admin'
);

-- Modification : seul un admin peut modifier
CREATE POLICY "Modification employés"
ON employees FOR INSERT
TO authenticated
WITH CHECK (
    (SELECT role FROM profiles WHERE id = auth.uid()) = 'admin'
);

-- ========================
-- Work Schedules
-- ========================
CREATE POLICY "Lecture horaires"
ON work_schedules FOR SELECT
TO authenticated
USING (
    TRUE  -- templates are shared, visible to all authenticated users
);

-- ========================
-- Attendance
-- ========================
-- Lecture : un employé voit ses propres pointages ; les admins voient tout
CREATE POLICY "Lecture pointages"
ON attendance FOR SELECT
TO authenticated
USING (
    employee_id IN (SELECT id FROM employees WHERE user_id = auth.uid())
    OR (SELECT role FROM profiles WHERE id = auth.uid()) = 'admin'
);

-- Insertion/modification : via le backend (service_role) ou admin
CREATE POLICY "Insertion pointages"
ON attendance FOR INSERT
TO authenticated
WITH CHECK (
    employee_id IN (SELECT id FROM employees WHERE user_id = auth.uid())
    OR (SELECT role FROM profiles WHERE id = auth.uid()) = 'admin'
);

-- ========================
-- Absence Types
-- ========================
CREATE POLICY "Lecture types absence"
ON absence_types FOR SELECT
TO authenticated
USING (TRUE);

-- ========================
-- Justifications
-- ========================
-- Lecture : un employé voit ses propres justificatifs ; les admins voient tout
CREATE POLICY "Lecture justificatifs"
ON justifications FOR SELECT
TO authenticated
USING (
    employee_id IN (SELECT id FROM employees WHERE user_id = auth.uid())
    OR (SELECT role FROM profiles WHERE id = auth.uid()) = 'admin'
);

-- Insertion/modification : seul un admin peut gérer les justificatifs
CREATE POLICY "Gestion justificatifs"
ON justifications FOR INSERT
TO authenticated
WITH CHECK (
    (SELECT role FROM profiles WHERE id = auth.uid()) = 'admin'
);

CREATE POLICY "Modification justificatifs"
ON justifications FOR UPDATE
TO authenticated
USING (
    (SELECT role FROM profiles WHERE id = auth.uid()) = 'admin'
);
```

---

## 7. Connecter le backend FastAPI

### 7.1 Variables d'environnement

Créez un fichier `.env` dans la racine du projet backend :

```env
# Supabase
SUPABASE_URL=https://[REF-PROJET].supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6Ik...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6Ik...

# Base de données (optionnel — pour connexion directe PostgreSQL)
DATABASE_URL=postgresql://postgres:[MOT-DE-PASSE]@db.[REF-PROJET].supabase.co:6543/postgres?pgbouncer=true
```

### 7.2 Exemple de connexion avec `supabase-py`

```python
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

supabase_url: str = os.environ["SUPABASE_URL"]
supabase_key: str = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

supabase: Client = create_client(supabase_url, supabase_key)
```

### 7.3 Test de connexion

```python
# Récupérer tous les employés
response = supabase.table("employees").select("*").execute()
print(response.data)

# Insérer un pointage
response = supabase.table("attendance").insert({
    "employee_id": "c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13",
    "date": "2026-06-27",
    "check_in": "2026-06-27T08:00:00+01:00",
    "status": "present"
}).execute()
```

---

## 8. Gestion des justificatifs d'absence

### 8.1 Principe

L'employé remet un justificatif papier à l'admin → l'admin le saisit dans le système.

### 8.2 Flux de saisie

1. L'admin se connecte et va dans l'interface "Justifier une absence"
2. Il sélectionne :
   - L'employé concerné
   - La ou les dates d'absence
   - Le type d'absence (Maladie, Congé payé, Motif familial, Formation, Autre)
   - Le fichier scan du justificatif (uploadé dans le bucket `absence-justificatifs`)
3. Il valide → le système :
   - Crée un enregistrement dans `justifications`
   - Marque `justified = TRUE` dans `attendance` pour les dates concernées
   - Lie l'enregistrement via `justification_id`

### 8.3 Exemple d'insertion par l'admin

```sql
-- 1. Créer le justificatif
INSERT INTO justifications (id, employee_id, absence_type_id, start_date, end_date, document_url, note, created_by)
VALUES (
    gen_random_uuid(),
    'UUID-DE-L-EMPLOYE',
    'UUID-DU-TYPE-ABSENCE',  -- ex: Maladie
    '2026-06-26', '2026-06-26',
    'https://[REF-PROJET].supabase.co/storage/v1/object/authenticated/absence-justificatifs/scan-abs.pdf',
    'Certificat médical fourni',
    'UUID-DE-L-ADMIN'
);

-- 2. Marquer l'attendance comme justifiée
UPDATE attendance
SET justified = TRUE,
    justification_id = 'UUID-DU-JUSTIFICATIF-CREE'
WHERE employee_id = 'UUID-DE-L-EMPLOYE'
  AND date = '2026-06-26';
```

### 8.4 API backend (exemple)

```python
@router.post("/justifications")
def create_justification(
    employee_id: str,
    absence_type_id: str,
    start_date: str,
    end_date: str,
    file: UploadFile,
    db: Session
):
    # Upload du fichier vers Supabase Storage
    file_url = upload_to_storage(file, "absence-justificatifs")
    
    # Création du justificatif
    justif = supabase.table("justifications").insert({
        "employee_id": employee_id,
        "absence_type_id": absence_type_id,
        "start_date": start_date,
        "end_date": end_date,
        "document_url": file_url,
        "created_by": get_current_admin().id
    }).execute()
    
    # Marquage des absences comme justifiées
    supabase.table("attendance").update({
        "justified": True,
        "justification_id": justif.data[0]["id"]
    }).eq("employee_id", employee_id).gte("date", start_date).lte("date", end_date).execute()
```

---

## Annexe : Commandes utiles

### Reset complet de la base

```sql
DROP TABLE IF EXISTS justifications CASCADE;
DROP TABLE IF EXISTS attendance CASCADE;
DROP TABLE IF EXISTS employees CASCADE;
DROP TABLE IF EXISTS work_schedules CASCADE;
DROP TABLE IF EXISTS absence_types CASCADE;
DROP TABLE IF EXISTS profiles CASCADE;
```

### Voir la structure d'une table

```sql
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'profiles'
ORDER BY ordinal_position;
```

### Voir les contraintes

```sql
SELECT
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
LEFT JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
WHERE tc.table_name = 'attendance';
```
