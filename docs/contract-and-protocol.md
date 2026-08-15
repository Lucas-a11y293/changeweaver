# Contract and Protocol Reference

## Contract lifecycle

A contract is a repository-owned `changeweaver.yaml` file. It is configuration, not a generated cache. Review it like source code: every new layer or deny rule changes what CI considers a regression.

The top-level `version` is currently `1`. `project.name` becomes the snapshot identity, while `roots`, `include`, and `exclude` bound the input set. A layer is a named collection of path patterns. A rule selects source layers and denies destination layers with a severity and explanation.

Unknown keys are rejected. The parser accepts a scalar string where a list is useful for `from` and `deny`, but serializes the normalized contract internally as tuples. A missing match is not silently accepted: the checker emits an `unclassified-node` warning, or an error when strict mode is requested.

## Snapshot protocol

A snapshot contains the following stable fields.

| Field | Meaning |
|---|---|
| `protocol_version` | Version of the envelope and artifact shape. |
| `snapshot_version` | Version of the analysis snapshot schema. |
| `repository` | Contract-owned project identity. |
| `analyzer` | Analyzer identity and version boundary. |
| `nodes` | Sorted Dart and external/unresolved nodes. |
| `edges` | Sorted import/export/part relations with source line and URI. |
| `diagnostics` | Explicit uncertainty or bounded-analysis warnings. |
| `digest` | SHA-256 of canonical content excluding the digest itself. |

Canonical JSON uses UTF-8, sorted object keys, compact separators, and deterministic list ordering. The digest is intended to detect accidental artifact changes; it is not a cryptographic signature or a trust statement about the repository.

## Findings

A finding has a stable `rule_id`, a severity, a human message, optional source and target node IDs, a repository-relative path and line, and evidence strings. SARIF maps error to `error`, warning to `warning`, and info to `note`. Findings are sorted by rule ID, source, target, path, and line.

## Exit semantics

The CLI uses four exit classes rather than conflating an invalid analysis with a failed policy. Exit `0` is clean, `1` is an enforced finding, `2` is an input or analysis error, and `3` means the selected baseline is not comparable. A caller can therefore distinguish “the architecture is out of policy” from “the tool could not safely analyze the input.”

## Compatibility policy

Before 1.0, the protocol may add optional fields and increment the snapshot version when semantics change. Removing or changing the meaning of a field requires a migration note and a regression test. A new renderer must consume the protocol models rather than perform a second analysis.
