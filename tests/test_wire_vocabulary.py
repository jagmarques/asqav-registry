"""Reference validation rejects ambiguity without widening receipt profiles."""

import builtins
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("wire_validator", ROOT / "vocabulary/validate.py")
wire = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(wire)


class ReferenceValidation(unittest.TestCase):
    def setUp(self):
        self.document = wire.load(ROOT / "vocabulary/wire.json")

    def rejects(self, document, message):
        with self.assertRaisesRegex(ValueError, message):
            wire.validate(document)

    def test_reference_keeps_profile_and_policy_alias_distinct(self):
        wire.validate(self.document)
        namespaces = wire.load(ROOT / "registry/type-namespaces.json")
        self.assertEqual(set(self.document["receipt_types"]), {e["namespace"] for e in namespaces["entries"]})
        self.assertEqual(len(self.document["receipt_types"]), 9)
        self.assertEqual(self.document["request_extra_types"], ["authoritative"])
        self.assertNotIn("allow", self.document["policy_decisions"])
        self.assertEqual(self.document["decision_map"], [
            ["permit", "allow"], ["allow", "allow"], ["deny", "deny"],
            ["rate_limit", "rate_limit"], ["none", "observation"],
        ])

    def test_reference_preserves_generic_taxonomy_metadata(self):
        expected = ["mitre_techniques", "mitre_atlas", "owasp_llm_top10", "nist_ai_rmf", "iso_42001", "eu_ai_act_articles"]
        self.assertEqual(self.document["taxonomy_order"], expected)
        self.assertEqual(list(self.document["fields"]), expected)
        self.assertEqual([f["typescript_option"] for f in self.document["fields"].values()], [
            "mitreTechniques", "mitreAtlas", "owaspLlmTop10", "nistAiRmf", "iso42001", "euAiActArticles",
        ])
        for field in self.document["fields"].values():
            self.assertEqual(field["list_entry_max_length"], 128)
            self.assertNotIn("allowed_values", field)

    def test_every_required_member_is_required(self):
        for name in self.document:
            with self.subTest(name=name):
                changed = copy.deepcopy(self.document)
                del changed[name]
                self.rejects(changed, "required property")

    def test_unknown_metadata_cannot_be_forwarded(self):
        for name in ["available", "capabilities", "runtime_endpoint", "private_source_path", "engine"]:
            with self.subTest(name=name):
                self.rejects(dict(self.document, **{name: "synthetic"}), "Additional properties")
        self.document["fields"]["mitre_atlas"]["allowed_values"] = ["AML.T0051"]
        self.rejects(self.document, "Additional properties")

    def test_schema_version_and_document_shape_are_closed(self):
        for value in [None, [], "", 1, True]:
            with self.subTest(value=value):
                self.rejects(value, "not of type 'object'")
        for value in [None, 0, 2, "1", True]:
            with self.subTest(version=value):
                self.rejects(dict(self.document, schema_version=value), "schema_version")

    def test_token_lists_reject_duplicates_empty_and_malformed_members(self):
        for name, value in self.document.items():
            if isinstance(value, list) and name != "decision_map":
                for changed in [[], value + [value[0]], [""], ["allow\n"], [None]]:
                    with self.subTest(name=name, changed=changed):
                        self.rejects(dict(self.document, **{name: changed}), name)

    def test_decision_mapping_references_and_sources(self):
        for mapping, message in [
            ([["permit", "allow"]], "omits a policy"),
            (self.document["decision_map"] + [["unknown", "allow"]], "unknown source"),
            (self.document["decision_map"] + [["permit", "deny"]], "duplicate source"),
            ([["permit", "unknown"]] + self.document["decision_map"][1:], "unknown target"),
            (self.document["decision_map"] + [["permit", "allow"]], "non-unique"),
            ([["permit"]], "too short"),
            ([["permit", "allow", "deny"]], "too long"),
        ]:
            with self.subTest(mapping=mapping):
                self.rejects(dict(self.document, decision_map=mapping), message)

    def test_profile_references_cannot_widen_or_hide_types(self):
        for name in self.document["profiles"]:
            for groups in [["unknown"], ["decisions"], ["request_extra_types"], ["receipt_types", "receipt_types"]]:
                with self.subTest(name=name, groups=groups):
                    changed = copy.deepcopy(self.document)
                    changed["profiles"][name] = groups
                    self.rejects(changed, name)
        self.document["request_extra_types"] = [self.document["receipt_types"][0]]
        self.rejects(self.document, "overlaps")

    def test_taxonomy_references_and_option_names_are_unique(self):
        for order in [self.document["taxonomy_order"][:-1], self.document["taxonomy_order"] + ["unknown"]]:
            self.rejects(dict(self.document, taxonomy_order=order), "reference every field")
        self.document["fields"]["mitre_atlas"]["typescript_option"] = "mitreTechniques"
        self.rejects(self.document, "duplicate typescript_option")

    def test_taxonomy_metadata_has_typed_nonempty_values(self):
        for key, bad in [
            ("typescript_option", "bad_name"), ("typescript_option", "name\n"),
            ("form", "   "), ("description", {"wire": ""}),
            ("description", {"wire": "text", "orm": "private"}),
            ("list_entry_max_length", 0), ("list_entry_max_length", "128"),
            ("list_entry_max_length", True),
        ]:
            with self.subTest(key=key, bad=bad):
                changed = copy.deepcopy(self.document)
                changed["fields"]["mitre_atlas"][key] = bad
                self.rejects(changed, key)

    def test_missing_schema_dependency_fails_clean(self):
        original = builtins.__import__

        def without_jsonschema(name, *args, **kwargs):
            if name == "jsonschema":
                raise ImportError("isolated missing dependency")
            return original(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=without_jsonschema):
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(wire.main([]), 1)
            self.assertIn("jsonschema is required", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())

    def test_cli_reads_explicit_file_and_fails_clean_on_bad_bytes(self):
        for raw in [b"", b"[", b"null", b"[]", b"\xff", b'{"schema_version":1,"schema_version":1}', b'{"nested":{"x":1,"x":2}}', b"NaN", b"Infinity", b"-Infinity"]:
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "wire.json"
                path.write_bytes(raw)
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    self.assertEqual(wire.main([str(path)]), 1)
                self.assertTrue(stderr.getvalue().startswith("FAIL:"))
                self.assertNotIn("Traceback", stderr.getvalue())

    def test_duplicate_json_members_cannot_hide_an_earlier_value(self):
        source = json.dumps(self.document)
        member = '"typescript_option": "mitreTechniques"'
        for raw in ['{"schema_version": 0,' + source[1:], source.replace(member, '"typescript_option": "wrong", ' + member)]:
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "wire.json"
                path.write_text(raw)
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    self.assertEqual(wire.main([str(path)]), 1)
                self.assertIn("duplicate JSON member", stderr.getvalue())

    def test_cli_entrypoint_and_missing_path(self):
        result = subprocess.run([sys.executable, str(ROOT / "vocabulary/validate.py")], capture_output=True, text=True, cwd=tempfile.gettempdir())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("reference shape and relationships", result.stdout)
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(wire.main([str(Path(directory) / "absent.json")]), 1)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(wire.main([]), 0)


if __name__ == "__main__":
    unittest.main()
