"""Command line for the read-only portfolio ES analysis.

AI-generated with Claude (Anthropic), built step by step with and reviewed by
Jakob Andreas Amtedal; see docs/ai_usage.md.

Run from the repository root:
    python -m portfolio_optimization.analysis --runs portfolio_optimization/results/raw/portfolio_runs.jsonl

The runs file is only read. Its SHA-256 is checked before and after the
analysis and recorded with the outputs.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from . import compare, figures

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "portfolio_optimization" / "results" / "analysis"


def sha256(path):
    """SHA-256 with Windows line endings normalised, so the value is the same
    on every platform and matches the file as stored in the repository."""
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def analyse(runs_path, out_dir, allow_partial=False, focus=("port5", 0.50)):
    runs_path, out_dir = Path(runs_path).resolve(), Path(out_dir).resolve()
    if out_dir == runs_path.parent:
        raise ValueError("Write the analysis to its own directory, not next to the raw runs")
    before = sha256(runs_path)

    runs = compare.load_runs(runs_path)
    status = compare.completeness(runs)
    if not status["complete"] and not allow_partial:
        raise ValueError(f"Only {status['runs']} of {status['expected']} runs present; "
                         "use --allow-partial for preliminary analysis")
    label = ("FINAL: all 450 runs" if status["complete"] else
             f"PRELIMINARY: {status['runs']} of {status['expected']} runs, "
             f"budget(s) {status['budgets']} - not the official result")
    groups = compare.group_runs(runs)

    out_dir.mkdir(parents=True, exist_ok=True)
    note = f"_{label}_"
    compare.write_table(compare.variant_summary(groups), out_dir / "variant_summary",
                        "Per case and variant: variance, runtime, sparsity, convergence", note)
    compare.write_table(compare.paired_comparisons(groups), out_dir / "paired_comparisons",
                        "Paired per-seed comparisons (ratio = variance a / variance b)", note)
    ranks = [{"variant": v, "mean_rank": r, "ranked_runs": n}
             for v, (r, n) in compare.mean_ranks(groups).items()]
    compare.write_table(ranks, out_dir / "mean_ranks",
                        "Mean rank over all cases and seeds (1 = lowest variance)", note)

    produced = [
        figures.convergence_grid(groups, out_dir / "convergence_all_cases.png"),
        figures.relative_excess_boxplots(groups, out_dir / "relative_excess_boxplots.png"),
        figures.sparsity_chart(groups, out_dir / "sparsity.png"),
        figures.population_vs_archive(groups, *focus,
                                      out_dir / f"population_vs_archive_{focus[0]}.png"),
    ]

    after = sha256(runs_path)
    if after != before:
        raise RuntimeError("The runs file changed during the analysis")
    (out_dir / "analysis_metadata.json").write_text(json.dumps({
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "runs_file": str(runs_path), "runs_sha256": before,
        "status": status, "label": label,
    }, indent=2) + "\n", encoding="utf-8")
    return label, produced


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m portfolio_optimization.analysis",
                                     description="Read-only comparison of the ES variants.")
    parser.add_argument("--runs", type=Path, required=True, help="JSONL run records")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output directory")
    parser.add_argument("--allow-partial", action="store_true",
                        help="analyse an incomplete set, labelled PRELIMINARY")
    args = parser.parse_args(argv)
    label, produced = analyse(args.runs, args.out, args.allow_partial)
    print(label)
    print(f"Tables and figures written to {args.out}")


if __name__ == "__main__":
    main()