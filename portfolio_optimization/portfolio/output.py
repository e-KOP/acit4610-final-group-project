
"""Summarise and visualise saved portfolio ES experiments.

AI-assisted implementation. See docs/ai_usage.md.

Run from the repository root:
    python -m portfolio_optimization.portfolio.output \
        --runs PATH --output-dir DIR
"""

import argparse
from bisect import bisect_right
import csv
import json
import math
from pathlib import Path
import statistics

from .data import load_portfolio
from .evaluation import (
    expected_return,
    minimum_return_target,
    portfolio_variance,
)
from .experiments import ROOT, load_config
from .feasibility import is_feasible


FIELDS = (
    "case",
    "dataset",
    "assets",
    "alpha",
    "min_return",
    "variant",
    "runs",
    "expected_runs",
    "valid_runs",
    "valid_rate",
    "complete",
    "best_variance",
    "mean_variance",
    "sd_variance",
    "mean_runtime_s",
)


def read_records(path):
    """Read JSONL without modifying the experimental records."""
    records = []

    with Path(path).open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON at line {line_number}"
                ) from exc

            if not isinstance(record, dict):
                raise ValueError(
                    f"Line {line_number} is not a run record"
                )

            records.append(record)

    if not records:
        raise ValueError("No experiment records found")

    return records


def _close(a, b):
    return math.isclose(
        a, b, rel_tol=1e-8, abs_tol=1e-11
    )


def _check_history(record):
    """Validate a saved best-so-far history."""
    history = record.get("history")
    budget = record["budget"]

    if not isinstance(history, list) or not history:
        raise ValueError("Missing best-so-far history")

    last_evaluation = 0
    last_value = math.inf

    for point in history:
        if (
            not isinstance(point, (list, tuple))
            or len(point) != 2
        ):
            raise ValueError("Invalid history point")

        evaluation, value = point

        if (
            type(evaluation) is not int
            or not last_evaluation < evaluation <= budget
        ):
            raise ValueError(
                "History evaluations are not strictly increasing"
            )

        if (
            not isinstance(value, (float, int))
            or not math.isfinite(value)
        ):
            raise ValueError("Invalid history variance")

        if (
            math.isfinite(last_value)
            and value > last_value
            and not _close(value, last_value)
        ):
            raise ValueError("Best-so-far history worsened")

        last_evaluation = evaluation
        last_value = value

    if history[0][0] != 1 or last_evaluation != budget:
        raise ValueError(
            "History must include evaluations 1 and budget"
        )

    if not _close(
        last_value, record["best_variance"]
    ):
        raise ValueError(
            "Final history variance does not match solution"
        )


def validate_records(
    records, *, require_complete=True
):
    """Validate records and configured experiment coverage.

    The complete study requires all 450 combinations.
    Partial studies are allowed only when explicitly requested.
    """
    config = load_config()

    datasets = {
        entry["name"]: load_portfolio(
            ROOT / entry["path"]
        )
        for entry in config["datasets"]
    }

    expected = {
        (entry["name"], alpha, variant, seed)
        for entry in config["datasets"]
        for alpha in config["alphas"]
        for variant in config["variants"]
        for seed in config["seeds"]
    }

    observed = {}

    for record in records:
        key = tuple(
            record.get(field)
            for field in (
                "dataset", "alpha", "variant", "seed"
            )
        )

        if key not in expected:
            raise ValueError(
                f"Unexpected experimental combination: {key}"
            )

        if key in observed:
            raise ValueError(
                f"Duplicate experimental combination: {key}"
            )

        name, alpha, variant, seed = key
        data = datasets[name]
        target = minimum_return_target(
            data.returns, alpha
        )

        if (
            record.get("case")
            != f"{name}_alpha{round(alpha * 100):03d}"
            or record.get("assets") != data.n_assets
            or not _close(
                record.get("min_return", math.nan),
                target,
            )
        ):
            raise ValueError(
                f"Incorrect case metadata: {key}"
            )

        budget = record.get("budget")

        if (
            type(budget) is not int
            or budget < 1
            or record.get("evaluations") != budget
            or (
                require_complete
                and budget != config["evaluation_budget"]
            )
        ):
            raise ValueError(
                f"Invalid evaluation budget: {key}"
            )

        runtime = record.get("runtime_s")

        if (
            not isinstance(runtime, (float, int))
            or not math.isfinite(runtime)
            or runtime < 0
        ):
            raise ValueError(f"Invalid runtime: {key}")

        if type(record.get("valid")) is not bool:
            raise ValueError(
                f"Missing or invalid feasibility status: {key}"
            )

        if record["valid"]:
            weights = record.get("best_weights")

            if not is_feasible(
                weights, data.returns, target
            ):
                raise ValueError(
                    f"Infeasible saved portfolio: {key}"
                )

            actual_return = expected_return(
                weights, data.returns
            )
            actual_variance = portfolio_variance(
                weights, data.covariance
            )

            if (
                not _close(
                    actual_return,
                    record.get("best_return", math.nan),
                )
                or not _close(
                    actual_variance,
                    record.get("best_variance", math.nan),
                )
            ):
                raise ValueError(
                    f"Saved objective or return is incorrect: {key}"
                )

            _check_history(record)

        observed[key] = record

    if require_complete and set(observed) != expected:
        missing = expected.difference(observed)
        raise ValueError(
            "Incomplete experimental coverage: "
            f"missing {len(missing)} runs"
        )

    return observed


def summarise_records(observed):
    """Build 45 summary rows, including incomplete cases."""
    config = load_config()
    rows = []

    for entry in config["datasets"]:
        data = load_portfolio(
            ROOT / entry["path"]
        )

        for alpha in config["alphas"]:
            case = (
                f"{entry['name']}_alpha"
                f"{round(alpha * 100):03d}"
            )

            for variant in config["variants"]:
                group = [
                    observed[
                        (
                            entry["name"],
                            alpha,
                            variant,
                            seed,
                        )
                    ]
                    for seed in config["seeds"]
                    if (
                        entry["name"],
                        alpha,
                        variant,
                        seed,
                    ) in observed
                ]

                values = [
                    record["best_variance"]
                    for record in group
                    if record["valid"]
                ]

                count = len(group)
                expected_count = len(config["seeds"])

                rows.append({
                    "case": case,
                    "dataset": entry["name"],
                    "assets": entry["assets"],
                    "alpha": alpha,
                    "min_return": minimum_return_target(
                        data.returns, alpha
                    ),
                    "variant": variant,
                    "runs": count,
                    "expected_runs": expected_count,
                    "valid_runs": len(values),
                    "valid_rate": (
                        len(values) / count
                        if count else None
                    ),
                    "complete": count == expected_count,
                    "best_variance": (
                        min(values) if values else None
                    ),
                    "mean_variance": (
                        statistics.fmean(values)
                        if values else None
                    ),
                    "sd_variance": (
                        statistics.stdev(values)
                        if len(values) >= 2 else None
                    ),
                    "mean_runtime_s": (
                        statistics.fmean(
                            r["runtime_s"] for r in group
                        )
                        if group else None
                    ),
                })

    return rows


def write_summary(rows, output_dir):
    """Export summary as CSV and Markdown."""
    directory = Path(output_dir)
    directory.mkdir(
        parents=True, exist_ok=True
    )

    csv_path = directory / "portfolio_summary.csv"
    md_path = directory / "portfolio_summary.md"

    with csv_path.open(
        "w", encoding="utf-8", newline=""
    ) as output:
        writer = csv.DictWriter(
            output, fieldnames=FIELDS
        )
        writer.writeheader()
        writer.writerows(rows)

    def fmt(value):
        if value is None:
            return "—"

        if isinstance(value, float):
            return f"{value:.10g}"

        return str(value)

    with md_path.open(
        "w", encoding="utf-8"
    ) as output:
        output.write(
            "# Portfolio ES experiment summary\n\n"
        )
        output.write(
            "Variance statistics use valid runs only. "
            "Runtime averages all available runs. "
            "SD is the sample standard deviation and "
            "is omitted when fewer than two valid runs "
            "are available. Incomplete cases are "
            "marked explicitly.\n\n"
        )

        output.write(
            "| " + " | ".join(FIELDS) + " |\n"
        )
        output.write(
            "| "
            + " | ".join("---" for _ in FIELDS)
            + " |\n"
        )

        for row in rows:
            output.write(
                "| "
                + " | ".join(
                    fmt(row[field]) for field in FIELDS
                )
                + " |\n"
            )

    return csv_path, md_path


def plot_convergence(observed, path):
    """Plot mean archive-best variance for port5_alpha050.

    Histories are treated as step functions, not linearly
    interpolated between improvements.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    config = load_config()
    chosen = {}

    for variant in config["variants"]:
        records = [
            observed[
                ("port5", 0.5, variant, seed)
            ]
            for seed in config["seeds"]
            if (
                "port5", 0.5, variant, seed
            ) in observed
            and observed[
                ("port5", 0.5, variant, seed)
            ]["valid"]
        ]

        if records:
            chosen[variant] = records

    if not chosen:
        raise ValueError(
            "No valid port5_alpha050 runs available"
        )

    budgets = {
        record["budget"]
        for records in chosen.values()
        for record in records
    }

    if len(budgets) != 1:
        raise ValueError(
            "Convergence runs use different evaluation budgets"
        )

    budget = budgets.pop()

    grid = sorted(
        {1, budget}
        | {
            evaluation
            for records in chosen.values()
            for record in records
            for evaluation, _ in record["history"]
        }
    )

    fig, ax = plt.subplots(
        figsize=(10, 5.5)
    )

    for variant, records in chosen.items():
        histories = [
            (
                [
                    point[0]
                    for point in record["history"]
                ],
                [
                    point[1]
                    for point in record["history"]
                ],
            )
            for record in records
        ]

        means = []

        for evaluation in grid:
            values = [
                values[
                    bisect_right(
                        steps, evaluation
                    ) - 1
                ]
                for steps, values in histories
            ]

            means.append(
                statistics.fmean(values)
            )

        ax.step(
            grid,
            means,
            where="post",
            label=(
                f"{variant} "
                f"(valid n={len(records)})"
            ),
        )

    ax.set(
        title=(
            "Portfolio ES convergence — "
            "port5, alpha=0.50"
        ),
        xlabel="Objective evaluations",
        ylabel="Mean archive-best variance",
    )

    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()

    path = Path(path)
    path.parent.mkdir(
        parents=True, exist_ok=True
    )

    fig.savefig(path, dpi=180)
    plt.close(fig)

    return path


def generate_outputs(
    raw_path,
    output_dir,
    *,
    require_complete=True,
):
    """Validate records and generate required outputs."""
    records = read_records(raw_path)

    observed = validate_records(
        records,
        require_complete=require_complete,
    )

    rows = summarise_records(observed)

    paths = list(
        write_summary(
            rows,
            Path(output_dir) / "tables",
        )
    )

    if any(
        key[0] == "port5"
        and key[1] == 0.5
        and record["valid"]
        for key, record in observed.items()
    ):
        paths.append(
            plot_convergence(
                observed,
                Path(output_dir)
                / "figures"
                / "port5_alpha050_convergence.png",
            )
        )

    elif require_complete:
        raise ValueError(
            "No valid port5_alpha050 results "
            "for required plot"
        )

    return paths


def main():
    parser = argparse.ArgumentParser(
        description=__doc__
    )

    parser.add_argument(
        "--runs", type=Path, required=True
    )
    parser.add_argument(
        "--output-dir", type=Path, required=True
    )
    parser.add_argument(
        "--allow-partial", action="store_true"
    )

    args = parser.parse_args()

    paths = generate_outputs(
        args.runs,
        args.output_dir,
        require_complete=not args.allow_partial,
    )

    for path in paths:
        print("Wrote", path)


if __name__ == "__main__":
    main()
