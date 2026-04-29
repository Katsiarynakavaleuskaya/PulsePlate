import os
import stat
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_COMPOSE_PATH = REPO_ROOT / "deploy" / "docker-compose.production.yaml"
PRODUCTION_COMPOSE_TEXT = PRODUCTION_COMPOSE_PATH.read_text(encoding="utf-8")


def test_production_compose_source_of_truth_matches_split_contract() -> None:
    compose = yaml.safe_load(PRODUCTION_COMPOSE_TEXT)
    assert isinstance(compose, dict), "production compose must deserialize to a mapping"

    services = compose.get("services")
    assert isinstance(services, dict), "production compose must define a services mapping"

    assert "postgres" not in services
    app_service = services.get("app")
    assert isinstance(app_service, dict), "production compose must define an app service"
    assert app_service["image"] == "${IMAGE_REF:?IMAGE_REF is required}"
    assert "build" not in app_service
    app_env_file = app_service.get("env_file")
    assert app_env_file in (".env", [".env"]), "app service must reference deploy/.env"

    caddy_service = services.get("caddy")
    assert isinstance(caddy_service, dict), "production compose must define a caddy service"
    assert "image" not in caddy_service

    caddy_build = caddy_service.get("build")
    assert isinstance(caddy_build, dict), "caddy service must use a build-based shell contract"
    assert caddy_build["context"] == "../frontend"
    assert caddy_build["dockerfile"] == "Dockerfile.caddy-spa"

    caddy_build_args = caddy_build.get("args")
    assert isinstance(caddy_build_args, dict), "caddy build must define build args"
    assert caddy_build_args["VITE_API_BASE"] == "${VITE_API_BASE:-/api/v1}"


@pytest.mark.parametrize(
    "relative_path",
    (
        "deploy/PRODUCTION.md",
        "deploy/WORKFLOW.md",
        "scripts/QUICK_DIAGNOSTIC.md",
    ),
)
def test_manual_shell_sync_docs_are_merged_truth_only(relative_path: str) -> None:
    content = (REPO_ROOT / relative_path).read_text(encoding="utf-8")

    rsync_command = "rsync -az --delete frontend/"
    rsync_indexes = [
        index for index in range(len(content)) if content.startswith(rsync_command, index)
    ]
    assert rsync_indexes, f"Expected rsync command not found in {relative_path}"

    for rsync_index in rsync_indexes:
        provenance_window = content[max(0, rsync_index - 1000) : rsync_index]
        has_git_release_truth = (
            "git fetch origin main" in provenance_window
            and "git switch --detach origin/main" in provenance_window
        )
        has_bundle_release_truth = (
            "CI-produced release bundle" in provenance_window
            or "unpacked CI-produced release bundle" in provenance_window
        )

        assert "merged" in provenance_window or "release bundle" in provenance_window
        assert has_git_release_truth or has_bundle_release_truth
        assert "dirty" in provenance_window or "unmerged" in provenance_window


def test_deploy_production_rejects_shell_bundle_without_redeploy_helper(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "production"
    shell_bundle_dir = tmp_path / "shell-bundle"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "docker.log"
    project_dir.mkdir()
    shell_bundle_dir.mkdir()
    bin_dir.mkdir()
    (project_dir / "docker-compose.production.yaml").write_text("services: {}\n", encoding="utf-8")
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )
    (shell_bundle_dir / "frontend").mkdir()
    (shell_bundle_dir / "deploy").mkdir()
    (shell_bundle_dir / "deploy" / "Caddyfile.production").write_text(
        'pulseplate.test {\n    respond "ok"\n}\n',
        encoding="utf-8",
    )
    (shell_bundle_dir / "deploy" / "docker-compose.production.yaml").write_text(
        PRODUCTION_COMPOSE_TEXT, encoding="utf-8"
    )
    (shell_bundle_dir / "scripts").mkdir()
    (shell_bundle_dir / "scripts" / "diagnose_web.sh").write_text(
        "#!/usr/bin/env bash\nprintf 'bundle-diagnose\\n'\n", encoding="utf-8"
    )

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
"""
    curl_stub = """#!/usr/bin/env bash
set -euo pipefail
"""
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = "docker-compose.production.yaml"
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"
    env["PRODUCTION_DOMAIN"] = "pulseplate.test"
    env["SHELL_BUNDLE_DIR"] = str(shell_bundle_dir)

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "SHELL_BUNDLE_DIR is missing scripts/redeploy_caddy.sh" in completed.stderr
    assert not log_file.exists()


def test_deploy_production_preflight_rejects_shell_bundle_without_frontend(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "production"
    shell_bundle_dir = tmp_path / "shell-bundle"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "docker.log"
    project_dir.mkdir()
    shell_bundle_dir.mkdir()
    bin_dir.mkdir()
    (project_dir / "docker-compose.production.yaml").write_text("services: {}\n", encoding="utf-8")
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )
    (shell_bundle_dir / "deploy").mkdir()
    (shell_bundle_dir / "deploy" / "Caddyfile.production").write_text(
        'pulseplate.test {\n    respond "ok"\n}\n',
        encoding="utf-8",
    )
    (shell_bundle_dir / "deploy" / "docker-compose.production.yaml").write_text(
        PRODUCTION_COMPOSE_TEXT, encoding="utf-8"
    )
    (shell_bundle_dir / "scripts").mkdir()
    (shell_bundle_dir / "scripts" / "redeploy_caddy.sh").write_text(
        "#!/usr/bin/env bash\nprintf 'bundle-redeploy\\n'\n", encoding="utf-8"
    )

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
"""
    curl_stub = """#!/usr/bin/env bash
set -euo pipefail
"""
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = "docker-compose.production.yaml"
    env["DATABASE_URL"] = (
        "postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate"  # pragma: allowlist secret
    )
    env["PRODUCTION_DOMAIN"] = "pulseplate.test"
    env["SHELL_BUNDLE_DIR"] = str(shell_bundle_dir)

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh"), "--preflight-only"],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "SHELL_BUNDLE_DIR is missing frontend/" in completed.stderr
    assert not log_file.exists()


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _assert_log_index(
    log_lines: list[str],
    *,
    predicate: Callable[[str], bool],
    message: str,
) -> int:
    index = next((position for position, line in enumerate(log_lines) if predicate(line)), None)
    assert index is not None, message
    return index


def test_postgres_backup_helper_passes_project_dir_and_compose_file(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    bin_dir = tmp_path / "bin"
    backup_dir = tmp_path / "backups"
    log_file = tmp_path / "docker.log"
    project_dir.mkdir()
    bin_dir.mkdir()
    backup_dir.mkdir()

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' "$*" >> "{log_file}"
cat <<'EOF'
FAKE_BACKUP
EOF
"""
    _write_executable(bin_dir / "docker", docker_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"  # pragma: allowlist secret
    env["PROJECT_DIR"] = str(project_dir)
    env["BACKUP_DIR"] = str(backup_dir)
    env["COMPOSE_FILE"] = "docker-compose.staging.yaml"
    env["POSTGRES_USER"] = "pulseplate"
    env["POSTGRES_DB"] = "pulseplate"

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/ops/postgres_backup.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Backup created:" in completed.stdout
    docker_call = log_file.read_text(encoding="utf-8")
    assert f"compose --project-directory {project_dir}" in docker_call
    assert f"-f {project_dir / 'docker-compose.staging.yaml'}" in docker_call
    assert "exec -T postgres pg_dump -U pulseplate -d pulseplate -Fc" in docker_call
    backup_files = list(backup_dir.glob("pulseplate_*.dump"))
    assert len(backup_files) == 1
    assert backup_files[0].read_text(encoding="utf-8").strip() == "FAKE_BACKUP"


def test_postgres_restore_helper_passes_project_dir_and_compose_file(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "docker.log"
    backup_file = tmp_path / "pulseplate.dump"
    project_dir.mkdir()
    bin_dir.mkdir()
    backup_file.write_text("FAKE_RESTORE", encoding="utf-8")

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' "$*" >> "{log_file}"
if printf '%s\\n' "$*" | grep -q 'pg_restore'; then
  cat >/dev/null
fi
"""
    _write_executable(bin_dir / "docker", docker_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["PROJECT_DIR"] = str(project_dir)
    env["COMPOSE_FILE"] = "docker-compose.production.yaml"
    env["POSTGRES_USER"] = "pulseplate"
    env["POSTGRES_DB"] = "pulseplate"

    completed = subprocess.run(
        [
            str(REPO_ROOT / "scripts/ops/postgres_restore.sh"),
            str(backup_file),
        ],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Restore completed from:" in completed.stdout
    docker_calls = log_file.read_text(encoding="utf-8").splitlines()
    assert len(docker_calls) == 2
    assert all(f"compose --project-directory {project_dir}" in call for call in docker_calls)
    assert all(
        f"-f {project_dir / 'docker-compose.production.yaml'}" in call for call in docker_calls
    )
    assert "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" in docker_calls[0]
    assert (
        "exec -T postgres pg_restore -U pulseplate -d pulseplate --clean --if-exists"
        in docker_calls[1]
    )


def test_deploy_production_runs_migrations_before_caddy_and_external_ready(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "production"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    bin_dir.mkdir()
    (project_dir / "docker-compose.production.yaml").write_text("services: {}\n", encoding="utf-8")
    (project_dir / ".env").write_text(
        "\n".join(
            [
                "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate",  # pragma: allowlist secret
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
case "$*" in
  *"compose --env-file "*"-f docker-compose.production.yaml ps -q app"*)
    printf 'app-id\\n'
    ;;
  *"inspect --format "*)
    printf 'healthy\\n'
    ;;
  *"ps --format "*)
    printf 'CONTAINER ID\\n'
    ;;
esac
"""
    curl_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'curl %s\\n' "$*" >> "{log_file}"
"""
    sleep_stub = "#!/usr/bin/env bash\nset -euo pipefail\n"
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)
    _write_executable(bin_dir / "sleep", sleep_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = "docker-compose.production.yaml"
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"
    env["PRODUCTION_DOMAIN"] = "pulseplate.test"

    subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    migrate_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "compose --env-file" in line
        and "run --rm --no-deps app alembic upgrade head" in line,
        message="Expected one-shot alembic migration step to appear in deploy log",
    )
    app_up_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "compose --env-file" in line
        and "up -d --remove-orphans app" in line,
        message="Expected app docker compose up step to appear in deploy log",
    )
    caddy_build_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "compose --env-file" in line and "build caddy" in line,
        message="Expected caddy docker compose build step to appear in deploy log",
    )
    caddy_up_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "compose --env-file" in line
        and "up -d --remove-orphans caddy" in line,
        message="Expected caddy docker compose up step to appear in deploy log",
    )
    external_ready_index = _assert_log_index(
        log_lines,
        predicate=lambda line: line.startswith("curl ") and "https://pulseplate.test/ready" in line,
        message="Expected external readiness check to appear in deploy log",
    )

    assert migrate_index < app_up_index < caddy_build_index < caddy_up_index < external_ready_index
    assert all("up -d --remove-orphans postgres" not in line for line in log_lines)
    assert all("helper " not in line for line in log_lines)


def test_deploy_production_preflight_only_exits_non_zero_when_default_env_file_is_missing(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "production"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    bin_dir.mkdir()
    (project_dir / "docker-compose.production.yaml").write_text("services: {}\n", encoding="utf-8")

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
"""
    _write_executable(bin_dir / "docker", docker_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["COMPOSE_FILE"] = "docker-compose.production.yaml"

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh"), "--preflight-only"],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert f"Missing production env file: {project_dir / '.env'}" in completed.stderr
    assert "GitHub Actions does not provision it." in completed.stderr
    assert "See deploy/PRODUCTION.md for the canonical bootstrap contract." in completed.stderr
    # RU: Неуспешный --preflight-only запуск не должен создавать deploy log.
    # EN: A failed --preflight-only run must not create a deploy log.
    assert not log_file.exists()


def test_deploy_production_fails_fast_when_resolved_compose_file_is_missing(tmp_path: Path) -> None:
    project_dir = tmp_path / "production"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    bin_dir.mkdir()
    (project_dir / ".env").write_text(
        "\n".join(
            [
                "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate",  # pragma: allowlist secret
                "PRODUCTION_DOMAIN=pulseplate.test",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
"""
    _write_executable(bin_dir / "docker", docker_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = str(project_dir / "missing-compose.yaml")
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh"), "--preflight-only"],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert (
        f"RESOLVED_COMPOSE_FILE does not exist: {project_dir / 'missing-compose.yaml'}"
        in completed.stderr
    )
    assert not log_file.exists()


def test_deploy_production_logs_in_to_ghcr_with_resolved_docker_binary(tmp_path: Path) -> None:
    project_dir = tmp_path / "production"
    docker_home = tmp_path / "docker-home"
    docker_dir = docker_home / "bin"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    docker_dir.mkdir(parents=True)
    bin_dir.mkdir()
    (project_dir / "docker-compose.production.yaml").write_text("services: {}\n", encoding="utf-8")
    (project_dir / ".env").write_text(
        "\n".join(
            [
                "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate",  # pragma: allowlist secret
                "GHCR_USER=stale-env-user",
                "GHCR_TOKEN=stale-env-token",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
case "$*" in
  "login ghcr.io -u deploy-bot --password-stdin")
    cat >/dev/null
    ;;
  *"compose --env-file "*"-f docker-compose.production.yaml ps -q app"*)
    printf 'app-id\\n'
    ;;
  *"inspect --format "*)
    printf 'healthy\\n'
    ;;
  *"ps --format "*)
    printf 'CONTAINER ID\\n'
    ;;
esac
"""
    curl_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'curl %s\\n' "$*" >> "{log_file}"
"""
    sleep_stub = "#!/usr/bin/env bash\nset -euo pipefail\n"
    _write_executable(docker_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)
    _write_executable(bin_dir / "sleep", sleep_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(docker_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = "docker-compose.production.yaml"
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"
    env["PRODUCTION_DOMAIN"] = "pulseplate.test"
    env["GHCR_USER"] = "deploy-bot"
    env["GHCR_TOKEN"] = "read-token"

    subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    login_index = _assert_log_index(
        log_lines,
        predicate=lambda line: line == "docker login ghcr.io -u deploy-bot --password-stdin",
        message="Expected deploy script to log in to GHCR via resolved docker binary",
    )
    pull_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "compose --env-file" in line and "pull app" in line,
        message="Expected deploy script to pull the production app image",
    )

    assert login_index < pull_index
    assert all("stale-env-user" not in line for line in log_lines)
    assert all("stale-env-token" not in line for line in log_lines)


def test_deploy_production_syncs_shell_bundle_and_prunes_stale_shell_files(tmp_path: Path) -> None:
    project_dir = tmp_path / "production"
    shell_root = project_dir.parent
    shell_bundle_dir = tmp_path / "shell-bundle"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    shell_bundle_dir.mkdir()
    bin_dir.mkdir()
    (project_dir / "docker-compose.production.yaml").write_text("services: {}\n", encoding="utf-8")
    (project_dir / ".env").write_text(
        "\n".join(
            [
                "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate",  # pragma: allowlist secret
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (shell_bundle_dir / "frontend").mkdir()
    (shell_bundle_dir / "frontend" / "bundle-marker.txt").write_text(
        "frontend-sync\n", encoding="utf-8"
    )
    (shell_bundle_dir / "deploy").mkdir()
    (shell_bundle_dir / "deploy" / "Caddyfile.production").write_text(
        'pulseplate.test {\n    respond "ok"\n}\n',
        encoding="utf-8",
    )
    (shell_bundle_dir / "deploy" / "docker-compose.production.yaml").write_text(
        PRODUCTION_COMPOSE_TEXT, encoding="utf-8"
    )
    (shell_bundle_dir / "scripts").mkdir()
    (shell_bundle_dir / "scripts" / "diagnose_web.sh").write_text(
        "#!/usr/bin/env bash\nprintf 'bundle-diagnose\\n'\n", encoding="utf-8"
    )
    (shell_bundle_dir / "scripts" / "redeploy_caddy.sh").write_text(
        "#!/usr/bin/env bash\nprintf 'bundle-redeploy\\n'\n", encoding="utf-8"
    )
    (shell_root / "frontend").mkdir()
    (shell_root / "frontend" / "stale.txt").write_text("old-shell\n", encoding="utf-8")
    (project_dir / "scripts").mkdir()
    (project_dir / "scripts" / "diagnose_web.sh").write_text("stale-diagnose\n", encoding="utf-8")
    (project_dir / "scripts" / "redeploy_caddy.sh").write_text("stale-redeploy\n", encoding="utf-8")

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
case "$*" in
  *"compose --env-file "*"-f docker-compose.production.yaml ps -q app"*)
    printf 'app-id\\n'
    ;;
  *"inspect --format "*)
    printf 'healthy\\n'
    ;;
  *"ps --format "*)
    printf 'CONTAINER ID\\n'
    ;;
esac
"""
    curl_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'curl %s\\n' "$*" >> "{log_file}"
"""
    sleep_stub = "#!/usr/bin/env bash\nset -euo pipefail\n"
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)
    _write_executable(bin_dir / "sleep", sleep_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = "docker-compose.production.yaml"
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"
    env["PRODUCTION_DOMAIN"] = "pulseplate.test"
    env["SHELL_BUNDLE_DIR"] = str(shell_bundle_dir)

    subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert (shell_root / "frontend" / "bundle-marker.txt").read_text(
        encoding="utf-8"
    ) == "frontend-sync\n"
    assert (
        (project_dir / "Caddyfile.production")
        .read_text(encoding="utf-8")
        .startswith("pulseplate.test")
    )
    assert (project_dir / "docker-compose.production.yaml").read_text(
        encoding="utf-8"
    ) == PRODUCTION_COMPOSE_TEXT
    assert not (shell_root / "frontend" / "stale.txt").exists()
    assert (project_dir / "scripts" / "diagnose_web.sh").read_text(
        encoding="utf-8"
    ) == "#!/usr/bin/env bash\nprintf 'bundle-diagnose\\n'\n"
    assert (project_dir / "scripts" / "redeploy_caddy.sh").read_text(
        encoding="utf-8"
    ) == "#!/usr/bin/env bash\nprintf 'bundle-redeploy\\n'\n"


def test_deploy_production_syncs_shell_bundle_with_autodetected_compose_file(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "production"
    shell_root = project_dir.parent
    shell_bundle_dir = tmp_path / "shell-bundle"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    shell_bundle_dir.mkdir()
    bin_dir.mkdir()
    (project_dir / "docker-compose.production.yaml").write_text("services: {}\n", encoding="utf-8")
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )
    (shell_bundle_dir / "frontend").mkdir()
    (shell_bundle_dir / "frontend" / "bundle-marker.txt").write_text(
        "frontend-sync\n", encoding="utf-8"
    )
    (shell_bundle_dir / "deploy").mkdir()
    (shell_bundle_dir / "deploy" / "Caddyfile.production").write_text(
        'pulseplate.test {\n    respond "ok"\n}\n',
        encoding="utf-8",
    )
    (shell_bundle_dir / "deploy" / "docker-compose.production.yaml").write_text(
        PRODUCTION_COMPOSE_TEXT, encoding="utf-8"
    )
    (shell_bundle_dir / "scripts").mkdir()
    (shell_bundle_dir / "scripts" / "diagnose_web.sh").write_text(
        "#!/usr/bin/env bash\nprintf 'bundle-diagnose\\n'\n", encoding="utf-8"
    )
    (shell_bundle_dir / "scripts" / "redeploy_caddy.sh").write_text(
        "#!/usr/bin/env bash\nprintf 'bundle-redeploy\\n'\n", encoding="utf-8"
    )

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
case "$*" in
  *"compose --env-file "*"-f docker-compose.production.yaml ps -q app"*)
    printf 'app-id\\n'
    ;;
  *"inspect --format "*)
    printf 'healthy\\n'
    ;;
  *"ps --format "*)
    printf 'CONTAINER ID\\n'
    ;;
esac
"""
    curl_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'curl %s\\n' "$*" >> "{log_file}"
"""
    sleep_stub = "#!/usr/bin/env bash\nset -euo pipefail\n"
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)
    _write_executable(bin_dir / "sleep", sleep_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env.pop("COMPOSE_FILE", None)
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"
    env["PRODUCTION_DOMAIN"] = "pulseplate.test"
    env["SHELL_BUNDLE_DIR"] = str(shell_bundle_dir)

    subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert (project_dir / "docker-compose.production.yaml").read_text(
        encoding="utf-8"
    ) == PRODUCTION_COMPOSE_TEXT
    assert (project_dir / "scripts" / "diagnose_web.sh").read_text(
        encoding="utf-8"
    ) == "#!/usr/bin/env bash\nprintf 'bundle-diagnose\\n'\n"
    assert (project_dir / "scripts" / "redeploy_caddy.sh").read_text(
        encoding="utf-8"
    ) == "#!/usr/bin/env bash\nprintf 'bundle-redeploy\\n'\n"


def test_deploy_production_syncs_shell_bundle_with_relative_compose_subpath(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "production"
    shell_root = project_dir.parent
    shell_bundle_dir = tmp_path / "shell-bundle"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    (project_dir / "deploy").mkdir()
    shell_bundle_dir.mkdir()
    bin_dir.mkdir()
    (project_dir / "deploy" / "docker-compose.production.yaml").write_text(
        "services: {}\n",
        encoding="utf-8",
    )
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )
    (shell_bundle_dir / "frontend").mkdir()
    (shell_bundle_dir / "frontend" / "bundle-marker.txt").write_text(
        "frontend-sync\n", encoding="utf-8"
    )
    (shell_bundle_dir / "deploy").mkdir()
    (shell_bundle_dir / "deploy" / "Caddyfile.production").write_text(
        'pulseplate.test {\n    respond "ok"\n}\n',
        encoding="utf-8",
    )
    (shell_bundle_dir / "deploy" / "docker-compose.production.yaml").write_text(
        "services:\n  app:\n    image: ghcr.io/example/pulseplate:test\n",
        encoding="utf-8",
    )
    (shell_bundle_dir / "scripts").mkdir()
    (shell_bundle_dir / "scripts" / "diagnose_web.sh").write_text(
        "#!/usr/bin/env bash\nprintf 'bundle-diagnose\\n'\n", encoding="utf-8"
    )
    (shell_bundle_dir / "scripts" / "redeploy_caddy.sh").write_text(
        "#!/usr/bin/env bash\nprintf 'bundle-redeploy\\n'\n", encoding="utf-8"
    )

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
case "$*" in
  *"compose --env-file "*"-f deploy/docker-compose.production.yaml ps -q app"*)
    printf 'app-id\\n'
    ;;
  *"inspect --format "*)
    printf 'healthy\\n'
    ;;
  *"ps --format "*)
    printf 'CONTAINER ID\\n'
    ;;
esac
"""
    curl_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'curl %s\\n' "$*" >> "{log_file}"
"""
    sleep_stub = "#!/usr/bin/env bash\nset -euo pipefail\n"
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)
    _write_executable(bin_dir / "sleep", sleep_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = "deploy/docker-compose.production.yaml"
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"
    env["PRODUCTION_DOMAIN"] = "pulseplate.test"
    env["SHELL_BUNDLE_DIR"] = str(shell_bundle_dir)

    subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert (project_dir / "deploy" / "docker-compose.production.yaml").read_text(
        encoding="utf-8"
    ) == "services:\n  app:\n    image: ghcr.io/example/pulseplate:test\n"
    assert (project_dir / "scripts" / "diagnose_web.sh").read_text(
        encoding="utf-8"
    ) == "#!/usr/bin/env bash\nprintf 'bundle-diagnose\\n'\n"
    assert (project_dir / "scripts" / "redeploy_caddy.sh").read_text(
        encoding="utf-8"
    ) == "#!/usr/bin/env bash\nprintf 'bundle-redeploy\\n'\n"


def test_deploy_production_autodetects_deploy_subdir_compose_and_env_file(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "production"
    deploy_dir = project_dir / "deploy"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    deploy_dir.mkdir()
    bin_dir.mkdir()
    (deploy_dir / "docker-compose.production.yaml").write_text("services: {}\n", encoding="utf-8")
    (deploy_dir / ".env").write_text(
        "\n".join(
            [
                "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate",  # pragma: allowlist secret
                "PRODUCTION_DOMAIN=pulseplate.test",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
case "$*" in
  *"compose --env-file "*"/deploy/.env -f deploy/docker-compose.production.yaml ps -q app"*)
    printf 'app-id\\n'
    ;;
  *"inspect --format "*)
    printf 'healthy\\n'
    ;;
  *"ps --format "*)
    printf 'CONTAINER ID\\n'
    ;;
esac
"""
    curl_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'curl %s\\n' "$*" >> "{log_file}"
"""
    sleep_stub = "#!/usr/bin/env bash\nset -euo pipefail\n"
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)
    _write_executable(bin_dir / "sleep", sleep_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env.pop("COMPOSE_FILE", None)
    env.pop("ENV_FILE", None)
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"

    subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any(
        "compose --env-file" in line
        and f"{deploy_dir / '.env'} -f deploy/docker-compose.production.yaml pull app" in line
        for line in log_lines
    )
    assert any(
        "compose --env-file" in line
        and f"{deploy_dir / '.env'} -f deploy/docker-compose.production.yaml up -d --remove-orphans caddy"
        in line
        for line in log_lines
    )


def test_deploy_production_uses_deploy_env_file_for_absolute_deploy_compose_path(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "production"
    deploy_dir = project_dir / "deploy"
    compose_file = deploy_dir / "docker-compose.production.yaml"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    deploy_dir.mkdir()
    bin_dir.mkdir()
    compose_file.write_text("services: {}\n", encoding="utf-8")
    (deploy_dir / ".env").write_text(
        "\n".join(
            [
                "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate",  # pragma: allowlist secret
                "PRODUCTION_DOMAIN=pulseplate.test",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
case "$*" in
  *"compose --env-file "*"/deploy/.env -f {compose_file} ps -q app"*)
    printf 'app-id\\n'
    ;;
  *"inspect --format "*)
    printf 'healthy\\n'
    ;;
  *"ps --format "*)
    printf 'CONTAINER ID\\n'
    ;;
esac
"""
    curl_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'curl %s\\n' "$*" >> "{log_file}"
"""
    sleep_stub = "#!/usr/bin/env bash\nset -euo pipefail\n"
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)
    _write_executable(bin_dir / "sleep", sleep_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["COMPOSE_FILE"] = str(compose_file)
    env.pop("ENV_FILE", None)
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"

    subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any(
        "compose --env-file" in line and f"{deploy_dir / '.env'} -f {compose_file} pull app" in line
        for line in log_lines
    )
    assert any(
        "compose --env-file" in line
        and f"{deploy_dir / '.env'} -f {compose_file} up -d --remove-orphans caddy" in line
        for line in log_lines
    )


def test_deploy_production_rejects_compose_file_outside_deploy_dir_during_shell_sync(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "production"
    shell_root = project_dir.parent
    shell_bundle_dir = tmp_path / "shell-bundle"
    outside_dir = tmp_path / "outside"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    shell_bundle_dir.mkdir()
    outside_dir.mkdir()
    bin_dir.mkdir()
    (project_dir / ".env").write_text(
        "\n".join(
            [
                "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate",  # pragma: allowlist secret
                "PRODUCTION_DOMAIN=pulseplate.test",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (outside_dir / "docker-compose.production.yaml").write_text("services: {}\n", encoding="utf-8")
    (shell_bundle_dir / "frontend").mkdir()
    (shell_bundle_dir / "frontend" / "bundle-marker.txt").write_text(
        "frontend-sync\n", encoding="utf-8"
    )
    (shell_bundle_dir / "deploy").mkdir()
    (shell_bundle_dir / "deploy" / "Caddyfile.production").write_text(
        'pulseplate.test {\n    respond "ok"\n}\n',
        encoding="utf-8",
    )
    (shell_bundle_dir / "scripts").mkdir()
    (shell_bundle_dir / "scripts" / "diagnose_web.sh").write_text(
        "#!/usr/bin/env bash\nprintf 'bundle-diagnose\\n'\n", encoding="utf-8"
    )
    (shell_bundle_dir / "scripts" / "redeploy_caddy.sh").write_text(
        "#!/usr/bin/env bash\nprintf 'bundle-redeploy\\n'\n", encoding="utf-8"
    )

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
case "$*" in
  *"ps -q app"*)
    printf 'app-id\\n'
    ;;
  *"inspect --format "*)
    printf 'healthy\\n'
    ;;
  *"ps --format "*)
    printf 'CONTAINER ID\\n'
    ;;
esac
"""
    curl_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'curl %s\\n' "$*" >> "{log_file}"
"""
    sleep_stub = "#!/usr/bin/env bash\nset -euo pipefail\n"
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)
    _write_executable(bin_dir / "sleep", sleep_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = str(outside_dir / "docker-compose.production.yaml")
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"
    env["SHELL_BUNDLE_DIR"] = str(shell_bundle_dir)

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "COMPOSE_FILE must stay within DEPLOY_DIR" in completed.stderr


def test_deploy_production_exits_non_zero_when_migrations_fail(tmp_path: Path) -> None:
    project_dir = tmp_path / "production"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    bin_dir.mkdir()
    (project_dir / "docker-compose.production.yaml").write_text("services: {}\n", encoding="utf-8")
    (project_dir / ".env").write_text(
        "\n".join(
            [
                "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate",  # pragma: allowlist secret
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
case "$*" in
  *"compose --env-file "*"-f docker-compose.production.yaml ps -q app"*)
    printf 'app-id\\n'
    ;;
  *"inspect --format "*)
    printf 'healthy\\n'
    ;;
  *"compose --env-file "*"-f docker-compose.production.yaml run --rm --no-deps app alembic upgrade head"*)
    printf 'migration failed\\n' >&2
    exit 1
    ;;
  *"ps --format "*)
    printf 'CONTAINER ID\\n'
    ;;
esac
"""
    curl_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'curl %s\\n' "$*" >> "{log_file}"
"""
    sleep_stub = "#!/usr/bin/env bash\nset -euo pipefail\n"
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)
    _write_executable(bin_dir / "sleep", sleep_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = "docker-compose.production.yaml"
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"
    env["PRODUCTION_DOMAIN"] = "pulseplate.test"

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "Database migrations failed (exit code: 1)" in completed.stderr

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any("run --rm --no-deps app alembic upgrade head" in line for line in log_lines)
    assert all("up -d --remove-orphans app" not in line for line in log_lines)
    assert all("up -d --remove-orphans caddy" not in line for line in log_lines)
    assert not any(
        line.startswith("curl ") and "https://pulseplate.test/ready" in line for line in log_lines
    )


def test_deploy_production_keeps_shell_bundle_untouched_when_migrations_fail(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "production"
    shell_root = project_dir.parent
    shell_bundle_dir = tmp_path / "shell-bundle"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    shell_bundle_dir.mkdir()
    bin_dir.mkdir()
    (project_dir / "docker-compose.production.yaml").write_text("services: {}\n", encoding="utf-8")
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )
    (shell_bundle_dir / "frontend").mkdir()
    (shell_bundle_dir / "frontend" / "bundle-marker.txt").write_text(
        "frontend-sync\n", encoding="utf-8"
    )
    (shell_bundle_dir / "deploy").mkdir()
    (shell_bundle_dir / "deploy" / "Caddyfile.production").write_text(
        'pulseplate.test {\n    respond "ok"\n}\n',
        encoding="utf-8",
    )
    (shell_bundle_dir / "deploy" / "docker-compose.production.yaml").write_text(
        PRODUCTION_COMPOSE_TEXT, encoding="utf-8"
    )
    (shell_bundle_dir / "scripts").mkdir()
    (shell_bundle_dir / "scripts" / "diagnose_web.sh").write_text(
        "#!/usr/bin/env bash\nprintf 'bundle-diagnose\\n'\n", encoding="utf-8"
    )
    (shell_bundle_dir / "scripts" / "redeploy_caddy.sh").write_text(
        "#!/usr/bin/env bash\nprintf 'bundle-redeploy\\n'\n", encoding="utf-8"
    )
    (shell_root / "frontend").mkdir()
    (shell_root / "frontend" / "stale.txt").write_text("old-shell\n", encoding="utf-8")
    (project_dir / "scripts").mkdir()
    (project_dir / "scripts" / "diagnose_web.sh").write_text("stale-diagnose\n", encoding="utf-8")
    (project_dir / "scripts" / "redeploy_caddy.sh").write_text("stale-redeploy\n", encoding="utf-8")

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
case "$*" in
  *"compose --env-file "*"-f docker-compose.production.yaml run --rm --no-deps app alembic upgrade head"*)
    printf 'migration failed\\n' >&2
    exit 1
    ;;
esac
"""
    curl_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'curl %s\\n' "$*" >> "{log_file}"
"""
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = "docker-compose.production.yaml"
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"
    env["PRODUCTION_DOMAIN"] = "pulseplate.test"
    env["SHELL_BUNDLE_DIR"] = str(shell_bundle_dir)

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert (shell_root / "frontend" / "stale.txt").read_text(encoding="utf-8") == "old-shell\n"
    assert not (shell_root / "frontend" / "bundle-marker.txt").exists()
    assert (project_dir / "scripts" / "diagnose_web.sh").read_text(
        encoding="utf-8"
    ) == "stale-diagnose\n"
    assert (project_dir / "scripts" / "redeploy_caddy.sh").read_text(
        encoding="utf-8"
    ) == "stale-redeploy\n"


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql+psycopg://pulseplate:secret@postgres:5432/pulseplate",  # pragma: allowlist secret
        "postgresql+psycopg://pulseplate:secret@postgres/pulseplate",  # pragma: allowlist secret
        "postgresql+psycopg://pulseplate:secret@postgres:6543/pulseplate",  # pragma: allowlist secret
    ],
)
def test_deploy_production_rejects_compose_local_postgres_dsn(
    tmp_path: Path,
    database_url: str,
) -> None:
    project_dir = tmp_path / "production"
    bin_dir = tmp_path / "bin"
    project_dir.mkdir()
    bin_dir.mkdir()
    (project_dir / "docker-compose.production.yaml").write_text("services: {}\n", encoding="utf-8")
    (project_dir / ".env").write_text(
        f"DATABASE_URL={database_url}\n",
        encoding="utf-8",
    )

    docker_stub = "#!/usr/bin/env bash\nset -euo pipefail\nexit 0\n"
    _write_executable(bin_dir / "docker", docker_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = "docker-compose.production.yaml"
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"
    env["PRODUCTION_DOMAIN"] = "pulseplate.test"

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "external managed PostgreSQL" in completed.stderr


def test_deploy_production_rejects_compose_with_local_postgres_reference(tmp_path: Path) -> None:
    project_dir = tmp_path / "production"
    bin_dir = tmp_path / "bin"
    project_dir.mkdir()
    bin_dir.mkdir()
    (project_dir / "docker-compose.production.yaml").write_text(
        "services:\n  app:\n    depends_on:\n      postgres:\n        condition: service_healthy\n  postgres:\n    image: postgres:16\n",
        encoding="utf-8",
    )
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )

    docker_stub = "#!/usr/bin/env bash\nset -euo pipefail\nexit 0\n"
    _write_executable(bin_dir / "docker", docker_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = "docker-compose.production.yaml"
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"
    env["PRODUCTION_DOMAIN"] = "pulseplate.test"

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "still references local postgres" in completed.stderr


def test_deploy_production_does_not_require_home_when_docker_bin_is_explicit(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "production"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    bin_dir.mkdir()
    (project_dir / "docker-compose.production.yaml").write_text("services: {}\n", encoding="utf-8")
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
case "$*" in
  *"compose --env-file "*"-f docker-compose.production.yaml ps -q app"*)
    printf 'app-id\\n'
    ;;
  *"inspect --format "*)
    printf 'healthy\\n'
    ;;
  *"ps --format "*)
    printf 'CONTAINER ID\\n'
    ;;
esac
"""
    curl_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'curl %s\\n' "$*" >> "{log_file}"
"""
    sleep_stub = "#!/usr/bin/env bash\nset -euo pipefail\n"
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)
    _write_executable(bin_dir / "sleep", sleep_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env.pop("HOME", None)
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = "docker-compose.production.yaml"
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"
    env["PRODUCTION_DOMAIN"] = "pulseplate.test"

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Deploy dir:" in completed.stdout
    assert "compose --env-file" in log_file.read_text(encoding="utf-8")


def test_deploy_production_rejects_relative_docker_bin_override(tmp_path: Path) -> None:
    project_dir = tmp_path / "production"
    project_dir.mkdir()
    (project_dir / "docker-compose.production.yaml").write_text("services: {}\n", encoding="utf-8")
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["DOCKER_BIN"] = "docker"
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = "docker-compose.production.yaml"
    env["IMAGE_REF"] = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test"
    env["TAG"] = "prod-vtest"
    env["PRODUCTION_DOMAIN"] = "pulseplate.test"

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "DOCKER_BIN must be an absolute path" in completed.stderr


def test_diagnose_web_reports_green_for_spa_and_api_contract(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "diag.log"
    bin_dir.mkdir()

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
exit 0
"""
    curl_stub = """#!/usr/bin/env bash
set -euo pipefail
headers=""
body=""
    url=""
    method="GET"
while [[ $# -gt 0 ]]; do
  case "$1" in
    -X)
      method="$2"
      shift 2
      ;;
    -D)
      headers="$2"
      shift 2
      ;;
    -o)
      body="$2"
      shift 2
      ;;
    http://*|https://*)
      url="$1"
      shift
      ;;
    *)
      shift
      ;;
  esac
done

status="418"
content_type="text/plain"
payload="unexpected"
case "$method:$url" in
  GET:https://pulseplate.test/|GET:https://pulseplate.test/bmi|GET:https://pulseplate.test/profile|GET:https://pulseplate.test/plate|GET:https://pulseplate.test/progress)
    status="200"
    content_type="text/html; charset=utf-8"
    payload='<!doctype html><html><head><link rel="stylesheet" href="/assets/index-test.css"></head><body><div id="root"></div></body></html>'
    ;;
  GET:https://pulseplate.test/assets/index-test.css)
    status="200"
    content_type="text/css"
    payload='.grid{display:grid}.min-h-screen{min-height:100vh}.rounded-2xl{border-radius:1rem}'
    ;;
  GET:https://pulseplate.test/health|GET:https://pulseplate.test/openapi.json)
    status="200"
    content_type="application/json"
    payload='{"ok": true}'
    ;;
  GET:https://pulseplate.test/sitemap.xml)
    status="200"
    content_type="application/xml"
    payload='<?xml version="1.0" encoding="UTF-8"?><urlset><url><loc>https://pulseplate.test/</loc></url></urlset>'
    ;;
  POST:https://pulseplate.test/bmi)
    status="422"
    content_type="application/json"
    payload='{"detail": "validation"}'
    ;;
  OPTIONS:https://pulseplate.test/bmi)
    status="405"
    content_type="application/json"
    payload='{"detail": "Method Not Allowed"}'
    ;;
  GET:https://pulseplate.test/plan|GET:https://pulseplate.test/insight|GET:https://pulseplate.test/premium_bmr|GET:https://pulseplate.test/premium_targets|GET:https://pulseplate.test/api/v1/does-not-exist)
    status="404"
    content_type="application/json"
    payload='{"detail": "not found"}'
    ;;
  GET:https://pulseplate.test/api/v1/admin/status)
    status="403"
    content_type="application/json"
    payload='{"detail": "forbidden"}'
    ;;
  GET:https://pulseplate.test/legacy/bmi-calculator)
    status="200"
    content_type="text/html; charset=utf-8"
    payload='<!doctype html><html><body><h1>Legacy calculator</h1></body></html>'
    ;;
  GET:https://pulseplate.test/ws)
    status="400"
    content_type="text/plain"
    payload='upgrade required'
    ;;
esac

printf 'HTTP/1.1 %s Stub\\nContent-Type: %s\\n\\n' "$status" "$content_type" > "$headers"
printf '%s' "$payload" > "$body"
printf '%s' "$status"
"""
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"

    completed = subprocess.run(
        [
            "bash",
            str(REPO_ROOT / "scripts/diagnose_web.sh"),
            "--skip-caddy-validate",
            "--base-url",
            "https://pulseplate.test",
        ],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "PASS: spa-bmi: /bmi serves the SPA shell with HTTP 200." in completed.stdout
    assert (
        "PASS: static-css: /assets/index-test.css is public CSS with HTTP 200." in completed.stdout
    )
    assert "PASS: health-json: /health reaches the JSON backend surface." in completed.stdout
    assert "PASS: sitemap-xml: /sitemap.xml reaches the XML sitemap surface." in completed.stdout
    assert (
        "PASS: legacy-bmi-post: /bmi reached the backend JSON surface (status 422)."
        in completed.stdout
    )
    assert "PASS: legacy-bmi-options: /bmi stayed off SPA/static-405" in completed.stdout
    assert "PASS: legacy-plan-get: /plan stayed off the SPA shell" in completed.stdout
    assert "PASS: legacy-insight-get: /insight stayed off the SPA shell" in completed.stdout
    assert (
        "PASS: legacy-bmi-calculator-get: /legacy/bmi-calculator stayed off the SPA shell"
        in completed.stdout
    )
    assert (
        "PASS: api-prefix: /api/v1/does-not-exist reached the backend JSON surface"
        in completed.stdout
    )
    assert (
        "PASS: admin-canary: /api/v1/admin/status reached the admin/backend canary surface"
        in completed.stdout
    )
    assert "PASS: websocket-upgrade: /ws did not fall through to SPA" in completed.stdout
    assert "Summary: all requested checks passed." in completed.stdout


def test_diagnose_web_uses_cloudflare_access_service_token_headers(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "diag-access.log"
    bin_dir.mkdir()

    docker_stub = "#!/usr/bin/env bash\nset -euo pipefail\nexit 0\n"
    curl_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'curl %s\\n' "$*" >> "{log_file}"
headers=""
body=""
url=""
method="GET"
while [[ $# -gt 0 ]]; do
  case "$1" in
    -X)
      method="$2"
      shift 2
      ;;
    -D)
      headers="$2"
      shift 2
      ;;
    -o)
      body="$2"
      shift 2
      ;;
    http://*|https://*)
      url="$1"
      shift
      ;;
    *)
      shift
      ;;
  esac
done

status="418"
content_type="text/plain"
payload="unexpected"
case "$method:$url" in
  GET:https://pulseplate.test/|GET:https://pulseplate.test/bmi|GET:https://pulseplate.test/profile|GET:https://pulseplate.test/plate|GET:https://pulseplate.test/progress)
    status="200"
    content_type="text/html; charset=utf-8"
    payload='<!doctype html><html><head><link rel="stylesheet" href="/assets/index-test.css"></head><body><div id="root"></div></body></html>'
    ;;
  GET:https://pulseplate.test/assets/index-test.css)
    status="200"
    content_type="text/css"
    payload='.grid{{display:grid}}.min-h-screen{{min-height:100vh}}.rounded-2xl{{border-radius:1rem}}'
    ;;
  GET:https://pulseplate.test/health|GET:https://pulseplate.test/openapi.json)
    status="200"
    content_type="application/json"
    payload='{{"ok": true}}'
    ;;
  GET:https://pulseplate.test/sitemap.xml)
    status="200"
    content_type="application/xml"
    payload='<?xml version="1.0" encoding="UTF-8"?><urlset><url><loc>https://pulseplate.test/</loc></url></urlset>'
    ;;
  POST:https://pulseplate.test/bmi)
    status="422"
    content_type="application/json"
    payload='{{"detail": "validation"}}'
    ;;
  OPTIONS:https://pulseplate.test/bmi)
    status="405"
    content_type="application/json"
    payload='{{"detail": "Method Not Allowed"}}'
    ;;
  GET:https://pulseplate.test/plan|GET:https://pulseplate.test/insight|GET:https://pulseplate.test/premium_bmr|GET:https://pulseplate.test/premium_targets|GET:https://pulseplate.test/api/v1/does-not-exist)
    status="404"
    content_type="application/json"
    payload='{{"detail": "not found"}}'
    ;;
  GET:https://pulseplate.test/api/v1/admin/status)
    status="403"
    content_type="application/json"
    payload='{{"detail": "forbidden"}}'
    ;;
  GET:https://pulseplate.test/legacy/bmi-calculator)
    status="200"
    content_type="text/html; charset=utf-8"
    payload='<!doctype html><html><body><h1>Legacy calculator</h1></body></html>'
    ;;
  GET:https://pulseplate.test/ws)
    status="400"
    content_type="text/plain"
    payload='upgrade required'
    ;;
esac

printf 'HTTP/1.1 %s Stub\\nContent-Type: %s\\n\\n' "$status" "$content_type" > "$headers"
printf '%s' "$payload" > "$body"
printf '%s' "$status"
"""
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["CF_ACCESS_CLIENT_ID"] = "client-id"
    env["CF_ACCESS_CLIENT_SECRET"] = "client-secret"  # pragma: allowlist secret

    completed = subprocess.run(
        [
            "bash",
            str(REPO_ROOT / "scripts/diagnose_web.sh"),
            "--skip-caddy-validate",
            "--base-url",
            "https://pulseplate.test",
        ],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    log_output = log_file.read_text(encoding="utf-8")
    assert "-H CF-Access-Client-Id: client-id" in log_output
    assert "-H CF-Access-Client-Secret: client-secret" in log_output
    assert (
        "PASS: Cloudflare Access service-token headers enabled for private probes."
        in completed.stdout
    )


def test_diagnose_web_fails_when_admin_canary_route_is_missing(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    docker_stub = "#!/usr/bin/env bash\nset -euo pipefail\nexit 0\n"
    curl_stub = """#!/usr/bin/env bash
set -euo pipefail
headers=""
body=""
url=""
method="GET"
while [[ $# -gt 0 ]]; do
  case "$1" in
    -X)
      method="$2"
      shift 2
      ;;
    -D)
      headers="$2"
      shift 2
      ;;
    -o)
      body="$2"
      shift 2
      ;;
    http://*|https://*)
      url="$1"
      shift
      ;;
    *)
      shift
      ;;
  esac
done

status="418"
content_type="text/plain"
payload="unexpected"
case "$method:$url" in
  GET:https://pulseplate.test/|GET:https://pulseplate.test/bmi|GET:https://pulseplate.test/profile|GET:https://pulseplate.test/plate|GET:https://pulseplate.test/progress)
    status="200"
    content_type="text/html; charset=utf-8"
    payload='<!doctype html><html><head><link rel="stylesheet" href="/assets/index-test.css"></head><body><div id="root"></div></body></html>'
    ;;
  GET:https://pulseplate.test/assets/index-test.css)
    status="200"
    content_type="text/css"
    payload='.grid{display:grid}.min-h-screen{min-height:100vh}.rounded-2xl{border-radius:1rem}'
    ;;
  GET:https://pulseplate.test/health|GET:https://pulseplate.test/openapi.json)
    status="200"
    content_type="application/json"
    payload='{"ok": true}'
    ;;
  GET:https://pulseplate.test/sitemap.xml)
    status="200"
    content_type="application/xml"
    payload='<?xml version="1.0" encoding="UTF-8"?><urlset><url><loc>https://pulseplate.test/</loc></url></urlset>'
    ;;
  POST:https://pulseplate.test/bmi)
    status="422"
    content_type="application/json"
    payload='{"detail": "validation"}'
    ;;
  OPTIONS:https://pulseplate.test/bmi)
    status="405"
    content_type="application/json"
    payload='{"detail": "Method Not Allowed"}'
    ;;
  GET:https://pulseplate.test/plan|GET:https://pulseplate.test/insight|GET:https://pulseplate.test/premium_bmr|GET:https://pulseplate.test/premium_targets|GET:https://pulseplate.test/api/v1/does-not-exist|GET:https://pulseplate.test/api/v1/admin/status)
    status="404"
    content_type="application/json"
    payload='{"detail": "not found"}'
    ;;
  GET:https://pulseplate.test/legacy/bmi-calculator)
    status="200"
    content_type="text/html; charset=utf-8"
    payload='<!doctype html><html><body><h1>Legacy calculator</h1></body></html>'
    ;;
  GET:https://pulseplate.test/ws)
    status="400"
    content_type="text/plain"
    payload='upgrade required'
    ;;
esac

printf 'HTTP/1.1 %s Stub\\nContent-Type: %s\\n\\n' "$status" "$content_type" > "$headers"
printf '%s' "$payload" > "$body"
printf '%s' "$status"
"""
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"

    completed = subprocess.run(
        [
            "bash",
            str(REPO_ROOT / "scripts/diagnose_web.sh"),
            "--skip-caddy-validate",
            "--base-url",
            "https://pulseplate.test",
        ],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert (
        "FAIL: admin-canary: /api/v1/admin/status returned 404, so the admin canary route is missing or misrouted."
        in completed.stdout
    )


def test_diagnose_web_rejects_partial_cloudflare_access_service_token_env(
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    docker_stub = "#!/usr/bin/env bash\nset -euo pipefail\nexit 0\n"
    _write_executable(bin_dir / "docker", docker_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["CF_ACCESS_CLIENT_ID"] = "client-id"
    env.pop("CF_ACCESS_CLIENT_SECRET", None)

    completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/diagnose_web.sh"), "--check-caddy-config-only"],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert (
        "FAIL: CF_ACCESS_CLIENT_ID and CF_ACCESS_CLIENT_SECRET must be provided together"
        in completed.stdout
    )


def test_diagnose_web_fails_without_base_url_for_http_probes(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    docker_stub = "#!/usr/bin/env bash\nset -euo pipefail\nexit 0\n"
    _write_executable(bin_dir / "docker", docker_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env.pop("BASE_URL", None)
    env.pop("PRODUCTION_DOMAIN", None)

    completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/diagnose_web.sh"), "--skip-caddy-validate"],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "FAIL: BASE_URL or PRODUCTION_DOMAIN is required for HTTP probes." in completed.stdout


def test_diagnose_web_warns_when_docker_daemon_is_unavailable(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    docker_stub = """#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "info" ]]; then
  exit 1
fi
exit 0
"""
    _write_executable(bin_dir / "docker", docker_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"

    completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/diagnose_web.sh"), "--check-caddy-config-only"],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert (
        "WARN: Docker daemon/socket is unavailable; skipping local Caddyfile validation."
        in completed.stdout
    )


def test_diagnose_web_reports_failure_for_spa_or_api_contract(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "diag-fail.log"
    bin_dir.mkdir()

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
exit 0
"""
    curl_stub = """#!/usr/bin/env bash
set -euo pipefail
headers=""
body=""
url=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -D)
      headers="$2"
      shift 2
      ;;
    -o)
      body="$2"
      shift 2
      ;;
    http://*|https://*)
      url="$1"
      shift
      ;;
    *)
      shift
      ;;
  esac
done

status="200"
content_type="text/html; charset=utf-8"
payload='<!doctype html><html><body><h1>maintenance</h1></body></html>'

if [[ "$url" == "https://pulseplate.test/health" ]]; then
  status="500"
  content_type="text/html; charset=utf-8"
  payload='<html><body>error</body></html>'
elif [[ "$url" == "https://pulseplate.test/openapi.json" ]]; then
  status="200"
  content_type="application/json"
  payload='{"ok": true}'
elif [[ "$url" == "https://pulseplate.test/ws" ]]; then
  status="400"
  content_type="text/plain"
  payload='upgrade required'
fi

printf 'HTTP/1.1 %s Stub\\nContent-Type: %s\\n\\n' "$status" "$content_type" > "$headers"
printf '%s' "$payload" > "$body"
printf '%s' "$status"
"""
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"

    completed = subprocess.run(
        [
            "bash",
            str(REPO_ROOT / "scripts/diagnose_web.sh"),
            "--skip-caddy-validate",
            "--base-url",
            "https://pulseplate.test",
        ],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "FAIL: spa-root: response does not contain the SPA shell marker." in completed.stdout
    assert "FAIL: health-json: expected HTTP 200, got 500." in completed.stdout


def test_redeploy_caddy_runs_diagnose_web_when_domain_is_available(tmp_path: Path) -> None:
    temp_repo = tmp_path / "repo"
    deploy_dir = temp_repo / "deploy"
    scripts_dir = temp_repo / "scripts"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "redeploy.log"
    temp_repo.mkdir()
    deploy_dir.mkdir()
    scripts_dir.mkdir()
    bin_dir.mkdir()

    (deploy_dir / "docker-compose.production.yaml").write_text("services: {}\n", encoding="utf-8")
    (deploy_dir / ".env").write_text('PRODUCTION_DOMAIN="pulseplate.test"\n', encoding="utf-8")

    diagnose_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'diagnose BASE_URL=%s ARGS=%s\\n' "${{BASE_URL:-}}" "$*" >> "{log_file}"
"""
    _write_executable(scripts_dir / "diagnose_web.sh", diagnose_stub)
    _write_executable(
        scripts_dir / "redeploy_caddy.sh",
        (REPO_ROOT / "scripts" / "redeploy_caddy.sh").read_text(encoding="utf-8"),
    )

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
if [[ "$*" == "compose version" ]]; then
  exit 0
fi
exit 0
"""
    _write_executable(bin_dir / "docker", docker_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DEPLOY_DIR"] = str(deploy_dir)
    env["DIAG_MAX_ATTEMPTS"] = "1"
    env["DIAG_RETRY_DELAY_SECONDS"] = "0"

    subprocess.run(
        ["bash", str(scripts_dir / "redeploy_caddy.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any(
        "docker compose -f docker-compose.production.yaml build caddy" in line for line in log_lines
    )
    assert any(
        "docker compose -f docker-compose.production.yaml up -d caddy" in line for line in log_lines
    )
    assert any(
        "diagnose BASE_URL=https://pulseplate.test ARGS=--skip-caddy-validate" in line
        for line in log_lines
    )


def test_redeploy_caddy_exits_non_zero_when_diagnosis_fails(tmp_path: Path) -> None:
    temp_repo = tmp_path / "repo"
    deploy_dir = temp_repo / "deploy"
    scripts_dir = temp_repo / "scripts"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "redeploy.log"
    temp_repo.mkdir()
    deploy_dir.mkdir()
    scripts_dir.mkdir()
    bin_dir.mkdir()

    (deploy_dir / "docker-compose.production.yaml").write_text("services: {}\n", encoding="utf-8")
    (deploy_dir / ".env").write_text('PRODUCTION_DOMAIN="pulseplate.test"\n', encoding="utf-8")

    diagnose_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'diagnose-fail BASE_URL=%s ARGS=%s\\n' "${{BASE_URL:-}}" "$*" >> "{log_file}"
exit 1
"""
    _write_executable(scripts_dir / "diagnose_web.sh", diagnose_stub)
    _write_executable(
        scripts_dir / "redeploy_caddy.sh",
        (REPO_ROOT / "scripts" / "redeploy_caddy.sh").read_text(encoding="utf-8"),
    )

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
if [[ "$*" == "compose version" ]]; then
  exit 0
fi
exit 0
"""
    _write_executable(bin_dir / "docker", docker_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DEPLOY_DIR"] = str(deploy_dir)
    env["DIAG_MAX_ATTEMPTS"] = "2"
    env["DIAG_RETRY_DELAY_SECONDS"] = "0"

    completed = subprocess.run(
        ["bash", str(scripts_dir / "redeploy_caddy.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "❌ diagnose_web.sh reported a routing mismatch" in completed.stdout
