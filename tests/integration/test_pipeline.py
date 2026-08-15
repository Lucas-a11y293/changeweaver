from pathlib import Path

from changeweaver.application.services import (
    build_snapshot,
    check_contract,
    diff_snapshots,
    has_error_findings,
    impact_report,
    make_change_plan,
)
from changeweaver.infrastructure.config import load_contract

FIXTURE = Path(__file__).parents[1] / "fixtures" / "sample_app"


def test_fixture_pipeline_detects_boundary_and_impact() -> None:
    contract = load_contract(FIXTURE)
    snapshot = build_snapshot(FIXTURE, contract)

    assert len(snapshot.nodes) == 3
    assert len(snapshot.edges) == 2
    assert snapshot.digest
    assert snapshot == build_snapshot(FIXTURE, contract)

    findings = check_contract(snapshot, contract)
    assert len(findings) == 1
    assert findings[0].rule_id == "presentation-cannot-import-data"
    assert has_error_findings(findings)

    report = impact_report(snapshot, ("lib/domain/user.dart",), 100, 8)
    assert report.affected == (
        "dart:lib/data/user_repository.dart",
        "dart:lib/domain/user.dart",
        "dart:lib/presentation/user_page.dart",
    )
    assert report.score == 66
    assert report.path_samples[-1][0] == "dart:lib/presentation/user_page.dart"


def test_diff_detects_added_edge() -> None:
    contract = load_contract(FIXTURE)
    baseline = build_snapshot(FIXTURE, contract)
    changed_file = FIXTURE / "lib" / "domain" / "new_type.dart"
    changed_file.write_text("class NewType {}\n", encoding="utf-8")
    try:
        current = build_snapshot(FIXTURE, contract)
        changes = diff_snapshots(baseline, current)
        assert [node.path for node in changes.added_nodes] == ["lib/domain/new_type.dart"]
        assert changes.changed
        plan = make_change_plan(changes, None, ())
        assert plan.mutates_files is False
        assert plan.steps[0].action == "Review structural diff"
    finally:
        changed_file.unlink()
