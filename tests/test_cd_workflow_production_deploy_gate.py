"""Regression tests for production deploy gating in the CD workflow."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts import verify_premium_alias_telemetry as verifier

REPO_ROOT = Path(__file__).resolve().parents[1]
CD_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "cd.yml"
PROD_DEPLOY_MODE_ENV_FETCH = (
    'get_actions_variable "environments/production/variables" "PROD_DEPLOY_MODE"'
)
WEB_IOS_RELEASE_READY_ENV_FETCH = (
    'get_actions_variable "environments/production/variables" "WEB_IOS_RELEASE_READY"'
)


def test_build_workflow_keeps_only_ordinary_fail_closed_topology() -> None:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/build.yml").read_text())
    jobs = workflow["jobs"]
    assert set(jobs) == {
        "build",
        "security-scan",
        "publish",
        "prometheus-source-qualification",
        "prometheus-ghcr-package-qualification",
        "backend-arm-sdk-qualification",
        "prometheus-oras-qualification",
        "prometheus-source-build-pair",
        "prometheus-publish",
    }
    inputs = workflow.get("on", workflow.get(True))["workflow_dispatch"]["inputs"]
    assert inputs == {
        "mode": {
            "description": "Explicit manual execution mode; disabled never publishes",
            "type": "choice",
            "required": True,
            "default": "disabled",
            "options": [
                "disabled",
                "normal",
                "prometheus-source-qualify",
                "backend-sdk-qualify",
                "prometheus-oras-qualify",
                "prometheus-source-pair",
            ],
        },
        "prometheus_module_action": {
            "description": "Explicit Prometheus metadata module action; unchanged retains original locks",
            "type": "choice",
            "required": True,
            "default": "unchanged",
            "options": ["unchanged", "xnet060-replay"],
        },
        "tool_prefetch_predecessor": {
            "description": "Exact failed precompile run:artifact evidence selector; no dispatch authorization",
            "type": "string",
            "required": False,
            "default": "",
        },
    }
    assert workflow["concurrency"] == {
        "group": "ghcr-build-push-${{ github.sha }}",
        "cancel-in-progress": False,
    }
    assert jobs["security-scan"]["needs"] == "build"
    assert jobs["publish"]["needs"] == ["build", "security-scan"]
    assert jobs["build"]["permissions"] == {"actions": "read", "contents": "read"}
    for retired in (
        "prometheus-candidate",
        "candidate_head_sha",
        "candidate_spec_digest",
        "prometheus_derivative_candidate.py",
        "PROMETHEUS_CANDIDATE_",
    ):
        assert retired not in str(workflow)
    for retired_path in (
        "scripts/ci/prometheus_derivative_candidate.py",
        "scripts/ci/_prometheus_derivative_transport.py",
    ):
        assert not (REPO_ROOT / retired_path).exists()
    assert (
        (REPO_ROOT / "deploy/prometheus/Containerfile")
        .read_text()
        .startswith("# Finite payload declaration;")
    )
    # These two manual, same-repository qualification sidecars cannot enter
    # the retained ordinary build/security/publish dependency chain.
    qualification_condition = (
        "github.event_name == 'workflow_dispatch' && "
        "inputs.mode == 'prometheus-source-qualify' && "
        "github.repository == 'Katsiarynakavaleuskaya/PulsePlate'"
    )
    for name, permissions in (
        ("prometheus-source-qualification", {"contents": "read"}),
        ("prometheus-ghcr-package-qualification", {"contents": "read", "packages": "read"}),
    ):
        job = jobs[name]
        assert " ".join(job["if"].split()) == qualification_condition
        assert job["permissions"] == permissions
        assert "needs" not in job
        assert "environment" not in job
        assert "continue-on-error" not in job
        steps = job["steps"]
        assert all("continue-on-error" not in step for step in steps)
        checkout = [
            step for step in steps if str(step.get("uses", "")).startswith("actions/checkout@")
        ]
        assert len(checkout) == 1
        assert checkout[0]["with"] == {"persist-credentials": False, "ref": "${{ github.sha }}"}
        assert "if [[ \"$GITHUB_RUN_ATTEMPT\" != '1' ]]; then" in steps[0]["run"]
        assert "scripts.ci.prometheus_source_image" in str(steps)
        for forbidden in (
            "docker/login-action",
            "docker/build-push-action",
            "packages: write",
            "--push",
        ):
            assert forbidden not in str(job)
    source_steps = jobs["prometheus-source-qualification"]["steps"]
    assert "secrets." not in str(source_steps)
    package_steps = jobs["prometheus-ghcr-package-qualification"]["steps"]
    package = next(step for step in package_steps if step.get("id") == "package")
    assert package["env"] == {"GH_TOKEN": "${{ secrets.GITHUB_TOKEN }}"}
    assert "--qualify-existing-ghcr-package" in package["run"]
    upload = package_steps[-1]
    assert upload["if"] == "${{ success() && steps.package.outputs.qualified == 'true' }}"
    assert upload["with"]["path"] == (
        "${{ runner.temp }}/ghcr-public-${{ github.run_id }}-${{ github.run_attempt }}/qualification.json"
    )
    listener = (REPO_ROOT / ".github/workflows/cd-test.yml").read_text()
    assert "github.event.workflow_run.event == 'push'" in listener


@pytest.mark.parametrize(
    "event,mode,ordinary,publish",
    (
        ("push", None, True, True),
        ("pull_request", None, True, False),
        ("pull_request", "normal", True, False),
        ("workflow_dispatch", None, False, False),
        ("workflow_dispatch", "", False, False),
        ("workflow_dispatch", "disabled", False, False),
        ("workflow_dispatch", "prometheus-candidate", False, False),
        ("workflow_dispatch", "invented", False, False),
        ("workflow_dispatch", "normal-extra", False, False),
        ("workflow_dispatch", "normal", True, True),
        ("workflow_dispatch", "NORMAL", True, True),
        ("workflow_dispatch", "Normal", True, True),
        ("workflow_dispatch", "nOrMaL", True, True),
    ),
)
def test_build_manual_mode_cannot_fall_through_to_ordinary_publication(
    event: str, mode: str | None, ordinary: bool, publish: bool
) -> None:
    jobs = yaml.safe_load((REPO_ROOT / ".github/workflows/build.yml").read_text())["jobs"]
    ordinary_expression = "github.event_name != 'workflow_dispatch' || inputs.mode == 'normal'"
    assert " ".join(jobs["build"]["if"].split()) == ordinary_expression
    assert " ".join(jobs["security-scan"]["if"].split()) == ordinary_expression
    assert " ".join(jobs["publish"]["if"].split()) == (
        "github.event_name != 'pull_request' && (" + ordinary_expression + ")"
    )
    # Bounded choice-string projection, not a GitHub Actions expression interpreter.
    # GitHub compares strings case-insensitively; missing inputs project to "".
    ordinary_result = event != "workflow_dispatch" or (mode or "").casefold() == "normal"
    assert ordinary_result is ordinary
    assert (event != "pull_request" and ordinary_result) is publish


PRODUCTION_ENV_READY_ENV_FETCH = (
    'get_actions_variable "environments/production/variables" "PRODUCTION_ENV_READY"'
)


def test_production_deploy_jobs_use_bridge_job_outputs() -> None:
    """Guard against build-only production tags caused by env var visibility."""

    workflow_text = CD_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "production-deploy-config:" in workflow_text
    assert "deploy-production:" in workflow_text
    bridge_section = workflow_text.split("production-deploy-config:", maxsplit=1)[1].split(
        "deploy-production:", maxsplit=1
    )[0]

    assert "Resolve production deploy configuration" in workflow_text
    assert PROD_DEPLOY_MODE_ENV_FETCH in workflow_text
    assert WEB_IOS_RELEASE_READY_ENV_FETCH in workflow_text
    assert PRODUCTION_ENV_READY_ENV_FETCH in workflow_text
    assert "GH_TOKEN: ${{ github.token }}" in workflow_text
    assert "PRODUCTION_ENV_READ_TOKEN: ${{ secrets.PRODUCTION_ENV_READ_TOKEN }}" in workflow_text
    assert 'DEFAULT_GH_TOKEN="${GH_TOKEN}"' in workflow_text
    assert 'FALLBACK_GH_TOKEN="${PRODUCTION_ENV_READ_TOKEN:-}"' in workflow_text
    assert (
        'if response="$(gh_api_value "$DEFAULT_GH_TOKEN" "$scope_path" "$variable_name" 2>&1)"; then'
        in workflow_text
    )
    assert "Resource not accessible by integration" in workflow_text
    assert (
        'if response="$(gh_api_value "$FALLBACK_GH_TOKEN" "$scope_path" "$variable_name" 2>&1)"; then'
        in workflow_text
    )
    assert "gh auth status >/dev/null" in workflow_text
    assert "needs.production-deploy-config.outputs.should_deploy == 'true'" in workflow_text
    assert "needs.production-deploy-config.outputs.deploy_mode == 'ssh'" in workflow_text
    assert "needs.production-deploy-config.outputs.deploy_mode == 'self-hosted'" in workflow_text
    assert 'env_ready="${env_ready:-false}"' in workflow_text
    assert 'if [ "$env_ready" = "true" ]; then' in workflow_text
    assert (
        "Production deploy remains build-only: PRODUCTION_ENV_READY=true is required after host bootstrap confirms"
        in workflow_text
    )
    assert 'echo "env_ready=$env_ready"' in workflow_text
    assert "environment:" not in bridge_section
    assert "vars.PROD_DEPLOY_MODE == 'ssh'" not in workflow_text
    assert "vars.PROD_DEPLOY_MODE == 'self-hosted'" not in workflow_text


def test_production_deploy_syncs_shell_bundle_for_caddy_rebuild() -> None:
    """Guard against shipping only the app image while leaving the web shell stale."""

    workflow_text = CD_WORKFLOW_PATH.read_text(encoding="utf-8")
    tar_bundle_pattern = re.compile(
        r'tar -czf "\$archive_path" \\\n'
        r"\s+frontend \\\n"
        r"\s+deploy/Caddyfile\.production \\\n"
        r"\s+deploy/docker-compose\.production\.yaml \\\n"
        r"\s+deploy/docker-compose\.production\.selfhosted\.yaml \\\n"
        r"\s+deploy/prometheus/prometheus\.yml \\\n"
        r"\s+deploy/prometheus/image-manifest\.json \\\n"
        r"\s+scripts/ci/prometheus_source_image\.py \\\n"
        r"\s+scripts/ci/fetch_docker_source_artifacts\.py \\\n"
        r"\s+scripts/diagnose_web\.sh \\\n"
        r"\s+scripts/redeploy_caddy\.sh \\\n"
        r"\s+scripts/ops/postgres_backup\.sh \\\n"
        r"\s+deploy/postgres-pgvector/image-manifest\.json",
        re.MULTILINE,
    )

    assert "Stage production shell bundle for SSH deploy" in workflow_text
    assert tar_bundle_pattern.search(workflow_text)
    assert (
        'bundle_name="pulseplate-shell-bundle-${{ github.run_id }}-${{ github.run_attempt }}"'
        in workflow_text
    )
    assert "SSH_HOST_PRODUCTION_FINGERPRINT" in workflow_text
    assert 'ssh-keyscan -H -t ed25519 "$SSH_HOST_PRODUCTION" > "$scan_path"' in workflow_text
    assert "SSH host fingerprint mismatch" in workflow_text
    assert 'ssh-keygen -lf "$scan_path"' in workflow_text
    assert 'tar -xzf "/tmp/${bundle_name}.tgz"' not in workflow_text
    assert 'export SHELL_BUNDLE_ARCHIVE="/tmp/${bundle_name}.tgz"' in workflow_text
    assert 'export SHELL_BUNDLE_DIR="${GITHUB_WORKSPACE}"' in workflow_text
    assert "DEPLOY_DIR is required for production shell sync" not in workflow_text
    assert "StrictHostKeyChecking=no" not in workflow_text
    assert "group: cd-deploy-production" in workflow_text


def test_production_deploy_jobs_delegate_registry_login_to_deploy_script() -> None:
    """Keep GHCR auth inside deploy_production.sh so SSH shells stay PATH-agnostic."""

    workflow_text = CD_WORKFLOW_PATH.read_text(encoding="utf-8")
    ssh_section = workflow_text.split("deploy-production:", maxsplit=1)[1].split(
        "deploy-production-self-hosted:", maxsplit=1
    )[0]
    self_hosted_section = workflow_text.split("deploy-production-self-hosted:", maxsplit=1)[1]

    assert (
        "envs: DEPLOY_SCRIPT_SHA256,PROMETHEUS_HELPER_SHA256,ALERTMANAGER_HELPER_SHA256,IMAGE_REF,TAG,PRODUCTION_DOMAIN,DEPLOY_DIR,GHCR_USER,GHCR_TOKEN"
        in ssh_section
    )
    assert (
        'echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin'
        not in ssh_section
    )
    assert "GHCR_USER: ${{ github.repository_owner }}" in ssh_section
    assert "GHCR_TOKEN: ${{ secrets.GHCR_READ_TOKEN }}" in ssh_section
    assert "export GHCR_USER='${{ github.repository_owner }}'" in self_hosted_section
    assert "export GHCR_TOKEN='${{ secrets.GHCR_READ_TOKEN }}'" in self_hosted_section
    assert "continue-on-error: true" in self_hosted_section
    assert "for candidate in /usr/bin/docker /usr/local/bin/docker /snap/bin/docker; do" in (
        self_hosted_section
    )
    assert 'if [[ -n "$PRUNE_DOCKER_BIN" ]]; then' in self_hosted_section
    assert '"$PRUNE_DOCKER_BIN" image prune -f' in self_hosted_section
    assert '"$PRUNE_DOCKER_BIN" image prune -f || true' not in self_hosted_section
    assert (
        "Skipping Docker image prune: trusted docker binary not found on self-hosted runner"
        in self_hosted_section
    )
    assert (
        'echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin'
        not in self_hosted_section
    )


def test_production_deploy_jobs_run_preflight_before_live_deploy() -> None:
    """Fail fast on missing remote env files before bundle extraction or deploy."""

    workflow_text = CD_WORKFLOW_PATH.read_text(encoding="utf-8")
    ssh_section = workflow_text.split("deploy-production:", maxsplit=1)[1].split(
        "deploy-production-self-hosted:", maxsplit=1
    )[0]
    self_hosted_section = workflow_text.split("deploy-production-self-hosted:", maxsplit=1)[1]
    ssh_lines = ssh_section.splitlines()
    self_hosted_lines = self_hosted_section.splitlines()

    assert '"$tmp_script" --preflight-only' in ssh_section
    archive_export = '            export SHELL_BUNDLE_ARCHIVE="/tmp/${bundle_name}.tgz"'
    assert archive_export in ssh_lines
    assert ssh_lines.index(archive_export) < ssh_lines.index(
        '            /bin/bash "$tmp_script" --preflight-only'
    )
    assert ssh_lines.index(
        '            /bin/bash "$tmp_script" --preflight-only'
    ) < ssh_lines.index('            /bin/bash "$tmp_script"')

    assert "Preflight production deploy on self-hosted runner" in self_hosted_section
    assert 'export SHELL_BUNDLE_DIR="${GITHUB_WORKSPACE}"' in self_hosted_section
    assert "bash scripts/deploy_production.sh --preflight-only" in self_hosted_section
    assert self_hosted_lines.index('          export SHELL_BUNDLE_DIR="${GITHUB_WORKSPACE}"') < (
        self_hosted_lines.index("          bash scripts/deploy_production.sh --preflight-only")
    )
    assert self_hosted_lines.index(
        "          bash scripts/deploy_production.sh --preflight-only"
    ) < self_hosted_lines.index("          bash scripts/deploy_production.sh")


def test_prometheus_security_job_owns_only_pr_and_schedule_execution() -> None:
    workflow = yaml.safe_load(CD_WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert isinstance(workflow, dict)
    triggers = workflow.get("on", workflow.get(True))
    assert isinstance(triggers, dict)
    assert triggers["pull_request"] == {}
    assert triggers["schedule"] == [{"cron": "17 4 * * 1"}]

    jobs = workflow.get("jobs")
    assert isinstance(jobs, dict)
    security_job = jobs.get("prometheus-image-security-pr")
    assert isinstance(security_job, dict)
    assert security_job["permissions"] == {
        "contents": "read",
        "actions": "read",
        "packages": "read",
    }
    assert "environment" not in security_job
    assert jobs["prometheus-image-security-trusted"]["environment"] == "staging"
    security_text = str(security_job)
    assert "secrets.GHCR_READ_TOKEN" in security_text
    assert "scripts.ci.prometheus_source_image --operation consume" in security_text
    assert "persist-credentials': False" in security_text
    assert ".trivyignore" not in security_text
    assert "ignore-policy" not in security_text

    steps = security_job.get("steps")
    assert isinstance(steps, list)
    create_index = next(
        index
        for index, step in enumerate(steps)
        if isinstance(step, dict)
        and step.get("name") == "Create empty Prometheus Trivy ignore file"
    )
    scan_index = next(
        index
        for index, step in enumerate(steps)
        if isinstance(step, dict)
        and step.get("name") == "Scan exact Prometheus image without suppressions"
    )
    install_index = next(
        index
        for index, step in enumerate(steps)
        if isinstance(step, dict) and step.get("name") == "Install exact Trivy CLI"
    )
    assert create_index < install_index < scan_index

    create_step = steps[create_index]
    assert create_step["id"] == "prometheus_trivy_ignore"
    create_script = create_step["run"]
    assert "mktemp" in create_script
    assert "${RUNNER_TEMP}/pulseplate-prometheus-empty-trivyignore.XXXXXX" in create_script
    assert "umask 077" in create_script
    assert '[ ! -f "$empty_ignore" ]' in create_script
    assert '[ -L "$empty_ignore" ]' in create_script
    assert '[ -s "$empty_ignore" ]' in create_script
    assert "path=%s" in create_script

    install_step = steps[install_index]
    assert install_step["id"] == "prometheus_trivy"
    install_env = install_step.get("env")
    assert install_env == {
        "TRIVY_VERSION": "0.74.0",
        "TRIVY_ARCHIVE_SHA256": (
            "2ae6fe3ee734b7fdf11335663e18c75ea12dccc76062f09f164a3b0f8be4371a"  # pragma: allowlist secret
        ),
    }
    install_script = install_step["run"]
    assert "https://github.com/aquasecurity/trivy/releases/download/" in install_script
    assert "trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz" in install_script
    assert "sha256sum --check -" in install_script
    assert 'tar -xzf "$archive_path"' in install_script
    assert '"$trivy_path" --version' in install_script
    assert "sudo" not in install_script

    scan_step = steps[scan_index]
    assert "uses" not in scan_step
    scan_env = scan_step.get("env")
    assert scan_env == {
        "TRIVY_DB_REPOSITORY": "ghcr.io/aquasecurity/trivy-db",
        "PROMETHEUS_RUNTIME_REF": "${{ steps.prometheus-image.outputs.runtime_ref }}",
        "TRIVY_BIN": "${{ steps.prometheus_trivy.outputs.path }}",
        "TRIVY_IGNORE_FILE": "${{ steps.prometheus_trivy_ignore.outputs.path }}",
    }
    scan_script = scan_step["run"]
    assert "/dev/null" not in scan_script
    assert '"$TRIVY_BIN" image' in scan_script
    for argument in (
        "--scanners vuln,secret",
        "--format table",
        "--pkg-types os,library",
        "--severity CRITICAL,HIGH",
        "--exit-code 1",
        "--timeout 15m",
        '--ignorefile "$TRIVY_IGNORE_FILE"',
        "--cache-dir /tmp/trivy-cache-prometheus-image-security",
        '"$PROMETHEUS_RUNTIME_REF"',
    ):
        assert argument in scan_script

    # Both jobs are intentionally push-only. Pull requests and schedules may run the
    # isolated Prometheus image check, but must not fan out into release fixture work.
    push_only_main_jobs = {
        "main-push-admission",
        "release-control-plane-fixture-gate",
    }
    tag_jobs = {
        "production-gates",
        "build-production",
        "production-deploy-config",
        "release-control-plane-production-evidence",
        "deploy-production",
        "deploy-production-self-hosted",
    }
    for name in push_only_main_jobs:
        job = jobs.get(name)
        assert isinstance(job, dict)
        condition = job.get("if")
        assert isinstance(condition, str)
        assert "github.event_name == 'push'" in condition
        assert "refs/heads/main" in condition
    for name in tag_jobs:
        job = jobs.get(name)
        assert isinstance(job, dict)
        condition = job.get("if")
        assert isinstance(condition, str)
        assert "refs/tags/v" in condition

    assert " ".join(jobs["build"]["if"].split()) == (
        "!cancelled() && github.event_name == 'push' && github.ref == 'refs/heads/main' "
        "&& needs.prometheus-image-security.result == 'success' "
        "&& needs.obs2a-checkpoint-native.result == 'success' "
        "&& needs.main-push-admission.result == 'success' "
        "&& needs.staging-postgres-native-integration.result == 'success'"
    )
    assert set(jobs["build"]["needs"]) == {
        "prometheus-image-security",
        "obs2a-checkpoint-native",
        "main-push-admission",
        "staging-postgres-native-integration",
    }
    admission = jobs["main-push-admission"]
    assert admission["permissions"] == {}
    assert "actions/checkout" not in str(admission)
    assert "GITHUB_EVENT_NAME" in str(admission)
    assert "GITHUB_REF" in str(admission)
    assert jobs["production-gates"]["needs"] == "prometheus-image-security"


def test_cd_has_no_prometheus_candidate_publication_carrier() -> None:
    workflow_text = CD_WORKFLOW_PATH.read_text(encoding="utf-8")
    workflow = yaml.safe_load(workflow_text)
    assert isinstance(workflow, dict)
    triggers = workflow.get("on", workflow.get(True))
    jobs = workflow.get("jobs")
    assert isinstance(triggers, dict)
    assert isinstance(jobs, dict)

    dispatch = triggers["workflow_dispatch"]
    assert set(dispatch) == {"inputs"}
    assert set(dispatch["inputs"]) == {
        "postgres_mode",
        "source_sha",
        "alertmanager_mode",
        "alertmanager_qualification_run",
        "alertmanager_qualification_artifact",
        "alertmanager_qualification_source",
        "alertmanager_support_run",
        "alertmanager_support_artifact",
        "alertmanager_support_source",
        "alertmanager_candidate_run",
        "alertmanager_candidate_artifact",
        "alertmanager_candidate_source",
        "alertmanager_pr",
    }
    assert dispatch["inputs"]["postgres_mode"]["options"] == [
        "disabled",
        "synthetic-probe",
        "reuse",
    ]
    assert dispatch["inputs"]["postgres_mode"]["default"] == "disabled"
    assert dispatch["inputs"]["alertmanager_mode"]["default"] == "disabled"
    assert dispatch["inputs"]["alertmanager_mode"]["options"] == [
        "disabled",
        "module-qualify",
        "support-inspect",
        "build",
        "publish",
    ]
    alert = jobs["alertmanager-module-qualification"]
    assert "github.event_name == 'workflow_dispatch'" in alert["if"]
    assert "github.run_attempt == 1" in alert["if"]
    assert "github.repository == 'Katsiarynakavaleuskaya/PulsePlate'" in alert["if"]
    assert alert["permissions"] == {"contents": "read", "actions": "read"}
    assert 'test "$ALERTMANAGER_MODE" = module-qualify' in alert["steps"][0]["run"]
    assert "prometheus-grpc-candidate-publish" not in jobs
    assert workflow["permissions"] == {
        "actions": "read",
        "contents": "read",
        "id-token": "write",
        "packages": "write",
    }
    for rejected_carrier in (
        "expected_head_sha",
        "publish-prometheus-grpc-v1.83.1-ae54350536bd",
        "PULSEPLATE_PROMETHEUS_GHCR_TOKEN",
        "scripts/ci/prometheus_derivative_candidate.py",
    ):
        assert rejected_carrier not in workflow_text


def test_prometheus_cd_registry_credential_route_preserves_base_execution_boundary() -> None:
    """Historical node name; fixed reviewed control now replaces executable base capability."""
    workflow = yaml.safe_load(CD_WORKFLOW_PATH.read_text(encoding="utf-8"))
    job = workflow["jobs"]["prometheus-image-security-pr"]
    ordered = job["steps"]
    steps = {step["name"]: step for step in ordered}
    names = [step["name"] for step in ordered]
    initial_pr = steps["Checkout immutable PR head Prometheus contracts"]
    assert initial_pr["if"] == "${{ github.event_name == 'pull_request' }}"
    assert initial_pr["with"] == {
        "persist-credentials": False,
        "fetch-depth": 0,
        "ref": "${{ github.event.pull_request.head.sha }}",
    }
    initial_published = steps["Checkout immutable published Prometheus contracts"]
    assert (
        initial_published["if"]
        == "${{ github.event_name == 'push' || github.event_name == 'schedule' }}"
    )
    assert initial_published["with"] == {
        "persist-credentials": False,
        "fetch-depth": 0,
        "ref": "${{ github.sha }}",
    }
    assert [
        step["name"]
        for step in ordered
        if str(step.get("uses", "")).startswith("actions/checkout@")
    ] == [
        initial_pr["name"],
        initial_published["name"],
        "Checkout fixed trusted Prometheus control",
        "Checkout separately designated AM controller",
    ]
    event = steps["Validate exact Prometheus checkout revisions"]
    assert "secrets." not in str(event)
    assert 'head, base = sha(pr["head"].get("sha")), sha(pr["base"].get("sha"))' in event["run"]
    assert 'output.write("head=" + head + "\\nbase=" + base + "\\n")' in event["run"]
    assert "checkout_ref" not in str(job)
    route = steps["Classify the fixed regular Prometheus source blobs"]
    assert route["id"] == "prometheus-route" and "secrets." not in str(route)
    assert set(route["env"]) == {"PROMETHEUS_EVENT_HEAD", "PROMETHEUS_EVENT_BASE"}
    for invariant in (
        '"--no-replace-objects"',
        '"GIT_CONFIG_NOSYSTEM": "1"',
        '"GIT_CONFIG_GLOBAL": "/dev/null"',
        'fields[:2] == [b"100644", b"blob"]',
        'paths = (*trusted["PRODUCER_FILES"], trusted["MANIFEST_PATH"])',
        "source_blob(base, path)",
        "source_blob(head, path)",
        '"Prometheus_source_object_HOLD"',
        '"Prometheus_manifest_object_HOLD"',
        'elif os.environ["GITHUB_EVENT_NAME"] in ("push", "schedule"):',
    ):
        assert invariant in route["run"]
    assert route["run"].count('trusted["classify_source_change"](previous, current)') == 1
    assert 'require(git("rev-parse", "HEAD").strip().decode() == head' in route["run"]
    assert '"historical_helper_change": "historical_pr_candidate"' in route["run"]
    consumer = steps["Admit retained PR candidate or published immutable subject"]
    assert consumer["id"] == "prometheus-image"
    assert consumer["env"]["GHCR_READ_TOKEN"] == (
        "${{ github.event_name == 'pull_request' && steps.prometheus-route.outputs.mode == 'unchanged_pr_published' && secrets.GITHUB_TOKEN || github.event_name != 'pull_request' && steps.prometheus-route.outputs.mode == 'trusted_published' && secrets.GHCR_READ_TOKEN || '' }}"
    )
    assert "changed_pr_candidate | historical_pr_candidate)" in consumer["run"]
    assert "Prometheus_candidate_registry_HOLD" in consumer["run"]
    assert '*) echo "Prometheus credential route HOLD" >&2; exit 1' in consumer["run"]
    assert 'if [ "$GITHUB_EVENT_NAME" = pull_request ]; then' in consumer["run"]
    assert 'test "$PROMETHEUS_CREDENTIAL_ROUTE" = trusted_published' in consumer["run"]
    assert "scripts.ci.prometheus_source_image --operation consume" in consumer["run"]
    control = steps["Checkout fixed trusted Prometheus control"]
    cleanup = steps["Remove fixed trusted Prometheus control checkout"]
    assert (
        control["with"]["ref"]
        # pragma: allowlist nextline secret - public trusted control commit
        == "dab47fc6153f87e35233e20aa255d97e68a5ed93"
    )
    assert control["with"]["persist-credentials"] is False
    assert control["with"]["sparse-checkout"] == "scripts/ci/prometheus_source_image.py"
    assert control["if"] == "${{ success() && github.event_name == 'pull_request' }}"
    assert cleanup["if"] == (
        "${{ always() && github.event_name == 'pull_request' && "
        "(steps.prometheus-control-checkout.outcome == 'success' || "
        "steps.prometheus-control-checkout.outcome == 'failure') }}"
    )
    control_bytes = (REPO_ROOT / "scripts/ci/prometheus_source_image.py").read_bytes()
    control_blob = hashlib.sha1(
        b"blob " + str(len(control_bytes)).encode("ascii") + b"\0" + control_bytes,
        usedforsecurity=False,
    ).hexdigest()
    control_object = f"100644 blob {control_blob}\\tscripts/ci/prometheus_source_image.py\\0"
    for script in (route["run"], consumer["run"]):
        assert "Prometheus_control_interface_HOLD" in script
        assert str(len(control_bytes)) in script
        assert control_object in script
        assert hashlib.sha256(control_bytes).hexdigest() in script
    assert 'trusted["consume_image"](work, material' in consumer["run"]
    assert 'trusted["one_object"](raw).get("admission")' in consumer["run"]
    assert 'admission != result["admission"]' in consumer["run"]
    assert "Prometheus_unchanged_result_HOLD" in consumer["run"]
    assert "Prometheus_unchanged_admission_HOLD" in consumer["run"]
    assert "Require the trusted base published consumer capability" not in names
    assert "Bind the unchanged PR admission after trusted cleanup" not in names
    expected_order = [
        event["name"],
        initial_pr["name"],
        initial_published["name"],
        control["name"],
        route["name"],
        "Wait for the exact trusted Prometheus publisher",
        consumer["name"],
        cleanup["name"],
        "Require separately designated AM controller",
        "Checkout separately designated AM controller",
        "Prepare exact AM subject before material execution",
        "Remove designated AM controller after credential cleanup",
        "Check canonical Prometheus config with exact-image promtool",
    ]
    assert [names.index(name) for name in expected_order] == sorted(
        names.index(name) for name in expected_order
    )


def test_prometheus_security_smoke_reuses_canonical_native_parser() -> None:
    workflow = yaml.safe_load(CD_WORKFLOW_PATH.read_text(encoding="utf-8"))
    jobs = workflow.get("jobs")
    assert isinstance(jobs, dict)
    security_job = jobs.get("prometheus-image-security-pr")
    assert isinstance(security_job, dict)
    steps = security_job.get("steps")
    assert isinstance(steps, list)
    smoke = next(
        step
        for step in steps
        if isinstance(step, dict)
        and step.get("name") == "Prove synthetic non-root header and named-volume runtime"
    )
    script = smoke.get("run")
    assert isinstance(script, str)

    assert 'scalar(up{job="pulseplate-obs1b-synthetic-self"})' in script
    assert (
        "from scripts.verify_premium_alias_telemetry import VerificationError, "
        "_parse_promtool_sample" in script
    )
    assert "_parse_promtool_sample(Path(sys.argv[1]).read_bytes())" in script
    assert "except VerificationError:" in script
    assert "value != 1.0" in script
    assert 'payload.get("data")' not in script
    assert 'payload.get("status")' not in script
    assert "resultType" not in script

    native_scalar = b'[1787504507.565,"1"]'
    native_vector = b'[{"metric":{},"value":[1787504507.821,"1"]}]'
    assert verifier._parse_promtool_sample(native_scalar) == (1787504507.565, 1.0)
    assert verifier._parse_promtool_sample(native_vector) == (1787504507.821, 1.0)


def test_self_hosted_preflight_and_deploy_bind_same_exact_image_ref() -> None:
    workflow = yaml.safe_load(CD_WORKFLOW_PATH.read_text(encoding="utf-8"))
    jobs = workflow.get("jobs")
    assert isinstance(jobs, dict)
    job = jobs.get("deploy-production-self-hosted")
    assert isinstance(job, dict)
    steps = job.get("steps")
    assert isinstance(steps, list)
    named_steps = {
        step.get("name"): step
        for step in steps
        if isinstance(step, dict) and isinstance(step.get("name"), str)
    }
    preflight = named_steps["Preflight production deploy on self-hosted runner"].get("run")
    deploy = named_steps["Deploy on self-hosted runner (pinned digest)"].get("run")
    assert isinstance(preflight, str)
    assert isinstance(deploy, str)

    exact_export = (
        'export IMAGE_REF="ghcr.io/${{ needs.build-production.outputs.image_name }}@'
        '${{ needs.build-production.outputs.digest }}"'
    )
    assert preflight.count(exact_export) == 1
    assert deploy.count(exact_export) == 1
    assert preflight.index(exact_export) < preflight.index(
        "bash scripts/deploy_production.sh --preflight-only"
    )
    assert "${IMAGE_REF:-" not in preflight
    assert "PROD_DEPLOY_MODE" not in preflight


@pytest.mark.parametrize(
    "filename,job,credential",
    [
        ("ci.yml", "lint", "${{ secrets.GITHUB_TOKEN }}"),
        ("cd.yml", "obs2a-checkpoint-native", "${{ secrets.GHCR_READ_TOKEN }}"),
    ],
)
def test_checkpoint_native_consumer_precedes_secret_free_child(
    filename: str, job: str, credential: str
) -> None:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows" / filename).read_text())
    selected = workflow["jobs"][job]
    assert selected["permissions"] == {"contents": "read", "actions": "read", "packages": "read"}
    if filename == "ci.yml":
        assert "environment" not in selected
    else:
        assert selected.get("environment") == "staging"
    step = next(
        s
        for s in selected["steps"]
        if s.get("name", "").startswith("Native ") and "OBS2A" in s["name"]
    )
    script = step["run"]
    if filename == "ci.yml":
        assert not {"GH_TOKEN", "GITHUB_TOKEN", "GHCR_READ_TOKEN"} & step["env"].keys()
        consumer = next(s for s in selected["steps"] if s.get("id") == "checkpoint-image")
        assert consumer["env"]["GH_TOKEN"] == consumer["env"]["GITHUB_TOKEN"] == credential
        assert consumer["env"]["GHCR_READ_TOKEN"] == (
            "${{ steps.checkpoint-route.outputs.mode == 'unchanged_pr_published' && secrets.GITHUB_TOKEN || '' }}"
        )
        assert 'trusted["consume_image"](work, material' in consumer["run"]
        setup = next(
            s for s in selected["steps"] if s.get("uses") == "./.github/actions/python-setup"
        )
        cleanup = next(
            s
            for s in selected["steps"]
            if s.get("name") == "Remove fixed trusted Prometheus control checkout"
        )
        assert (
            selected["steps"].index(consumer)
            < selected["steps"].index(cleanup)
            < selected["steps"].index(setup)
            < selected["steps"].index(step)
        )
    else:
        consumer = next(
            s
            for s in selected["steps"]
            if s.get("name") == "Consume exact Prometheus before main native fixtures"
        )
        assert consumer["env"]["GHCR_READ_TOKEN"] == credential
        assert (
            consumer["env"]["GH_TOKEN"]
            == consumer["env"]["GITHUB_TOKEN"]
            == "${{ secrets.GITHUB_TOKEN }}"
        )
        assert selected["steps"].index(consumer) < selected["steps"].index(step)
        assert "--operation consume" in consumer["run"] and "--operation consume" not in script
        assert not {"GH_TOKEN", "GITHUB_TOKEN", "GHCR_READ_TOKEN"} & step["env"].keys()
        assert consumer["timeout-minutes"] == 18
        assert step["timeout-minutes"] == "${{ fromJSON(env.ALERTMANAGER_GENERIC_NATIVE_MINUTES) }}"
    child = next(
        line.strip()
        for line in script.splitlines()
        if line.strip().startswith("sudo /usr/bin/env -i ")
    )
    assert not any(
        value in child for value in ("GH_TOKEN", "GITHUB_TOKEN", "GHCR_READ_TOKEN", "DOCKER_CONFIG")
    )
    assert (
        'native_python="$(command -v python)"'
        if filename == "ci.yml"
        else 'native_python="$AM_HOST_PYTHON"'
    ) in script
    assert 'exit "$native_status"' in script and 'exit "$capture_status"' in script
    assert not any("login-action" in str(s.get("uses", "")) for s in selected["steps"])


@pytest.mark.parametrize("symlink_position", [None, 0, 1, 2])
@pytest.mark.parametrize("old_and_list_oracle", [False, True])
def test_trusted_ssh_file_loop_rejects_matching_symlink_before_file_effects(
    tmp_path: Path,
    symlink_position: int | None,
    old_and_list_oracle: bool,
) -> None:
    """Execute only the extracted local boundary with synthetic files, never SSH/deployment."""
    workflow = yaml.safe_load(CD_WORKFLOW_PATH.read_text())
    step = next(
        item
        for item in workflow["jobs"]["deploy-production"]["steps"]
        if item.get("name") == "Deploy to production over SSH (pinned digest)"
    )
    actual = step["with"]["script"]
    start = actual.index('for trusted in "$tmp_script"')
    end = actual.index("\nbundle_name=", start)
    snippet = actual[start:end]
    fixed = '[ ! -L "$trusted" ]\n  [ -f "$trusted" ]'
    assert fixed in snippet
    if old_and_list_oracle:
        snippet = snippet.replace(fixed, '[ ! -L "$trusted" ] && [ -f "$trusted" ]')
    assert '/bin/bash "$tmp_script" --preflight-only' in actual
    snippet = "set -euo pipefail\n" + snippet + '\n/bin/bash "$tmp_script" --preflight-only\n'
    tools = tmp_path / "trusted-tools"
    tools.mkdir(mode=0o700)
    trace = tmp_path / "effects"
    contents = [
        b'#!/bin/sh\nprintf "launch\\n" >> "$CONTROL_TRACE"\n',
        b"# synthetic Prometheus helper\n",
        b"# synthetic AM helper\n",
    ]
    files = [tools / name for name in ("deploy.sh", "prometheus.py", "alertmanager.py")]
    for path, content in zip(files, contents):
        path.write_bytes(content)
        path.chmod(0o640)
    target = tmp_path / "owned-target-outside-tool-directory"
    if symlink_position is not None:
        target.write_bytes(contents[symlink_position])
        target.chmod(0o640)
        files[symlink_position].unlink()
        files[symlink_position].symlink_to(target)
        assert files[symlink_position].read_bytes() == contents[symlink_position]
        assert files[symlink_position].lstat().st_uid == os.geteuid()
        assert files[symlink_position].lstat().st_nlink == 1
    commands = tmp_path / "commands"
    commands.mkdir()
    native_observer = f"#!{sys.executable}\n" + r"""
import hashlib
import os
from pathlib import Path
import sys
name = Path(sys.argv[0]).name
args = sys.argv[1:]
trace = Path(os.environ["CONTROL_TRACE"])
def record(value):
    with trace.open("a") as stream:
        stream.write(value + "\n")
if name == "stat":
    assert args[:2] == ["-c", "%u:%h"] and len(args) == 3
    path = Path(args[2])
    record("stat|" + str(path))
    value = path.lstat()
    print(str(value.st_uid) + ":" + str(value.st_nlink))
elif name == "sha256sum":
    assert len(args) == 1
    path = Path(args[0])
    record("hash|" + str(path))
    print(hashlib.sha256(path.read_bytes()).hexdigest() + "  " + str(path))
elif name == "chmod":
    assert args[:2] == ["600", "--"] and len(args) == 5
    record("chmod")
    for raw in args[2:]:
        path = Path(raw)
        assert path.resolve().is_relative_to(Path(os.environ["CONTROL_ROOT"]))
        path.chmod(0o600)
else:
    raise AssertionError(name)
"""
    for name in ("stat", "sha256sum", "chmod"):
        command = commands / name
        command.write_text(native_observer)
        command.chmod(0o700)
    environment = {
        "PATH": str(commands) + os.pathsep + os.defpath,
        "HOME": str(tmp_path),
        "LANG": "C",
        "tmp_script": str(files[0]),
        "PROMETHEUS_CONTRACT_HELPER": str(files[1]),
        "ALERTMANAGER_CONTRACT_HELPER": str(files[2]),
        "DEPLOY_SCRIPT_SHA256": hashlib.sha256(contents[0]).hexdigest(),
        "PROMETHEUS_HELPER_SHA256": hashlib.sha256(contents[1]).hexdigest(),
        "ALERTMANAGER_HELPER_SHA256": hashlib.sha256(contents[2]).hexdigest(),
        "CONTROL_TRACE": str(trace),
        "CONTROL_ROOT": str(tmp_path),
    }
    bash = shutil.which("bash")
    assert bash is not None
    result = subprocess.run(
        [bash, "-c", snippet],
        env=environment,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    events = trace.read_text().splitlines() if trace.exists() else []
    if symlink_position is None:
        assert result.returncode == 0, result.stdout + result.stderr
        assert events == [
            *("stat|" + str(path) for path in files),
            *("hash|" + str(path) for path in files),
            "chmod",
            "launch",
        ]
        assert all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in files)
    elif old_and_list_oracle:
        # Counterfactual reproduces the original bug despite matching hash/owner/link count.
        assert result.returncode == 0, result.stdout + result.stderr
        assert "stat|" + str(files[symlink_position]) in events
        assert events[-2:] == ["chmod", "launch"]
        assert stat.S_IMODE(target.stat().st_mode) == 0o600
    else:
        assert result.returncode != 0
        assert events == ["stat|" + str(path) for path in files[:symlink_position]]
        assert stat.S_IMODE(target.stat().st_mode) == 0o640
        assert all(stat.S_IMODE(path.stat().st_mode) == 0o640 for path in files)
        assert target.read_bytes() == contents[symlink_position]
