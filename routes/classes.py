from flask import Blueprint
from utils.crud import register_crud

classes_bp = Blueprint("classes", __name__, url_prefix="/classes")

register_crud(classes_bp, {
    "table": "classes",
    "title": "Classes",
    "singular": "Class",
    "list_sql": (
        "SELECT id, name, department, year, section, num_students FROM classes "
        "WHERE name LIKE %s OR department LIKE %s ORDER BY name"
    ),
    "columns": [("id", "ID"), ("name", "Class"), ("department", "Department"),
                ("year", "Year"), ("section", "Section"), ("num_students", "Students")],
    "fields": [
        {"name": "name", "label": "Class Name (e.g. CSE-A)", "type": "text"},
        {"name": "department", "label": "Department", "type": "text"},
        {"name": "year", "label": "Year (1-4)", "type": "number", "min": 1, "max": 4},
        {"name": "section", "label": "Section", "type": "text"},
        {"name": "num_students", "label": "Number of Students", "type": "number", "min": 1, "max": 300},
    ],
    "defaults": {"department": "Computer Science", "year": 2, "num_students": 60},
    "dup_message": "A class with this name already exists.",
    "confirm_delete": "Delete this class? Its subjects and timetable entries will also be deleted.",
})