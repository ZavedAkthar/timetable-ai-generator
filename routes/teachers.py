import mysql.connector
from mysql.connector import errorcode
from flask import Blueprint, render_template, request, redirect, url_for, flash
from utils.helpers import fetch_all, execute

teachers_bp = Blueprint("teachers", __name__, url_prefix="/teachers")

STATUSES = ["Available", "Absent", "Unavailable"]
FIELDS = ["name", "email", "department", "designation",
          "max_hours_per_day", "max_hours_per_week", "status"]


def read_form():
    form = {f: request.form.get(f, "").strip() for f in FIELDS}
    form["email"] = form["email"].lower()
    errors = []

    if not form["name"]:
        errors.append("Name is required.")
    if "@" not in form["email"] or "." not in form["email"]:
        errors.append("Enter a valid email address.")
    if not form["department"]:
        errors.append("Department is required.")
    if not form["designation"]:
        errors.append("Designation is required.")
    if form["status"] not in STATUSES:
        errors.append("Invalid availability status.")

    try:
        per_day = int(form["max_hours_per_day"])
        per_week = int(form["max_hours_per_week"])
    except ValueError:
        errors.append("Hours must be whole numbers.")
    else:
        if not 1 <= per_day <= 8:
            errors.append("Max hours per day must be between 1 and 8.")
        if not 1 <= per_week <= 48:
            errors.append("Max hours per week must be between 1 and 48.")
        if per_week < per_day:
            errors.append("Weekly hours cannot be less than daily hours.")
        if not errors:
            form["max_hours_per_day"] = per_day
            form["max_hours_per_week"] = per_week
    return form, errors


def db_message(err):
    if err.errno == errorcode.ER_DUP_ENTRY:
        return "A teacher with this email already exists."
    return "Database error. Please try again."


def render_form(form, errors, title):
    return render_template("teacher_form.html", form=form, errors=errors,
                           statuses=STATUSES, title=title)


@teachers_bp.route("")
def list_teachers():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    like = f"%{q}%"
    sql = ("SELECT * FROM teachers "
           "WHERE (name LIKE %s OR email LIKE %s OR department LIKE %s)")
    params = [like, like, like]
    if status in STATUSES:
        sql += " AND status = %s"
        params.append(status)
    sql += " ORDER BY name"
    try:
        teachers = fetch_all(sql, params)
    except mysql.connector.Error:
        flash("Could not load teachers.", "error")
        teachers = []
    return render_template("teachers.html", teachers=teachers,
                           q=q, status=status, statuses=STATUSES)


@teachers_bp.route("/add", methods=["GET", "POST"])
def add_teacher():
    form = {"max_hours_per_day": 4, "max_hours_per_week": 20, "status": "Available"}
    errors = []
    if request.method == "POST":
        form, errors = read_form()
        if not errors:
            try:
                execute(
                    "INSERT INTO teachers (name, email, department, designation, "
                    "max_hours_per_day, max_hours_per_week, status) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    [form[f] for f in FIELDS])
                flash("Teacher added.", "success")
                return redirect(url_for("teachers.list_teachers"))
            except mysql.connector.Error as err:
                errors.append(db_message(err))
    return render_form(form, errors, "Add Teacher")


@teachers_bp.route("/<int:teacher_id>/edit", methods=["GET", "POST"])
def edit_teacher(teacher_id):
    rows = fetch_all("SELECT * FROM teachers WHERE id = %s", (teacher_id,))
    if not rows:
        flash("Teacher not found.", "error")
        return redirect(url_for("teachers.list_teachers"))
    form, errors = rows[0], []
    if request.method == "POST":
        form, errors = read_form()
        if not errors:
            try:
                execute(
                    "UPDATE teachers SET name=%s, email=%s, department=%s, "
                    "designation=%s, max_hours_per_day=%s, max_hours_per_week=%s, "
                    "status=%s WHERE id=%s",
                    [form[f] for f in FIELDS] + [teacher_id])
                flash("Teacher updated.", "success")
                return redirect(url_for("teachers.list_teachers"))
            except mysql.connector.Error as err:
                errors.append(db_message(err))
    return render_form(form, errors, "Edit Teacher")


@teachers_bp.route("/<int:teacher_id>/delete", methods=["POST"])
def delete_teacher(teacher_id):
    try:
        execute("DELETE FROM teachers WHERE id = %s", (teacher_id,))
        flash("Teacher deleted.", "success")
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ROW_IS_REFERENCED_2:
            flash("Cannot delete: this teacher is assigned to subjects. "
                  "Reassign those subjects first.", "error")
        else:
            flash("Database error. Please try again.", "error")
    return redirect(url_for("teachers.list_teachers"))