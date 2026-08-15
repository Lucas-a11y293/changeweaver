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


def test_verify_writes_deterministic_receipt(tmp_path: Path) -> None:
    output = tmp_path / "receipt.json"
    result = runner.invoke(
        app,
        [
            "verify",
            "--root",
            str(FIXTURE),
            "--target",
            "lib/domain/user.dart",
            "--output",
            str(output),
            "--json",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    receipt = payload["result"]
    assert payload["command"] == "verify"
    assert payload["status"] == "failed"
    assert receipt["status"] == "failed"
    assert receipt["checks"] == ["snapshot", "architecture-contract", "reverse-impact"]
    assert receipt["error_findings"] == 1
    assert len(receipt["digest"]) == 64
    persisted = json.loads(output.read_text(encoding="utf-8"))
    assert persisted == receipt


def test_verify_without_target_reports_no_impact() -> None:
    result = runner.invoke(app, ["verify", "--root", str(FIXTURE), "--json"])

    assert result.exit_code == 1
    receipt = json.loads(result.stdout)["result"]
    assert receipt["impact_score"] is None
    assert "reverse-impact" not in receipt["checks"]


def test_verify_returns_zero_for_clean_project(tmp_path: Path) -> None:
    (tmp_path / "lib" / "domain").mkdir(parents=True)
    (tmp_path / "lib" / "presentation").mkdir(parents=True)
    (tmp_path / "lib" / "domain" / "user.dart").write_text(
        "class User {}\n", encoding="utf-8"
    )
    (tmp_path / "lib" / "presentation" / "page.dart").write_text(
        "import '../domain/user.dart';\nclass Page { User user = User(); }\n", encoding="utf-8"
    )
    (tmp_path / "changeweaver.yaml").write_text(
        """version: 1
project:
  name: clean_project
  roots: [lib]
  include: ['**/*.dart']
  exclude: []
architecture:
  layers:
    - name: presentation
      paths: ['**/presentation/**']
    - name: domain
      paths: ['**/domain/**']
  rules:
    - id: presentation-cannot-import-data
      from: [presentation]
      deny: [data]
      severity: error
      message: Presentation must not import data.
""",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["verify", "--root", str(tmp_path), "--json"])

    assert result.exit_code == 0, result.stdout
    receipt = json.loads(result.stdout)["result"]
    assert receipt["status"] == "passed"
    assert receipt["error_findings"] == 0
    assert receipt["findings_count"] == 0
