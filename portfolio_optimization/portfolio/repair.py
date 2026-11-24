
"""Repair portfolio weights to satisfy allocation and return constraints.

AI-assisted implementation. See docs/ai_usage.md.
"""

import math


def _finite_vector(values, name):
    """Convert a nonempty numeric sequence to finite floats."""
    result = [float(value) for value in values]

    if not result:
        raise ValueError(f"{name} must not be empty")

    if not all(math.isfinite(value) for value in result):
        raise ValueError(f"{name} must contain only finite values")

    return result


def project_simplex(weights) -> list[float]:
    """Project weights onto the nonnegative unit simplex.

    Returns the Euclidean projection satisfying:
        w_i >= 0
        sum(w) = 1

    The input is not modified.
    """
    values = _finite_vector(weights, "Weights")

    ordered = sorted(values, reverse=True)

    cumulative = 0.0
    theta = None

    for k, value in enumerate(ordered, start=1):
        cumulative += value
        candidate = (cumulative - 1.0) / k

        if value > candidate:
            theta = candidate

    if theta is None:
        raise ValueError("Could not project weights onto simplex")

    projected = [max(value - theta, 0.0) for value in values]

    total = math.fsum(projected)

    if not math.isfinite(total) or total <= 0:
        raise ValueError("Invalid simplex projection")

    # Correct small floating-point summation differences.
    return [weight / total for weight in projected]


def repair_weights(
    weights,
    returns,
    min_return,
) -> list[float]:
    """Repair portfolio weights to satisfy all three constraints.

    1. Project onto the nonnegative unit simplex.
    2. If required return is unmet, mix with the highest-return asset.

    Returns a new list; does not modify the input.
    """
    values = _finite_vector(weights, "Weights")
    mean_returns = _finite_vector(returns, "Returns")

    if len(values) != len(mean_returns):
        raise ValueError("Weights and returns must have equal lengths")

    target = float(min_return)

    if not math.isfinite(target):
        raise ValueError("Minimum return must be finite")

    max_return = max(mean_returns)

    if target > max_return:
        raise ValueError(
            "Minimum return is unattainable under long-only constraints"
        )

    projected = project_simplex(values)

    current_return = math.fsum(
        weight * mean_return
        for weight, mean_return in zip(projected, mean_returns)
    )

    if current_return >= target:
        return projected

    best_asset = mean_returns.index(max_return)

    denominator = max_return - current_return

    if denominator <= 0:
        raise ValueError("Cannot satisfy the minimum return")

    beta = (target - current_return) / denominator
    beta = min(1.0, max(0.0, beta))

    repaired = [
        (1.0 - beta) * weight
        for weight in projected
    ]
    repaired[best_asset] += beta

    return repaired
