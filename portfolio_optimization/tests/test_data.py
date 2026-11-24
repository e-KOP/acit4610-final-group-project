
"""Tests for OR-Library portfolio loading and validation.

AI-assisted implementation. See docs/ai_usage.md.
"""

import math
from pathlib import Path
import unittest

from portfolio_optimization.portfolio.data import (
    load_portfolio,
    parse_portfolio_text,
)


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "portfolio_optimization" / "data" / "or_library"

EXPECTED_ASSETS = {
    "port1": 31,
    "port2": 85,
    "port3": 89,
    "port4": 98,
    "port5": 225,
}

SAMPLE = """\
2
0.01 0.1
0.02 0.2
1 1 1
1 2 0.5
2 2 1
"""


class TestPortfolioData(unittest.TestCase):

    def test_all_five_datasets(self):
        for name, expected_n in EXPECTED_ASSETS.items():
            with self.subTest(dataset=name):
                data = load_portfolio(DATA_DIR / f"{name}.txt")

                self.assertEqual(data.name, name)
                self.assertEqual(data.n_assets, expected_n)
                self.assertEqual(len(data.returns), expected_n)
                self.assertEqual(len(data.std_devs), expected_n)
                self.assertEqual(len(data.correlation), expected_n)
                self.assertEqual(len(data.covariance), expected_n)

                for i in range(expected_n):
                    self.assertEqual(len(data.covariance[i]), expected_n)
                    self.assertAlmostEqual(
                        data.correlation[i][i], 1.0, places=9
                    )
                    self.assertAlmostEqual(
                        data.covariance[i][i],
                        data.std_devs[i] ** 2,
                        places=12,
                    )

                    for j in range(expected_n):
                        self.assertEqual(
                            data.correlation[i][j],
                            data.correlation[j][i],
                        )
                        self.assertAlmostEqual(
                            data.covariance[i][j],
                            data.covariance[j][i],
                            places=12,
                        )

    def test_port1_numerical_checkpoints(self):
        data = load_portfolio(DATA_DIR / "port1.txt")
        n = data.n_assets

        equal_return = math.fsum(data.returns) / n

        equal_variance = math.fsum(
            value
            for row in data.covariance
            for value in row
        ) / (n * n)

        min_return = (
            0.5 * equal_return
            + 0.5 * max(data.returns)
        )

        self.assertAlmostEqual(
            equal_return, 0.003504064516129, places=12
        )
        self.assertAlmostEqual(
            equal_variance, 0.001130937943724, places=12
        )
        self.assertAlmostEqual(
            min_return, 0.007184532258065, places=12
        )

    def test_small_manual_example(self):
        data = parse_portfolio_text(SAMPLE, name="sample")

        self.assertEqual(data.n_assets, 2)
        self.assertEqual(data.returns, (0.01, 0.02))
        self.assertEqual(data.std_devs, (0.1, 0.2))
        self.assertEqual(data.correlation[0][1], 0.5)
        self.assertEqual(data.correlation[1][0], 0.5)

        self.assertAlmostEqual(data.covariance[0][0], 0.01)
        self.assertAlmostEqual(data.covariance[0][1], 0.01)
        self.assertAlmostEqual(data.covariance[1][1], 0.04)

    def test_incomplete_file(self):
        text = SAMPLE.replace("2 2 1\n", "")

        with self.assertRaisesRegex(ValueError, "Expected"):
            parse_portfolio_text(text)

    def test_duplicate_correlation(self):
        text = SAMPLE.replace("2 2 1", "1 2 0.5")

        with self.assertRaisesRegex(ValueError, "duplicate"):
            parse_portfolio_text(text)

    def test_invalid_correlation_index(self):
        text = SAMPLE.replace("1 2 0.5", "1 3 0.5")

        with self.assertRaisesRegex(ValueError, "out of range"):
            parse_portfolio_text(text)

    def test_invalid_correlation_value(self):
        text = SAMPLE.replace("1 2 0.5", "1 2 1.5")

        with self.assertRaisesRegex(ValueError, "correlation"):
            parse_portfolio_text(text)

    def test_invalid_diagonal(self):
        text = SAMPLE.replace("1 1 1", "1 1 0.9")

        with self.assertRaisesRegex(ValueError, "diagonal"):
            parse_portfolio_text(text)

    def test_nonfinite_asset_input(self):
        text = SAMPLE.replace("0.01 0.1", "nan 0.1")

        with self.assertRaisesRegex(ValueError, "non-finite"):
            parse_portfolio_text(text)

    def test_negative_standard_deviation(self):
        text = SAMPLE.replace("0.01 0.1", "0.01 -0.1")

        with self.assertRaisesRegex(ValueError, "negative"):
            parse_portfolio_text(text)

    def test_invalid_asset_count(self):
        text = SAMPLE.replace("2\n", "0\n", 1)

        with self.assertRaisesRegex(ValueError, "positive"):
            parse_portfolio_text(text)

    def test_invalid_asset_record(self):
        text = SAMPLE.replace("0.01 0.1", "0.01")

        with self.assertRaisesRegex(ValueError, "standard deviation"):
            parse_portfolio_text(text)


if __name__ == "__main__":
    unittest.main()
