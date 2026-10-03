import random
from copy import deepcopy

from optimizer.workload import workload_penalty


DAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
]


# =========================================================
# HARD CONFLICTS
# =========================================================

def count_hard_conflicts(schedule):
    """
    Count class, teacher and room conflicts.

    Lower is better.
    """

    conflicts = 0

    class_slots = set()
    teacher_slots = set()
    room_slots = set()

    for item in schedule:

        class_key = (
            item["day"],
            item["period"],
            item["class_id"],
        )

        teacher_key = (
            item["day"],
            item["period"],
            item["teacher_id"],
        )

        room_key = (
            item["day"],
            item["period"],
            item["room_id"],
        )

        if class_key in class_slots:
            conflicts += 100

        if teacher_key in teacher_slots:
            conflicts += 100

        if room_key in room_slots:
            conflicts += 100

        class_slots.add(class_key)
        teacher_slots.add(teacher_key)
        room_slots.add(room_key)

    return conflicts


# =========================================================
# TEACHER CONSECUTIVE CLASSES
# =========================================================

def count_consecutive_classes(schedule):
    """
    Penalize consecutive classes for the same teacher.

    Lower is better.
    """

    penalty = 0

    teacher_schedule = {}

    for item in schedule:

        teacher_id = item["teacher_id"]

        teacher_schedule.setdefault(
            teacher_id,
            {}
        )

        teacher_schedule[teacher_id].setdefault(
            item["day"],
            []
        )

        teacher_schedule[teacher_id][item["day"]].append(
            item["period"]
        )

    for days in teacher_schedule.values():

        for periods in days.values():

            periods = sorted(periods)

            for i in range(1, len(periods)):

                if periods[i] == periods[i - 1] + 1:

                    penalty += 5

    return penalty


# =========================================================
# CLASS CONSECUTIVE CLASSES
# =========================================================

def count_class_consecutive(schedule):
    """
    Penalize consecutive classes for the same class.

    Lower is better.
    """

    penalty = 0

    class_schedule = {}

    for item in schedule:

        class_id = item["class_id"]

        class_schedule.setdefault(
            class_id,
            {}
        )

        class_schedule[class_id].setdefault(
            item["day"],
            []
        )

        class_schedule[class_id][item["day"]].append(
            item["period"]
        )

    for days in class_schedule.values():

        for periods in days.values():

            periods = sorted(periods)

            for i in range(1, len(periods)):

                if periods[i] == periods[i - 1] + 1:

                    penalty += 3

    return penalty


# =========================================================
# FITNESS FUNCTION
# =========================================================

def calculate_fitness(schedule):
    """
    Calculate timetable fitness.

    Lower score = better timetable.

    Priority:

    1. Hard conflicts
    2. Teacher consecutive classes
    3. Class consecutive classes
    4. Teacher workload balance
    """

    # -----------------------------------------------------
    # 1. HARD CONFLICTS
    # -----------------------------------------------------

    hard_conflicts = count_hard_conflicts(
        schedule
    )

    # -----------------------------------------------------
    # 2. TEACHER CONSECUTIVE CLASSES
    # -----------------------------------------------------

    teacher_consecutive = (
        count_consecutive_classes(
            schedule
        )
    )

    # -----------------------------------------------------
    # 3. CLASS CONSECUTIVE CLASSES
    # -----------------------------------------------------

    class_consecutive = (
        count_class_consecutive(
            schedule
        )
    )

    # -----------------------------------------------------
    # 4. TEACHER WORKLOAD BALANCE
    # -----------------------------------------------------

    workload = workload_penalty(
        schedule
    )

    # -----------------------------------------------------
    # WEIGHTED FITNESS
    # -----------------------------------------------------

    fitness = (
        hard_conflicts
        + (teacher_consecutive * 2)
        + (class_consecutive * 2)
        + (workload * 3)
    )

    return fitness


# =========================================================
# SLOT SAFETY CHECK
# =========================================================

def slot_is_safe(
    item,
    day,
    period,
    schedule,
    ignore_index=None,
):
    """
    Check whether assigning an item to a day/period
    creates a hard conflict.

    Checks:

    - Class conflict
    - Teacher conflict
    - Room conflict
    """

    class_id = item["class_id"]
    teacher_id = item["teacher_id"]
    room_id = item["room_id"]

    for index, other in enumerate(schedule):

        if (
            ignore_index is not None
            and index == ignore_index
        ):
            continue

        if other["day"] != day:
            continue

        if other["period"] != period:
            continue

        # Same class
        if other["class_id"] == class_id:
            return False

        # Same teacher
        if other["teacher_id"] == teacher_id:
            return False

        # Same room
        if other["room_id"] == room_id:
            return False

    return True


# =========================================================
# FIND SAFE SLOT
# =========================================================

def find_safe_slot(
    item,
    schedule,
    periods,
    ignore_index=None,
):
    """
    Find a random valid day/period for an assignment.
    """

    period_numbers = [
        p["period"]
        for p in periods
    ]

    candidates = []

    for day in DAYS:

        for period in period_numbers:

            if slot_is_safe(
                item=item,
                day=day,
                period=period,
                schedule=schedule,
                ignore_index=ignore_index,
            ):

                candidates.append(
                    (
                        day,
                        period
                    )
                )

    if not candidates:
        return None

    return random.choice(
        candidates
    )


# =========================================================
# REPAIR SCHEDULE
# =========================================================

def repair_schedule(
    schedule,
    periods,
):
    """
    Repair hard conflicts created by genetic operations.

    Prevents duplicate:

    - class/day/period
    - teacher/day/period
    - room/day/period
    """

    repaired = []

    items = list(schedule)

    random.shuffle(items)

    for item in items:

        candidate = deepcopy(
            item
        )

        # -------------------------------------------------
        # Keep original slot if valid
        # -------------------------------------------------

        if slot_is_safe(
            item=candidate,
            day=candidate["day"],
            period=candidate["period"],
            schedule=repaired,
        ):

            repaired.append(
                candidate
            )

            continue

        # -------------------------------------------------
        # Find another valid slot
        # -------------------------------------------------

        safe_slot = find_safe_slot(
            item=candidate,
            schedule=repaired,
            periods=periods,
        )

        if safe_slot is not None:

            candidate["day"] = safe_slot[0]
            candidate["period"] = safe_slot[1]

            repaired.append(
                candidate
            )

        else:

            # Keep the item if there is no free slot.
            # The validator will catch the problem later.
            repaired.append(
                candidate
            )

    return repaired


# =========================================================
# MUTATION
# =========================================================

def mutate(
    schedule,
    periods,
):
    """
    Safely move one timetable assignment.
    """

    child = deepcopy(
        schedule
    )

    if len(child) < 1:
        return child

    index = random.randrange(
        len(child)
    )

    item = child[index]

    # Temporarily remove the selected item.
    remaining = (
        child[:index]
        + child[index + 1:]
    )

    safe_slot = find_safe_slot(
        item=item,
        schedule=remaining,
        periods=periods,
    )

    if safe_slot is not None:

        item["day"] = safe_slot[0]
        item["period"] = safe_slot[1]

    child = (
        remaining[:index]
        + [item]
        + remaining[index:]
    )

    return child


# =========================================================
# CROSSOVER
# =========================================================

def crossover(
    parent1,
    parent2,
    periods,
):
    """
    Create a child while respecting hard constraints.
    """

    if not parent1:
        return []

    child = []

    # -----------------------------------------------------
    # Start with parent 1
    # -----------------------------------------------------

    for item in parent1:

        candidate = deepcopy(
            item
        )

        if slot_is_safe(
            item=candidate,
            day=candidate["day"],
            period=candidate["period"],
            schedule=child,
        ):

            child.append(
                candidate
            )

        else:

            safe_slot = find_safe_slot(
                item=candidate,
                schedule=child,
                periods=periods,
            )

            if safe_slot is not None:

                candidate["day"] = (
                    safe_slot[0]
                )

                candidate["period"] = (
                    safe_slot[1]
                )

            child.append(
                candidate
            )

    # -----------------------------------------------------
    # Inherit some slots from parent 2
    # -----------------------------------------------------

    if parent2:

        for index in range(
            min(
                len(child),
                len(parent2),
            )
        ):

            if random.random() > 0.25:
                continue

            candidate = deepcopy(
                child[index]
            )

            parent2_item = parent2[index]

            remaining = (
                child[:index]
                + child[index + 1:]
            )

            if slot_is_safe(
                item=candidate,
                day=parent2_item["day"],
                period=parent2_item["period"],
                schedule=remaining,
            ):

                candidate["day"] = (
                    parent2_item["day"]
                )

                candidate["period"] = (
                    parent2_item["period"]
                )

                child[index] = candidate

    # -----------------------------------------------------
    # Final repair
    # -----------------------------------------------------

    child = repair_schedule(
        child,
        periods,
    )

    return child


# =========================================================
# OPTIMIZER
# =========================================================

def optimize_timetable(
    initial_schedule,
    periods,
    population_size=30,
    generations=50,
    mutation_rate=0.20,
):
    """
    Optimize timetable using a Genetic Algorithm.

    Hard constraints are repaired after crossover
    and mutation.
    """

    if not initial_schedule:
        return []

    # -----------------------------------------------------
    # Clean initial schedule
    # -----------------------------------------------------

    initial_schedule = repair_schedule(
        deepcopy(initial_schedule),
        periods,
    )

    # -----------------------------------------------------
    # Create population
    # -----------------------------------------------------

    population = []

    for _ in range(
        population_size
    ):

        candidate = deepcopy(
            initial_schedule
        )

        # Add diversity
        if random.random() < 0.70:

            candidate = mutate(
                candidate,
                periods,
            )

        candidate = repair_schedule(
            candidate,
            periods,
        )

        population.append(
            candidate
        )

    # -----------------------------------------------------
    # Initial best
    # -----------------------------------------------------

    best_schedule = deepcopy(
        initial_schedule
    )

    best_score = calculate_fitness(
        best_schedule
    )

    print(
        f"Optimizer starting fitness: "
        f"{best_score}"
    )

    # -----------------------------------------------------
    # Genetic algorithm
    # -----------------------------------------------------

    for generation in range(
        generations
    ):

        # Rank population
        population.sort(
            key=calculate_fitness
        )

        current_best = population[0]

        current_score = calculate_fitness(
            current_best
        )

        # -------------------------------------------------
        # Update global best
        # -------------------------------------------------

        if current_score < best_score:

            best_schedule = deepcopy(
                current_best
            )

            best_score = current_score

        # -------------------------------------------------
        # Elite selection
        # -------------------------------------------------

        elite_count = max(
            2,
            population_size // 5,
        )

        elite = population[
            :elite_count
        ]

        # -------------------------------------------------
        # Preserve elite solutions
        # -------------------------------------------------

        new_population = [
            deepcopy(item)
            for item in elite
        ]

        # -------------------------------------------------
        # Generate children
        # -------------------------------------------------

        while len(
            new_population
        ) < population_size:

            parent1 = random.choice(
                elite
            )

            parent2 = random.choice(
                elite
            )

            child = crossover(
                parent1,
                parent2,
                periods,
            )

            # Mutation
            if (
                random.random()
                < mutation_rate
            ):

                child = mutate(
                    child,
                    periods,
                )

            # Final repair
            child = repair_schedule(
                child,
                periods,
            )

            new_population.append(
                child
            )

        population = new_population

        # -------------------------------------------------
        # Progress output
        # -------------------------------------------------

        if (
            generation == 0
            or (generation + 1) % 10 == 0
            or generation == generations - 1
        ):

            print(
                f"Generation "
                f"{generation + 1}/"
                f"{generations} | "
                f"Best fitness: "
                f"{best_score}"
            )

    # -----------------------------------------------------
    # Final repair
    # -----------------------------------------------------

    best_schedule = repair_schedule(
        best_schedule,
        periods,
    )

    final_score = calculate_fitness(
        best_schedule
    )

    print(
        f"Optimizer final fitness: "
        f"{final_score}"
    )

    return best_schedule
