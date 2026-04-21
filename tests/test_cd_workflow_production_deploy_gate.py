"""Regression tests for production deploy gating in the CD workflow."""

from __future__ import annotations

import re
from pathlib import Path

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
    assert 'tar -xzf "/tmp/${bundle_name}.tgz" -C "$tmp_bundle_dir"' in workflow_text
    assert 'rm -f "/tmp/${bundle_name}.tgz"' in workflow_text
    assert 'export SHELL_BUNDLE_DIR="$tmp_bundle_dir"' in workflow_text
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
    assert ssh_lines.index('            "$tmp_script" --preflight-only') < ssh_lines.index(
        '            tar -xzf "/tmp/${bundle_name}.tgz" -C "$tmp_bundle_dir"'
    )
    assert ssh_lines.index('            "$tmp_script" --preflight-only') < ssh_lines.index(
        '            "$tmp_script"'
    )

    assert "Preflight production deploy on self-hosted runner" in self_hosted_section
    assert "bash scripts/deploy_production.sh --preflight-only" in self_hosted_section
    assert self_hosted_lines.index(
        "          bash scripts/deploy_production.sh --preflight-only"
    ) < self_hosted_lines.index("          bash scripts/deploy_production.sh")
