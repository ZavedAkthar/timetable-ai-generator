import mysql.connector
from flask import Blueprint, render_template
from utils.helpers import get_db_connection

dashboard_bp = Blueprint("dashboard", __name__)

COUNT_QUERIES = {
    "teachers": "SELECT COUNT(*) FROM teachers",
    "subjects": "SELECT COUNT(*) FROM subjects",
    "classes": "SELECT COUNT(*) FROM classes",
    "rooms": "SELECT COUNT(*) FROM rooms WHERE is_available = TRUE",
}


def get_counts():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        counts = {}
        for key, sql in COUNT_QUERIES.items():
            cursor.execute(sql)
            counts[key] = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return counts
    except mysql.connector.Error:
        return None


@dashboard_bp.route("/")
def dashboard():
    return render_template("dashboard.html", counts=get_counts())