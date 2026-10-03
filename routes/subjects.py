from flask import Blueprint
from utils.crud import register_crud
from utils.helpers import fetch_all

subjects_bp = Blueprint("subjects", __name__, url_prefix="/subjects")


def class_options():
    rows = fetch_all("SELECT id, name FROM classes ORDER BY name")
    return [(r["id"], r["name"]) for r in rows]


def teacher_options():
    rows = fetch_all("SELECT id, name FROM teachers ORDER BY name")
    return [(r["id"], r["name"]) for r in rows]


register_crud(subjects_bp, {
    "table": "subjects",
    "title": "Subjects",
    "singular": "Subject",
    "list_sql": (
        "SELECT s.id, s.name, s.code, s.department, c.name AS class_name, "
        "t.name AS teacher_name, s.hours_per_week, s.subject_type "
        "FROM subjects s JOIN classes c ON c.id = s.class_id "
        "JOIN teachers t ON t.id = s.teacher_id "
        "WHERE s.name LIKE %s OR s.code LIKE %s OR c.name LIKE %s OR t.name LIKE %s "
        "ORDER BY c.name, s.name"
    ),
    "columns": [("id", "ID"), ("name", "Subject"), ("code", "Code"),
                ("department", "Dept"), ("class_name", "Class"),
                ("teacher_name", "Teacher"), ("hours_per_week", "Hrs/Week"),
                ("subject_type", "Type")],
    "fields": [
        {"name": "name", "label": "Subject Name", "type": "text"},
        {"name": "code", "label": "Subject Code", "type": "text"},
        {"name": "department", "label": "Department", "type": "text"},
        {"name": "class_id", "label": "Class / Section", "type": "select", "options": class_options},
        {"name": "teacher_id", "label": "Assigned Teacher", "type": "select", "options": teacher_options},
        {"name": "hours_per_week", "label": "Hours Per Week", "type": "number", "min": 1, "max": 10},
        {"name": "subject_type", "label": "Subject Type", "type": "select",
         "options": [("Theory", "Theory"), ("Lab", "Lab"), ("Tutorial", "Tutorial")]},
    ],
    "defaults": {"department": "CSE", "hours_per_week": 3, "subject_type": "Theory"},
    "dup_message": "This subject code already exists for the selected class.",
    "confirm_delete": "Delete this subject? Its timetable entries will also be deleted.",
})