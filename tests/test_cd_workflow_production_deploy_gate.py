"""Regression tests for production deploy gating in the CD workflow."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CD_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "cd.yml"


def test_production_deploy_jobs_use_bridge_job_outputs() -> None:
    """Guard against build-only production tags caused by env var visibility."""

    workflow_text = CD_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "production-deploy-config:" in workflow_text
    assert "Resolve production deploy configuration" in workflow_text
    assert "needs.production-deploy-config.outputs.should_deploy == 'true'" in workflow_text
    assert "needs.production-deploy-config.outputs.deploy_mode == 'ssh'" in workflow_text
    assert "needs.production-deploy-config.outputs.deploy_mode == 'self-hosted'" in workflow_text
    assert "vars.PROD_DEPLOY_MODE == 'ssh'" not in workflow_text
    assert "vars.PROD_DEPLOY_MODE == 'self-hosted'" not in workflow_text


def test_production_deploy_syncs_shell_bundle_for_caddy_rebuild() -> None:
    """Guard against shipping only the app image while leaving the web shell stale."""

    workflow_text = CD_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "Stage production shell bundle for SSH deploy" in workflow_text
    assert (
        'tar -czf "$archive_path" frontend deploy/Caddyfile.production scripts/diagnose_web.sh'
        in workflow_text
    )
    assert 'tar -xzf /tmp/pulseplate-shell-bundle.tgz -C "$tmp_bundle_dir"' in workflow_text
    assert 'export SHELL_BUNDLE_DIR="$tmp_bundle_dir"' in workflow_text
    assert 'export SHELL_BUNDLE_DIR="${GITHUB_WORKSPACE}"' in workflow_text
