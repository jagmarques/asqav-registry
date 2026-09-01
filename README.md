# Asqav Compliance Receipts registries

The two registries defined by the Compliance Receipts profile
(`draft-marques-asqav-compliance-receipts`), administered here rather than at IANA because the
document is an Independent Submission and [RFC 8726][rfc8726] bars that stream from creating IANA
registries.

| File | Registry |
|---|---|
| [`registry/extension-fields.json`](registry/extension-fields.json) | Compliance Receipt Extension Fields |
| [`registry/type-namespaces.json`](registry/type-namespaces.json) | Compliance Receipt Type Namespaces |

Each has a JSON Schema alongside it. Both carry a `version` that verifiers report in their output.

**To register an entry, read [REGISTRATION.md](REGISTRATION.md).** Third parties may register only
under their own top-level namespace; `protectmcp` and its sub-namespaces are reserved to the
defining document. Nothing is pre-registered on anyone's behalf.

## Consuming these files

Verifiers vendor both files at build time. The rules they enforce, and the reasoning behind each,
are in [REGISTRATION.md](REGISTRATION.md#what-a-verifier-does-with-these-files). In short: an
unregistered `protectmcp:*` type is a non-conformance, an unregistered third-party namespace is
reported but not failed, and a wrong scope tag is a non-conformance.

## Stability

This URL is intended not to move. The registries are versioned; entries are added, and existing
entries are not renamed or removed, so a verifier pinned to an older copy stays correct about
everything it already knew.

[rfc8726]: https://www.rfc-editor.org/rfc/rfc8726.html
