
"""Portfolio evaluation functions.

AI-assisted implementation. See docs/ai_usage.md.

All returns are expressed in decimal form.
The objective is portfolio variance, not standard deviation.
"""

import math


def _check_vector(values, name):
    """Require a nonempty vector containing finite numbers."""
    if len(values) == 0:
        raise ValueError(f"{name} must not be empty")

    if any(not math.isfinite(value) for value in values):
        raise ValueError(f"{name} contains a non-finite value")


def expected_return(weights, returns) -> float:
    """Calculate r^T w without imposing portfolio constraints."""
    if len(weights) != len(returns):
        raise ValueError("Weights and returns must have equal lengths")

    _check_vector(weights, "Weights")
    _check_vector(returns, "Returns")

    return math.fsum(
        weight * mean_return
        for weight, mean_return in zip(weights, returns)
    )


def portfolio_variance(weights, covariance) -> float:
    """Calculate w^T Sigma w for a dense covariance matrix."""
    _check_vector(weights, "Weights")

    n = len(weights)

    if len(covariance) != n:
        raise ValueError("Covariance matrix has incorrect dimensions")

    for row in covariance:
        if len(row) != n:
            raise ValueError("Covariance matrix must be square")

    variance = math.fsum(
        weights[i] * math.fsum(
            covariance[i][j] * weights[j]
            for j in range(n)
        )
        for i in range(n)
    )

    if not math.isfinite(variance):
        raise ValueError("Calculated variance is not finite")

    return variance


def minimum_return_target(returns, alpha: float) -> float:
    """Interpolate between equal-weight return and maximum asset return.

    R_min(alpha) = (1-alpha)*R_eq + alpha*R_max
    """
    _check_vector(returns, "Returns")

    if not math.isfinite(alpha) or not 0.0 <= alpha <= 1.0:
        raise ValueError("Alpha must be finite and between 0 and 1")

    equal_return = math.fsum(returns) / len(returns)
    maximum_return = max(returns)

    return (
        (1.0 - alpha) * equal_return
        + alpha * maximum_return
    )
