"""Reproduce the Bees Algorithm settings pilot without touching official results.

AI-generated with OpenAI ChatGPT and intended for group inspection;
see docs/ai_usage.md. Run from the repository root:
    python -m bees_optimization.pilot.run_pilot
    python -m bees_optimization.pilot.run_pilot --smoke

All output is written under the git-ignored bees_optimization/results/scratch/.
"""

import argparse
import csv
import json
import statistics
import time
from collections import defaultdict
from pathlib import Path

from bees_optimization.bees.experiments import (
    load_config,
    run_continuous_case,
    run_tsp_case,
)
from bees_optimization.bees.tsplib import (
    create_distance_matrix,
    load_tsplib,
    validate_tsplib,
)

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT / "bees_optimization" / "results" / "scratch"
SEEDS = (100, 101, 102, 103, 104)
BUDGET = 30_000
SETTINGS = {
    "A": (30, 10, 3, 10, 5),
    "B": (10, 3, 1, 10, 5),
    "C": (6, 2, 1, 5, 3),
}
SETTING_KEYS = (
    "n_scouts", "n_selected", "n_elite",
    "n_elite_recruits", "n_other_recruits",
)


def parameters(setting):
    return dict(zip(SETTING_KEYS, SETTINGS[setting]))


def save_csv(path, rows, fields):
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def summarise(records, output_dir, budget, seeds):
    tsp = defaultdict(list)
    cont = defaultdict(list)
    for rec in records:
        setting = rec["pilot_setting"]
        if rec["part"] == "tsp":
            tsp[(setting, rec["neighborhood"], rec["instance"])].append(rec)
        else:
            cont[(setting, rec["function"], rec["dimension"])].append(rec)

    tsp_rows = []
    for (setting, neighborhood, instance), runs in sorted(tsp.items()):
        tsp_rows.append({
            "setting": setting, "neighborhood": neighborhood,
            "instance": instance, "runs": len(runs),
            "mean_gap_pct": statistics.fmean(r["gap_pct"] for r in runs),
            "mean_length": statistics.fmean(r["best_length"] for r in runs),
        })
    save_csv(output_dir / "tsp_by_instance.csv", tsp_rows,
             ("setting", "neighborhood", "instance", "runs", "mean_gap_pct", "mean_length"))

    cont_rows = []
    for (setting, function, dimension), runs in sorted(cont.items()):
        cont_rows.append({
            "setting": setting, "function": function,
            "dimension": dimension, "runs": len(runs),
            "mean_final_error": statistics.fmean(r["best_value"] for r in runs),
        })
    save_csv(output_dir / "continuous_by_case.csv", cont_rows,
             ("setting", "function", "dimension", "runs", "mean_final_error"))

    lines = [
        "# Bees Algorithm setting-selection pilot — reproducible output", "",
        f"Seeds: {', '.join(map(str, seeds))}. Evaluation budget: {budget} per run.",
        "All entries below were computed from the pilot-run JSONL in this folder.", "",
        "## TSP: mean gap (%) averaged equally across tested instances", "",
        "| Setting | Swap | Segment reversal |",
        "| --- | ---: | ---: |",
    ]
    for setting in SETTINGS:
        means = {}
        for neighborhood in ("swap", "segment_reversal"):
            values = [r["mean_gap_pct"] for r in tsp_rows
                      if r["setting"] == setting and r["neighborhood"] == neighborhood]
            if values:
                means[neighborhood] = f"{statistics.fmean(values):.1f}"
            else:
                means[neighborhood] = "n/a"
        lines.append(f"| {setting} | {means['swap']} | {means['segment_reversal']} |")

    lines += ["", "## Continuous: lowest mean error per function and dimension", "",
              "| Function | D | Best setting (descriptive only) |", "| --- | ---: | --- |"]
    keys = sorted(set((r["function"], r["dimension"]) for r in cont_rows))
    for function, dimension in keys:
        rows = [r for r in cont_rows if (r["function"], r["dimension"]) == (function, dimension)]
        winner = min(rows, key=lambda r: (r["mean_final_error"], r["setting"]))
        lines.append(f"| {function} | {dimension} | {winner['setting']} |")

    lines += [
        "", "This pilot is descriptive. It does not establish statistical",
        "significance or a universally best Bees Algorithm setting.", "",
    ]
    (output_dir / "pilot_summary.md").write_text("\n".join(lines), encoding="utf-8")


def run(output_dir, smoke=False):
    seeds = SEEDS[:1] if smoke else SEEDS
    budget = 100 if smoke else BUDGET
    tsp_config = load_config("tsp")
    continuous_config = load_config("continuous")
    instances = tsp_config["instances"][:1] if smoke else tsp_config["instances"]
    neighborhoods = ("segment_reversal",) if smoke else tuple(tsp_config["neighborhoods"])
    functions = (continuous_config["functions"][0]["name"],) if smoke else tuple(
        f["name"] for f in continuous_config["functions"]
    )
    dimensions = (10,) if smoke else tuple(continuous_config["dimensions"])

    # Never write to official raw/, configs/, datasets/, or committed figures.
    scratch = SCRATCH.resolve()
    target = output_dir.resolve()
    if not target.is_relative_to(scratch) or target == scratch:
        raise ValueError("Pilot output must be a new folder inside results/scratch/")
    target.mkdir(parents=True, exist_ok=False)
    records = []
    started = time.perf_counter()
    raw = target / "pilot_runs.jsonl"
    with raw.open("x", encoding="utf-8", newline="\n") as stream:
        for setting in SETTINGS:
            options = parameters(setting)
            for instance in instances:
                metadata, coordinates = load_tsplib(ROOT / instance["path"])
                validate_tsplib(metadata, coordinates)
                if len(coordinates) != instance["cities"]:
                    raise ValueError("Unexpected number of TSP cities")
                distance_matrix = create_distance_matrix(coordinates)
                for neighborhood in neighborhoods:
                    for seed in seeds:
                        rec = run_tsp_case(instance, distance_matrix, neighborhood,
                                           seed, options, budget)
                        rec.update(pilot_setting=setting, part="tsp")
                        records.append(rec)
                        stream.write(json.dumps(rec, allow_nan=False) + "\n")
                        print(f"[{len(records)}] TSP {setting} {instance['name']} "
                              f"{neighborhood} seed {seed}: gap {rec['gap_pct']:.2f}%", flush=True)
            for function in functions:
                for dimension in dimensions:
                    for seed in seeds:
                        rec = run_continuous_case(function, dimension, seed,
                                                  options, budget)
                        rec.update(pilot_setting=setting, part="continuous")
                        records.append(rec)
                        stream.write(json.dumps(rec, allow_nan=False) + "\n")
                        print(f"[{len(records)}] CONT {setting} {function} "
                              f"D={dimension} seed {seed}: {rec['best_value']:.6g}", flush=True)

    expected = len(SETTINGS) * len(seeds) * (
        len(instances) * len(neighborhoods) + len(functions) * len(dimensions)
    )
    if len(records) != expected or any(r["evaluations"] != budget for r in records):
        raise AssertionError("Pilot results are incomplete or have incorrect budgets")
    summarise(records, target, budget, seeds)
    (target / "pilot_metadata.json").write_text(json.dumps({
        "smoke": smoke,
        "seeds": list(seeds),
        "budget": budget,
        "settings": {k: parameters(k) for k in SETTINGS},
        "cases": {"tsp_instances": [i["name"] for i in instances],
                  "neighborhoods": list(neighborhoods),
                  "continuous_functions": list(functions),
                  "continuous_dimensions": list(dimensions)},
        "runs": expected,
        "elapsed_seconds": time.perf_counter() - started,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Pilot complete: {expected} runs saved in {target}")
    print((target / "pilot_summary.md").read_text(encoding="utf-8"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true",
                        help="Use one seed, one instance, one function and 100 evaluations")
    parser.add_argument("--out", type=Path,
                        help="New output directory under bees_optimization/results/scratch/")
    args = parser.parse_args(argv)
    default = SCRATCH / ("ba_pilot_smoke" if args.smoke else "ba_pilot_full")
    run(default if args.out is None else args.out, smoke=args.smoke)


if __name__ == "__main__":
    main()
