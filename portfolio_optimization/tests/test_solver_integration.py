"""Integration tests: all three ES variants on all 15 assignment cases.

AI-generated with Claude (Anthropic), built step by step with and reviewed by
Jakob Andreas Amtedal; see docs/ai_usage.md.

Every combination of 5 datasets x 3 alpha values x 3 variants is run once
(seed 0, 1,000 evaluations) and checked independently with the shared
evaluation and feasibility functions. Run from the repository root:
    python -m unittest portfolio_optimization.tests.test_solver_integration -v
"""
import math
import unittest
from pathlib import Path

from portfolio_optimization.portfolio import population_es as pes
from portfolio_optimization.portfolio.data import load_portfolio
from portfolio_optimization.portfolio.evaluation import (
    expected_return, minimum_return_target, portfolio_variance,
)
from portfolio_optimization.portfolio.experiments import run_case
from portfolio_optimization.portfolio.feasibility import is_feasible
from portfolio_optimization.portfolio.one_plus_one import Archive, solve_one_plus_one

DATA = Path(__file__).resolve().parents[1] / "data" / "or_library"
DATASETS = ("port1", "port2", "port3", "port4", "port5")
ALPHAS = (0.25, 0.50, 0.75)
VARIANTS = ("one_plus_one", "mu_plus_lambda", "mu_comma_lambda")
SEED = 0
BUDGET = 1000
TOL = 1e-8
# Population ES: 10 initial + 14 full generations of 70 + a partial batch of 10
GENERATION_CHECKPOINTS = [10 + 70 * g for g in range(15)]


def solve(variant, data, target, seed=SEED, budget=BUDGET):
    if variant == "one_plus_one":
        return solve_one_plus_one(data.returns, data.covariance, target, seed, budget)
    selection = "plus" if variant == "mu_plus_lambda" else "comma"
    return pes.solve_population(data.returns, data.covariance, target, seed,
                                selection, budget)


def solve_recording(variant, data, target):
    """Solve while recording the variance of every evaluated candidate, in order."""
    variances = []
    original = Archive.evaluate

    def recording(self, weights):
        value = original(self, weights)
        variances.append(value)
        return value

    Archive.evaluate = recording
    try:
        result = solve(variant, data, target)
    finally:
        Archive.evaluate = original
    return result, variances


class TestAllCases(unittest.TestCase):
    """Run every case and variant once, then check each result independently."""

    @classmethod
    def setUpClass(cls):
        cls.data = {name: load_portfolio(DATA / f"{name}.txt") for name in DATASETS}
        cls.runs = {}
        for name, data in cls.data.items():
            for alpha in ALPHAS:
                target = minimum_return_target(data.returns, alpha)
                for variant in VARIANTS:
                    result, variances = solve_recording(variant, data, target)
                    cls.runs[name, alpha, variant] = (target, result, variances)

    def cases(self):
        """(label, data, alpha, variant, target, result, variances) for all 45 runs."""
        return [
            (f"{name}_alpha{round(alpha * 100):03d} {variant}", self.data[name],
             alpha, variant, target, result, variances)
            for (name, alpha, variant), (target, result, variances) in self.runs.items()
        ]

    def test_all_45_combinations_ran(self):
        self.assertEqual(len(self.runs), 5 * 3 * 3)

    def test_exact_evaluation_budget(self):
        for label, _, _, _, _, result, variances in self.cases():
            with self.subTest(label):
                self.assertEqual(result["evaluations"], BUDGET)
                self.assertEqual(len(variances), BUDGET)
                self.assertEqual(len(result["history"]), BUDGET)

    def test_weights_are_feasible(self):
        for label, data, _, _, target, result, _ in self.cases():
            with self.subTest(label):
                weights = result["best_weights"]
                self.assertTrue(result["feasible"])
                self.assertEqual(len(weights), data.n_assets)
                self.assertTrue(all(w >= -TOL for w in weights))
                self.assertLessEqual(abs(math.fsum(weights) - 1.0), TOL)
                self.assertTrue(is_feasible(weights, data.returns, target))

    def test_return_constraint(self):
        for label, data, _, _, target, result, _ in self.cases():
            with self.subTest(label):
                achieved = expected_return(result["best_weights"], data.returns)
                self.assertGreaterEqual(achieved, target - TOL)
                self.assertTrue(math.isclose(achieved, result["best_return"],
                                             rel_tol=1e-9, abs_tol=1e-15))

    def test_reported_variance_matches_independent_recomputation(self):
        for label, data, _, _, _, result, _ in self.cases():
            with self.subTest(label):
                recomputed = portfolio_variance(result["best_weights"], data.covariance)
                self.assertTrue(math.isclose(recomputed, result["best_variance"],
                                             rel_tol=1e-9, abs_tol=1e-15))
                self.assertTrue(math.isfinite(result["best_variance"]))
                self.assertGreater(result["best_variance"], 0.0)

    def test_archive_history(self):
        for label, _, _, variant, _, result, variances in self.cases():
            with self.subTest(label):
                history = result["history"]
                self.assertEqual([e for e, _ in history], list(range(1, BUDGET + 1)))
                values = [v for _, v in history]
                # never worsens, and equals the running minimum of all evaluations
                running, minimum = [], math.inf
                for v in variances:
                    minimum = min(minimum, v)
                    running.append(minimum)
                self.assertEqual(values, running)
                # initial_best is the archive after initialization: 1 evaluation
                # for (1+1)-ES, 10 for the population variants
                initialized = 1 if variant == "one_plus_one" else 10
                self.assertEqual(values[initialized - 1], result["initial_best"])
                self.assertEqual(values[-1], result["best_variance"])
                self.assertLessEqual(result["best_variance"], result["initial_best"])

    def test_archive_best_is_the_minimum_evaluated_variance(self):
        for label, _, _, _, _, result, variances in self.cases():
            with self.subTest(label):
                self.assertEqual(result["best_variance"], min(variances))

    def test_alpha_075_targets(self):
        """Highest targets: closest to r_max, so the return repair is most active."""
        for (name, alpha, variant), (target, result, _) in self.runs.items():
            if alpha != 0.75:
                continue
            with self.subTest(case=name, variant=variant):
                data = self.data[name]
                self.assertLess(target, max(data.returns))
                achieved = expected_return(result["best_weights"], data.returns)
                self.assertGreaterEqual(achieved, target - TOL)
                # the best asset must carry real weight to reach such a target
                best_asset = data.returns.index(max(data.returns))
                self.assertGreater(result["best_weights"][best_asset], 0.0)

    def test_generation_checkpoints(self):
        for label, _, _, variant, _, result, _ in self.cases():
            with self.subTest(label):
                if variant == "one_plus_one":
                    self.assertNotIn("population_best", result)
                    continue
                checkpoints = [e for e, _ in result["population_best"]]
                self.assertEqual(checkpoints, GENERATION_CHECKPOINTS)

    def test_plus_and_comma_survivor_selection(self):
        """Plus keeps the best of parents + offspring, comma the best of offspring only.

        With the same seed both variants make identical draws until the first
        selection, so the first 80 evaluated variances are the same. After that
        first generation:
            plus  population best = min(all 80 candidates)
            comma population best = min(the 70 offspring only)
        """
        for name in DATASETS:
            for alpha in ALPHAS:
                with self.subTest(case=f"{name}_alpha{round(alpha * 100):03d}"):
                    _, plus, plus_vars = self.runs[name, alpha, "mu_plus_lambda"]
                    _, comma, comma_vars = self.runs[name, alpha, "mu_comma_lambda"]
                    self.assertEqual(plus_vars[:80], comma_vars[:80])
                    self.assertEqual(plus["population_best"][1][1], min(plus_vars[:80]))
                    self.assertEqual(comma["population_best"][1][1], min(comma_vars[10:80]))

                    plus_values = [v for _, v in plus["population_best"]]
                    self.assertTrue(all(b <= a for a, b in zip(plus_values, plus_values[1:])))
                    comma_values = [v for _, v in comma["population_best"]]
                    self.assertLessEqual(comma["best_variance"], min(comma_values))

    def test_comma_population_best_worsens_somewhere(self):
        """At least one comma run loses its best parent, which plus never does."""
        worsened = 0
        for name in DATASETS:
            for alpha in ALPHAS:
                _, comma, _ = self.runs[name, alpha, "mu_comma_lambda"]
                values = [v for _, v in comma["population_best"]]
                worsened += any(b > a for a, b in zip(values, values[1:]))
        self.assertGreater(worsened, 0)

    def test_runner_accepts_every_result(self):
        """The experiment runner's independent checks accept all 45 combinations."""
        for name, data in self.data.items():
            for alpha in ALPHAS:
                for variant in VARIANTS:
                    with self.subTest(case=name, alpha=alpha, variant=variant):
                        record = run_case(data, alpha, variant, SEED, BUDGET)
                        _, result, _ = self.runs[name, alpha, variant]
                        self.assertTrue(math.isclose(record["best_variance"],
                                                     result["best_variance"], rel_tol=1e-9))


class TestReproducibility(unittest.TestCase):
    def test_same_seed_same_run_on_every_dataset(self):
        for name in DATASETS:
            data = load_portfolio(DATA / f"{name}.txt")
            target = minimum_return_target(data.returns, 0.75)
            for variant in VARIANTS:
                with self.subTest(dataset=name, variant=variant):
                    first = solve(variant, data, target, seed=3, budget=300)
                    second = solve(variant, data, target, seed=3, budget=300)
                    self.assertEqual(first, second)

    def test_different_seeds_give_different_runs(self):
        data = load_portfolio(DATA / "port1.txt")
        target = minimum_return_target(data.returns, 0.5)
        for variant in VARIANTS:
            with self.subTest(variant=variant):
                a = solve(variant, data, target, seed=1, budget=300)
                b = solve(variant, data, target, seed=2, budget=300)
                self.assertNotEqual(a["best_weights"], b["best_weights"])


if __name__ == "__main__":
    unittest.main()