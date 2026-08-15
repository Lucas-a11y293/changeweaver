"""Validated YAML configuration for architecture contracts."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from changeweaver.domain.errors import ConfigurationError
from changeweaver.domain.models import (
    AnalysisLimits,
    ArchitectureContract,
    ArchitectureRule,
    Layer,
    ProjectConfig,
    Severity,
)

DEFAULT_CONFIG = """version: 1
project:
  name: sample_app
  roots: [lib]
  include: ['**/*.dart']
  exclude: ['**/*.g.dart', '**/*.freezed.dart', '.dart_tool/**']
architecture:
  layers: []
  rules: []
analysis:
  max_path_samples: 8
  max_nodes: 10000
  max_file_bytes: 1000000
"""


def load_contract(root: Path, filename: str = "changeweaver.yaml") -> ArchitectureContract:
    path = root / filename
    if not path.is_file():
        raise ConfigurationError(f"Contract not found: {path.relative_to(root)}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ConfigurationError(f"Could not read contract {path.name}: {exc}") from exc
    return parse_contract(raw)


def parse_contract(raw: Any) -> ArchitectureContract:
    mapping = _mapping(raw, "contract")
    _keys(mapping, {"version", "project", "architecture", "analysis"}, "contract")
    version = _int(mapping.get("version", 1), "version")
    if version != 1:
        raise ConfigurationError(f"Unsupported contract version: {version}")

    project_raw = _mapping(mapping.get("project"), "project")
    _keys(project_raw, {"name", "roots", "include", "exclude"}, "project")
    project = ProjectConfig(
        name=_string(project_raw.get("name", "changeweaver-project"), "project.name"),
        roots=_strings(project_raw.get("roots", ["lib"]), "project.roots"),
        include=_strings(project_raw.get("include", ["**/*.dart"]), "project.include"),
        exclude=_strings(
            project_raw.get("exclude", ["**/*.g.dart", "**/*.freezed.dart", ".dart_tool/**"]),
            "project.exclude",
            allow_empty=True,
        ),
    )

    architecture_raw = _mapping(mapping.get("architecture", {}), "architecture")
    _keys(architecture_raw, {"layers", "rules"}, "architecture")
    layers = tuple(_parse_layer(item, index) for index, item in enumerate(architecture_raw.get("layers", [])))
    rules = tuple(_parse_rule(item, index) for index, item in enumerate(architecture_raw.get("rules", [])))

    analysis_raw = _mapping(mapping.get("analysis", {}), "analysis")
    _keys(analysis_raw, {"max_path_samples", "max_nodes", "max_file_bytes"}, "analysis")
    limits = AnalysisLimits(
        max_path_samples=_positive_int(analysis_raw.get("max_path_samples", 8), "analysis.max_path_samples"),
        max_nodes=_positive_int(analysis_raw.get("max_nodes", 10_000), "analysis.max_nodes"),
        max_file_bytes=_positive_int(analysis_raw.get("max_file_bytes", 1_000_000), "analysis.max_file_bytes"),
    )
    return ArchitectureContract(version, project, layers, rules, limits)


def match_layer(path: str, layers: tuple[Layer, ...]) -> str | None:
    matches: list[tuple[int, str]] = []
    for layer in layers:
        for pattern in layer.paths:
            if _matches(path, pattern):
                matches.append((len(pattern), layer.name))
    if not matches:
        return None
    return sorted(matches, key=lambda item: (-item[0], item[1]))[0][1]


def _matches(path: str, pattern: str) -> bool:
    normalized_path = PurePosixPath(path)
    return normalized_path.match(pattern) or PurePosixPath(path).match(pattern.lstrip("./"))


def _parse_layer(raw: Any, index: int) -> Layer:
    mapping = _mapping(raw, f"architecture.layers[{index}]")
    _keys(mapping, {"name", "paths"}, f"architecture.layers[{index}]")
    return Layer(
        name=_string(mapping.get("name"), f"architecture.layers[{index}].name"),
        paths=_strings(mapping.get("paths"), f"architecture.layers[{index}].paths"),
    )


def _parse_rule(raw: Any, index: int) -> ArchitectureRule:
    location = f"architecture.rules[{index}]"
    mapping = _mapping(raw, location)
    _keys(mapping, {"id", "from", "deny", "severity", "message"}, location)
    severity_text = _string(mapping.get("severity", "error"), f"{location}.severity")
    try:
        severity = Severity(severity_text)
    except ValueError as exc:
        raise ConfigurationError(f"{location}.severity must be info, warning, or error") from exc
    return ArchitectureRule(
        rule_id=_string(mapping.get("id"), f"{location}.id"),
        from_layers=_strings(mapping.get("from"), f"{location}.from"),
        deny_layers=_strings(mapping.get("deny"), f"{location}.deny"),
        severity=severity,
        message=_string(mapping.get("message", "Architecture boundary violated."), f"{location}.message"),
    )


def _mapping(value: Any, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"{location} must be a mapping")
    return value


def _keys(value: Mapping[str, Any], allowed: set[str], location: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ConfigurationError(f"{location} contains unknown keys: {', '.join(unknown)}")


def _string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{location} must be a non-empty string")
    return value.strip()


def _strings(value: Any, location: str, allow_empty: bool = False) -> tuple[str, ...]:
    if isinstance(value, str):
        return (_string(value, location),)
    if not isinstance(value, (list, tuple)) or (not value and not allow_empty):
        requirement = "list of strings" if allow_empty else "non-empty list of strings"
        raise ConfigurationError(f"{location} must be a {requirement}")
    result = tuple(_string(item, f"{location}[{index}]") for index, item in enumerate(value))
    if len(set(result)) != len(result):
        raise ConfigurationError(f"{location} contains duplicate values")
    return result


def _int(value: Any, location: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{location} must be an integer")
    if isinstance(value, int):
        return value
    raise ConfigurationError(f"{location} must be an integer")


def _positive_int(value: Any, location: str) -> int:
    result = _int(value, location)
    if result <= 0:
        raise ConfigurationError(f"{location} must be greater than zero")
    return result
