"""Exercise generated literals and the fixed filesystem command surface."""

import ast
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import typing
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("wire_renderer", ROOT / "tools/wire_vocabulary.py")
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)


class RendererTests(unittest.TestCase):
    """Reference rendering preserves typed values and rejects unsafe destinations."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        (self.root / "vocabulary").mkdir()
        for name in ("wire.json", "wire.schema.json", "validate.py"):
            shutil.copyfile(ROOT / "vocabulary" / name, self.root / "vocabulary" / name)
        self.document = renderer.load_reference(self.root / "vocabulary")

    def generated(self):
        renderer._sync(self.root, True)
        return self.root / "vocabulary/generated"

    def hashes(self):
        return {str(path.relative_to(self.root)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in (self.root / "vocabulary/generated").rglob("*") if path.is_file()}

    def test_python_ast_literals_aliases_and_independent_baseline(self):
        directory = self.generated()
        tree = ast.parse((directory / "wire.py").read_bytes())
        literals = {node.targets[0].id: ast.literal_eval(node.value)
                    for node in tree.body if isinstance(node, ast.Assign)
                    and not isinstance(node.value, ast.Subscript)}
        self.assertEqual(literals["POLICY_DECISIONS"], ("permit", "deny", "rate_limit", "none"))
        self.assertEqual(literals["DECISION_MAP"], {
            "permit": "allow", "allow": "allow", "deny": "deny",
            "rate_limit": "rate_limit", "none": "observation"})
        self.assertEqual(len(literals["RECEIPT_PROFILE"]), 9)
        self.assertEqual(literals["RECEIPT_REQUEST"], literals["RECEIPT_PROFILE"] + ("authoritative",))
        self.assertNotIn("authoritative", literals["RECEIPT_PROFILE"])
        self.assertEqual(len(literals["METADATA"]), 43)
        self.assertNotIn("beacon_ref", literals["METADATA"])
        self.assertNotIn("owasp_agentic_top10", literals["FIELDS"])
        self.assertEqual(literals["METADATA"], self.document["metadata"])
        self.assertEqual(list(literals["FIELDS"]), self.document["taxonomy_order"])
        for field in literals["FIELDS"].values():
            self.assertEqual(field["list_entry_max_length"], 128)
            self.assertNotIn("allowed_values", field)
        actual = runpy.run_path(str(directory / "wire.py"))
        for alias, constant in renderer.ALIASES.items():
            self.assertEqual(typing.get_args(actual[alias]), literals[constant])
        values = json.loads((directory / "wire-cases.json").read_bytes())["values"]
        self.assertEqual(json.loads(json.dumps(literals)), values)
        cases = json.loads((directory / "wire-cases.json").read_bytes())
        self.assertEqual(cases["kind"], "lexical-vocabulary")
        self.assertEqual(cases["type_membership"][-1], {
            "value": "authoritative", "receipt_profile": False, "receipt_request": True})
        self.assertTrue(all(case["receipt_profile"] for case in cases["type_membership"][:-1]))

    def test_two_roots_and_twice_in_place_have_identical_bytes(self):
        self.generated()
        first = self.hashes()
        self.assertEqual(set(first), {f"vocabulary/generated/{name}" for name in renderer.OUTPUTS})
        with tempfile.TemporaryDirectory() as other:
            second_root = Path(other).resolve()
            shutil.copytree(self.root / "vocabulary", second_root / "vocabulary", ignore=shutil.ignore_patterns("generated"))
            renderer._sync(second_root, True)
            second = {str(p.relative_to(second_root)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in (second_root / "vocabulary/generated").rglob("*") if p.is_file()}
            self.assertEqual(first, second)
        renderer._sync(self.root, True)
        self.assertEqual(first, self.hashes())
        renderer._sync(self.root, True)
        self.assertEqual(first, self.hashes())
        self.assertEqual(renderer._sync(self.root, False), [])

    def test_every_output_drift_and_missing_file_names_the_path(self):
        directory = self.generated()
        for name in renderer.OUTPUTS:
            with self.subTest(name=name):
                path = directory / name
                original = path.read_bytes()
                path.write_bytes(original + b" ")
                before = self.hashes()
                with patch.object(renderer, "ROOT", self.root), contextlib.redirect_stderr(io.StringIO()) as err:
                    self.assertEqual(renderer.main(["--check"]), 1)
                self.assertIn(f"vocabulary/generated/{name}", err.getvalue())
                self.assertEqual(before, self.hashes())
                path.unlink()
                self.assertEqual(renderer._sync(self.root, False), [f"vocabulary/generated/{name}"])
                path.write_bytes(original)

    def test_symlinks_and_invalid_destinations_preflight_all_outputs(self):
        directory = self.generated()
        (directory / "wire.py").write_bytes(b"deliberate drift")
        for name in renderer.OUTPUTS:
            path = directory / name
            original = path.read_bytes()
            path.unlink()
            target = self.root / "outside"
            target.write_bytes(b"keep")
            path.symlink_to(target)
            first = (directory / "wire.py").read_bytes()
            with self.assertRaisesRegex(ValueError, "symlink"):
                renderer._sync(self.root, True)
            self.assertEqual(target.read_bytes(), b"keep")
            self.assertEqual((directory / "wire.py").read_bytes(), first)
            path.unlink()
            path.mkdir()
            with self.assertRaisesRegex(ValueError, "not a file"):
                renderer._sync(self.root, True)
            path.rmdir()
            path.write_bytes(original)
        shutil.rmtree(directory)
        directory.symlink_to(self.root / "absent")
        with self.assertRaisesRegex(ValueError, "symlink"):
            renderer._sync(self.root, True)
        self.assertFalse((self.root / "absent").exists())
        directory.unlink()
        directory.write_text("keep")
        with self.assertRaisesRegex(ValueError, "not a directory"):
            renderer._sync(self.root, True)

    def test_malformed_reference_is_rejected_without_writes(self):
        path = self.root / "vocabulary/wire.json"
        inputs = ['[]', '{"schema_version":2,"schema_version":2}', '{"x":NaN}',
                  '{"x":Infinity}', '{"x":-Infinity}', '{}', '{']
        for source in inputs:
            path.write_text(source)
            with self.subTest(source=source), self.assertRaises(ValueError):
                renderer._sync(self.root, True)
            self.assertFalse((self.root / "vocabulary/generated").exists())
        for document in [None, [], {}, {**self.document, "schema_version": 1}]:
            for render in (renderer.render_python, renderer.render_typescript, renderer.render_cases):
                with self.assertRaises(ValueError):
                    render(document)

    def test_escaping_roundtrips_through_both_actual_compilers(self):
        adversary = "apostrophe ' quote \" slash \\ newline\n雪 😀\u2028\u2029\x00; throw Error('data'); #"
        document = copy.deepcopy(self.document)
        document["metadata"]["invocation_ref"] = {"form": adversary, "description": adversary}
        document["taxonomy_order"].reverse()
        (self.root / "vocabulary/wire.json").write_text(json.dumps(document))
        directory = self.generated()
        actual = runpy.run_path(str(directory / "wire.py"))
        self.assertEqual(actual["METADATA"]["invocation_ref"], document["metadata"]["invocation_ref"])
        self.assertEqual(actual["TAXONOMY_ORDER"], tuple(document["taxonomy_order"]))
        result = subprocess.run(["node", str(ROOT / "tests/typescript-consumer/roundtrip.mjs"), str(directory)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_typescript_integer_range_fails_before_any_output_write(self):
        self.document["fields"]["mitre_atlas"]["list_entry_max_length"] = 2**53 + 1
        (self.root / "vocabulary/wire.json").write_text(json.dumps(self.document))
        with self.assertRaisesRegex(ValueError, "exact TypeScript integers"):
            renderer._sync(self.root, True)
        self.assertFalse((self.root / "vocabulary/generated").exists())

    def test_cli_different_cwd_modes_and_missing_dependency(self):
        with patch.object(renderer, "ROOT", self.root), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(renderer.main(["--write"]), 0)
            self.assertEqual(renderer.main(["--check"]), 0)
        for argv in ([], ["--unknown"], ["--check", "--write"]):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
                renderer.main(argv)
            self.assertEqual(exc.exception.code, 2)
        command = [sys.executable, "-B", str(ROOT / "tools/wire_vocabulary.py"), "--check"]
        result = subprocess.run(command, cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        missing = subprocess.run([sys.executable, "-S", *command[1:]], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(missing.returncode, 1)
        self.assertIn("jsonschema is required", missing.stderr)
        self.assertNotIn("Traceback", missing.stderr)
        with patch.object(renderer, "ROOT", self.root / "missing"), contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(renderer.main(["--check"]), 1)
        self.assertIn("FAIL:", err.getvalue())


if __name__ == "__main__":
    unittest.main()
