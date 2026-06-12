"""Regression guards for the Docker workflow build-path consolidation contract."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"


def _load_workflow(path: Path) -> dict[str, object]:
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(workflow, dict)
    return workflow


def _step_names(job: dict[str, object]) -> list[str]:
    steps = job.get("steps")
    assert isinstance(steps, list)
    names: list[str] = []
    for step in steps:
        assert isinstance(step, dict)
        name = step.get("name")
        if isinstance(name, str):
            names.append(name)
    return names


def test_removed_duplicate_docker_pr_workflows() -> None:
    """PR-time production image validation stays in the canonical Docker workflow."""
    assert not (WORKFLOWS_DIR / "docker-image.yml").exists()
    assert not (WORKFLOWS_DIR / "docker-openapi-smoke.yml").exists()


def test_build_workflow_owns_docker_validation_contract() -> None:
    """Build workflow keeps runtime, telemetry, budget, and OpenAPI smoke checks together."""
    workflow = _load_workflow(WORKFLOWS_DIR / "build.yml")
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)

    build_job = jobs["build"]
    assert isinstance(build_job, dict)
    step_names = _step_names(build_job)

    assert "Build Docker image (local, for tests)" in step_names
    assert "Check Docker runtime dependency surface" in step_names
    assert "Collect Docker image telemetry" in step_names
    assert "Enforce Docker image budget" in step_names
    assert "Test Docker image" in step_names

    test_step = next(
        step
        for step in build_job["steps"]
        if isinstance(step, dict) and step.get("name") == "Test Docker image"
    )
    build_step = next(
        step
        for step in build_job["steps"]
        if isinstance(step, dict) and step.get("name") == "Build Docker image (local, for tests)"
    )
    build_step_with = build_step["with"]
    assert isinstance(build_step_with, dict)
    assert build_step_with["target"] == "production"
    assert build_step_with["load"] is True
    assert build_step_with["push"] is False
    assert build_step_with["provenance"] is False

    run_script = test_step["run"]
    assert isinstance(run_script, str)
    assert "openapi.json" in run_script
    assert "/api/v1/bmi" in run_script
    assert (
        'assert "/api/v1/bodyfat" not in paths, '
        '"/api/v1/bodyfat must not leak into canonical OpenAPI"'
    ) in run_script


def test_build_workflow_does_not_expose_github_token_to_pr_baseline_script() -> None:
    """PR builds must not pass workflow tokens to checked-out baseline code."""
    workflow = _load_workflow(WORKFLOWS_DIR / "build.yml")
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    build_job = jobs["build"]
    assert isinstance(build_job, dict)
    steps = build_job["steps"]
    assert isinstance(steps, list)

    fallback_step = next(
        step
        for step in steps
        if isinstance(step, dict)
        and step.get("name") == "Use checked-in Docker image telemetry baseline on pull requests"
    )
    assert fallback_step["if"] == "github.event_name == 'pull_request'"
    fallback_run = fallback_step["run"]
    assert isinstance(fallback_run, str)
    assert "fetch_docker_image_baseline.py" not in fallback_run
    assert "GH_TOKEN" not in fallback_step.get("env", {})
    assert "GITHUB_TOKEN" not in fallback_step.get("env", {})

    resolve_step = next(
        step
        for step in steps
        if isinstance(step, dict) and step.get("name") == "Resolve Docker image telemetry baseline"
    )
    assert resolve_step["if"] == "github.event_name != 'pull_request'"
    resolve_env = resolve_step["env"]
    assert isinstance(resolve_env, dict)
    assert resolve_env["GH_TOKEN"] == "${{ secrets.GITHUB_TOKEN }}"
    assert resolve_env["GITHUB_TOKEN"] == "${{ secrets.GITHUB_TOKEN }}"


def test_production_dockerfile_prunes_package_manager_surface() -> None:
    """Production target removes package-manager packages after runtime-base."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    production_section = dockerfile.split("FROM runtime-base AS production", 1)[1]
    production_section = production_section.split("FROM production AS staging", 1)[0]

    assert "dpkg --purge --force-depends apt gpgv libgnutls30" in production_section
    assert "dpkg-query -W" in production_section
    assert "import ssl" in production_section


def test_docker_entrypoint_keeps_bodyfat_hidden_but_routable() -> None:
    """Docker entrypoint serves app.main while preserving bodyfat compatibility."""
    from app.main import app

    client = TestClient(app)
    openapi_response = client.get("/openapi.json")
    assert openapi_response.headers.get("content-type", "").startswith("application/json")
    openapi_paths = openapi_response.json()["paths"]

    assert "/api/v1/bodyfat" not in openapi_paths
    response = client.post(
        "/api/v1/bodyfat",
        json={
            "gender": "male",
            "age": 30,
            "waist_cm": 80.0,
            "neck_cm": 38.0,
            "height_m": 1.75,
            "weight_kg": 75.0,
        },
    )

    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("application/json")
    assert {"labels", "lang", "median", "methods"} <= response.json().keys()


def test_trivy_workflow_is_main_push_image_security_lane() -> None:
    """Trivy scans production images on main pushes, schedule, and manual dispatch."""
    workflow = _load_workflow(WORKFLOWS_DIR / "trivy.yml")
    on_section = workflow.get("on", workflow.get(True))
    assert isinstance(on_section, dict)
    push = on_section["push"]
    assert isinstance(push, dict)
    assert push["branches"] == ["main"]
    assert "pull_request" not in on_section
    assert "pull_request_target" not in on_section
    assert "schedule" in on_section
    assert "workflow_dispatch" in on_section

    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    build_job = jobs["build"]
    assert isinstance(build_job, dict)
    scan_step = next(
        step
        for step in build_job["steps"]
        if isinstance(step, dict) and step.get("name") == "Run Trivy vulnerability scanner"
    )
    scan_step_with = scan_step["with"]
    assert isinstance(scan_step_with, dict)
    assert scan_step_with["scan-type"] == "image"
    assert scan_step_with["exit-code"] == "1"
    assert "continue-on-error" not in scan_step
    assert "Fail when Trivy SARIF is missing" in _step_names(build_job)


def test_publish_image_scan_fails_closed() -> None:
    """Publish path image scan blocks HIGH/CRITICAL findings and missing SARIF."""
    workflow = _load_workflow(WORKFLOWS_DIR / "build.yml")
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    publish_job = jobs["publish"]
    assert isinstance(publish_job, dict)
    publish_steps = publish_job["steps"]
    scan_step = next(
        step
        for step in publish_steps
        if isinstance(step, dict)
        and step.get("name") == "Run Trivy vulnerability scanner (image scan, fail-closed)"
    )
    scan_step_with = scan_step["with"]
    assert isinstance(scan_step_with, dict)
    assert scan_step_with["scan-type"] == "image"
    assert scan_step_with["exit-code"] == "1"
    assert "continue-on-error" not in scan_step
    assert "Fail when Trivy image SARIF is missing" in _step_names(publish_job)
