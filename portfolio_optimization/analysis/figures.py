"""Comparative figures from saved portfolio ES run records (read-only).

AI-generated with Claude (Anthropic), built step by step with and reviewed by
Jakob Andreas Amtedal; see docs/ai_usage.md.
"""
import statistics
from pathlib import Path

import matplotlib
matplotlib.use("Agg")                      # write files; never open a window
import matplotlib.pyplot as plt

from .compare import ALPHAS, DATASETS, LABELS, VARIANTS, case_name, held_assets, value_at

COLORS = {"one_plus_one": "#D55E00", "mu_plus_lambda": "#0072B2",
          "mu_comma_lambda": "#009E73"}       # colour-blind safe


def _mean_curve(records, key="history", grid_points=300):
    """Mean of step-function histories on a shared evaluation grid (forward fill)."""
    budget = min(r["budget"] for r in records)
    start = max(r[key][0][0] for r in records)
    step = max(1, (budget - start) // grid_points)
    grid = list(range(start, budget + 1, step))
    if grid[-1] != budget:
        grid.append(budget)
    means = [statistics.fmean(value_at(r[key], e) for r in records) for e in grid]
    return grid, means


def _save(fig, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def convergence_grid(groups, path):
    """Mean archive-best variance against evaluations for all 15 cases."""
    fig, axes = plt.subplots(len(DATASETS), len(ALPHAS), figsize=(13, 16), squeeze=False)
    for i, dataset in enumerate(DATASETS):
        for j, alpha in enumerate(ALPHAS):
            ax = axes[i][j]
            for variant in VARIANTS:
                runs = groups.get((dataset, alpha, variant))
                if runs:
                    grid, means = _mean_curve(list(runs.values()))
                    ax.plot(grid, means, color=COLORS[variant],
                            label=f"{LABELS[variant]} (n={len(runs)})")
            ax.set_yscale("log")
            ax.set_title(case_name(dataset, alpha), fontsize=10)
            ax.grid(alpha=0.3, which="both")
            if j == 0:
                ax.set_ylabel("Mean archive-best variance (log)")
            if i == len(DATASETS) - 1:
                ax.set_xlabel("Objective evaluations")
            if ax.get_lines():
                ax.legend(fontsize=7)
    fig.suptitle("Mean best-so-far variance per case (archive best, mean over seeds)")
    return _save(fig, path)


def relative_excess_boxplots(groups, path):
    """Per case: excess variance over the best run of any variant, in percent."""
    fig, axes = plt.subplots(len(DATASETS), len(ALPHAS), figsize=(12, 15), squeeze=False)
    for i, dataset in enumerate(DATASETS):
        for j, alpha in enumerate(ALPHAS):
            ax = axes[i][j]
            per_variant = [list(groups.get((dataset, alpha, v), {}).values()) for v in VARIANTS]
            all_values = [r["best_variance"] for runs in per_variant for r in runs]
            if not all_values:
                ax.set_visible(False)
                continue
            reference = min(all_values)
            data = [[100 * (r["best_variance"] / reference - 1) for r in runs]
                    for runs in per_variant]
            box = ax.boxplot(data, widths=0.6, patch_artist=True,
                             medianprops={"color": "black"})
            for patch, variant in zip(box["boxes"], VARIANTS):
                patch.set_facecolor(COLORS[variant])
                patch.set_alpha(0.35)
            ax.set_xticks(range(1, len(VARIANTS) + 1),
                          [LABELS[variant] for variant in VARIANTS], fontsize=8)
            ax.set_yscale("symlog", linthresh=1)
            ax.set_title(case_name(dataset, alpha), fontsize=10)
            ax.grid(alpha=0.3, axis="y")
            if j == 0:
                ax.set_ylabel("Excess over best run (%)")
    fig.suptitle("Final variance relative to the best run found for each case "
                 "(0% = best; symmetric log scale)")
    return _save(fig, path)


def sparsity_chart(groups, path):
    """Mean number of held assets (weight > 1e-8) per dataset and variant."""
    fig, axes = plt.subplots(1, len(ALPHAS), figsize=(14, 4.5), sharey=True)
    width = 0.27
    for ax, alpha in zip(axes, ALPHAS):
        for k, variant in enumerate(VARIANTS):
            xs, means, sds = [], [], []
            for d, dataset in enumerate(DATASETS):
                runs = groups.get((dataset, alpha, variant))
                if runs:
                    counts = [held_assets(r["best_weights"]) for r in runs.values()]
                    xs.append(d + (k - 1) * width)
                    means.append(statistics.fmean(counts))
                    sds.append(statistics.stdev(counts) if len(counts) > 1 else 0)
            ax.bar(xs, means, width, yerr=sds, color=COLORS[variant],
                   label=LABELS[variant], capsize=2)
        ax.set_xticks(range(len(DATASETS)), DATASETS)
        ax.set_title(f"alpha = {alpha}")
        ax.set_yscale("log")
        ax.grid(alpha=0.3, axis="y")
    axes[0].set_ylabel("Assets held (weight > 1e-8), mean ± SD")
    axes[0].legend(fontsize=8)
    fig.suptitle("Portfolio sparsity of the final best allocation")
    return _save(fig, path)


def population_vs_archive(groups, dataset, alpha, path, seed=None):
    """Population best (per generation) and archive best for plus and comma, one seed.

    A single seed is shown because averaging over seeds hides the individual
    generations where the comma population best gets worse.
    """
    fig, ax = plt.subplots(figsize=(9, 5))
    shown = None
    for variant in ("mu_plus_lambda", "mu_comma_lambda"):
        runs = groups.get((dataset, alpha, variant))
        if not runs:
            continue
        shown = min(runs) if seed is None else seed
        record = runs[shown]
        steps, values = zip(*record["history"])
        ax.step(steps, values, where="post", color=COLORS[variant], linewidth=2,
                label=f"{LABELS[variant]} archive best")
        steps, values = zip(*record["population_best"])
        ax.step(steps, values, where="post", color=COLORS[variant], linewidth=1,
                linestyle=":", label=f"{LABELS[variant]} current population best")
    ax.set_yscale("log")
    ax.set(xlabel="Objective evaluations", ylabel="Variance (log scale)",
           title=f"{case_name(dataset, alpha)}, seed {shown}: "
                 f"population best vs archive best")
    ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=8)
    return _save(fig, path)