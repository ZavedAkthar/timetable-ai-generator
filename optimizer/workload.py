def get_teacher_workload(teacher_id, schedule):
    """
    Return the number of classes assigned to a teacher.
    """

    return sum(
        1
        for item in schedule
        if item["teacher_id"] == teacher_id
    )


def get_daily_workload(teacher_id, day, schedule):
    """
    Return the number of classes assigned to a teacher
    on a particular day.
    """

    return sum(
        1
        for item in schedule
        if item["teacher_id"] == teacher_id
        and item["day"] == day
    )


def workload_penalty(schedule):
    """
    Calculate a simple penalty for uneven teacher workload.

    Lower penalty = better balance.
    """

    workloads = {}

    for item in schedule:
        teacher_id = item["teacher_id"]

        workloads[teacher_id] = workloads.get(teacher_id, 0) + 1

    if not workloads:
        return 0

    average = sum(workloads.values()) / len(workloads)

    penalty = 0

    for workload in workloads.values():
        penalty += abs(workload - average)

    return penalty