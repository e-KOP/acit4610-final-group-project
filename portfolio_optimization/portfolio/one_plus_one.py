"""(1+1)-ES for long-only minimum-variance portfolios.

AI-generated with Claude (Anthropic), built step by step with and reviewed by
Jakob Andreas Amtedal; see docs/ai_usage.md.

One parent, one mutated child per trial. The child replaces the parent only if
its variance is strictly lower. The scalar step size follows the 1/5th success
rule. A separate archive keeps the best feasible allocation ever evaluated.

Every candidate is repaired with the shared repair_weights() and archived only
if the shared is_feasible() accepts it. During the search, variance is computed
with NumPy for speed; the experiment runner recomputes the reported variance
independently with evaluation.portfolio_variance().
"""
import math

import numpy as np

from .feasibility import is_feasible
from .repair import repair_weights

SIGMA_MIN, SIGMA_MAX = 1e-8, 1.0
SUCCESS_FACTOR = math.exp(1 / 3)       # strict improvement
FAILURE_FACTOR = math.exp(-1 / 12)     # otherwise


class Archive:
    """Counts evaluations and keeps the best feasible allocation seen so far."""

    def __init__(self, returns, covariance, min_return, max_evaluations):
        self.returns = returns
        self.covariance = covariance
        self.min_return = min_return
        self.max_evaluations = max_evaluations
        self.evaluations = 0
        self.best_weights = None
        self.best_variance = math.inf
        self.history = []              # [evaluation, archive best variance]

    def remaining(self):
        return self.max_evaluations - self.evaluations

    def evaluate(self, weights):
        """One objective evaluation: variance w^T Sigma w of a repaired allocation."""
        if self.evaluations >= self.max_evaluations:
            raise RuntimeError("evaluation budget exceeded")
        variance = float(weights @ self.covariance @ weights)
        self.evaluations += 1
        if (variance < self.best_variance
                and is_feasible(weights, self.returns, self.min_return)):
            self.best_variance = variance
            self.best_weights = weights.copy()
        if self.best_weights is not None:
            self.history.append([self.evaluations, self.best_variance])
        return variance

    def result(self, initial_best):
        feasible = self.best_weights is not None
        return {
            "best_weights": self.best_weights.tolist() if feasible else None,
            "best_variance": self.best_variance if feasible else None,
            "best_return": float(self.returns @ self.best_weights) if feasible else None,
            "feasible": feasible,
            "evaluations": self.evaluations,
            "initial_best": initial_best,
            "history": self.history,
        }

def update_step_size(sigma, success):
    """1/5th success rule for one trial, then clamp to [1e-8, 1.0]."""
    sigma *= SUCCESS_FACTOR if success else FAILURE_FACTOR
    return min(max(sigma, SIGMA_MIN), SIGMA_MAX)


def repair(z, returns, min_return):
    """Shared repair (simplex projection + return repair), as a NumPy array."""
    return np.asarray(repair_weights(z, returns, min_return), dtype=float)


def solve_one_plus_one(returns, covariance, min_return, seed, max_evaluations=30000):
    """Run one (1+1)-ES and return the best feasible allocation found."""
    returns = np.asarray(returns, dtype=float)
    covariance = np.asarray(covariance, dtype=float)
    n = returns.size
    if covariance.shape != (n, n):
        raise ValueError("covariance must be n x n for n returns")
    if type(max_evaluations) is not int or max_evaluations < 1:
        raise ValueError("max_evaluations must be a positive integer")

    rng = np.random.default_rng(seed)
    archive = Archive(returns, covariance, min_return, max_evaluations)

    # Initialization: independent uniform [0, 1] weights, then repair
    parent = repair(rng.uniform(0.0, 1.0, n), returns, min_return)
    parent_variance = archive.evaluate(parent)
    initial_best = archive.best_variance if archive.best_weights is not None else None
    sigma = 0.1 / math.sqrt(n)

    while archive.remaining() > 0:
        # Mutation: sigma times an independent N(0, 1) per weight, then repair
        child = repair(parent + sigma * rng.standard_normal(n), returns, min_return)
        child_variance = archive.evaluate(child)

        # Selection (strict) and 1/5th success rule, updated after every trial
        success = child_variance < parent_variance
        if success:
            parent, parent_variance = child, child_variance
        sigma = update_step_size(sigma, success)

    return archive.result(initial_best)

    