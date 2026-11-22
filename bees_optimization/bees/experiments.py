"""Run the Problem 1 experiments and save raw per-run records.

AI-generated with Claude (Anthropic), 2026-11-20, built step by step with and
reviewed by Jakob Andreas Amtedal; see docs/ai_usage.md.

Run from the repository root:
    python -m bees_optimization.bees.experiments all        # full set: 120 TSP + 80 continuous
    python -m bees_optimization.bees.experiments tsp --instances berlin52 \
        --neighborhoods segment_reversal --seeds 0          # one run (saved to results/scratch)
"""
import json
import time
from pathlib import Path

from .algorithm import bees_algorithm
from .tsplib import (
    calculate_tour_length, create_distance_matrix, load_tsplib,
    validate_tour, validate_tsplib,
)

from .continuous import continuous_bees
from .functions import BENCHMARKS

PACKAGE_DIR = Path(__file__).resolve().parents[1]      # bees_optimization/
REPO_ROOT = PACKAGE_DIR.parent
CONFIG_DIR = PACKAGE_DIR / "configs"

# config field name -> keyword argument of bees_algorithm / continuous_bees
SETTING_NAMES = {
    "scout_population": "n_scouts",
    "selected_sites": "n_selected",
    "elite_sites": "n_elite",
    "elite_recruits": "n_elite_recruits",
    "other_site_recruits": "n_other_recruits",
}


def load_config(name):
    """Read configs/<name>.json."""
    return json.loads((CONFIG_DIR / f"{name}.json").read_text(encoding="utf-8"))


def ba_settings(config):
    """Turn the config's "ba" block into keyword arguments; refuse missing values."""
    settings = {}
    for field, keyword in SETTING_NAMES.items():
        value = config["ba"].get(field)
        if type(value) is not int:
            raise ValueError(f"BA setting '{field}' is not set in the config")
        settings[keyword] = value
    return settings


def compress_history(history):
    """Keep only the evaluations where best-so-far changed, plus the first and last.

    The search stores best-so-far after every evaluation (30,000 points per run).
    Best-so-far only changes when something better is found, so the change
    points describe exactly the same curve in far fewer entries.
    """
    kept = [list(history[0])]
    for evaluation, value in history[1:]:
        if value != kept[-1][1]:
            kept.append([evaluation, value])
    if kept[-1][0] != history[-1][0]:
        kept.append(list(history[-1]))
    return kept


def run_tsp_case(instance, matrix, neighborhood, seed, settings, budget):
    """Do one TSP run, check it, and return it as a record (a dict)."""
    start = time.perf_counter()
    result = bees_algorithm(matrix, neighborhood, seed,
                            max_evaluations=budget, **settings)
    runtime = time.perf_counter() - start

    # Check the run before trusting it
    tour = result["best_tour"]
    validate_tour(tour, instance["cities"])
    length = calculate_tour_length(tour, matrix)
    if length != result["best_length"] or result["evaluations"] != budget:
        raise RuntimeError(f"Inconsistent result: {instance['name']} {neighborhood} seed {seed}")

    optimum = instance["optimal_length"]
    return {
        "instance": instance["name"],
        "cities": instance["cities"],
        "optimum": optimum,
        "neighborhood": neighborhood,
        "seed": seed,
        "settings": settings,
        "budget": budget,
        "evaluations": result["evaluations"],
        "initial_best": result["initial_best"],
        "best_length": length,
        "gap_pct": 100 * (length - optimum) / optimum,
        "runtime_s": runtime,
        "best_tour": tour,
        "history": compress_history(result["history"]),
    }



def run_tsp(output_dir, seeds=None, instances=None, neighborhoods=None):
    """Run the configured TSP cases (or a subset) and write tsp_runs.jsonl."""
    config = load_config("tsp")
    settings = ba_settings(config)
    seeds = config["seeds"] if seeds is None else seeds
    budget = config["evaluation_budget"]
    neighborhoods = config["neighborhoods"] if neighborhoods is None else neighborhoods
    names = [i["name"] for i in config["instances"]]
    if instances is not None and not set(instances) <= set(names):
        raise ValueError(f"Unknown instance in {instances}; choose from {names}")
    instances = [i for i in config["instances"] if instances is None or i["name"] in instances]

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "tsp_runs.jsonl"

    total = len(instances) * len(neighborhoods) * len(seeds)
    done = 0
    with path.open("w", encoding="utf-8") as out:
        for instance in instances:
            # Load each map once, then reuse its distance matrix for all 20 runs
            metadata, coordinates = load_tsplib(REPO_ROOT / instance["path"])
            validate_tsplib(metadata, coordinates)
            if len(coordinates) != instance["cities"]:
                raise ValueError(f"{instance['name']}: unexpected number of cities")
            matrix = create_distance_matrix(coordinates)

            for neighborhood in neighborhoods:
                for seed in seeds:
                    record = run_tsp_case(instance, matrix, neighborhood,
                                          seed, settings, budget)
                    out.write(json.dumps(record) + "\n")
                    done += 1
                    print(f"[TSP {done:3}/{total}] {instance['name']:8} "
                          f"{neighborhood:16} seed {seed}: {record['best_length']} "
                          f"(gap {record['gap_pct']:.2f}%), {record['runtime_s']:.2f} s")
    return path

def run_continuous_case(function, dimension, seed, settings, budget):
    """Do one continuous run, check it, and return it as a record (a dict)."""
    start = time.perf_counter()
    result = continuous_bees(function, dimension, seed,
                             max_evaluations=budget, **settings)
    runtime = time.perf_counter() - start

    # Check the run before trusting it
    benchmark = BENCHMARKS[function]
    vector = result["best_vector"]
    low, high = benchmark.bounds
    if (len(vector) != dimension
            or not all(low <= v <= high for v in vector)
            or benchmark.objective(vector) != result["best_value"]
            or result["evaluations"] != budget):
        raise RuntimeError(f"Inconsistent result: {function} D={dimension} seed {seed}")

    return {
        "function": function,
        "dimension": dimension,
        "bounds": list(benchmark.bounds),
        "seed": seed,
        "settings": settings,
        "budget": budget,
        "evaluations": result["evaluations"],
        "initial_best": result["initial_best"],
        "best_value": result["best_value"],
        "runtime_s": runtime,
        "best_vector": vector,
        "history": compress_history(result["history"]),
    }


def run_continuous(output_dir, seeds=None, functions=None, dimensions=None):
    """Run the configured continuous cases (or a subset) and write continuous_runs.jsonl."""
    config = load_config("continuous")
    settings = ba_settings(config)
    seeds = config["seeds"] if seeds is None else seeds
    budget = config["evaluation_budget"]
    dimensions = config["dimensions"] if dimensions is None else dimensions
    names = [f["name"] for f in config["functions"]]
    if functions is not None and not set(functions) <= set(names):
        raise ValueError(f"Unknown function in {functions}; choose from {names}")
    functions = [n for n in names if functions is None or n in functions]

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "continuous_runs.jsonl"

    total = len(functions) * len(dimensions) * len(seeds)
    done = 0
    with path.open("w", encoding="utf-8") as out:
        for function in functions:
            for dimension in dimensions:
                for seed in seeds:
                    record = run_continuous_case(function, dimension, seed,
                                                 settings, budget)
                    out.write(json.dumps(record) + "\n")
                    done += 1
                    print(f"[CONT {done:2}/{total}] {function:10} D={dimension:2} "
                          f"seed {seed}: {record['best_value']:.6g}, "
                          f"{record['runtime_s']:.2f} s")
    return path

def write_metadata(output_dir, command):
    """Record what produced the raw files: command, code version, environment, inputs."""
    import hashlib
    import platform
    import subprocess
    import sys
    from datetime import datetime, timezone

    try:
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
                                  capture_output=True, text=True, check=True).stdout.strip()
        changed = subprocess.run(["git", "status", "--porcelain", "--",
                                  "bees_optimization/bees", "bees_optimization/configs"],
                                 cwd=REPO_ROOT, capture_output=True, text=True,
                                 check=True).stdout.strip()
        if changed:
            revision += "-modified"   # code or configs differ from the commit
    except (OSError, subprocess.CalledProcessError):
        revision = "unknown"

    checksums = {
        i["path"]: hashlib.sha256((REPO_ROOT / i["path"]).read_bytes()).hexdigest()
        for i in load_config("tsp")["instances"]
    }
    metadata = {
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "command": command,
        "source_revision": revision,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "runtime_scope": "wall-clock time of the search call only; data loading excluded; runs sequential",
        "history_format": "[evaluation, best-so-far] at every change, plus the first and last evaluation",
        "configs": {name: load_config(name) for name in ("tsp", "continuous")},
        "tsplib_sha256": checksums,
    }
    path = Path(output_dir) / "metadata.json"
    path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return path

def main(argv=None):
    import argparse
    import sys

    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(prog="python -m bees_optimization.bees.experiments",
                                     description="Run the Problem 1 Bees Algorithm experiments.")
    parser.add_argument("part", choices=("tsp", "continuous", "all"))
    parser.add_argument("--seeds", type=int, nargs="+", help="override the configured seeds")
    parser.add_argument("--instances", nargs="+", help="TSP: only these instances")
    parser.add_argument("--neighborhoods", nargs="+", choices=("swap", "segment_reversal"),
                        help="TSP: only these moves")
    parser.add_argument("--functions", nargs="+", help="continuous: only these functions")
    parser.add_argument("--dimensions", type=int, nargs="+", choices=(10, 30),
                        help="continuous: only these dimensions")
    args = parser.parse_args(argv)

    # A subset must never overwrite the saved full experiment.
    partial = any(v is not None for v in (args.seeds, args.instances, args.neighborhoods,
                                          args.functions, args.dimensions))
    output_dir = PACKAGE_DIR / "results" / ("scratch" if partial else "raw")
    output_dir.mkdir(parents=True, exist_ok=True)

    start = time.perf_counter()
    if args.part in ("tsp", "all"):
        run_tsp(output_dir, args.seeds, args.instances, args.neighborhoods)
    if args.part in ("continuous", "all"):
        run_continuous(output_dir, args.seeds, args.functions, args.dimensions)
    write_metadata(output_dir, "python -m bees_optimization.bees.experiments " + " ".join(argv))
    print(f"Done in {time.perf_counter() - start:.0f} s. Results in {output_dir}")


if __name__ == "__main__":
    main()