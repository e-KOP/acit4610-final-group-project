"""Unshifted benchmark objectives and assignment bounds.

AI-generated implementation of the mathematical definitions; see docs/ai_usage.md.
References: https://www.sfu.ca/~ssurjano/optimization.html
"""
from dataclasses import dataclass
import math
from typing import Callable


def _validate_vector(x, minimum_dimension=1):
    if len(x) < minimum_dimension or any(not math.isfinite(v) for v in x):
        raise ValueError("Expected a finite vector of sufficient dimension")


def sphere(x):
    """Sum of squared coordinates; minimum zero at the origin."""
    _validate_vector(x)
    return sum(v * v for v in x)


def rosenbrock(x):
    """Adjacent-coordinate Rosenbrock chain; minimum zero at all ones."""
    _validate_vector(x, minimum_dimension=2)
    return sum(100 * (b - a * a) ** 2 + (1 - a) ** 2
               for a, b in zip(x, x[1:]))


def rastrigin(x):
    """Rastrigin with amplitude 10; minimum zero at the origin."""
    _validate_vector(x)
    return 10 * len(x) + sum(v * v - 10 * math.cos(2 * math.pi * v)
                             for v in x)


def ackley(x):
    """Ackley with a=20, b=0.2, c=2*pi; minimum zero at the origin."""
    _validate_vector(x)
    mean_square = sum(v * v for v in x) / len(x)
    mean_cosine = sum(math.cos(2 * math.pi * v) for v in x) / len(x)
    return (-20 * math.exp(-0.2 * math.sqrt(mean_square))
            - math.exp(mean_cosine) + 20 + math.e)


@dataclass(frozen=True)
class Benchmark:
    objective: Callable
    bounds: tuple[float, float]


BENCHMARKS = {
    "sphere": Benchmark(sphere, (-5.12, 5.12)),
    "rosenbrock": Benchmark(rosenbrock, (-5.0, 10.0)),
    "rastrigin": Benchmark(rastrigin, (-5.12, 5.12)),
    "ackley": Benchmark(ackley, (-32.768, 32.768)),
}
