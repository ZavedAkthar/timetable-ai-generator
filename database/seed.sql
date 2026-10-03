SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE notifications;
TRUNCATE TABLE timetable;
TRUNCATE TABLE constraints;
TRUNCATE TABLE teacher_availability;
TRUNCATE TABLE time_slots;
TRUNCATE TABLE subjects;
TRUNCATE TABLE rooms;
TRUNCATE TABLE classes;
TRUNCATE TABLE teachers;
SET FOREIGN_KEY_CHECKS = 1;

INSERT INTO time_slots (period, start_time, end_time) VALUES
(1, '09:00', '10:00'),
(2, '10:00', '11:00'),
(3, '11:15', '12:15'),
(4, '12:15', '13:15'),
(5, '14:00', '15:00'),
(6, '15:00', '16:00');

INSERT INTO constraints (name, description, constraint_type, is_enabled, weight) VALUES
('Teacher clash', 'A teacher cannot teach two classes at the same time', 'Hard', TRUE, 0),
('Class clash', 'A class cannot have two subjects at the same time', 'Hard', TRUE, 0),
('Room clash', 'A room cannot be used by two classes at the same time', 'Hard', TRUE, 0),
('Teacher availability', 'Teacher must be available in the slot', 'Hard', TRUE, 0),
('Room availability', 'Room must be available', 'Hard', TRUE, 0),
('Room capacity', 'Room capacity must be at least the class strength', 'Hard', TRUE, 0),
('Weekly subject hours', 'Each subject must get its required weekly hours', 'Hard', TRUE, 0),
('Avoid consecutive classes', 'Reduce back-to-back classes for teachers', 'Soft', TRUE, 3),
('Balance teacher workload', 'Spread teaching hours evenly across days', 'Soft', TRUE, 4),
('Balance section workload', 'Spread class hours evenly across days', 'Soft', TRUE, 3),
('Minimize idle gaps', 'Reduce long idle periods in a day', 'Soft', TRUE, 2),
('Balanced daily schedule', 'Avoid overloaded or empty days', 'Soft', TRUE, 2),
('Minimize room changes', 'Keep a class in the same room where possible', 'Soft', TRUE, 1);

INSERT INTO teachers (id, name, email, department, designation, max_hours_per_day, max_hours_per_week) VALUES
(1, 'Dr. Ahmed', 'ahmed@example.com', 'Computer Science', 'Professor', 4, 20),
(2, 'Dr. Priya Sharma', 'priya@example.com', 'Computer Science', 'Associate Professor', 4, 20),
(3, 'Mr. Rahul Verma', 'rahul@example.com', 'Computer Science', 'Assistant Professor', 4, 18),
(4, 'Ms. Anita Rao', 'anita@example.com', 'Computer Science', 'Assistant Professor', 4, 18),
(5, 'Dr. Kiran Kumar', 'kiran@example.com', 'Computer Science', 'Professor', 4, 20);

INSERT INTO classes (id, name, department, year, section, num_students) VALUES
(1, 'CSE-A', 'Computer Science', 2, 'A', 60),
(2, 'CSE-B', 'Computer Science', 2, 'B', 55);

INSERT INTO rooms (id, name, building, room_type, capacity, is_available) VALUES
(1, 'Room 201', 'Block A', 'Classroom', 60, TRUE),
(2, 'Room 202', 'Block A', 'Classroom', 65, TRUE),
(3, 'Lab 1', 'Block B', 'Laboratory', 60, TRUE),
(4, 'Seminar Hall', 'Block C', 'Seminar Hall', 120, TRUE);

INSERT INTO subjects (name, code, department, class_id, teacher_id, hours_per_week, subject_type) VALUES
('Artificial Intelligence', 'CS401', 'CSE', 1, 1, 4, 'Theory'),
('Database Management Systems', 'CS402', 'CSE', 1, 2, 4, 'Theory'),
('Operating Systems', 'CS403', 'CSE', 1, 3, 3, 'Theory'),
('Computer Networks', 'CS404', 'CSE', 1, 4, 3, 'Theory'),
('Machine Learning', 'CS405', 'CSE', 1, 5, 4, 'Theory'),
('DBMS Lab', 'CS406', 'CSE', 1, 2, 2, 'Lab'),
('Artificial Intelligence', 'CS401', 'CSE', 2, 1, 4, 'Theory'),
('Database Management Systems', 'CS402', 'CSE', 2, 2, 4, 'Theory'),
('Operating Systems', 'CS403', 'CSE', 2, 3, 3, 'Theory'),
('Computer Networks', 'CS404', 'CSE', 2, 4, 3, 'Theory'),
('Machine Learning', 'CS405', 'CSE', 2, 5, 4, 'Theory'),
('DBMS Lab', 'CS406', 'CSE', 2, 2, 2, 'Lab');