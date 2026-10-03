from flask import Blueprint
from utils.crud import register_crud

rooms_bp = Blueprint("rooms", __name__, url_prefix="/rooms")

register_crud(rooms_bp, {
    "table": "rooms",
    "title": "Rooms",
    "singular": "Room",
    "list_sql": (
        "SELECT id, name, building, room_type, capacity, "
        "IF(is_available, 'Available', 'Unavailable') AS availability FROM rooms "
        "WHERE name LIKE %s OR building LIKE %s ORDER BY name"
    ),
    "columns": [("id", "ID"), ("name", "Room"), ("building", "Building"),
                ("room_type", "Type"), ("capacity", "Capacity"), ("availability", "Availability")],
    "badges": ["availability"],
    "fields": [
        {"name": "name", "label": "Room Name", "type": "text"},
        {"name": "building", "label": "Building", "type": "text"},
        {"name": "room_type", "label": "Room Type", "type": "select",
         "options": [("Classroom", "Classroom"), ("Laboratory", "Laboratory"),
                     ("Seminar Hall", "Seminar Hall")]},
        {"name": "capacity", "label": "Capacity", "type": "number", "min": 1, "max": 500},
        {"name": "is_available", "label": "Availability", "type": "select",
         "options": [(1, "Available"), (0, "Unavailable")]},
    ],
    "defaults": {"room_type": "Classroom", "capacity": 60, "is_available": 1},
    "dup_message": "A room with this name already exists.",
    "confirm_delete": "Delete this room? Its timetable entries will also be deleted.",
})