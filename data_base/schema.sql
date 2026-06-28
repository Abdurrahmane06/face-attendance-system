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

-- 2. work_schedules — weekly schedule templates
-- Each row represents a full weekly schedule assigned to one or more employees.
-- NULL start/end time means non-working day.
CREATE TABLE work_schedules (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT NOT NULL,
    monday_start        TIME,
    monday_end          TIME,
    tuesday_start       TIME,
    tuesday_end         TIME,
    wednesday_start     TIME,
    wednesday_end       TIME,
    thursday_start      TIME,
    thursday_end        TIME,
    friday_start        TIME,
    friday_end          TIME,
    saturday_start      TIME,
    saturday_end        TIME,
    sunday_start        TIME,
    sunday_end          TIME,
    grace_period_minutes INTEGER DEFAULT 10,
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now(),
    deleted_at          TIMESTAMPTZ DEFAULT NULL
);

-- 3. employees — employee information
CREATE TABLE employees (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES profiles(id),
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    phone           TEXT,
    photo_url       TEXT,
    face_encoding   TEXT,
    schedule_id     UUID NOT NULL REFERENCES work_schedules(id),
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    deleted_at      TIMESTAMPTZ DEFAULT NULL
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
    justified       BOOLEAN DEFAULT FALSE,
    justification_id UUID REFERENCES justifications(id),
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    deleted_at      TIMESTAMPTZ DEFAULT NULL,
    UNIQUE(employee_id, date)
);

-- 5. absence_types — predefined absence categories
CREATE TABLE absence_types (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL UNIQUE,
    requires_doc    BOOLEAN DEFAULT FALSE,
    is_paid         BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    deleted_at      TIMESTAMPTZ DEFAULT NULL
);

-- 6. justifications — absence justifications managed by admin
CREATE TABLE justifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id     UUID NOT NULL REFERENCES employees(id),
    absence_type_id UUID NOT NULL REFERENCES absence_types(id),
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    document_url    TEXT,
    note            TEXT,
    created_by      UUID NOT NULL REFERENCES profiles(id),
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    deleted_at      TIMESTAMPTZ DEFAULT NULL,
    CHECK (end_date >= start_date)
);

-- === DATA ===

-- Profiles (IDs must match existing Supabase auth.users)
INSERT INTO profiles (id, role, display_name, is_active)
VALUES
    ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'admin',    'Ahmed Benali', TRUE),
    ('b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12', 'employee', 'Sara Dupont',  TRUE);

-- Work schedules — weekly templates
INSERT INTO work_schedules (id, name,
    monday_start, monday_end,
    tuesday_start, tuesday_end,
    wednesday_start, wednesday_end,
    thursday_start, thursday_end,
    friday_start, friday_end,
    saturday_start, saturday_end,
    sunday_start, sunday_end,
    grace_period_minutes)
VALUES
    (
        'e1eebc99-9c0b-4ef8-bb6d-6bb9bd380a01',
        'Standard Semaine (08:00-17:00)',
        '08:00', '17:00',
        '08:00', '17:00',
        '08:00', '17:00',
        '08:00', '17:00',
        '08:00', '17:00',
        NULL, NULL,
        NULL, NULL,
        10
    ),
    (
        'e1eebc99-9c0b-4ef8-bb6d-6bb9bd380a02',
        'Flex Semaine (09:00-18:00 / 13:00-21:00)',
        '09:00', '18:00',
        '13:00', '21:00',
        '09:00', '18:00',
        '13:00', '21:00',
        '09:00', '18:00',
        NULL, NULL,
        NULL, NULL,
        15
    );

-- Employees
INSERT INTO employees (id, user_id, first_name, last_name, phone, photo_url, face_encoding, schedule_id)
VALUES
    (
        'c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13',
        'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
        'Ahmed', 'Benali',
        '+213-555-123456',
        'https://storage.supabase.co/attendance/photos/ahmed-benali.jpg',
        'base64:W5Y8xP7qzR3...',
        'e1eebc99-9c0b-4ef8-bb6d-6bb9bd380a01'
    ),
    (
        'd0eebc99-9c0b-4ef8-bb6d-6bb9bd380a14',
        'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12',
        'Sara', 'Dupont',
        '+33-6-12-34-56-78',
        'https://storage.supabase.co/attendance/photos/sara-dupont.jpg',
        'base64:T2mH9kL4vQx...',
        'e1eebc99-9c0b-4ef8-bb6d-6bb9bd380a02'
    );

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

-- Absence types
INSERT INTO absence_types (id, name, requires_doc, is_paid) VALUES
    ('f1eebc99-9c0b-4ef8-bb6d-6bb9bd380a01', 'Maladie',          TRUE,  TRUE),
    ('f1eebc99-9c0b-4ef8-bb6d-6bb9bd380a02', 'Congé payé',       FALSE, TRUE),
    ('f1eebc99-9c0b-4ef8-bb6d-6bb9bd380a03', 'Motif familial',   TRUE,  TRUE),
    ('f1eebc99-9c0b-4ef8-bb6d-6bb9bd380a04', 'Formation',        FALSE, TRUE),
    ('f1eebc99-9c0b-4ef8-bb6d-6bb9bd380a05', 'Autre',            FALSE, FALSE);

-- Justifications — Ahmed a fourni un certificat pour son absence du 26 juin
INSERT INTO justifications (id, employee_id, absence_type_id, start_date, end_date, document_url, note, created_by)
VALUES (
    'f2eebc99-9c0b-4ef8-bb6d-6bb9bd380a01',
    'c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13',
    'f1eebc99-9c0b-4ef8-bb6d-6bb9bd380a01',
    '2026-06-26', '2026-06-26',
    'https://storage.supabase.co/justificatifs/ahmed-certificat-26-06.pdf',
    'Certificat médical fourni',
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'
);

-- Lier la justification à l'enregistrement attendance correspondant
UPDATE attendance
SET justified = TRUE,
    justification_id = 'f2eebc99-9c0b-4ef8-bb6d-6bb9bd380a01'
WHERE employee_id = 'c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13'
  AND date = '2026-06-26';

-- === INDEXES ===

CREATE INDEX idx_employees_user_id          ON employees (user_id);
CREATE INDEX idx_employees_schedule_id      ON employees (schedule_id);
CREATE INDEX idx_attendance_emp_date        ON attendance (employee_id, date);
CREATE INDEX idx_attendance_date            ON attendance (date);
CREATE INDEX idx_attendance_status          ON attendance (status);
CREATE INDEX idx_attendance_justified       ON attendance (justified) WHERE justified = TRUE;
CREATE INDEX idx_justifications_employee    ON justifications (employee_id);
CREATE INDEX idx_justifications_dates       ON justifications (start_date, end_date);
