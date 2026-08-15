# Competitive Landscape

ChangeWeaver is intentionally positioned as a focused workflow artifact rather than a claim to be the first architecture-intelligence tool. Existing projects solve adjacent problems well, so the project must state its boundary clearly.

| Area | Representative tool | What it does well | ChangeWeaver’s distinct boundary |
|---|---|---|---|
| Templates and scaffolding | [Mason][1], [Very Good CLI][2] | Reusable bricks and opinionated Flutter/Dart project starters. | ChangeWeaver starts after the repository exists and reasons about evolution, not initial generation. |
| Workspace operations | [Melos][3] | Pub Workspaces setup, bootstrapping, scripts, and multi-package operations. | ChangeWeaver consumes workspace facts to explain dependency and architecture impact. |
| Dart dependency graphs | [Lakos][4] | Graphviz output, cycles, orphans, and coupling metrics for Dart libraries. | ChangeWeaver stores reviewable snapshots, evaluates contracts, and produces a no-mutation plan. |
| Flutter architecture linting | [DCM architecture rules][5] | Enforceable import/type/export boundaries in IDE and CI. | ChangeWeaver provides a small open contract format plus impact evidence and stable artifact protocol. |
| General architecture intelligence | [enola][6], [Drift][7] | Snapshots, architectural regressions, erosion, temporal signals, CI, and agent integrations. | ChangeWeaver is deliberately Flutter/Dart-first, local-first, conservative, and centered on a reviewable architecture ledger. |

## Why this narrow scope matters

Flutter’s official architecture overview describes an extensible layered system in which libraries depend on underlying layers and platform integration crosses Dart and native boundaries [8]. That structure makes a repository-owned contract useful, but only if the contract is explicit, the evidence is reproducible, and unresolved semantics are reported rather than guessed.

ChangeWeaver therefore does not replace a compiler, analyzer, linter, workspace manager, or general code-intelligence product. Its MVP composes a small workflow: scan facts, persist a deterministic snapshot, compare structural changes, calculate reverse reachability, check explicit rules, and produce a verification plan. The result is intentionally portable across terminal, CI, JSON, SARIF, Mermaid, and HTML.

## References

[1]: https://github.com/felangel/mason "Mason — reusable Dart templates"
[2]: https://verygood.ventures/blog/generate-flutter-plugins-with-very-good-cli/ "Very Good CLI — Flutter plugin generation"
[3]: https://melos.invertase.dev/getting-started "Melos — Getting Started"
[4]: https://pub.dev/packages/lakos "Lakos — Dart dependency graph"
[5]: https://dcm.dev/docs/guides/advanced-architecture-rules-guide/ "DCM — Enforcing Architecture Boundaries"
[6]: https://github.com/enola-labs/enola "enola — architecture intelligence"
[7]: https://github.com/marketplace/actions/drift-architectural-erosion-check "Drift — Architectural Erosion Check"
[8]: https://docs.flutter.dev/resources/architectural-overview "Flutter architectural overview"
