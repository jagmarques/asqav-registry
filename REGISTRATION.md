# Registration process

This repository holds the two registries the Compliance Receipts profile defines: the
**Compliance Receipt Extension Fields** registry and the **Compliance Receipt Type Namespaces**
registry.

## Why these are here and not at IANA

The defining document is an Independent Submission. [RFC 8726][rfc8726] Section 4 states that
"In general, documents on the Independent Stream cannot request the creation of a new IANA
registry", and Section 5 states that the Independent Submissions Editor "will not appoint a DE",
so no new subregistry may use the Specification Required or Expert Review policies.

The registries therefore stay as normative tables in the document, and are **administered here**
under the process below. If the document is later progressed on the IETF Stream, transfer of both
registries to IANA under Specification Required is expected.

Nothing here is pre-registered on anyone's behalf. Entries appear only after a request is made and
reviewed.

## How to register

1. Open an issue using the **Registration request** template.
2. Provide every field:
   - **Name** — the field name, or the namespace.
   - **Which registry** — extension field, or type namespace.
   - **Scope tag** (extension fields only) — one of `signed-payload`, `envelope-level`, or
     `signing-time declaration`.
   - **Stable public specification URL** — a dereferenceable document defining the semantics.
   - **Contact** — the party who will answer questions about the entry.
   - **Change controller** — the party authorized to request changes.
3. A maintainer reviews it against the criteria below.
4. On approval the entry is merged and the registry `version` is bumped.

## Registration review criteria

These mirror the criteria the defining document states, with the Designated Expert language
removed because the Independent Stream has no DE.

**Both registries**

- The reference is a **stable, dereferenceable** specification. A link that can silently change
  content, or that requires an account to read, does not qualify.
- The entry does not collide with an existing entry.

**Extension fields**

- The field name is lowercase ASCII letters, digits and underscore.
- The name does not collide with any field defined by the upstream ACTA receipts draft.
- The **scope tag is correct**. This is not bookkeeping: a verifier that reads an envelope-level
  field as though it were signed would report unsigned data as covered by the signature.
- The vocabulary is documented well enough for an independent verifier to validate values, or is
  explicitly `free-form`.

**Type namespaces**

- The namespace is lowercase ASCII letters, digits, hyphen, underscore and colon.
- A sub-namespace request of the form `parent:suffix` names its parent entry, and inherits that
  parent's change controller.

## Allocation policy

**First come, first served within a namespace.**

Third parties may register **only under their own top-level namespace**, against a stable public
specification. The `protectmcp` namespace and every sub-namespace under it are **reserved to the
defining document** and are not available for third-party registration.

## Stability guarantee

These promises exist so an implementer can start emitting `type` today without betting on what
happens to this repository later.

1. **An entry, once registered, is never removed and never renamed.** It may only be marked
   deprecated, by setting `deprecated: true` on the entry with a `deprecated_note` saying why and
   what replaces it. A name that a receipt already carries therefore always resolves. Deprecation
   is a statement about new receipts, not a retraction: a verifier MUST keep validating existing
   receipts that use a deprecated entry exactly as before it was deprecated.
2. **Registration is not revocable for editorial reasons.** An entry is withdrawn only if its
   change controller asks for it, and even then it is deprecated rather than deleted.
3. **`protectmcp` and its sub-namespaces are reserved to the defining document.** No third-party
   registration can take a name out from under a receipt already in the field.
4. **If the defining document is later progressed on the IETF Stream and these registries transfer
   to IANA, the entries registered at that time are submitted as the initial contents of the IANA
   registries unchanged** — same names, same scope tags, same change controllers. Transfer is not
   an occasion to renumber, re-scope or re-review what is already registered.

The registry `version` moves whenever entries change, and verifiers report it, so a deprecation is
visible as a version skew rather than as a silent difference between two verifiers.

## What a verifier does with these files

Verifiers vendor both files at build time and report the registry `version` in their output, so a
disagreement between two verifiers can be traced to a registry skew rather than to a receipt.

- A `protectmcp:*` type or sub-namespace **not** in the registry is a **non-conformance**.
- An unknown **non-`protectmcp`** namespace is reported as an *unregistered namespace*, and is
  **not** a failure. A registry that has not yet caught up with a legitimate third-party extension
  should not turn that party's valid receipts into invalid ones.
- A registered extension field name carrying the **wrong scope tag or wrong type** is a
  **non-conformance**.
- Unknown extension fields keep their existing behaviour.

[rfc8726]: https://www.rfc-editor.org/rfc/rfc8726.html
