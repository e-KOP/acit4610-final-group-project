"""Continuous BA using uniform initialization and clipped uniform perturbation.

AI-generated implementation; see docs/ai_usage.md.
"""
from .functions import BENCHMARKS
from .search import run_bees


NEIGHBORHOOD_RANGE_FRACTION = 0.1


def random_vector(dimension, bounds, rng):
    """Draw each coordinate independently within the benchmark bounds."""
    lower, upper = bounds
    return [rng.uniform(lower, upper) for _ in range(dimension)]


def continuous_neighbor(vector, bounds, rng):
    """Perturb every coordinate by +/-10% of its range, then clip."""
    lower, upper = bounds
    radius = NEIGHBORHOOD_RANGE_FRACTION * (upper - lower)
    return [min(upper, max(lower, value + rng.uniform(-radius, radius)))
            for value in vector]


def continuous_bees(function_name, dimension, seed, n_scouts=30,
                    n_selected=10, n_elite=3, n_elite_recruits=10,
                    n_other_recruits=5, max_evaluations=30000):
    """Run one assignment benchmark at dimension 10 or 30.

    Return best_vector, best_value, initial_best, evaluations, and history.
    Initialization and every recruited/scout evaluation count toward the budget.
    History begins after initialization, matching the TSP interface.
    """
    if function_name not in BENCHMARKS:
        raise ValueError(f"Unknown benchmark: {function_name}")
    if type(dimension) is not int or dimension not in (10, 30):
        raise ValueError("Assignment dimensions must be 10 or 30")
    benchmark = BENCHMARKS[function_name]
    result = run_bees(
        benchmark.objective,
        lambda rng: random_vector(dimension, benchmark.bounds, rng),
        lambda vector, rng: continuous_neighbor(vector, benchmark.bounds, rng),
        seed, n_scouts, n_selected, n_elite, n_elite_recruits,
        n_other_recruits, max_evaluations,
    )
    result["best_vector"] = result.pop("best_solution")
    return result
