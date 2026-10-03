def has_class_conflict(class_id, day, period, schedule):
    for item in schedule:
        if (
            item["class_id"] == class_id
            and item["day"] == day
            and item["period"] == period
        ):
            return True

    return False


def has_teacher_conflict(teacher_id, day, period, schedule):
    for item in schedule:
        if (
            item["teacher_id"] == teacher_id
            and item["day"] == day
            and item["period"] == period
        ):
            return True

    return False


def has_room_conflict(room_id, day, period, schedule):
    for item in schedule:
        if (
            item["room_id"] == room_id
            and item["day"] == day
            and item["period"] == period
        ):
            return True

    return False