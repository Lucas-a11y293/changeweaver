import json
from pathlib import Path

from typer.testing import CliRunner

from changeweaver.presentation.cli import app

FIXTURE = Path(__file__).parents[1] / "fixtures" / "sample_app"
runner = CliRunner()


def test_snapshot_command_writes_artifact(tmp_path: Path) -> None:
    output = tmp_path / "current.json"
    result = runner.invoke(app, ["snapshot", "--root", str(FIXTURE), "--output", str(output)])

    assert result.exit_code == 0, result.stdout
    assert output.is_file()
    assert "Nodes: 3" in result.stdout


def test_check_returns_one_for_enforced_regression() -> None:
    result = runner.invoke(app, ["check", "--root", str(FIXTURE)])

    assert result.exit_code == 1
    assert "presentation-cannot-import-data" in result.stdout


def test_json_check_is_machine_readable() -> None:
    result = runner.invoke(app, ["check", "--root", str(FIXTURE), "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["protocol_version"] == 1
    assert payload["command"] == "check"
    assert payload["status"] == "failed"
    assert payload["result"]["findings"][0]["rule_id"] == "presentation-cannot-import-data"


def test_sarif_check_is_machine_readable() -> None:
    result = runner.invoke(app, ["check", "--root", str(FIXTURE), "--sarif"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["version"] == "2.1.0"
    assert payload["runs"][0]["results"][0]["ruleId"] == "presentation-cannot-import-data"
