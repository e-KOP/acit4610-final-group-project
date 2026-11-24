
"""Portfolio Evolution Strategies experiment runner.

AI-assisted implementation. See docs/ai_usage.md.

Imports the actual ES solvers only when they are needed, allowing the
experiment pipeline to be tested before the algorithms are merged.
"""

import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from .data import load_portfolio
from .evaluation import (
    expected_return,
    portfolio_variance,
    minimum_return_target,
)
from .feasibility import is_feasible
from .provenance import (
    build_metadata, metadata_path_for, verify_metadata,
    write_metadata_exclusive,
)


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


def _load_recoverable_jsonl(path):
    """Parse saved JSONL, identifying only an interrupted final partial line.

    Parsing never changes the file. The caller validates all complete records
    before applying any proposed truncation or appended newline.
    """
    raw = Path(path).read_bytes()
    records = []
    offset = 0
    truncated_at = None
    newline_missing = bool(raw) and not raw.endswith(b"\n")
    lines = raw.splitlines(keepends=True)

    for number, line in enumerate(lines, 1):
        if not line.strip():
            raise ValueError(f"Blank JSONL line at {number}")
        try:
            record = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            # A terminated malformed record or earlier malformed record
            # cannot safely be attributed to an interrupted write.
            if number != len(lines) or line.endswith(b"\n"):
                raise ValueError(f"Corrupted JSONL record at line {number}") from exc
            truncated_at = offset
            break
        if not isinstance(record, dict):
            raise ValueError(f"JSONL line {number} is not an object")
        records.append(record)
        offset += len(line)

    return records, raw, truncated_at, newline_missing


def _apply_safe_recovery(path, raw, truncated_at, newline_missing):
    """Save the original bytes before truncating an interrupted final line."""
    path = Path(path)
    if truncated_at is not None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup = path.with_name(path.name + ".interrupted-" + stamp + ".bak")
        with backup.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        with path.open("r+b") as stream:
            stream.truncate(truncated_at)
            stream.flush()
            os.fsync(stream.fileno())
        print(f"Recovered incomplete final JSONL line; original saved at {backup}")
    elif newline_missing:
        # The final record is complete JSON, but an interrupted newline write
        # would otherwise cause the next record to be concatenated with it.
        with path.open("ab") as stream:
            stream.write(b"\n")
            stream.flush()
            os.fsync(stream.fileno())


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
    """Run selected experiments, recording provenance and saving JSONL.

    The sidecar is created before the first run. On resume the *entire*
    experimental identity must match, and all existing complete records are
    independently revalidated before anything is appended. A single torn
    final JSONL line is backed up and removed after validation succeeds.
    """
    config = load_config()
    entries = {item["name"]: item for item in config["datasets"]}

    datasets = tuple(entries) if datasets is None else tuple(datasets)
    alphas = tuple(config["alphas"]) if alphas is None else tuple(alphas)
    variants = tuple(config["variants"]) if variants is None else tuple(variants)
    seeds = tuple(config["seeds"]) if seeds is None else tuple(seeds)
    budget = config["evaluation_budget"] if budget is None else budget

    if type(budget) is not int or budget < 1:
        raise ValueError("Evaluation budget must be a positive integer")

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
            raise ValueError(f"Invalid or duplicate {label} selection")

    output_path = Path(output_path)
    sidecar = metadata_path_for(output_path)

    selection = {
        "datasets": datasets,
        "alphas": alphas,
        "variants": variants,
        "seeds": seeds,
        "budget": budget,
    }
    metadata = build_metadata(
        ROOT, CONFIG_PATH, config, selection,
        solver_mode="actual_es" if solver is None else "injected_solver",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not resume:
        if output_path.exists() or sidecar.exists():
            raise FileExistsError(
                f"Refusing to overwrite existing output or metadata: {output_path}"
            )
        write_metadata_exclusive(sidecar, metadata)
        completed = set()
    else:
        if sidecar.exists():
            verify_metadata(sidecar, metadata)
        elif output_path.exists():
            raise ValueError(
                "Refusing unsafe resume: an existing JSONL file has no metadata sidecar"
            )
        else:
            write_metadata_exclusive(sidecar, metadata)

        completed = set()
        if output_path.exists():
            records, raw, torn_at, newline_missing = _load_recoverable_jsonl(output_path)
            if records:
                # Import here to avoid circular import (output imports ROOT and
                # load_config from this module). Independently checks weights,
                # return, variance, history, metadata and duplicate case keys.
                from .output import validate_records
                observed = validate_records(records, require_complete=False)
                selected_keys = {
                    (name, alpha, variant, seed)
                    for name in datasets
                    for alpha in alphas
                    for variant in variants
                    for seed in seeds
                }
                if not set(observed) <= selected_keys:
                    raise ValueError("Existing JSONL contains cases outside the selected matrix")

                for key, record in observed.items():
                    if (
                        record.get("budget") != budget
                        or record.get("evaluations") != budget
                        or record.get("valid") is not True
                    ):
                        raise ValueError("Existing output contains an incompatible run")
                    expected_settings = dict(
                        config["one_plus_one"]
                        if record["variant"] == "one_plus_one"
                        else config["population"]
                    )
                    expected_settings["initial_step_size"] = config["initial_step_size"]
                    expected_settings["step_size_bounds"] = config["step_size_bounds"]
                    if record.get("settings") != expected_settings:
                        raise ValueError("Existing run has incompatible algorithm settings")
                    if "population_best" in record:
                        _validated_population_best(
                            record["population_best"], budget, record["variant"]
                        )
                    completed.add(key)

            # No file mutation occurs until every complete record has passed.
            _apply_safe_recovery(output_path, raw, torn_at, newline_missing)

    written = 0
    with output_path.open("a" if resume else "x", encoding="utf-8", newline="\n") as output:
        for name in datasets:
            data = load_portfolio(ROOT / entries[name]["path"])
            if data.n_assets != entries[name]["assets"]:
                raise ValueError(f"Unexpected asset count in {name}")
            for alpha in alphas:
                for variant in variants:
                    for seed in seeds:
                        key = (name, alpha, variant, seed)
                        if key in completed:
                            continue
                        record = run_case(
                            data, alpha, variant, seed, budget,
                            solver=solver, config=config,
                        )
                        output.write(json.dumps(record, allow_nan=False) + "\n")
                        output.flush()
                        os.fsync(output.fileno())
                        written += 1
                        print(
                            f"[{written}] {record['case']} {variant} seed={seed}: "
                            f"variance={record['best_variance']:.8g} "
                            f"time={record['runtime_s']:.2f}s"
                        )
    return written
