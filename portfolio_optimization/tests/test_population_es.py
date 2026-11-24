"""Tests for the (mu+lambda)-ES and (mu,lambda)-ES.

AI-generated with Claude (Anthropic), built step by step with and reviewed by
Jakob Andreas Amtedal; see docs/ai_usage.md.

Run from the repository root:
    python -m unittest portfolio_optimization.tests.test_population_es -v
"""
import math
import unittest
from pathlib import Path

import numpy as np

from portfolio_optimization.portfolio import population_es as pes
from portfolio_optimization.portfolio.data import load_portfolio
from portfolio_optimization.portfolio.evaluation import (
    expected_return, minimum_return_target, portfolio_variance,
)
from portfolio_optimization.portfolio.feasibility import is_feasible
from portfolio_optimization.portfolio.one_plus_one import Archive

DATA = Path(__file__).resolve().parents[1] / "data" / "or_library"
TWO_RETURNS = [0.05, 0.05]
TWO_COVARIANCE = [[0.04, 0.0], [0.0, 0.01]]   # optimum (0.2, 0.8), variance 0.008


def individual(variance, n=2):
    return pes.Individual(np.full(n, 1 / n), variance, np.full(n, 0.1))


class FixedNormals:
    """Fake random generator: fixed parent choice and fixed normal draws."""

    def __init__(self, normals):
        self.normals = list(normals)

    def choice(self, a, size=None, replace=False):
        return np.array([0, 1])

    def standard_normal(self, size=None):
        if size is None:
            return self.normals.pop(0)
        values, self.normals = self.normals[:size], self.normals[size:]
        return np.array(values)


class TestOperators(unittest.TestCase):
    def test_recombination_self_adaptation_and_mutation(self):
        n = 4
        returns = np.array([0.01, 0.02, 0.03, 0.04])
        first = pes.Individual(np.array([0.4, 0.3, 0.2, 0.1]), 1.0, np.full(n, 0.01))
        second = pes.Individual(np.array([0.1, 0.2, 0.3, 0.4]), 1.0, np.full(n, 0.04))
        tau_prime, tau = 1 / math.sqrt(2 * n), 1 / math.sqrt(2 * math.sqrt(n))
        z0, zi, mutation = 0.5, [0.1, -0.2, 0.3, 0.0], [0.0, 0.0, 0.0, 0.0]
        rng = FixedNormals([z0] + zi + mutation)

        child, sigmas = pes.make_child([first, second], returns, 0.0, tau_prime, tau, rng)

        # geometric mean of 0.01 and 0.04 is 0.02, then exp(tau'*Z0 + tau*Zi)
        expected = 0.02 * np.exp(tau_prime * z0 + tau * np.array(zi))
        np.testing.assert_allclose(sigmas, expected)
        # zero mutation: the child is the arithmetic mean (already feasible)
        np.testing.assert_allclose(child, [0.25, 0.25, 0.25, 0.25])

    def test_step_sizes_are_clamped(self):
        n = 2
        parent = pes.Individual(np.array([0.5, 0.5]), 1.0, np.full(n, 1.0))
        rng = FixedNormals([10.0, 10.0, 10.0, 0.0, 0.0])
        _, sigmas = pes.make_child([parent, parent], np.array([0.0, 0.0]), 0.0, 1, 1, rng)
        np.testing.assert_array_equal(sigmas, [1.0, 1.0])
        rng = FixedNormals([-50.0, -50.0, -50.0, 0.0, 0.0])
        _, sigmas = pes.make_child([parent, parent], np.array([0.0, 0.0]), 0.0, 1, 1, rng)
        np.testing.assert_array_equal(sigmas, [1e-8, 1e-8])

    def test_plus_selection_uses_parents_and_offspring(self):
        parents = [individual(v) for v in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)]
        offspring = [individual(v) for v in (0.5, 11, 12) + (20,) * 67]
        survivors = pes.select_survivors(parents, offspring, "plus")
        self.assertEqual([s.variance for s in survivors], [0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9])

    def test_comma_selection_uses_offspring_only(self):
        parents = [individual(v) for v in range(1, 11)]          # better than all offspring
        offspring = [individual(v) for v in range(100, 170)]
        survivors = pes.select_survivors(parents, offspring, "comma")
        self.assertEqual([s.variance for s in survivors], list(range(100, 110)))
        self.assertFalse(any(s in parents for s in survivors))


class TestBudget(unittest.TestCase):
    def test_exact_budget_including_partial_batches(self):
        # 10 initial + 70 per generation: 80 = 1 full generation, 100 ends with 20,
        # 30000 = 10 + 428*70 + 30, 5 stops during initialization
        for budget in (1, 5, 10, 11, 80, 100, 30000):
            for selection in ("plus", "comma"):
                result = pes.solve_population(TWO_RETURNS, TWO_COVARIANCE, 0.05, 0,
                                              selection, budget)
                self.assertEqual(result["evaluations"], budget)
                self.assertEqual(len(result["history"]), budget)

    def test_generations_and_partial_last_batch(self):
        result = pes.solve_population(TWO_RETURNS, TWO_COVARIANCE, 0.05, 0, "comma", 30000)
        evaluations = [e for e, _ in result["population_best"]]
        self.assertEqual(evaluations[0], 10)
        self.assertEqual(evaluations[-1], 10 + 428 * 70)           # last full generation
        self.assertEqual(len(evaluations), 1 + 428)

    def test_partial_batch_updates_the_archive(self):
        calls = []
        original = Archive.evaluate

        def recording(self, weights):
            variance = original(self, weights)
            calls.append((self.evaluations, self.best_variance))
            return variance

        Archive.evaluate = recording
        try:
            result = pes.solve_population(TWO_RETURNS, TWO_COVARIANCE, 0.05, 1, "plus", 100)
        finally:
            Archive.evaluate = original
        self.assertEqual(len(calls), 100)                          # last 20 were evaluated
        self.assertEqual(result["best_variance"], min(v for _, v in calls))

    def test_rejects_invalid_input(self):
        with self.assertRaises(ValueError):
            pes.solve_population(TWO_RETURNS, TWO_COVARIANCE, 0.05, 0, "best")
        with self.assertRaises(ValueError):
            pes.solve_population(TWO_RETURNS, [[0.04]], 0.05, 0, "plus")
        for budget in (0, -3, 1.5):
            with self.assertRaises(ValueError):
                pes.solve_population(TWO_RETURNS, TWO_COVARIANCE, 0.05, 0, "plus", budget)


class TestBehaviour(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_portfolio(DATA / "port1.txt")
        cls.target = minimum_return_target(cls.data.returns, 0.5)

    def run_es(self, selection, seed, budget=3000):
        return pes.solve_population(self.data.returns, self.data.covariance,
                                    self.target, seed, selection, budget)

    def test_finds_known_two_asset_optimum(self):
        for selection in ("plus", "comma"):
            result = pes.solve_population(TWO_RETURNS, TWO_COVARIANCE, 0.05, 0,
                                          selection, 3000)
            self.assertAlmostEqual(result["best_variance"], 0.008, places=6)

    def test_result_is_feasible_and_reproduces_its_values(self):
        for selection in ("plus", "comma"):
            result = self.run_es(selection, 0)
            weights = result["best_weights"]
            self.assertTrue(is_feasible(weights, self.data.returns, self.target))
            self.assertTrue(math.isclose(portfolio_variance(weights, self.data.covariance),
                                         result["best_variance"], rel_tol=1e-9))
            self.assertTrue(math.isclose(expected_return(weights, self.data.returns),
                                         result["best_return"], rel_tol=1e-9))

    def test_archive_never_worsens(self):
        for selection in ("plus", "comma"):
            values = [v for _, v in self.run_es(selection, 1)["history"]]
            self.assertTrue(all(b <= a for a, b in zip(values, values[1:])))

    def test_plus_population_best_never_worsens(self):
        values = [v for _, v in self.run_es("plus", 2)["population_best"]]
        self.assertTrue(all(b <= a for a, b in zip(values, values[1:])))

    def test_comma_population_best_can_worsen_but_archive_cannot(self):
        result = self.run_es("comma", 2)
        values = [v for _, v in result["population_best"]]
        self.assertTrue(any(b > a for a, b in zip(values, values[1:])))
        self.assertLessEqual(result["best_variance"], min(values))

    def test_same_seed_same_result(self):
        for selection in ("plus", "comma"):
            a, b = self.run_es(selection, 5, 1000), self.run_es(selection, 5, 1000)
            self.assertEqual(a["best_weights"], b["best_weights"])
            self.assertEqual(a["history"], b["history"])


if __name__ == "__main__":
    unittest.main()