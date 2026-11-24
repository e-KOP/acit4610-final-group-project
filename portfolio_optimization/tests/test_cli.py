
"""Tests for portfolio experiment CLI.

AI-assisted implementation. See docs/ai_usage.md.
"""

from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from portfolio_optimization.portfolio import __main__ as cli


class TestPortfolioCLI(unittest.TestCase):

    def test_pilot_dispatch(self):
        with (
            patch.object(cli, "require_solvers") as check,
            patch.object(cli, "run_selected") as run,
        ):
            cli.main([
                "pilot",
                "--dataset", "port1",
                "--alpha", "0.5",
                "--variant", "one_plus_one",
                "--seed", "2",
                "--budget", "300",
            ])

            check.assert_called_once_with(
                ("one_plus_one",)
            )

            run.assert_called_once()
            args, kwargs = run.call_args

            self.assertIn(
                "scratch", str(args[0])
            )
            self.assertEqual(
                kwargs["datasets"], ("port1",)
            )
            self.assertEqual(
                kwargs["seeds"], (2,)
            )
            self.assertEqual(
                kwargs["budget"], 300
            )
            self.assertFalse(kwargs["resume"])

    def test_pilot_resume(self):
        with (
            patch.object(cli, "require_solvers"),
            patch.object(cli, "run_selected") as run,
        ):
            cli.main([
                "pilot",
                "--dataset", "port2",
                "--alpha", "0.25",
                "--variant", "mu_plus_lambda",
                "--resume",
            ])

            self.assertTrue(
                run.call_args.kwargs["resume"]
            )

    def test_invalid_pilot_budget(self):
        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit):
                cli.main([
                    "pilot",
                    "--dataset", "port1",
                    "--alpha", "0.5",
                    "--variant", "one_plus_one",
                    "--budget", "0",
                ])

    def test_full_requires_confirmation(self):
        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit):
                cli.main(["full"])

    def test_full_dispatch(self):
        with (
            patch.object(cli, "require_solvers") as check,
            patch.object(cli, "run_selected") as run,
        ):
            cli.main(["full", "--confirm-450"])

            check.assert_called_once()
            run.assert_called_once()

            args, kwargs = run.call_args

            self.assertEqual(
                args[0], cli.RAW_FILE
            )
            self.assertFalse(kwargs["resume"])

    def test_missing_solver_rejected(self):
        with (
            patch.object(
                cli, "_solver_for",
                side_effect=ModuleNotFoundError("missing"),
            ),
            patch.object(cli, "run_selected") as run,
        ):
            with self.assertRaisesRegex(
                RuntimeError, "unavailable"
            ):
                cli.main([
                    "pilot",
                    "--dataset", "port1",
                    "--alpha", "0.5",
                    "--variant", "one_plus_one",
                ])

            run.assert_not_called()

    def test_partial_summary(self):
        with (
            tempfile.TemporaryDirectory() as temp,
            patch.object(
                cli, "generate_outputs",
                return_value=[Path(temp) / "summary.csv"],
            ) as generate,
        ):
            cli.main([
                "summarize",
                "--runs", str(Path(temp) / "runs.jsonl"),
                "--allow-partial",
            ])

            self.assertFalse(
                generate.call_args.kwargs["require_complete"]
            )

    def test_complete_summary(self):
        with (
            tempfile.TemporaryDirectory() as temp,
            patch.object(
                cli, "generate_outputs",
                return_value=[],
            ) as generate,
        ):
            cli.main([
                "summarize",
                "--runs", str(Path(temp) / "runs.jsonl"),
            ])

            self.assertTrue(
                generate.call_args.kwargs["require_complete"]
            )


if __name__ == "__main__":
    unittest.main()
