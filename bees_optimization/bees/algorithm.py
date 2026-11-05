import random

from .initialization import initialize_scouts
from .neighborhoods import swap_neighbor, reverse_neighbor
from .tsplib import calculate_tour_length

def select_sites(population, n_selected, n_elite):
    if not 0 <= n_elite <= n_selected <= len(population):
        raise ValueError("Invalid site selection settings")

    # Population contains (tour, tour_length) pairs
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
    distance_matrix,
    neighborhood,
    rng
):
    if n_recruits < 0:
        raise ValueError("Recruitment count cannot be negative")

    if neighborhood == "swap":
        move = swap_neighbor
    elif neighborhood == "reverse":
        move = reverse_neighbor
    else:
        raise ValueError("Unknown neighborhood operator")

    # Keep the original site unchanged
    best_tour, best_length = site
    best_tour = best_tour.copy()
    best_tour_original = best_tour.copy()

    evaluations = 0

    local_history = []

    for _ in range(n_recruits):
        # Generate a neighbor from the ORIGINAL site
        neighbor = move(best_tour_original, rng)

        neighbor_length = calculate_tour_length(
            neighbor, distance_matrix
        )

        evaluations += 1

        # Update the best solution if the neighbor is better
        if neighbor_length < best_length:
            best_tour = neighbor
            best_length = neighbor_length

        local_history.append(best_length)

    return (best_tour, best_length), evaluations, local_history


def bees_algorithm(
    distance_matrix,
    neighborhood,
    seed,
    n_scouts=30,
    n_selected=10,
    n_elite=3,
    n_elite_recruits=10,
    n_other_recruits=5,
    max_evaluations=30000
):
    if not 0 <= n_elite <= n_selected <= n_scouts:
        raise ValueError("Invalid site selection settings")

    if n_scouts < 1 or max_evaluations < n_scouts:
        raise ValueError("Invalid scouts or evaluation budget")

    
    if n_selected > 0 and (
        n_elite_recruits < 0 or n_other_recruits < 0
    ):
        raise ValueError("Recruitment counts cannot be negative")

    # Step 49: Additional parameter validation

    # Check that the neighborhood operator is valid
    if neighborhood not in ("swap", "reverse"):
        raise ValueError("Invalid neighborhood operator")

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

    rng = random.Random(seed)
    n = len(distance_matrix)


    # 1. Initialize and evaluate scout population
    tours = initialize_scouts(n, n_scouts, rng)

    population = [
        (tour, calculate_tour_length(tour, distance_matrix))
        for tour in tours
    ]

    evaluations = len(population)

    # 2. Record the best initial solution
    best_tour, best_length = min(
        population, key=lambda candidate: candidate[1]
    )

    best_tour = best_tour.copy()
    initial_best = best_length

    history = [(evaluations, best_length)]

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
                previous_global_best = best_length

                winner, used, local_history = recruit_neighbors(
                    site,
                    min(recruits, remaining),
                    distance_matrix,
                    neighborhood,
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
                if winner[1] < best_length:
                    best_tour = winner[0].copy()
                    best_length = winner[1]


            if evaluations >= max_evaluations:
                break

        # 5. Generate fresh scouts
        while (
            len(new_population) < n_scouts
            and evaluations < max_evaluations
        ):
            tour = initialize_scouts(n, 1, rng)[0]
            length = calculate_tour_length(tour, distance_matrix)

            evaluations += 1
            new_population.append((tour, length))

            if length < best_length:
                best_tour = tour.copy()
                best_length = length

            history.append((evaluations, best_length))

        # Stop if the budget was exhausted
        if evaluations >= max_evaluations:
            break

        # Update the population for the next iteration
        population = new_population

    return {
        "best_tour": best_tour,
        "best_length": best_length,
        "initial_best": initial_best,
        "evaluations": evaluations,
        "history": history
    }
