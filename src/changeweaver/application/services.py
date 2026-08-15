"""Application use cases built on top of pure domain models."""

from __future__ import annotations

from pathlib import Path

from changeweaver.adapters.dart import scan_repository
from changeweaver.domain.errors import SnapshotError
from changeweaver.domain.graph import Graph
from changeweaver.domain.models import (
    ArchitectureContract,
    ChangePlan,
    ChangePlanStep,
    ChangeSet,
    Diagnostic,
    Finding,
    ImpactReport,
    Severity,
    Snapshot,
    VerificationReceipt,
)
from changeweaver.infrastructure.serialization import receipt_digest, snapshot_digest

ANALYZER_ID = "lexical-dart/0.1"


def build_snapshot(root: Path, contract: ArchitectureContract) -> Snapshot:
    result = scan_repository(root, contract)
    snapshot = Snapshot(
        protocol_version=1,
        snapshot_version=1,
        repository=contract.project.name,
        analyzer=ANALYZER_ID,
        nodes=result.nodes,
        edges=result.edges,
        diagnostics=result.diagnostics,
        digest="",
    )
    return Snapshot(
        protocol_version=snapshot.protocol_version,
        snapshot_version=snapshot.snapshot_version,
        repository=snapshot.repository,
        analyzer=snapshot.analyzer,
        nodes=snapshot.nodes,
        edges=snapshot.edges,
        diagnostics=snapshot.diagnostics,
        digest=snapshot_digest(snapshot),
    )


def diff_snapshots(baseline: Snapshot, current: Snapshot) -> ChangeSet:
    if baseline.repository != current.repository or baseline.analyzer != current.analyzer:
        raise SnapshotError(
            "Snapshots are not comparable: repository identity or analyzer differs. "
            "Use a baseline from the same project and analyzer."
        )
    baseline_nodes = {node.node_id: node for node in baseline.nodes}
    current_nodes = {node.node_id: node for node in current.nodes}
    baseline_edges = {edge.fact_key: edge for edge in baseline.edges}
    current_edges = {edge.fact_key: edge for edge in current.edges}
    return ChangeSet(
        added_nodes=tuple(sorted((current_nodes[key] for key in current_nodes.keys() - baseline_nodes.keys()), key=lambda item: item.node_id)),
        removed_nodes=tuple(sorted((baseline_nodes[key] for key in baseline_nodes.keys() - current_nodes.keys()), key=lambda item: item.node_id)),
        added_edges=tuple(sorted((current_edges[key] for key in current_edges.keys() - baseline_edges.keys()), key=lambda item: item.fact_key)),
        removed_edges=tuple(sorted((baseline_edges[key] for key in baseline_edges.keys() - current_edges.keys()), key=lambda item: item.fact_key)),
        diagnostics=tuple(sorted((*baseline.diagnostics, *current.diagnostics), key=lambda item: (item.path or "", item.line or 0, item.code))),
    )


def impact_report(
    snapshot: Snapshot,
    targets: tuple[str, ...],
    max_nodes: int,
    max_path_samples: int,
) -> ImpactReport:
    node_map = snapshot.node_map
    roots: set[str] = set()
    diagnostics: list[Diagnostic] = []
    for target in targets:
        candidate = target if target.startswith(("dart:", "external:", "unresolved:")) else f"dart:{target}"
        if candidate in node_map:
            roots.add(candidate)
            continue
        matches = sorted(node.node_id for node in snapshot.nodes if node.path == target or node.node_id.endswith(f"/{target}"))
        if matches:
            roots.add(matches[0])
        else:
            diagnostics.append(
                Diagnostic("target-not-found", f"Impact target was not found: {target}", severity=Severity.ERROR)
            )
    if not roots:
        return ImpactReport((), (), (), 0, 0, tuple(diagnostics))
    graph = Graph(snapshot.nodes, snapshot.edges)
    affected, paths = graph.reverse_reachable(tuple(sorted(roots)), max_nodes, max_path_samples)
    crossings = graph.boundary_crossings(paths)
    layers = {node_map[node_id].layer for node_id in affected if node_id in node_map and node_map[node_id].layer}
    score = min(100, 20 + (10 * len(layers)) + (2 * len(affected)) + (5 * crossings))
    return ImpactReport(tuple(sorted(roots)), affected, paths, score, crossings, tuple(diagnostics))


def check_contract(
    snapshot: Snapshot,
    contract: ArchitectureContract,
    strict_unclassified: bool = False,
) -> tuple[Finding, ...]:
    nodes = snapshot.node_map
    findings: list[Finding] = []
    for node in snapshot.nodes:
        if node.kind == "dart_library" and node.layer is None:
            findings.append(
                Finding(
                    rule_id="unclassified-node",
                    severity=Severity.ERROR if strict_unclassified else Severity.WARNING,
                    message=f"No architecture layer matches {node.path}.",
                    path=node.path,
                    evidence=("Add a layer path pattern or explicitly accept unclassified nodes.",),
                )
            )
    for edge in snapshot.edges:
        source = nodes.get(edge.source)
        target = nodes.get(edge.target)
        if source is None or target is None or target.kind != "dart_library":
            continue
        for rule in contract.rules:
            if source.layer not in rule.from_layers or target.layer not in rule.deny_layers:
                continue
            findings.append(
                Finding(
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    message=rule.message,
                    source=source.node_id,
                    target=target.node_id,
                    path=source.path,
                    line=edge.source_line,
                    evidence=(
                        f"{source.path}:{edge.source_line or 0} imports {target.path}",
                        f"source layer={source.layer}; target layer={target.layer}",
                    ),
                )
            )
    return tuple(sorted(findings, key=lambda item: item.finding_key))


def make_change_plan(
    changes: ChangeSet,
    impact: ImpactReport | None,
    findings: tuple[Finding, ...],
) -> ChangePlan:
    steps: list[ChangePlanStep] = []
    order = 1
    if changes.changed:
        steps.append(
            ChangePlanStep(
                order,
                "Review structural diff",
                f"{len(changes.added_nodes)} nodes and {len(changes.added_edges)} edges added; "
                f"{len(changes.removed_nodes)} nodes and {len(changes.removed_edges)} edges removed.",
                tuple(edge.source for edge in changes.added_edges[:5]),
            )
        )
        order += 1
    if impact is not None and impact.roots:
        steps.append(
            ChangePlanStep(
                order,
                "Run targeted verification",
                f"Blast radius score is {impact.score}/100 across {len(impact.affected)} nodes.",
                tuple(" -> ".join(path) for path in impact.path_samples[:5]),
            )
        )
        order += 1
    for finding in findings:
        steps.append(
            ChangePlanStep(
                order,
                "Resolve architecture finding",
                f"{finding.rule_id}: {finding.message}",
                finding.evidence,
            )
        )
        order += 1
    if not steps:
        steps.append(ChangePlanStep(1, "Run repository tests", "No structural regression was detected.", ()))
    summary = (
        f"Review {len(steps)} verification step(s); ChangeWeaver will not mutate repository files."
    )
    return ChangePlan("ChangeWeaver verification plan", summary, tuple(steps), findings, impact, False)


def has_error_findings(findings: tuple[Finding, ...]) -> bool:
    return any(item.severity == Severity.ERROR for item in findings)


def build_verification_receipt(
    current: Snapshot,
    baseline: Snapshot | None,
    findings: tuple[Finding, ...],
    impact: ImpactReport | None,
) -> VerificationReceipt:
    """Create deterministic evidence for the exact checks performed."""

    changes = diff_snapshots(baseline, current) if baseline is not None else None
    diagnostics = tuple(current.diagnostics)
    if changes is not None:
        diagnostics = tuple((*diagnostics, *changes.diagnostics))
    checks = ["snapshot", "architecture-contract"]
    if baseline is not None:
        checks.insert(1, "structural-diff")
    if impact is not None:
        checks.append("reverse-impact")
    errors = sum(item.severity == Severity.ERROR for item in findings)
    status = "failed" if errors or any(item.severity == Severity.ERROR for item in diagnostics) else "passed"
    receipt = VerificationReceipt(
        protocol_version=1,
        receipt_version=1,
        repository=current.repository,
        snapshot_digest=current.digest,
        baseline_digest=baseline.digest if baseline is not None else None,
        changed=changes.changed if changes is not None else bool(findings or current.diagnostics),
        checks=tuple(checks),
        findings_count=len(findings),
        error_findings=errors,
        impact_score=impact.score if impact is not None else None,
        status=status,
        diagnostics=diagnostics,
        digest="",
    )
    return VerificationReceipt(
        protocol_version=receipt.protocol_version,
        receipt_version=receipt.receipt_version,
        repository=receipt.repository,
        snapshot_digest=receipt.snapshot_digest,
        baseline_digest=receipt.baseline_digest,
        changed=receipt.changed,
        checks=receipt.checks,
        findings_count=receipt.findings_count,
        error_findings=receipt.error_findings,
        impact_score=receipt.impact_score,
        status=receipt.status,
        diagnostics=receipt.diagnostics,
        digest=receipt_digest(receipt),
    )
