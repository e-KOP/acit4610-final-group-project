"""Tests for Portfolio ES run provenance and metadata identity.

AI-assisted implementation. See docs/ai_usage.md.
"""

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from portfolio_optimization.portfolio.provenance import (
    build_metadata,
    fingerprint,
    metadata_path_for,
    sha256_file,
    verify_metadata,
    write_metadata_exclusive,
)


class TestProvenance(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        data = self.root / "portfolio_optimization/data/or_library/port1.txt"
        data.parent.mkdir(parents=True)
        data.write_bytes(b"initial benchmark bytes\n")
        self.data = data
        config_path = self.root / "portfolio_optimization/configs/experiments.json"
        config_path.parent.mkdir(parents=True)
        config = {
            "datasets": [{
                "name": "port1",
                "path": "portfolio_optimization/data/or_library/port1.txt",
                "assets": 2,
            }],
            "evaluation_budget": 30,
        }
        config_path.write_text(json.dumps(config), encoding="utf-8")
        self.config_path = config_path
        self.config = config
        self.selection = {
            "datasets": ("port1",),
            "alphas": (0.5,),
            "variants": ("one_plus_one",),
            "seeds": (0, 1),
            "budget": 30,
        }

    def build(self):
        with patch("portfolio_optimization.portfolio.provenance._git", return_value=None):
            return build_metadata(
                self.root, self.config_path, self.config,
                self.selection, solver_mode="actual_es",
            )

    def test_sha256_is_exact_file_bytes(self):
        self.assertEqual(sha256_file(self.data),
                         hashlib.sha256(self.data.read_bytes()).hexdigest())

    def test_sidecar_name(self):
        self.assertEqual(
            metadata_path_for(self.root / "raw/portfolio_runs.jsonl").name,
            "portfolio_runs.metadata.json",
        )

    def test_identity_records_inputs_and_environment(self):
        meta = self.build()
        identity = meta["identity"]
        self.assertIn("python", identity["environment"])
        self.assertIn("numpy", identity["environment"])
        self.assertEqual(identity["selection"]["seeds"], [0, 1])
        self.assertEqual(identity["dataset_sha256"]["port1"], sha256_file(self.data))
        self.assertEqual(meta["fingerprint_sha256"], fingerprint(identity))

    def test_dataset_changed_blocks_resume(self):
        before = self.build()
        self.data.write_bytes(b"modified benchmark bytes\n")
        after = self.build()
        self.assertNotEqual(before["fingerprint_sha256"],
                            after["fingerprint_sha256"])

    def test_code_changed_blocks_resume(self):
        source = self.root / "portfolio_optimization/portfolio/one_plus_one.py"
        source.parent.mkdir(parents=True)
        source.write_text("# implementation v1\n", encoding="utf-8")
        before = self.build()
        source.write_text("# implementation v2\n", encoding="utf-8")
        after = self.build()
        self.assertNotEqual(before["fingerprint_sha256"],
                            after["fingerprint_sha256"])

    def test_rejects_data_that_disagrees_with_manifest(self):
        manifest = self.root / "portfolio_optimization/data/manifest.json"
        manifest.write_text(json.dumps({"files": [{
            "path": "or_library/port1.txt",
            "sha256": "0" * 64,
        }]}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Benchmark checksum mismatch"):
            self.build()

    def test_metadata_matches_and_refuses_overwrite(self):
        meta = self.build()
        path = self.root / "test.metadata.json"
        write_metadata_exclusive(path, meta)
        self.assertEqual(verify_metadata(path, meta)["identity"], meta["identity"])
        with self.assertRaises(FileExistsError):
            write_metadata_exclusive(path, meta)

    def test_incompatible_sidecar_fails(self):
        meta = self.build()
        path = self.root / "test.metadata.json"
        write_metadata_exclusive(path, meta)
        altered = copy.deepcopy(meta)
        altered["identity"]["selection"]["budget"] = 31
        altered["fingerprint_sha256"] = fingerprint(altered["identity"])
        with self.assertRaisesRegex(ValueError, "incompatible experiment resume"):
            verify_metadata(path, altered)


if __name__ == "__main__":
    unittest.main()
