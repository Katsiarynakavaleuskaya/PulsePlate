import os
import stat
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


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
        message="Expected app docker-compose up step to appear in deploy log",
    )
    caddy_build_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "compose --env-file" in line and "build caddy" in line,
        message="Expected caddy docker-compose build step to appear in deploy log",
    )
    caddy_up_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "compose --env-file" in line
        and "up -d --remove-orphans caddy" in line,
        message="Expected caddy docker-compose up step to appear in deploy log",
    )
    external_ready_index = _assert_log_index(
        log_lines,
        predicate=lambda line: line.startswith("curl ") and "https://pulseplate.test/ready" in line,
        message="Expected external readiness check to appear in deploy log",
    )

    assert migrate_index < app_up_index < caddy_build_index < caddy_up_index < external_ready_index
    assert all("up -d --remove-orphans postgres" not in line for line in log_lines)
    assert all("helper " not in line for line in log_lines)


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
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
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
    (shell_bundle_dir / "scripts").mkdir()
    (shell_bundle_dir / "scripts" / "diagnose_web.sh").write_text(
        "#!/usr/bin/env bash\nprintf 'bundle-diagnose\\n'\n", encoding="utf-8"
    )
    (shell_root / "frontend").mkdir()
    (shell_root / "frontend" / "stale.txt").write_text("old-shell\n", encoding="utf-8")
    (shell_root / "scripts").mkdir()
    (shell_root / "scripts" / "diagnose_web.sh").write_text("stale-diagnose\n", encoding="utf-8")

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
    assert not (shell_root / "frontend" / "stale.txt").exists()
    assert (shell_root / "scripts" / "diagnose_web.sh").read_text(
        encoding="utf-8"
    ) == "#!/usr/bin/env bash\nprintf 'bundle-diagnose\\n'\n"


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
    (shell_bundle_dir / "scripts").mkdir()
    (shell_bundle_dir / "scripts" / "diagnose_web.sh").write_text(
        "#!/usr/bin/env bash\nprintf 'bundle-diagnose\\n'\n", encoding="utf-8"
    )
    (shell_root / "frontend").mkdir()
    (shell_root / "frontend" / "stale.txt").write_text("old-shell\n", encoding="utf-8")
    (shell_root / "scripts").mkdir()
    (shell_root / "scripts" / "diagnose_web.sh").write_text("stale-diagnose\n", encoding="utf-8")

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
    assert (shell_root / "scripts" / "diagnose_web.sh").read_text(
        encoding="utf-8"
    ) == "stale-diagnose\n"


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
    payload='<!doctype html><html><body><div id="root"></div></body></html>'
    ;;
  GET:https://pulseplate.test/health|GET:https://pulseplate.test/openapi.json)
    status="200"
    content_type="application/json"
    payload='{"ok": true}'
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
    assert "PASS: health-json: /health reaches the JSON backend surface." in completed.stdout
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
    assert "PASS: websocket-upgrade: /ws did not fall through to SPA" in completed.stdout
    assert "Summary: all requested checks passed." in completed.stdout


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
