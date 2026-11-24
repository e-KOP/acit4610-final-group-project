"""Tests for the independent portfolio result validator.

Synthetic experiments use the three-asset example from the assignment
(returns 2%, 6%, 10%; standard deviations 10%, 20%, 30%; zero correlation), so
every expected value can be calculated by hand. The final test validates the
committed 450-run experiment.

AI-generated with Claude (Anthropic), 2026-11-24; see docs/ai_usage.md.
"""

import copy
import csv
import hashlib
import json
import math
import statistics
import tempfile
import unittest
from pathlib import Path

from portfolio_optimization.portfolio import validate_results as vr


REAL_CONFIG = json.loads(vr.CONFIG_PATH.read_text(encoding="utf-8"))
TOY_FILE = (
    "3\n .02 .1\n .06 .2\n .10 .3\n"
    " 1 1 1.0\n 1 2 0.0\n 1 3 0.0\n 2 2 1.0\n 2 3 0.0\n 3 3 1.0\n"
)
RETURNS, SDS = (0.02, 0.06, 0.10), (0.1, 0.2, 0.3)
BUDGET, SEEDS, ALPHAS = 200, [0, 1], [0.25, 0.5]


def toy_weights(alpha, seed):
    """Mix equal weights with asset 3 to reach or exceed the target exactly."""
    target = (1 - alpha) * 0.06 + alpha * 0.10
    beta = (target - 0.06) / (0.10 - 0.06) + 0.05 * seed
    return [(1 - beta) / 3, (1 - beta) / 3, (1 - beta) / 3 + beta]


def hand_variance(weights):
    # Zero correlation: only the diagonal terms remain.
    return sum((w * s) ** 2 for w, s in zip(weights, SDS))


def toy_record(alpha, variant, seed):
    weights = toy_weights(alpha, seed)
    variance = hand_variance(weights)
    settings = dict(REAL_CONFIG["one_plus_one"] if variant == "one_plus_one"
                    else REAL_CONFIG["population"])
    settings["initial_step_size"] = REAL_CONFIG["initial_step_size"]
    settings["step_size_bounds"] = REAL_CONFIG["step_size_bounds"]
    record = {
        "case": f"toy_alpha{round(alpha * 100):03d}", "dataset": "toy",
        "assets": 3, "alpha": alpha,
        "min_return": (1 - alpha) * 0.06 + alpha * 0.10,
        "variant": variant, "seed": seed, "settings": settings,
        "budget": BUDGET, "evaluations": BUDGET, "best_weights": weights,
        "best_return": sum(w * r for w, r in zip(weights, RETURNS)),
        "best_variance": variance, "valid": True, "runtime_s": 0.5 + seed,
        "history": [[1, variance + 0.01], [50, variance + 0.001], [BUDGET, variance]],
    }
    # Checkpoints for mu = 10, lambda = 70 and a budget of 200: 10, 80, 150.
    if variant == "mu_plus_lambda":
        record["population_best"] = [[10, variance + 0.01], [80, variance + 0.001],
                                     [150, variance + 0.001]]
    elif variant == "mu_comma_lambda":
        record["population_best"] = [[10, variance + 0.02], [80, variance + 0.002],
                                     [150, variance + 0.005]]
    return record


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ToyExperiment:
    """A complete synthetic experiment on disk: data, config, runs, sidecar, table."""

    def __init__(self, directory):
        self.root = Path(directory)
        (self.root / "data").mkdir()
        self.data = self.root / "data/toy.txt"
        self.data.write_text(TOY_FILE, encoding="ascii")
        config = copy.deepcopy(REAL_CONFIG)
        config.update(datasets=[{"name": "toy", "path": "data/toy.txt", "assets": 3}],
                      alphas=ALPHAS, seeds=SEEDS, evaluation_budget=BUDGET)
        self.config = config
        self.config_path = self.root / "config.json"
        self.config_path.write_text(json.dumps(config), encoding="utf-8")
        self.runs = self.root / "runs.jsonl"
        self.summary = self.root / "summary.csv"
        self.records = [toy_record(a, v, s) for a in ALPHAS
                        for v in config["variants"] for s in SEEDS]
        self.metadata = {"identity": {
            "selection": {"datasets": ["toy"], "alphas": ALPHAS,
                          "variants": config["variants"], "seeds": SEEDS,
                          "budget": BUDGET},
            "solver_mode": "actual_es", "git_source_dirty": False,
            "config_sha256": sha(self.config_path),
            "dataset_sha256": {"toy": sha(self.data)},
        }}
        self.write()

    def write(self, summary=True):
        self.runs.write_text("".join(json.dumps(r) + "\n" for r in self.records),
                             encoding="utf-8")
        self.runs.with_suffix(".metadata.json").write_text(
            json.dumps(self.metadata), encoding="utf-8")
        if summary:
            report = self.validate(summary_path=None)
            with open(self.summary, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=vr.SUMMARY_FIELDS)
                writer.writeheader()
                for row in report.rows:
                    writer.writerow({k: ("" if v is None else v) for k, v in row.items()})

    def validate(self, summary_path="default", allow_partial=False):
        return vr.validate(
            self.runs,
            summary_path=self.summary if summary_path == "default" else summary_path,
            config_path=self.config_path, root=self.root, allow_partial=allow_partial)

    def find(self, alpha, variant, seed):
        return next(r for r in self.records if r["alpha"] == alpha
                    and r["variant"] == variant and r["seed"] == seed)


class ValidatorTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.toy = ToyExperiment(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def reset(self):
        self.tearDown()
        self.setUp()

    def assertFails(self, fragment, **kwargs):
        report = self.toy.validate(**kwargs)
        self.assertFalse(report.passed, "validation unexpectedly passed")
        self.assertTrue(any(fragment in e for e in report.errors),
                        f"no error containing {fragment!r}: {report.errors[:5]}")
        return report


class TestParser(unittest.TestCase):
    def test_port1_checkpoints_from_the_brief(self):
        data = vr.parse_or_library(
            vr.ROOT / "portfolio_optimization/data/or_library/port1.txt")
        equal = [1 / data.n] * data.n
        self.assertEqual(data.n, 31)
        self.assertAlmostEqual(vr.equal_weight_return(data.returns), 0.003504064516129, places=14)
        self.assertAlmostEqual(vr.portfolio_variance(equal, data), 0.001130937943724, places=14)
        self.assertAlmostEqual(vr.target_return(data.returns, 0.5), 0.007184532258065, places=14)

    def test_all_five_datasets_have_the_published_sizes(self):
        for entry in REAL_CONFIG["datasets"]:
            data = vr.parse_or_library(vr.ROOT / entry["path"])
            self.assertEqual(data.n, entry["assets"])
            self.assertEqual(data.correlation, [list(r) for r in zip(*data.correlation)])

    def test_rejects_duplicate_missing_and_out_of_range_pairs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.txt"
            for text in (TOY_FILE.replace(" 2 3 0.0", " 3 2 0.0").replace(" 1 3 0.0", " 2 3 0.0"),
                         TOY_FILE.replace(" 3 3 1.0\n", ""),
                         TOY_FILE.replace(" 2 3 0.0", " 2 4 0.0"),
                         TOY_FILE.replace(" 2 2 1.0", " 2 2 0.9")):
                path.write_text(text, encoding="ascii")
                with self.assertRaises(ValueError):
                    vr.parse_or_library(path)

    def test_hand_calculated_example(self):
        # Candidates A and B from the assignment: variance 0.0097 and 0.0081.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "toy.txt"
            path.write_text(TOY_FILE, encoding="ascii")
            data = vr.parse_or_library(path)
        self.assertAlmostEqual(vr.portfolio_variance([0.5, 0.3, 0.2], data), 0.0097, places=15)
        self.assertAlmostEqual(vr.portfolio_variance([0.6, 0.3, 0.1], data), 0.0081, places=15)
        self.assertAlmostEqual(vr.portfolio_return([0.6, 0.3, 0.1], data), 0.04, places=15)


class TestCompleteExperiment(ValidatorTestCase):
    def test_valid_synthetic_experiment_passes_as_final(self):
        report = self.toy.validate()
        self.assertEqual(report.errors, [])
        self.assertTrue(report.complete and report.final)
        self.assertEqual(report.records, 12)
        self.assertEqual(len(report.rows), 6)

    def test_statistics_match_hand_calculation(self):
        report = self.toy.validate()
        row = next(r for r in report.rows
                   if r["case"] == "toy_alpha050" and r["variant"] == "mu_plus_lambda")
        values = [hand_variance(toy_weights(0.5, s)) for s in SEEDS]
        self.assertAlmostEqual(row["best_variance"], min(values), places=15)
        self.assertAlmostEqual(row["mean_variance"], sum(values) / 2, places=15)
        self.assertAlmostEqual(row["sd_variance"], abs(values[0] - values[1]) / math.sqrt(2), places=15)
        self.assertEqual(row["mean_runtime_s"], 1.0)
        self.assertEqual((row["runs"], row["valid_runs"], row["valid_rate"]), (2, 2, 1.0))

    def test_comma_worsening_is_counted_but_allowed(self):
        report = self.toy.validate()
        self.assertEqual(report.facts["population_best_worsened"],
                         {"mu_plus_lambda": 0, "mu_comma_lambda": 4})

    def test_validation_never_modifies_files(self):
        before = {p: sha(p) for p in self.toy.root.rglob("*") if p.is_file()}
        self.toy.validate()
        self.assertEqual(before, {p: sha(p) for p in self.toy.root.rglob("*") if p.is_file()})


class TestCoverage(ValidatorTestCase):
    def test_missing_record_fails_final_validation(self):
        self.toy.records.pop()
        self.toy.write(summary=False)
        self.assertFails("missing", summary_path=None)

    def test_partial_set_is_never_reported_as_final(self):
        self.toy.records = self.toy.records[:5]
        self.toy.metadata["identity"]["selection"]["seeds"] = [0]
        self.toy.write(summary=False)
        report = self.toy.validate(summary_path=None, allow_partial=True)
        self.assertEqual(report.errors, [])
        self.assertFalse(report.complete or report.final)
        self.assertIn("PARTIAL", vr.format_report(report, self.toy.runs))

    def test_duplicate_record(self):
        self.toy.records.append(copy.deepcopy(self.toy.records[0]))
        self.toy.write(summary=False)
        self.assertFails("duplicate record", summary_path=None)

    def test_record_outside_matrix(self):
        self.toy.records[0]["seed"] = 7
        self.toy.write(summary=False)
        self.assertFails("outside the configured experiment matrix", summary_path=None)

    def test_corrupted_line(self):
        self.toy.write()
        with open(self.toy.runs, "a", encoding="utf-8") as handle:
            handle.write("{not json\n")
        self.assertFails("invalid JSON")


class TestRecordChecks(ValidatorTestCase):
    def corrupt(self, change, fragment, variant="one_plus_one"):
        record = self.toy.find(0.5, variant, 1)
        change(record)
        self.toy.write(summary=False)
        return self.assertFails(fragment, summary_path=None)

    def test_wrong_variance_and_return(self):
        self.corrupt(lambda r: r.update(best_variance=r["best_variance"] * 1.001), "saved best_variance")
        self.reset()
        self.corrupt(lambda r: r.update(best_return=r["best_return"] + 1e-6), "saved best_return")

    def test_negative_weight_and_budget_sum(self):
        self.corrupt(lambda r: r["best_weights"].__setitem__(0, -1e-6), "negative weight")
        self.reset()
        self.corrupt(lambda r: r["best_weights"].__setitem__(0, r["best_weights"][0] + 1e-6), "weights sum")

    def test_return_below_target(self):
        def lower(r):
            r["best_weights"] = [0.4, 0.3, 0.3]     # return 0.056 < R_min(0.5) = 0.08
        self.corrupt(lower, "below R_min")

    def test_budget_settings_assets_and_target(self):
        for change, fragment in (
                (lambda r: r.update(evaluations=29999), "evaluations is not exactly"),
                (lambda r: r.update(budget=300), "budget is not exactly"),
                (lambda r: r["settings"].update(mu=12), "settings"),
                (lambda r: r.update(assets=4), "asset count"),
                (lambda r: r.update(min_return=0.07), "minimum return"),
                (lambda r: r.update(case="toy_alpha025"), "case name")):
            self.reset()
            self.corrupt(change, fragment, variant="mu_plus_lambda")

    def test_history_errors(self):
        for change, fragment in (
                (lambda r: r["history"].insert(1, [20, 1.0]), "worsened"),
                (lambda r: r["history"].pop(), "end at the evaluation budget"),
                (lambda r: r["history"][0].__setitem__(0, 2), "start at evaluation 1"),
                (lambda r: r["history"][-1].__setitem__(1, r["history"][-1][1] * 0.9), "endpoint"),
                (lambda r: r["history"].append([150, 0.0]), "strictly increasing")):
            self.reset()
            self.corrupt(change, fragment)

    def test_population_history_rules(self):
        for variant, change, fragment in (
                ("mu_plus_lambda", lambda r: r["population_best"][2].__setitem__(1, 1.0), "worsened"),
                ("mu_plus_lambda", lambda r: r["population_best"][1].__setitem__(1, r["history"][1][1] * 1.1), "differs from the archive"),
                ("mu_comma_lambda", lambda r: r["population_best"][1].__setitem__(1, r["best_variance"] * 0.5), "better than the archive"),
                ("mu_comma_lambda", lambda r: r["population_best"].pop(), "checkpoints"),
                ("mu_plus_lambda", lambda r: r.pop("population_best"), "missing population-best"),
                ("one_plus_one", lambda r: r.update(population_best=[[10, 0.1]]), "(1+1)-ES record has")):
            self.reset()
            self.corrupt(change, fragment, variant=variant)

    def test_invalid_record_excluded_from_variance_statistics(self):
        record = self.toy.find(0.5, "one_plus_one", 1)
        record.update(valid=False, best_weights=[0.5, 0.5, 0.5])
        self.toy.write()
        report = self.toy.validate()
        self.assertEqual(report.errors, [])
        self.assertEqual(report.facts["invalid_records"], 1)
        row = next(r for r in report.rows
                   if r["case"] == "toy_alpha050" and r["variant"] == "one_plus_one")
        self.assertEqual((row["valid_runs"], row["valid_rate"], row["sd_variance"]), (1, 0.5, None))
        self.assertAlmostEqual(row["mean_variance"], hand_variance(toy_weights(0.5, 0)), places=15)
        self.assertEqual(row["mean_runtime_s"], 1.0)       # runtime averages all runs


class TestSummaryAndProvenance(ValidatorTestCase):
    def rewrite_summary(self, change):
        with open(self.toy.summary, newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        change(rows)
        with open(self.toy.summary, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=vr.SUMMARY_FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    def test_summary_value_mismatch(self):
        self.rewrite_summary(lambda rows: rows[3].update(
            mean_variance=repr(float(rows[3]["mean_variance"]) * (1 + 1e-9))))
        self.assertFails("mean_variance")

    def test_summary_missing_row_and_count(self):
        self.rewrite_summary(lambda rows: rows.pop())
        self.assertFails("row missing")
        self.reset()
        self.rewrite_summary(lambda rows: rows[0].update(valid_runs="1"))
        self.assertFails("valid_runs")

    def test_metadata_required_for_final_result(self):
        self.toy.runs.with_suffix(".metadata.json").unlink()
        self.assertFails("provenance sidecar")

    def test_metadata_detects_pilot_or_changed_inputs(self):
        for change, fragment in (
                (lambda i: i.update(solver_mode="test_solver"), "solver mode"),
                (lambda i: i["selection"].update(seeds=[0]), "full configured matrix"),
                (lambda i: i.update(config_sha256="0" * 64), "configuration file changed"),
                (lambda i: i["dataset_sha256"].update(toy="0" * 64), "data file changed")):
            self.reset()
            change(self.toy.metadata["identity"])
            self.toy.write(summary=False)
            self.assertFails(fragment, summary_path=None)


@unittest.skipUnless(vr.DEFAULT_RUNS.is_file(), "committed 450-run records not present")
class TestCommittedExperiment(unittest.TestCase):
    def test_all_450_committed_runs(self):
        report = vr.validate()
        self.assertEqual(report.errors, [])
        self.assertTrue(report.final)
        self.assertEqual((report.records, len(report.rows)), (450, 45))
        self.assertEqual(report.facts["invalid_records"], 0)
        self.assertLess(report.facts["max_relative_value_difference"], 1e-12)
        self.assertEqual(report.facts["population_best_worsened"]["mu_plus_lambda"], 0)
        self.assertGreater(report.facts["population_best_worsened"]["mu_comma_lambda"], 0)
        self.assertEqual(statistics.fmean(
            r["valid_rate"] for r in report.rows), 1.0)


if __name__ == "__main__":
    unittest.main()
