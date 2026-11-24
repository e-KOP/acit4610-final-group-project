
"""Tests for portfolio ES summaries and convergence plots.

AI-assisted implementation. See docs/ai_usage.md.
"""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from portfolio_optimization.portfolio.data import (
    load_portfolio,
)
from portfolio_optimization.portfolio.evaluation import (
    expected_return,
    portfolio_variance,
    minimum_return_target,
)
from portfolio_optimization.portfolio.output import (
    generate_outputs,
    read_records,
    summarise_records,
    validate_records,
)


def make_record(
    name="port1",
    variant="one_plus_one",
    seed=0,
    budget=5,
):
    """Construct a synthetic record, not a real ES result."""
    data = load_portfolio(
        f"portfolio_optimization/data/or_library/{name}.txt"
    )

    weights = [0.0] * data.n_assets

    best = max(
        range(data.n_assets),
        key=lambda i: data.returns[i],
    )

    weights[best] = 1.0

    variance = portfolio_variance(
        weights, data.covariance
    )

    history = (
        [[1, variance], [budget, variance]]
        if budget > 1
        else [[1, variance]]
    )

    return {
        "case": f"{name}_alpha050",
        "dataset": name,
        "assets": data.n_assets,
        "alpha": 0.5,
        "min_return": minimum_return_target(
            data.returns, 0.5
        ),
        "variant": variant,
        "seed": seed,
        "budget": budget,
        "evaluations": budget,
        "valid": True,
        "best_weights": weights,
        "best_return": expected_return(
            weights, data.returns
        ),
        "best_variance": variance,
        "runtime_s": 0.1,
        "history": history,
    }


class TestPortfolioOutput(unittest.TestCase):

    def test_partial_summary_and_files(self):
        records = [
            make_record(seed=0),
            make_record(seed=1),
        ]

        observed = validate_records(
            records,
            require_complete=False,
        )

        rows = summarise_records(observed)

        self.assertEqual(len(rows), 45)

        row = next(
            r for r in rows
            if r["case"] == "port1_alpha050"
            and r["variant"] == "one_plus_one"
        )

        self.assertEqual(row["runs"], 2)
        self.assertEqual(row["valid_runs"], 2)
        self.assertFalse(row["complete"])

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "runs.jsonl"

            path.write_text(
                "\n".join(
                    json.dumps(r) for r in records
                ),
                encoding="utf-8",
            )

            paths = generate_outputs(
                path,
                Path(temp) / "output",
                require_complete=False,
            )

            self.assertEqual(len(paths), 2)
            self.assertTrue(
                all(p.is_file() for p in paths)
            )

    def test_reject_duplicate(self):
        record = make_record()

        with self.assertRaisesRegex(
            ValueError, "Duplicate"
        ):
            validate_records(
                [record, record],
                require_complete=False,
            )

    def test_reject_missing_complete_study(self):
        record = make_record(budget=30000)

        with self.assertRaisesRegex(
            ValueError, "Incomplete"
        ):
            validate_records(
                [record],
                require_complete=True,
            )

    def test_reject_wrong_objective(self):
        record = make_record()
        record["best_variance"] += 0.01

        with self.assertRaisesRegex(
            ValueError, "objective"
        ):
            validate_records(
                [record],
                require_complete=False,
            )

    def test_reject_increasing_history(self):
        record = make_record()
        record["history"][1][1] += 0.01

        with self.assertRaisesRegex(
            ValueError, "history worsened"
        ):
            validate_records(
                [record],
                require_complete=False,
            )

    def test_failed_runs_excluded_from_variance(self):
        good = make_record(seed=0)
        bad = make_record(seed=1)
        bad["valid"] = False

        observed = validate_records(
            [good, bad],
            require_complete=False,
        )

        row = next(
            r for r in summarise_records(observed)
            if r["case"] == "port1_alpha050"
            and r["variant"] == "one_plus_one"
        )

        self.assertEqual(row["valid_runs"], 1)
        self.assertEqual(row["valid_rate"], 0.5)
        self.assertIsNone(row["sd_variance"])
        self.assertAlmostEqual(
            row["mean_runtime_s"], 0.1
        )

    @unittest.skipUnless(
        importlib.util.find_spec("matplotlib"),
        "matplotlib not installed",
    )
    def test_port5_plot_with_partial_study(self):
        records = [
            make_record(
                name="port5",
                variant=variant,
                seed=seed,
            )
            for variant in (
                "one_plus_one",
                "mu_plus_lambda",
                "mu_comma_lambda",
            )
            for seed in (0, 1)
        ]

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "runs.jsonl"

            path.write_text(
                "\n".join(
                    json.dumps(r) for r in records
                ),
                encoding="utf-8",
            )

            paths = generate_outputs(
                path,
                Path(temp) / "output",
                require_complete=False,
            )

            self.assertEqual(len(paths), 3)
            self.assertTrue(paths[-1].is_file())

    def test_invalid_json(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.jsonl"
            path.write_text(
                "{broken",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ValueError, "Invalid JSON"
            ):
                read_records(path)


if __name__ == "__main__":
    unittest.main()
