
"""Tests for simplex projection and minimum-return repair."""

import math
from pathlib import Path
import unittest

from portfolio_optimization.portfolio.data import load_portfolio
from portfolio_optimization.portfolio.evaluation import (
    minimum_return_target,
)
from portfolio_optimization.portfolio.feasibility import is_feasible
from portfolio_optimization.portfolio.repair import (
    project_simplex,
    repair_weights,
)


DATA_DIR = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "or_library"
)


class TestPortfolioRepair(unittest.TestCase):

    def test_already_valid_simplex(self):
        result = project_simplex([0.2, 0.3, 0.5])

        for actual, expected in zip(result, [0.2, 0.3, 0.5]):
            self.assertAlmostEqual(actual, expected, places=12)

    def test_negative_weights(self):
        result = project_simplex([2.0, -1.0])

        self.assertAlmostEqual(result[0], 1.0)
        self.assertAlmostEqual(result[1], 0.0)

    def test_zero_weights(self):
        result = project_simplex([0.0, 0.0])

        self.assertAlmostEqual(result[0], 0.5)
        self.assertAlmostEqual(result[1], 0.5)

    def test_all_negative_weights(self):
        result = project_simplex([-1.0, -1.0, -1.0])

        for weight in result:
            self.assertAlmostEqual(weight, 1 / 3)

    def test_repair_already_feasible(self):
        weights = [0.8, 0.2]
        returns = [0.01, 0.03]

        repaired = repair_weights(weights, returns, 0.013)

        self.assertTrue(is_feasible(repaired, returns, 0.013))
        self.assertAlmostEqual(repaired[0], 0.8)
        self.assertAlmostEqual(repaired[1], 0.2)

    def test_minimum_return_repair(self):
        returns = [0.01, 0.03]
        target = 0.025

        repaired = repair_weights(
            [0.8, 0.2], returns, target
        )

        self.assertTrue(is_feasible(repaired, returns, target))
        self.assertAlmostEqual(repaired[0], 0.25)
        self.assertAlmostEqual(repaired[1], 0.75)

    def test_target_at_maximum_return(self):
        returns = [0.01, 0.03]

        repaired = repair_weights(
            [0.5, 0.5], returns, 0.03
        )

        self.assertTrue(is_feasible(repaired, returns, 0.03))
        self.assertAlmostEqual(repaired[0], 0.0)
        self.assertAlmostEqual(repaired[1], 1.0)

    def test_impossible_return_target(self):
        with self.assertRaisesRegex(ValueError, "unattainable"):
            repair_weights(
                [0.5, 0.5],
                [0.01, 0.03],
                0.04,
            )

    def test_nonfinite_inputs(self):
        with self.assertRaises(ValueError):
            project_simplex([math.nan, 0.5])

        with self.assertRaises(ValueError):
            repair_weights(
                [0.5, 0.5],
                [0.01, 0.03],
                math.inf,
            )

    def test_input_not_modified(self):
        weights = [1.5, -0.5]
        original = weights.copy()

        repair_weights(weights, [0.01, 0.03], 0.02)

        self.assertEqual(weights, original)

    def test_all_dataset_targets(self):
        for dataset_name in (
            "port1", "port2", "port3", "port4", "port5"
        ):
            data = load_portfolio(
                DATA_DIR / f"{dataset_name}.txt"
            )

            for alpha in (0.25, 0.50, 0.75):
                with self.subTest(
                    dataset=dataset_name,
                    alpha=alpha,
                ):
                    target = minimum_return_target(
                        data.returns, alpha
                    )

                    initial = [
                        1.0 / data.n_assets
                    ] * data.n_assets

                    repaired = repair_weights(
                        initial,
                        data.returns,
                        target,
                    )

                    self.assertTrue(
                        is_feasible(
                            repaired,
                            data.returns,
                            target,
                        )
                    )


if __name__ == "__main__":
    unittest.main()
