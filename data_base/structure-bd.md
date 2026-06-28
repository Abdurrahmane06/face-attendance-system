# Structure de la Base de Données

> Système de reconnaissance faciale — Gestion des présences
> PostgreSQL 15+ / Supabase

---

## Conventions générales

- **UUID** pour toutes les clés primaires (`gen_random_uuid()`)
- **Soft delete** — aucun enregistrement supprimé physiquement, `deleted_at` mis à `NULL` par défaut
- **TIMESTAMPTZ** pour toutes les dates/heures
- **TIME** pour les horaires de travail

---

## Tables

### 1. `profiles` — Profils des comptes (liés à Supabase Auth)

Cette table stocke les profils des comptes utilisateur, liés directement à l'authentification Supabase (`auth.users`) via la clé primaire. Le champ `role` détermine les permissions : un `admin` peut gérer les employés et consulter tous les pointages, tandis qu'un `employee` ne peut voir que ses propres données. `display_name` permet d'afficher un nom sans JOIN avec `employees`. `is_active` permet de désactiver un compte sans soft delete.

| Colonne          | Type                  | Contraintes                                       |
|------------------|-----------------------|---------------------------------------------------|
| `id`             | UUID                  | PK, FK → `auth.users(id)` ON DELETE CASCADE       |
| `role`           | TEXT                  | NOT NULL, CHECK(`role` IN ('admin', 'employee'))   |
| `display_name`   | TEXT                  |                                                   |
| `is_active`      | BOOLEAN               | DEFAULT TRUE                                      |
| `last_login_at`  | TIMESTAMPTZ           |                                                   |
| `created_at`     | TIMESTAMPTZ           | DEFAULT `now()`                                   |
| `updated_at`     | TIMESTAMPTZ           | DEFAULT `now()`                                   |
| `deleted_at`     | TIMESTAMPTZ           | DEFAULT NULL                                      |

---

### 2. `employees` — Informations des employés

Cette table contient les informations personnelles et biométriques des employés. Chaque employé est lié à un profil via la clé étrangère `user_id` (relation 1-1). Le champ `face_encoding` stocke le vecteur facial sérialisé (en base64 ou JSON) produit par la librairie `face_recognition` — c'est ce vecteur qui permet d'identifier l'employé lors du pointage par caméra. `photo_url` pointe vers l'image stockée dans Supabase Storage.

| Colonne         | Type                  | Contraintes                        |
|-----------------|-----------------------|------------------------------------|
| `id`            | UUID                  | PK                                 |
| `user_id`       | UUID                  | FK → `profiles(id)`                |
| `first_name`    | TEXT                  | NOT NULL                           |
| `last_name`     | TEXT                  | NOT NULL                           |
| `phone`         | TEXT                  |                                    |
| `photo_url`     | TEXT                  | URL photo stockée Supabase Storage |
| `face_encoding` | TEXT                  | Vecteur facial sérialisé           |
| `created_at`    | TIMESTAMPTZ           | DEFAULT `now()`                    |
| `updated_at`    | TIMESTAMPTZ           | DEFAULT `now()`                    |
| `deleted_at`    | TIMESTAMPTZ           | DEFAULT NULL                       |

---

### 3. `work_schedules` — Modèles d'horaires (templates)

Cette table définit des **modèles d'horaires** réutilisables (ex: "Standard Lundi 08:00–17:00", "Flex Mardi 13:00–21:00"). Ces modèles sont **partagés** entre plusieurs employés via la table de liaison `employee_schedules`. Le champ `label` permet d'identifier chaque modèle. Si `is_working_day` est `FALSE`, le créneau représente un jour de repos. L'unicité est portée par l'`id`.

| Colonne              | Type                  | Contraintes                                       |
|----------------------|-----------------------|---------------------------------------------------|
| `id`                 | UUID                  | PK                                                |
| `day_of_week`        | INTEGER               | NOT NULL, CHECK(0–6) — 0=Lundi, 6=Dimanche        |
| `start_time`         | TIME                  | NOT NULL                                          |
| `end_time`           | TIME                  | NOT NULL                                          |
| `grace_period_minutes` | INTEGER             | DEFAULT 10 — tolérance de retard en minutes       |
| `is_working_day`     | BOOLEAN               | DEFAULT TRUE — FALSE si repos                     |
| `label`              | TEXT                  | Libellé du modèle (ex: "Standard Lundi")          |
| `created_at`         | TIMESTAMPTZ           | DEFAULT `now()`                                   |
| `updated_at`         | TIMESTAMPTZ           | DEFAULT `now()`                                   |
| `deleted_at`         | TIMESTAMPTZ           | DEFAULT NULL                                      |

---

### 4. `employee_schedules` — Liaison employés ↔ modèles d'horaires

Cette table de liaison (junction) réalise la relation **N:N** entre `employees` et `work_schedules`. Un employé peut avoir plusieurs modèles d'horaires (un par jour de la semaine), et un même modèle peut être assigné à plusieurs employés. Cela évite la duplication de données : le modèle "Standard Lundi 08:00–17:00" est créé une seule fois dans `work_schedules` et réutilisé pour tous les employés qui travaillent selon ce créneau.

| Colonne        | Type                  | Contraintes                        |
|----------------|-----------------------|------------------------------------|
| `id`           | UUID                  | PK                                 |
| `employee_id`  | UUID                  | FK → `employees(id)`               |
| `schedule_id`  | UUID                  | FK → `work_schedules(id)`          |
| `created_at`   | TIMESTAMPTZ           | DEFAULT `now()`                    |
| `updated_at`   | TIMESTAMPTZ           | DEFAULT `now()`                    |
| `deleted_at`   | TIMESTAMPTZ           | DEFAULT NULL                       |

---

### 5. `attendance` — Pointages quotidiens

Cette table enregistre les pointages d'entrée et de sortie de chaque employé pour chaque jour. La contrainte `UNIQUE(employee_id, date)` garantit qu'il ne peut y avoir qu'un seul enregistrement par employé et par jour. Le `status` est calculé automatiquement (ou saisi) selon l'heure d'arrivée par rapport à l'horaire prévu dans `work_schedules` : `present` si dans les temps (ou pendant la grâce), `late` si au-delà, `absent` si pas de pointage. Les champs `late_minutes` et `worked_hours` sont dérivés des timestamps `check_in`/`check_out`.

| Colonne         | Type                  | Contraintes                                       |
|-----------------|-----------------------|---------------------------------------------------|
| `id`            | UUID                  | PK                                                |
| `employee_id`   | UUID                  | FK → `employees(id)`                              |
| `date`          | DATE                  | NOT NULL                                          |
| `check_in`      | TIMESTAMPTZ           |                                                   |
| `check_out`     | TIMESTAMPTZ           |                                                   |
| `status`        | TEXT                  | CHECK(`status` IN ('present', 'late', 'absent')), DEFAULT 'absent' |
| `late_minutes`  | INTEGER               | DEFAULT 0                                         |
| `worked_hours`  | NUMERIC(5,2)          | DEFAULT 0                                         |
| `note`          | TEXT                  |                                                   |
| `created_at`    | TIMESTAMPTZ           | DEFAULT `now()`                                   |
| `updated_at`    | TIMESTAMPTZ           | DEFAULT `now()`                                   |
| `deleted_at`    | TIMESTAMPTZ           | DEFAULT NULL                                      |

**Contrainte unique :** UNIQUE(`employee_id`, `date`) — un seul pointage par employé par jour

---

## Index de performance

| Index                         | Table                 | Colonnes                       |
|-------------------------------|-----------------------|--------------------------------|
| `idx_employees_user_id`       | `employees`           | `user_id`                      |
| `idx_employee_schedules_emp`  | `employee_schedules`  | `employee_id`                  |
| `idx_employee_schedules_sched`| `employee_schedules`  | `schedule_id`                  |
| `idx_attendance_emp_date`     | `attendance`          | `employee_id`, `date`          |
| `idx_attendance_date`         | `attendance`          | `date`                         |
| `idx_attendance_status`       | `attendance`          | `status`                       |

---

## Diagrammes

### Diagramme de classes (UML)

Ce diagramme représente la structure statique du système sous forme de classes avec leurs attributs et relations. Chaque classe correspond à une table de la base de données. Les attributs sont typés (UUID, String, Timestamp, etc.) et la visibilité est privée (`-`). Les relations indiquent les cardinalités :
- **Profile 1 → 1 Employee** : un profil possède un et un seul employé
- **Employee 1 → N EmployeeSchedule ← N WorkSchedule** : relation N:N entre employés et modèles d'horaires via la classe de liaison `EmployeeSchedule`
- **Employee 1 → N Attendance** : un employé a plusieurs pointages (un par jour travaillé)

```mermaid
classDiagram
    class Profile {
        -UUID id
        -String role
        -String display_name
        -bool is_active
        -Timestamp last_login_at
        -Timestamp created_at
        -Timestamp updated_at
        -Timestamp deleted_at
    }

    class Employee {
        -UUID id
        -UUID user_id
        -String first_name
        -String last_name
        -String phone
        -String photo_url
        -String face_encoding
        -Timestamp created_at
        -Timestamp updated_at
        -Timestamp deleted_at
    }

    class WorkSchedule {
        -UUID id
        -int day_of_week
        -Time start_time
        -Time end_time
        -int grace_period_minutes
        -bool is_working_day
        -String label
        -Timestamp created_at
        -Timestamp updated_at
        -Timestamp deleted_at
    }

    class EmployeeSchedule {
        -UUID id
        -UUID employee_id
        -UUID schedule_id
        -Timestamp created_at
        -Timestamp updated_at
        -Timestamp deleted_at
    }

    class Attendance {
        -UUID id
        -UUID employee_id
        -Date date
        -Timestamp check_in
        -Timestamp check_out
        -String status
        -int late_minutes
        -Number worked_hours
        -String note
        -Timestamp created_at
        -Timestamp updated_at
        -Timestamp deleted_at
    }

    Profile "1" --> "1" Employee : possède
    Employee "1" --> "N" EmployeeSchedule : a
    WorkSchedule "1" --> "N" EmployeeSchedule : assigné à
    Employee "1" --> "N" Attendance : pointe
```

### Modèle Conceptuel de Données (MCD — Merise)

Ce diagramme conceptuel (indépendant de toute implémentation technique) décrit les entités et leurs relations selon la notation Merise (Pascal Chen). Les cardinalités se lisent comme suit :
- **PROFILE ||--|| EMPLOYEE** : un PROFILE a au moins un et au plus un EMPLOYEE (relation 1-1 totale)
- **EMPLOYEE ||--o{ EMPLOYEE_SCHEDULE** : un EMPLOYEE peut avoir plusieurs assignations d'horaires
- **WORK_SCHEDULE ||--o{ EMPLOYEE_SCHEDULE** : un WORK_SCHEDULE peut être assigné à plusieurs employés
- **EMPLOYEE ||--o{ ATTENDANCE** : un EMPLOYEE a au moins un et plusieurs ATTENDANCE (relation 1-N totale côté employé, optionnelle côté pointage)

Les attributs clés (`PK`, `FK`, `UK`) sont indiqués pour chaque entité.

```mermaid
erDiagram
    PROFILE ||--|| EMPLOYEE : "possède"
    EMPLOYEE ||--o{ EMPLOYEE_SCHEDULE : "a"
    WORK_SCHEDULE ||--o{ EMPLOYEE_SCHEDULE : "assigné à"
    EMPLOYEE ||--o{ ATTENDANCE : "pointe"

    PROFILE {
        uuid id PK
        string role
        string display_name
        bool is_active
        timestamp last_login_at
    }

    EMPLOYEE {
        uuid id PK
        uuid user_id FK
        string first_name
        string last_name
        string phone
        string photo_url
        string face_encoding
    }

    WORK_SCHEDULE {
        uuid id PK
        int day_of_week
        time start_time
        time end_time
        int grace_period_minutes
        bool is_working_day
        string label
    }

    EMPLOYEE_SCHEDULE {
        uuid id PK
        uuid employee_id FK
        uuid schedule_id FK
    }

    ATTENDANCE {
        uuid id PK
        uuid employee_id FK
        date date
        timestamp check_in
        timestamp check_out
        string status
        int late_minutes
        numeric worked_hours
        string note
    }
```

---

## Données de test (résumé)

| Table                | Contenu                                                  |
|----------------------|----------------------------------------------------------|
| `profiles`           | 1 admin, 1 employee                                      |
| `employees`          | Ahmed Benali (admin), Sara Dupont (employee)              |
| `work_schedules`     | 14 modèles : Standard (Lun-Ven 08:00–17:00 + WE), Flex (Lun-Ven 09:00–18:00 / Mar-Jeu 13:00–21:00 + WE) |
| `employee_schedules` | Ahmed → 7 modèles Standard, Sara → 7 modèles Flex       |
| `attendance`         | 5 derniers jours ouvrés pour chaque employé              |
