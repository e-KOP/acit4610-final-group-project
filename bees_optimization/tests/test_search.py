"""AI-generated checks of actual evaluations and retention; see docs/ai_usage.md."""
import random
import unittest

from bees_optimization.bees.search import recruit_neighbors, run_bees
from bees_optimization.bees.algorithm import bees_algorithm
from bees_optimization.bees.continuous import continuous_bees


class TestSharedSearch(unittest.TestCase):
    def test_every_call_counts_and_history_matches_observed_minima(self):
        for budget in range(3, 17):
            with self.subTest(budget=budget):
                observed = []

                def objective(point):
                    value = point[0] ** 2
                    observed.append(value)
                    return value

                result = run_bees(
                    objective, lambda rng: [rng.uniform(-2, 2)],
                    lambda x, rng: [x[0] + rng.uniform(-1, 1)], seed=8,
                    n_scouts=3, n_selected=2, n_elite=1,
                    n_elite_recruits=2, n_other_recruits=1, max_evaluations=budget,
                )
                self.assertEqual(len(observed), budget)
                self.assertEqual(result["evaluations"], budget)
                self.assertEqual(result["history"],
                                 [(i, min(observed[:i])) for i in range(3, budget + 1)])
                self.assertEqual(result["best_value"], min(observed))
                self.assertEqual(result["best_solution"][0] ** 2, min(observed))

    def test_minimum_or_rejected_neighbors_do_not_stop_budget(self):
        evaluations = []

        def constant_objective(point):
            evaluations.append(point.copy())
            return 0

        result = run_bees(constant_objective, lambda rng: [1], lambda x, rng: [2],
                          seed=0, max_evaluations=30000)
        self.assertEqual(len(evaluations), 30000)
        self.assertEqual(result["history"][-1], (30000, 0))
        self.assertIn([2], evaluations)

    def test_recruits_use_original_site_and_keep_best(self):
        origins = []
        proposals = iter(([8], [12], [9]))

        def move(point, rng):
            origins.append(point.copy())
            return next(proposals)

        original = [10]
        winner, used, history = recruit_neighbors(
            (original, 10), 3, lambda x: x[0], move, random.Random(0))
        self.assertEqual(origins, [[10], [10], [10]])
        self.assertEqual(original, [10])
        self.assertEqual(winner, ([8], 8))
        self.assertEqual((used, history), (3, [8, 8, 8]))

    def test_scout_only_and_no_fresh_scout_boundaries(self):
        for selected, elite in ((0, 0), (3, 0), (3, 3)):
            result = run_bees(lambda x: x[0], lambda rng: [rng.random()],
                              lambda x, rng: [rng.random()], seed=1,
                              n_scouts=3, n_selected=selected, n_elite=elite,
                              n_elite_recruits=1, n_other_recruits=1, max_evaluations=17)
            self.assertEqual(result["evaluations"], 17)
            self.assertEqual(result["history"][-1][0], 17)

    def test_both_adapters_reject_invalid_settings(self):
        matrix = [[0, 1, 2], [1, 0, 3], [2, 3, 0]]
        invalid = [
            {"n_scouts": 0}, {"n_scouts": 2.5}, {"n_scouts": True},
            {"n_selected": -1}, {"n_selected": 31}, {"n_selected": 1.5},
            {"n_elite": -1}, {"n_elite": 11}, {"n_elite": 1.5},
            {"n_elite_recruits": -1}, {"n_elite_recruits": 0},
            {"n_other_recruits": -1}, {"n_other_recruits": 0},
            {"n_elite_recruits": 1.5}, {"n_other_recruits": 1.5},
            {"max_evaluations": 29}, {"max_evaluations": 30.5},
            {"n_selected": 0, "n_elite": 0, "n_elite_recruits": -1},
        ]
        for settings in invalid:
            for name, run in (
                ("tsp", lambda: bees_algorithm(matrix, "swap", 0, **settings)),
                ("continuous", lambda: continuous_bees("sphere", 10, 0, **settings)),
            ):
                with self.subTest(adapter=name, settings=settings), self.assertRaises(ValueError):
                    run()


if __name__ == "__main__":
    unittest.main()
