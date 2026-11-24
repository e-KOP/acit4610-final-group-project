
"""Independent portfolio feasibility checks.

AI-assisted implementation. See docs/ai_usage.md.
"""

import math


def is_feasible(
    weights,
    returns,
    min_return,
    tolerance=1e-8,
) -> bool:
    """Check all portfolio constraints independently.

    Requires:
        w_i >= -tolerance
        abs(sum(w) - 1) <= tolerance
        expected_return >= min_return - tolerance
    """
    try:
        w = [float(value) for value in weights]
        r = [float(value) for value in returns]
        target = float(min_return)
        tol = float(tolerance)

        if not w or len(w) != len(r):
            return False

        if not math.isfinite(tol) or tol < 0:
            return False

        if not math.isfinite(target):
            return False

        if not all(math.isfinite(value) for value in w):
            return False

        if not all(math.isfinite(value) for value in r):
            return False

        if any(weight < -tol for weight in w):
            return False

        if abs(math.fsum(w) - 1.0) > tol:
            return False

        actual_return = math.fsum(
            weight * mean_return
            for weight, mean_return in zip(w, r)
        )

        if not math.isfinite(actual_return):
            return False

        return actual_return >= target - tol

    except (TypeError, ValueError, OverflowError):
        return False
