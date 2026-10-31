import os
import json
import uuid
import tempfile

from datetime import datetime, time, timedelta
from io import BytesIO

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    send_file,
    current_app,
)

from openpyxl import Workbook

from utils.helpers import get_db_connection
from utils.excel_importer import REQUIRED_SHEETS, read_excel_file


# ==================================================
# BLUEPRINT CONFIGURATION
# ==================================================

imports_bp = Blueprint(
    "imports",
    __name__,
    url_prefix="/imports"
)

UPLOAD_FOLDER = os.path.join(
    tempfile.gettempdir(),
    "timetable_excel_imports"
)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

MAX_FILE_SIZE = 5 * 1024 * 1024


# ==================================================
# HELPER FUNCTIONS
# ==================================================

def parse_bool(value):

    if isinstance(value, bool):
        return value

    if isinstance(value, int) and value in (0, 1):
        return bool(value)

    value = str(value).strip().lower()

    if value in ("true", "yes", "1"):
        return True

    if value in ("false", "no", "0"):
        return False

    raise ValueError(f"Invalid boolean value: {value}")


def required(record, field):

    value = record.get(field)

    if value is None or str(value).strip() == "":
        raise ValueError(
            f"Row {record.get('_row_number')}: "
            f"{field} is required."
        )

    return value


def normalize_time(value):

    if isinstance(value, timedelta):

        total_seconds = int(value.total_seconds())

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        return f"{hours:02}:{minutes:02}:{seconds:02}"

    if isinstance(value, (datetime, time)):
        return value.strftime("%H:%M:%S")

    return str(value).strip()


def validate_positive(value, field):

    number = int(value)

    if number <= 0:
        raise ValueError(
            f"{field} must be greater than zero."
        )

    return number


# ==================================================
# DATABASE DUPLICATE VALIDATION
# ==================================================

def validate_against_database(data):
    """Reject conflicting time slots but allow existing records."""

    errors = []
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT period, start_time, end_time FROM time_slots"
        )

        existing_slots = {
            int(period): (
                normalize_time(start),
                normalize_time(end)
            )
            for period, start, end in cursor.fetchall()
        }

        for row in data["Time Slots"]:
            period = int(row["period"])

            if period in existing_slots:
                uploaded = (
                    normalize_time(row["start_time"]),
                    normalize_time(row["end_time"])
                )

                if uploaded != existing_slots[period]:
                    errors.append(
                        f"Time Slots, row {row['_row_number']}: "
                        f"Period {period} already exists with "
                        "different timings."
                    )

    except Exception as error:
        current_app.logger.exception(
            "Database validation failed"
        )
        errors.append(
            f"Unable to validate against database: {error}"
        )

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return errors
    """
    Check uploaded Excel records against existing
    MySQL records before displaying the preview.

    Matching existing time slots are allowed.
    """

    errors = []

    conn = None
    cursor = None

    try:

        conn = get_db_connection()
        cursor = conn.cursor()

        # ------------------------------------------
        # 1. EXISTING TEACHERS
        # ------------------------------------------

        cursor.execute(
            "SELECT email FROM teachers"
        )

        existing_emails = {
            str(row[0]).strip().lower()
            for row in cursor.fetchall()
        }

        for row in data["Teachers"]:

            email = str(
                row["email"]
            ).strip().lower()

            if email in existing_emails:

                errors.append(
                    f"Teachers, row {row['_row_number']}: "
                    f"Email already exists: {email}"
                )

        # ------------------------------------------
        # 2. EXISTING CLASSES
        # ------------------------------------------

        cursor.execute(
            "SELECT name FROM classes"
        )

        existing_classes = {
            str(row[0]).strip().lower()
            for row in cursor.fetchall()
        }

        for row in data["Classes"]:

            name = str(
                row["name"]
            ).strip().lower()

            if name in existing_classes:

                errors.append(
                    f"Classes, row {row['_row_number']}: "
                    f"Class already exists: {row['name']}"
                )

        # ------------------------------------------
        # 3. EXISTING ROOMS
        # ------------------------------------------

        cursor.execute(
            "SELECT name FROM rooms"
        )

        existing_rooms = {
            str(row[0]).strip().lower()
            for row in cursor.fetchall()
        }

        for row in data["Rooms"]:

            name = str(
                row["name"]
            ).strip().lower()

            if name in existing_rooms:

                errors.append(
                    f"Rooms, row {row['_row_number']}: "
                    f"Room already exists: {row['name']}"
                )

        # ------------------------------------------
        # 4. EXISTING SUBJECTS
        # ------------------------------------------

        cursor.execute(
            """
            SELECT s.code, c.name
            FROM subjects s
            JOIN classes c
                ON s.class_id = c.id
            """
        )

        existing_subjects = {
            (
                str(code).strip().lower(),
                str(class_name).strip().lower()
            )
            for code, class_name in cursor.fetchall()
        }

        for row in data["Subjects"]:

            key = (
                str(row["code"]).strip().lower(),
                str(row["class_name"]).strip().lower()
            )

            if key in existing_subjects:

                errors.append(
                    f"Subjects, row {row['_row_number']}: "
                    f"Subject code {row['code']} already exists "
                    f"for class {row['class_name']}."
                )

        # ------------------------------------------
        # 5. EXISTING TIME SLOTS
        # ------------------------------------------

        cursor.execute(
            """
            SELECT period, start_time, end_time
            FROM time_slots
            """
        )

        existing_slots = {}

        for period, start, end in cursor.fetchall():

            existing_slots[int(period)] = (
                normalize_time(start),
                normalize_time(end)
            )

        for row in data["Time Slots"]:

            period = int(row["period"])

            if period in existing_slots:

                uploaded_times = (
                    normalize_time(row["start_time"]),
                    normalize_time(row["end_time"])
                )

                if uploaded_times != existing_slots[period]:

                    errors.append(
                        f"Time Slots, row {row['_row_number']}: "
                        f"Period {period} already exists "
                        "with different timings."
                    )

        # ------------------------------------------
        # 6. EXISTING TEACHER AVAILABILITY
        # ------------------------------------------

        cursor.execute(
            """
            SELECT
                ta.day,
                ta.period,
                t.email
            FROM teacher_availability ta
            JOIN teachers t
                ON ta.teacher_id = t.id
            """
        )

        existing_availability = {
            (
                str(email).strip().lower(),
                str(day).strip().lower(),
                int(period)
            )
            for day, period, email in cursor.fetchall()
        }

        for row in data["Teacher Availability"]:

            key = (
                str(row["teacher_email"]).strip().lower(),
                str(row["day"]).strip().lower(),
                int(row["period"])
            )

            if key in existing_availability:

                errors.append(
                    f"Teacher Availability, "
                    f"row {row['_row_number']}: "
                    f"Availability already exists for "
                    f"{row['teacher_email']} on "
                    f"{row['day']}, period {row['period']}."
                )

    except Exception as error:

        current_app.logger.exception(
            "Database validation failed"
        )

        errors.append(
            f"Unable to validate against database: {error}"
        )

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

    return errors


# ==================================================
# IMPORT PAGE
# ==================================================

@imports_bp.route("/")
def index():

    return render_template("imports.html")


# ==================================================
# DOWNLOAD EXCEL TEMPLATE
# ==================================================

@imports_bp.route("/template")
def download_template():

    workbook = Workbook()

    workbook.remove(workbook.active)

    for sheet_name, columns in REQUIRED_SHEETS.items():

        sheet = workbook.create_sheet(sheet_name)

        sheet.append(columns)

        sheet.freeze_panes = "A2"

        for column in sheet.columns:

            column_letter = column[0].column_letter

            sheet.column_dimensions[
                column_letter
            ].width = 22

    output = BytesIO()

    workbook.save(output)

    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="timetable_import_template.xlsx",
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )


# ==================================================
# UPLOAD EXCEL FILE AND PREVIEW
# ==================================================

@imports_bp.route("/upload", methods=["POST"])
def upload_excel():

    # Check file size

    if (
        request.content_length
        and request.content_length > MAX_FILE_SIZE
    ):

        return render_template(
            "imports.html",
            errors=[
                "File size exceeds the 5 MB limit."
            ]
        ), 413

    # Check file existence

    if "excel_file" not in request.files:

        flash(
            "Please select an Excel file.",
            "danger"
        )

        return redirect(
            url_for("imports.index")
        )

    file = request.files["excel_file"]

    if not file.filename:

        flash(
            "No file selected.",
            "danger"
        )

        return redirect(
            url_for("imports.index")
        )

    # Check extension

    if not file.filename.lower().endswith(".xlsx"):

        return render_template(
            "imports.html",
            errors=[
                "Only .xlsx Excel files are supported."
            ]
        )

    # ----------------------------------------------
    # STEP 1: EXCEL VALIDATION
    # ----------------------------------------------

    data, errors = read_excel_file(file)

    if errors:

        return render_template(
            "imports.html",
            errors=errors
        )

    # ----------------------------------------------
    # STEP 2: DATABASE DUPLICATE VALIDATION
    # ----------------------------------------------

    database_errors = validate_against_database(data)

    if database_errors:

        return render_template(
            "imports.html",
            errors=database_errors
        )

    # ----------------------------------------------
    # STEP 3: STORE VALID UPLOAD
    # ----------------------------------------------

    token = uuid.uuid4().hex

    file_path = os.path.join(
        UPLOAD_FOLDER,
        f"{token}.json"
    )

    with open(
        file_path,
        "w",
        encoding="utf-8"
    ) as output:

        json.dump(
            data,
            output,
            ensure_ascii=False
        )

    session["import_token"] = token

    return render_template(
        "imports.html",
        preview=data
    )


# ==================================================
# CONFIRM AND IMPORT DATA INTO MYSQL
# ==================================================

@imports_bp.route("/confirm", methods=["POST"])
@imports_bp.route("/confirm", methods=["POST"])
def confirm_import():

    token = session.get("import_token")

    if not token:
        flash("Please upload an Excel file first.", "danger")
        return redirect(url_for("imports.index"))

    file_path = os.path.join(
        UPLOAD_FOLDER,
        f"{token}.json"
    )

    if not os.path.isfile(file_path):
        session.pop("import_token", None)
        return render_template(
            "imports.html",
            errors=["Upload expired. Please upload again."]
        )

    conn = None
    cursor = None

    try:
        with open(file_path, "r", encoding="utf-8") as source:
            data = json.load(source)

        conn = get_db_connection()
        cursor = conn.cursor()
        conn.start_transaction()

        counts = {}
        skipped = {}

        # ==========================================
        # 1. TEACHERS
        # ==========================================

        imported = 0
        skipped_count = 0

        for row in data["Teachers"]:

            email = required(row, "email").strip()

            cursor.execute(
                "SELECT id FROM teachers WHERE LOWER(email) = LOWER(%s)",
                (email,)
            )

            if cursor.fetchone():
                skipped_count += 1
                continue

            cursor.execute(
                """
                INSERT INTO teachers
                (name, email, department, designation,
                 max_hours_per_day, max_hours_per_week, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    required(row, "name"),
                    email,
                    required(row, "department"),
                    required(row, "designation"),
                    validate_positive(row["max_hours_per_day"], "Maximum hours per day"),
                    validate_positive(row["max_hours_per_week"], "Maximum hours per week"),
                    row["status"]
                )
            )

            imported += 1

        counts["Teachers"] = imported
        skipped["Teachers"] = skipped_count

        # ==========================================
        # 2. CLASSES
        # ==========================================

        imported = 0
        skipped_count = 0

        for row in data["Classes"]:

            name = required(row, "name").strip()

            cursor.execute(
                "SELECT id FROM classes WHERE LOWER(name) = LOWER(%s)",
                (name,)
            )

            if cursor.fetchone():
                skipped_count += 1
                continue

            cursor.execute(
                """
                INSERT INTO classes
                (name, department, year, section, num_students)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    name,
                    required(row, "department"),
                    int(row["year"]),
                    required(row, "section"),
                    validate_positive(row["num_students"], "Number of students")
                )
            )

            imported += 1

        counts["Classes"] = imported
        skipped["Classes"] = skipped_count

        # ==========================================
        # 3. ROOMS
        # ==========================================

        imported = 0
        skipped_count = 0

        for row in data["Rooms"]:

            name = required(row, "name").strip()

            cursor.execute(
                "SELECT id FROM rooms WHERE LOWER(name) = LOWER(%s)",
                (name,)
            )

            if cursor.fetchone():
                skipped_count += 1
                continue

            cursor.execute(
                """
                INSERT INTO rooms
                (name, building, room_type, capacity, is_available)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    name,
                    required(row, "building"),
                    row["room_type"],
                    validate_positive(row["capacity"], "Room capacity"),
                    parse_bool(row["is_available"])
                )
            )

            imported += 1

        counts["Rooms"] = imported
        skipped["Rooms"] = skipped_count

        # ==========================================
        # 4. TIME SLOTS
        # ==========================================

        imported = 0
        skipped_count = 0

        for row in data["Time Slots"]:

            period = int(row["period"])
            start = normalize_time(row["start_time"])
            end = normalize_time(row["end_time"])

            cursor.execute(
                """
                SELECT start_time, end_time
                FROM time_slots
                WHERE period = %s
                """,
                (period,)
            )

            existing = cursor.fetchone()

            if existing:
                if (
                    normalize_time(existing[0]) != start
                    or normalize_time(existing[1]) != end
                ):
                    raise ValueError(
                        f"Period {period} already exists with different timings."
                    )

                skipped_count += 1
                continue

            cursor.execute(
                """
                INSERT INTO time_slots (period, start_time, end_time)
                VALUES (%s, %s, %s)
                """,
                (period, start, end)
            )

            imported += 1

        counts["Time Slots"] = imported
        skipped["Time Slots"] = skipped_count

        # ==========================================
        # BUILD LOOKUP MAPS
        # ==========================================

        cursor.execute("SELECT id, name FROM classes")
        class_map = {
            name: class_id
            for class_id, name in cursor.fetchall()
        }

        cursor.execute("SELECT id, email FROM teachers")
        teacher_map = {
            email.strip().lower(): teacher_id
            for teacher_id, email in cursor.fetchall()
        }

        cursor.execute("SELECT period FROM time_slots")
        period_map = {
            period for (period,) in cursor.fetchall()
        }

        # ==========================================
        # 5. SUBJECTS
        # ==========================================

        imported = 0
        skipped_count = 0

        for row in data["Subjects"]:

            class_name = required(row, "class_name")
            code = required(row, "code")
            teacher_email = required(row, "teacher_email").strip().lower()

            class_id = class_map.get(class_name)
            teacher_id = teacher_map.get(teacher_email)

            if class_id is None:
                raise ValueError(f"Class not found: {class_name}")

            if teacher_id is None:
                raise ValueError(f"Teacher not found: {teacher_email}")

            cursor.execute(
                """
                SELECT id FROM subjects
                WHERE code = %s AND class_id = %s
                """,
                (code, class_id)
            )

            if cursor.fetchone():
                skipped_count += 1
                continue

            cursor.execute(
                """
                INSERT INTO subjects
                (name, code, department, class_id, teacher_id,
                 hours_per_week, subject_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    required(row, "name"),
                    code,
                    required(row, "department"),
                    class_id,
                    teacher_id,
                    validate_positive(row["hours_per_week"], "Hours per week"),
                    row["subject_type"]
                )
            )

            imported += 1

        counts["Subjects"] = imported
        skipped["Subjects"] = skipped_count

        # ==========================================
        # 6. TEACHER AVAILABILITY
        # ==========================================

        imported = 0
        skipped_count = 0

        for row in data["Teacher Availability"]:

            email = required(row, "teacher_email").strip().lower()
            day = required(row, "day")
            period = int(row["period"])

            teacher_id = teacher_map.get(email)

            if teacher_id is None:
                raise ValueError(f"Teacher not found: {email}")

            if period not in period_map:
                raise ValueError(f"Time slot not found: {period}")

            cursor.execute(
                """
                SELECT id
                FROM teacher_availability
                WHERE teacher_id = %s
                  AND day = %s
                  AND period = %s
                """,
                (teacher_id, day, period)
            )

            if cursor.fetchone():
                skipped_count += 1
                continue

            cursor.execute(
                """
                INSERT INTO teacher_availability
                (teacher_id, day, period, is_available)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    teacher_id,
                    day,
                    period,
                    parse_bool(row["is_available"])
                )
            )

            imported += 1

        counts["Teacher Availability"] = imported
        skipped["Teacher Availability"] = skipped_count

        # ==========================================
        # COMMIT
        # ==========================================

        conn.commit()

        os.remove(file_path)
        session.pop("import_token", None)

        return render_template(
            "imports.html",
            success=True,
            counts=counts,
            skipped=skipped
        )

    except Exception as error:

        if conn:
            conn.rollback()

        current_app.logger.exception("Excel import failed")

        return render_template(
            "imports.html",
            errors=[
                f"Import failed. No records were saved: {error}"
            ]
        )

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()