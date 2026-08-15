# ChangeWeaver v0.1.0

ChangeWeaver 0.1.0 is the first public alpha of a local-first architecture contract and change-impact tool for Dart and Flutter repositories.

## Included

The release contains deterministic lexical Dart graph snapshots, YAML architecture contracts, reverse dependency impact analysis, snapshot diffs, explainable findings, no-mutation verification plans, JSON/SARIF/Mermaid/HTML renderers, secure bounded filesystem access, CI documentation, and a fixture-backed test suite.

The release was verified with 14 passing tests, 78% total coverage on the current suite, ruff, strict mypy, sdist/wheel builds, a clean runtime `pip-audit` scan, and a ten-iteration benchmark over the three-file fixture. The benchmark is a smoke measurement and is not a capacity claim for production repositories.

## Important boundaries

The 0.1 analyzer is lexical and conservative. It is not a complete Dart semantic analyzer, compiler replacement, refactoring engine, runtime verifier, or replacement for Flutter CLI, Melos, DCM, enola, or Drift. It does not execute target repository code or send source contents over the network.

## Activation note

The GitHub Actions workflow is included as `docs/ci/quality.yml` because the publishing token used for this initial release does not have workflow-write permission. Maintainers can copy it to `.github/workflows/quality.yml` when workflow permission is available.
