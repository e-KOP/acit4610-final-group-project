
"""Tests for independent portfolio feasibility checks."""

import math
import unittest

from portfolio_optimization.portfolio.feasibility import is_feasible


class TestPortfolioFeasibility(unittest.TestCase):

    def setUp(self):
        self.returns = [0.01, 0.03]

    def test_valid_portfolio(self):
        self.assertTrue(
            is_feasible([0.5, 0.5], self.returns, 0.02)
        )

    def test_negative_weights(self):
        self.assertFalse(
            is_feasible([-0.1, 1.1], self.returns, 0.02)
        )

    def test_sum_below_one(self):
        self.assertFalse(
            is_feasible([0.3, 0.3], self.returns, 0.01)
        )

    def test_sum_above_one(self):
        self.assertFalse(
            is_feasible([0.7, 0.7], self.returns, 0.01)
        )

    def test_return_below_target(self):
        self.assertFalse(
            is_feasible([0.9, 0.1], self.returns, 0.025)
        )

    def test_numerical_tolerance(self):
        self.assertTrue(
            is_feasible(
                [-1e-9, 1.0 + 1e-9],
                self.returns,
                0.03,
            )
        )

    def test_invalid_dimensions(self):
        self.assertFalse(
            is_feasible([1.0], self.returns, 0.01)
        )

    def test_nonfinite_values(self):
        self.assertFalse(
            is_feasible(
                [math.nan, 0.5],
                self.returns,
                0.01,
            )
        )

    def test_invalid_tolerance(self):
        self.assertFalse(
            is_feasible(
                [0.5, 0.5],
                self.returns,
                0.02,
                tolerance=-1,
            )
        )

    def test_empty_portfolio(self):
        self.assertFalse(is_feasible([], [], 0.0))


if __name__ == "__main__":
    unittest.main()
