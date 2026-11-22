
"""Regression tests for the Problem 1 experiment and output pipeline.

AI-assisted implementation; see docs/ai_usage.md.
"""

import contextlib
import copy
import io
import json
import shutil
import statistics
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bees_optimization.bees import experiments
from bees_optimization.bees import output


class TestExperimentPipeline(unittest.TestCase):

    def test_configuration_settings(self):
        config = experiments.load_config("tsp")
        settings = experiments.ba_settings(config)

        self.assertEqual(settings["n_scouts"], 10)
        self.assertEqual(settings["n_selected"], 3)
        self.assertEqual(settings["n_elite"], 1)
        self.assertEqual(settings["n_elite_recruits"], 10)
        self.assertEqual(settings["n_other_recruits"], 5)

    def test_invalid_configuration(self):
        config = copy.deepcopy(
            experiments.load_config("tsp")
        )
        config["ba"]["scout_population"] = None

        with self.assertRaises(ValueError):
            experiments.ba_settings(config)

    def test_history_compression(self):
        original = [
            (3, 10),
            (4, 10),
            (5, 8),
            (6, 8),
            (7, 6),
            (8, 6),
        ]

        expected = [
            [3, 10],
            [5, 8],
            [7, 6],
            [8, 6],
        ]

        compressed = experiments.compress_history(original)
        self.assertEqual(compressed, expected)

        for evaluation in range(3, 9):
            actual = output.value_at(compressed, evaluation)
            original_value = original[evaluation - 3][1]
            self.assertEqual(actual, original_value)

    def test_small_tsp_experiment_batch(self):
        config = copy.deepcopy(
            experiments.load_config("tsp")
        )

        config["instances"] = [
            next(
                instance
                for instance in config["instances"]
                if instance["name"] == "eil51"
            )
        ]
        config["seeds"] = [0]
        config["evaluation_budget"] = 40

        with tempfile.TemporaryDirectory() as directory:
            with patch.object(
                experiments, "load_config",
                return_value=config
            ):
                with contextlib.redirect_stdout(io.StringIO()):
                    path = experiments.run_tsp(directory)

            with Path(path).open(encoding="utf-8") as file:
                saved = [json.loads(line) for line in file]

            self.assertEqual(len(saved), 2)
            self.assertEqual(
                {r["neighborhood"] for r in saved},
                {"swap", "segment_reversal"}
            )

            for record in saved:
                self.assertEqual(record["evaluations"], 40)
                self.assertEqual(record["history"][0][0], 10)
                self.assertEqual(record["history"][-1][0], 40)
                self.assertEqual(
                    record["history"][-1][1],
                    record["best_length"]
                )
                self.assertEqual(len(record["best_tour"]), 51)

    def test_small_continuous_experiment_batch(self):
        config = copy.deepcopy(
            experiments.load_config("continuous")
        )

        config["functions"] = [
            f for f in config["functions"]
            if f["name"] == "sphere"
        ]
        config["dimensions"] = [10]
        config["seeds"] = [0, 1]
        config["evaluation_budget"] = 40

        with tempfile.TemporaryDirectory() as directory:
            with patch.object(
                experiments, "load_config",
                return_value=config
            ):
                with contextlib.redirect_stdout(io.StringIO()):
                    path = experiments.run_continuous(directory)

            with Path(path).open(encoding="utf-8") as file:
                saved = [json.loads(line) for line in file]

            self.assertEqual(len(saved), 2)
            self.assertEqual({r["seed"] for r in saved}, {0, 1})

            for record in saved:
                self.assertEqual(record["evaluations"], 40)
                self.assertEqual(record["history"][-1][0], 40)
                self.assertEqual(
                    record["history"][-1][1],
                    record["best_value"]
                )

    def test_convergence_alignment(self):
        runs = [
            {
                "budget": 12,
                "history": [[2, 10], [5, 8], [12, 6]],
            },
            {
                "budget": 12,
                "history": [[2, 12], [7, 10], [12, 9]],
            },
        ]

        with patch.object(output, "GRID_STEP", 5):
            grid, means, sds = output.mean_curve(runs)

        self.assertEqual(grid, [2, 5, 10, 12])
        self.assertEqual(means, [11, 10, 9, 7.5])
        self.assertAlmostEqual(
            sds[0],
            statistics.stdev([10, 12])
        )
        self.assertAlmostEqual(
            sds[-1],
            statistics.stdev([6, 9])
        )

    def test_regenerate_all_tables_and_figures(self):
        """Regenerate outputs in a temporary folder, not the repository."""
        original_results = output.RESULTS

        with tempfile.TemporaryDirectory() as directory:
            temp_results = Path(directory)
            temp_raw = temp_results / "raw"
            temp_raw.mkdir()

            for filename in (
                "tsp_runs.jsonl",
                "continuous_runs.jsonl",
            ):
                shutil.copy2(
                    original_results / "raw" / filename,
                    temp_raw / filename
                )

            with patch.object(output, "RESULTS", temp_results), \
                 patch.object(
                     output, "FIGURES",
                     temp_results / "figures"
                 ):
                with contextlib.redirect_stdout(io.StringIO()):
                    output.main()

            for filename in (
                "tsp_summary.csv",
                "continuous_summary.csv",
                "tsp_summary.md",
                "continuous_summary.md",
            ):
                original = (
                    original_results / "tables" / filename
                ).read_text(encoding="utf-8")

                regenerated = (
                    temp_results / "tables" / filename
                ).read_text(encoding="utf-8")

                self.assertEqual(original, regenerated)

            figures = [
                "tsp_convergence_berlin52.png",
                "tsp_convergence_ch150.png",
                "berlin52_best_route.png",
                "rastrigin_d10_convergence.png",
                "continuous_d30_boxplots.png",
            ]

            for filename in figures:
                figure = temp_results / "figures" / filename

                self.assertTrue(
                    figure.is_file(),
                    f"Missing generated figure: {filename}"
                )
                self.assertGreater(figure.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
