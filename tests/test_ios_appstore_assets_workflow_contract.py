"""Contract tests for the protected iOS App Store release-ops workflow."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest
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


def _resolve_snapshot_devices_with_inventory(
    tmp_path: Path, devices: dict[str, list[dict[str, object]]]
) -> subprocess.CompletedProcess[str]:
    """Execute the Fastfile's actual device resolver against a simctl JSON fixture."""

    inventory_path = tmp_path / "simctl-devices.json"
    inventory_path.write_text(json.dumps({"devices": devices}), encoding="utf-8")
    ruby = r"""
require "json"
module UI
  def self.message(_message); end
  def self.user_error!(message); abort(message); end
end
def sh(command)
  raise "unexpected simctl command" unless command == "xcrun simctl list devices available -j"
  File.read(ARGV.fetch(1))
end
source = File.read(ARGV.fetch(0))
start_at = source.index("IOS_SNAPSHOT_RUNTIME_ID =") or abort("missing runtime and device candidates")
end_at = source.index("def snapshot_bundle_identifier", start_at) or abort("missing resolver end")
eval(source[start_at...end_at], TOPLEVEL_BINDING)
puts JSON.generate(resolved_snapshot_devices)
"""
    return subprocess.run(
        ["ruby", "-e", ruby, str(FASTFILE_PATH), str(inventory_path)],
        capture_output=True,
        text=True,
        check=False,
    )


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


def test_screenshot_jobs_require_exact_xcode27_sdk_and_runtime() -> None:
    for job_name in ("validate-assets", "upload-assets"):
        job = _job(job_name)
        assert job["runs-on"] == "xcode-27"
        select = _step_by_name(job_name, "Select Xcode")
        run = select["run"]
        assert isinstance(run, str)
        assert "/Applications/Xcode_27.0.0.app/Contents/Developer" in run
        assert 'if [ "$XCODE_VERSION" != "27.0" ]; then' in run
        assert 'if [ "$sdk_version" != "27.0" ]; then' in run
        assert "Apple Swift version 6.4" in run
        assert "com.apple.CoreSimulator.SimRuntime.iOS-27-0" in run
        assert "Runner image:" in run
        assert "Xcode_26" not in run

    fastfile = _fastfile_text()
    phone_candidates = fastfile.split("IPHONE_DEVICE_CANDIDATES = [", 1)[1].split("].freeze", 1)[0]
    assert re.findall(r'"(iPhone [^"]+)"', phone_candidates) == [
        "iPhone 18 Pro Max",
        "iPhone 17 Pro Max",
        "iPhone 16 Pro Max",
    ]
    assert 'ios_version: "27.0"' in fastfile


def test_snapshot_device_resolver_ignores_newer_name_on_old_runtime(tmp_path: Path) -> None:
    result = _resolve_snapshot_devices_with_inventory(
        tmp_path,
        {
            "com.apple.CoreSimulator.SimRuntime.iOS-26-5": [
                {"name": "iPhone 18 Pro Max", "udid": "older-only", "isAvailable": True},
            ],
            "com.apple.CoreSimulator.SimRuntime.iOS-27-0": [
                {"name": "iPhone 17 Pro Max", "udid": "current-phone", "isAvailable": True},
                {"name": "iPad Pro 13-inch (M5)", "udid": "current-ipad", "isAvailable": True},
            ],
        },
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == ["iPhone 17 Pro Max", "iPad Pro 13-inch (M5)"]


def test_snapshot_device_resolver_fails_without_ios27_candidate(tmp_path: Path) -> None:
    result = _resolve_snapshot_devices_with_inventory(
        tmp_path,
        {
            "com.apple.CoreSimulator.SimRuntime.iOS-26-5": [
                {"name": "iPhone 18 Pro Max", "udid": "older-only", "isAvailable": True},
            ],
            "com.apple.CoreSimulator.SimRuntime.iOS-27-0": [
                {"name": "iPhone 18 Pro Max", "udid": "unavailable", "isAvailable": False},
                {"name": "iPad Pro 13-inch (M5)", "udid": "current-ipad", "isAvailable": True},
            ],
        },
    )
    assert result.returncode != 0
    assert "No available iOS 27.0 simulator found for iPhone" in result.stderr


def test_snapshot_device_resolver_prefers_max_over_smaller_pro_on_ios27(tmp_path: Path) -> None:
    result = _resolve_snapshot_devices_with_inventory(
        tmp_path,
        {
            "com.apple.CoreSimulator.SimRuntime.iOS-27-0": [
                {"name": "iPhone 16 Pro", "udid": "small-pro", "isAvailable": True},
                {"name": "iPhone 17 Pro Max", "udid": "eligible-max", "isAvailable": True},
                {"name": "iPad Pro 13-inch (M5)", "udid": "current-ipad", "isAvailable": True},
            ],
        },
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == ["iPhone 17 Pro Max", "iPad Pro 13-inch (M5)"]


def test_fastlane_upload_lanes_stay_fail_closed() -> None:
    fastfile_text = _fastfile_text()

    assert (
        'IOS_APPSTORE_ASSETS_RUNBOOK = "docs/runbooks/IOS_APPSTORE_ASSETS_ROLLOUT.md".freeze'
        in fastfile_text
    )
    assert "def require_env_vars!(names, context: nil)" in fastfile_text
    assert "def require_existing_directory!(path, description)" in fastfile_text
    assert "def require_existing_file!(path, description)" in fastfile_text
    assert 'context: "App Store Connect API key preflight"' in fastfile_text
    assert 'context: "App Store metadata/screenshots upload"' in fastfile_text
    assert 'context: "App Privacy protected upload"' in fastfile_text
    assert (
        "FASTLANE_USER\n"
        "        FASTLANE_SESSION\n"
        "        FASTLANE_TEAM_ID\n"
        "        FASTLANE_TEAM_NAME\n"
        "        APP_STORE_BUNDLE_IDENTIFIER"
    ) in fastfile_text
    assert (
        'require_existing_directory!(fastlane_path("metadata"), "App Store metadata directory")'
        in fastfile_text
    )
    assert (
        'require_non_empty_directory!(fastlane_path("screenshots"), "App Store screenshots directory")'
        in fastfile_text
    )
    assert (
        'require_existing_file!(fastlane_path("app_privacy_details.json"), "App Privacy JSON package")'
        in fastfile_text
    )
    assert "See #{IOS_APPSTORE_ASSETS_RUNBOOK}" in fastfile_text


def test_runbook_reference_is_present_in_workflow_preflight_errors() -> None:
    workflow_text = _workflow_text()
    assert "docs/runbooks/IOS_APPSTORE_ASSETS_ROLLOUT.md" in workflow_text
    assert "Missing protected App Store upload secret(s):" in workflow_text
    assert "Missing protected App Privacy secret(s):" in workflow_text


@pytest.mark.parametrize("job_name", ("validate-assets", "upload-assets", "upload-app-privacy"))
def test_fastlane_bundle_and_configuration_stay_outside_snapshot_search_tree(job_name: str) -> None:
    job = _job(job_name)
    bundle_root = "${RUNNER_TEMP}/pulseplate-ios-bundle-" + job_name
    assert job["env"] == {"BUNDLE_GEMFILE": "${{ github.workspace }}/ios/Gemfile"}
    steps = job["steps"]
    assert isinstance(steps, list)
    prepare = _step_by_name(job_name, "Prepare external Bundler root")
    assert prepare["run"] == (
        "set -euo pipefail\numask 077\n"
        f'bundle_root="{bundle_root}"\n'
        'mkdir -p "$bundle_root"\n'
        "printf 'PULSEPLATE_BUNDLE_ROOT=%s\\nBUNDLE_APP_CONFIG=%s/.bundle\\n' \\\n"
        '  "$bundle_root" "$bundle_root" >> "$GITHUB_ENV"\n'
    )
    setup_steps = [
        step
        for step in steps
        if isinstance(step, dict) and str(step.get("uses", "")).startswith("ruby/setup-ruby@")
    ]
    assert len(setup_steps) == 1
    setup = setup_steps[0]
    assert setup["uses"] == "ruby/setup-ruby@d45b1a4e94b71acab930e56e79c6aa188764e7f9"
    assert setup["with"] == {
        "ruby-version": "3.4.10",
        "bundler-cache": "true",
        "working-directory": "${{ env.PULSEPLATE_BUNDLE_ROOT }}",
    }
    assert steps.index(prepare) < steps.index(setup)
    assert "env" not in prepare and "env" not in setup
    bundle_steps = [
        step
        for step in steps
        if isinstance(step, dict) and str(step.get("run", "")).startswith("bundle ")
    ]
    assert bundle_steps
    assert bundle_steps[0] == {
        "name": "Install gems",
        "working-directory": "ios",
        "run": "bundle install",
    }
    for step in steps:
        assert isinstance(step, dict)
        overrides = step.get("env", {})
        assert isinstance(overrides, dict)
        assert not set(overrides).intersection(
            {"BUNDLE_GEMFILE", "PULSEPLATE_BUNDLE_ROOT", "BUNDLE_APP_CONFIG"}
        )
    for step in bundle_steps:
        assert steps.index(setup) < steps.index(step)
        assert step["working-directory"] == "ios"
    # The pinned action derives vendor/bundle and its cache key from its own cwd.
    # Moving that cwd excludes the old ios/vendor/bundle cache without disabling caching.
    assert "github.workspace" not in bundle_root
    assert "BUNDLE_PATH" not in _workflow_text()
    assert "bundle-path:" not in _workflow_text()
    assert "skip_helper_version_check" not in _workflow_text()
    assert "snapshot update" not in _workflow_text()


def test_fastlane_bundle_roots_are_exactly_one_per_literal_job() -> None:
    jobs = _load_workflow()["jobs"]
    assert isinstance(jobs, dict)
    assert set(jobs) == {"validate-assets", "upload-assets", "upload-app-privacy"}
    initializers = [
        _step_by_name(job_name, "Prepare external Bundler root")["run"] for job_name in jobs
    ]
    assert len(initializers) == len(set(initializers)) == 3
    for job_name in jobs:
        steps = _job(job_name)["steps"]
        assert isinstance(steps, list)
        writers = [
            step
            for step in steps
            if isinstance(step, dict) and "PULSEPLATE_BUNDLE_ROOT=" in str(step.get("run", ""))
        ]
        assert writers == [_step_by_name(job_name, "Prepare external Bundler root")]
