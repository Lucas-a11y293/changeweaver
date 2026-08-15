"""Safe, bounded repository file access."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path, PurePosixPath

from changeweaver.domain.errors import RepositoryError
from changeweaver.domain.models import ArchitectureContract


def safe_root(path: Path) -> Path:
    try:
        root = path.expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise RepositoryError(f"Repository root is not readable: {path}") from exc
    if not root.is_dir():
        raise RepositoryError(f"Repository root is not a directory: {path}")
    return root


def safe_path(root: Path, relative: str) -> Path:
    if Path(relative).is_absolute():
        raise RepositoryError(f"Absolute paths are not allowed: {relative}")
    candidate = (root / relative).resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise RepositoryError(f"Path escapes repository root: {relative}") from exc
    return candidate


def iter_dart_files(root: Path, contract: ArchitectureContract) -> Iterator[tuple[Path, str]]:
    """Yield bounded, repository-relative Dart files without following symlinks."""

    root = safe_root(root)
    seen: set[Path] = set()
    for configured_root in contract.project.roots:
        start = safe_path(root, configured_root)
        if not start.exists():
            continue
        if start.is_symlink() or not start.is_dir():
            continue
        for directory, directories, files in os.walk(start, topdown=True, followlinks=False):
            directory_path = Path(directory)
            directories[:] = [
                name
                for name in directories
                if not (directory_path / name).is_symlink()
                and name not in {".dart_tool", "build", ".git"}
            ]
            for filename in sorted(files):
                path = directory_path / filename
                if path.is_symlink() or path.suffix != ".dart" or path in seen:
                    continue
                relative = path.relative_to(root).as_posix()
                if not _matches_any(relative, contract.project.include):
                    continue
                if _matches_any(relative, contract.project.exclude):
                    continue
                try:
                    size = path.stat().st_size
                except OSError as exc:
                    raise RepositoryError(f"Could not stat {relative}: {exc}") from exc
                if size > contract.limits.max_file_bytes:
                    raise RepositoryError(
                        f"File exceeds analysis.max_file_bytes ({contract.limits.max_file_bytes}): {relative}"
                    )
                seen.add(path)
                yield path, relative


def read_text(path: Path, relative: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise RepositoryError(f"Could not read {relative}: {exc}") from exc


def _matches_any(path: str, patterns: tuple[str, ...]) -> bool:
    normalized = PurePosixPath(path)
    return any(normalized.match(pattern) or normalized.match(pattern.lstrip("./")) for pattern in patterns)
