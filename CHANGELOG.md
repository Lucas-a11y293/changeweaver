# Changelog

All notable changes to ChangeWeaver are documented here.

## [0.1.0] - 2026-08-16

### Added

- Deterministic lexical Dart import/export/part graph snapshots.
- YAML architecture contracts with typed validation and fail-closed unknown keys.
- Reverse dependency impact analysis with bounded path evidence and explainable score.
- Snapshot diff for added and removed nodes and edges.
- Architecture findings with stable rule IDs, severity, source locations, and evidence.
- No-mutation verification plans.
- Evidence-first `verify` command producing deterministic, content-addressed verification receipts.
- Terminal, JSON, SARIF 2.1.0, Mermaid, and HTML renderers.
- Safe root/path handling, symlink avoidance, file-size limits, node limits, and no network execution.
- Unit, integration, CLI, and security tests with a Dart/Flutter-like fixture.
- Project architecture, contribution, security, and roadmap documentation.
- GitHub Actions example that persists a verification receipt as a build artifact.

### Boundaries

This alpha release uses conservative lexical analysis. It is not a replacement for Dart Analyzer, Flutter CLI, Melos, DCM, or a semantic refactoring engine.
