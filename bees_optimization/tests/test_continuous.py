"""AI-generated numerical and search-invariant tests; see docs/ai_usage.md."""
import json
import math
from pathlib import Path
import random
import unittest
from unittest.mock import Mock

from bees_optimization.bees.continuous import (
    continuous_bees, continuous_neighbor, random_vector,
    NEIGHBORHOOD_RANGE_FRACTION,
)
from bees_optimization.bees.functions import (
    BENCHMARKS, sphere, rosenbrock, rastrigin, ackley,
)


class TestBenchmarkFunctions(unittest.TestCase):
    def test_minimizers_at_required_dimensions(self):
        for dimension in (10, 30):
            for name, benchmark in BENCHMARKS.items():
                with self.subTest(function=name, dimension=dimension):
                    point = [1.0 if name == "rosenbrock" else 0.0] * dimension
                    self.assertAlmostEqual(benchmark.objective(point), 0.0, places=12)

    def test_known_nonoptimal_values(self):
        # Hand-calculated values also exercise adjacent pairs and cosine terms.
        self.assertEqual(sphere([1, -2, 3]), 14)
        self.assertAlmostEqual(rosenbrock([-1.2, 1]), 24.2)
        self.assertEqual(rosenbrock([1, 2, 3]), 201)
        self.assertAlmostEqual(rastrigin([0.5, -0.5]), 40.5)
        self.assertAlmostEqual(ackley([1, -1]), 3.625384938440362)
        self.assertAlmostEqual(ackley([0.5, -0.5]), 4.253654026568412)

    def test_invalid_vectors(self):
        for benchmark in BENCHMARKS.values():
            for point in ([], [math.nan, 0], [math.inf, 0]):
                with self.subTest(objective=benchmark.objective.__name__, point=point):
                    with self.assertRaises(ValueError):
                        benchmark.objective(point)
        with self.assertRaises(ValueError):
            rosenbrock([1])

    def test_bounds_match_assignment_configuration(self):
        path = Path(__file__).resolve().parents[1] / "configs" / "continuous.json"
        config = json.loads(path.read_text())
        self.assertEqual(set(BENCHMARKS), {f["name"] for f in config["functions"]})
        for function in config["functions"]:
            self.assertEqual(BENCHMARKS[function["name"]].bounds, tuple(function["bounds"]))
        self.assertEqual(NEIGHBORHOOD_RANGE_FRACTION, config["neighborhood_range_fraction"])
        self.assertEqual(config["bounds_handling"], "clip")


class TestContinuousSearch(unittest.TestCase):
    def test_initialization_uses_independent_uniform_coordinates(self):
        rng = Mock()
        rng.uniform.side_effect = [-5, 2, 10]
        self.assertEqual(random_vector(3, (-5, 10), rng), [-5, 2, 10])
        self.assertEqual(rng.uniform.call_count, 3)
        self.assertTrue(all(call.args == (-5, 10) for call in rng.uniform.call_args_list))

    def test_neighbor_perturbs_every_coordinate_and_clips(self):
        original = [-5.0, 10.0, 0.0]
        rng = Mock()
        rng.uniform.side_effect = [-1.5, 1.5, 0.75]
        self.assertEqual(continuous_neighbor(original, (-5, 10), rng), [-5, 10, 0.75])
        self.assertEqual(original, [-5, 10, 0])
        self.assertEqual(rng.uniform.call_count, 3)
        self.assertTrue(all(call.args == (-1.5, 1.5) for call in rng.uniform.call_args_list))

    def test_initialization_and_neighbors_stay_in_each_domain(self):
        rng = random.Random(73)
        for benchmark in BENCHMARKS.values():
            low, high = benchmark.bounds
            for dimension in (10, 30):
                point = random_vector(dimension, benchmark.bounds, rng)
                self.assertEqual(len(point), dimension)
                self.assertTrue(all(low <= v <= high for v in point))
                for _ in range(100):
                    neighbor = continuous_neighbor(point, benchmark.bounds, rng)
                    self.assertTrue(all(low <= v <= high for v in neighbor))
                    self.assertTrue(all(abs(a - b) <= 0.1 * (high - low) + 1e-12
                                        for a, b in zip(point, neighbor)))
                    point = neighbor

    def test_all_benchmarks_are_reproducible_and_consistent(self):
        for name, benchmark in BENCHMARKS.items():
            for dimension in (10, 30):
                with self.subTest(function=name, dimension=dimension):
                    result = continuous_bees(name, dimension, seed=42, max_evaluations=1000)
                    self.assertEqual(result, continuous_bees(name, dimension, 42, max_evaluations=1000))
                    self.assertEqual(result["evaluations"], 1000)
                    self.assertEqual(len(result["best_vector"]), dimension)
                    self.assertEqual(benchmark.objective(result["best_vector"]), result["best_value"])
                    self.assertTrue(math.isfinite(result["best_value"]))
                    self.assertLessEqual(result["best_value"], result["initial_best"])
                    self.assertEqual([n for n, _ in result["history"]], list(range(30, 1001)))
                    values = [value for _, value in result["history"]]
                    self.assertTrue(all(a >= b for a, b in zip(values, values[1:])))
                    self.assertEqual(values[-1], result["best_value"])
                    low, high = benchmark.bounds
                    self.assertTrue(all(low <= v <= high for v in result["best_vector"]))

    def test_invalid_problem_specification(self):
        for name, dimension in (("unknown", 10), ("sphere", 0), ("sphere", 2),
                                ("sphere", 10.0), ("sphere", True)):
            with self.subTest(name=name, dimension=dimension), self.assertRaises(ValueError):
                continuous_bees(name, dimension, seed=0)


if __name__ == "__main__":
    unittest.main()
