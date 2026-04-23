from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ci import check_docker_image_budget


def _write_budget_policy(tmp_path: Path) -> Path:
    budget_path = tmp_path / "budget.json"
    budget_path.write_text(
        json.dumps(
            {
                "budget_name": "production-backend-image",
                "budget_version": 1,
                "budget_scope": "production-backend-image",
                "max_image_size_bytes": 470000000,
                "max_positive_delta_bytes": 20000000,
                "baseline_reference": {
                    "baseline_file": "docs/telemetry/docker_image_baseline.production.json",
                    "workflow": "build.yml",
                },
                "policy_note": "Hard gate for the production backend image.",
            }
        ),
        encoding="utf-8",
    )
    return budget_path


def _write_telemetry_payload(
    tmp_path: Path,
    *,
    image_size_bytes: int,
    size_delta_bytes: int | None,
    baseline_size_bytes: int | None = 445565354,
) -> Path:
    telemetry_path = tmp_path / "telemetry.json"
    telemetry_path.write_text(
        json.dumps(
            {
                "advisory_only": True,
                "image_ref": "pulseplate:test",
                "image_size_bytes": image_size_bytes,
                "baseline": {
                    "baseline_source": "main-artifact",
                    "baseline_size_bytes": baseline_size_bytes,
                    "size_delta_bytes": size_delta_bytes,
                },
            }
        ),
        encoding="utf-8",
    )
    return telemetry_path


def test_evaluate_budget_passes_within_policy(tmp_path: Path) -> None:
    telemetry_path = _write_telemetry_payload(
        tmp_path,
        image_size_bytes=460000000,
        size_delta_bytes=15000000,
    )
    budget_path = _write_budget_policy(tmp_path)

    result = check_docker_image_budget.evaluate_budget(
        telemetry_path=telemetry_path,
        budget_path=budget_path,
    )

    assert result.passed is True
    assert result.violations == ()


def test_evaluate_budget_fails_on_absolute_cap_breach(tmp_path: Path) -> None:
    telemetry_path = _write_telemetry_payload(
        tmp_path,
        image_size_bytes=470000001,
        size_delta_bytes=1000000,
    )
    budget_path = _write_budget_policy(tmp_path)

    result = check_docker_image_budget.evaluate_budget(
        telemetry_path=telemetry_path,
        budget_path=budget_path,
    )

    assert result.passed is False
    assert "absolute hard-budget cap" in result.violations[0]


def test_evaluate_budget_fails_on_positive_delta_breach(tmp_path: Path) -> None:
    telemetry_path = _write_telemetry_payload(
        tmp_path,
        image_size_bytes=460000000,
        size_delta_bytes=20000001,
    )
    budget_path = _write_budget_policy(tmp_path)

    result = check_docker_image_budget.evaluate_budget(
        telemetry_path=telemetry_path,
        budget_path=budget_path,
    )

    assert result.passed is False
    assert "positive regression budget" in result.violations[0]


def test_evaluate_budget_allows_negative_delta_within_cap(tmp_path: Path) -> None:
    telemetry_path = _write_telemetry_payload(
        tmp_path,
        image_size_bytes=430000000,
        size_delta_bytes=-12000000,
    )
    budget_path = _write_budget_policy(tmp_path)

    result = check_docker_image_budget.evaluate_budget(
        telemetry_path=telemetry_path,
        budget_path=budget_path,
    )

    assert result.passed is True
    assert result.size_delta_bytes == -12000000


def test_evaluate_budget_rejects_negative_baseline_size_bytes(tmp_path: Path) -> None:
    telemetry_path = _write_telemetry_payload(
        tmp_path,
        image_size_bytes=430000000,
        size_delta_bytes=-12000000,
        baseline_size_bytes=-1,
    )
    budget_path = _write_budget_policy(tmp_path)

    with pytest.raises(RuntimeError, match="baseline_size_bytes"):
        check_docker_image_budget.evaluate_budget(
            telemetry_path=telemetry_path,
            budget_path=budget_path,
        )


def test_evaluate_budget_rejects_blank_baseline_source(tmp_path: Path) -> None:
    telemetry_path = _write_telemetry_payload(
        tmp_path,
        image_size_bytes=430000000,
        size_delta_bytes=-12000000,
    )
    payload = json.loads(telemetry_path.read_text(encoding="utf-8"))
    payload["baseline"]["baseline_source"] = ""
    telemetry_path.write_text(json.dumps(payload), encoding="utf-8")
    budget_path = _write_budget_policy(tmp_path)

    with pytest.raises(RuntimeError, match="baseline_source"):
        check_docker_image_budget.evaluate_budget(
            telemetry_path=telemetry_path,
            budget_path=budget_path,
        )


def test_main_writes_artifacts_on_budget_breach(tmp_path: Path) -> None:
    telemetry_path = _write_telemetry_payload(
        tmp_path,
        image_size_bytes=470000001,
        size_delta_bytes=1000000,
    )
    budget_path = _write_budget_policy(tmp_path)
    json_out = tmp_path / "budget-check.json"
    markdown_out = tmp_path / "budget-check.md"

    exit_code = check_docker_image_budget.main(
        [
            "--telemetry-json",
            str(telemetry_path),
            "--budget-json",
            str(budget_path),
            "--json-out",
            str(json_out),
            "--markdown-out",
            str(markdown_out),
        ]
    )

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    markdown = markdown_out.read_text(encoding="utf-8")

    assert exit_code == 1
    assert payload["passed"] is False
    assert payload["violations"]
    assert "absolute hard-budget cap" in payload["violations"][0]
    assert "## Violations" in markdown
    assert "Passed: `false`" in markdown


def test_main_fails_closed_on_malformed_telemetry_and_writes_evidence(tmp_path: Path) -> None:
    telemetry_path = tmp_path / "telemetry.json"
    telemetry_path.write_text(
        json.dumps({"image_ref": "pulseplate:test", "baseline": {}}),
        encoding="utf-8",
    )
    budget_path = _write_budget_policy(tmp_path)
    json_out = tmp_path / "budget-check.json"
    markdown_out = tmp_path / "budget-check.md"

    exit_code = check_docker_image_budget.main(
        [
            "--telemetry-json",
            str(telemetry_path),
            "--budget-json",
            str(budget_path),
            "--json-out",
            str(json_out),
            "--markdown-out",
            str(markdown_out),
        ]
    )

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    markdown = markdown_out.read_text(encoding="utf-8")

    assert exit_code == 1
    assert payload["passed"] is False
    assert "image_size_bytes" in payload["error"]
    assert "Fail-Closed Error" in markdown


def test_main_fails_closed_on_malformed_policy_and_writes_evidence(tmp_path: Path) -> None:
    telemetry_path = _write_telemetry_payload(
        tmp_path,
        image_size_bytes=460000000,
        size_delta_bytes=1000000,
    )
    budget_path = tmp_path / "budget.json"
    budget_path.write_text(json.dumps({"budget_name": ""}), encoding="utf-8")
    json_out = tmp_path / "budget-check.json"
    markdown_out = tmp_path / "budget-check.md"

    exit_code = check_docker_image_budget.main(
        [
            "--telemetry-json",
            str(telemetry_path),
            "--budget-json",
            str(budget_path),
            "--json-out",
            str(json_out),
            "--markdown-out",
            str(markdown_out),
        ]
    )

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    markdown = markdown_out.read_text(encoding="utf-8")

    assert exit_code == 1
    assert payload["passed"] is False
    assert "budget_name" in payload["error"]
    assert "Docker image budget policy" in markdown
