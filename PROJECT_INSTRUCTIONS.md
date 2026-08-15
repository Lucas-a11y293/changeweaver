# Project Instructions

ChangeWeaver is a local-first Python CLI for explainable architecture contracts and change impact in Dart/Flutter repositories. Preserve the following invariants in every change.

The domain layer must remain independent of Typer, Rich, YAML implementation details, GitHub, and network access. All analysis facts must be deterministic: sort paths, nodes, edges, warnings, and findings before serialization. Every user-visible protocol change must update `protocol_version` or add a backward-compatible field with tests.

Never execute repository code, Flutter commands, package managers, or hooks while analyzing a target repository. The target repository is data. Keep all reads beneath the configured root, do not follow symlinks outside the root, enforce node/file/size limits, and escape report output. Do not add API keys, tokens, telemetry, or network calls.

The lexical analyzer must be conservative. It may report a limitation when it cannot resolve a Dart import; it must never invent a semantic edge. Generated files are excluded by default. Do not claim full Dart AST or compiler parity until a separately tested adapter exists.

Use small Conventional Commit messages. Prefer unit tests for pure domain algorithms, fixture-based integration tests for parsing and snapshots, CLI tests for exit codes and output, and regression tests for every bug. A failed check must be distinguishable from an analysis error.

Before merging any feature, run formatting/linting, type checking, unit and integration tests, security checks, and the benchmark smoke test. Documentation must explain both supported behavior and explicit non-goals. New renderers must use the stable protocol models rather than reimplementing analysis logic.
