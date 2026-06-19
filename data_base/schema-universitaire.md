# Schéma de la Base de Données — FaceAttend (Contexte Universitaire)

> Version améliorée avec les suggestions d'intégrité, périodes académiques, salles, et polymorphisme des pointages.

---

## 1. Diagramme MCD (Modèle Conceptuel de Données)

```mermaid
erDiagram
    USERS {
        uuid id PK
        string email UK
        string password_hash
        enum role "student | teacher | admin"
        string full_name
        string phone
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    STUDENTS {
        uuid id PK, FK
        string student_number UK
        date date_of_birth
        string address
        uuid group_id FK
    }

    TEACHERS {
        uuid id PK, FK
        string employee_number UK
        string specialty
    }

    DEPARTMENTS_SPECIALTIES {
        uuid id PK
        string name
        string code UK
        text description
    }

    GROUPS_CLASSES {
        uuid id PK
        string name
        string level "L1 | L2 | L3 | M1 | M2"
        uuid department_id FK
    }

    ACADEMIC_PERIODS {
        uuid id PK
        string label "2024/2025 - S1"
        date start_date
        date end_date
        enum semester "S1 | S2"
    }

    COURSES {
        uuid id PK
        string name
        string code UK
        int credits
        uuid teacher_id FK
        uuid department_id FK
    }

    ROOMS {
        uuid id PK
        string name UK
        string building
        int capacity
    }

    CLASS_SESSIONS {
        uuid id PK
        uuid course_id FK
        uuid group_id FK
        uuid room_id FK
        uuid academic_period_id FK
        datetime start_time
        datetime end_time
        string type "CM | TD | TP"
    }

    FACE_DATA {
        uuid id PK
        uuid student_id FK
        text encoding
        string image_path
        datetime created_at
    }

    ATTENDANCE_RECORDS {
        uuid id PK
        uuid student_id FK
        uuid session_id FK "NULLABLE → pointage campus"
        date record_date
        datetime check_in
        datetime check_out "NULLABLE"
        enum method "FACE | MANUAL"
        text notes
        datetime created_at
    }

    USERS ||--o| STUDENTS : ""
    USERS ||--o| TEACHERS : ""
    DEPARTMENTS_SPECIALTIES ||--o{ GROUPS_CLASSES : ""
    GROUPS_CLASSES ||--o{ STUDENTS : ""
    DEPARTMENTS_SPECIALTIES ||--o{ COURSES : ""
    USERS ||--o{ COURSES : "enseignant responsable"
    COURSES ||--o{ CLASS_SESSIONS : ""
    GROUPS_CLASSES ||--o{ CLASS_SESSIONS : ""
    ROOMS ||--o{ CLASS_SESSIONS : ""
    ACADEMIC_PERIODS ||--o{ CLASS_SESSIONS : ""
    STUDENTS ||--o{ FACE_DATA : ""
    STUDENTS ||--o{ ATTENDANCE_RECORDS : ""
    CLASS_SESSIONS ||--o{ ATTENDANCE_RECORDS : ""
```

---

## 2. Diagramme de Classes (UML)

```mermaid
classDiagram
    class User {
        +UUID id
        +String email
        +String password_hash
        +Role role
        +String full_name
        +String phone
        +Boolean is_active
        +DateTime created_at
        +DateTime updated_at
        +login() Token
        +has_permission(perm) bool
    }

    class Student {
        +UUID id
        +String student_number
        +Date date_of_birth
        +String address
        +GroupClass group
        +get_attendance_summary() dict
        +get_face_encodings() List~FaceData~
    }

    class Teacher {
        +UUID id
        +String employee_number
        +String specialty
        +List~Course~ courses
        +get_schedule() List~ClassSession~
    }

    class DepartmentSpecialty {
        +UUID id
        +String name
        +String code
        +String description
        +List~GroupClass~ groups
        +List~Course~ courses
    }

    class GroupClass {
        +UUID id
        +String name
        +String level
        +DepartmentSpecialty department
        +List~Student~ students
        +List~ClassSession~ sessions
    }

    class AcademicPeriod {
        +UUID id
        +String label
        +Date start_date
        +Date end_date
        +Semester semester
    }

    class Course {
        +UUID id
        +String name
        +String code
        +Integer credits
        +Teacher teacher
        +DepartmentSpecialty department
        +List~ClassSession~ sessions
    }

    class Room {
        +UUID id
        +String name
        +String building
        +Integer capacity
    }

    class ClassSession {
        +UUID id
        +Course course
        +GroupClass group
        +Room room
        +AcademicPeriod period
        +DateTime start_time
        +DateTime end_time
        +SessionType type
        +List~AttendanceRecord~ records
    }

    class FaceData {
        +UUID id
        +Student student
        +String encoding
        +String image_path
        +DateTime created_at
    }

    class AttendanceRecord {
        +UUID id
        +Student student
        +ClassSession session
        +Date record_date
        +DateTime check_in
        +DateTime check_out
        +RecognitionMethod method
        +String notes
        +DateTime created_at
    }

    User <|-- Student : extends
    User <|-- Teacher : extends
    Student "1" --> "1" GroupClass : belongs to
    GroupClass "*" --> "1" DepartmentSpecialty : belongs to
    Course "*" --> "1" DepartmentSpecialty : belongs to
    Course "*" --> "1" Teacher : taught by
    ClassSession "*" --> "1" Course : concerns
    ClassSession "*" --> "1" GroupClass : for
    ClassSession "*" --> "1" Room : in
    ClassSession "*" --> "1" AcademicPeriod : during
    FaceData "*" --> "1" Student : belongs to
    AttendanceRecord "*" --> "1" Student : concerns
    AttendanceRecord "*" --> "0..1" ClassSession : linked to (nullable)
```

---

## 3. Dictionnaire des Tables

### 3.1 `users` — Table unique d'authentification

**Rôle :** Centralise l'authentification et les identités de toutes les personnes (étudiants, enseignants, administrateurs). C'est la porte d'entrée du système.

**Pourquoi :** Au lieu d'avoir 3 tables séparées avec login/mot de passe (Étudiants, Enseignants, Admins), une seule table unifie l'auth, simplifie le code et évite la redondance. Un enseignant peut aussi être étudiant (doctorant) — un seul compte avec un profil `Teacher`.

| Champ | Type | Contraintes | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Identifiant unique |
| email | VARCHAR(255) | UNIQUE, NOT NULL | Email de connexion |
| password_hash | VARCHAR(255) | NOT NULL | Hash bcrypt du mot de passe |
| role | ENUM | `student`, `teacher`, `admin`, NOT NULL | Rôle dans le système |
| full_name | VARCHAR(255) | NOT NULL | Nom complet |
| phone | VARCHAR(20) | NULLABLE | Téléphone |
| is_active | BOOLEAN | DEFAULT `true` | Soft-delete / désactivation |
| created_at | TIMESTAMPTZ | DEFAULT `now()` | Date de création |
| updated_at | TIMESTAMPTZ | DEFAULT `now()` | Date de modification |

---

### 3.2 `students` — Profil étudiant (extension de `users`)

**Rôle :** Contient les informations spécifiques aux étudiants (matricule, date de naissance, groupe d'affectation). Chaque étudiant est d'abord un `user` avec `role = 'student'`.

**Pourquoi :** Les étudiants ont des champs que les enseignants et admins n'ont pas (matricule, groupe, date naissance). Une table séparée évite d'avoir des colonnes NULL chez les non-étudiants et permet de lier facilement les pointages et les données faciales.

| Champ | Type | Contraintes | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, FK → `users.id` ON DELETE CASCADE | Référence au compte user |
| student_number | VARCHAR(20) | UNIQUE, NOT NULL | Numéro matricule |
| date_of_birth | DATE | NULLABLE | Date de naissance |
| address | TEXT | NULLABLE | Adresse |
| group_id | UUID | FK → `groups_classes.id`, NOT NULL | Groupe/classe d'affectation |

---

### 3.3 `teachers` — Profil enseignant (extension de `users`)

**Rôle :** Contient les informations spécifiques aux enseignants (numéro d'employé, spécialité). Chaque enseignant est d'abord un `user` avec `role = 'teacher'`.

**Pourquoi :** Les enseignants sont responsables des cours et peuvent consulter les pointages de leurs séances. Ils n'ont pas besoin de groupe ni de matricule étudiant, mais ont un numéro d'employé et une spécialité. Cette séparation garde le modèle propre.

| Champ | Type | Contraintes | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, FK → `users.id` ON DELETE CASCADE | Référence au compte user |
| employee_number | VARCHAR(20) | UNIQUE, NOT NULL | Numéro d'employé |
| specialty | VARCHAR(255) | NULLABLE | Spécialité / domaine |

---

### 3.4 `departments_specialties` — Filières / Départements

**Rôle :** Structure l'université en filières/départements (Informatique, Génie Civil, Médecine, etc.). Permet d'organiser les groupes, les cours et les étudiants par filière.

**Pourquoi :** Une université a plusieurs filières. Les rapports de présence par filière, les cours spécifiques à une filière, et l'organisation des groupes en dépendent. Sans cette table, on ne pourrait pas filtrer « tous les étudiants de la filière INFO ».

| Champ | Type | Contraintes | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Identifiant unique |
| name | VARCHAR(255) | NOT NULL | Nom (ex: Informatique, Génie Civil) |
| code | VARCHAR(20) | UNIQUE, NOT NULL | Code court (ex: INFO, GC) |
| description | TEXT | NULLABLE | Description optionnelle |

---

### 3.5 `groups_classes` — Niveaux / Groupes

**Rôle :** Divise chaque filière en groupes pédagogiques (L2-INFO-A, L2-INFO-B, M1-GC, etc.). Un étudiant appartient à un seul groupe.

**Pourquoi :** Les séances (cours) sont planifiées par groupe, pas par étudiant individuellement. Les pointages sont ensuite rattachés au groupe via la séance. Cette table permet de générer les emplois du temps et de filtrer les présences par groupe/classe.

| Champ | Type | Contraintes | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Identifiant unique |
| name | VARCHAR(255) | NOT NULL | Nom (ex: L2-INFO-A) |
| level | ENUM | `L1`, `L2`, `L3`, `M1`, `M2`, NOT NULL | Niveau d'étude |
| department_id | UUID | FK → `departments_specialties.id`, NOT NULL | Filière de rattachement |

---

### 3.6 `academic_periods` — Périodes académiques (NOUVEAU)

**Rôle :** Définit les semestres et années universitaires (ex: « 2024/2025 - S1 »). Chaque séance de cours est rattachée à une période.

**Pourquoi :** Sans cette table, on ne peut pas générer de rapports par semestre, archiver les données d'une année, ou vérifier qu'une séance se déroule dans une période valide. Essentiel pour le suivi longitudinal des étudiants.

| Champ | Type | Contraintes | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Identifiant unique |
| label | VARCHAR(100) | NOT NULL | Ex: « 2024/2025 - S1 » |
| start_date | DATE | NOT NULL | Date de début |
| end_date | DATE | NOT NULL | Date de fin |
| semester | ENUM | `S1`, `S2`, NOT NULL | Semestre |

---

### 3.7 `courses` — Matières / Cours

**Rôle :** Liste toutes les matières enseignées (Algèbre, Réseaux, Base de données, etc.). Chaque cours a un enseignant responsable et appartient à une filière.

**Pourquoi :** Les séances et les pointages sont organisés autour des cours. Cette table permet de savoir « combien d'heures d'INFO401 ont eu lieu », « quel enseignant est responsable », et « quels sont les cours de la filière INFO ». Elle porte aussi les crédits ECTS, utiles pour les relevés de notes.

| Champ | Type | Contraintes | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Identifiant unique |
| name | VARCHAR(255) | NOT NULL | Nom du cours |
| code | VARCHAR(20) | UNIQUE, NOT NULL | Code matière (ex: INFO401) |
| credits | INTEGER | DEFAULT `0` | Nombre de crédits ECTS |
| teacher_id | UUID | FK → `users.id`, NOT NULL | Enseignant responsable |
| department_id | UUID | FK → `departments_specialties.id`, NOT NULL | Filière propriétaire du cours |

---

### 3.8 `rooms` — Salles (NOUVEAU)

**Rôle :** Référence toutes les salles de l'université (amphis, salles de TD, labos). Chaque séance de cours se déroule dans une salle spécifique.

**Pourquoi :** Sans cette table, la salle n'est qu'un champ texte dans `class_sessions`, ce qui empêche de détecter les conflits d'occupation (deux cours dans la même salle au même moment). Elle permet aussi de filtrer les pointages par bâtiment ou de vérifier la capacité.

| Champ | Type | Contraintes | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Identifiant unique |
| name | VARCHAR(100) | UNIQUE, NOT NULL | Numéro/nom de salle |
| building | VARCHAR(100) | NULLABLE | Bâtiment |
| capacity | INTEGER | DEFAULT `0` | Capacité maximale |

---

### 3.9 `class_sessions` — Séances (Emploi du temps)

**Rôle :** C'est **le planning** — chaque ligne représente une séance réelle ou prévue (ex: « Cours d'Algèbre du groupe L2-INFO-A, le lundi 8h-10h en Amphi 3, Semestre 1 »).

**Pourquoi :** C'est la table pivot entre les cours, les groupes, les salles et les périodes. Les pointages par cours sont liés à une séance spécifique. Sans elle, on ne pourrait pas savoir à quel cours correspond un pointage, ni générer l'emploi du temps. C'est également elle qui permet de détecter les absences : si une séance a eu lieu mais qu'un étudiant n'a pas pointé, on peut le marquer absent automatiquement.

| Champ | Type | Contraintes | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Identifiant unique |
| course_id | UUID | FK → `courses.id`, NOT NULL | Matière concernée |
| group_id | UUID | FK → `groups_classes.id`, NOT NULL | Groupe concerné |
| room_id | UUID | FK → `rooms.id`, NOT NULL | Salle |
| academic_period_id | UUID | FK → `academic_periods.id`, NOT NULL | Période académique |
| start_time | TIMESTAMPTZ | NOT NULL | Début du cours |
| end_time | TIMESTAMPTZ | NOT NULL, CHECK(end_time > start_time) | Fin du cours |
| type | ENUM | `CM`, `TD`, `TP`, NOT NULL | Type de séance |

---

### 3.10 `face_data` — Données biométriques

**Rôle :** Stocke les encodages faciaux (vecteurs de 128 floats) extraits des photos des étudiants, utilisés par le modèle de reconnaissance faciale pour identifier qui pointe.

**Pourquoi :** Le système de reconnaissance a besoin de références biométriques pour comparer et identifier un visage. Chaque étudiant peut avoir plusieurs encodages (différents angles, différentes photos) pour améliorer la précision. C'est le cœur du système « sans contact » — sans cette table, pas de reconnaissance possible. Les données sont stockées sous forme de texte JSON pour être facilement chargées en mémoire par la bibliothèque `face_recognition`.

| Champ | Type | Contraintes | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Identifiant unique |
| student_id | UUID | FK → `students.id` ON DELETE CASCADE, NOT NULL | Étudiant concerné |
| encoding | TEXT | NOT NULL | Encodage facial (JSON array 128 floats) |
| image_path | VARCHAR(500) | NULLABLE | Chemin de l'image source |
| created_at | TIMESTAMPTZ | DEFAULT `now()` | Date d'enregistrement |

---

### 3.11 `attendance_records` — Pointages (table centrale)

**Rôle :** Table la **plus importante** du système. Chaque ligne représente une détection de présence par reconnaissance faciale, que ce soit pour un cours spécifique (lié à une séance) ou pour une entrée/sortie générale du campus.

**Pourquoi :** C'est elle qui répond à la question « l'étudiant X était-il présent au cours Y ? » ou « l'étudiant X est-il sur le campus aujourd'hui ? ». Elle est conçue pour être **polymorphe** : si `session_id` est renseigné → pointage de cours ; si `session_id` est NULL → pointage campus. Les contraintes d'unicité empêchent les doublons (un étudiant ne peut pas pointer deux fois la même séance ou avoir deux entrées campus le même jour). Le `check_out` permet de mesurer la durée de présence sur le campus.

| Champ | Type | Contraintes | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Identifiant unique |
| student_id | UUID | FK → `students.id` ON DELETE CASCADE, NOT NULL | Étudiant pointé |
| session_id | UUID | FK → `class_sessions.id`, **NULLABLE** | NULL = pointage campus, renseigné = pointage cours |
| record_date | DATE | NOT NULL | Date du pointage |
| check_in | TIMESTAMPTZ | NOT NULL | Heure d'arrivée |
| check_out | TIMESTAMPTZ | NULLABLE | Heure de départ (pour campus) |
| method | ENUM | `FACE`, `MANUAL`, NOT NULL | Méthode de reconnaissance |
| notes | TEXT | NULLABLE | Notes optionnelles |
| created_at | TIMESTAMPTZ | DEFAULT `now()` | Date de création |

**Contraintes :**
- `UNIQUE(student_id, session_id)` — pas de doublon par séance
- `UNIQUE(student_id, record_date)` — 1 seul pointage campus par jour
- `CHECK(check_out IS NULL OR check_out > check_in)`
- `CHECK(session_id IS NOT NULL OR ...)` — au moins un contexte défini

---

## 4. Résumé des relations

```
users (role=student) ── 1:1 ── students ── 1:N ── face_data
                                          ── 1:N ── attendance_records
                                                    |
                                                    └── 0:1 ── class_sessions

users (role=teacher) ── 1:1 ── teachers ── 1:N ── courses

departments_specialties ── 1:N ── groups_classes ── 1:N ── students
                        ── 1:N ── courses

academic_periods ── 1:N ── class_sessions ── 1:N ── attendance_records
courses ── 1:N ── class_sessions
groups_classes ── 1:N ── class_sessions
rooms ── 1:N ── class_sessions
```

---

## 5. Contraintes d'intégrité clés

```sql
-- Pas de doublon de pointage par séance pour un étudiant
UNIQUE (student_id, session_id);

-- Pas de doublon de pointage campus par jour
UNIQUE (student_id, record_date) WHERE session_id IS NULL;

-- Cohérence temporelle
CHECK (check_out IS NULL OR check_out > check_in);

-- Horaires de séance cohérents
CHECK (end_time > start_time);

-- Un étudiant appartient forcément à un groupe
NOT NULL (students.group_id);
```

---

## 6. Améliorations par rapport à la proposition initiale

| Proposition initiale | Version améliorée |
|---|---|
| 3 tables users (Étudiants, Enseignants, Admins) | 1 table `users` avec `role` + extensions `students` / `teachers` |
| Pas de période académique | Table `academic_periods` |
| Salle = champ texte | Table `rooms` |
| Pointage cours / campus = tables séparées ou flou | `session_id NULLABLE` dans `attendance_records` |
| Pas de `check_in` / `check_out` | Colonnes `check_in`, `check_out` avec contrainte |
| Peu de contraintes d'intégrité | `UNIQUE`, `CHECK`, clés étrangères explicites |
