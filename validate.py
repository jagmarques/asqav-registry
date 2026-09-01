#!/usr/bin/env python3
"""Validate both registry files against their schemas and the invariants a verifier relies on.

Run: python3 validate.py
Exit code is non-zero on any violation, so CI can gate a registration PR on it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / "registry"

VALID_SCOPES = {"signed-payload", "envelope-level", "signing-time declaration"}
RESERVED_ROOT = "protectmcp"


def _load(name: str) -> dict:
    return json.loads((REGISTRY / name).read_text())


def check_schema(doc: dict, schema_name: str, errors: list[str]) -> None:
    try:
        import jsonschema
    except ImportError:
        errors.append(f"NOTE: jsonschema not installed, skipped schema check for {schema_name}")
        return
    schema = _load(schema_name)
    validator = jsonschema.Draft202012Validator(schema)
    for err in sorted(validator.iter_errors(doc), key=str):
        errors.append(f"{schema_name}: {list(err.path)}: {err.message}")


def check_fields(doc: dict, errors: list[str]) -> None:
    seen: set[str] = set()
    for e in doc["entries"]:
        name = e["field_name"]
        if name in seen:
            errors.append(f"extension-fields: duplicate field_name {name!r}")
        seen.add(name)
        if e["scope"] not in VALID_SCOPES:
            errors.append(f"extension-fields: {name}: bad scope {e['scope']!r}")
        if not e.get("description", "").strip():
            errors.append(f"extension-fields: {name}: empty description")


def check_namespaces(doc: dict, errors: list[str]) -> None:
    seen: set[str] = set()
    entries = {e["namespace"] for e in doc["entries"]}
    for e in doc["entries"]:
        ns = e["namespace"]
        if ns in seen:
            errors.append(f"type-namespaces: duplicate namespace {ns!r}")
        seen.add(ns)
        # The registered unit is `root:category` (e.g. protectmcp:decision); the bare root is
        # not itself an entry, and no `type` value is ever the bare root. So a parent is
        # required only from the third level down, which is where the document's parent:suffix
        # delegation rule actually bites: protectmcp:lifecycle:risk_acceptance inherits its
        # change controller from protectmcp:lifecycle, and an orphan there would have none.
        if ns.count(":") >= 2:
            parent = ns.rsplit(":", 1)[0]
            if parent not in entries:
                errors.append(
                    f"type-namespaces: {ns!r} is a sub-namespace whose parent {parent!r} "
                    "is not registered; a sub-namespace inherits its parent's change controller, "
                    "so an orphan has no controller"
                )


def check_reserved_namespace_is_ours(doc: dict, errors: list[str]) -> None:
    """protectmcp is reserved to the defining document. A third-party controller on any
    protectmcp entry would mean the reservation had been given away by accident."""
    for e in doc["entries"]:
        if e["namespace"].split(":")[0] == RESERVED_ROOT and e["change_controller"] != "Asqav":
            errors.append(
                f"type-namespaces: {e['namespace']!r} is under the reserved {RESERVED_ROOT!r} "
                f"root but its change_controller is {e['change_controller']!r}"
            )


def main() -> int:
    errors: list[str] = []
    fields = _load("extension-fields.json")
    namespaces = _load("type-namespaces.json")

    check_schema(fields, "extension-fields.schema.json", errors)
    check_schema(namespaces, "type-namespaces.schema.json", errors)
    check_fields(fields, errors)
    check_namespaces(namespaces, errors)
    check_reserved_namespace_is_ours(namespaces, errors)

    if fields["version"] != namespaces["version"]:
        errors.append(
            f"the two registries version together, but extension-fields is "
            f"{fields['version']} and type-namespaces is {namespaces['version']}"
        )

    hard = [e for e in errors if not e.startswith("NOTE:")]
    for e in errors:
        print(("  " if e.startswith("NOTE:") else "FAIL ") + e, file=sys.stderr)
    if hard:
        print(f"\n{len(hard)} problem(s)", file=sys.stderr)
        return 1
    print(
        f"OK: {len(fields['entries'])} extension fields, "
        f"{len(namespaces['entries'])} type namespaces, version {fields['version']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
