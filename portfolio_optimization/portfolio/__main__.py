
"""Command-line interface for portfolio ES experiments.

AI-assisted implementation. See docs/ai_usage.md.

Run with:
    python -m portfolio_optimization.portfolio --help
"""

import argparse
from pathlib import Path

from .experiments import (
    VARIANTS,
    ROOT,
    _solver_for,
    load_config,
    run_selected,
)
from .output import generate_outputs


RESULTS = ROOT / "portfolio_optimization" / "results"
RAW_FILE = RESULTS / "raw" / "portfolio_runs.jsonl"


def build_parser():
    parser = argparse.ArgumentParser(
        description="Portfolio ES experiments and result processing"
    )
    commands = parser.add_subparsers(
        dest="command", required=True
    )

    pilot = commands.add_parser(
        "pilot",
        help="Run one small experiment in results/scratch",
    )
    pilot.add_argument(
        "--dataset", required=True,
        choices=("port1", "port2", "port3", "port4", "port5"),
    )
    pilot.add_argument(
        "--alpha", required=True, type=float,
        choices=(0.25, 0.50, 0.75),
    )
    pilot.add_argument(
        "--variant", required=True, choices=VARIANTS,
    )
    pilot.add_argument(
        "--seed", type=int, default=0,
        choices=range(10),
    )
    pilot.add_argument(
        "--budget", type=int, default=300,
    )
    pilot.add_argument(
        "--resume", action="store_true",
    )

    full = commands.add_parser(
        "full",
        help="Run all 450 experiments at the configured budget",
    )
    full.add_argument(
        "--confirm-450", action="store_true",
        help="Explicitly confirm the complete experiment",
    )
    full.add_argument(
        "--resume", action="store_true",
    )

    summary = commands.add_parser(
        "summarize",
        help="Validate saved records and generate outputs",
    )
    summary.add_argument(
        "--runs", type=Path, required=True,
    )
    summary.add_argument(
        "--allow-partial", action="store_true",
        help="Process pilot or incomplete experimental records",
    )

    return parser


def require_solvers(variants):
    """Check solver availability before creating result files."""
    for variant in variants:
        try:
            _solver_for(variant)
        except ImportError as exc:
            raise RuntimeError(
                f"ES solver '{variant}' is unavailable. "
                "Integrate and test J's algorithms first."
            ) from exc


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "pilot":
        if args.budget < 1:
            parser.error("--budget must be positive")

        require_solvers((args.variant,))

        filename = (
            f"{args.dataset}_alpha"
            f"{round(args.alpha * 100):03d}_"
            f"{args.variant}_seed{args.seed}_"
            f"eval{args.budget}.jsonl"
        )
        path = RESULTS / "scratch" / filename

        print("Pilot output:", path)

        run_selected(
            path,
            datasets=(args.dataset,),
            alphas=(args.alpha,),
            variants=(args.variant,),
            seeds=(args.seed,),
            budget=args.budget,
            resume=args.resume,
        )

        return

    if args.command == "full":
        if not args.confirm_450:
            parser.error(
                "Full experiment requires --confirm-450"
            )

        config = load_config()

        count = (
            len(config["datasets"])
            * len(config["alphas"])
            * len(config["variants"])
            * len(config["seeds"])
        )

        if count != 450 or config["evaluation_budget"] != 30000:
            raise ValueError(
                "Unexpected experiment configuration"
            )

        require_solvers(config["variants"])

        print("Full experiment: 450 runs")
        print("Evaluation budget: 30000 per run")
        print("Output:", RAW_FILE)

        run_selected(
            RAW_FILE,
            resume=args.resume,
        )

        return

    if args.command == "summarize":
        directory = (
            RESULTS / "scratch" / "reports"
            if args.allow_partial
            else RESULTS
        )

        paths = generate_outputs(
            args.runs,
            directory,
            require_complete=not args.allow_partial,
        )

        for path in paths:
            print("Generated:", path)


if __name__ == "__main__":
    main()
