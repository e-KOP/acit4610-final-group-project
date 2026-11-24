"""(mu+lambda)-ES and (mu,lambda)-ES for long-only minimum-variance portfolios.

AI-generated with Claude (Anthropic), built step by step with and reviewed by
Jakob Andreas Amtedal; see docs/ai_usage.md.

Both variants share initialization, recombination, self-adaptation and mutation;
they differ only in survivor selection:
    plus  - best mu of parents and offspring combined
    comma - best mu of the offspring only
A separate archive (shared with the (1+1)-ES) keeps the best feasible allocation
ever evaluated. In comma selection the archive is for reporting only and never
enters parent selection.
"""
import math

import numpy as np

from .one_plus_one import SIGMA_MAX, SIGMA_MIN, Archive, repair

MU = 10          # parents
LAMBDA = 70      # offspring per full generation


class Individual:
    """Repaired weights, their variance, and their own step-size vector."""

    __slots__ = ("weights", "variance", "sigmas")

    def __init__(self, weights, variance, sigmas):
        self.weights = weights
        self.variance = variance
        self.sigmas = sigmas


def make_child(parents, returns, min_return, tau_prime, tau, rng):
    """Recombine two random parents, self-adapt the step sizes, mutate and repair.

    Returns the repaired child weights and its updated step sizes (not yet evaluated).
    """
    n = returns.size
    i, j = rng.choice(len(parents), size=2, replace=False)
    first, second = parents[i], parents[j]

    # Recombination: arithmetic mean of weights, geometric mean of step sizes
    weights = (first.weights + second.weights) / 2
    sigmas = np.sqrt(first.sigmas * second.sigmas)

    # Self-adaptation: one Z0 shared by all coordinates, one Zi per coordinate
    z0 = rng.standard_normal()
    sigmas = sigmas * np.exp(tau_prime * z0 + tau * rng.standard_normal(n))
    sigmas = np.clip(sigmas, SIGMA_MIN, SIGMA_MAX)

    # Mutation with fresh, independent normal draws, then repair
    child = repair(weights + sigmas * rng.standard_normal(n), returns, min_return)
    return child, sigmas


def select_survivors(parents, offspring, selection):
    """Return the MU candidates with the lowest variance.

    Python's sort is stable, so on equal variance parents (listed first) are
    kept before offspring, and earlier offspring before later ones.
    """
    if selection == "plus":
        pool = parents + offspring
    else:
        pool = offspring
    return sorted(pool, key=lambda ind: ind.variance)[:MU]


def solve_population(returns, covariance, min_return, seed, selection,
                     max_evaluations=30000):
    """Run one (mu+lambda)- or (mu,lambda)-ES; return the best feasible allocation."""
    if selection not in ("plus", "comma"):
        raise ValueError("selection must be 'plus' or 'comma'")
    returns = np.asarray(returns, dtype=float)
    covariance = np.asarray(covariance, dtype=float)
    n = returns.size
    if covariance.shape != (n, n):
        raise ValueError("covariance must be n x n for n returns")
    if type(max_evaluations) is not int or max_evaluations < 1:
        raise ValueError("max_evaluations must be a positive integer")

    rng = np.random.default_rng(seed)
    archive = Archive(returns, covariance, min_return, max_evaluations)
    tau_prime = 1 / math.sqrt(2 * n)
    tau = 1 / math.sqrt(2 * math.sqrt(n))
    population_best = []    # [evaluation, best variance in the parent population]

    # Initialization: MU parents as in (1+1)-ES, all step sizes 0.1/sqrt(n)
    parents = []
    for _ in range(MU):
        if archive.remaining() == 0:
            break
        weights = repair(rng.uniform(0.0, 1.0, n), returns, min_return)
        sigmas = np.full(n, 0.1 / math.sqrt(n))
        parents.append(Individual(weights, archive.evaluate(weights), sigmas))
    initial_best = archive.best_variance if archive.best_weights is not None else None
    population_best.append([archive.evaluations, min(p.variance for p in parents)])

    while archive.remaining() > 0:
        # One generation: LAMBDA offspring, fewer if the budget runs out
        offspring = []
        for _ in range(min(LAMBDA, archive.remaining())):
            child, sigmas = make_child(parents, returns, min_return, tau_prime, tau, rng)
            offspring.append(Individual(child, archive.evaluate(child), sigmas))

        if len(offspring) < LAMBDA:
            break                       # partial last batch: archive updated, budget used
        parents = select_survivors(parents, offspring, selection)
        population_best.append([archive.evaluations, parents[0].variance])

    result = archive.result(initial_best)
    result["population_best"] = population_best
    return result