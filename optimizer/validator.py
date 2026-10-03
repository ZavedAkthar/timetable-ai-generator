def validate_schedule(
    schedule,
    subjects,
    teachers,
    rooms,
    availability,
):
    """
    Validate a generated timetable against all hard constraints.

    Returns:
        (True, []) if valid
        (False, [error messages]) if invalid
    """

    errors = []

    # ---------------------------------------------------------
    # Create lookup maps
    # ---------------------------------------------------------

    teacher_map = {
        teacher["id"]: teacher
        for teacher in teachers
    }

    room_map = {
        room["id"]: room
        for room in rooms
    }

    subject_map = {
        subject["id"]: subject
        for subject in subjects
    }

    availability_map = {
        (
            item["teacher_id"],
            item["day"],
            item["period"],
        ): bool(item["is_available"])
        for item in availability
    }

    # ---------------------------------------------------------
    # Tracking sets
    # ---------------------------------------------------------

    class_slots = set()
    teacher_slots = set()
    room_slots = set()

    # Count hours
    subject_hours = {}
    teacher_daily_hours = {}
    teacher_weekly_hours = {}

    # ---------------------------------------------------------
    # Validate every timetable entry
    # ---------------------------------------------------------

    for item in schedule:

        day = item.get("day")
        period = item.get("period")
        class_id = item.get("class_id")
        subject_id = item.get("subject_id")
        teacher_id = item.get("teacher_id")
        room_id = item.get("room_id")

        # -----------------------------------------------------
        # Basic field validation
        # -----------------------------------------------------

        if day is None or period is None:
            errors.append("Timetable entry has missing day or period.")
            continue

        if class_id is None:
            errors.append(
                f"Missing class for {day}, period {period}."
            )
            continue

        if subject_id is None:
            errors.append(
                f"Missing subject for class {class_id}, "
                f"{day}, period {period}."
            )
            continue

        if teacher_id is None:
            errors.append(
                f"Missing teacher for subject {subject_id}, "
                f"{day}, period {period}."
            )
            continue

        if room_id is None:
            errors.append(
                f"Missing room for subject {subject_id}, "
                f"{day}, period {period}."
            )
            continue

        # -----------------------------------------------------
        # Lookup entities
        # -----------------------------------------------------

        subject = subject_map.get(subject_id)
        teacher = teacher_map.get(teacher_id)
        room = room_map.get(room_id)

        if subject is None:
            errors.append(
                f"Subject {subject_id} does not exist."
            )
            continue

        if teacher is None:
            errors.append(
                f"Teacher {teacher_id} does not exist."
            )
            continue

        if room is None:
            errors.append(
                f"Room {room_id} does not exist."
            )
            continue

        # -----------------------------------------------------
        # 1. Class conflict
        # -----------------------------------------------------

        class_key = (
            class_id,
            day,
            period,
        )

        if class_key in class_slots:
            errors.append(
                f"Class conflict: class {class_id} has "
                f"multiple classes on {day}, period {period}."
            )

        class_slots.add(class_key)

        # -----------------------------------------------------
        # 2. Teacher conflict
        # -----------------------------------------------------

        teacher_key = (
            teacher_id,
            day,
            period,
        )

        if teacher_key in teacher_slots:
            errors.append(
                f"Teacher conflict: teacher {teacher_id} has "
                f"multiple classes on {day}, period {period}."
            )

        teacher_slots.add(teacher_key)

        # -----------------------------------------------------
        # 3. Room conflict
        # -----------------------------------------------------

        room_key = (
            room_id,
            day,
            period,
        )

        if room_key in room_slots:
            errors.append(
                f"Room conflict: room {room_id} is used by "
                f"multiple classes on {day}, period {period}."
            )

        room_slots.add(room_key)

        # -----------------------------------------------------
        # 4. Teacher-subject assignment
        # -----------------------------------------------------

        expected_teacher_id = subject.get("teacher_id")

        if (
            expected_teacher_id is not None
            and teacher_id != expected_teacher_id
        ):
            errors.append(
                f"Teacher conflict: subject {subject_id} "
                f"is assigned to teacher {teacher_id}, "
                f"but its assigned teacher is "
                f"{expected_teacher_id}."
            )

        # -----------------------------------------------------
        # 5. Teacher availability
        # -----------------------------------------------------

        availability_key = (
            teacher_id,
            day,
            period,
        )

        # If availability exists for this teacher/slot,
        # it must be available.
        if availability_key in availability_map:

            if not availability_map[availability_key]:
                errors.append(
                    f"Teacher {teacher_id} is unavailable "
                    f"on {day}, period {period}."
                )

        # -----------------------------------------------------
        # 6. Room availability
        # -----------------------------------------------------

        if not room.get("is_available", False):
            errors.append(
                f"Room {room_id} is unavailable."
            )

        # -----------------------------------------------------
        # 7. Room capacity
        # -----------------------------------------------------

        room_capacity = room.get("capacity", 0)
        student_count = subject.get("num_students", 0)

        if room_capacity < student_count:
            errors.append(
                f"Room {room_id} is too small for "
                f"subject {subject_id}. "
                f"Capacity: {room_capacity}, "
                f"Students: {student_count}."
            )

        # -----------------------------------------------------
        # 8. Subject weekly hours
        # -----------------------------------------------------

        subject_hours[subject_id] = (
            subject_hours.get(subject_id, 0) + 1
        )

        # -----------------------------------------------------
        # 9. Teacher daily workload
        # -----------------------------------------------------

        daily_key = (
            teacher_id,
            day,
        )

        teacher_daily_hours[daily_key] = (
            teacher_daily_hours.get(daily_key, 0) + 1
        )

        max_daily = teacher.get(
            "max_hours_per_day",
            999999,
        )

        if teacher_daily_hours[daily_key] > max_daily:
            errors.append(
                f"Teacher {teacher_id} exceeds daily "
                f"teaching limit on {day}. "
                f"Limit: {max_daily}."
            )

        # -----------------------------------------------------
        # 10. Teacher weekly workload
        # -----------------------------------------------------

        teacher_weekly_hours[teacher_id] = (
            teacher_weekly_hours.get(teacher_id, 0) + 1
        )

        max_weekly = teacher.get(
            "max_hours_per_week",
            999999,
        )

        if teacher_weekly_hours[teacher_id] > max_weekly:
            errors.append(
                f"Teacher {teacher_id} exceeds weekly "
                f"teaching limit. "
                f"Limit: {max_weekly}."
            )

    # =========================================================
    # Validate required subject hours
    # =========================================================

    for subject_id, subject in subject_map.items():

        required_hours = subject.get(
            "hours_per_week",
            0,
        )

        actual_hours = subject_hours.get(
            subject_id,
            0,
        )

        if actual_hours != required_hours:

            errors.append(
                f"Subject {subject_id} requires "
                f"{required_hours} hours/week but has "
                f"{actual_hours} scheduled."
            )

    # =========================================================
    # Remove duplicate errors
    # =========================================================

    errors = list(dict.fromkeys(errors))

    # =========================================================
    # Limit error output
    # =========================================================

    # Prevent hundreds of repeated messages from flooding
    # the Flask page.
    if len(errors) > 50:
        errors = errors[:50] + [
            f"... and {len(errors) - 50} more validation errors."
        ]

    return len(errors) == 0, errors