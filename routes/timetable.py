from flask import Blueprint, render_template, request, redirect, url_for, flash

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
                tt.day,
                tt.period,

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