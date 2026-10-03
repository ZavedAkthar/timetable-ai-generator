def is_teacher_available(teacher_id, day, period, availability):
    """
    Check whether a teacher is available for a specific slot.
    """

    for item in availability:
        if (
            item["teacher_id"] == teacher_id
            and item["day"] == day
            and item["period"] == period
        ):
            return item["is_available"]

    # If no restriction is stored, assume available.
    return True


def is_teacher_at_daily_limit(teacher_id, day, schedule, max_hours):
    """
    Check whether assigning another class would exceed
    the teacher's daily limit.
    """

    current_hours = sum(
        1
        for item in schedule
        if item["teacher_id"] == teacher_id
        and item["day"] == day
    )

    return current_hours >= max_hours


def is_teacher_at_weekly_limit(teacher_id, schedule, max_hours):
    """
    Check whether assigning another class would exceed
    the teacher's weekly limit.
    """

    current_hours = sum(
        1
        for item in schedule
        if item["teacher_id"] == teacher_id
    )

    return current_hours >= max_hours