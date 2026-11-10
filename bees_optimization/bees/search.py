"""Shared minimization loop for TSP and continuous Bees Algorithm searches.

AI-assisted extraction from the group's TSP implementation; see docs/ai_usage.md.
"""
import random


def select_sites(population, n_selected, n_elite):
    if (type(n_elite) is not int or type(n_selected) is not int
            or not 0 <= n_elite <= n_selected <= len(population)):
        raise ValueError("Invalid site selection settings")

    # Population contains (solution, objective value) pairs
    ranked = sorted(
        population,
        key=lambda candidate: candidate[1]
    )

    elite_sites = ranked[:n_elite]

    other_sites = ranked[n_elite:n_selected]

    return elite_sites, other_sites


def recruit_neighbors(
    site,
    n_recruits,
    objective,
    move,
    rng
):
    if type(n_recruits) is not int or n_recruits < 0:
        raise ValueError("Recruitment count must be a nonnegative integer")

    # Keep the original site unchanged
    best_solution, best_value = site
    best_solution = best_solution.copy()
    original_solution = best_solution.copy()

    evaluations = 0

    local_history = []

    for _ in range(n_recruits):
        # Generate a neighbor from the ORIGINAL site
        neighbor = move(original_solution, rng)

        neighbor_value = objective(neighbor)

        evaluations += 1

        # Update the best solution if the neighbor is better
        if neighbor_value < best_value:
            best_solution = neighbor
            best_value = neighbor_value

        local_history.append(best_value)

    return (best_solution, best_value), evaluations, local_history


def validate_settings(n_scouts, n_selected, n_elite, n_elite_recruits,
                      n_other_recruits, max_evaluations):
    """Reject invalid counts before any objective evaluations or random draws."""
    counts = (n_scouts, n_selected, n_elite, n_elite_recruits,
              n_other_recruits, max_evaluations)
    if any(type(value) is not int for value in counts):
        raise ValueError("BA counts and evaluation budget must be integers")
    if n_elite_recruits < 0 or n_other_recruits < 0:
        raise ValueError("Recruitment counts cannot be negative")
    if not 0 <= n_elite <= n_selected <= n_scouts:
        raise ValueError("Invalid site selection settings")

    if n_scouts < 1 or max_evaluations < n_scouts:
        raise ValueError("Invalid scouts or evaluation budget")


    # Elite and other selected sites must receive recruits
    if n_elite > 0 and n_elite_recruits < 1:
        raise ValueError("Elite sites require recruitment")

    if n_selected > n_elite and n_other_recruits < 1:
        raise ValueError("Other selected sites require recruitment")

    # Calculate how many new solutions each iteration evaluates
    fresh_scouts = n_scouts - n_selected

    total_recruits = (
        n_elite * n_elite_recruits
        + (n_selected - n_elite) * n_other_recruits
    )

    # Prevent an infinite loop with no new evaluations
    if total_recruits + fresh_scouts == 0:
        raise ValueError("Algorithm cannot make progress")


def run_bees(
    objective,
    make_scout,
    move,
    seed,
    n_scouts=30,
    n_selected=10,
    n_elite=3,
    n_elite_recruits=10,
    n_other_recruits=5,
    max_evaluations=30000
):
    """Minimize with fixed-site recruitment, fresh scouts, and an exact budget."""
    validate_settings(n_scouts, n_selected, n_elite, n_elite_recruits,
                      n_other_recruits, max_evaluations)

    rng = random.Random(seed)


    # 1. Initialize and evaluate scout population
    solutions = [make_scout(rng) for _ in range(n_scouts)]

    population = [
        (solution, objective(solution))
        for solution in solutions
    ]

    evaluations = len(population)

    # 2. Record the best initial solution
    best_solution, best_value = min(
        population, key=lambda candidate: candidate[1]
    )

    best_solution = best_solution.copy()
    initial_best = best_value

    history = [(evaluations, best_value)]

    # 3. Main optimization loop
    while evaluations < max_evaluations:
        elite_sites, other_sites = select_sites(
            population, n_selected, n_elite
        )

        new_population = []

        # 4. Recruit around elite and other selected sites
        for sites, recruits in [
            (elite_sites, n_elite_recruits),
            (other_sites, n_other_recruits)
        ]:

            for site in sites:
                remaining = max_evaluations - evaluations

                if remaining == 0:
                    break

                # Save global best before recruitment
                previous_global_best = best_value

                winner, used, local_history = recruit_neighbors(
                    site,
                    min(recruits, remaining),
                    objective,
                    move,
                    rng
                )

                evaluations += used
                new_population.append(winner)

                # Record global best after every evaluation
                for step, local_best in enumerate(
                    local_history, start=1
                ):
                    global_best_at_step = min(
                        previous_global_best,
                        local_best
                    )

                    evaluation_number = evaluations - used + step

                    history.append(
                        (evaluation_number, global_best_at_step)
                    )

                # Update global best solution
                if winner[1] < best_value:
                    best_solution = winner[0].copy()
                    best_value = winner[1]


            if evaluations >= max_evaluations:
                break

        # 5. Generate fresh scouts
        while (
            len(new_population) < n_scouts
            and evaluations < max_evaluations
        ):
            solution = make_scout(rng)
            value = objective(solution)

            evaluations += 1
            new_population.append((solution, value))

            if value < best_value:
                best_solution = solution.copy()
                best_value = value

            history.append((evaluations, best_value))

        # Stop if the budget was exhausted
        if evaluations >= max_evaluations:
            break

        # Update the population for the next iteration
        population = new_population

    return {
        "best_solution": best_solution,
        "best_value": best_value,
        "initial_best": initial_best,
        "evaluations": evaluations,
        "history": history
    }
