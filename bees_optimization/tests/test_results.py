
"""Tests for independent validation of Problem 1 experiment results.

AI-assisted implementation; see docs/ai_usage.md.

Run:
    python -m unittest bees_optimization.tests.test_results -v
"""

import contextlib
import copy
import csv
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bees_optimization.bees import validate_results as vr


class TestIndependentCalculations(unittest.TestCase):

    def test_tour_length_includes_return_edge(self):
        coordinates = {
            1: (0, 0),
            2: (3, 0),
            3: (0, 4),
        }

        # Distances: 3 + 5 + 4 = 12
        self.assertEqual(
            vr.independent_tour_length([1, 2, 3], coordinates),
            12
        )

    def test_continuous_global_minima(self):
        cases = [
            ("sphere", [0.0] * 10),
            ("rosenbrock", [1.0] * 10),
            ("rastrigin", [0.0] * 10),
            ("ackley", [0.0] * 10),
        ]

        for name, vector in cases:
            with self.subTest(function=name):
                self.assertAlmostEqual(
                    vr.independent_objective(name, vector),
                    0.0,
                    places=10
                )

    def test_invalid_function_rejected(self):
        with self.assertRaises(ValueError):
            vr.independent_objective("unknown", [0.0] * 10)


class TestRecordValidation(unittest.TestCase):

    def setUp(self):
        self.coordinates = {
            1: (0, 0),
            2: (3, 0),
            3: (0, 4),
        }

        self.instance = {
            "name": "triangle",
            "cities": 3,
            "optimal_length": 12,
            "path": "unused.tsp",
        }

        self.settings = {
            "n_scouts": 3,
            "n_selected": 1,
            "n_elite": 1,
            "n_elite_recruits": 2,
            "n_other_recruits": 1,
        }

        self.record = {
            "instance": "triangle",
            "cities": 3,
            "optimum": 12,
            "neighborhood": "swap",
            "seed": 0,
            "settings": self.settings.copy(),
            "budget": 12,
            "evaluations": 12,
            "initial_best": 14,
            "best_length": 12,
            "gap_pct": 0.0,
            "runtime_s": 0.01,
            "best_tour": [1, 2, 3],
            "history": [[3, 14], [4, 12], [12, 12]],
        }

        self.config = {
            "evaluation_budget": 12,
            "seeds": [0],
            "instances": [self.instance],
            "neighborhoods": ["swap"],
            "expected_runs": 1,
            "ba": {
                "scout_population": 3,
                "selected_sites": 1,
                "elite_sites": 1,
                "elite_recruits": 2,
                "other_site_recruits": 1,
            },
        }

    def validate_records(self, records, config=None):
        if config is None:
            config = self.config

        with patch.object(
            vr, "load_coordinates",
            return_value=self.coordinates
        ):
            return vr.validate_runs(records, config, "tsp")

    def test_valid_tsp_record(self):
        self.assertEqual(
            vr.validate_tsp(
                self.record,
                self.instance,
                self.coordinates
            ),
            12
        )

    def test_invalid_tour_rejected(self):
        corrupted = copy.deepcopy(self.record)
        corrupted["best_tour"] = [1, 2, 2]

        with self.assertRaises(ValueError):
            vr.validate_tsp(
                corrupted,
                self.instance,
                self.coordinates
            )

    def test_incorrect_tour_length_rejected(self):
        corrupted = copy.deepcopy(self.record)
        corrupted["best_length"] = 11

        with self.assertRaises(ValueError):
            vr.validate_tsp(
                corrupted,
                self.instance,
                self.coordinates
            )

    def test_increasing_history_rejected(self):
        corrupted = copy.deepcopy(self.record)
        corrupted["history"][1][1] = 16

        with self.assertRaises(ValueError):
            vr.validate_history(corrupted, 3, 12, 12)

    def test_incomplete_history_rejected(self):
        corrupted = copy.deepcopy(self.record)
        corrupted["history"][-1][0] = 11

        with self.assertRaises(ValueError):
            vr.validate_history(corrupted, 3, 12, 12)

    def test_duplicate_seed_rejected(self):
        duplicate = copy.deepcopy(self.record)

        with self.assertRaises(ValueError):
            self.validate_records([self.record, duplicate])

    def test_missing_seed_rejected(self):
        config = copy.deepcopy(self.config)
        config["seeds"] = [0, 1]
        config["expected_runs"] = 2

        with self.assertRaises(ValueError):
            self.validate_records([self.record], config)

    def test_wrong_settings_rejected(self):
        corrupted = copy.deepcopy(self.record)
        corrupted["settings"]["n_scouts"] = 5

        with self.assertRaises(ValueError):
            self.validate_records([corrupted])

    def test_valid_record_group(self):
        groups = self.validate_records([self.record])

        self.assertEqual(len(groups), 1)
        self.assertIn(("triangle", "swap"), groups)

    def test_continuous_bounds_and_objective(self):
        function = {
            "bounds": [-5.12, 5.12],
        }

        record = {
            "function": "sphere",
            "dimension": 10,
            "bounds": [-5.12, 5.12],
            "best_vector": [0.0] * 10,
            "best_value": 0.0,
        }

        self.assertEqual(
            vr.validate_continuous(record, function),
            0.0
        )

        corrupted = copy.deepcopy(record)
        corrupted["best_value"] = 99.0

        with self.assertRaises(ValueError):
            vr.validate_continuous(corrupted, function)

        corrupted = copy.deepcopy(record)
        corrupted["best_vector"][0] = 100.0

        with self.assertRaises(ValueError):
            vr.validate_continuous(corrupted, function)

    def test_summary_statistics_rejected_if_incorrect(self):
        second = copy.deepcopy(self.record)
        second["seed"] = 1

        groups = {
            ("triangle", "swap"): [self.record, second]
        }

        row = {
            "instance": "triangle",
            "neighborhood": "swap",
            "cities": 3,
            "optimum": 12,
            "runs": 2,
            "best": 12,
            "mean": 12,
            "sd": 0,
            "mean_gap_pct": 0,
            "mean_initial_best": 14,
            "mean_runtime_s": 0.01,
        }

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "summary.csv"

            def write_row(values):
                with path.open(
                    "w", newline="", encoding="utf-8"
                ) as file:
                    writer = csv.DictWriter(
                        file, fieldnames=list(values)
                    )
                    writer.writeheader()
                    writer.writerow(values)

            # Valid summary should pass.
            write_row(row)
            vr.validate_table(path, groups, "tsp")

            # A fabricated mean must be detected.
            row["mean"] = 13
            write_row(row)

            with self.assertRaises(ValueError):
                vr.validate_table(path, groups, "tsp")


class TestCommittedExperiments(unittest.TestCase):

    def test_all_200_committed_runs(self):
        """Integration test using the actual saved experiment files."""
        with contextlib.redirect_stdout(io.StringIO()):
            result = vr.main()

        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
