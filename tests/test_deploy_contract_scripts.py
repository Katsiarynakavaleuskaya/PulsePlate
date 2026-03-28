import os
import stat
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


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
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
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
    scripts_dir = project_dir / "scripts" / "ops"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    bin_dir.mkdir()
    scripts_dir.mkdir(parents=True)
    (project_dir / "docker-compose.production.yaml").write_text("services: {}\n", encoding="utf-8")
    (project_dir / ".env").write_text(
        "\n".join(
            [
                "POSTGRES_USER=pulseplate",
                "POSTGRES_DB=pulseplate",
                "POSTGRES_PASSWORD=secret",
                "DATABASE_URL=postgresql+psycopg://pulseplate:secret@postgres:5432/pulseplate",  # pragma: allowlist secret
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    helper_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'helper %s %s\\n' "$PROJECT_DIR" "${{COMPOSE_FILE:-}}" >> "{log_file}"
"""
    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
case "$*" in
  *"compose --env-file "*"-f docker-compose.production.yaml ps -q postgres"*)
    printf 'postgres-id\\n'
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
    _write_executable(scripts_dir / "postgres_backup.sh", helper_stub)
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
    postgres_up_index = next(
        index
        for index, line in enumerate(log_lines)
        if "compose --env-file" in line and "up -d --remove-orphans postgres" in line
    )
    helper_index = next(index for index, line in enumerate(log_lines) if line.startswith("helper "))
    app_up_index = next(
        index
        for index, line in enumerate(log_lines)
        if "compose --env-file" in line and "up -d --remove-orphans app" in line
    )
    migrate_index = next(
        index for index, line in enumerate(log_lines) if "exec app-id alembic upgrade head" in line
    )
    caddy_up_index = next(
        index
        for index, line in enumerate(log_lines)
        if "compose --env-file" in line and "up -d --remove-orphans caddy" in line
    )
    external_ready_index = next(
        index
        for index, line in enumerate(log_lines)
        if line.startswith("curl ") and "https://pulseplate.test/ready" in line
    )

    assert (
        postgres_up_index
        < helper_index
        < app_up_index
        < migrate_index
        < caddy_up_index
        < external_ready_index
    )
    assert any("helper " in line and "docker-compose.production.yaml" in line for line in log_lines)
