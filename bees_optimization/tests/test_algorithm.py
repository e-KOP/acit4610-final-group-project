import random
import unittest
from pathlib import Path

from bees_optimization.bees.algorithm import (
    select_sites,
    recruit_neighbors,
    bees_algorithm,
)

from bees_optimization.bees.tsplib import (
    load_tsplib,
    validate_tsplib,
    create_distance_matrix,
    calculate_tour_length,
    validate_tour,
)


DATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "data" / "tsplib" / "eil51.tsp"
)


class TestBeesAlgorithm(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        metadata, coordinates = load_tsplib(DATA_PATH)
        validate_tsplib(metadata, coordinates)
        cls.matrix = create_distance_matrix(coordinates)

    def test_site_selection(self):
        population = [
            ([1, 2, 3, 4], 150),
            ([1, 3, 2, 4], 120),
            ([1, 4, 2, 3], 140),
            ([1, 2, 4, 3], 100),
            ([1, 3, 4, 2], 130),
        ]

        elite, other = select_sites(population, 3, 1)

        self.assertEqual(
            [length for _, length in elite], [100]
        )
        self.assertEqual(
            [length for _, length in other], [120, 130]
        )

    def test_recruitment(self):
        original = list(range(1, 52))
        original_length = calculate_tour_length(
            original, self.matrix
        )

        for neighborhood in ("swap", "reverse"):
            with self.subTest(neighborhood=neighborhood):
                winner, evaluations, history = recruit_neighbors(
                    (original, original_length),
                    20,
                    self.matrix,
                    neighborhood,
                    random.Random(42),
                )

                self.assertEqual(evaluations, 20)
                self.assertEqual(len(history), 20)
                self.assertLessEqual(
                    winner[1], original_length
                )
                self.assertTrue(validate_tour(winner[0], 51))
                self.assertEqual(
                    calculate_tour_length(
                        winner[0], self.matrix
                    ),
                    winner[1]
                )

        self.assertEqual(original, list(range(1, 52)))

    def test_complete_algorithm(self):
        result = bees_algorithm(
            self.matrix,
            neighborhood="swap",
            seed=42,
            max_evaluations=1000,
        )

        self.assertEqual(result["evaluations"], 1000)
        self.assertEqual(result["initial_best"], 1352)
        self.assertEqual(result["best_length"], 1098)
        self.assertTrue(
            validate_tour(result["best_tour"], 51)
        )
        self.assertEqual(
            calculate_tour_length(
                result["best_tour"], self.matrix
            ),
            result["best_length"]
        )

    def test_evaluation_history(self):
        result = bees_algorithm(
            self.matrix,
            neighborhood="swap",
            seed=42,
            max_evaluations=1000,
        )

        history = result["history"]

        self.assertEqual(history[0][0], 30)
        self.assertEqual(history[-1][0], 1000)
        self.assertEqual(len(history), 971)
        self.assertEqual(
            history[-1][1], result["best_length"]
        )

        for previous, current in zip(
            history, history[1:]
        ):
            self.assertEqual(
                current[0], previous[0] + 1
            )
            self.assertLessEqual(
                current[1], previous[1]
            )

    def test_partial_iteration(self):
        for budget in (30, 31, 37, 100):
            with self.subTest(budget=budget):
                result = bees_algorithm(
                    self.matrix,
                    neighborhood="swap",
                    seed=42,
                    max_evaluations=budget,
                )

                self.assertEqual(
                    result["evaluations"], budget
                )
                self.assertEqual(
                    result["history"][-1][0], budget
                )

    def test_invalid_parameters(self):
        with self.assertRaises(ValueError):
            bees_algorithm(
                self.matrix,
                neighborhood="invalid",
                seed=42,
                max_evaluations=100,
            )


if __name__ == "__main__":
    unittest.main()
