import mysql.connector
from flask import Blueprint, render_template, request, redirect, url_for, flash
from utils.helpers import fetch_all, execute

constraints_bp = Blueprint("constraints", __name__, url_prefix="/constraints")


@constraints_bp.route("")
def show():
    try:
        rows = fetch_all("SELECT * FROM constraints ORDER BY id")
    except mysql.connector.Error:
        flash("Could not load constraints.", "error")
        rows = []
    hard = [r for r in rows if r["constraint_type"] == "Hard"]
    soft = [r for r in rows if r["constraint_type"] == "Soft"]
    return render_template("constraints.html", hard=hard, soft=soft)


@constraints_bp.route("/save", methods=["POST"])
def save():
    try:
        soft = fetch_all("SELECT id FROM constraints WHERE constraint_type = 'Soft'")
        for row in soft:
            cid = row["id"]
            enabled = 1 if request.form.get(f"enabled_{cid}") else 0
            try:
                weight = int(request.form.get(f"weight_{cid}", 1))
            except ValueError:
                weight = 1
            weight = max(1, min(weight, 10))
            execute("UPDATE constraints SET is_enabled = %s, weight = %s WHERE id = %s",
                    (enabled, weight, cid))
        flash("Constraints saved.", "success")
    except mysql.connector.Error:
        flash("Could not save constraints.", "error")
    return redirect(url_for("constraints.show"))