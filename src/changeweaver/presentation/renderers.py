"""Stable renderers for humans and CI consumers."""

from __future__ import annotations

import html
import json
from typing import Any, cast

from changeweaver.domain.models import (
    ChangePlan,
    ChangeSet,
    Finding,
    ImpactReport,
    Severity,
    Snapshot,
    VerificationReceipt,
    dataclass_value,
)
from changeweaver.infrastructure.serialization import snapshot_to_dict


def envelope(command: str, status: str, result: Any, diagnostics: Any = (), warnings: Any = ()) -> dict[str, Any]:
    return {
        "protocol_version": 1,
        "command": command,
        "status": status,
        "diagnostics": [dataclass_value(item) for item in diagnostics],
        "warnings": [dataclass_value(item) for item in warnings],
        "result": result,
        "verification": {"mutates_files": False, "deterministic": True},
    }


def render_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def snapshot_result(snapshot: Snapshot) -> dict[str, Any]:
    return snapshot_to_dict(snapshot)


def changes_result(changes: ChangeSet) -> dict[str, Any]:
    return cast(dict[str, Any], dataclass_value(changes))


def impact_result(impact: ImpactReport) -> dict[str, Any]:
    return cast(dict[str, Any], dataclass_value(impact))


def plan_result(plan: ChangePlan) -> dict[str, Any]:
    return cast(dict[str, Any], dataclass_value(plan))


def receipt_result(receipt: VerificationReceipt) -> dict[str, Any]:
    return cast(dict[str, Any], dataclass_value(receipt))


def render_text_receipt(receipt: VerificationReceipt) -> str:
    baseline = receipt.baseline_digest[:12] if receipt.baseline_digest else "none"
    impact = f"{receipt.impact_score}/100" if receipt.impact_score is not None else "not requested"
    return (
        f"Verification: {receipt.status.upper()}\n"
        f"Receipt: {receipt.digest[:12]}\n"
        f"Repository: {receipt.repository}\n"
        f"Snapshot: {receipt.snapshot_digest[:12]}\n"
        f"Baseline: {baseline}\n"
        f"Changed: {str(receipt.changed).lower()}\n"
        f"Checks: {', '.join(receipt.checks)}\n"
        f"Findings: {receipt.findings_count} ({receipt.error_findings} errors)\n"
        f"Impact: {impact}\n"
        f"Diagnostics: {len(receipt.diagnostics)}\n"
    )


def render_text_snapshot(snapshot: Snapshot) -> str:
    return (
        f"Snapshot {snapshot.digest[:12]}\n"
        f"Repository: {snapshot.repository}\n"
        f"Analyzer: {snapshot.analyzer}\n"
        f"Nodes: {len(snapshot.nodes)}\n"
        f"Edges: {len(snapshot.edges)}\n"
        f"Diagnostics: {len(snapshot.diagnostics)}\n"
    )


def render_text_changes(changes: ChangeSet) -> str:
    lines = [
        "Structural diff",
        f"Added nodes: {len(changes.added_nodes)}",
        f"Removed nodes: {len(changes.removed_nodes)}",
        f"Added edges: {len(changes.added_edges)}",
        f"Removed edges: {len(changes.removed_edges)}",
    ]
    for node in changes.added_nodes:
        lines.append(f"  + node {node.path}")
    for node in changes.removed_nodes:
        lines.append(f"  - node {node.path}")
    for edge in changes.added_edges:
        lines.append(f"  + {edge.source} -[{edge.relation}]-> {edge.target}")
    for edge in changes.removed_edges:
        lines.append(f"  - {edge.source} -[{edge.relation}]-> {edge.target}")
    return "\n".join(lines) + "\n"


def render_text_impact(impact: ImpactReport) -> str:
    lines = [
        f"Impact score: {impact.score}/100",
        f"Roots: {', '.join(impact.roots) or 'none'}",
        f"Affected nodes: {len(impact.affected)}",
        f"Boundary crossings: {impact.boundary_crossings}",
        "Paths:",
    ]
    lines.extend(f"  {' -> '.join(path)}" for path in impact.path_samples)
    return "\n".join(lines) + "\n"


def render_text_findings(findings: tuple[Finding, ...]) -> str:
    if not findings:
        return "No architecture findings.\n"
    lines = [f"Architecture findings: {len(findings)}"]
    for finding in findings:
        location = f"{finding.path}:{finding.line}" if finding.path else "repository"
        lines.append(f"  [{finding.severity.value}] {finding.rule_id} at {location}: {finding.message}")
        lines.extend(f"    evidence: {item}" for item in finding.evidence)
    return "\n".join(lines) + "\n"


def render_text_plan(plan: ChangePlan) -> str:
    lines = [plan.title, plan.summary]
    for step in plan.steps:
        lines.append(f"{step.order}. {step.action}: {step.reason}")
        lines.extend(f"   evidence: {item}" for item in step.evidence)
    return "\n".join(lines) + "\n"


def render_mermaid(snapshot: Snapshot) -> str:
    lines = ["flowchart LR"]
    for node in snapshot.nodes:
        label = node.path.replace('"', "'")
        lines.append(f'    "{node.node_id}"["{label}"]')
    for edge in snapshot.edges:
        relation = edge.relation.replace('"', "'")
        lines.append(f'    "{edge.source}" -->|"{relation}"| "{edge.target}"')
    return "\n".join(lines) + "\n"


def render_sarif(findings: tuple[Finding, ...]) -> str:
    rules: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []
    for finding in findings:
        rules.setdefault(
            finding.rule_id,
            {"id": finding.rule_id, "shortDescription": {"text": finding.message}},
        )
        result: dict[str, Any] = {
            "ruleId": finding.rule_id,
            "level": _sarif_level(finding.severity),
            "message": {"text": finding.message},
        }
        if finding.path:
            location: dict[str, Any] = {
                "physicalLocation": {"artifactLocation": {"uri": finding.path}}
            }
            if finding.line:
                location["physicalLocation"]["region"] = {"startLine": finding.line}
            result["locations"] = [location]
        results.append(result)
    payload = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{"tool": {"driver": {"name": "ChangeWeaver", "rules": list(rules.values())}}, "results": results}],
    }
    return render_json(payload)


def render_html(title: str, body: str) -> str:
    return """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>
body{{font-family:system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#202124;background:#f7f8fc}}
main{{background:#fff;border:1px solid #dfe3ef;border-radius:14px;padding:2rem;box-shadow:0 8px 30px #17255412}}
pre{{white-space:pre-wrap;overflow:auto;background:#111827;color:#e5e7eb;border-radius:10px;padding:1rem}}
.badge{{color:#4338ca;font-weight:700;letter-spacing:.04em;text-transform:uppercase}}
</style></head><body><main><div class="badge">ChangeWeaver report</div><h1>{title}</h1><pre>{body}</pre></main></body></html>
""".format(title=html.escape(title), body=html.escape(body))


def _sarif_level(severity: Severity) -> str:
    return "error" if severity == Severity.ERROR else "warning" if severity == Severity.WARNING else "note"
