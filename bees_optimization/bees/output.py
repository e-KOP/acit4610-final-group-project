"""Build the Problem 1 tables and figures from the saved raw records only.

AI-generated with Claude (Anthropic), 2026-11-20, built step by step with and
reviewed by Jakob Andreas Amtedal; see docs/ai_usage.md.

Run from the repository root (after the experiments):
    python -m bees_optimization.bees.output
"""
import bisect
import csv
import json
import statistics
from pathlib import Path

import matplotlib
matplotlib.use("Agg")          # save files; don't open a window
import matplotlib.pyplot as plt

from .tsplib import load_tsplib

PACKAGE_DIR = Path(__file__).resolve().parents[1]      # bees_optimization/
RESULTS = PACKAGE_DIR / "results"

INSTANCE_ORDER = ["eil51", "berlin52", "st70", "eil76", "kroA100", "ch150"]
FUNCTION_ORDER = ["sphere", "rosenbrock", "rastrigin", "ackley"]
NEIGHBORHOODS = ["swap", "segment_reversal"]
FIGURES = RESULTS / "figures"
TSPLIB_DIR = PACKAGE_DIR / "data" / "tsplib"
GRID_STEP = 100                # read every run at every 100 evaluations
LABELS = {"swap": "Swap", "segment_reversal": "Segment reversal"}
COLORS = {"swap": "#D55E00", "segment_reversal": "#0072B2"}   # colour-blind safe pair


def load_runs(path):
    """Read a .jsonl file: one run record (a dict) per line."""
    with Path(path).open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def sample_sd(values):
    """Sample standard deviation (n - 1), the project convention."""
    return statistics.stdev(values) if len(values) > 1 else 0.0


def tsp_summary(runs):
    """One row per instance and move, in a fixed order."""
    rows = []
    for instance in INSTANCE_ORDER:
        for move in NEIGHBORHOODS:
            group = [r for r in runs if r["instance"] == instance and r["neighborhood"] == move]
            if not group:
                continue
            lengths = [r["best_length"] for r in group]
            rows.append({
                "instance": instance,
                "cities": group[0]["cities"],
                "optimum": group[0]["optimum"],
                "neighborhood": move,
                "runs": len(group),
                "best": min(lengths),
                "mean": statistics.mean(lengths),
                "sd": sample_sd(lengths),
                "mean_gap_pct": statistics.mean(r["gap_pct"] for r in group),
                "mean_initial_best": statistics.mean(r["initial_best"] for r in group),
                "mean_runtime_s": statistics.mean(r["runtime_s"] for r in group),
            })
    return rows


def continuous_summary(runs):
    """One row per function and dimension, in a fixed order."""
    rows = []
    for function in FUNCTION_ORDER:
        for dimension in (10, 30):
            group = [r for r in runs if r["function"] == function and r["dimension"] == dimension]
            if not group:
                continue
            values = [r["best_value"] for r in group]
            rows.append({
                "function": function,
                "dimension": dimension,
                "runs": len(group),
                "best": min(values),
                "mean": statistics.mean(values),
                "sd": sample_sd(values),
                "mean_initial_best": statistics.mean(r["initial_best"] for r in group),
                "mean_runtime_s": statistics.mean(r["runtime_s"] for r in group),
            })
    return rows


def write_table(rows, columns, csv_path, md_path, title):
    """Write a table twice: CSV with full precision, Markdown rounded for reading.

    columns: list of (key, header, format_function)
    """
    with Path(csv_path).open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=[key for key, _, _ in columns],
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows({key: row[key] for key, _, _ in columns} for row in rows)

    lines = [f"# {title}", "",
             "| " + " | ".join(header for _, header, _ in columns) + " |",
             "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(fmt(row[key]) for key, _, fmt in columns) + " |")
    Path(md_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return "\n".join(lines)


TSP_COLUMNS = [
    ("instance", "Instance", str),
    ("cities", "Cities", str),
    ("optimum", "Optimum", lambda v: f"{v:,}"),
    ("neighborhood", "Neighbourhood", lambda v: {"swap": "Swap", "segment_reversal": "Segment reversal"}[v]),
    ("runs", "Runs", str),
    ("best", "Best", lambda v: f"{v:,}"),
    ("mean", "Mean", lambda v: f"{v:,.1f}"),
    ("sd", "SD", lambda v: f"{v:,.1f}"),
    ("mean_gap_pct", "Mean gap (%)", lambda v: f"{v:.2f}"),
    ("mean_initial_best", "Mean initial best", lambda v: f"{v:,.1f}"),
    ("mean_runtime_s", "Mean runtime (s)", lambda v: f"{v:.3f}"),
]
CONTINUOUS_COLUMNS = [
    ("function", "Function", str.capitalize),
    ("dimension", "D", str),
    ("runs", "Runs", str),
    ("best", "Best", lambda v: f"{v:.4g}"),
    ("mean", "Mean", lambda v: f"{v:.4g}"),
    ("sd", "SD", lambda v: f"{v:.4g}"),
    ("mean_initial_best", "Mean initial best", lambda v: f"{v:.4g}"),
    ("mean_runtime_s", "Mean runtime (s)", lambda v: f"{v:.3f}"),
]

def value_at(history, evaluation):
    """Best-so-far after `evaluation` evaluations.

    history holds [evaluation, best] at every change, so the value at any
    evaluation is the last change at or before it (forward filling).
    """
    index = bisect.bisect_right([e for e, _ in history], evaluation) - 1
    if index < 0:
        raise ValueError("evaluation is before the first recorded point")
    return history[index][1]


def mean_curve(runs):
    """Mean and SD of best-so-far over runs, on a shared evaluation grid."""
    start = max(r["history"][0][0] for r in runs)       # end of initialization
    budget = min(r["budget"] for r in runs)
    grid = [start] + list(range((start // GRID_STEP + 1) * GRID_STEP, budget + 1, GRID_STEP))
    if grid[-1] != budget:
        grid.append(budget)
    curves = [[value_at(r["history"], e) for e in grid] for r in runs]
    means = [statistics.mean(column) for column in zip(*curves)]
    sds = [sample_sd(list(column)) for column in zip(*curves)]
    return grid, means, sds


def plot_tsp_convergence(runs, instance, path):
    """Mean best-so-far over seeds for both moves, with the optimum marked."""
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for move in NEIGHBORHOODS:
        group = [r for r in runs if r["instance"] == instance and r["neighborhood"] == move]
        grid, means, sds = mean_curve(group)
        ax.plot(grid, means, color=COLORS[move], linewidth=2,
                label=f"{LABELS[move]} (mean of {len(group)} runs)")
        ax.fill_between(grid, [m - s for m, s in zip(means, sds)],
                        [m + s for m, s in zip(means, sds)],
                        color=COLORS[move], alpha=0.15)
    optimum = group[0]["optimum"]
    ax.axhline(optimum, color="black", linestyle="--", linewidth=1.2,
               label=f"Optimum ({optimum:,})")
    ax.set_xlabel("Objective evaluations")
    ax.set_ylabel("Best-so-far tour length")
    ax.set_title(f"{instance}: mean best-so-far tour length (shaded: ±1 SD)")
    ax.set_xlim(0, group[0]["budget"])
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)

def plot_best_route(runs, instance, path):
    """Draw the shortest tour over all runs of one instance (both moves, all seeds)."""
    group = [r for r in runs if r["instance"] == instance]
    # shortest tour; ties broken by move name, then seed, so the choice is fixed
    best = min(group, key=lambda r: (r["best_length"], r["neighborhood"], r["seed"]))

    _, coordinates = load_tsplib(TSPLIB_DIR / f"{instance}.tsp")
    route = best["best_tour"] + [best["best_tour"][0]]       # close the loop
    xs = [coordinates[city][0] for city in route]
    ys = [coordinates[city][1] for city in route]

    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.plot(xs[:-1], ys[:-1], "-", color=COLORS[best["neighborhood"]],
            linewidth=1.3, zorder=1, label="Tour")
    ax.plot(xs[-2:], ys[-2:], "--", color="grey", linewidth=1.5,
            zorder=1, label="Return leg")
    ax.scatter(xs[:-1], ys[:-1], s=18, color="black", zorder=2)
    ax.scatter(xs[0], ys[0], s=160, marker="*", color="#E69F00",
               edgecolor="black", zorder=3, label=f"Start: city {best['best_tour'][0]}")
    ax.set_title(f"Shortest {instance} tour over all {len(group)} runs\n"
                 f"{LABELS[best['neighborhood']]}, seed {best['seed']}, "
                 f"length {best['best_length']:,} "
                 f"(optimum {best['optimum']:,}, gap {best['gap_pct']:.2f}%)")
    ax.set_xlabel("x coordinate")
    ax.set_ylabel("y coordinate")
    ax.set_aspect("equal", adjustable="datalim")     # don't stretch the map
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return best

def plot_continuous_convergence(runs, function, dimension, path):
    """Mean best-so-far over seeds for one function and dimension, log y-axis."""
    group = [r for r in runs if r["function"] == function and r["dimension"] == dimension]
    grid, means, _ = mean_curve(group)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(grid, means, color="#0072B2", linewidth=2, label=f"Mean of {len(group)} runs")
    ax.set_yscale("log")
    ax.set_xlabel("Objective evaluations")
    ax.set_ylabel("Mean best-so-far objective value (log scale)")
    ax.set_title(f"{function.capitalize()}, D = {dimension}: mean best-so-far objective "
                 f"(global minimum 0)")
    ax.set_xlim(0, group[0]["budget"])
    ax.grid(alpha=0.3, which="both")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def plot_final_boxplots(runs, dimension, path):
    """One panel per function: final objective values of all seeds at one dimension."""
    fig, axes = plt.subplots(1, len(FUNCTION_ORDER), figsize=(13, 4.2))
    for ax, function in zip(axes, FUNCTION_ORDER):
        values = [r["best_value"] for r in runs
                  if r["function"] == function and r["dimension"] == dimension]
        ax.boxplot(values, widths=0.5)
        # show the individual runs on top of the box
        ax.scatter([1] * len(values), values, s=14, color="#0072B2", alpha=0.7, zorder=3)
        ax.set_title(f"{function.capitalize()} ({len(values)} runs)")
        ax.set_xticks([1], [f"D = {dimension}"])
        ax.set_ylabel("Final best objective value")
        ax.grid(alpha=0.3, axis="y")
    fig.suptitle(f"Final objective values after 30,000 evaluations, D = {dimension} "
                 f"(global minimum 0 for every function)")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)

def main():
    raw = RESULTS / "raw"
    tables = RESULTS / "tables"
    tables.mkdir(parents=True, exist_ok=True)

    tsp = load_runs(raw / "tsp_runs.jsonl")
    cont = load_runs(raw / "continuous_runs.jsonl")

    print(write_table(tsp_summary(tsp), TSP_COLUMNS,
                      tables / "tsp_summary.csv", tables / "tsp_summary.md",
                      "TSP summary: final tour length over 10 seeds"))
    print()
    print(write_table(continuous_summary(cont), CONTINUOUS_COLUMNS,
                      tables / "continuous_summary.csv", tables / "continuous_summary.md",
                      "Continuous summary: final objective value (error to the minimum 0)"))

    FIGURES.mkdir(parents=True, exist_ok=True)
    for instance in ("berlin52", "ch150"):
        plot_tsp_convergence(tsp, instance, FIGURES / f"tsp_convergence_{instance}.png")

    best = plot_best_route(tsp, "berlin52", FIGURES / "berlin52_best_route.png")
    print(f"Shortest berlin52 tour: {best['best_length']} "
          f"({best['neighborhood']}, seed {best['seed']}, gap {best['gap_pct']:.2f}%)")
    
    plot_continuous_convergence(cont, "rastrigin", 10, FIGURES / "rastrigin_d10_convergence.png")
    plot_final_boxplots(cont, 30, FIGURES / "continuous_d30_boxplots.png")
   
    print(f"Figures written to {FIGURES}")
    



if __name__ == "__main__":
    main()