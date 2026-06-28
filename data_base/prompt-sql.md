# Prompt — Génération de la base de données SQL / SQL Database Generation Prompt
## Système de reconnaissance faciale — Gestion des présences / Facial Recognition Attendance System

---

### Project Context

You are a PostgreSQL and Supabase database expert. I am building a **facial recognition system** to automatically manage employee attendance in a company. The backend uses **FastAPI + Python**, the database is **Supabase (hosted PostgreSQL)**, and facial recognition is handled with `face_recognition` + OpenCV.

### What You Must Generate

Generate a complete SQL file ready to be executed in the **Supabase SQL Editor**, containing:

1. **All table creation statements** (with constraints, foreign keys, etc.)
2. **Realistic test data** (INSERT INTO)
3. **Performance indexes** on the most frequently queried columns

---

### Mandatory Technical Rules

- Use **UUID** for all primary keys (`gen_random_uuid()`)
- Add the following tracking columns to **every table**:
  - `created_at TIMESTAMPTZ DEFAULT now()`
  - `updated_at TIMESTAMPTZ DEFAULT now()`
  - `deleted_at TIMESTAMPTZ DEFAULT NULL` *(soft delete — records are never physically deleted, only marked)*
- Use `TIMESTAMPTZ` for all date/time values
- Use `TIME` type for schedule times (e.g. `08:00:00`)
- All `NOT NULL`, `UNIQUE`, and `CHECK` constraints must be explicit
- Must be compatible with **Supabase / PostgreSQL 15+**

---

### Tables to Create

#### 1. `profiles` — User profiles (linked to Supabase Auth)
- `id` UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE
- `role` TEXT CHECK (role IN ('admin', 'employee')) NOT NULL
- `display_name` TEXT — display name without joining employees
- `is_active` BOOLEAN DEFAULT true — disable account without soft delete
- `last_login_at` TIMESTAMPTZ — track last connection
- tracking columns (created_at, updated_at, deleted_at)

#### 2. `employees` — Employee information
- `id` UUID PRIMARY KEY
- `user_id` UUID REFERENCES profiles(id)
- `first_name` TEXT NOT NULL
- `last_name` TEXT NOT NULL
- `phone` TEXT
- `photo_url` TEXT — URL to photo stored in Supabase Storage
- `face_encoding` TEXT — serialized face vector (JSON/base64)
- tracking columns

#### 3. `work_schedules` — Schedule templates (shared across employees)
> Reusable schedule templates (e.g. "Standard Monday 08:00–17:00"). Templates are assigned to employees via the N:N junction table `employee_schedules`.

- `id` UUID PRIMARY KEY
- `day_of_week` INTEGER CHECK (day_of_week BETWEEN 0 AND 6) — 0=Monday, 6=Sunday
- `start_time` TIME NOT NULL
- `end_time` TIME NOT NULL
- `grace_period_minutes` INTEGER DEFAULT 10 — lateness tolerance in minutes
- `is_working_day` BOOLEAN DEFAULT true — FALSE if the employee is off that day
- `label` TEXT — human-readable name (e.g. "Standard Monday")
- tracking columns

#### 4. `employee_schedules` — N:N junction between employees and work_schedules
> Links employees to their assigned schedule templates. An employee can have multiple templates (one per day), and a template can be shared by many employees.

- `id` UUID PRIMARY KEY
- `employee_id` UUID REFERENCES employees(id)
- `schedule_id` UUID REFERENCES work_schedules(id)
- tracking columns

#### 5. `attendance` — Daily check-in / check-out records
- `id` UUID PRIMARY KEY
- `employee_id` UUID REFERENCES employees(id)
- `date` DATE NOT NULL
- `check_in` TIMESTAMPTZ
- `check_out` TIMESTAMPTZ
- `status` TEXT CHECK (status IN ('present', 'late', 'absent')) DEFAULT 'absent'
- `late_minutes` INTEGER DEFAULT 0
- `worked_hours` NUMERIC(5,2) DEFAULT 0
- `note` TEXT — optional remark
- tracking columns
- UNIQUE(employee_id, date) — one record per employee per day

---

### Test Data to Insert

Insert the following:

1. **2 profile accounts** (IDs must match existing Supabase auth.users):
   - 1 admin: `admin@company.com`
   - 1 employee: `employee@company.com`

2. **2 employees**:
   - Employee 1: Ahmed Benali, linked to the admin account
   - Employee 2: Sara Dupont, linked to the employee account
   - Include fake `photo_url` values (e.g. `https://storage.supabase.co/...`)
   - Include fake `face_encoding` values (e.g. short base64 string)

3. **Work schedules**:
   - Ahmed: Monday to Friday, 08:00 → 17:00, 10 min grace period
   - Sara: Mon/Wed/Fri 09:00 → 18:00, Tue/Thu 13:00 → 21:00

4. **Attendance records** (last 5 working days):
   - Ahmed: 3 days on time, 1 day late (12 min), 1 day absent
   - Sara: 4 days present, 1 day absent
   - Include realistic `check_in` / `check_out` timestamps with calculated `worked_hours`

---

### Performance Indexes to Create

Create indexes on:
- `employees(user_id)`
- `employee_schedules(employee_id)`
- `employee_schedules(schedule_id)`
- `attendance(employee_id, date)`
- `attendance(date)` — for daily reports
- `attendance(status)` — for filtering by status

---

### Expected Output Format

- A single well-structured `.sql` file
- Sections separated by clear comments: `-- === TABLES ===`, `-- === DATA ===`, `-- === INDEXES ===`
- All statements end with `;`
- The file must be copy-pasteable directly into **Supabase > SQL Editor > New Query** and run without errors
