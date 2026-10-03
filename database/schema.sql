SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS notifications, timetable, constraints, teacher_availability,
                     time_slots, subjects, rooms, classes, teachers;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE teachers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    department VARCHAR(100) NOT NULL,
    designation VARCHAR(60) NOT NULL,
    max_hours_per_day INT NOT NULL DEFAULT 4 CHECK (max_hours_per_day > 0),
    max_hours_per_week INT NOT NULL DEFAULT 20 CHECK (max_hours_per_week > 0),
    status ENUM('Available', 'Absent', 'Unavailable') NOT NULL DEFAULT 'Available'
);

CREATE TABLE classes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    department VARCHAR(100) NOT NULL,
    year INT NOT NULL CHECK (year BETWEEN 1 AND 4),
    section VARCHAR(5) NOT NULL,
    num_students INT NOT NULL CHECK (num_students > 0)
);

CREATE TABLE rooms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(60) NOT NULL UNIQUE,
    building VARCHAR(60) NOT NULL,
    room_type ENUM('Classroom', 'Laboratory', 'Seminar Hall') NOT NULL DEFAULT 'Classroom',
    capacity INT NOT NULL CHECK (capacity > 0),
    is_available BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE subjects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    code VARCHAR(20) NOT NULL,
    department VARCHAR(100) NOT NULL,
    class_id INT NOT NULL,
    teacher_id INT NOT NULL,
    hours_per_week INT NOT NULL CHECK (hours_per_week > 0),
    subject_type ENUM('Theory', 'Lab', 'Tutorial') NOT NULL DEFAULT 'Theory',
    UNIQUE KEY uq_subject_class (code, class_id),
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
    FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE RESTRICT
);

CREATE TABLE time_slots (
    period INT PRIMARY KEY,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL
);

CREATE TABLE teacher_availability (
    id INT AUTO_INCREMENT PRIMARY KEY,
    teacher_id INT NOT NULL,
    day ENUM('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday') NOT NULL,
    period INT NOT NULL,
    is_available BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE KEY uq_teacher_slot (teacher_id, day, period),
    FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
    FOREIGN KEY (period) REFERENCES time_slots(period)
);

CREATE TABLE constraints (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL UNIQUE,
    description VARCHAR(255),
    constraint_type ENUM('Hard', 'Soft') NOT NULL,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    weight INT NOT NULL DEFAULT 1
);

CREATE TABLE timetable (
    id INT AUTO_INCREMENT PRIMARY KEY,
    day ENUM('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday') NOT NULL,
    period INT NOT NULL,
    class_id INT NOT NULL,
    subject_id INT NOT NULL,
    teacher_id INT NOT NULL,
    room_id INT NOT NULL,
    UNIQUE KEY uq_class_slot (day, period, class_id),
    UNIQUE KEY uq_teacher_slot (day, period, teacher_id),
    UNIQUE KEY uq_room_slot (day, period, room_id),
    FOREIGN KEY (period) REFERENCES time_slots(period),
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
    FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
    FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
);

CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message VARCHAR(255) NOT NULL,
    notification_type VARCHAR(40) NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);