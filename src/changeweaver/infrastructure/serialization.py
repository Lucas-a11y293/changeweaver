"""Canonical artifact serialization and snapshot persistence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from changeweaver.domain.errors import SnapshotError
from changeweaver.domain.models import (
    Diagnostic,
    Edge,
    Node,
    Severity,
    Snapshot,
    VerificationReceipt,
    dataclass_value,
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def snapshot_without_digest(snapshot: Snapshot) -> dict[str, Any]:
    return {
        "protocol_version": snapshot.protocol_version,
        "snapshot_version": snapshot.snapshot_version,
        "repository": snapshot.repository,
        "analyzer": snapshot.analyzer,
        "nodes": [dataclass_value(node) for node in snapshot.nodes],
        "edges": [dataclass_value(edge) for edge in snapshot.edges],
        "diagnostics": [dataclass_value(item) for item in snapshot.diagnostics],
    }


def snapshot_to_dict(snapshot: Snapshot) -> dict[str, Any]:
    payload = snapshot_without_digest(snapshot)
    payload["digest"] = snapshot.digest
    return payload


def snapshot_digest(snapshot: Snapshot) -> str:
    encoded = canonical_json(snapshot_without_digest(snapshot)).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def receipt_without_digest(receipt: VerificationReceipt) -> dict[str, Any]:
    payload = dataclass_value(receipt)
    if not isinstance(payload, dict):
        raise TypeError("receipt must serialize to an object")
    payload.pop("digest", None)
    return payload


def receipt_digest(receipt: VerificationReceipt) -> str:
    encoded = canonical_json(receipt_without_digest(receipt)).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def receipt_to_dict(receipt: VerificationReceipt) -> dict[str, Any]:
    payload = receipt_without_digest(receipt)
    payload["digest"] = receipt.digest
    return payload


def write_receipt(path: Path, receipt: VerificationReceipt) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(receipt_to_dict(receipt)) + "\n", encoding="utf-8")


def write_snapshot(path: Path, snapshot: Snapshot) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = snapshot_to_dict(snapshot)
    path.write_text(canonical_json(payload) + "\n", encoding="utf-8")


def read_snapshot(path: Path) -> Snapshot:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SnapshotError(f"Could not read snapshot {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise SnapshotError("Snapshot root must be an object")
    try:
        snapshot = Snapshot(
            protocol_version=_required_int(raw, "protocol_version"),
            snapshot_version=_required_int(raw, "snapshot_version"),
            repository=_required_string(raw, "repository"),
            analyzer=_required_string(raw, "analyzer"),
            nodes=tuple(_node(item) for item in _required_list(raw, "nodes")),
            edges=tuple(_edge(item) for item in _required_list(raw, "edges")),
            diagnostics=tuple(_diagnostic(item) for item in _required_list(raw, "diagnostics")),
            digest=_required_string(raw, "digest"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SnapshotError(f"Malformed snapshot {path}: {exc}") from exc
    if snapshot.protocol_version != 1 or snapshot.snapshot_version != 1:
        raise SnapshotError("Unsupported snapshot protocol or version")
    expected = snapshot_digest(snapshot)
    if expected != snapshot.digest:
        raise SnapshotError("Snapshot digest does not match its canonical content")
    if tuple(sorted(snapshot.nodes, key=lambda item: item.node_id)) != snapshot.nodes:
        raise SnapshotError("Snapshot nodes are not sorted")
    if tuple(sorted(snapshot.edges, key=lambda item: item.fact_key)) != snapshot.edges:
        raise SnapshotError("Snapshot edges are not sorted")
    return snapshot


def _node(value: Any) -> Node:
    if not isinstance(value, dict):
        raise TypeError("node must be an object")
    return Node(
        node_id=str(value["node_id"]),
        kind=str(value["kind"]),
        path=str(value["path"]),
        package=str(value["package"]) if value.get("package") is not None else None,
        layer=str(value["layer"]) if value.get("layer") is not None else None,
    )


def _edge(value: Any) -> Edge:
    if not isinstance(value, dict):
        raise TypeError("edge must be an object")
    return Edge(
        source=str(value["source"]),
        target=str(value["target"]),
        relation=str(value["relation"]),
        source_line=int(value["source_line"]) if value.get("source_line") is not None else None,
        uri=str(value["uri"]) if value.get("uri") is not None else None,
    )


def _diagnostic(value: Any) -> Diagnostic:
    if not isinstance(value, dict):
        raise TypeError("diagnostic must be an object")
    return Diagnostic(
        code=str(value["code"]),
        message=str(value["message"]),
        path=str(value["path"]) if value.get("path") is not None else None,
        line=int(value["line"]) if value.get("line") is not None else None,
        severity=Severity(str(value.get("severity", "warning"))),
    )


def _required_list(value: dict[str, Any], key: str) -> list[Any]:
    result = value[key]
    if not isinstance(result, list):
        raise TypeError(f"{key} must be a list")
    return result


def _required_string(value: dict[str, Any], key: str) -> str:
    result = value[key]
    if not isinstance(result, str) or not result:
        raise TypeError(f"{key} must be a non-empty string")
    return result


def _required_int(value: dict[str, Any], key: str) -> int:
    result: Any = value[key]
    if isinstance(result, bool) or not isinstance(result, int):
        raise TypeError(f"{key} must be an integer")
    if isinstance(result, int):
        return result
    raise TypeError(f"{key} must be an integer")
