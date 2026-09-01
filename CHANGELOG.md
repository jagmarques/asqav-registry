# Changelog

Both registries version together.

## [1.0.0] - 2026-09-01

Initial contents, generated from Sections 12.1 and 12.2 of
`draft-marques-asqav-compliance-receipts-09` rather than transcribed by hand, so the registry and
the document cannot drift apart on their first edit.

- **46 extension fields**: 44 `signed-payload`, 1 `envelope-level`, 1 `signing-time declaration`
  (`witness_policy`, annotated "not a wire member").
- **9 type namespaces**: `protectmcp:acknowledgment`, `protectmcp:decision`,
  `protectmcp:restraint`, `protectmcp:lifecycle`, `protectmcp:lifecycle:configuration_change`,
  `protectmcp:lifecycle:risk_acceptance`, `protectmcp:lifecycle:code_authorship`,
  `protectmcp:observation`, `protectmcp:observation:result_bound`.
- JSON Schemas for both files, and the registration process in `REGISTRATION.md`.

No third-party entries. Nothing is pre-registered on anyone's behalf.

### Known not-yet-registered

These ship in the platform or are defined in the in-flight draft revision but are **not** in the
initial contents, because the initial contents are exactly what the -09 registry sections list:

- `seq` — the per-chain counter, shipped and emitting in production.
- `beacon_ref` — the earliest-time bound.
- `human_approval`, `owasp_agentic_top10`, and the
  `protectmcp:lifecycle:oversight_ruling` sub-namespace and its fields.

They are added when the draft sections that define them land, so the registry keeps tracking the
document rather than running ahead of it.
