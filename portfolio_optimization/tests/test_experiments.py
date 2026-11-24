"""Tests for the portfolio experiment runner.

AI-assisted implementation. See docs/ai_usage.md.
"""

import copy
import json
import tempfile
from pathlib import Path
import unittest

from portfolio_optimization.portfolio.data import load_portfolio
from portfolio_optimization.portfolio.evaluation import (
    expected_return,
    portfolio_variance,
)
from portfolio_optimization.portfolio.experiments import (
    VARIANTS,
    run_case,
    run_selected,
)
from portfolio_optimization.portfolio.provenance import (
    metadata_path_for, verify_metadata, fingerprint,
)


DATA_DIR = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "or_library"
)


def fake_solver(returns, covariance, target, seed, budget):
    """A deterministic feasible stub, not an optimisation algorithm."""

    best = max(
        range(len(returns)),
        key=lambda i: returns[i],
    )

    weights = [0.0] * len(returns)
    weights[best] = 1.0

    variance = portfolio_variance(
        weights, covariance
    )

    return {
        "best_weights": weights,
        "best_variance": variance,
        "best_return": expected_return(
            weights, returns
        ),
        "evaluations": budget,
        "history": (
            [[1, variance], [budget, variance]]
            if budget > 1
            else [[1, variance]]
        ),
    }


class TestPortfolioExperiments(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.data = load_portfolio(
            DATA_DIR / "port1.txt"
        )

    def test_all_three_variants(self):
        for variant in VARIANTS:
            with self.subTest(variant=variant):
                record = run_case(
                    self.data,
                    0.50,
                    variant,
                    0,
                    budget=5,
                    solver=fake_solver,
                )

                self.assertEqual(
                    record["evaluations"], 5
                )
                self.assertEqual(
                    record["case"], "port1_alpha050"
                )
                self.assertTrue(record["valid"])
                self.assertEqual(
                    record["history"][-1][0], 5
                )

    def test_reject_wrong_budget(self):
        def bad(*args):
            result = fake_solver(*args)
            result["evaluations"] = 4
            return result

        with self.assertRaisesRegex(
            ValueError, "evaluation budget"
        ):
            run_case(
                self.data, 0.5,
                "one_plus_one", 0,
                budget=5, solver=bad,
            )

    def test_reject_wrong_variance(self):
        def bad(*args):
            result = fake_solver(*args)
            result["best_variance"] += 1
            return result

        with self.assertRaisesRegex(
            ValueError, "variance does not match"
        ):
            run_case(
                self.data, 0.5,
                "one_plus_one", 0,
                budget=5, solver=bad,
            )

    def test_reject_wrong_return(self):
        def bad(*args):
            result = fake_solver(*args)
            result["best_return"] += 1
            return result

        with self.assertRaisesRegex(
            ValueError, "expected return"
        ):
            run_case(
                self.data, 0.5,
                "one_plus_one", 0,
                budget=5, solver=bad,
            )

    def test_reject_infeasible_weights(self):
        def bad(*args):
            result = fake_solver(*args)
            result["best_weights"] = (
                [0.0] * self.data.n_assets
            )
            return result

        with self.assertRaisesRegex(
            ValueError, "infeasible"
        ):
            run_case(
                self.data, 0.5,
                "one_plus_one", 0,
                budget=5, solver=bad,
            )

    def test_reject_increasing_history(self):
        def bad(*args):
            result = fake_solver(*args)
            result["history"] = [
                [1, 0.01],
                [5, 0.02],
            ]
            return result

        with self.assertRaisesRegex(
            ValueError, "history worsened"
        ):
            run_case(
                self.data, 0.5,
                "one_plus_one", 0,
                budget=5, solver=bad,
            )

    def test_reject_incomplete_history(self):
        def bad(*args):
            result = fake_solver(*args)
            result["history"] = [
                result["history"][0]
            ]
            return result

        with self.assertRaisesRegex(
            ValueError, "end at the evaluation budget"
        ):
            run_case(
                self.data, 0.5,
                "one_plus_one", 0,
                budget=5, solver=bad,
            )

    def test_saved_records_and_resume(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "runs.jsonl"

            arguments = {
                "datasets": ("port1",),
                "alphas": (0.50,),
                "variants": ("one_plus_one",),
                "seeds": (0, 1),
                "budget": 5,
                "solver": fake_solver,
            }

            count = run_selected(
                path, **arguments
            )
            self.assertEqual(count, 2)

            records = [
                json.loads(line)
                for line in path.read_text(
                    encoding="utf-8"
                ).splitlines()
            ]

            self.assertEqual(len(records), 2)
            self.assertEqual(
                {r["seed"] for r in records},
                {0, 1},
            )

            with self.assertRaises(FileExistsError):
                run_selected(path, **arguments)

            count = run_selected(
                path, resume=True, **arguments
            )
            self.assertEqual(count, 0)

    def test_reject_invalid_selection(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "runs.jsonl"

            with self.assertRaises(ValueError):
                run_selected(
                    path,
                    datasets=("not_a_dataset",),
                    solver=fake_solver,
                )

    def test_preserves_comma_population_history(self):
        """Comma ES may have worsening population-best values."""

        def solver(*args):
            result = fake_solver(*args)
            value = result["best_variance"]
            result["population_best"] = [
                [10, value],
                [80, value * 1.1],
            ]
            return result

        record = run_case(
            self.data,
            0.5,
            "mu_comma_lambda",
            0,
            budget=100,
            solver=solver,
        )

        self.assertIn("population_best", record)
        self.assertEqual(len(record["population_best"]), 2)
        self.assertGreater(
            record["population_best"][1][1],
            record["population_best"][0][1],
        )

    def test_rejects_worsening_plus_population(self):
        """Plus ES must not have worsening population-best values."""

        def solver(*args):
            result = fake_solver(*args)
            value = result["best_variance"]
            result["population_best"] = [
                [10, value],
                [80, value * 1.1],
            ]
            return result

        with self.assertRaisesRegex(
            ValueError,
            "population best worsened",
        ):
            run_case(
                self.data,
                0.5,
                "mu_plus_lambda",
                0,
                budget=100,
                solver=solver,
            )

    def test_run_creates_provenance_sidecar(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "runs.jsonl"
            count = run_selected(
                path,
                datasets=("port1",), alphas=(0.5,),
                variants=("one_plus_one",), seeds=(0,),
                budget=5, solver=fake_solver,
            )
            self.assertEqual(count, 1)
            sidecar = metadata_path_for(path)
            self.assertTrue(sidecar.is_file())
            metadata = json.loads(sidecar.read_text(encoding="utf-8"))
            self.assertIn("git_revision", metadata["identity"])
            self.assertIn("source_sha256", metadata["identity"])
            self.assertIn("dataset_sha256", metadata["identity"])
            self.assertIn("config_sha256", metadata["identity"])
            self.assertEqual(metadata["fingerprint_sha256"],
                             fingerprint(metadata["identity"]))

    def test_refuse_legacy_resume_missing_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "runs.jsonl"
            path.write_text('{}\n', encoding="utf-8")
            original = path.read_bytes()
            with self.assertRaisesRegex(ValueError, "no metadata"):
                run_selected(
                    path, datasets=("port1",), alphas=(0.5,),
                    variants=("one_plus_one",), seeds=(0,),
                    budget=5, solver=fake_solver, resume=True,
                )
            self.assertEqual(path.read_bytes(), original)

    def test_resume_rejects_changed_selection_without_modifying_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "runs.jsonl"
            args = dict(datasets=("port1",), alphas=(0.5,),
                        variants=("one_plus_one",), seeds=(0,),
                        budget=5, solver=fake_solver)
            run_selected(path, **args)
            original = path.read_bytes()
            with self.assertRaisesRegex(ValueError, "incompatible experiment resume"):
                run_selected(path, **{**args, "budget": 6}, resume=True)
            self.assertEqual(path.read_bytes(), original)

    def test_resume_rejects_changed_provenance_and_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "runs.jsonl"
            args = dict(datasets=("port1",), alphas=(0.5,),
                        variants=("one_plus_one",), seeds=(0,),
                        budget=5, solver=fake_solver)
            run_selected(path, **args)
            original = path.read_bytes()
            sidecar = metadata_path_for(path)
            meta = json.loads(sidecar.read_text(encoding="utf-8"))
            meta["identity"]["config_sha256"] = "0" * 64
            sidecar.write_text(json.dumps(meta), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "fingerprint is corrupt"):
                run_selected(path, **args, resume=True)
            meta["fingerprint_sha256"] = fingerprint(meta["identity"])
            sidecar.write_text(json.dumps(meta), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "incompatible experiment resume"):
                run_selected(path, **args, resume=True)
            self.assertEqual(path.read_bytes(), original)

    def test_recover_torn_last_record_with_backup(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "runs.jsonl"
            args = dict(datasets=("port1",), alphas=(0.5,),
                        variants=("one_plus_one",), seeds=(0, 1),
                        budget=5)
            def interrupted(returns, cov, target, seed, budget):
                if seed == 1:
                    raise RuntimeError("simulated interruption")
                return fake_solver(returns, cov, target, seed, budget)
            with self.assertRaisesRegex(RuntimeError, "simulated interruption"):
                run_selected(path, **args, solver=interrupted)
            with path.open("ab") as stream:
                stream.write(b'{"seed": 1, "partial":')
            before = path.read_bytes()
            count = run_selected(path, **args, solver=fake_solver, resume=True)
            self.assertEqual(count, 1)
            records = [json.loads(line) for line in path.read_text(
                encoding="utf-8").splitlines()]
            self.assertEqual([r["seed"] for r in records], [0, 1])
            backups = list(path.parent.glob("runs.jsonl.interrupted-*.bak"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), before)

    def test_resume_appends_newline_to_complete_trailing_record(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "runs.jsonl"
            args = dict(datasets=("port1",), alphas=(0.5,),
                        variants=("one_plus_one",), seeds=(0, 1),
                        budget=5, solver=fake_solver)
            def interrupted(*args):
                if args[-2] == 1:
                    raise RuntimeError("simulated interruption")
                return fake_solver(*args)
            with self.assertRaises(RuntimeError):
                run_selected(path, **{**args, "solver": interrupted})
            path.write_bytes(path.read_bytes().rstrip(b"\n"))
            self.assertEqual(run_selected(path, **args, resume=True), 1)
            records = [json.loads(line) for line in path.read_text(
                encoding="utf-8").splitlines()]
            self.assertEqual(len(records), 2)

    def test_refuse_terminated_malformed_record_without_modification(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "runs.jsonl"
            args = dict(datasets=("port1",), alphas=(0.5,),
                        variants=("one_plus_one",), seeds=(0,),
                        budget=5, solver=fake_solver)
            run_selected(path, **args)
            with path.open("ab") as stream:
                stream.write(b"{not valid JSON}\n")
            original = path.read_bytes()
            with self.assertRaisesRegex(ValueError, "Corrupted JSONL"):
                run_selected(path, **args, resume=True)
            self.assertEqual(path.read_bytes(), original)

    def test_resume_rejects_corrupted_completed_objective(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "runs.jsonl"
            args = dict(datasets=("port1",), alphas=(0.5,),
                        variants=("one_plus_one",), seeds=(0,),
                        budget=5, solver=fake_solver)
            run_selected(path, **args)
            record = json.loads(path.read_text(encoding="utf-8"))
            record["best_variance"] += 0.1
            path.write_text(json.dumps(record) + "\n", encoding="utf-8")
            original = path.read_bytes()
            with self.assertRaises(ValueError):
                run_selected(path, **args, resume=True)
            self.assertEqual(path.read_bytes(), original)



if __name__ == "__main__":
    unittest.main()
