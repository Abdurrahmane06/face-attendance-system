-- =============================================================================
-- Face Attendance System — Schema SQL
-- PostgreSQL 15+ / Supabase
-- =============================================================================

-- === TABLES ===

-- 1. profiles — linked to Supabase Auth
CREATE TABLE profiles (
    id              UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('admin', 'employee')),
    display_name    TEXT,
    is_active       BOOLEAN DEFAULT TRUE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    deleted_at      TIMESTAMPTZ DEFAULT NULL
);

-- 2. employees — employee information
CREATE TABLE employees (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES profiles(id),
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    phone           TEXT,
    photo_url       TEXT,
    face_encoding   TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    deleted_at      TIMESTAMPTZ DEFAULT NULL
);

-- 3. work_schedules — per-employee, per-day custom schedules
CREATE TABLE work_schedules (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id         UUID NOT NULL REFERENCES employees(id),
    day_of_week         INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
    start_time          TIME NOT NULL,
    end_time            TIME NOT NULL,
    grace_period_minutes INTEGER DEFAULT 10,
    is_working_day      BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now(),
    deleted_at          TIMESTAMPTZ DEFAULT NULL
);

-- 4. attendance — daily check-in / check-out records
CREATE TABLE attendance (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id     UUID NOT NULL REFERENCES employees(id),
    date            DATE NOT NULL,
    check_in        TIMESTAMPTZ,
    check_out       TIMESTAMPTZ,
    status          TEXT DEFAULT 'absent' CHECK (status IN ('present', 'late', 'absent')),
    late_minutes    INTEGER DEFAULT 0,
    worked_hours    NUMERIC(5,2) DEFAULT 0,
    note            TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    deleted_at      TIMESTAMPTZ DEFAULT NULL,
    UNIQUE(employee_id, date)
);

-- === DATA ===

-- Profiles (IDs must match existing Supabase auth.users)
INSERT INTO profiles (id, role, display_name, is_active)
VALUES
    ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'admin',    'Ahmed Benali', TRUE),
    ('b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12', 'employee', 'Sara Dupont',  TRUE);

-- Employees
INSERT INTO employees (id, user_id, first_name, last_name, phone, photo_url, face_encoding)
VALUES
    (
        'c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13',
        'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
        'Ahmed', 'Benali',
        '+213-555-123456',
        'https://storage.supabase.co/attendance/photos/ahmed-benali.jpg',
        'base64:W5Y8xP7qzR3...'
    ),
    (
        'd0eebc99-9c0b-4ef8-bb6d-6bb9bd380a14',
        'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12',
        'Sara', 'Dupont',
        '+33-6-12-34-56-78',
        'https://storage.supabase.co/attendance/photos/sara-dupont.jpg',
        'base64:T2mH9kL4vQx...'
    );

-- Work schedules
-- Ahmed: Monday to Friday, 08:00→17:00, 10 min grace
INSERT INTO work_schedules (employee_id, day_of_week, start_time, end_time, grace_period_minutes, is_working_day)
VALUES
    ('c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13', 0, '08:00', '17:00', 10, TRUE),
    ('c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13', 1, '08:00', '17:00', 10, TRUE),
    ('c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13', 2, '08:00', '17:00', 10, TRUE),
    ('c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13', 3, '08:00', '17:00', 10, TRUE),
    ('c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13', 4, '08:00', '17:00', 10, TRUE),
    ('c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13', 5, NULL, NULL, 0, FALSE),
    ('c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13', 6, NULL, NULL, 0, FALSE);

-- Sara: Mon/Wed/Fri 09:00→18:00, Tue/Thu 13:00→21:00, 15 min grace
INSERT INTO work_schedules (employee_id, day_of_week, start_time, end_time, grace_period_minutes, is_working_day)
VALUES
    ('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a14', 0, '09:00', '18:00', 15, TRUE),
    ('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a14', 1, '13:00', '21:00', 15, TRUE),
    ('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a14', 2, '09:00', '18:00', 15, TRUE),
    ('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a14', 3, '13:00', '21:00', 15, TRUE),
    ('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a14', 4, '09:00', '18:00', 15, TRUE),
    ('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a14', 5, NULL, NULL, 0, FALSE),
    ('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a14', 6, NULL, NULL, 0, FALSE);

-- Attendance — last 5 working days: Mon 2026-06-22 → Fri 2026-06-26
-- Ahmed: 3 on time, 1 late (12 min), 1 absent
INSERT INTO attendance (employee_id, date, check_in, check_out, status, late_minutes, worked_hours)
VALUES
    -- Mon 22 — on time
    (
        'c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13',
        '2026-06-22',
        '2026-06-22 07:55:00+01',
        '2026-06-22 17:00:00+01',
        'present', 0, 9.00
    ),
    -- Tue 23 — on time
    (
        'c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13',
        '2026-06-23',
        '2026-06-23 08:00:00+01',
        '2026-06-23 17:05:00+01',
        'present', 0, 9.00
    ),
    -- Wed 24 — late (12 min)
    (
        'c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13',
        '2026-06-24',
        '2026-06-24 08:12:00+01',
        '2026-06-24 17:00:00+01',
        'late', 12, 8.80
    ),
    -- Thu 25 — on time
    (
        'c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13',
        '2026-06-25',
        '2026-06-25 07:58:00+01',
        '2026-06-25 17:00:00+01',
        'present', 0, 9.00
    ),
    -- Fri 26 — absent (no check-in)
    (
        'c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13',
        '2026-06-26',
        NULL, NULL,
        'absent', 0, 0.00
    );

-- Sara: 4 days present, 1 day absent
INSERT INTO attendance (employee_id, date, check_in, check_out, status, late_minutes, worked_hours)
VALUES
    -- Mon 22 — 09:00–18:00
    (
        'd0eebc99-9c0b-4ef8-bb6d-6bb9bd380a14',
        '2026-06-22',
        '2026-06-22 08:55:00+01',
        '2026-06-22 18:05:00+01',
        'present', 0, 9.00
    ),
    -- Tue 23 — 13:00–21:00
    (
        'd0eebc99-9c0b-4ef8-bb6d-6bb9bd380a14',
        '2026-06-23',
        '2026-06-23 12:58:00+01',
        '2026-06-23 21:00:00+01',
        'present', 0, 8.00
    ),
    -- Wed 24 — 09:00–18:00
    (
        'd0eebc99-9c0b-4ef8-bb6d-6bb9bd380a14',
        '2026-06-24',
        '2026-06-24 09:00:00+01',
        '2026-06-24 18:00:00+01',
        'present', 0, 9.00
    ),
    -- Thu 25 — 13:00–21:00
    (
        'd0eebc99-9c0b-4ef8-bb6d-6bb9bd380a14',
        '2026-06-25',
        '2026-06-25 13:00:00+01',
        '2026-06-25 21:00:00+01',
        'present', 0, 8.00
    ),
    -- Fri 26 — absent
    (
        'd0eebc99-9c0b-4ef8-bb6d-6bb9bd380a14',
        '2026-06-26',
        NULL, NULL,
        'absent', 0, 0.00
    );

-- === INDEXES ===

CREATE INDEX idx_employees_user_id       ON employees (user_id);
CREATE INDEX idx_work_schedules_emp_day  ON work_schedules (employee_id, day_of_week);
CREATE INDEX idx_attendance_emp_date     ON attendance (employee_id, date);
CREATE INDEX idx_attendance_date         ON attendance (date);
CREATE INDEX idx_attendance_status       ON attendance (status);
