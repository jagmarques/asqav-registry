"""Backward-compatibility gate probes (criterion 523).

Each probe copies the tree to a scratch dir, mutates one registry fact,
and runs that copy's validate.py: deletions and renames must fail loud
naming the entry, while a deprecation flip stays green. Run against a
validate.py without the gate, the exit-1 assertions fail — the red
proof the gate is what fires.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _scratch_tree(tmp_path: Path) -> Path:
    """A runnable copy: validator plus everything it reads."""
    root = tmp_path / "registry-copy"
    shutil.copytree(REPO_ROOT, root, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    return root


def _run_validator(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "validate.py"], cwd=root, capture_output=True, text=True
    )


def _rewrite(root: Path, name: str, mutate) -> None:
    path = root / "registry" / name
    doc = json.loads(path.read_text())
    mutate(doc)
    path.write_text(json.dumps(doc, indent=2) + "\n")


def test_clean_tree_passes(tmp_path: Path) -> None:
    proc = _run_validator(_scratch_tree(tmp_path))
    assert proc.returncode == 0, proc.stderr


def test_deleted_field_fails_naming_it(tmp_path: Path) -> None:
    root = _scratch_tree(tmp_path)

    def drop(doc: dict) -> None:
        doc["entries"] = [
            e for e in doc["entries"] if e["field_name"] != "authorized_under_mandate"
        ]

    _rewrite(root, "extension-fields.json", drop)
    proc = _run_validator(root)
    assert proc.returncode == 1, proc.stderr
    assert "authorized_under_mandate" in proc.stderr


def test_renamed_namespace_fails(tmp_path: Path) -> None:
    root = _scratch_tree(tmp_path)

    def rename(doc: dict) -> None:
        for e in doc["entries"]:
            if e["namespace"] == "protectmcp:restraint":
                e["namespace"] = "protectmcp:restraint2"

    _rewrite(root, "type-namespaces.json", rename)
    proc = _run_validator(root)
    assert proc.returncode == 1, proc.stderr


def test_deprecated_flip_stays_green(tmp_path: Path) -> None:
    root = _scratch_tree(tmp_path)

    def deprecate(doc: dict) -> None:
        doc["entries"][0]["deprecated"] = True

    _rewrite(root, "extension-fields.json", deprecate)
    proc = _run_validator(root)
    assert proc.returncode == 0, proc.stderr
