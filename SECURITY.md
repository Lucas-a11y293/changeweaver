# Security Policy

## Supported versions

Only the latest release on the `main` branch is supported with security fixes during the alpha period. Snapshot and contract formats may evolve before 1.0, but unsafe behavior should be reported immediately.

## Security model

ChangeWeaver treats the analyzed repository as untrusted data. The MVP does not execute Dart, Flutter, shell commands, hooks, package managers, or network requests. It canonicalizes the repository root, rejects absolute and escaping paths, does not follow symlinks outside the root, enforces file and node limits, and escapes HTML/SARIF output. It does not collect telemetry or upload source code.

## Reporting a vulnerability

Please do not disclose vulnerabilities in a public issue. Open a private GitHub Security Advisory for the repository when available, or contact the maintainer privately through the account associated with the repository. Include a clear description, affected version, reproduction steps that do not contain secrets, and the potential impact. Do not include API keys, tokens, private source code, or personal data in a report.

## Dependency and supply-chain hygiene

Dependencies are intentionally minimal and pinned to compatible major ranges in `pyproject.toml`. Pull requests should run the test suite, lint, type checking, and dependency audit where available. Generated artifacts and local environments must remain ignored by Git.
