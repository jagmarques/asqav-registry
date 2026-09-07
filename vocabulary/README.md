# Asqav wire vocabulary reference

`wire.json` records public wire identifiers, ordered groups and taxonomy metadata.
Its `schema_version` describes this file's shape, independently of the two registries
in [`registry/`](../registry/). The request group includes `authoritative`; the
receipt profile group contains the nine registered type namespaces.

The data comes from the [public governance document](https://api.asqav.com/.well-known/governance.json),
the [SDK reference declarations](https://github.com/jagmarques/asqav-sdk/blob/22a970d8fd5a0b20fdd1626226ba3c0a6fe0a5b1/typescript/src/index.ts),
and the [type registry](https://github.com/jagmarques/asqav-registry/blob/65d6b2864f8bf650851cc01920192eb58357e2a8/registry/type-namespaces.json).
Public governance bytes used for this snapshot have SHA256
`e448e47b7b4ee9bf91fb0c3f139682fd02bf098594c8d6de6f6ef4bca09f3b17`.

From the repository root, install the validation dependency and check the data:

```sh
python3 -m pip install jsonschema
python3 vocabulary/validate.py
python3 -m unittest discover -s tests -p 'test_wire_vocabulary.py'
```

Validation checks file shape and references. It does not verify receipts or report
deployed capabilities. Consumers should vendor a pinned snapshot and apply their
own validation policies. This directory does not generate consumer code or check
consumer drift.

The reference data and validation tool use the repository's [Apache License 2.0](../LICENSE)
and [NOTICE](../NOTICE). They contain no signing or verification implementation.
