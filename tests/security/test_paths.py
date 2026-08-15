from pathlib import Path

import pytest

from changeweaver.domain.errors import RepositoryError
from changeweaver.infrastructure.filesystem import safe_path, safe_root


def test_safe_path_rejects_traversal(tmp_path: Path) -> None:
    root = safe_root(tmp_path)
    with pytest.raises(RepositoryError, match="escapes repository root"):
        safe_path(root, "../outside.txt")


def test_safe_path_rejects_absolute_path(tmp_path: Path) -> None:
    root = safe_root(tmp_path)
    with pytest.raises(RepositoryError, match="Absolute paths"):
        safe_path(root, "/etc/passwd")
