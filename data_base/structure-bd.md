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

### 1. `users` — Comptes d'authentification (liés à Supabase Auth)

| Colonne       | Type                  | Contraintes                        |
|---------------|-----------------------|------------------------------------|
| `id`          | UUID                  | PK, lié à `auth.users` Supabase    |
| `email`       | TEXT                  | UNIQUE NOT NULL                    |
| `role`        | TEXT                  | NOT NULL, CHECK(`role` IN ('admin', 'employee')) |
| `created_at`  | TIMESTAMPTZ           | DEFAULT `now()`                    |
| `updated_at`  | TIMESTAMPTZ           | DEFAULT `now()`                    |
| `deleted_at`  | TIMESTAMPTZ           | DEFAULT NULL                       |

---

### 2. `employees` — Informations des employés

| Colonne         | Type                  | Contraintes                        |
|-----------------|-----------------------|------------------------------------|
| `id`            | UUID                  | PK                                 |
| `user_id`       | UUID                  | FK → `users(id)`                   |
| `first_name`    | TEXT                  | NOT NULL                           |
| `last_name`     | TEXT                  | NOT NULL                           |
| `phone`         | TEXT                  |                                    |
| `photo_url`     | TEXT                  | URL photo stockée Supabase Storage |
| `face_encoding` | TEXT                  | Vecteur facial sérialisé           |
| `created_at`    | TIMESTAMPTZ           | DEFAULT `now()`                    |
| `updated_at`    | TIMESTAMPTZ           | DEFAULT `now()`                    |
| `deleted_at`    | TIMESTAMPTZ           | DEFAULT NULL                       |

---

### 3. `work_schedules` — Emplois du temps personnalisés

| Colonne              | Type                  | Contraintes                                       |
|----------------------|-----------------------|---------------------------------------------------|
| `id`                 | UUID                  | PK                                                |
| `employee_id`        | UUID                  | FK → `employees(id)`                              |
| `day_of_week`        | INTEGER               | NOT NULL, CHECK(0–6) — 0=Lundi, 6=Dimanche        |
| `start_time`         | TIME                  | NOT NULL                                          |
| `end_time`           | TIME                  | NOT NULL                                          |
| `grace_period_minutes` | INTEGER             | DEFAULT 10 — tolérance de retard en minutes       |
| `is_working_day`     | BOOLEAN               | DEFAULT TRUE — FALSE si repos                     |
| `created_at`         | TIMESTAMPTZ           | DEFAULT `now()`                                   |
| `updated_at`         | TIMESTAMPTZ           | DEFAULT `now()`                                   |
| `deleted_at`         | TIMESTAMPTZ           | DEFAULT NULL                                      |

---

### 4. `attendance` — Pointages quotidiens

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

| Index                         | Table             | Colonnes                       |
|-------------------------------|-------------------|--------------------------------|
| `idx_employees_user_id`       | `employees`       | `user_id`                      |
| `idx_work_schedules_emp_day`  | `work_schedules`  | `employee_id`, `day_of_week`   |
| `idx_attendance_emp_date`     | `attendance`      | `employee_id`, `date`          |
| `idx_attendance_date`         | `attendance`      | `date`                         |
| `idx_attendance_status`       | `attendance`      | `status`                       |

---

## Relations (schéma logique)

```
users (1) ──── (1) employees
employees (1) ──── (N) work_schedules
employees (1) ──── (N) attendance
```

---

## Données de test (résumé)

| Table            | Contenu                                    |
|------------------|--------------------------------------------|
| `users`          | 1 admin, 1 employee                        |
| `employees`      | Ahmed Benali (admin), Sara Dupont (employee) |
| `work_schedules` | Ahmed : Lun-Ven 08:00–17:00                |
|                  | Sara : Lun/Mer/Ven 09:00–18:00, Mar/Jeu 13:00–21:00 |
| `attendance`     | 5 derniers jours ouvrés pour chaque employé |
