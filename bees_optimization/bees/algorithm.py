"""TSP adapter for the shared Bees Algorithm search.

AI-assisted refactor and input validation; see docs/ai_usage.md.
"""
import math

from .initialization import random_tour
from .neighborhoods import swap_neighbor, reverse_neighbor
from .search import select_sites, run_bees
from .search import recruit_neighbors as recruit_solutions
from .tsplib import calculate_tour_length


def _neighborhood_move(neighborhood):
    if neighborhood == "swap":
        return swap_neighbor
    if neighborhood in ("reverse", "segment_reversal"):
        return reverse_neighbor
    raise ValueError("Unknown neighborhood operator")


def recruit_neighbors(site, n_recruits, distance_matrix, neighborhood, rng):
    """Retain the best of an original TSP site and its sampled neighbors."""
    return recruit_solutions(
        site, n_recruits,
        lambda tour: calculate_tour_length(tour, distance_matrix),
        _neighborhood_move(neighborhood), rng,
    )


def bees_algorithm(distance_matrix, neighborhood, seed, n_scouts=30,
                   n_selected=10, n_elite=3, n_elite_recruits=10,
                   n_other_recruits=5, max_evaluations=30000):
    """Search a TSP with fixed city 1; preserve the original result interface."""
    move = _neighborhood_move(neighborhood)
    n = len(distance_matrix)
    if n < 3 or any(len(row) != n for row in distance_matrix):
        raise ValueError("TSP search requires a square matrix of at least 3 cities")
    if any(not math.isfinite(value) or value < 0
           for row in distance_matrix for value in row):
        raise ValueError("Distances must be finite and nonnegative")
    result = run_bees(
        lambda tour: calculate_tour_length(tour, distance_matrix),
        lambda rng: random_tour(n, rng), move, seed,
        n_scouts, n_selected, n_elite, n_elite_recruits,
        n_other_recruits, max_evaluations,
    )
    result["best_tour"] = result.pop("best_solution")
    result["best_length"] = result.pop("best_value")
    return result
