"""Conservative lexical facts for Dart and Flutter repositories."""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from changeweaver.domain.models import ArchitectureContract, Diagnostic, Edge, Node, Severity
from changeweaver.infrastructure.config import match_layer
from changeweaver.infrastructure.filesystem import iter_dart_files, read_text, safe_path

_DIRECTIVE = re.compile(r"^\s*(import|export|part)\s+['\"]([^'\"]+)['\"]")


@dataclass(frozen=True, slots=True)
class ScanResult:
    nodes: tuple[Node, ...]
    edges: tuple[Edge, ...]
    diagnostics: tuple[Diagnostic, ...]


@dataclass(frozen=True, slots=True)
class PackageRoot:
    name: str
    root: Path


def scan_repository(root: Path, contract: ArchitectureContract) -> ScanResult:
    root = root.resolve(strict=True)
    package_roots = discover_package_roots(root)
    package_map = {item.name: item.root for item in package_roots}
    nodes_by_id: dict[str, Node] = {}
    edges: list[Edge] = []
    diagnostics: list[Diagnostic] = []

    files = list(iter_dart_files(root, contract))
    if len(files) > contract.limits.max_nodes:
        raise ValueError(
            f"Repository contains {len(files)} Dart files; analysis.max_nodes is "
            f"{contract.limits.max_nodes}"
        )
    for path, relative in files:
        node_id = f"dart:{relative}"
        node = Node(
            node_id=node_id,
            kind="dart_library",
            path=relative,
            package=package_for_path(relative, package_roots, root),
            layer=match_layer(relative, contract.layers),
        )
        nodes_by_id[node_id] = node
        text = read_text(path, relative)
        for line_number, line in enumerate(text.splitlines(), start=1):
            match = _DIRECTIVE.match(line)
            if not match:
                continue
            relation, uri = match.groups()
            target_id, target_node, diagnostic = resolve_uri(
                root=root,
                source_path=path,
                source_relative=relative,
                uri=uri,
                package_roots=package_map,
                layers=contract.layers,
            )
            if target_node is not None:
                nodes_by_id.setdefault(target_node.node_id, target_node)
            if diagnostic is not None:
                diagnostics.append(
                    Diagnostic(
                        code=diagnostic.code,
                        message=diagnostic.message,
                        path=relative,
                        line=line_number,
                        severity=diagnostic.severity,
                    )
                )
            edges.append(Edge(node_id, target_id, relation, line_number, uri))

    if len(nodes_by_id) > contract.limits.max_nodes * 2:
        raise ValueError("Analysis produced too many local and external nodes")
    return ScanResult(
        nodes=tuple(sorted(nodes_by_id.values(), key=lambda item: item.node_id)),
        edges=tuple(sorted(set(edges), key=lambda item: item.fact_key)),
        diagnostics=tuple(sorted(diagnostics, key=lambda item: (item.path or "", item.line or 0, item.code))),
    )


def discover_package_roots(root: Path) -> tuple[PackageRoot, ...]:
    candidates: list[PackageRoot] = []
    for directory, _directories, files in _walk_directories(root):
        if "pubspec.yaml" not in files:
            continue
        path = Path(directory) / "pubspec.yaml"
        try:
            raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError):
            continue
        if not isinstance(raw, dict) or not isinstance(raw.get("name"), str):
            continue
        candidates.append(PackageRoot(raw["name"].strip(), Path(directory)))
    return tuple(sorted(candidates, key=lambda item: (len(item.root.parts), item.name)))


def package_for_path(
    relative: str, package_roots: tuple[PackageRoot, ...], repository_root: Path
) -> str | None:
    candidate = repository_root / relative
    matches = [item for item in package_roots if _is_relative_to(candidate, item.root)]
    if not matches:
        return None
    return sorted(matches, key=lambda item: len(item.root.parts), reverse=True)[0].name


def resolve_uri(
    root: Path,
    source_path: Path,
    source_relative: str,
    uri: str,
    package_roots: dict[str, Path],
    layers: tuple[Any, ...],
) -> tuple[str, Node | None, Diagnostic | None]:
    if uri.startswith("dart:"):
        node_id = f"external:{uri}"
        return node_id, Node(node_id, "external", uri), None

    target_path: Path | None = None
    if uri.startswith("package:"):
        parts = uri.removeprefix("package:").split("/", 1)
        package_name = parts[0]
        suffix = parts[1] if len(parts) == 2 else ""
        package_root = package_roots.get(package_name)
        if package_root is not None:
            target_path = package_root / "lib" / suffix
    else:
        try:
            target_path = safe_path(root, (source_path.parent / uri).relative_to(root).as_posix())
        except (ValueError, OSError):
            target_path = None

    if target_path is not None:
        try:
            relative = target_path.relative_to(root).as_posix()
        except ValueError:
            relative = ""
        if relative and target_path.is_file() and target_path.suffix == ".dart":
            node_id = f"dart:{relative}"
            return (
                node_id,
                Node(
                    node_id,
                    "dart_library",
                    relative,
                    package_for_path(relative, _package_tuple(package_roots), root),
                    match_layer(relative, layers),
                ),
                None,
            )

    node_id = f"unresolved:{uri}"
    diagnostic = Diagnostic(
        code="unresolved-import",
        message=f"Could not resolve Dart URI '{uri}' from {source_relative}.",
        severity=Severity.WARNING,
    )
    return node_id, Node(node_id, "unresolved", uri), diagnostic


def _package_tuple(package_roots: dict[str, Path]) -> tuple[PackageRoot, ...]:
    return tuple(PackageRoot(name, root) for name, root in package_roots.items())


def _walk_directories(root: Path) -> Iterator[tuple[str, list[str], list[str]]]:
    import os

    for directory, directories, files in os.walk(root, topdown=True, followlinks=False):
        directory_path = Path(directory)
        directories[:] = [
            name
            for name in directories
            if not (directory_path / name).is_symlink() and name not in {".git", ".dart_tool", "build"}
        ]
        yield directory, directories, files


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
