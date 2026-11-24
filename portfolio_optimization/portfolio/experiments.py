
"""Portfolio Evolution Strategies experiment runner.

AI-assisted implementation. See docs/ai_usage.md.

Imports the actual ES solvers only when they are needed, allowing the
experiment pipeline to be tested before the algorithms are merged.
"""

import json
import math
import time
from pathlib import Path

from .data import load_portfolio
from .evaluation import (
    expected_return,
    portfolio_variance,
    minimum_return_target,
)
from .feasibility import is_feasible


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = (
    ROOT / "portfolio_optimization/configs/experiments.json"
)

VARIANTS = (
    "one_plus_one",
    "mu_plus_lambda",
    "mu_comma_lambda",
)


def load_config():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _solver_for(variant):
    """Resolve J's solver implementation when it is available."""

    if variant == "one_plus_one":
        from .one_plus_one import solve_one_plus_one

        return lambda r, c, t, s, b: solve_one_plus_one(
            r, c, t, s, b
        )

    if variant in ("mu_plus_lambda", "mu_comma_lambda"):
        from .population_es import solve_population

        selection = (
            "plus" if variant == "mu_plus_lambda" else "comma"
        )

        return lambda r, c, t, s, b: solve_population(
            r, c, t, s, selection, b
        )

    raise ValueError(f"Unknown ES variant: {variant}")


def _close(actual, reported):
    return math.isclose(
        actual, reported, rel_tol=1e-8, abs_tol=1e-11
    )


def _validated_history(history, budget, best_variance):
    """Validate and compress the best-so-far history."""

    if not isinstance(history, (list, tuple)) or not history:
        raise ValueError(
            "Solver history must be a nonempty sequence"
        )

    previous_evaluation = 0
    previous_best = math.inf
    compressed = []

    for point in history:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError(
                "Each history point must be "
                "[evaluations, best variance]"
            )

        evaluation, value = point

        if (
            type(evaluation) is not int
            or not previous_evaluation < evaluation <= budget
        ):
            raise ValueError(
                "History evaluation numbers must be "
                "strictly increasing"
            )

        try:
            value = float(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(
                "History contains a nonnumeric value"
            ) from exc

        if not math.isfinite(value):
            raise ValueError(
                "History contains a non-finite variance"
            )

        if (
            value > previous_best
            and not _close(value, previous_best)
        ):
            raise ValueError(
                "Best-so-far history worsened"
            )

        if (
            not compressed
            or not _close(value, compressed[-1][1])
        ):
            compressed.append([evaluation, value])

        previous_evaluation = evaluation
        previous_best = value

    if previous_evaluation != budget:
        raise ValueError(
            "History must end at the evaluation budget"
        )

    if not _close(previous_best, best_variance):
        raise ValueError(
            "Final history value disagrees with best variance"
        )

    if compressed[-1][0] != budget:
        compressed.append([budget, previous_best])

    return compressed



def _validated_population_best(points, budget, variant):
    """Validate generation-level population-best history.

    This differs from the best-so-far archive:
    comma-selection population best is allowed to worsen.
    """
    if variant not in ("mu_plus_lambda", "mu_comma_lambda"):
        raise ValueError("Unexpected population history for ES variant")

    if not isinstance(points, (list, tuple)) or not points:
        raise ValueError("Missing population-best history")

    first = min(10, budget)
    expected_evaluation = first
    previous_value = math.inf
    validated = []

    for point in points:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError("Invalid population history point")

        evaluation, value = point

        if (
            type(evaluation) is not int
            or evaluation != expected_evaluation
            or evaluation > budget
        ):
            raise ValueError("Invalid population generation checkpoint")

        try:
            value = float(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("Invalid population variance") from exc

        if not math.isfinite(value):
            raise ValueError("Non-finite population variance")

        if (
            variant == "mu_plus_lambda"
            and value > previous_value
            and not _close(value, previous_value)
        ):
            raise ValueError("Plus-selection population best worsened")

        validated.append([evaluation, value])
        previous_value = value
        expected_evaluation += 70

    last_expected = first + 70 * ((budget - first) // 70)

    if validated[-1][0] != last_expected:
        raise ValueError("Incomplete population generation history")

    return validated


def run_case(
    data,
    alpha,
    variant,
    seed,
    budget=30000,
    solver=None,
    config=None,
):
    """Run and independently validate a single ES experiment.

    A test solver may be supplied with this signature:
        solver(returns, covariance, target, seed, budget)

    Without a test solver, J's real ES implementation is used.
    """

    if variant not in VARIANTS:
        raise ValueError(f"Unknown ES variant: {variant}")

    if type(seed) is not int or seed < 0:
        raise ValueError("Seed must be a nonnegative integer")

    if type(budget) is not int or budget < 1:
        raise ValueError(
            "Evaluation budget must be a positive integer"
        )

    if (
        not math.isfinite(alpha)
        or alpha not in (0.25, 0.50, 0.75)
    ):
        raise ValueError("Unsupported alpha")

    config = load_config() if config is None else config
    target = minimum_return_target(data.returns, alpha)
    chosen_solver = (
        _solver_for(variant) if solver is None else solver
    )

    start = time.perf_counter()
    result = chosen_solver(
        data.returns,
        data.covariance,
        target,
        seed,
        budget,
    )
    elapsed = time.perf_counter() - start

    if not isinstance(result, dict):
        raise ValueError(
            "Solver must return a result dictionary"
        )

    if (
        type(result.get("evaluations")) is not int
        or result["evaluations"] != budget
    ):
        raise ValueError(
            "Solver did not use the exact evaluation budget"
        )

    try:
        weights = [
            float(w) for w in result["best_weights"]
        ]
        reported_variance = float(
            result["best_variance"]
        )
        reported_return = float(
            result["best_return"]
        )
    except (
        KeyError, TypeError, ValueError, OverflowError
    ) as exc:
        raise ValueError(
            "Solver result is missing a valid best solution"
        ) from exc

    if (
        not math.isfinite(reported_variance)
        or not math.isfinite(reported_return)
    ):
        raise ValueError(
            "Solver returned non-finite objective values"
        )

    if not is_feasible(weights, data.returns, target):
        raise ValueError(
            "Solver returned an infeasible best portfolio"
        )

    checked_variance = portfolio_variance(
        weights, data.covariance
    )
    checked_return = expected_return(
        weights, data.returns
    )

    if not _close(checked_variance, reported_variance):
        raise ValueError(
            "Solver variance does not match "
            "independently recomputed value"
        )

    if not _close(checked_return, reported_return):
        raise ValueError(
            "Solver expected return does not match "
            "independently recomputed value"
        )

    history = _validated_history(
        result.get("history"),
        budget,
        checked_variance,
    )

    settings = dict(
        config["one_plus_one"]
        if variant == "one_plus_one"
        else config["population"]
    )
    settings["initial_step_size"] = config["initial_step_size"]
    settings["step_size_bounds"] = config["step_size_bounds"]

    record = {
        "case": f"{data.name}_alpha{round(alpha * 100):03d}",
        "dataset": data.name,
        "assets": data.n_assets,
        "alpha": alpha,
        "min_return": target,
        "variant": variant,
        "seed": seed,
        "settings": settings,
        "budget": budget,
        "evaluations": budget,
        "best_weights": weights,
        "best_return": checked_return,
        "best_variance": checked_variance,
        "valid": True,
        "runtime_s": elapsed,
        "history": history,
    }

    if "population_best" in result:
        record["population_best"] = _validated_population_best(
            result["population_best"],
            budget,
            variant,
        )

    return record


def run_selected(
    output_path,
    *,
    datasets=None,
    alphas=None,
    variants=None,
    seeds=None,
    budget=None,
    solver=None,
    resume=False,
):
    """Run selected experiments and save JSONL records incrementally.

    Defaults to all 450 runs. Use explicit selections for small tests.

    Existing outputs are never overwritten.
    resume=True skips previously recorded combinations.
    """

    config = load_config()

    entries = {
        item["name"]: item
        for item in config["datasets"]
    }

    datasets = (
        tuple(entries)
        if datasets is None
        else tuple(datasets)
    )
    alphas = (
        tuple(config["alphas"])
        if alphas is None
        else tuple(alphas)
    )
    variants = (
        tuple(config["variants"])
        if variants is None
        else tuple(variants)
    )
    seeds = (
        tuple(config["seeds"])
        if seeds is None
        else tuple(seeds)
    )
    budget = (
        config["evaluation_budget"]
        if budget is None
        else budget
    )

    for selected, allowed, label in (
        (datasets, entries, "dataset"),
        (alphas, config["alphas"], "alpha"),
        (variants, VARIANTS, "variant"),
        (seeds, config["seeds"], "seed"),
    ):
        if (
            not selected
            or len(selected) != len(set(selected))
            or not set(selected) <= set(allowed)
        ):
            raise ValueError(
                f"Invalid or duplicate {label} selection"
            )

    output_path = Path(output_path)
    output_path.parent.mkdir(
        parents=True, exist_ok=True
    )

    completed = set()

    if output_path.exists():
        if not resume:
            raise FileExistsError(
                f"Refusing to overwrite {output_path}"
            )

        for line in output_path.read_text(
            encoding="utf-8"
        ).splitlines():
            if not line.strip():
                continue

            record = json.loads(line)
            key = (
                record["dataset"],
                record["alpha"],
                record["variant"],
                record["seed"],
            )

            if key in completed:
                raise ValueError(
                    "Existing output has duplicate "
                    "experiment records"
                )

            if (
                record["budget"] != budget
                or record["evaluations"] != budget
                or not record["valid"]
            ):
                raise ValueError(
                    "Existing output contains "
                    "an incompatible run"
                )

            completed.add(key)

    written = 0

    mode = "a" if resume else "x"

    with output_path.open(
        mode, encoding="utf-8"
    ) as output:

        for name in datasets:
            data = load_portfolio(
                ROOT / entries[name]["path"]
            )

            if data.n_assets != entries[name]["assets"]:
                raise ValueError(
                    f"Unexpected asset count in {name}"
                )

            for alpha in alphas:
                for variant in variants:
                    for seed in seeds:
                        key = (
                            name, alpha, variant, seed
                        )

                        if key in completed:
                            continue

                        record = run_case(
                            data,
                            alpha,
                            variant,
                            seed,
                            budget,
                            solver=solver,
                            config=config,
                        )

                        output.write(
                            json.dumps(
                                record, allow_nan=False
                            ) + "\n"
                        )
                        output.flush()

                        written += 1

                        print(
                            f"[{written}] {record['case']} "
                            f"{variant} seed={seed}: "
                            f"variance="
                            f"{record['best_variance']:.8g} "
                            f"time="
                            f"{record['runtime_s']:.2f}s"
                        )

    return written
