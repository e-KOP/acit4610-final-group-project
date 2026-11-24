"""Optional diagnostic: record the (1+1)-ES step size during a few runs.

AI-generated with Claude (Anthropic), built step by step with and reviewed by
Jakob Andreas Amtedal; see docs/ai_usage.md.

The saved experiment records do not contain step sizes, so the step-size
collapse cannot be measured from them directly. This script re-runs the
unchanged (1+1)-ES for ONE case and the chosen seeds, observing every
step-size update through a wrapper. It is a diagnostic, not part of the
official 450-run dataset; it writes only to results/analysis/step_size/.

    python -m portfolio_optimization.analysis.step_size --dataset port5 --alpha 0.5 \
        --runs portfolio_optimization/results/raw/portfolio_runs.jsonl

With --runs, each re-run is checked against the official record for the same
seed: identical best variance and weights show that the diagnostic observed
exactly the official run.
"""
import argparse
import csv
import json
import math
import statistics
from pathlib import Path

from ..portfolio import one_plus_one
from ..portfolio.data import load_portfolio
from ..portfolio.evaluation import minimum_return_target

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "portfolio_optimization" / "results" / "analysis" / "step_size"


def trace(returns, covariance, target, seed, budget=30000):
    """Run the (1+1)-ES once; return its result and [(trial, sigma, success)]."""
    steps = []
    original = one_plus_one.update_step_size

    def observed(sigma, success):
        new_sigma = original(sigma, success)
        steps.append((len(steps) + 1, new_sigma, success))
        return new_sigma

    one_plus_one.update_step_size = observed
    try:
        result = one_plus_one.solve_one_plus_one(returns, covariance, target, seed, budget)
    finally:
        one_plus_one.update_step_size = original
    return result, steps


def summarise(steps, floor=1e-8):
    successes = sum(s for _, _, s in steps)
    first_floor = next((t for t, sigma, _ in steps if sigma <= floor * 1.0001), None)
    return {"trials": len(steps), "success_rate": successes / len(steps),
            "first_trial_at_floor": first_floor, "final_sigma": steps[-1][1],
            "trials_at_floor": sum(sigma <= floor * 1.0001 for _, sigma, _ in steps)}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m portfolio_optimization.analysis.step_size")
    parser.add_argument("--dataset", required=True, choices=("port1", "port2", "port3", "port4", "port5"))
    parser.add_argument("--alpha", type=float, required=True, choices=(0.25, 0.5, 0.75))
    parser.add_argument("--seeds", type=int, nargs="+", default=list(range(10)))
    parser.add_argument("--budget", type=int, default=30000)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--runs", type=Path, help="official JSONL, to confirm identical re-runs")
    args = parser.parse_args(argv)

    official = {}
    if args.runs:
        with args.runs.open(encoding="utf-8") as source:
            for line in source:
                if line.strip():
                    rec = json.loads(line)
                    if (rec["dataset"], rec["alpha"], rec["variant"]) == (
                            args.dataset, args.alpha, "one_plus_one"):
                        official[rec["seed"]] = rec

    data = load_portfolio(ROOT / "portfolio_optimization" / "data" / "or_library" / f"{args.dataset}.txt")
    target = minimum_return_target(data.returns, args.alpha)
    args.out.mkdir(parents=True, exist_ok=True)
    rows, traces = [], {}
    for seed in args.seeds:
        result, steps = trace(data.returns, data.covariance, target, seed, args.budget)
        summary = summarise(steps)
        row = {"seed": seed, "best_variance": result["best_variance"], **summary}
        if seed in official:
            rec = official[seed]
            row["matches_official"] = (
                rec["budget"] == args.budget
                and math.isclose(rec["best_variance"], result["best_variance"], rel_tol=1e-9)
                and all(math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-15)
                        for a, b in zip(rec["best_weights"], result["best_weights"])))
        rows.append(row)
        traces[seed] = steps
        print(f"seed {seed}: success rate {summary['success_rate']:.3f}, "
              f"sigma at 1e-8 from trial {summary['first_trial_at_floor']}, "
              f"{summary['trials_at_floor']} trials at the floor"
              + (f", matches official run: {row['matches_official']}"
                 if "matches_official" in row else ""))

    stem = args.out / f"{args.dataset}_alpha{round(args.alpha * 100):03d}"
    with stem.with_suffix(".csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for seed, steps in traces.items():
        ax.plot([t + 1 for t, _, _ in steps], [s for _, s, _ in steps], linewidth=0.8, alpha=0.7)
    ax.axhline(1e-8, color="black", linestyle="--", linewidth=1, label="lower bound 1e-8")
    ax.set_yscale("log")
    ax.set(xlabel="Objective evaluations", ylabel="Step size sigma (log scale)",
           title=f"(1+1)-ES step size, {args.dataset} alpha={args.alpha} "
                 f"({len(traces)} seeds, diagnostic re-run)")
    ax.grid(alpha=0.3, which="both")
    ax.legend()
    fig.tight_layout()
    fig.savefig(stem.with_suffix(".png"), dpi=180)
    print(f"mean success rate {statistics.fmean(r['success_rate'] for r in rows):.3f}; "
          f"written to {stem}.csv/.png")


if __name__ == "__main__":
    main()