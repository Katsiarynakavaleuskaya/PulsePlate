"""Contract tests for the protected iOS App Store release-ops workflow."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ios-appstore-assets.yml"
FASTFILE_PATH = REPO_ROOT / "ios" / "fastlane" / "Fastfile"
EXPECTED_ALLOWED_REFS_REGEX = "^refs/heads/main$|^refs/heads/release/.+$|^refs/tags/release-.+$"


def _load_workflow() -> dict[str, object]:
    """Load GitHub Actions YAML without coercing `on` into a boolean key."""

    return yaml.load(WORKFLOW_PATH.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def _job(job_name: str) -> dict[str, object]:
    workflow = _load_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    job = jobs[job_name]
    assert isinstance(job, dict)
    return job


def _step_by_name(job_name: str, step_name: str) -> dict[str, object]:
    steps = _job(job_name)["steps"]
    assert isinstance(steps, list)
    for step in steps:
        assert isinstance(step, dict)
        if step.get("name") == step_name:
            return step
    raise AssertionError(f"Missing step {step_name!r} in job {job_name!r}")


def _workflow_text() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def _fastfile_text() -> str:
    return FASTFILE_PATH.read_text(encoding="utf-8")


def test_workflow_dispatch_inputs_match_release_ops_contract() -> None:
    workflow = _load_workflow()
    workflow_on = workflow["on"]
    assert isinstance(workflow_on, dict)
    workflow_dispatch = workflow_on["workflow_dispatch"]
    assert isinstance(workflow_dispatch, dict)
    inputs = workflow_dispatch["inputs"]
    assert isinstance(inputs, dict)

    assert set(inputs) == {"upload_to_asc", "upload_app_privacy"}


def test_protected_environment_names_are_exact() -> None:
    assert _job("upload-assets")["environment"] == "appstore-assets"
    assert _job("upload-app-privacy")["environment"] == "appstore-privacy"


def test_asc_upload_step_uses_exact_secret_mapping() -> None:
    upload_step = _step_by_name("upload-assets", "Upload metadata and screenshots")
    env = upload_step["env"]
    assert isinstance(env, dict)
    assert env == {
        "APP_STORE_CONNECT_API_KEY_ID": "${{ secrets.ASC_KEY_ID }}",
        "APP_STORE_CONNECT_API_ISSUER_ID": "${{ secrets.ASC_ISSUER_ID }}",
        "APP_STORE_CONNECT_API_KEY": "${{ secrets.ASC_KEY_P8_BASE64 }}",
        "APP_STORE_BUNDLE_IDENTIFIER": "${{ secrets.APP_STORE_BUNDLE_IDENTIFIER }}",
    }


def test_app_privacy_step_uses_exact_secret_mapping() -> None:
    upload_step = _step_by_name("upload-app-privacy", "Upload App Privacy")
    env = upload_step["env"]
    assert isinstance(env, dict)
    assert env == {
        "FASTLANE_USER": "${{ secrets.FASTLANE_USER }}",
        "FASTLANE_SESSION": "${{ secrets.FASTLANE_SESSION }}",
        "FASTLANE_TEAM_ID": "${{ secrets.FASTLANE_TEAM_ID }}",
        "FASTLANE_TEAM_NAME": "${{ secrets.FASTLANE_TEAM_NAME }}",
        "APP_STORE_BUNDLE_IDENTIFIER": "${{ secrets.APP_STORE_BUNDLE_IDENTIFIER }}",
    }


def test_workflow_preflight_steps_require_exact_protected_secrets() -> None:
    asc_preflight = _step_by_name("upload-assets", "Preflight protected App Store upload secrets")
    asc_env = asc_preflight["env"]
    assert isinstance(asc_env, dict)
    assert asc_env == {
        "ASC_KEY_ID": "${{ secrets.ASC_KEY_ID }}",
        "ASC_ISSUER_ID": "${{ secrets.ASC_ISSUER_ID }}",
        "ASC_KEY_P8_BASE64": "${{ secrets.ASC_KEY_P8_BASE64 }}",
        "APP_STORE_BUNDLE_IDENTIFIER": "${{ secrets.APP_STORE_BUNDLE_IDENTIFIER }}",
    }

    privacy_preflight = _step_by_name(
        "upload-app-privacy", "Preflight protected App Privacy secrets"
    )
    privacy_env = privacy_preflight["env"]
    assert isinstance(privacy_env, dict)
    assert privacy_env == {
        "FASTLANE_USER": "${{ secrets.FASTLANE_USER }}",
        "FASTLANE_SESSION": "${{ secrets.FASTLANE_SESSION }}",
        "FASTLANE_TEAM_ID": "${{ secrets.FASTLANE_TEAM_ID }}",
        "FASTLANE_TEAM_NAME": "${{ secrets.FASTLANE_TEAM_NAME }}",
        "APP_STORE_BUNDLE_IDENTIFIER": "${{ secrets.APP_STORE_BUNDLE_IDENTIFIER }}",
    }


def test_privileged_upload_jobs_guard_allowed_refs() -> None:
    for job_name in ("upload-assets", "upload-app-privacy"):
        guard_step = _step_by_name(job_name, "Guard privileged upload ref")
        env = guard_step["env"]
        assert isinstance(env, dict)
        assert env == {"ALLOWED_UPLOAD_REFS_REGEX": EXPECTED_ALLOWED_REFS_REGEX}
        run_script = guard_step["run"]
        assert isinstance(run_script, str)
        assert "Privileged App Store uploads may run only from main or release refs." in run_script


def test_pull_request_path_cannot_execute_privileged_uploads() -> None:
    validate_assets_if = _job("validate-assets")["if"]
    upload_assets_if = _job("upload-assets")["if"]
    upload_app_privacy_if = _job("upload-app-privacy")["if"]

    assert validate_assets_if == (
        "github.event_name == 'pull_request' || (github.event_name == 'workflow_dispatch' && inputs.upload_to_asc)"
    )
    assert upload_assets_if == "github.event_name == 'workflow_dispatch' && inputs.upload_to_asc"
    assert upload_app_privacy_if == (
        "github.event_name == 'workflow_dispatch' && inputs.upload_app_privacy"
    )


def test_fastlane_upload_lanes_stay_fail_closed() -> None:
    fastfile_text = _fastfile_text()

    assert (
        'IOS_APPSTORE_ASSETS_RUNBOOK = "docs/runbooks/IOS_APPSTORE_ASSETS_ROLLOUT.md".freeze'
        in fastfile_text
    )
    assert "def require_env_vars!(names, context: nil)" in fastfile_text
    assert 'context: "App Store Connect API key preflight"' in fastfile_text
    assert 'context: "App Store metadata/screenshots upload"' in fastfile_text
    assert 'context: "App Privacy protected upload"' in fastfile_text
    assert (
        'require_existing_path!(fastlane_path("metadata"), "App Store metadata directory")'
        in fastfile_text
    )
    assert (
        'require_non_empty_directory!(fastlane_path("screenshots"), "App Store screenshots directory")'
        in fastfile_text
    )
    assert (
        'require_existing_path!(fastlane_path("app_privacy_details.json"), "App Privacy JSON package")'
        in fastfile_text
    )
    assert "See #{IOS_APPSTORE_ASSETS_RUNBOOK}" in fastfile_text


def test_runbook_reference_is_present_in_workflow_preflight_errors() -> None:
    workflow_text = _workflow_text()
    assert "docs/runbooks/IOS_APPSTORE_ASSETS_ROLLOUT.md" in workflow_text
    assert "Missing protected App Store upload secret(s):" in workflow_text
    assert "Missing protected App Privacy secret(s):" in workflow_text
