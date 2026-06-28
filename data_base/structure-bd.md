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

Cette table contient les informations personnelles et biométriques des employés. Chaque employé est lié à un profil via la clé étrangère `user_id` (relation 1-1). Le champ `face_encoding` stocke le vecteur facial sérialisé (en base64 ou JSON) produit par la librairie `face_recognition` — c'est ce vecteur qui permet d'identifier l'employé lors du pointage par caméra. `photo_url` pointe vers l'image stockée dans Supabase Storage. La colonne `schedule_id` lie l'employé à son planning hebdomadaire (relation N:1 avec `work_schedules`).

| Colonne         | Type                  | Contraintes                        |
|-----------------|-----------------------|------------------------------------|
| `id`            | UUID                  | PK                                 |
| `user_id`       | UUID                  | FK → `profiles(id)`                |
| `first_name`    | TEXT                  | NOT NULL                           |
| `last_name`     | TEXT                  | NOT NULL                           |
| `phone`         | TEXT                  |                                    |
| `photo_url`     | TEXT                  | URL photo stockée Supabase Storage |
| `face_encoding` | TEXT                  | Vecteur facial sérialisé           |
| `schedule_id`   | UUID                  | NOT NULL, FK → `work_schedules(id)` |
| `created_at`    | TIMESTAMPTZ           | DEFAULT `now()`                    |
| `updated_at`    | TIMESTAMPTZ           | DEFAULT `now()`                    |
| `deleted_at`    | TIMESTAMPTZ           | DEFAULT NULL                       |

---

### 3. `work_schedules` — Plannings hebdomadaires

Cette table définit des **plannings hebdomadaires complets** (ex: "Standard Semaine 08:00–17:00 du lundi au vendredi"). Chaque ligne décrit les horaires pour les 7 jours de la semaine. Les colonnes `*_start` / `*_end` sont NULL pour les jours non travaillés. Un employé se voit attribuer un seul planning via la colonne `schedule_id` de la table `employees`.

| Colonne              | Type                  | Contraintes                                    |
|----------------------|-----------------------|------------------------------------------------|
| `id`                 | UUID                  | PK                                             |
| `name`               | TEXT                  | NOT NULL — nom du planning                     |
| `monday_start`       | TIME                  | NULL si repos                                  |
| `monday_end`         | TIME                  | NULL si repos                                  |
| `tuesday_start`      | TIME                  | NULL si repos                                  |
| `tuesday_end`        | TIME                  | NULL si repos                                  |
| `wednesday_start`    | TIME                  | NULL si repos                                  |
| `wednesday_end`      | TIME                  | NULL si repos                                  |
| `thursday_start`     | TIME                  | NULL si repos                                  |
| `thursday_end`       | TIME                  | NULL si repos                                  |
| `friday_start`       | TIME                  | NULL si repos                                  |
| `friday_end`         | TIME                  | NULL si repos                                  |
| `saturday_start`     | TIME                  | NULL si repos                                  |
| `saturday_end`       | TIME                  | NULL si repos                                  |
| `sunday_start`       | TIME                  | NULL si repos                                  |
| `sunday_end`         | TIME                  | NULL si repos                                  |
| `grace_period_minutes` | INTEGER             | DEFAULT 10 — tolérance de retard en minutes    |
| `created_at`         | TIMESTAMPTZ           | DEFAULT `now()`                                |
| `updated_at`         | TIMESTAMPTZ           | DEFAULT `now()`                                |
| `deleted_at`         | TIMESTAMPTZ           | DEFAULT NULL                                   |

---

### 4. `attendance` — Pointages quotidiens

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
| `idx_employees_schedule_id`   | `employees`           | `schedule_id`                  |
| `idx_attendance_emp_date`     | `attendance`          | `employee_id`, `date`          |
| `idx_attendance_date`         | `attendance`          | `date`                         |
| `idx_attendance_status`       | `attendance`          | `status`                       |

---

## Diagrammes

### Diagramme de classes (UML)

Ce diagramme représente la structure statique du système sous forme de classes avec leurs attributs et relations. Chaque classe correspond à une table de la base de données. Les attributs sont typés (UUID, String, Timestamp, etc.) et la visibilité est privée (`-`). Les relations indiquent les cardinalités :
- **Profile 1 → 1 Employee** : un profil possède un et un seul employé
- **WorkSchedule 1 → N Employee** : un planning hebdomadaire peut être assigné à plusieurs employés
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
        -UUID schedule_id
        -Timestamp created_at
        -Timestamp updated_at
        -Timestamp deleted_at
    }

    class WorkSchedule {
        -UUID id
        -String name
        -Time monday_start
        -Time monday_end
        -Time tuesday_start
        -Time tuesday_end
        -Time wednesday_start
        -Time wednesday_end
        -Time thursday_start
        -Time thursday_end
        -Time friday_start
        -Time friday_end
        -Time saturday_start
        -Time saturday_end
        -Time sunday_start
        -Time sunday_end
        -int grace_period_minutes
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
    WorkSchedule "1" --> "N" Employee : assigné à
    Employee "1" --> "N" Attendance : pointe
```

### Modèle Conceptuel de Données (MCD — Merise)

Ce diagramme conceptuel (indépendant de toute implémentation technique) décrit les entités et leurs relations selon la notation Merise (Pascal Chen). Les cardinalités se lisent comme suit :
- **PROFILE ||--|| EMPLOYEE** : un PROFILE a au moins un et au plus un EMPLOYEE (relation 1-1 totale)
- **WORK_SCHEDULE ||--o{ EMPLOYEE** : un WORK_SCHEDULE peut être assigné à plusieurs employés (relation 1-N)
- **EMPLOYEE ||--o{ ATTENDANCE** : un EMPLOYEE a plusieurs ATTENDANCE (relation 1-N totale côté employé, optionnelle côté pointage)

Les attributs clés (`PK`, `FK`, `UK`) sont indiqués pour chaque entité.

```mermaid
erDiagram
    PROFILE ||--|| EMPLOYEE : "possède"
    WORK_SCHEDULE ||--o{ EMPLOYEE : "assigné à"
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
        uuid schedule_id FK
    }

    WORK_SCHEDULE {
        uuid id PK
        string name
        time monday_start
        time monday_end
        time tuesday_start
        time tuesday_end
        time wednesday_start
        time wednesday_end
        time thursday_start
        time thursday_end
        time friday_start
        time friday_end
        time saturday_start
        time saturday_end
        time sunday_start
        time sunday_end
        int grace_period_minutes
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
| `work_schedules`     | 2 plannings hebdomadaires : Standard (08:00–17:00), Flex (09:00–18:00 / 13:00–21:00) |
| `employees`          | Ahmed Benali → Standard, Sara Dupont → Flex              |
| `attendance`         | 5 derniers jours ouvrés pour chaque employé              |
