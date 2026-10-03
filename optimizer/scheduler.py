from optimizer.constraints import (
    is_teacher_available,
    is_teacher_at_daily_limit,
    is_teacher_at_weekly_limit,
)

from optimizer.conflict_checker import (
    has_class_conflict,
    has_teacher_conflict,
    has_room_conflict,
)


DAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
]


def can_assign(
    subject,
    teacher,
    room,
    day,
    period,
    schedule,
    availability,
):
    """
    Check all hard constraints before assigning a subject.
    """

    # Teacher availability
    if not is_teacher_available(
        teacher["id"],
        day,
        period,
        availability,
    ):
        return False

    # Class conflict
    if has_class_conflict(
        subject["class_id"],
        day,
        period,
        schedule,
    ):
        return False

    # Teacher conflict
    if has_teacher_conflict(
        teacher["id"],
        day,
        period,
        schedule,
    ):
        return False

    # Room conflict
    if has_room_conflict(
        room["id"],
        day,
        period,
        schedule,
    ):
        return False

    # Daily teacher limit
    if is_teacher_at_daily_limit(
        teacher["id"],
        day,
        schedule,
        teacher["max_hours_per_day"],
    ):
        return False

    # Weekly teacher limit
    if is_teacher_at_weekly_limit(
        teacher["id"],
        schedule,
        teacher["max_hours_per_week"],
    ):
        return False

    # Room capacity
    if room["capacity"] < subject["num_students"]:
        return False

    return True


def room_usage_count(room_id, schedule):
    """
    Count how many classes are currently assigned
    to a particular room.
    """

    return sum(
        1
        for item in schedule
        if item["room_id"] == room_id
    )


def room_day_usage_count(room_id, day, schedule):
    """
    Count how many classes a room has on a particular day.
    """

    return sum(
        1
        for item in schedule
        if item["room_id"] == room_id
        and item["day"] == day
    )


def get_best_room(
    subject,
    rooms,
    day,
    period,
    schedule,
    teacher,
    availability,
):
    """
    Select the most suitable room.

    Priority:
    1. Room must be available.
    2. Room must have sufficient capacity.
    3. Room must not have a conflict.
    4. Prefer the least-used room.
    5. Prefer the smallest room that can fit the class.
    """

    suitable_rooms = []

    for room in rooms:

        if not room["is_available"]:
            continue

        if room["capacity"] < subject["num_students"]:
            continue

        if not can_assign(
            subject,
            teacher,
            room,
            day,
            period,
            schedule,
            availability,
        ):
            continue

        total_usage = room_usage_count(
            room["id"],
            schedule,
        )

        daily_usage = room_day_usage_count(
            room["id"],
            day,
            schedule,
        )

        # Extra capacity means unused space.
        extra_capacity = (
            room["capacity"]
            - subject["num_students"]
        )

        suitable_rooms.append(
            (
                total_usage,
                daily_usage,
                extra_capacity,
                room["id"],
                room,
            )
        )

    if not suitable_rooms:
        return None

    # Lower values are better.
    suitable_rooms.sort(
        key=lambda item: (
            item[0],  # Overall room usage
            item[1],  # Daily room usage
            item[2],  # Wasted capacity
            item[3],  # Stable room ordering
        )
    )

    return suitable_rooms[0][4]


def generate_timetable(
    subjects,
    teachers,
    rooms,
    periods,
    availability,
):
    """
    Generate a timetable using greedy constraint-based
    scheduling with balanced room allocation.
    """

    schedule = []

    # Schedule subjects with higher weekly requirements first.
    subjects = sorted(
        subjects,
        key=lambda subject: (
            -subject["hours_per_week"],
            -subject["num_students"],
        ),
    )

    for subject in subjects:

        teacher = next(
            (
                t
                for t in teachers
                if t["id"] == subject["teacher_id"]
            ),
            None,
        )

        if teacher is None:
            continue

        assigned_hours = 0

        for day in DAYS:

            if assigned_hours >= subject["hours_per_week"]:
                break

            for period in periods:

                if assigned_hours >= subject["hours_per_week"]:
                    break

                period_number = period["period"]

                room = get_best_room(
                    subject=subject,
                    rooms=rooms,
                    day=day,
                    period=period_number,
                    schedule=schedule,
                    teacher=teacher,
                    availability=availability,
                )

                if room is None:
                    continue

                schedule.append(
                    {
                        "day": day,
                        "period": period_number,
                        "class_id": subject["class_id"],
                        "subject_id": subject["id"],
                        "teacher_id": teacher["id"],
                        "room_id": room["id"],
                    }
                )

                assigned_hours += 1

    return schedule