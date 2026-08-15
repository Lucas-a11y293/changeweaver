# Contributing to ChangeWeaver

Thank you for considering a contribution. ChangeWeaver is intentionally small at its core: deterministic facts, explainable graph operations, and portable artifacts are more important than a large feature count.

## Development setup

Use Python 3.11 or newer:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
ruff check src tests
mypy src
```

## Design expectations

Keep domain logic independent from Typer, filesystem details, GitHub Actions, and network access. Every analysis result must be deterministic and must surface uncertainty as a diagnostic. Do not execute target repository code or package-manager commands. New policy rules should be data-driven and must include a focused fixture or unit test.

## Pull requests

A pull request should explain the user problem, the invariant it preserves, and the verification performed. If it changes the JSON protocol, SARIF shape, snapshot schema, or exit codes, update the relevant documentation and add a compatibility regression test. Keep commits focused and use Conventional Commit prefixes such as `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, and `chore:`.

## Scope boundaries

The lexical Dart adapter deliberately does not claim compiler-level semantic analysis. Contributions that add richer parsing should introduce a separate adapter, document its supported versions, and preserve the conservative fallback. New external integrations must be optional, explicit, and tested without network access in the default suite.

## Reporting vulnerabilities

Please do not open a public issue for a suspected security vulnerability. Follow the process in [`SECURITY.md`](SECURITY.md).
