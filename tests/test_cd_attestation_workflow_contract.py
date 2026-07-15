"""Workflow contract tests for CD attestation verification sequencing.

Ensures that Docker attestation verification steps only run when all upstream
attestation steps (provenance, SBOM generation, SBOM attestation) have succeeded.

Root cause: CD workflow on main failed because SBOM attestation timed out
(Rekor InternalError), but the downstream verification step still ran because
its condition only checked ``steps.build.outcome == 'success'``. The verifier
correctly failed closed (no SBOM predicate found), producing a misleading error.

Fix: gate verification on build + provenance + SBOM generation + SBOM attestation
success outcomes. Keep ``always()`` so the condition is always *evaluated* (GitHub
Actions skips ``if:`` entirely on upstream failure without ``always()``), but the
explicit outcome checks prevent the step from *running* unless all upstream steps
passed.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CD_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "cd.yml"

STAGING_ATTESTATION_STEP_IDS = (
    "attest-staged-provenance",
    "generate-staged-sbom",
    "attest-staged-sbom",
    "attest-staged-caddy-provenance",
    "generate-staged-caddy-sbom",
    "attest-staged-caddy-sbom",
)

PRODUCTION_ATTESTATION_STEP_IDS = (
    "attest-production-provenance",
    "generate-production-sbom",
    "attest-production-sbom",
)


def _load_cd_workflow() -> dict[str, object]:
    """Load and parse the CD workflow YAML."""
    return yaml.safe_load(CD_WORKFLOW_PATH.read_text(encoding="utf-8"))


def _job_steps(workflow: dict[str, object], job_name: str) -> list[dict[str, object]]:
    """Return the steps list for a given job."""
    return workflow["jobs"][job_name]["steps"]  # type: ignore[index]


def _step_by_name(steps: list[dict[str, object]], step_name: str) -> dict[str, object]:
    """Find a step by display name."""
    for step in steps:
        if step.get("name") == step_name:
            return step
    raise AssertionError(f"Step {step_name!r} not found in job steps")


def _step_ids(steps: list[dict[str, object]]) -> set[str]:
    """Return the set of step IDs defined in a job."""
    return {step["id"] for step in steps if "id" in step}


def test_cd_staging_attestation_verify_depends_on_all_attestation_steps() -> None:
    """Staging verify must not run unless build + all attestation steps succeeded."""
    workflow = _load_cd_workflow()
    steps = _job_steps(workflow, "build")

    # All required attestation step IDs must exist
    existing_ids = _step_ids(steps)
    for required_id in STAGING_ATTESTATION_STEP_IDS:
        assert required_id in existing_ids, f"Missing step id {required_id!r} in build job"

    # Verify step condition must reference all attestation outcomes
    verify_step = _step_by_name(steps, "Verify staged backend image attestations")
    verify_if = verify_step["if"]
    assert "always()" in verify_if, "Verify step must use always() to ensure condition evaluation"
    assert "steps.build.outcome == 'success'" in verify_if
    assert "steps.attest-staged-provenance.outcome == 'success'" in verify_if
    assert "steps.generate-staged-sbom.outcome == 'success'" in verify_if
    assert "steps.attest-staged-sbom.outcome == 'success'" in verify_if

    caddy_verify_step = _step_by_name(steps, "Verify staged Caddy image attestations")
    caddy_verify_if = caddy_verify_step["if"]
    assert "always()" in caddy_verify_if
    assert "steps.build-caddy.outcome == 'success'" in caddy_verify_if
    assert "steps.attest-staged-caddy-provenance.outcome == 'success'" in caddy_verify_if
    assert "steps.generate-staged-caddy-sbom.outcome == 'success'" in caddy_verify_if
    assert "steps.attest-staged-caddy-sbom.outcome == 'success'" in caddy_verify_if

    for step in (verify_step, caddy_verify_step):
        env = step.get("env")
        assert isinstance(env, dict)
        assert env["REPO_SLUG"] == "${{ github.repository }}"
        assert env["SOURCE_REF"] == "${{ github.ref }}"
        run = step.get("run")
        assert isinstance(run, str)
        assert '--repo "$REPO_SLUG"' in run
        assert '--signer-workflow "$REPO_SLUG/.github/workflows/cd.yml"' in run
        assert '--source-ref "$SOURCE_REF"' in run
        assert "${{ github.repository }}" not in run
        assert "${{ github.ref }}" not in run


def test_cd_production_attestation_verify_depends_on_all_attestation_steps() -> None:
    """Production verify must not run unless build + all attestation steps succeeded."""
    workflow = _load_cd_workflow()
    steps = _job_steps(workflow, "build-production")

    # All required attestation step IDs must exist
    existing_ids = _step_ids(steps)
    for required_id in PRODUCTION_ATTESTATION_STEP_IDS:
        assert (
            required_id in existing_ids
        ), f"Missing step id {required_id!r} in build-production job"

    # Verify step condition must reference all attestation outcomes
    verify_step = _step_by_name(steps, "Verify production image attestations")
    verify_if = verify_step["if"]
    assert "always()" in verify_if, "Verify step must use always() to ensure condition evaluation"
    assert "steps.build.outcome == 'success'" in verify_if
    assert "steps.attest-production-provenance.outcome == 'success'" in verify_if
    assert "steps.generate-production-sbom.outcome == 'success'" in verify_if
    assert "steps.attest-production-sbom.outcome == 'success'" in verify_if


def test_cd_attestation_steps_remain_fail_closed() -> None:
    """Attestation and verification steps must not use continue-on-error."""
    workflow = _load_cd_workflow()

    attestation_step_names = {
        "Attest staged backend image provenance",
        "Generate staged backend image SBOM",
        "Attest staged backend image SBOM",
        "Verify staged backend image attestations",
        "Attest staged Caddy image provenance",
        "Generate staged Caddy image SBOM",
        "Attest staged Caddy image SBOM",
        "Verify staged Caddy image attestations",
        "Attest production image provenance",
        "Generate production image SBOM",
        "Attest production image SBOM",
        "Verify production image attestations",
    }

    for job_name in ("build", "build-production"):
        for step in _job_steps(workflow, job_name):
            name = step.get("name", "")
            if name in attestation_step_names:
                assert (
                    step.get("continue-on-error") is not True
                ), f"Step {name!r} in job {job_name!r} must not use continue-on-error"
                # Also check for || true in run scripts
                run_script = step.get("run", "")
                if run_script:
                    assert (
                        "|| true" not in run_script
                    ), f"Step {name!r} in job {job_name!r} must not use || true"
