"""ChangeWeaver public package."""

__version__ = "0.1.0"

from changeweaver.application.services import (
    build_snapshot,
    check_contract,
    diff_snapshots,
    impact_report,
)
from changeweaver.domain.models import (
    ArchitectureContract,
    ChangeSet,
    Finding,
    ImpactReport,
    Snapshot,
)

__all__ = [
    "ArchitectureContract",
    "ChangeSet",
    "Finding",
    "ImpactReport",
    "Snapshot",
    "build_snapshot",
    "check_contract",
    "diff_snapshots",
    "impact_report",
    "__version__",
]
