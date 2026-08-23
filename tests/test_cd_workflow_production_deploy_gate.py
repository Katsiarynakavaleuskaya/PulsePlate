"""Regression tests for production deploy gating in the CD workflow."""

from __future__ import annotations

import re
from pathlib import Path

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
        r"\s+deploy/prometheus/prometheus\.yml \\\n"
        r"\s+deploy/prometheus/image-manifest\.json \\\n"
        r"\s+scripts/diagnose_web\.sh \\\n"
        r"\s+scripts/redeploy_caddy\.sh",
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
        "envs: DEPLOY_SCRIPT_B64,IMAGE_REF,TAG,PRODUCTION_DOMAIN,DEPLOY_DIR,GHCR_USER,GHCR_TOKEN"
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
        '            "$tmp_script" --preflight-only'
    )
    assert ssh_lines.index('            "$tmp_script" --preflight-only') < ssh_lines.index(
        '            "$tmp_script"'
    )

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
    security_job = jobs.get("prometheus-image-security")
    assert isinstance(security_job, dict)
    assert security_job["permissions"] == {"contents": "read"}
    assert "environment" not in security_job
    security_text = str(security_job)
    assert "secrets." not in security_text
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
        "TRIVY_VERSION": "0.72.0",
        "TRIVY_ARCHIVE_SHA256": (
            "bbb64b9695866ce4a7a8f5c9592002c5961cab378577fa3f8a040df362b9b2ea"  # pragma: allowlist secret
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

    main_jobs = {"main-push-admission", "release-control-plane-fixture-gate"}
    tag_jobs = {
        "production-gates",
        "build-production",
        "production-deploy-config",
        "release-control-plane-production-evidence",
        "deploy-production",
        "deploy-production-self-hosted",
    }
    for name in main_jobs:
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

    assert jobs["build"]["if"] == "github.ref == 'refs/heads/main'"
    assert set(jobs["build"]["needs"]) == {
        "prometheus-image-security",
        "main-push-admission",
    }
    admission = jobs["main-push-admission"]
    assert admission["permissions"] == {}
    assert "actions/checkout" not in str(admission)
    assert "GITHUB_EVENT_NAME" in str(admission)
    assert "GITHUB_REF" in str(admission)
    assert jobs["production-gates"]["needs"] == "prometheus-image-security"


def test_prometheus_security_smoke_reuses_canonical_native_parser() -> None:
    workflow = yaml.safe_load(CD_WORKFLOW_PATH.read_text(encoding="utf-8"))
    jobs = workflow.get("jobs")
    assert isinstance(jobs, dict)
    security_job = jobs.get("prometheus-image-security")
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
