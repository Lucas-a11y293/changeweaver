import json
from pathlib import Path

from changeweaver.application.services import build_snapshot, check_contract
from changeweaver.infrastructure.config import load_contract
from changeweaver.infrastructure.serialization import read_snapshot, write_snapshot
from changeweaver.presentation.renderers import render_html, render_mermaid, render_sarif

FIXTURE = Path(__file__).parents[1] / "fixtures" / "sample_app"


def test_snapshot_round_trip_preserves_digest(tmp_path: Path) -> None:
    snapshot = build_snapshot(FIXTURE, load_contract(FIXTURE))
    path = tmp_path / "snapshot.json"
    write_snapshot(path, snapshot)

    loaded = read_snapshot(path)

    assert loaded == snapshot
    assert json.loads(path.read_text(encoding="utf-8"))["digest"] == snapshot.digest


def test_renderers_escape_and_preserve_machine_format() -> None:
    contract = load_contract(FIXTURE)
    snapshot = build_snapshot(FIXTURE, contract)
    findings = check_contract(snapshot, contract)

    sarif = json.loads(render_sarif(findings))
    assert sarif["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "lib/presentation/user_page.dart"
    assert "flowchart LR" in render_mermaid(snapshot)
    assert "<title>&lt;title&gt;</title>" in render_html("<title>", "plain")
