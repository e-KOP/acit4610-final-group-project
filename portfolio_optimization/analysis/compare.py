"""Read-only comparative analysis of saved portfolio ES run records.

AI-generated with Claude (Anthropic), built step by step with and reviewed by
Jakob Andreas Amtedal; see docs/ai_usage.md.

Nothing here runs an optimizer or writes to the raw results. Every number is
computed from the JSONL records written by the experiment runner:
best_weights, best_return, best_variance, min_return, runtime_s, history
(archive best at every change point) and, for population ES, population_best.
"""
import itertools
import json
import math
import statistics
from bisect import bisect_right
from collections import defaultdict
from pathlib import Path

DATASETS = ("port1", "port2", "port3", "port4", "port5")
ALPHAS = (0.25, 0.50, 0.75)
VARIANTS = ("one_plus_one", "mu_plus_lambda", "mu_comma_lambda")
LABELS = {"one_plus_one": "(1+1)-ES", "mu_plus_lambda": "(μ+λ)-ES",
          "mu_comma_lambda": "(μ,λ)-ES"}
PAIRS = (("mu_plus_lambda", "mu_comma_lambda"),
         ("mu_plus_lambda", "one_plus_one"),
         ("mu_comma_lambda", "one_plus_one"))
EXPECTED_SEEDS = 10
WEIGHT_TOL = 1e-8          # a weight above this counts as a held asset
ACTIVE_TOL = 1e-10         # return within this of the target: constraint active


# ---------- loading ----------

def case_name(dataset, alpha):
    return f"{dataset}_alpha{round(alpha * 100):03d}"


def load_runs(path):
    """Read run records; refuse duplicates of (dataset, alpha, variant, seed)."""
    runs, seen = [], set()
    with Path(path).open(encoding="utf-8") as source:
        for number, line in enumerate(source, 1):
            if not line.strip():
                continue
            record = json.loads(line)
            key = (record["dataset"], record["alpha"], record["variant"], record["seed"])
            if key in seen:
                raise ValueError(f"Duplicate run {key} at line {number}")
            seen.add(key)
            runs.append(record)
    if not runs:
        raise ValueError("No run records found")
    return runs


def group_runs(runs):
    """{(dataset, alpha, variant): {seed: record}} for valid runs only."""
    groups = defaultdict(dict)
    for record in runs:
        if record.get("valid", False):
            groups[record["dataset"], record["alpha"], record["variant"]][record["seed"]] = record
    return groups


def completeness(runs):
    """How much of the 450-run design the records cover."""
    expected = len(DATASETS) * len(ALPHAS) * len(VARIANTS) * EXPECTED_SEEDS
    budgets = sorted({r["budget"] for r in runs})
    return {"runs": len(runs), "expected": expected,
            "valid": sum(bool(r.get("valid")) for r in runs),
            "complete": len(runs) == expected, "budgets": budgets}


# ---------- per-run diagnostics ----------

def value_at(history, evaluation):
    """Archive best after `evaluation` evaluations (history holds change points)."""
    index = bisect_right([e for e, _ in history], evaluation) - 1
    if index < 0:
        raise ValueError("evaluation precedes the first history point")
    return history[index][1]


def held_assets(weights, tol=WEIGHT_TOL):
    return sum(w > tol for w in weights)


def effective_assets(weights):
    """1 / sum(w^2): equals k for k equal weights, 1 for a single asset."""
    return 1.0 / math.fsum(w * w for w in weights)


def run_diagnostics(record):
    """Sparsity, constraint activity and convergence/stagnation of one run."""
    history, budget = record["history"], record["budget"]
    first = history[0][1]
    final = record["best_variance"]
    total_gain = first - final
    # evaluation at which 99% of the total improvement had been reached
    if total_gain > 0:
        threshold = final + 0.01 * total_gain
        eval_99 = next(e for e, v in history if v <= threshold)
    else:
        eval_99 = history[0][0]
    improvements = [e for (e, v), (_, prev) in zip(history[1:], history) if v < prev]
    halfway = value_at(history, budget // 2)
    slack = record["best_return"] - record["min_return"]
    row = {
        "held_assets": held_assets(record["best_weights"]),
        "effective_assets": effective_assets(record["best_weights"]),
        "max_weight": max(record["best_weights"]),
        "return_slack": slack,
        "return_active": abs(slack) <= ACTIVE_TOL * max(1.0, abs(record["min_return"])),
        "last_improvement": improvements[-1] if improvements else history[0][0],
        "eval_99pct": eval_99,
        "second_half_gain_pct": 100.0 * (halfway - final) / halfway if halfway > 0 else 0.0,
    }
    if "population_best" in record:
        values = [v for _, v in record["population_best"]]
        row["population_worsened"] = sum(b > a for a, b in zip(values, values[1:]))
        row["generations"] = len(values) - 1
        gap = 100.0 * (values[-1] - final) / final
        # differences below 1e-9 % are floating-point rounding between the
        # solver's NumPy variance and the runner's recomputation, not real gaps
        row["final_population_gap_pct"] = gap if abs(gap) > 1e-9 else 0.0
    return row


# ---------- statistics ----------

def sample_sd(values):
    return statistics.stdev(values) if len(values) > 1 else 0.0


def _ranks(values):
    """Average ranks (1-based) with ties sharing their mean rank."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def wilcoxon_exact(differences):
    """Exact two-sided Wilcoxon signed-rank p-value by full enumeration.

    Zero differences are dropped. Feasible for up to 20 pairs (2^20 sign
    patterns). Returns (W+, n_used, p) with p = None when no pairs remain.
    """
    nonzero = [d for d in differences if d != 0]
    n = len(nonzero)
    if n == 0:
        return 0.0, 0, None
    if n > 20:
        raise ValueError("exact enumeration supports at most 20 pairs")
    ranks = _ranks([abs(d) for d in nonzero])
    w_plus = sum(r for r, d in zip(ranks, nonzero) if d > 0)
    centre = sum(ranks) / 2
    observed = abs(w_plus - centre)
    extreme = sum(
        abs(sum(r for r, s in zip(ranks, signs) if s) - centre) >= observed - 1e-12
        for signs in itertools.product((0, 1), repeat=n)
    )
    return w_plus, n, extreme / 2 ** n


def sign_test(wins, losses):
    """Exact two-sided sign test p-value (ties excluded)."""
    n = wins + losses
    if n == 0:
        return None
    k = min(wins, losses)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


# ---------- tables ----------

def variant_summary(groups):
    """One row per case and variant: variance statistics plus diagnostics."""
    rows = []
    for dataset in DATASETS:
        for alpha in ALPHAS:
            for variant in VARIANTS:
                runs = groups.get((dataset, alpha, variant), {})
                if not runs:
                    continue
                records = [runs[s] for s in sorted(runs)]
                variances = [r["best_variance"] for r in records]
                diag = [run_diagnostics(r) for r in records]
                row = {
                    "case": case_name(dataset, alpha), "dataset": dataset,
                    "assets": records[0]["assets"], "alpha": alpha,
                    "min_return": records[0]["min_return"], "variant": variant,
                    "valid_runs": len(records),
                    "best_variance": min(variances),
                    "mean_variance": statistics.fmean(variances),
                    "median_variance": statistics.median(variances),
                    "sd_variance": sample_sd(variances),
                    "cv_pct": 100 * sample_sd(variances) / statistics.fmean(variances),
                    "mean_runtime_s": statistics.fmean(r["runtime_s"] for r in records),
                    "mean_held_assets": statistics.fmean(d["held_assets"] for d in diag),
                    "mean_effective_assets": statistics.fmean(d["effective_assets"] for d in diag),
                    "return_active_runs": sum(d["return_active"] for d in diag),
                    "mean_eval_99pct": statistics.fmean(d["eval_99pct"] for d in diag),
                    "mean_last_improvement": statistics.fmean(d["last_improvement"] for d in diag),
                    "mean_second_half_gain_pct": statistics.fmean(
                        d["second_half_gain_pct"] for d in diag),
                }
                if all("population_worsened" in d for d in diag):
                    row["mean_population_worsened"] = statistics.fmean(
                        d["population_worsened"] for d in diag)
                    row["mean_final_population_gap_pct"] = statistics.fmean(
                        d["final_population_gap_pct"] for d in diag)
                rows.append(row)
    return rows


def paired_comparisons(groups):
    """Per case, compare variants seed by seed (same seed = paired runs).

    ratio = variance_a / variance_b per seed; wins = seeds where a < b.
    """
    rows = []
    for dataset in DATASETS:
        for alpha in ALPHAS:
            for a, b in PAIRS:
                runs_a = groups.get((dataset, alpha, a), {})
                runs_b = groups.get((dataset, alpha, b), {})
                seeds = sorted(set(runs_a) & set(runs_b))
                if not seeds:
                    continue
                va = [runs_a[s]["best_variance"] for s in seeds]
                vb = [runs_b[s]["best_variance"] for s in seeds]
                diffs = [x - y for x, y in zip(va, vb)]
                ratios = [x / y for x, y in zip(va, vb)]
                wins = sum(d < 0 for d in diffs)
                losses = sum(d > 0 for d in diffs)
                _, n_used, p_w = wilcoxon_exact(diffs)
                rows.append({
                    "case": case_name(dataset, alpha), "dataset": dataset, "alpha": alpha,
                    "a": a, "b": b, "paired_seeds": len(seeds),
                    "a_wins": wins, "b_wins": losses, "ties": len(seeds) - wins - losses,
                    "median_ratio": statistics.median(ratios),
                    "geo_mean_ratio": math.exp(statistics.fmean(math.log(r) for r in ratios)),
                    "sign_test_p": sign_test(wins, losses),
                    "wilcoxon_p": p_w,
                })
    return rows


def mean_ranks(groups):
    """Average rank of each variant over all cases and seeds (1 = lowest variance)."""
    ranks = defaultdict(list)
    for dataset in DATASETS:
        for alpha in ALPHAS:
            runs = {v: groups.get((dataset, alpha, v), {}) for v in VARIANTS}
            seeds = set.intersection(*(set(r) for r in runs.values()))
            for seed in seeds:
                values = [runs[v][seed]["best_variance"] for v in VARIANTS]
                for v, r in zip(VARIANTS, _ranks(values)):
                    ranks[v].append(r)
    return {v: (statistics.fmean(r) if r else None, len(r)) for v, r in ranks.items()}


# ---------- writing ----------

def _fmt(value):
    if isinstance(value, bool):
        return "yes" if value else "no"
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4g}"
    if isinstance(value, str):
        return LABELS.get(value, value)
    return str(value)


def write_table(rows, path_stem, title, note=""):
    """Write rows to CSV (full precision) and Markdown (4 significant digits)."""
    import csv
    path_stem = Path(path_stem)
    columns = list(dict.fromkeys(k for row in rows for k in row))
    with path_stem.with_suffix(".csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    lines = [f"# {title}", ""] + ([note, ""] if note else [])
    lines += ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    lines += ["| " + " | ".join(_fmt(row.get(c)) for c in columns) + " |" for row in rows]
    path_stem.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")