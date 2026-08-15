"""Stable domain models shared by every ChangeWeaver adapter and renderer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class Node:
    """A repository-relative analyzable unit."""

    node_id: str
    kind: str
    path: str
    package: str | None = None
    layer: str | None = None


@dataclass(frozen=True, slots=True)
class Edge:
    """A typed relationship between two nodes."""

    source: str
    target: str
    relation: str
    source_line: int | None = None
    uri: str | None = None

    @property
    def fact_key(self) -> tuple[str, str, str, int | None, str | None]:
        return (self.source, self.target, self.relation, self.source_line, self.uri)


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str
    message: str
    path: str | None = None
    line: int | None = None
    severity: Severity = Severity.WARNING


@dataclass(frozen=True, slots=True)
class Layer:
    name: str
    paths: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ArchitectureRule:
    rule_id: str
    from_layers: tuple[str, ...]
    deny_layers: tuple[str, ...]
    severity: Severity
    message: str


@dataclass(frozen=True, slots=True)
class AnalysisLimits:
    max_path_samples: int = 8
    max_nodes: int = 10_000
    max_file_bytes: int = 1_000_000


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    name: str
    roots: tuple[str, ...]
    include: tuple[str, ...]
    exclude: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ArchitectureContract:
    version: int
    project: ProjectConfig
    layers: tuple[Layer, ...]
    rules: tuple[ArchitectureRule, ...]
    limits: AnalysisLimits = field(default_factory=AnalysisLimits)


@dataclass(frozen=True, slots=True)
class Snapshot:
    protocol_version: int
    snapshot_version: int
    repository: str
    analyzer: str
    nodes: tuple[Node, ...]
    edges: tuple[Edge, ...]
    diagnostics: tuple[Diagnostic, ...]
    digest: str

    @property
    def node_map(self) -> dict[str, Node]:
        return {node.node_id: node for node in self.nodes}


@dataclass(frozen=True, slots=True)
class ChangeSet:
    added_nodes: tuple[Node, ...]
    removed_nodes: tuple[Node, ...]
    added_edges: tuple[Edge, ...]
    removed_edges: tuple[Edge, ...]
    diagnostics: tuple[Diagnostic, ...] = ()

    @property
    def changed(self) -> bool:
        return bool(self.added_nodes or self.removed_nodes or self.added_edges or self.removed_edges)


@dataclass(frozen=True, slots=True)
class Finding:
    rule_id: str
    severity: Severity
    message: str
    source: str | None = None
    target: str | None = None
    path: str | None = None
    line: int | None = None
    evidence: tuple[str, ...] = ()

    @property
    def finding_key(self) -> tuple[str, str, str, str, int]:
        return (
            self.rule_id,
            self.source or "",
            self.target or "",
            self.path or "",
            self.line or 0,
        )


@dataclass(frozen=True, slots=True)
class ImpactReport:
    roots: tuple[str, ...]
    affected: tuple[str, ...]
    path_samples: tuple[tuple[str, ...], ...]
    score: int
    boundary_crossings: int
    diagnostics: tuple[Diagnostic, ...] = ()


@dataclass(frozen=True, slots=True)
class ChangePlanStep:
    order: int
    action: str
    reason: str
    evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ChangePlan:
    title: str
    summary: str
    steps: tuple[ChangePlanStep, ...]
    findings: tuple[Finding, ...]
    impact: ImpactReport | None
    mutates_files: bool = False


@dataclass(frozen=True, slots=True)
class VerificationReceipt:
    """Deterministic evidence that a repository state was checked."""

    protocol_version: int
    receipt_version: int
    repository: str
    snapshot_digest: str
    baseline_digest: str | None
    changed: bool
    checks: tuple[str, ...]
    findings_count: int
    error_findings: int
    impact_score: int | None
    status: str
    diagnostics: tuple[Diagnostic, ...] = ()
    digest: str = ""


def dataclass_dict(value: Any) -> dict[str, Any]:
    """Convert supported frozen dataclasses to a JSON-ready recursive mapping."""

    if hasattr(value, "__dataclass_fields__"):
        result: dict[str, Any] = {}
        for name in value.__dataclass_fields__:
            item = getattr(value, name)
            result[name] = dataclass_value(item)
        return result
    raise TypeError(f"Unsupported value: {type(value)!r}")


def dataclass_value(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return dataclass_dict(value)
    if isinstance(value, tuple):
        return [dataclass_value(item) for item in value]
    if isinstance(value, list):
        return [dataclass_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): dataclass_value(item) for key, item in value.items()}
    if isinstance(value, StrEnum):
        return value.value
    return value
