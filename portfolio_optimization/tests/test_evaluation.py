
"""Tests for portfolio objective and return calculations.

AI-assisted implementation. See docs/ai_usage.md.
"""

import math
from pathlib import Path
import unittest

from portfolio_optimization.portfolio.data import load_portfolio
from portfolio_optimization.portfolio.evaluation import (
    expected_return,
    portfolio_variance,
    minimum_return_target,
)


DATA_DIR = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "or_library"
)


class TestPortfolioEvaluation(unittest.TestCase):

    def setUp(self):
        self.returns = (0.01, 0.02)
        self.covariance = (
            (0.01, 0.01),
            (0.01, 0.04),
        )
        self.weights = (0.25, 0.75)

    def test_expected_return_manual(self):
        result = expected_return(self.weights, self.returns)
        self.assertAlmostEqual(result, 0.0175, places=12)

    def test_variance_manual(self):
        # 0.25²*0.01 + 2*0.25*0.75*0.01 + 0.75²*0.04
        result = portfolio_variance(
            self.weights, self.covariance
        )
        self.assertAlmostEqual(result, 0.026875, places=12)

    def test_minimum_return_targets(self):
        self.assertAlmostEqual(
            minimum_return_target(self.returns, 0.0),
            0.015,
        )
        self.assertAlmostEqual(
            minimum_return_target(self.returns, 0.5),
            0.0175,
        )
        self.assertAlmostEqual(
            minimum_return_target(self.returns, 1.0),
            0.02,
        )

    def test_port1_numerical_checkpoints(self):
        data = load_portfolio(DATA_DIR / "port1.txt")
        weights = [1.0 / data.n_assets] * data.n_assets

        self.assertAlmostEqual(
            expected_return(weights, data.returns),
            0.003504064516129,
            places=12,
        )
        self.assertAlmostEqual(
            portfolio_variance(weights, data.covariance),
            0.001130937943724,
            places=12,
        )
        self.assertAlmostEqual(
            minimum_return_target(data.returns, 0.50),
            0.007184532258065,
            places=12,
        )

    def test_invalid_weight_dimensions(self):
        with self.assertRaisesRegex(ValueError, "equal lengths"):
            expected_return([1.0], self.returns)

    def test_invalid_covariance_dimensions(self):
        with self.assertRaisesRegex(ValueError, "dimensions"):
            portfolio_variance(
                self.weights, ((0.01,),)
            )

        with self.assertRaisesRegex(ValueError, "square"):
            portfolio_variance(
                self.weights, ((0.01,), (0.01, 0.04))
            )

    def test_invalid_alpha(self):
        for alpha in (-0.1, 1.1, math.nan, math.inf):
            with self.subTest(alpha=alpha):
                with self.assertRaises(ValueError):
                    minimum_return_target(self.returns, alpha)

    def test_nonfinite_inputs(self):
        with self.assertRaises(ValueError):
            expected_return(
                (math.nan, 0.5), self.returns
            )

        with self.assertRaises(ValueError):
            portfolio_variance(
                self.weights,
                ((math.nan, 0.01), (0.01, 0.04)),
            )

        with self.assertRaises(ValueError):
            minimum_return_target((0.01, math.inf), 0.5)

    def test_empty_inputs(self):
        with self.assertRaises(ValueError):
            expected_return([], [])

        with self.assertRaises(ValueError):
            minimum_return_target([], 0.5)


if __name__ == "__main__":
    unittest.main()