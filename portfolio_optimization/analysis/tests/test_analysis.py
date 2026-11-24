"""Tests for the read-only portfolio ES analysis.

AI-generated with Claude (Anthropic), built step by step with and reviewed by
Jakob Andreas Amtedal; see docs/ai_usage.md.

Run from the repository root:
    python -m unittest discover -s portfolio_optimization/analysis/tests -v
"""
import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path

from portfolio_optimization.analysis import compare
from portfolio_optimization.analysis.__main__ import analyse
from portfolio_optimization.portfolio.data import load_portfolio
from portfolio_optimization.portfolio.experiments import run_case

DATA = Path(__file__).resolve().parents[2] / "data" / "or_library"


def record(variance, seed=0, variant="mu_plus_lambda", dataset="port1", alpha=0.5,
           history=None, weights=(0.5, 0.5, 0.0), best_return=0.02, min_return=0.01,
           population_best=None, budget=100):
    rec = {"dataset": dataset, "alpha": alpha, "variant": variant, "seed": seed,
           "assets": len(weights), "min_return": min_return, "budget": budget,
           "best_variance": variance, "best_return": best_return,
           "best_weights": list(weights), "runtime_s": 1.0, "valid": True,
           "history": history or [[1, 2 * variance], [50, variance], [budget, variance]]}
    if population_best is not None:
        rec["population_best"] = population_best
    return rec


class TestStatistics(unittest.TestCase):
    def test_ranks_share_ties(self):
        self.assertEqual(compare._ranks([3.0, 1.0, 3.0, 2.0]), [3.5, 1.0, 3.5, 2.0])

    def test_wilcoxon_known_values(self):
        # three positive differences: W+ = 6, only 2 of 8 sign patterns are as extreme
        self.assertEqual(compare.wilcoxon_exact([1, 2, 3]), (6.0, 3, 0.25))
        # ten negative differences: the smallest possible two-sided p, 2 / 2^10
        _, n, p = compare.wilcoxon_exact([-x for x in range(1, 11)])
        self.assertEqual((n, p), (10, 2 / 1024))
        # zeros are dropped; all-zero gives no test
        self.assertEqual(compare.wilcoxon_exact([0, 0]), (0.0, 0, None))
        _, n, _ = compare.wilcoxon_exact([0, 1, -2])
        self.assertEqual(n, 2)

    def test_wilcoxon_balanced_differences_give_p_one(self):
        _, _, p = compare.wilcoxon_exact([1, -1, 2, -2])
        self.assertEqual(p, 1.0)

    def test_sign_test(self):
        self.assertEqual(compare.sign_test(10, 0), 2 / 1024)
        self.assertEqual(compare.sign_test(5, 5), 1.0)
        self.assertIsNone(compare.sign_test(0, 0))


class TestRunDiagnostics(unittest.TestCase):
    def test_sparsity(self):
        self.assertEqual(compare.held_assets([0.5, 0.5, 0.0, 1e-12]), 2)
        self.assertAlmostEqual(compare.effective_assets([0.25] * 4), 4.0)
        self.assertAlmostEqual(compare.effective_assets([1.0, 0.0]), 1.0)

    def test_convergence_and_stagnation(self):
        # improvements at 1 (100), 10 (20), 60 (11), 90 (10); budget 100
        rec = record(10.0, history=[[1, 100.0], [10, 20.0], [60, 11.0], [90, 10.0], [100, 10.0]])
        d = compare.run_diagnostics(rec)
        self.assertEqual(d["last_improvement"], 90)
        # 99% of the gain 90 means reaching 10 + 0.9 = 10.9 -> first at evaluation 90
        self.assertEqual(d["eval_99pct"], 90)
        # value at 50 is 20; final 10 -> 50% gained in the second half
        self.assertAlmostEqual(d["second_half_gain_pct"], 50.0)

    def test_return_constraint_activity(self):
        self.assertTrue(compare.run_diagnostics(
            record(1.0, best_return=0.01, min_return=0.01))["return_active"])
        self.assertFalse(compare.run_diagnostics(
            record(1.0, best_return=0.02, min_return=0.01))["return_active"])

    def test_population_worsening(self):
        rec = record(1.0, population_best=[[10, 3.0], [80, 2.0], [150, 2.5], [220, 1.0]])
        d = compare.run_diagnostics(rec)
        self.assertEqual((d["population_worsened"], d["generations"]), (1, 3))
        self.assertAlmostEqual(d["final_population_gap_pct"], 0.0)


class TestTables(unittest.TestCase):
    def setUp(self):
        runs = []
        for seed, (plus, comma, one) in enumerate([(1.0, 2.0, 4.0), (1.0, 3.0, 4.0),
                                                   (2.0, 1.0, 4.0)]):
            runs.append(record(plus, seed, "mu_plus_lambda"))
            runs.append(record(comma, seed, "mu_comma_lambda"))
            runs.append(record(one, seed, "one_plus_one"))
        self.groups = compare.group_runs(runs)

    def test_variant_summary(self):
        rows = {r["variant"]: r for r in compare.variant_summary(self.groups)}
        plus = rows["mu_plus_lambda"]
        self.assertEqual((plus["valid_runs"], plus["best_variance"]), (3, 1.0))
        self.assertAlmostEqual(plus["mean_variance"], 4 / 3)
        self.assertAlmostEqual(plus["sd_variance"], math.sqrt(1 / 3))
        self.assertEqual(plus["mean_held_assets"], 2)

    def test_paired_comparisons(self):
        rows = {(r["a"], r["b"]): r for r in compare.paired_comparisons(self.groups)}
        pc = rows["mu_plus_lambda", "mu_comma_lambda"]
        self.assertEqual((pc["a_wins"], pc["b_wins"], pc["ties"]), (2, 1, 0))
        self.assertAlmostEqual(pc["median_ratio"], 0.5)
        self.assertAlmostEqual(pc["geo_mean_ratio"], (0.5 * (1 / 3) * 2) ** (1 / 3))
        one = rows["mu_plus_lambda", "one_plus_one"]
        self.assertEqual((one["a_wins"], one["b_wins"]), (3, 0))

    def test_mean_ranks(self):
        ranks = compare.mean_ranks(self.groups)
        self.assertEqual(ranks["one_plus_one"], (3.0, 3))
        self.assertAlmostEqual(ranks["mu_plus_lambda"][0], 4 / 3)
        self.assertAlmostEqual(ranks["mu_comma_lambda"][0], 5 / 3)

    def test_invalid_runs_are_excluded(self):
        runs = [record(1.0, 0), dict(record(9.0, 1), valid=False)]
        self.assertEqual(list(compare.group_runs(runs)[("port1", 0.5, "mu_plus_lambda")]), [0])


class TestEndToEnd(unittest.TestCase):
    """Real (short) runner records -> tables and figures, raw file untouched."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.raw_dir = root / "raw"
        cls.raw_dir.mkdir()
        cls.runs = cls.raw_dir / "portfolio_runs.jsonl"
        with cls.runs.open("w", encoding="utf-8") as out:
            for name in ("port1", "port5"):
                data = load_portfolio(DATA / f"{name}.txt")
                for variant in compare.VARIANTS:
                    for seed in (0, 1):
                        out.write(json.dumps(run_case(data, 0.5, variant, seed, 300)) + "\n")
        cls.out = root / "analysis"

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_incomplete_set_needs_allow_partial(self):
        with self.assertRaises(ValueError):
            analyse(self.runs, self.out)

    def test_refuses_to_write_next_to_raw_runs(self):
        with self.assertRaises(ValueError):
            analyse(self.runs, self.raw_dir, allow_partial=True)

    def test_outputs_and_raw_file_unchanged(self):
        before = hashlib.sha256(self.runs.read_bytes()).hexdigest()
        label, figures = analyse(self.runs, self.out, allow_partial=True)
        self.assertTrue(label.startswith("PRELIMINARY: 12 of 450"))
        self.assertEqual(hashlib.sha256(self.runs.read_bytes()).hexdigest(), before)
        for name in ("variant_summary", "paired_comparisons", "mean_ranks"):
            self.assertTrue((self.out / f"{name}.csv").stat().st_size > 0)
            self.assertIn("PRELIMINARY", (self.out / f"{name}.md").read_text())
        for path in figures:
            self.assertTrue(Path(path).stat().st_size > 0)
        meta = json.loads((self.out / "analysis_metadata.json").read_text())
        self.assertEqual(meta["runs_sha256"], before)

    def test_duplicate_runs_are_rejected(self):
        line = self.runs.read_text().splitlines()[0]
        duplicate = Path(self.tmp.name) / "dup.jsonl"
        duplicate.write_text(line + "\n" + line + "\n")
        with self.assertRaises(ValueError):
            compare.load_runs(duplicate)


if __name__ == "__main__":
    unittest.main()