"""AI-generated TSP input, operator, and regression tests; see docs/ai_usage.md."""
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import Mock

from bees_optimization.bees.algorithm import bees_algorithm
from bees_optimization.bees.neighborhoods import swap_neighbor, reverse_neighbor
from bees_optimization.bees.tsplib import (
    load_tsplib, validate_tsplib, calculate_distance, create_distance_matrix,
    calculate_tour_length, validate_tour,
)


DATA = Path(__file__).resolve().parents[1] / "data" / "tsplib"
SAMPLE = """NAME : triangle
TYPE : TSP
DIMENSION : 3
EDGE_WEIGHT_TYPE : EUC_2D
NODE_COORD_SECTION
1 0 0
2 3 0
3 0 4
EOF
"""


class TestTSPData(unittest.TestCase):
    def parse(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.tsp"
            path.write_text(text)
            metadata, coordinates = load_tsplib(path)
        validate_tsplib(metadata, coordinates)
        return metadata, coordinates

    def test_all_six_original_instances(self):
        for name, size in (("eil51", 51), ("berlin52", 52), ("st70", 70),
                           ("eil76", 76), ("kroA100", 100), ("ch150", 150)):
            with self.subTest(name=name):
                metadata, coordinates = load_tsplib(DATA / f"{name}.tsp")
                self.assertTrue(validate_tsplib(metadata, coordinates))
                self.assertEqual(len(coordinates), size)

    def test_whitespace_and_metadata(self):
        metadata, coordinates = self.parse(SAMPLE.replace(" : ", ":").replace("1 0 0", " 1\t0\t0 "))
        self.assertEqual(metadata["NAME"], "triangle")
        self.assertEqual(coordinates, {1: (0, 0), 2: (3, 0), 3: (0, 4)})

    def test_rejects_malformed_input(self):
        invalid = [
            SAMPLE.replace("NODE_COORD_SECTION\n", ""),
            SAMPLE.replace("NODE_COORD_SECTION", "NODE_COORD_SECTION\nNODE_COORD_SECTION"),
            SAMPLE.replace("NAME : triangle\n", ""),
            SAMPLE.replace("TYPE : TSP", "TYPE : ATSP"),
            SAMPLE.replace("EUC_2D", "GEO"),
            SAMPLE.replace("DIMENSION : 3", "DIMENSION : 4"),
            SAMPLE.replace("DIMENSION : 3", "DIMENSION : 0"),
            SAMPLE.replace("3 0 4", "2 0 4"),
            SAMPLE.replace("3 0 4", "4 0 4"),
            SAMPLE.replace("3 0 4", "3 0"),
            SAMPLE.replace("3 0 4", "3 0 4 5"),
            SAMPLE.replace("3 0 4", "3 nan 4"),
            SAMPLE.replace("3 0 4", "3 0 inf"),
        ]
        for text in invalid:
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.parse(text)

    def test_rounding_matrix_and_return_edge(self):
        self.assertEqual(calculate_distance((0, 0), (2.5, 0)), 3)
        self.assertEqual(calculate_distance((0, 0), (2.49, 0)), 2)
        _, coordinates = self.parse(SAMPLE)
        matrix = create_distance_matrix(coordinates)
        self.assertEqual(matrix, [[0, 3, 4], [3, 0, 5], [4, 5, 0]])
        self.assertEqual(calculate_tour_length([1, 2, 3], matrix), 12)
        self.assertEqual(calculate_tour_length([1, 3, 2], matrix), 12)
        # Round each edge before summing, rather than rounding the perimeter.
        matrix = create_distance_matrix({1: (0, 0), 2: (1, 1), 3: (2, 0)})
        self.assertEqual(calculate_tour_length([1, 2, 3], matrix), 4)

    def test_invalid_tours(self):
        for tour in ([1, 2], [2, 1, 3], [1, 2, 2], [1, 2, 4], [1, 2, 3, 1]):
            with self.subTest(tour=tour), self.assertRaises(ValueError):
                validate_tour(tour, 3)

    def test_operators_change_only_selected_positions(self):
        original = [1, 2, 3, 4, 5, 6]
        rng = Mock()
        rng.sample.return_value = [1, 4]
        self.assertEqual(swap_neighbor(original, rng), [1, 5, 3, 4, 2, 6])
        self.assertEqual(reverse_neighbor(original, rng), [1, 5, 4, 3, 2, 6])
        self.assertEqual(original, [1, 2, 3, 4, 5, 6])
        for move in (swap_neighbor, reverse_neighbor):
            rng = random.Random(0)
            for n in (3, 51):
                tour = list(range(1, n + 1))
                for _ in range(100):
                    tour = move(tour, rng)
                    self.assertTrue(validate_tour(tour, n))
            with self.assertRaises(ValueError):
                move([1, 2], rng)

    def test_full_budget_preserves_existing_tsp_results(self):
        _, coordinates = load_tsplib(DATA / "eil51.tsp")
        matrix = create_distance_matrix(coordinates)
        for move, expected in (("swap", 622), ("reverse", 468), ("segment_reversal", 468)):
            with self.subTest(move=move):
                result = bees_algorithm(matrix, move, seed=42)
                self.assertEqual(result["evaluations"], 30000)
                self.assertEqual(result["initial_best"], 1352)
                self.assertEqual(result["best_length"], expected)
                self.assertEqual(calculate_tour_length(result["best_tour"], matrix), expected)
                self.assertEqual(result["history"][-1], (30000, expected))

    def test_rejects_invalid_distance_matrices(self):
        for matrix in ([], [[0, 1], [1, 0]], [[0, 1, 2], [1], [2, 3, 0]],
                       [[0, float("nan"), 2], [1, 0, 3], [2, 3, 0]],
                       [[0, -1, 2], [1, 0, 3], [2, 3, 0]]):
            with self.subTest(matrix=matrix), self.assertRaises(ValueError):
                bees_algorithm(matrix, "swap", seed=0)


if __name__ == "__main__":
    unittest.main()
