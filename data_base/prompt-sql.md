# Prompt — Génération de la base de données SQL / SQL Database Generation Prompt
## Système de reconnaissance faciale — Gestion des présences / Facial Recognition Attendance System

---

### Project Context

You are a PostgreSQL and Supabase database expert. I am building a **facial recognition system** to automatically manage employee attendance in a company. The backend uses **FastAPI + Python**, the database is **Supabase (hosted PostgreSQL)**, and facial recognition is handled with `face_recognition` + OpenCV.

### What You Must Generate

Generate a complete SQL file ready to be executed in the **Supabase SQL Editor**, containing:

1. **All table creation statements** (6 tables: profiles, work_schedules, employees, attendance, absence_types, justifications — with constraints, foreign keys, etc.)
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
- `schedule_id` UUID NOT NULL REFERENCES work_schedules(id) — assigned weekly schedule
- tracking columns

#### 3. `work_schedules` — Weekly schedule templates
> Each row represents a full weekly schedule (e.g. "Standard Week 08:00-17:00 Mon-Fri"). An employee is assigned a single schedule via `employees.schedule_id`. NULL start/end time means non-working day.

- `id` UUID PRIMARY KEY
- `name` TEXT NOT NULL — human-readable name (e.g. "Standard Week")
- `monday_start` TIME — start time Monday (NULL if off)
- `monday_end` TIME — end time Monday
- `tuesday_start` TIME
- `tuesday_end` TIME
- `wednesday_start` TIME
- `wednesday_end` TIME
- `thursday_start` TIME
- `thursday_end` TIME
- `friday_start` TIME
- `friday_end` TIME
- `saturday_start` TIME
- `saturday_end` TIME
- `sunday_start` TIME
- `sunday_end` TIME
- `grace_period_minutes` INTEGER DEFAULT 10 — lateness tolerance in minutes
- tracking columns

#### 4. `attendance` — Daily check-in / check-out records
- `id` UUID PRIMARY KEY
- `employee_id` UUID REFERENCES employees(id)
- `date` DATE NOT NULL
- `check_in` TIMESTAMPTZ
- `check_out` TIMESTAMPTZ
- `status` TEXT CHECK (status IN ('present', 'late', 'absent')) DEFAULT 'absent'
- `late_minutes` INTEGER DEFAULT 0
- `worked_hours` NUMERIC(5,2) DEFAULT 0
- `note` TEXT — optional remark
- `justified` BOOLEAN DEFAULT FALSE — marked as justified by admin
- `justification_id` UUID REFERENCES justifications(id) — link to justification record
- tracking columns
- UNIQUE(employee_id, date) — one record per employee per day

---

#### 5. `absence_types` — Absence categories
- `id` UUID PRIMARY KEY
- `name` TEXT NOT NULL UNIQUE — e.g. "Maladie", "Congé payé"
- `requires_doc` BOOLEAN DEFAULT FALSE — whether a document is needed
- `is_paid` BOOLEAN DEFAULT TRUE — whether absence is paid
- tracking columns

#### 6. `justifications` — Absence justifications (admin-managed)
> Employee gives a paper document to the admin → admin enters it into the system with document scan.

- `id` UUID PRIMARY KEY
- `employee_id` UUID NOT NULL REFERENCES employees(id)
- `absence_type_id` UUID NOT NULL REFERENCES absence_types(id)
- `start_date` DATE NOT NULL — start of absence period
- `end_date` DATE NOT NULL — end of absence period
- `document_url` TEXT — URL of scanned document in Supabase Storage
- `note` TEXT — admin comment
- `created_by` UUID NOT NULL REFERENCES profiles(id) — the admin who entered it
- tracking columns
- CHECK (end_date >= start_date)

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

3. **Work schedules** (weekly templates):
   - Standard Semaine: Mon-Fri 08:00→17:00, weekend off, 10 min grace
   - Flex Semaine: Mon/Wed/Fri 09:00→18:00, Tue/Thu 13:00→21:00, weekend off, 15 min grace

4. **Employees** (with schedule assignment):
   - Ahmed: assigned to 'Standard Semaine'
   - Sara: assigned to 'Flex Semaine'

5. **Attendance records** (last 5 working days):
   - Ahmed: 3 days on time, 1 day late (12 min), 1 day absent (justified with medical certificate)
   - Sara: 4 days present, 1 day absent
   - Include realistic `check_in` / `check_out` timestamps with calculated `worked_hours`

6. **Absence types** (5 types):
   - Maladie, Congé payé, Motif familial, Formation, Autre

7. **Justifications** (1 justification):
   - Ahmed's absence on Fri 26 → justified with "Maladie", document_url pointing to Supabase Storage

---

### Performance Indexes to Create

Create indexes on:
- `employees(user_id)`
- `employees(schedule_id)`
- `attendance(employee_id, date)`
- `attendance(date)` — for daily reports
- `attendance(status)` — for filtering by status
- `attendance(justified)` — partial index WHERE justified = TRUE
- `justifications(employee_id)`
- `justifications(start_date, end_date)` — for period queries

---

### Expected Output Format

- A single well-structured `.sql` file
- Sections separated by clear comments: `-- === TABLES ===`, `-- === DATA ===`, `-- === INDEXES ===`
- All statements end with `;`
- The file must be copy-pasteable directly into **Supabase > SQL Editor > New Query** and run without errors
