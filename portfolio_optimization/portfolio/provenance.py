"""Experiment source/data provenance and safe metadata sidecars.

AI-assisted implementation; see docs/ai_usage.md.

Provenance covers the exact code bytes, Git revision, selected experiments,
benchmark checksums and numeric environment.  A run cannot be resumed if any
identity field changes.  Timestamps and invocation command are informational.
"""

import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = 1
CODE_FILES = (
    "portfolio_optimization/portfolio/__init__.py",
    "portfolio_optimization/portfolio/__main__.py",
    "portfolio_optimization/portfolio/data.py",
    "portfolio_optimization/portfolio/evaluation.py",
    "portfolio_optimization/portfolio/experiments.py",
    "portfolio_optimization/portfolio/feasibility.py",
    "portfolio_optimization/portfolio/one_plus_one.py",
    "portfolio_optimization/portfolio/output.py",
    "portfolio_optimization/portfolio/population_es.py",
    "portfolio_optimization/portfolio/provenance.py",
    "portfolio_optimization/portfolio/repair.py",
    "requirements.txt",
)
GIT_SCOPE = (
    "portfolio_optimization/portfolio",
    "portfolio_optimization/configs",
    "portfolio_optimization/data",
    "portfolio_optimization/tests",
    "requirements.txt",
)


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(root, *args):
    try:
        result = subprocess.run(
            ["git", *args], cwd=root, text=True, capture_output=True,
            check=False, timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _package_version(name):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def metadata_path_for(output_path):
    return Path(output_path).with_suffix(".metadata.json")


def _identity_json(identity):
    return json.dumps(identity, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def fingerprint(identity):
    return hashlib.sha256(_identity_json(identity)).hexdigest()


def build_metadata(root, config_path, config, selection, *, solver_mode):
    """Build a stable identity plus informational creation fields.

    `selection` is the explicit dataset/alpha/variant/seed/budget matrix.
    Only code/data files relevant to Portfolio Problem 2 are hashed.
    Git's dirty status is likewise scoped, excluding generated results.
    """
    root = Path(root).resolve()
    config_path = Path(config_path)
    if not config_path.is_absolute():
        config_path = root / config_path

    datasets = {}
    for entry in config["datasets"]:
        path = root / entry["path"]
        datasets[entry["name"]] = sha256_file(path)

    # If the repository's original-source manifest is present, refuse to
    # run against modified benchmark bytes even on a brand-new experiment.
    data_root = root / "portfolio_optimization/data"
    manifest_path = data_root / "manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected = {item["path"]: item["sha256"] for item in manifest["files"]}
        for entry in config["datasets"]:
            relative = (root / entry["path"]).relative_to(data_root).as_posix()
            if expected.get(relative) != datasets[entry["name"]]:
                raise ValueError(f"Benchmark checksum mismatch: {relative}")

    code = {}
    for relative in CODE_FILES:
        path = root / relative
        # This module also supports pre-integration test scaffolds where
        # an algorithm file has not yet been added.
        code[relative] = sha256_file(path) if path.is_file() else None

    revision = _git(root, "rev-parse", "HEAD")
    status = _git(root, "status", "--porcelain", "--untracked-files=normal",
                  "--", *GIT_SCOPE)
    identity = {
        "schema_version": SCHEMA_VERSION,
        "selection": {
            "datasets": list(selection["datasets"]),
            "alphas": list(selection["alphas"]),
            "variants": list(selection["variants"]),
            "seeds": list(selection["seeds"]),
            "budget": selection["budget"],
        },
        "solver_mode": solver_mode,
        "git_revision": revision,
        "git_source_dirty": (bool(status) if status is not None else None),
        "source_sha256": code,
        "config_sha256": sha256_file(config_path),
        "dataset_sha256": datasets,
        "manifest_sha256": sha256_file(manifest_path) if manifest_path.is_file() else None,
        "environment": {
            "python": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "numpy": _package_version("numpy"),
            "matplotlib": _package_version("matplotlib"),
            "platform": platform.platform(),
            "processor": platform.processor(),
        },
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "identity": identity,
        "fingerprint_sha256": fingerprint(identity),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "invocation": " ".join(sys.argv),
    }


def write_metadata_exclusive(path, metadata):
    """Write the sidecar before any new JSONL record, refusing overwrite."""
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(metadata, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def verify_metadata(path, expected):
    """Require the previously saved experimental identity to match exactly."""
    try:
        actual = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("Missing or invalid experiment metadata sidecar") from exc
    if not isinstance(actual, dict) or not isinstance(actual.get("identity"), dict):
        raise ValueError("Invalid experiment metadata structure")
    if actual.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Incompatible experiment metadata schema")
    if actual.get("fingerprint_sha256") != fingerprint(actual["identity"]):
        raise ValueError("Experiment metadata fingerprint is corrupt")
    if actual["identity"] != expected["identity"]:
        keys = sorted(
            key for key in set(actual["identity"]) | set(expected["identity"])
            if actual["identity"].get(key) != expected["identity"].get(key)
        )
        raise ValueError(
            "Refusing incompatible experiment resume; differences: " + ", ".join(keys)
        )
    return actual
