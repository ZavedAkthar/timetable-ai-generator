from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from io import BytesIO
import re
import mysql.connector

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from utils.helpers import fetch_all, execute
from optimizer.scheduler import generate_timetable
from optimizer.genetic_optimizer import optimize_timetable
from optimizer.validator import validate_schedule


timetable_bp = Blueprint(
    "timetable",
    __name__,
    url_prefix="/timetable"
)


DAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
]


VIEWS = {
    "class": (
        "Class",
        "SELECT id, name FROM classes ORDER BY name",
        "tt.class_id",
    ),

    "teacher": (
        "Teacher",
        "SELECT id, name FROM teachers ORDER BY name",
        "tt.teacher_id",
    ),

    "room": (
        "Room",
        "SELECT id, name FROM rooms ORDER BY name",
        "tt.room_id",
    ),
}


# =========================================================
# TIME FORMATTER
# =========================================================

def fmt(value):
    """
    Convert MySQL TIME value into HH:MM format.
    """

    if value is None:
        return ""

    # MySQL connector may return timedelta
    if hasattr(value, "total_seconds"):

        seconds = int(
            value.total_seconds()
        )

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60

        return f"{hours:02d}:{minutes:02d}"

    # Fallback if value is already a string
    value = str(value)

    return value[:5]


# =========================================================
# SCHEDULE STRUCTURE VALIDATION
# =========================================================

def check_schedule_uniqueness(schedule):
    """
    Check all database-level uniqueness rules before saving.

    This prevents errors such as:

        Duplicate entry 'Tuesday-5-1'

    from reaching MySQL.
    """

    errors = []

    class_slots = set()
    teacher_slots = set()
    room_slots = set()

    for item in schedule:

        day = item["day"]
        period = item["period"]
        class_id = item["class_id"]
        teacher_id = item["teacher_id"]
        room_id = item["room_id"]

        # ---------------------------------------------
        # Class + Day + Period
        # ---------------------------------------------

        class_key = (
            day,
            period,
            class_id,
        )

        if class_key in class_slots:

            errors.append(
                f"Duplicate class slot: "
                f"{day}, period {period}, "
                f"class {class_id}."
            )

        class_slots.add(class_key)

        # ---------------------------------------------
        # Teacher + Day + Period
        # ---------------------------------------------

        teacher_key = (
            day,
            period,
            teacher_id,
        )

        if teacher_key in teacher_slots:

            errors.append(
                f"Duplicate teacher slot: "
                f"{day}, period {period}, "
                f"teacher {teacher_id}."
            )

        teacher_slots.add(teacher_key)

        # ---------------------------------------------
        # Room + Day + Period
        # ---------------------------------------------

        room_key = (
            day,
            period,
            room_id,
        )

        if room_key in room_slots:

            errors.append(
                f"Duplicate room slot: "
                f"{day}, period {period}, "
                f"room {room_id}."
            )

        room_slots.add(room_key)

    # Remove duplicate messages
    return list(dict.fromkeys(errors))


# =========================================================
# TIMETABLE DISPLAY
# =========================================================

@timetable_bp.route("")
def show():

    view = request.args.get(
        "view",
        "class"
    )

    if view not in VIEWS:
        view = "class"

    _, options_sql, column = VIEWS[view]

    options = fetch_all(
        options_sql
    )

    selected = request.args.get(
        "item",
        type=int
    )

    valid_ids = [
        option["id"]
        for option in options
    ]

    if selected not in valid_ids:

        selected = (
            options[0]["id"]
            if options
            else None
        )

    # -----------------------------------------------------
    # Time slots
    # -----------------------------------------------------

    slots = []

    for slot in fetch_all(
        """
        SELECT
            period,
            start_time,
            end_time
        FROM time_slots
        ORDER BY period
        """
    ):

        slots.append(
            {
                "period": slot["period"],
                "start": fmt(
                    slot["start_time"]
                ),
                "end": fmt(
                    slot["end_time"]
                ),
            }
        )

    # -----------------------------------------------------
    # Timetable grid
    # -----------------------------------------------------

    grid = {}

    if selected is not None:

        rows = fetch_all(
            """
            SELECT
                tt.id AS timetable_id,
                tt.day,
                tt.period,
                tt.class_id,
                tt.subject_id,
                tt.teacher_id,
                tt.room_id,

                s.name AS subject,

                t.name AS teacher,

                c.name AS class_name,

                r.name AS room

            FROM timetable tt

            JOIN subjects s
                ON s.id = tt.subject_id

            JOIN teachers t
                ON t.id = tt.teacher_id

            JOIN classes c
                ON c.id = tt.class_id

            JOIN rooms r
                ON r.id = tt.room_id

            WHERE
                """
            + column
            + """
                = %s

            ORDER BY
                tt.period
            """,
            (selected,),
        )

        for row in rows:

            grid[
                f"{row['day']}-{row['period']}"
            ] = row

    view_choices = [
        (key, spec[0])
        for key, spec in VIEWS.items()
    ]

    return render_template(
        "timetable.html",

        view=view,

        view_choices=view_choices,

        options=options,

        selected=selected,

        slots=slots,

        days=DAYS,

        grid=grid,
        edit_subjects=fetch_all("SELECT id, name, class_id FROM subjects ORDER BY name"),
        edit_teachers=fetch_all("SELECT id, name, status FROM teachers ORDER BY name"),
        edit_rooms=fetch_all("SELECT id, name, is_available, capacity FROM rooms ORDER BY name"),
    )


# =========================================================
# MANUAL TIMETABLE EDITING
# =========================================================

@timetable_bp.route("/edit/<int:entry_id>", methods=["POST"])
def edit_entry(entry_id):
    view = request.form.get("view", "class")
    selected = request.form.get("item", type=int)
    day = request.form.get("day", "")
    period = request.form.get("period", type=int)
    subject_id = request.form.get("subject_id", type=int)
    teacher_id = request.form.get("teacher_id", type=int)
    room_id = request.form.get("room_id", type=int)

    def back():
        if view not in VIEWS:
            return redirect(url_for("timetable.show"))
        return redirect(url_for("timetable.show", view=view, item=selected))

    if view not in VIEWS or not selected or not day or day not in DAYS or not all([period, subject_id, teacher_id, room_id]):
        flash("Please provide valid timetable details.", "error")
        return back()

    try:
        current = fetch_all("SELECT id, day, period, class_id FROM timetable WHERE id = %s", (entry_id,))
        if not current:
            flash("This timetable entry no longer exists.", "error")
            return back()
        current = current[0]
        class_id = current["class_id"]

        # Ensure the edited slot belongs to the selected view.
        _, _, view_column = VIEWS[view]
        selected_check = fetch_all(
            f"SELECT tt.id FROM timetable tt WHERE tt.id = %s AND {view_column} = %s",
            (entry_id, selected),
        )
        if not selected_check:
            flash("The selected timetable entry does not match this view.", "error")
            return back()

        slot_exists = fetch_all("SELECT period FROM time_slots WHERE period = %s", (period,))
        subject = fetch_all("SELECT id, class_id FROM subjects WHERE id = %s", (subject_id,))
        teacher = fetch_all("SELECT id, status, max_hours_per_day, max_hours_per_week FROM teachers WHERE id = %s", (teacher_id,))
        room = fetch_all("SELECT id, is_available, capacity FROM rooms WHERE id = %s", (room_id,))
        class_row = fetch_all("SELECT num_students FROM classes WHERE id = %s", (class_id,))

        if not slot_exists or not subject or not teacher or not room or not class_row:
            flash("One of the selected records is invalid or no longer exists.", "error")
            return back()
        if subject[0]["class_id"] != class_id:
            flash("The selected subject does not belong to this class.", "error")
            return back()
        if teacher[0]["status"] != "Available":
            flash("The selected teacher is not currently available.", "error")
            return back()
        if not room[0]["is_available"]:
            flash("The selected room is unavailable.", "error")
            return back()
        if room[0]["capacity"] < class_row[0]["num_students"]:
            flash("The selected room does not have enough capacity for this class.", "error")
            return back()

        # Respect explicitly blocked teacher slots. A missing availability row
        # is treated as available, matching a permissive default timetable setup.
        availability = fetch_all(
            "SELECT is_available FROM teacher_availability WHERE teacher_id = %s AND day = %s AND period = %s",
            (teacher_id, day, period),
        )
        if availability and not availability[0]["is_available"]:
            flash("The selected teacher is unavailable during this day and period.", "error")
            return back()

        # Hard conflict checks; exclude the entry being edited.
        conflicts = [
            ("class_id", class_id, "This class already has another subject in that period."),
            ("teacher_id", teacher_id, "This teacher is already assigned in that period."),
            ("room_id", room_id, "This room is already booked in that period."),
        ]
        for field, value, message in conflicts:
            found = fetch_all(
                f"SELECT id FROM timetable WHERE day = %s AND period = %s AND {field} = %s AND id <> %s",
                (day, period, value, entry_id),
            )
            if found:
                flash(message, "error")
                return back()

        # Enforce teacher workload limits for the proposed assignment.
        daily = fetch_all(
            "SELECT COUNT(*) AS total FROM timetable WHERE teacher_id = %s AND day = %s AND id <> %s",
            (teacher_id, day, entry_id),
        )[0]["total"]
        weekly = fetch_all(
            "SELECT COUNT(*) AS total FROM timetable WHERE teacher_id = %s AND id <> %s",
            (teacher_id, entry_id),
        )[0]["total"]
        if daily >= teacher[0]["max_hours_per_day"]:
            flash("This change would exceed the teacher's daily workload limit.", "error")
            return back()
        if weekly >= teacher[0]["max_hours_per_week"]:
            flash("This change would exceed the teacher's weekly workload limit.", "error")
            return back()

        execute(
            "UPDATE timetable SET day = %s, period = %s, subject_id = %s, teacher_id = %s, room_id = %s WHERE id = %s",
            (day, period, subject_id, teacher_id, room_id, entry_id),
        )
        flash("Timetable entry updated successfully.", "success")

    except mysql.connector.Error as error:
        if error.errno == 1062:
            flash("This change creates a class, teacher, or room conflict.", "error")
        else:
            flash("Could not update the timetable. Please check the database and try again.", "error")
    except Exception as error:
        print("MANUAL TIMETABLE EDIT ERROR:", error)
        flash("An unexpected error occurred while updating the timetable.", "error")

    return back()


# =========================================================
# EXPORT HELPERS
# =========================================================

def get_export_data():
    """Build the same day/period grid used by the timetable webpage."""
    view = request.args.get("view", "class")
    if view not in VIEWS:
        view = "class"

    _, options_sql, column = VIEWS[view]
    options = fetch_all(options_sql)
    selected = request.args.get("item", type=int)
    valid_ids = [option["id"] for option in options]

    if selected not in valid_ids:
        selected = options[0]["id"] if options else None

    if selected is None:
        return view, None, None, [], {}

    selected_option = next(
        (option for option in options if option["id"] == selected),
        None
    )

    slots = []
    for slot in fetch_all("""
        SELECT period, start_time, end_time
        FROM time_slots
        ORDER BY period
    """):
        slots.append({
            "period": slot["period"],
            "start": fmt(slot["start_time"]),
            "end": fmt(slot["end_time"]),
        })

    rows = fetch_all(f"""
        SELECT
            tt.day, tt.period,
            s.name AS subject,
            t.name AS teacher,
            c.name AS class_name,
            r.name AS room
        FROM timetable tt
        JOIN subjects s ON s.id = tt.subject_id
        JOIN teachers t ON t.id = tt.teacher_id
        JOIN classes c ON c.id = tt.class_id
        JOIN rooms r ON r.id = tt.room_id
        WHERE {column} = %s
    """, (selected,))

    grid = {
        f"{row['day']}-{row['period']}": row
        for row in rows
    }

    return view, selected, selected_option["name"], slots, grid


def export_filename(view, name, extension):
    safe_name = re.sub(
        r"[^A-Za-z0-9_-]+", "_", name or "timetable"
    ).strip("_")
    return f"{view}_timetable_{safe_name or 'download'}.{extension}"


def timetable_cell_text(cell, view):
    """Return cell text following the website's class/teacher/room rules."""
    if not cell:
        return ""

    lines = [str(cell["subject"])]

    if view == "class":
        lines.append(str(cell["teacher"]))
    elif view == "teacher":
        lines.append(str(cell["class_name"]))
    else:
        lines.append(f"{cell['class_name']} | {cell['teacher']}")

    if view != "room":
        lines.append(str(cell["room"]))

    return "\n".join(lines)


# =========================================================
# DOWNLOAD EXCEL - WEBSITE GRID LAYOUT
# =========================================================

@timetable_bp.route("/export/excel")
def download_excel():
    view, selected, name, slots, grid = get_export_data()

    if selected is None:
        flash("No records available to export.", "error")
        return redirect(url_for("timetable.show"))

    if not grid:
        flash("No timetable entries available for this selection.", "error")
        return redirect(url_for("timetable.show", view=view, item=selected))

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Timetable"

    # Title and selected view
    sheet.merge_cells("A1:G1")
    sheet["A1"] = f"TIMETABLE - {VIEWS[view][0].upper()} VIEW"
    sheet["A1"].font = Font(bold=True, size=16, color="FFFFFF")
    sheet["A1"].fill = PatternFill("solid", fgColor="E9683E")
    sheet["A1"].alignment = Alignment(horizontal="center", vertical="center")
    sheet.row_dimensions[1].height = 30

    sheet.merge_cells("A2:G2")
    sheet["A2"] = f"Selected: {name}"
    sheet["A2"].font = Font(bold=True, size=11)
    sheet["A2"].alignment = Alignment(horizontal="center")
    sheet.row_dimensions[2].height = 22

    headers = ["Time"] + [day[:3] for day in DAYS]
    for col_num, heading in enumerate(headers, start=1):
        cell = sheet.cell(row=4, column=col_num, value=heading)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="E9683E")
        cell.alignment = Alignment(horizontal="center", vertical="center")

    thin_border = Border(
        left=Side(style="thin", color="D6D6D6"),
        right=Side(style="thin", color="D6D6D6"),
        top=Side(style="thin", color="D6D6D6"),
        bottom=Side(style="thin", color="D6D6D6"),
    )

    for row_num, slot in enumerate(slots, start=5):
        time_cell = sheet.cell(
            row=row_num,
            column=1,
            value=f"{slot['start']}\n{slot['end']}"
        )
        time_cell.font = Font(bold=True, size=9)
        time_cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        time_cell.fill = PatternFill("solid", fgColor="F2F2F2")
        time_cell.border = thin_border

        for col_num, day in enumerate(DAYS, start=2):
            cell_data = grid.get(f"{day}-{slot['period']}")
            value = timetable_cell_text(cell_data, view)
            excel_cell = sheet.cell(row=row_num, column=col_num, value=value)
            excel_cell.alignment = Alignment(
                horizontal="center", vertical="center", wrap_text=True
            )
            excel_cell.font = Font(
                size=9, bold=bool(cell_data), color="333333"
            )
            if cell_data:
                excel_cell.fill = PatternFill("solid", fgColor="FFF4EF")
            excel_cell.border = thin_border

        sheet.row_dimensions[row_num].height = 58

    sheet.column_dimensions["A"].width = 14
    for col_num in range(2, 8):
        sheet.column_dimensions[get_column_letter(col_num)].width = 22

    sheet.freeze_panes = "B5"
    sheet.sheet_view.showGridLines = False
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.paperSize = sheet.PAPERSIZE_A4
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 1
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.print_area = f"A1:G{max(4 + len(slots), 4)}"
    sheet.sheet_properties.pageSetUpPr.autoPageBreaks = False
    sheet.page_margins.left = 0.25
    sheet.page_margins.right = 0.25
    sheet.page_margins.top = 0.4
    sheet.page_margins.bottom = 0.4

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name=export_filename(view, name, "xlsx"),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# =========================================================
# DOWNLOAD PDF - WEBSITE GRID LAYOUT
# =========================================================

@timetable_bp.route("/export/pdf")
def download_pdf():
    view, selected, name, slots, grid = get_export_data()

    if selected is None:
        flash("No records available to export.", "error")
        return redirect(url_for("timetable.show"))

    if not grid:
        flash("No timetable entries available for this selection.", "error")
        return redirect(url_for("timetable.show", view=view, item=selected))

    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=18,
        leftMargin=18,
        topMargin=22,
        bottomMargin=22
    )

    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    title_style.fontName = "Helvetica-Bold"
    title_style.fontSize = 16
    title_style.textColor = colors.HexColor("#333333")
    subtitle_style = styles["Normal"]
    subtitle_style.fontSize = 10
    subtitle_style.alignment = 1

    cell_style = ParagraphStyle(
        "TimetableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7,
        leading=9,
        alignment=1,
        textColor=colors.HexColor("#333333")
    )
    header_style = ParagraphStyle(
        "TimetableHeader",
        parent=cell_style,
        fontName="Helvetica-Bold",
        textColor=colors.white
    )

    story = [
        Paragraph("TIMETABLE", title_style),
        Paragraph(
            f"{VIEWS[view][0]}: {name}",
            subtitle_style
        ),
        Spacer(1, 12)
    ]

    table_data = [
        [Paragraph("Time", header_style)] +
        [Paragraph(day[:3], header_style) for day in DAYS]
    ]

    for slot in slots:
        time_text = f"{slot['start']}<br/>{slot['end']}"
        table_row = [Paragraph(time_text, cell_style)]

        for day in DAYS:
            cell_data = grid.get(f"{day}-{slot['period']}")
            if not cell_data:
                table_row.append("")
                continue

            lines = [str(cell_data["subject"])]
            if view == "class":
                lines.append(str(cell_data["teacher"]))
            elif view == "teacher":
                lines.append(str(cell_data["class_name"]))
            else:
                lines.append(
                    f"{cell_data['class_name']} | {cell_data['teacher']}"
                )

            if view != "room":
                lines.append(str(cell_data["room"]))

            paragraph_text = "<br/>".join(
                line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                for line in lines
            )
            table_row.append(Paragraph(paragraph_text, cell_style))

        table_data.append(table_row)

    page_width = landscape(A4)[0] - 36
    time_col_width = 62
    day_col_width = (page_width - time_col_width) / len(DAYS)

    table = Table(
        table_data,
        colWidths=[time_col_width] + [day_col_width] * len(DAYS),
        repeatRows=1,
        hAlign="CENTER"
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9683E")),
        ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#F2F2F2")),
        ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#D6D6D6")),
        ("ROWBACKGROUNDS", (1, 1), (-1, -1), [
            colors.white, colors.HexColor("#FFF4EF")
        ]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))

    story.append(table)
    document.build(story)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name=export_filename(view, name, "pdf"),
        mimetype="application/pdf"
    )


# =========================================================
# GENERATE TIMETABLE
# =========================================================

@timetable_bp.route(
    "/generate",
    methods=["POST"]
)
def generate():

    try:

        # =================================================
        # 1. GET SUBJECTS
        # =================================================

        subjects = fetch_all(
            """
            SELECT
                s.id,
                s.name,
                s.class_id,
                s.teacher_id,
                s.hours_per_week,
                c.num_students

            FROM subjects s

            JOIN classes c
                ON c.id = s.class_id

            ORDER BY
                s.hours_per_week DESC
            """
        )

        if not subjects:

            flash(
                "No subjects found.",
                "error"
            )

            return redirect(
                url_for("timetable.show")
            )

        # =================================================
        # 2. GET TEACHERS
        # =================================================

        teachers = fetch_all(
            """
            SELECT
                id,
                name,
                max_hours_per_day,
                max_hours_per_week,
                status

            FROM teachers

            WHERE status = 'Available'
            """
        )

        if not teachers:

            flash(
                "No available teachers found.",
                "error"
            )

            return redirect(
                url_for("timetable.show")
            )

        # =================================================
        # 3. GET ROOMS
        # =================================================

        rooms = fetch_all(
            """
            SELECT
                id,
                name,
                capacity,
                is_available

            FROM rooms

            WHERE is_available = 1
            """
        )

        if not rooms:

            flash(
                "No available rooms found.",
                "error"
            )

            return redirect(
                url_for("timetable.show")
            )

        # =================================================
        # 4. GET PERIODS
        # =================================================

        periods = fetch_all(
            """
            SELECT
                period,
                start_time,
                end_time

            FROM time_slots

            ORDER BY period
            """
        )

        if not periods:

            flash(
                "No time periods found.",
                "error"
            )

            return redirect(
                url_for("timetable.show")
            )

        # =================================================
        # 5. GET TEACHER AVAILABILITY
        # =================================================

        availability = fetch_all(
            """
            SELECT
                teacher_id,
                day,
                period,
                is_available

            FROM teacher_availability
            """
        )

        # =================================================
        # 6. GENERATE INITIAL TIMETABLE
        # =================================================

        schedule = generate_timetable(
            subjects=subjects,
            teachers=teachers,
            rooms=rooms,
            periods=periods,
            availability=availability,
        )

        if not schedule:

            flash(
                "The scheduler could not generate "
                "any timetable entries.",
                "error"
            )

            return redirect(
                url_for("timetable.show")
            )

        # =================================================
        # 7. SHOW BASE FITNESS
        # =================================================

        try:

            from optimizer.genetic_optimizer import (
                calculate_fitness
            )

            base_fitness = calculate_fitness(
                schedule
            )

            print()
            print(
                f"Base fitness: {base_fitness}"
            )

        except Exception:

            base_fitness = None

        # =================================================
        # 8. RUN GENETIC OPTIMIZER
        # =================================================

        optimized_schedule = optimize_timetable(
            initial_schedule=schedule,

            periods=periods,

            population_size=30,

            generations=50,

            mutation_rate=0.20,
        )

        if not optimized_schedule:

            flash(
                "Optimization produced an empty timetable.",
                "error"
            )

            return redirect(
                url_for("timetable.show")
            )

        schedule = optimized_schedule

        # =================================================
        # 9. SHOW OPTIMIZED FITNESS
        # =================================================

        try:

            optimized_fitness = calculate_fitness(
                schedule
            )

            print(
                f"Optimized fitness: "
                f"{optimized_fitness}"
            )

            if (
                base_fitness is not None
                and base_fitness > 0
            ):

                improvement = (
                    (
                        base_fitness
                        - optimized_fitness
                    )
                    / base_fitness
                ) * 100

                print()
                print(
                    "============================================================"
                )
                print(
                    "OPTIMIZATION RESULTS"
                )
                print(
                    "============================================================"
                )
                print(
                    f"Before: {base_fitness}"
                )
                print(
                    f"After: {optimized_fitness}"
                )
                print(
                    f"Improvement: "
                    f"{improvement:.2f} %"
                )
                print(
                    "============================================================"
                )

        except Exception:
            pass

        # =================================================
        # 10. VALIDATE HARD CONSTRAINTS
        # =================================================

        is_valid, validation_errors = validate_schedule(
            schedule=schedule,

            subjects=subjects,

            teachers=teachers,

            rooms=rooms,

            availability=availability,
        )

        if not is_valid:

            print()
            print(
                "TIMETABLE VALIDATION FAILED"
            )

            for error in validation_errors:

                print(
                    f" - {error}"
                )

            flash(
                "Generated timetable failed validation. "
                "No timetable was saved.",
                "error"
            )

            return redirect(
                url_for("timetable.show")
            )

        # =================================================
        # 11. EXTRA DATABASE UNIQUENESS CHECK
        # =================================================

        uniqueness_errors = (
            check_schedule_uniqueness(
                schedule
            )
        )

        if uniqueness_errors:

            print()
            print(
                "DATABASE UNIQUENESS VALIDATION FAILED"
            )

            for error in uniqueness_errors:

                print(
                    f" - {error}"
                )

            flash(
                "Generated timetable contains duplicate "
                "class, teacher, or room slots. "
                "No timetable was saved.",
                "error"
            )

            return redirect(
                url_for("timetable.show")
            )

        # =================================================
        # 12. ONLY NOW DELETE OLD TIMETABLE
        # =================================================

        execute(
            "DELETE FROM timetable"
        )

        # =================================================
        # 13. SAVE NEW TIMETABLE
        # =================================================

        saved_count = 0

        for item in schedule:

            execute(
                """
                INSERT INTO timetable
                (
                    day,
                    period,
                    class_id,
                    subject_id,
                    teacher_id,
                    room_id
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,

                (
                    item["day"],
                    item["period"],
                    item["class_id"],
                    item["subject_id"],
                    item["teacher_id"],
                    item["room_id"],
                ),
            )

            saved_count += 1

        # =================================================
        # 14. SUCCESS MESSAGE
        # =================================================

        flash(
            f"Timetable generated successfully: "
            f"{saved_count} classes scheduled.",
            "success"
        )

    # =====================================================
    # ERROR HANDLING
    # =====================================================

    except Exception as e:

        print()
        print(
            "TIMETABLE GENERATION ERROR:"
        )
        print(
            str(e)
        )

        flash(
            f"Timetable generation failed: {str(e)}",
            "error"
        )

    return redirect(
        url_for("timetable.show")
    )