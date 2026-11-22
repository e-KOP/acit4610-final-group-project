
"""Independent validation of the saved Problem 1 experiments.

Checks all TSP and continuous BA runs without rerunning the optimizer
or modifying any saved experiment data.

Run from the repository root:
    python -m bees_optimization.bees.validate_results

AI-assisted implementation; see docs/ai_usage.md.
"""

import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BEES = ROOT / "bees_optimization"
RAW = BEES / "results" / "raw"
TABLES = BEES / "results" / "tables"

SETTING_NAMES = {
    "scout_population": "n_scouts",
    "selected_sites": "n_selected",
    "elite_sites": "n_elite",
    "elite_recruits": "n_elite_recruits",
    "other_site_recruits": "n_other_recruits",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def close(actual, expected):
    return math.isclose(
        float(actual), float(expected),
        rel_tol=1e-10, abs_tol=1e-9
    )


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path):
    with path.open(encoding="utf-8") as file:
        return [
            json.loads(line)
            for line in file
            if line.strip()
        ]


def expected_settings(config):
    return {
        argument: config["ba"][field]
        for field, argument in SETTING_NAMES.items()
    }


def load_coordinates(path):
    """Read TSPLIB coordinates independently of the project's parser."""
    coordinates = {}
    reading = False

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if line == "NODE_COORD_SECTION":
            reading = True
            continue

        if not reading:
            continue

        if line == "EOF":
            break

        if not line:
            continue

        fields = line.split()
        require(len(fields) == 3, "Invalid TSPLIB coordinate row")

        city = int(fields[0])
        require(city not in coordinates, "Duplicate TSPLIB city")

        coordinates[city] = (
            float(fields[1]),
            float(fields[2]),
        )

    require(bool(coordinates), "No TSPLIB coordinates found")
    return coordinates


def independent_tour_length(tour, coordinates):
    """Calculate EUC_2D length, including the return to city 1."""
    total = 0

    for i, city in enumerate(tour):
        next_city = tour[(i + 1) % len(tour)]

        x1, y1 = coordinates[city]
        x2, y2 = coordinates[next_city]

        distance = math.hypot(x2 - x1, y2 - y1)
        total += math.floor(distance + 0.5)

    return total


def independent_objective(name, vector):
    """Evaluate the mathematical benchmark definitions independently."""
    n = len(vector)
    squares = sum(x * x for x in vector)

    if name == "sphere":
        return squares

    if name == "rosenbrock":
        return sum(
            100 * (vector[i + 1] - vector[i] ** 2) ** 2
            + (1 - vector[i]) ** 2
            for i in range(n - 1)
        )

    if name == "rastrigin":
        return 10 * n + sum(
            x * x - 10 * math.cos(2 * math.pi * x)
            for x in vector
        )

    if name == "ackley":
        mean_cos = sum(
            math.cos(2 * math.pi * x)
            for x in vector
        ) / n

        return (
            -20 * math.exp(-0.2 * math.sqrt(squares / n))
            - math.exp(mean_cos)
            + 20 + math.e
        )

    raise ValueError(f"Unknown function: {name}")


def validate_history(record, scouts, budget, final_value):
    """Verify the compressed best-so-far trajectory."""
    history = record["history"]

    require(
        isinstance(history, list) and len(history) >= 2,
        "Missing or invalid history"
    )

    require(
        history[0][0] == scouts,
        "History starts at the wrong evaluation"
    )
    require(
        close(history[0][1], record["initial_best"]),
        "Initial history value mismatch"
    )
    require(
        history[-1][0] == budget,
        "History does not end at the evaluation budget"
    )
    require(
        close(history[-1][1], final_value),
        "Final history value mismatch"
    )

    previous_evaluation = 0
    previous_best = float("inf")

    for evaluation, best in history:
        require(
            type(evaluation) is int
            and previous_evaluation < evaluation <= budget,
            "History evaluation indices are invalid"
        )
        require(
            isinstance(best, (int, float))
            and math.isfinite(best),
            "Non-finite history objective"
        )
        require(
            best <= previous_best + 1e-9,
            "Best-so-far history increases"
        )

        previous_evaluation = evaluation
        previous_best = best


def validate_tsp(record, instance, coordinates):
    """Verify a saved tour using independently computed distances."""
    n = instance["cities"]
    tour = record["best_tour"]

    require(
        isinstance(tour, list)
        and len(tour) == n
        and tour[0] == 1
        and all(type(city) is int for city in tour)
        and set(tour) == set(range(1, n + 1)),
        "Invalid TSP tour"
    )

    require(
        record["cities"] == n
        and record["optimum"] == instance["optimal_length"],
        "Incorrect instance metadata"
    )

    require(
        set(coordinates) == set(range(1, n + 1)),
        "Invalid TSPLIB city identifiers"
    )

    calculated = independent_tour_length(tour, coordinates)

    require(
        calculated == record["best_length"],
        f"Tour length mismatch: {calculated} vs {record['best_length']}"
    )

    gap = 100 * (
        calculated - instance["optimal_length"]
    ) / instance["optimal_length"]

    require(
        close(gap, record["gap_pct"]),
        "Incorrect percentage gap"
    )

    return calculated


def validate_continuous(record, function):
    """Verify solution bounds and independently evaluate the objective."""
    vector = record["best_vector"]
    dimension = record["dimension"]
    lower, upper = function["bounds"]

    require(
        isinstance(vector, list)
        and len(vector) == dimension
        and dimension in (10, 30),
        "Incorrect continuous vector dimension"
    )

    require(
        all(
            isinstance(x, (int, float))
            and math.isfinite(x)
            and lower <= x <= upper
            for x in vector
        ),
        "Continuous vector violates bounds"
    )

    require(
        record["bounds"] == function["bounds"],
        "Incorrect recorded bounds"
    )

    value = independent_objective(record["function"], vector)

    require(
        close(value, record["best_value"]),
        f"Objective mismatch: {value} vs {record['best_value']}"
    )

    return value


def validate_runs(records, config, kind):
    """Validate every record and enforce complete case/seed coverage."""
    settings = expected_settings(config)
    budget = config["evaluation_budget"]
    scouts = settings["n_scouts"]

    if kind == "tsp":
        instances = {
            item["name"]: item
            for item in config["instances"]
        }

        expected = {
            (name, move, seed)
            for name in instances
            for move in config["neighborhoods"]
            for seed in config["seeds"]
        }

        coordinates = {
            name: load_coordinates(ROOT / item["path"])
            for name, item in instances.items()
        }

    else:
        functions = {
            item["name"]: item
            for item in config["functions"]
        }

        expected = {
            (name, dimension, seed)
            for name in functions
            for dimension in config["dimensions"]
            for seed in config["seeds"]
        }

    require(
        len(expected) == config["expected_runs"],
        f"{kind}: incorrect expected run count in configuration"
    )

    seen = set()
    groups = defaultdict(list)

    for index, record in enumerate(records, start=1):
        try:
            if kind == "tsp":
                key = (
                    record["instance"],
                    record["neighborhood"],
                    record["seed"]
                )

                require(key in expected, "Unexpected TSP case or seed")

                value = validate_tsp(
                    record,
                    instances[record["instance"]],
                    coordinates[record["instance"]]
                )

            else:
                key = (
                    record["function"],
                    record["dimension"],
                    record["seed"]
                )

                require(key in expected, "Unexpected continuous case or seed")

                value = validate_continuous(
                    record,
                    functions[record["function"]]
                )

            require(key not in seen, "Duplicate case/seed")
            seen.add(key)

            require(
                record["settings"] == settings,
                "BA settings mismatch"
            )
            require(
                record["budget"] == budget
                and record["evaluations"] == budget,
                "Incorrect evaluation count"
            )
            require(
                math.isfinite(record["runtime_s"])
                and record["runtime_s"] >= 0,
                "Invalid runtime"
            )
            require(
                value <= record["initial_best"] + 1e-9,
                "Final value is worse than initial best"
            )

            validate_history(record, scouts, budget, value)
            groups[key[:2]].append(record)

        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise ValueError(
                f"{kind} record {index}: {error}"
            ) from error

    require(
        seen == expected,
        f"{kind}: missing {len(expected - seen)} case/seed combinations"
    )
    require(
        len(records) == len(expected),
        f"{kind}: unexpected number of records"
    )

    return groups


def validate_table(path, groups, kind):
    """Recompute full-precision CSV statistics from raw run records."""
    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    seen = set()

    for row in rows:
        if kind == "tsp":
            key = (row["instance"], row["neighborhood"])
            objective = "best_length"
        else:
            key = (row["function"], int(row["dimension"]))
            objective = "best_value"

        require(key in groups, f"Unknown {kind} summary group")
        require(key not in seen, f"Duplicate {kind} summary row")

        seen.add(key)
        records = groups[key]
        values = [r[objective] for r in records]

        expected = {
            "runs": len(records),
            "best": min(values),
            "mean": statistics.mean(values),
            "sd": statistics.stdev(values),
            "mean_initial_best": statistics.mean(
                r["initial_best"] for r in records
            ),
            "mean_runtime_s": statistics.mean(
                r["runtime_s"] for r in records
            ),
        }

        if kind == "tsp":
            expected.update({
                "cities": records[0]["cities"],
                "optimum": records[0]["optimum"],
                "mean_gap_pct": statistics.mean(
                    r["gap_pct"] for r in records
                ),
            })

        for column, calculated in expected.items():
            require(
                close(row[column], calculated),
                f"{kind} {key}: incorrect {column}"
            )

    require(
        seen == set(groups),
        f"{kind}: summary table has missing groups"
    )


def validate_metadata(tsp_config, continuous_config):
    """Check saved configurations and original TSPLIB file hashes."""
    metadata = read_json(RAW / "metadata.json")

    require(
        metadata["configs"]["tsp"] == tsp_config,
        "TSP provenance configuration differs"
    )
    require(
        metadata["configs"]["continuous"] == continuous_config,
        "Continuous provenance configuration differs"
    )

    for relative_path, expected_hash in metadata["tsplib_sha256"].items():
        actual_hash = hashlib.sha256(
            (ROOT / relative_path).read_bytes()
        ).hexdigest()

        require(
            actual_hash == expected_hash,
            f"Dataset checksum mismatch: {relative_path}"
        )


def main():
    try:
        tsp_config = read_json(BEES / "configs" / "tsp.json")
        continuous_config = read_json(
            BEES / "configs" / "continuous.json"
        )

        tsp_records = read_jsonl(RAW / "tsp_runs.jsonl")
        continuous_records = read_jsonl(
            RAW / "continuous_runs.jsonl"
        )

        tsp_groups = validate_runs(
            tsp_records, tsp_config, "tsp"
        )
        continuous_groups = validate_runs(
            continuous_records, continuous_config, "continuous"
        )

        validate_table(
            TABLES / "tsp_summary.csv", tsp_groups, "tsp"
        )
        validate_table(
            TABLES / "continuous_summary.csv",
            continuous_groups,
            "continuous"
        )

        validate_metadata(tsp_config, continuous_config)

    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"FAIL: {error}")
        return 1

    print("=" * 55)
    print("ACIT4610 - PROBLEM 1 EXPERIMENT VALIDATION")
    print("=" * 55)
    print(f"TSP runs validated:        {len(tsp_records)}")
    print(f"Continuous runs validated: {len(continuous_records)}")
    print(f"TSP groups validated:      {len(tsp_groups)}")
    print(f"Continuous groups:         {len(continuous_groups)}")
    print("Evaluation budget:         30,000 per run")
    print("Objectives:                independently recomputed")
    print("Convergence histories:     verified")
    print("Summary statistics:        verified")
    print("Dataset checksums:         verified")
    print("=" * 55)
    print("PASS: All Problem 1 experimental results are consistent.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
