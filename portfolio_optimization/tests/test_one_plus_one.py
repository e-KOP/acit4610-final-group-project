"""Tests for the (1+1)-ES.

AI-generated with Claude (Anthropic), built step by step with and reviewed by
Jakob Andreas Amtedal; see docs/ai_usage.md.

Run from the repository root:
    python -m unittest portfolio_optimization.tests.test_one_plus_one -v
"""
import math
import unittest
from pathlib import Path

import numpy as np

from portfolio_optimization.portfolio import one_plus_one as es
from portfolio_optimization.portfolio.data import load_portfolio
from portfolio_optimization.portfolio.evaluation import (
    expected_return, minimum_return_target, portfolio_variance,
)
from portfolio_optimization.portfolio.feasibility import is_feasible

DATA = Path(__file__).resolve().parents[1] / "data" / "or_library"

# Two uncorrelated assets with variances 0.04 and 0.01 and equal returns:
# the minimum-variance portfolio is w = (0.01, 0.04) / 0.05 = (0.2, 0.8),
# with variance 0.04*0.2^2 + 0.01*0.8^2 = 0.008.
TWO_RETURNS = [0.05, 0.05]
TWO_COVARIANCE = [[0.04, 0.0], [0.0, 0.01]]


class TestStepSizeRule(unittest.TestCase):
    def test_success_and_failure_factors(self):
        self.assertAlmostEqual(es.update_step_size(0.1, True), 0.1 * math.exp(1 / 3))
        self.assertAlmostEqual(es.update_step_size(0.1, False), 0.1 * math.exp(-1 / 12))

    def test_one_fifth_success_rate_is_neutral(self):
        # 1 success and 4 failures cancel: exp(1/3) * exp(-1/12)^4 = 1
        sigma = 0.1
        for success in (True, False, False, False, False):
            sigma = es.update_step_size(sigma, success)
        self.assertAlmostEqual(sigma, 0.1)

    def test_step_size_is_clamped(self):
        self.assertEqual(es.update_step_size(1.0, True), 1.0)
        self.assertEqual(es.update_step_size(1e-8, False), 1e-8)


class TestSmallProblem(unittest.TestCase):
    def test_finds_known_two_asset_optimum(self):
        result = es.solve_one_plus_one(TWO_RETURNS, TWO_COVARIANCE, 0.05, seed=0,
                                       max_evaluations=2000)
        self.assertAlmostEqual(result["best_variance"], 0.008, places=6)
        np.testing.assert_allclose(result["best_weights"], [0.2, 0.8], atol=1e-3)

    def test_budget_is_exact_including_tiny_budgets(self):
        for budget in (1, 2, 3, 17, 500):
            result = es.solve_one_plus_one(TWO_RETURNS, TWO_COVARIANCE, 0.05, 0, budget)
            self.assertEqual(result["evaluations"], budget)
            self.assertEqual(len(result["history"]), budget)
            self.assertEqual(result["history"][-1][0], budget)

    def test_budget_of_one_returns_the_initial_solution(self):
        result = es.solve_one_plus_one(TWO_RETURNS, TWO_COVARIANCE, 0.05, 0, 1)
        self.assertEqual(result["best_variance"], result["initial_best"])

    def test_every_evaluation_is_counted(self):
        calls = []
        original = es.Archive.evaluate

        def counting(self, weights):
            calls.append(1)
            return original(self, weights)

        es.Archive.evaluate = counting
        try:
            es.solve_one_plus_one(TWO_RETURNS, TWO_COVARIANCE, 0.05, 0, 250)
        finally:
            es.Archive.evaluate = original
        self.assertEqual(len(calls), 250)

    def test_rejects_invalid_input(self):
        with self.assertRaises(ValueError):
            es.solve_one_plus_one(TWO_RETURNS, [[0.04]], 0.05, 0)
        for budget in (0, -1, 2.5):
            with self.assertRaises(ValueError):
                es.solve_one_plus_one(TWO_RETURNS, TWO_COVARIANCE, 0.05, 0, budget)


class TestPort1(unittest.TestCase):
    """Behaviour on a real dataset, with a short budget."""

    @classmethod
    def setUpClass(cls):
        cls.data = load_portfolio(DATA / "port1.txt")
        cls.target = minimum_return_target(cls.data.returns, 0.5)

    def run_es(self, seed, budget=3000):
        return es.solve_one_plus_one(self.data.returns, self.data.covariance,
                                     self.target, seed, budget)

    def test_result_is_feasible_and_reproduces_its_values(self):
        result = self.run_es(0)
        weights = result["best_weights"]
        self.assertTrue(result["feasible"])
        self.assertTrue(is_feasible(weights, self.data.returns, self.target))
        self.assertTrue(math.isclose(portfolio_variance(weights, self.data.covariance),
                                     result["best_variance"], rel_tol=1e-9))
        self.assertTrue(math.isclose(expected_return(weights, self.data.returns),
                                     result["best_return"], rel_tol=1e-9))

    def test_archive_never_worsens_and_improves_on_initial(self):
        result = self.run_es(1)
        values = [v for _, v in result["history"]]
        self.assertTrue(all(b <= a for a, b in zip(values, values[1:])))
        self.assertEqual(values[0], result["initial_best"])
        self.assertEqual(values[-1], result["best_variance"])
        self.assertLess(result["best_variance"], result["initial_best"])

    def test_same_seed_same_result_and_different_seed_differs(self):
        a, b, c = self.run_es(7), self.run_es(7), self.run_es(8)
        self.assertEqual(a["best_weights"], b["best_weights"])
        self.assertEqual(a["history"], b["history"])
        self.assertNotEqual(a["best_weights"], c["best_weights"])


if __name__ == "__main__":
    unittest.main()