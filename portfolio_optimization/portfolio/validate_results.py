"""Independent validation of the saved Problem 2 portfolio ES experiments.

Reads the saved run records, the original OR-Library files, the experiment
configuration, the provenance sidecar and the committed summary table, and
recomputes every checked quantity with its own parser and arithmetic. It does
not import the project's data, evaluation, repair, feasibility, experiment or
output modules, never runs an optimizer, and never writes to any result file.

Run from the repository root:
    python -m portfolio_optimization.portfolio.validate_results
    python -m portfolio_optimization.portfolio.validate_results --runs PATH --allow-partial

AI-generated with Claude (Anthropic), 2026-11-24; see docs/ai_usage.md.
"""

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
from bisect import bisect_right
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "portfolio_optimization/configs/experiments.json"
RESULTS = ROOT / "portfolio_optimization/results"
DEFAULT_RUNS = RESULTS / "raw/portfolio_runs.jsonl"
DEFAULT_SUMMARY = RESULTS / "tables/portfolio_summary.csv"

# Feasibility tolerance required by the assignment.
FEASIBILITY_TOL = 1e-8
# Saved return/variance against the independent recomputation. The saved values
# and this module sum the same terms in a different order; observed relative
# differences are of order 1e-16, so 1e-9 only absorbs summation order.
VALUE_REL_TOL = 1e-9
VALUE_ABS_TOL = 1e-15
# Summary statistics and target returns, recomputed from the same inputs.
STAT_REL_TOL = 1e-12
STAT_ABS_TOL = 1e-15
# Allowed rounding when checking that a best-so-far sequence never worsens.
MONOTONE_REL_TOL = 1e-12
# The runner stores the archive history compressed: a change is saved only when
# it differs from the last saved value by more than rel 1e-8 / abs 1e-11. Values
# read back from the history are therefore compared with that tolerance.
HISTORY_REL_TOL = 1e-8
HISTORY_ABS_TOL = 1e-11

POPULATION_VARIANTS = ("mu_plus_lambda", "mu_comma_lambda")
CONVERGENCE_CASE = ("port5", 0.5)
SUMMARY_FIELDS = (
    "case", "dataset", "assets", "alpha", "min_return", "variant", "runs",
    "expected_runs", "valid_runs", "valid_rate", "complete", "best_variance",
    "mean_variance", "sd_variance", "mean_runtime_s",
)


# ---------------------------------------------------------------- data

class Dataset:
    """Asset statistics parsed directly from an OR-Library file."""

    def __init__(self, name, returns, sds, correlation):
        self.name = name
        self.returns = returns
        self.sds = sds
        self.correlation = correlation

    @property
    def n(self):
        return len(self.returns)

    def covariance(self, i, j):
        return self.sds[i] * self.sds[j] * self.correlation[i][j]


def parse_or_library(path, name=None):
    """Parse n, n (mean, sd) pairs and n(n+1)/2 (i, j, correlation) records."""
    tokens = Path(path).read_text(encoding="ascii").split()
    if not tokens:
        raise ValueError(f"{path}: empty file")
    n = int(tokens[0])
    pairs = n * (n + 1) // 2
    if n < 1 or len(tokens) != 1 + 2 * n + 3 * pairs:
        raise ValueError(f"{path}: expected {1 + 2 * n + 3 * pairs} tokens "
                         f"for {n} assets, found {len(tokens)}")

    returns, sds = [], []
    position = 1
    for _ in range(n):
        returns.append(float(tokens[position]))
        sds.append(float(tokens[position + 1]))
        position += 2

    correlation = [[None] * n for _ in range(n)]
    for _ in range(pairs):
        i = int(tokens[position]) - 1
        j = int(tokens[position + 1]) - 1
        value = float(tokens[position + 2])
        position += 3
        if not (0 <= i < n and 0 <= j < n):
            raise ValueError(f"{path}: asset index out of range")
        if correlation[i][j] is not None:
            raise ValueError(f"{path}: duplicate correlation pair "
                             f"({i + 1}, {j + 1})")
        correlation[i][j] = correlation[j][i] = value

    for i in range(n):
        if any(value is None for value in correlation[i]):
            raise ValueError(f"{path}: missing correlation pair for asset {i + 1}")
        if not math.isclose(correlation[i][i], 1.0, abs_tol=1e-12):
            raise ValueError(f"{path}: diagonal correlation of asset {i + 1} is not 1")
    numbers = returns + sds + [v for row in correlation for v in row]
    if not all(math.isfinite(v) for v in numbers) or min(sds) < 0:
        raise ValueError(f"{path}: non-finite value or negative standard deviation")

    return Dataset(name or Path(path).stem, returns, sds, correlation)


def equal_weight_return(returns):
    return math.fsum(returns) / len(returns)


def target_return(returns, alpha):
    """R_min(alpha) = (1 - alpha) * R_eq + alpha * r_max."""
    return (1.0 - alpha) * equal_weight_return(returns) + alpha * max(returns)


def portfolio_return(weights, dataset):
    return math.fsum(w * r for w, r in zip(weights, dataset.returns))


def portfolio_variance(weights, dataset):
    """w^T Sigma w as an exactly rounded sum over the held assets."""
    held = [i for i, w in enumerate(weights) if w != 0.0]
    return math.fsum(
        weights[i] * weights[j] * dataset.covariance(i, j)
        for i in held for j in held
    )


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _close(a, b, rel, abs_tol):
    return math.isclose(a, b, rel_tol=rel, abs_tol=abs_tol)


def _not_worse(value, previous):
    return value <= previous + MONOTONE_REL_TOL * abs(previous)


def _number(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


# ---------------------------------------------------------------- report

class Report:
    """Collected findings; validation never stops at the first problem."""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.facts = {}
        self.records = 0
        self.expected_records = 0
        self.complete = False
        self.final = False
        self.rows = []

    def error(self, where, message):
        self.errors.append(f"{where}: {message}")

    def warning(self, where, message):
        self.warnings.append(f"{where}: {message}")

    @property
    def passed(self):
        return not self.errors


# ---------------------------------------------------------------- records

def expected_settings(config, variant):
    settings = dict(config["one_plus_one"] if variant == "one_plus_one"
                    else config["population"])
    settings["initial_step_size"] = config["initial_step_size"]
    settings["step_size_bounds"] = config["step_size_bounds"]
    return settings


def case_name(dataset, alpha):
    return f"{dataset}_alpha{round(alpha * 100):03d}"


def read_records(path, report):
    records = []
    with open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            if not line.strip():
                report.error(f"line {number}", "blank line in the runs file")
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                report.error(f"line {number}", "invalid JSON")
                continue
            if not isinstance(record, dict):
                report.error(f"line {number}", "record is not a JSON object")
                continue
            records.append((number, record))
    return records


def _check_history(where, record, budget, report):
    """Archive best-so-far: starts at 1, ends at the budget, never worsens."""
    history = record.get("history")
    if not isinstance(history, list) or not history:
        report.error(where, "missing best-so-far history")
        return None
    previous_evaluation, previous_value = 0, math.inf
    for point in history:
        if (not isinstance(point, list) or len(point) != 2
                or type(point[0]) is not int or not _number(point[1])):
            report.error(where, "invalid history point")
            return None
        evaluation, value = point
        if not previous_evaluation < evaluation <= budget:
            report.error(where, "history evaluations are not strictly increasing "
                                "within the budget")
            return None
        if not _not_worse(value, previous_value):
            report.error(where, f"best-so-far history worsened at evaluation {evaluation}")
            return None
        previous_evaluation, previous_value = evaluation, value
    if history[0][0] != 1:
        report.error(where, "history does not start at evaluation 1")
    if history[-1][0] != budget:
        report.error(where, "history does not end at the evaluation budget")
    return history


def _archive_at(history, evaluation):
    steps = [point[0] for point in history]
    index = bisect_right(steps, evaluation) - 1
    return history[index][1] if index >= 0 else math.inf


def _check_population(where, record, variant, history, config, budget, report):
    """Generation checkpoints; plus equals the archive, comma never beats it."""
    points = record.get("population_best")
    if variant not in POPULATION_VARIANTS:
        if points is not None:
            report.error(where, "(1+1)-ES record has a population history")
        return 0, 0
    if not isinstance(points, list) or not points:
        report.error(where, "missing population-best history")
        return 0, 0

    mu, lam = config["population"]["mu"], config["population"]["lambda"]
    first = min(mu, budget)
    expected = list(range(first, first + lam * ((budget - first) // lam) + 1, lam))
    if [p[0] if isinstance(p, list) and len(p) == 2 else None for p in points] != expected:
        report.error(where, "population checkpoints are not the initial population "
                            "and every complete generation")
        return 0, 0

    worsened, previous = 0, math.inf
    for evaluation, value in points:
        if not _number(value):
            report.error(where, "non-finite population-best variance")
            return 0, 0
        if value > previous:
            worsened += 1
        if variant == "mu_plus_lambda" and not _not_worse(value, previous):
            report.error(where, f"plus-selection population best worsened "
                                f"at evaluation {evaluation}")
            return worsened, len(points) - 1
        if history is not None:
            archive = _archive_at(history, evaluation)
            agrees = _close(value, archive, HISTORY_REL_TOL, HISTORY_ABS_TOL)
            # Plus selection keeps the best candidate ever evaluated, so its
            # population best is the archive best. Comma selection can lose it,
            # but can never hold anything better than the archive.
            if variant == "mu_plus_lambda" and not agrees:
                report.error(where, f"plus population best differs from the archive "
                                    f"at evaluation {evaluation}")
                return worsened, len(points) - 1
            if variant == "mu_comma_lambda" and value < archive and not agrees:
                report.error(where, f"comma population best is better than the archive "
                                    f"at evaluation {evaluation}")
                return worsened, len(points) - 1
        previous = value
    return worsened, len(points) - 1


def check_record(where, record, datasets, config, report, stats):
    """Check one saved run; returns its matrix key or None."""
    dataset_name, alpha = record.get("dataset"), record.get("alpha")
    variant, seed = record.get("variant"), record.get("seed")
    if (dataset_name not in datasets or alpha not in config["alphas"]
            or variant not in config["variants"] or type(seed) is not int
            or seed not in config["seeds"]):
        report.error(where, "record lies outside the configured experiment matrix")
        return None
    key = (dataset_name, alpha, variant, seed)
    where = f"{where} {case_name(dataset_name, alpha)} {variant} seed {seed}"
    data = datasets[dataset_name]
    budget = config["evaluation_budget"]
    target = target_return(data.returns, alpha)

    # Identity and recorded parameters.
    if record.get("case") != case_name(dataset_name, alpha):
        report.error(where, "case name does not match dataset and alpha")
    if record.get("assets") != data.n:
        report.error(where, f"asset count {record.get('assets')} != {data.n}")
    if not _number(record.get("min_return")) or not _close(
            record["min_return"], target, STAT_REL_TOL, STAT_ABS_TOL):
        report.error(where, "saved minimum return differs from R_min(alpha)")
    if record.get("settings") != expected_settings(config, variant):
        report.error(where, "recorded ES settings differ from the configuration")
    for field in ("budget", "evaluations"):
        if type(record.get(field)) is not int or record[field] != budget:
            report.error(where, f"{field} is not exactly {budget}")
    if not _number(record.get("runtime_s")) or record["runtime_s"] <= 0:
        report.error(where, "runtime is missing or not positive")
    if type(record.get("valid")) is not bool:
        report.error(where, "missing validity flag")
        return key

    weights = record.get("best_weights")
    if (not isinstance(weights, list) or len(weights) != data.n
            or not all(_number(w) for w in weights)):
        report.error(where, f"best weights must be {data.n} finite numbers")
        return key

    # Constraints, recomputed independently.
    total = math.fsum(weights)
    achieved = portfolio_return(weights, data)
    feasible = (min(weights) >= -FEASIBILITY_TOL
                and abs(total - 1.0) <= FEASIBILITY_TOL
                and achieved >= target - FEASIBILITY_TOL)
    if not record["valid"]:
        stats["invalid"] += 1
        if feasible:
            report.warning(where, "marked invalid although its allocation is feasible")
        return key
    if min(weights) < -FEASIBILITY_TOL:
        report.error(where, f"negative weight {min(weights):.3e}")
    if abs(total - 1.0) > FEASIBILITY_TOL:
        report.error(where, f"weights sum to {total!r}")
    if achieved < target - FEASIBILITY_TOL:
        report.error(where, f"return {achieved!r} below R_min {target!r}")

    # Saved objective values against the recomputation.
    variance = portfolio_variance(weights, data)
    for field, value in (("best_return", achieved), ("best_variance", variance)):
        saved = record.get(field)
        if not _number(saved) or not _close(saved, value, VALUE_REL_TOL, VALUE_ABS_TOL):
            report.error(where, f"saved {field} {saved!r} != recomputed {value!r}")
        elif value != 0:
            stats["max_rel_diff"] = max(stats["max_rel_diff"], abs(saved - value) / abs(value))
    if abs(achieved - target) <= 1e-9:
        stats["active_target"][case_name(dataset_name, alpha)] = (
            stats["active_target"].get(case_name(dataset_name, alpha), 0) + 1)

    # Histories.
    history = _check_history(where, record, budget, report)
    if history is not None and _number(record.get("best_variance")) and not _close(
            history[-1][1], record["best_variance"], VALUE_REL_TOL, VALUE_ABS_TOL):
        report.error(where, "history endpoint differs from the saved best variance")
    worsened, generations = _check_population(
        where, record, variant, history, config, budget, report)
    if variant in POPULATION_VARIANTS:
        stats["worsened"][variant] += worsened
        stats["generations"][variant] += generations
    return key


# ---------------------------------------------------------------- statistics

def summary_rows(observed, datasets, config):
    """Recompute the 45 summary rows from the saved records."""
    rows = []
    for entry in config["datasets"]:
        data = datasets[entry["name"]]
        for alpha in config["alphas"]:
            for variant in config["variants"]:
                group = [observed[(entry["name"], alpha, variant, seed)]
                         for seed in config["seeds"]
                         if (entry["name"], alpha, variant, seed) in observed]
                values = [r["best_variance"] for r in group
                          if r.get("valid") is True and _number(r.get("best_variance"))]
                runtimes = [r["runtime_s"] for r in group if _number(r.get("runtime_s"))]
                rows.append({
                    "case": case_name(entry["name"], alpha),
                    "dataset": entry["name"],
                    "assets": data.n,
                    "alpha": alpha,
                    "min_return": target_return(data.returns, alpha),
                    "variant": variant,
                    "runs": len(group),
                    "expected_runs": len(config["seeds"]),
                    "valid_runs": len(values),
                    "valid_rate": len(values) / len(group) if group else None,
                    "complete": len(group) == len(config["seeds"]),
                    "best_variance": min(values) if values else None,
                    "mean_variance": statistics.fmean(values) if values else None,
                    "sd_variance": statistics.stdev(values) if len(values) >= 2 else None,
                    "mean_runtime_s": statistics.fmean(runtimes) if runtimes else None,
                })
    return rows


def compare_summary(rows, path, report):
    """The saved summary table must equal the statistics recomputed here."""
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != SUMMARY_FIELDS:
            report.error("summary table", f"unexpected columns {reader.fieldnames}")
            return
        saved = list(reader)
    if len(saved) != len(rows):
        report.error("summary table", f"{len(saved)} rows, expected {len(rows)}")
    by_key = {(r["case"], r["variant"]): r for r in saved}
    for row in rows:
        where = f"summary table {row['case']} {row['variant']}"
        line = by_key.get((row["case"], row["variant"]))
        if line is None:
            report.error(where, "row missing")
            continue
        for field in SUMMARY_FIELDS:
            expected, text = row[field], line[field]
            if expected is None:
                ok = text == ""
            elif isinstance(expected, bool):
                ok = text == str(expected)
            elif isinstance(expected, int):
                ok = text == str(expected)
            elif isinstance(expected, float):
                try:
                    ok = _close(float(text), expected, STAT_REL_TOL, STAT_ABS_TOL)
                except ValueError:
                    ok = False
            else:
                ok = text == expected
            if not ok:
                report.error(where, f"{field} is {text!r}, recomputed {expected!r}")


def convergence_curve(records, budget):
    """Mean archive-best variance on the union of all history evaluations."""
    histories = [r["history"] for r in records]
    grid = sorted({1, budget} | {p[0] for h in histories for p in h})
    return grid, [statistics.fmean(_archive_at(h, e) for h in histories) for e in grid]


def check_convergence(observed, rows, config, report):
    """The required port5_alpha050 plot data must be consistent with the table."""
    dataset, alpha = CONVERGENCE_CASE
    if dataset not in {d["name"] for d in config["datasets"]} or alpha not in config["alphas"]:
        return
    finals = {}
    for variant in config["variants"]:
        where = f"convergence {case_name(dataset, alpha)} {variant}"
        records = [observed[(dataset, alpha, variant, seed)] for seed in config["seeds"]
                   if (dataset, alpha, variant, seed) in observed
                   and observed[(dataset, alpha, variant, seed)].get("valid") is True
                   and isinstance(observed[(dataset, alpha, variant, seed)].get("history"), list)]
        if len(records) != len(config["seeds"]):
            report.warning(where, f"{len(records)} of {len(config['seeds'])} valid runs available")
        if not records:
            continue
        grid, means = convergence_curve(records, config["evaluation_budget"])
        if grid[0] != 1 or grid[-1] != config["evaluation_budget"]:
            report.error(where, "curve does not span evaluations 1 to the budget")
        if any(not _not_worse(b, a) for a, b in zip(means, means[1:])):
            report.error(where, "mean archive-best curve is not non-increasing")
        row = next(r for r in rows if r["case"] == case_name(dataset, alpha)
                   and r["variant"] == variant)
        if row["mean_variance"] is not None and not _close(
                means[-1], row["mean_variance"], STAT_REL_TOL, STAT_ABS_TOL):
            report.error(where, "final curve value differs from the summary mean")
        finals[variant] = (means[-1], len(grid))
    report.facts["convergence"] = finals


def check_metadata(path, config, config_path, root, final, report):
    """Provenance sidecar: actual ES runs of this configuration and data."""
    if not Path(path).is_file():
        (report.error if final else report.warning)(
            "metadata", f"provenance sidecar {Path(path).name} not found")
        return
    try:
        metadata = json.loads(Path(path).read_text(encoding="utf-8"))
        identity = metadata["identity"]
    except (json.JSONDecodeError, KeyError, TypeError):
        report.error("metadata", "unreadable provenance sidecar")
        return
    selection = identity.get("selection", {})
    expected = {
        "datasets": [d["name"] for d in config["datasets"]],
        "alphas": config["alphas"], "variants": config["variants"],
        "seeds": config["seeds"], "budget": config["evaluation_budget"],
    }
    for field, value in expected.items():
        if selection.get(field) != value:
            (report.error if final else report.warning)(
                "metadata", f"selected {field} {selection.get(field)!r} is not the "
                            f"full configured matrix {value!r}")
    if identity.get("solver_mode") != "actual_es":
        report.error("metadata", f"solver mode is {identity.get('solver_mode')!r}, "
                                 "not the actual ES solvers")
    if identity.get("git_source_dirty") is not False:
        report.warning("metadata", "records were not produced from a clean source tree")
    if identity.get("config_sha256") != sha256_file(config_path):
        report.error("metadata", "configuration file changed since the runs")
    for entry in config["datasets"]:
        if identity.get("dataset_sha256", {}).get(entry["name"]) != sha256_file(root / entry["path"]):
            report.error("metadata", f"{entry['name']} data file changed since the runs")


# ---------------------------------------------------------------- driver

def validate(runs_path=DEFAULT_RUNS, summary_path=DEFAULT_SUMMARY,
             config_path=CONFIG_PATH, root=ROOT, metadata_path=None,
             allow_partial=False):
    """Validate a runs file; returns a Report. Nothing is written."""
    report = Report()
    root, runs_path = Path(root), Path(runs_path)
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    before = sha256_file(runs_path)

    datasets = {}
    for entry in config["datasets"]:
        data = parse_or_library(root / entry["path"], entry["name"])
        if data.n != entry["assets"]:
            report.error(entry["name"], f"file has {data.n} assets, configuration {entry['assets']}")
        datasets[entry["name"]] = data

    matrix = {(d["name"], a, v, s) for d in config["datasets"] for a in config["alphas"]
              for v in config["variants"] for s in config["seeds"]}
    report.expected_records = len(matrix)
    stats = {"invalid": 0, "max_rel_diff": 0.0, "active_target": {},
             "worsened": {v: 0 for v in POPULATION_VARIANTS},
             "generations": {v: 0 for v in POPULATION_VARIANTS}}

    observed = {}
    for number, record in read_records(runs_path, report):
        report.records += 1
        key = check_record(f"line {number}", record, datasets, config, report, stats)
        if key is None:
            continue
        if key in observed:
            report.error(f"line {number}", f"duplicate record for {key}")
            continue
        observed[key] = record

    missing = sorted(matrix - set(observed))
    report.complete = not missing and report.records == len(matrix)
    if missing:
        message = (f"{len(missing)} of {len(matrix)} configured runs are missing, "
                   f"first {missing[0]}")
        (report.warning if allow_partial else report.error)("coverage", message)

    report.rows = summary_rows(observed, datasets, config)
    if summary_path is not None:
        if Path(summary_path).is_file():
            compare_summary(report.rows, summary_path, report)
        else:
            report.error("summary table", f"{summary_path} not found")
    check_convergence(observed, report.rows, config, report)
    metadata_path = (runs_path.with_suffix(".metadata.json")
                     if metadata_path is None else Path(metadata_path))
    check_metadata(metadata_path, config, config_path, root, not allow_partial, report)

    if sha256_file(runs_path) != before:
        report.error("runs file", "changed while it was being validated")

    report.facts.update(
        invalid_records=stats["invalid"],
        max_relative_value_difference=stats["max_rel_diff"],
        return_target_active=stats["active_target"],
        population_best_worsened=stats["worsened"],
        population_generations=stats["generations"],
    )
    report.final = report.complete and report.passed and not allow_partial
    return report


def format_report(report, runs_path):
    lines = ["Portfolio ES result validation", f"Runs file: {runs_path}",
             f"Records: {report.records} of {report.expected_records} expected "
             f"({'complete' if report.complete else 'INCOMPLETE'})"]
    facts = report.facts
    if "invalid_records" in facts:
        lines.append(f"Records marked invalid: {facts['invalid_records']}")
        lines.append("Largest relative difference, saved vs recomputed return/variance: "
                     f"{facts['max_relative_value_difference']:.2e}")
        worse, gens = facts["population_best_worsened"], facts["population_generations"]
        for variant in POPULATION_VARIANTS:
            lines.append(f"{variant}: population best worsened in "
                         f"{worse[variant]:,} of {gens[variant]:,} generations")
    for variant, (final, points) in facts.get("convergence", {}).items():
        lines.append(f"Convergence {case_name(*CONVERGENCE_CASE)} {variant}: "
                     f"{points} points, final mean variance {final:.6e}")
    lines.append(f"Summary rows recomputed: {len(report.rows)}")
    for kind, items in (("WARNING", report.warnings), ("ERROR", report.errors)):
        for item in items[:50]:
            lines.append(f"{kind} {item}")
        if len(items) > 50:
            lines.append(f"... {len(items) - 50} more {kind.lower()}s")
    if report.final:
        lines.append(f"Result: PASSED - final {report.expected_records}-run experiment")
    elif report.passed:
        lines.append("Result: PASSED for a PARTIAL record set - not the final experiment")
    else:
        lines.append(f"Result: FAILED with {len(report.errors)} error(s)")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Independently validate saved portfolio ES runs")
    parser.add_argument("--runs", type=Path, default=DEFAULT_RUNS)
    parser.add_argument("--summary", type=Path, default=None,
                        help="summary CSV to compare (default: the committed table, "
                             "none with --allow-partial)")
    parser.add_argument("--allow-partial", action="store_true",
                        help="validate a pilot or incomplete file; never reported as final")
    args = parser.parse_args(argv)
    summary = args.summary
    if summary is None and not args.allow_partial:
        summary = DEFAULT_SUMMARY
    report = validate(args.runs, summary_path=summary, allow_partial=args.allow_partial)
    print(format_report(report, args.runs))
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
