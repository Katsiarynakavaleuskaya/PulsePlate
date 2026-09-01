import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tarfile
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CD_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "cd.yml"
PRODUCTION_COMPOSE_PATH = REPO_ROOT / "deploy" / "docker-compose.production.yaml"
PRODUCTION_COMPOSE_TEXT = PRODUCTION_COMPOSE_PATH.read_text(encoding="utf-8")
SELF_HOSTED_COMPOSE_PATH = REPO_ROOT / "deploy" / "docker-compose.production.selfhosted.yaml"
STAGING_COMPOSE_PATH = REPO_ROOT / "deploy" / "docker-compose.staging.yaml"
PROMETHEUS_CONFIG_PATH = REPO_ROOT / "deploy" / "prometheus" / "prometheus.yml"
PROMETHEUS_MANIFEST_PATH = REPO_ROOT / "deploy" / "prometheus" / "image-manifest.json"
PROMETHEUS_SOURCE_REVISION = "09fdfcd2659dd9c816e9e23c992fc161c0091757"
PROMETHEUS_INDEX_DIGEST = "sha256:1b88c17bf5f023ee6daf6bb1ee5605e1f69fd2df9e87fca3658949c44b0588ab"
PROMETHEUS_PLATFORM_MANIFEST_DIGEST = (
    "sha256:84f0d46e960e86b6965d2e4d99a06f92f176dd75a31ead99126a009891e00f22"
)
PROMETHEUS_RUNTIME_REF = f"prom/prometheus@{PROMETHEUS_PLATFORM_MANIFEST_DIGEST}"
FAKE_PROMETHEUS_COMPOSE_JSON = json.dumps(
    {
        "services": {
            "prometheus": {
                "image": PROMETHEUS_RUNTIME_REF,
                "platform": "linux/amd64",
            }
        }
    },
    separators=(",", ":"),
)
FAKE_PROMETHEUS_IMAGE_INSPECT_JSON = json.dumps(
    [
        {
            "Os": "linux",
            "Architecture": "amd64",
            "RepoDigests": [f"prom/prometheus@{PROMETHEUS_PLATFORM_MANIFEST_DIGEST}"],
        }
    ],
    separators=(",", ":"),
)
CANONICAL_MANAGED_COMPOSE = "deploy/docker-compose.production.yaml"
CANONICAL_SELF_HOSTED_COMPOSE = "deploy/docker-compose.production.selfhosted.yaml"
METRICS_SECRET_SENTINEL = "obs1b-test-metrics-token-12345678"  # pragma: allowlist secret


def _write_production_host_contract(
    project_dir: Path,
    *,
    compose_text: str = "services: {}\n",
    self_hosted: bool = False,
) -> Path:
    deploy_dir = project_dir / "deploy"
    prometheus_dir = deploy_dir / "prometheus"
    secret_dir = deploy_dir / "secrets"
    prometheus_dir.mkdir(parents=True, exist_ok=True)
    secret_dir.mkdir(parents=True, exist_ok=True)
    secret_dir.chmod(0o700)
    secret_file = secret_dir / "pulseplate_metrics_scrape_key"
    secret_file.write_text(METRICS_SECRET_SENTINEL, encoding="ascii")
    secret_file.chmod(0o444)
    (prometheus_dir / "prometheus.yml").write_text(
        PROMETHEUS_CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (prometheus_dir / "image-manifest.json").write_text(
        PROMETHEUS_MANIFEST_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    compose_name = (
        "docker-compose.production.selfhosted.yaml"
        if self_hosted
        else "docker-compose.production.yaml"
    )
    compose_path = deploy_dir / compose_name
    compose_path.write_text(compose_text, encoding="utf-8")
    return compose_path


def _write_shell_bundle_contract(
    shell_bundle_dir: Path,
    *,
    compose_text: str = PRODUCTION_COMPOSE_TEXT,
    include_frontend: bool = True,
    include_redeploy: bool = True,
) -> None:
    deploy_dir = shell_bundle_dir / "deploy"
    prometheus_dir = deploy_dir / "prometheus"
    scripts_dir = shell_bundle_dir / "scripts"
    deploy_dir.mkdir(parents=True, exist_ok=True)
    prometheus_dir.mkdir(parents=True, exist_ok=True)
    scripts_dir.mkdir(parents=True, exist_ok=True)
    if include_frontend:
        (shell_bundle_dir / "frontend").mkdir(parents=True, exist_ok=True)
    (deploy_dir / "Caddyfile.production").write_text(
        'pulseplate.test {\n    respond "ok"\n}\n', encoding="utf-8"
    )
    (deploy_dir / "docker-compose.production.yaml").write_text(compose_text, encoding="utf-8")
    (prometheus_dir / "prometheus.yml").write_text(
        PROMETHEUS_CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (prometheus_dir / "image-manifest.json").write_text(
        PROMETHEUS_MANIFEST_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (scripts_dir / "diagnose_web.sh").write_text(
        "#!/usr/bin/env bash\nprintf 'bundle-diagnose\\n'\n", encoding="utf-8"
    )
    if include_redeploy:
        (scripts_dir / "redeploy_caddy.sh").write_text(
            "#!/usr/bin/env bash\nprintf 'bundle-redeploy\\n'\n", encoding="utf-8"
        )


def _canonical_test_archive_path(suffix: int) -> Path:
    return Path("/tmp") / f"pulseplate-shell-bundle-{os.getpid()}-{suffix}.tgz"


def _write_shell_bundle_archive(
    archive_path: Path,
    source_dir: Path,
    *,
    variant: str = "valid",
) -> None:
    required_paths = [
        "frontend",
        "deploy/Caddyfile.production",
        "deploy/docker-compose.production.yaml",
        "deploy/prometheus/prometheus.yml",
        "deploy/prometheus/image-manifest.json",
        "scripts/diagnose_web.sh",
        "scripts/redeploy_caddy.sh",
    ]
    if archive_path.exists():
        archive_path.unlink()
    if variant == "oversized_archive":
        with archive_path.open("wb") as handle:
            handle.truncate(512 * 1024 * 1024 + 1)
        return

    with tarfile.open(archive_path, "w:gz") as archive:
        for relative_path in required_paths:
            if variant == "missing_manifest" and relative_path.endswith("image-manifest.json"):
                continue
            archive.add(source_dir / relative_path, arcname=relative_path, recursive=True)

        if variant == "duplicate":
            archive.add(
                source_dir / "deploy/Caddyfile.production",
                arcname="deploy/Caddyfile.production",
            )
        elif variant in {"traversal", "absolute", "non_normalized", "unexpected"}:
            names = {
                "traversal": "../escape.txt",
                "absolute": "/escape.txt",
                "non_normalized": "frontend/../escape.txt",
                "unexpected": "unexpected.txt",
            }
            payload = b"invalid\n"
            member = tarfile.TarInfo(names[variant])
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))
        elif variant in {"symlink", "hardlink", "fifo"}:
            member = tarfile.TarInfo(f"frontend/{variant}")
            if variant == "symlink":
                member.type = tarfile.SYMTYPE
                member.linkname = "target"
            elif variant == "hardlink":
                member.type = tarfile.LNKTYPE
                member.linkname = "frontend/bundle-marker.txt"
            else:
                member.type = tarfile.FIFOTYPE
            archive.addfile(member)


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


def test_prometheus_image_manifest_is_one_closed_exact_record() -> None:
    manifest = json.loads(PROMETHEUS_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest == {
        "schema": "pulseplate.prometheus_image_manifest.v2",
        "repository": "prom/prometheus",
        "source_revision": PROMETHEUS_SOURCE_REVISION,
        "index_digest": PROMETHEUS_INDEX_DIGEST,
        "platform": "linux/amd64",
        "platform_manifest_digest": PROMETHEUS_PLATFORM_MANIFEST_DIGEST,
        "runtime_ref": PROMETHEUS_RUNTIME_REF,
    }


def test_prometheus_cd_security_job_cross_binds_v2_digest_and_revision() -> None:
    workflow = yaml.safe_load(CD_WORKFLOW_PATH.read_text(encoding="utf-8"))
    job = workflow["jobs"]["prometheus-image-security"]
    steps = {step["name"]: step for step in job["steps"]}

    validate_run = steps["Validate closed Prometheus image record"]["run"]
    assert '"schema": "pulseplate.prometheus_image_manifest.v2"' in validate_run
    assert f'"source_revision": "{PROMETHEUS_SOURCE_REVISION}"' in validate_run
    assert f'"index_digest": "{PROMETHEUS_INDEX_DIGEST}"' in validate_run
    assert f'"platform_manifest_digest": "{PROMETHEUS_PLATFORM_MANIFEST_DIGEST}"' in validate_run
    assert f'"runtime_ref": "{PROMETHEUS_RUNTIME_REF}"' in validate_run
    assert "f\"index_ref={manifest['repository']}@{manifest['index_digest']}\"" in validate_run
    assert "f\"{manifest['repository']}@{manifest['platform_manifest_digest']}\"" in validate_run

    cross_bind = steps["Cross-bind immutable index, linux amd64 manifest, and local image config"]
    assert cross_bind["env"] == {
        "PROMETHEUS_INDEX_REF": "${{ steps.prometheus-image.outputs.index_ref }}",
        "PROMETHEUS_INDEX_DIGEST": "${{ steps.prometheus-image.outputs.index_digest }}",
        "PROMETHEUS_PLATFORM_MANIFEST_DIGEST": (
            "${{ steps.prometheus-image.outputs.platform_manifest_digest }}"
        ),
        "PROMETHEUS_RUNTIME_REF": "${{ steps.prometheus-image.outputs.runtime_ref }}",
        "PROMETHEUS_SOURCE_REVISION": "${{ steps.prometheus-image.outputs.source_revision }}",
    }
    cross_bind_run = cross_bind["run"]
    for required in (
        'docker buildx imagetools inspect --raw "$PROMETHEUS_INDEX_REF"',
        'docker buildx imagetools inspect --raw "$PROMETHEUS_RUNTIME_REF"',
        'docker pull --platform linux/amd64 "$PROMETHEUS_RUNTIME_REF"',
        "--entrypoint /bin/prometheus",
        '--version > "$evidence_dir/version.txt" 2>&1',
        r're.findall(r"\brevision: ([0-9a-f]{40})\b", version_text)',
        "if revisions != [expected_revision]:",
        'image.get("Id") != config_digest',
    ):
        assert required in cross_bind_run
    assert "PROMETHEUS_TAG_REF" not in cross_bind_run
    assert "main-distroless" not in cross_bind_run

    scan_run = steps["Scan exact Prometheus image without suppressions"]["run"]
    for required in (
        "--scanners vuln,secret",
        "--severity CRITICAL,HIGH",
        "--exit-code 1",
        '--ignorefile "$TRIVY_IGNORE_FILE"',
        '"$PROMETHEUS_RUNTIME_REF"',
    ):
        assert required in scan_run
    assert "--ignore-unfixed" not in scan_run
    assert "continue-on-error" not in scan_run


def test_prometheus_config_has_one_private_exact_target() -> None:
    config = yaml.safe_load(PROMETHEUS_CONFIG_PATH.read_text(encoding="utf-8"))
    assert config == {
        "global": {"scrape_interval": "30s", "scrape_timeout": "10s"},
        "scrape_configs": [
            {
                "job_name": "pulseplate-api",
                "scheme": "http",
                "metrics_path": "/metrics",
                "http_headers": {
                    "X-API-Key": {"files": ["/run/secrets/pulseplate_metrics_scrape_key"]}
                },
                "static_configs": [{"targets": ["app:8000"]}],
            }
        ],
    }
    config_text = PROMETHEUS_CONFIG_PATH.read_text(encoding="utf-8")
    for forbidden in (
        "remote_write",
        "remote_read",
        "rule_files",
        "alerting",
        "storage.tsdb.retention",
        "web.enable-lifecycle",
        "web.enable-admin-api",
        "otlp",
    ):
        assert forbidden not in config_text


@pytest.mark.parametrize(
    "compose_path",
    (STAGING_COMPOSE_PATH, PRODUCTION_COMPOSE_PATH, SELF_HOSTED_COMPOSE_PATH),
)
def test_three_compose_contours_normalize_to_one_private_prometheus_contract(
    compose_path: Path,
) -> None:
    docker_bin = shutil.which("docker")
    assert docker_bin is not None, "docker compose is required for normalized contract validation"
    completed = subprocess.run(
        [
            docker_bin,
            "compose",
            "-f",
            str(compose_path),
            "config",
            "--no-interpolate",
            "--format",
            "json",
        ],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    normalized = json.loads(completed.stdout)
    services = normalized["services"]
    prometheus = services["prometheus"]

    assert normalized["networks"]["observability"]["internal"] is True
    assert set(services["app"]["networks"]) == {"web", "observability"}
    assert set(prometheus["networks"]) == {"observability"}
    assert prometheus["image"] == PROMETHEUS_RUNTIME_REF
    assert prometheus["platform"] == "linux/amd64"
    assert prometheus["user"] == "65532:65532"
    assert prometheus["restart"] == "unless-stopped"
    assert prometheus["cap_drop"] == ["ALL"]
    assert prometheus["security_opt"] == ["no-new-privileges:true"]
    assert prometheus["command"] == [
        "--config.file=/etc/prometheus/prometheus.yml",
        "--storage.tsdb.path=/prometheus",
        "--storage.tsdb.retention.time=45d",
    ]
    assert prometheus["depends_on"] == {"app": {"condition": "service_healthy", "required": True}}
    assert prometheus["healthcheck"]["test"] == [
        "CMD",
        "/bin/promtool",
        "check",
        "ready",
        "--url=http://localhost:9090",
    ]
    assert "ports" not in prometheus

    volume_projection = {
        (item["type"], item["target"], item.get("source"), item.get("read_only", False))
        for item in prometheus["volumes"]
    }
    assert ("bind", "/etc/prometheus/prometheus.yml", str(PROMETHEUS_CONFIG_PATH), True) in (
        volume_projection
    )
    assert ("volume", "/prometheus", "prometheus_data", False) in volume_projection
    assert prometheus["secrets"] == [
        {
            "source": "pulseplate_metrics_scrape_key",
            "target": "/run/secrets/pulseplate_metrics_scrape_key",
        }
    ]
    assert services["app"]["secrets"] == prometheus["secrets"]
    assert "prometheus" not in services["app"].get("depends_on", {})
    for service_name in ("caddy", "worker", "postgres"):
        service = services.get(service_name)
        if isinstance(service, dict):
            assert "observability" not in service.get("networks", {})
            assert "secrets" not in service
    assert "prometheus_data" in normalized["volumes"]


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
    _write_production_host_contract(project_dir)
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )
    _write_shell_bundle_contract(shell_bundle_dir, include_redeploy=False)

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
    env["COMPOSE_FILE"] = CANONICAL_MANAGED_COMPOSE
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
    _write_production_host_contract(project_dir)
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )
    _write_shell_bundle_contract(shell_bundle_dir, include_frontend=False)

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
    env["COMPOSE_FILE"] = CANONICAL_MANAGED_COMPOSE
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
    if path.name == "docker":
        contract_responses = f"""case \"$*\" in
  *\"config --format json\"*)
    if [ \"${{STUB_COMPOSE_CONFIG_STATUS:-0}}\" -ne 0 ]; then
      exit \"${{STUB_COMPOSE_CONFIG_STATUS}}\"
    fi
    if [ -n \"${{STUB_PROMETHEUS_COMPOSE_JSON+x}}\" ]; then
      printf '%s\\n' \"$STUB_PROMETHEUS_COMPOSE_JSON\"
    else
      printf '%s\\n' '{FAKE_PROMETHEUS_COMPOSE_JSON}'
    fi
    ;;
  image\\ inspect\\ *)
    if [ \"${{STUB_IMAGE_INSPECT_STATUS:-0}}\" -ne 0 ]; then
      exit \"${{STUB_IMAGE_INSPECT_STATUS}}\"
    fi
    if [ -n \"${{STUB_PROMETHEUS_IMAGE_INSPECT_JSON+x}}\" ]; then
      printf '%s\\n' \"$STUB_PROMETHEUS_IMAGE_INSPECT_JSON\"
    else
      printf '%s\\n' '{FAKE_PROMETHEUS_IMAGE_INSPECT_JSON}'
    fi
    ;;
esac
"""
        marker = "set -euo pipefail\n"
        if marker in content:
            content = content.replace(marker, marker + contract_responses, 1)
        else:
            content = content.replace("\n", "\n" + contract_responses, 1)
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


def _write_prometheus_manifest_variant(path: Path, variant: str) -> None:
    canonical = json.loads(PROMETHEUS_MANIFEST_PATH.read_text(encoding="utf-8"))
    if variant == "malformed":
        path.write_text("{", encoding="utf-8")
        return
    if variant == "duplicate":
        canonical_text = json.dumps(canonical, separators=(",", ":"))
        path.write_text(
            '{"schema":"pulseplate.prometheus_image_manifest.v2",' + canonical_text[1:],
            encoding="utf-8",
        )
        return
    if variant == "missing":
        canonical.pop("index_digest")
    elif variant == "extra":
        canonical["unexpected"] = "forbidden"
    elif variant == "wrong-platform-digest":
        canonical["platform_manifest_digest"] = "sha256:" + "b" * 64
    elif variant == "wrong-source-revision":
        canonical["source_revision"] = "A" * 40
    elif variant == "wrong-runtime-ref":
        canonical["runtime_ref"] = (
            "prom/prometheus:main-distroless@" + PROMETHEUS_PLATFORM_MANIFEST_DIGEST
        )
    elif variant == "index-digest-runtime-ref":
        canonical["runtime_ref"] = f"prom/prometheus@{PROMETHEUS_INDEX_DIGEST}"
    elif variant == "wrong-type":
        canonical["source_revision"] = 314
    else:
        raise AssertionError(f"unsupported manifest variant: {variant}")
    path.write_text(json.dumps(canonical), encoding="utf-8")


def _production_preflight_fixture(
    tmp_path: Path,
    *,
    with_bundle: bool,
) -> tuple[dict[str, str], Path, Path, Path | None]:
    project_dir = tmp_path / "production"
    shell_bundle_dir = tmp_path / "shell-bundle" if with_bundle else None
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "docker.log"
    project_dir.mkdir()
    bin_dir.mkdir()
    _write_production_host_contract(project_dir, compose_text=PRODUCTION_COMPOSE_TEXT)
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )
    if shell_bundle_dir is not None:
        shell_bundle_dir.mkdir()
        _write_shell_bundle_contract(shell_bundle_dir)
        (shell_bundle_dir / "frontend" / "bundle-marker.txt").write_text(
            "bounded-frontend\n", encoding="utf-8"
        )
    _write_executable(
        bin_dir / "docker",
        f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
case "$*" in
  *"config --services"*) printf 'app\\nworker\\ncaddy\\nprometheus\\n' ;;
esac
""",
    )
    _write_executable(bin_dir / "curl", "#!/usr/bin/env bash\nset -euo pipefail\n")
    env = os.environ.copy()
    env.update(
        {
            "DOCKER_BIN": str(bin_dir / "docker"),
            "PYTHON_BIN": sys.executable,
            "CURL_BIN": str(bin_dir / "curl"),
            "DEPLOY_DIR": str(project_dir),
            "ENV_FILE": str(project_dir / ".env"),
            "COMPOSE_FILE": CANONICAL_MANAGED_COMPOSE,
            "PRODUCTION_DOMAIN": "pulseplate.test",
        }
    )
    if shell_bundle_dir is not None:
        env["SHELL_BUNDLE_DIR"] = str(shell_bundle_dir)
    return env, project_dir, log_file, shell_bundle_dir


@pytest.mark.parametrize(
    "variant",
    (
        "malformed",
        "duplicate",
        "missing",
        "extra",
        "wrong-platform-digest",
        "wrong-source-revision",
        "wrong-runtime-ref",
        "index-digest-runtime-ref",
        "wrong-type",
    ),
)
def test_staging_deploy_rejects_noncanonical_prometheus_manifest_before_docker(
    tmp_path: Path,
    variant: str,
) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)
    manifest_path = Path(env["PROJECT_DIR"]) / "prometheus" / "image-manifest.json"
    _write_prometheus_manifest_variant(manifest_path, variant)
    backend_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64

    completed = subprocess.run(
        [
            str(REPO_ROOT / "scripts/deploy.sh"),
            "--preflight-only",
            backend_ref,
            caddy_ref,
        ],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "Prometheus manifest" in completed.stderr
    assert not log_file.exists()


@pytest.mark.parametrize(
    "variant",
    (
        "malformed",
        "duplicate",
        "missing",
        "extra",
        "wrong-platform-digest",
        "wrong-source-revision",
        "wrong-runtime-ref",
        "index-digest-runtime-ref",
        "wrong-type",
    ),
)
def test_production_deploy_rejects_noncanonical_prometheus_manifest_before_docker(
    tmp_path: Path,
    variant: str,
) -> None:
    env, project_dir, log_file, _bundle = _production_preflight_fixture(
        tmp_path,
        with_bundle=False,
    )
    _write_prometheus_manifest_variant(
        project_dir / "deploy" / "prometheus" / "image-manifest.json",
        variant,
    )

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh"), "--preflight-only"],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "Prometheus manifest" in completed.stderr
    assert not log_file.exists()


@pytest.mark.parametrize(
    "rendered_compose",
    (
        "{",
        "{}",
        json.dumps(
            {
                "services": {
                    "prometheus": {
                        "image": "prom/prometheus:latest",
                        "platform": "linux/amd64",
                    }
                }
            }
        ),
        json.dumps(
            {
                "services": {
                    "prometheus": {
                        "image": PROMETHEUS_RUNTIME_REF,
                        "platform": "linux/arm64",
                    }
                }
            }
        ),
    ),
)
def test_staging_deploy_rejects_rendered_prometheus_identity_drift_before_pull(
    tmp_path: Path,
    rendered_compose: str,
) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)
    env["STUB_PROMETHEUS_COMPOSE_JSON"] = rendered_compose
    backend_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64

    completed = subprocess.run(
        [
            str(REPO_ROOT / "scripts/deploy.sh"),
            "--preflight-only",
            backend_ref,
            caddy_ref,
        ],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any("config --format json" in line for line in log_lines)
    assert all(
        " login " not in line and " pull " not in line and " up " not in line for line in log_lines
    )


@pytest.mark.parametrize(
    "rendered_compose",
    (
        "{",
        "{}",
        json.dumps(
            {
                "services": {
                    "prometheus": {
                        "image": "prom/prometheus:latest",
                        "platform": "linux/amd64",
                    }
                }
            }
        ),
        json.dumps(
            {
                "services": {
                    "prometheus": {
                        "image": PROMETHEUS_RUNTIME_REF,
                        "platform": "linux/arm64",
                    }
                }
            }
        ),
    ),
)
def test_production_deploy_rejects_rendered_prometheus_identity_drift_before_pull(
    tmp_path: Path,
    rendered_compose: str,
) -> None:
    env, _project_dir, log_file, _bundle = _production_preflight_fixture(
        tmp_path,
        with_bundle=False,
    )
    env["STUB_PROMETHEUS_COMPOSE_JSON"] = rendered_compose

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh"), "--preflight-only"],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any("config --format json" in line for line in log_lines)
    assert all(
        " login " not in line and " pull " not in line and " up " not in line for line in log_lines
    )


IMAGE_INSPECT_REJECTIONS = (
    "{",
    "[]",
    json.dumps(
        [
            {
                "Os": "linux",
                "Architecture": "amd64",
                "RepoDigests": [f"prom/prometheus@{PROMETHEUS_PLATFORM_MANIFEST_DIGEST}"],
            },
            {
                "Os": "linux",
                "Architecture": "amd64",
                "RepoDigests": [f"prom/prometheus@{PROMETHEUS_PLATFORM_MANIFEST_DIGEST}"],
            },
        ]
    ),
    json.dumps(
        [
            {
                "Os": "windows",
                "Architecture": "amd64",
                "RepoDigests": [f"prom/prometheus@{PROMETHEUS_PLATFORM_MANIFEST_DIGEST}"],
            }
        ]
    ),
    json.dumps(
        [
            {
                "Os": "linux",
                "Architecture": "arm64",
                "RepoDigests": [f"prom/prometheus@{PROMETHEUS_PLATFORM_MANIFEST_DIGEST}"],
            }
        ]
    ),
    json.dumps([{"Os": "linux", "Architecture": "amd64", "RepoDigests": []}]),
    json.dumps(
        [
            {
                "Os": "linux",
                "Architecture": "amd64",
                "RepoDigests": [f"prom/prometheus@{PROMETHEUS_INDEX_DIGEST}"],
            }
        ]
    ),
    json.dumps(
        [
            {
                "Os": "linux",
                "Architecture": "amd64",
                "RepoDigests": [
                    f"example.invalid/prometheus@{PROMETHEUS_PLATFORM_MANIFEST_DIGEST}"
                ],
            }
        ]
    ),
)


@pytest.mark.parametrize("inspect_payload", IMAGE_INSPECT_REJECTIONS)
def test_staging_deploy_rejects_pulled_prometheus_identity_before_product_mutation(
    tmp_path: Path,
    inspect_payload: str,
) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)
    env["STUB_PROMETHEUS_IMAGE_INSPECT_JSON"] = inspect_payload
    backend_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy.sh"), backend_ref, caddy_ref],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any(" pull app caddy prometheus" in line for line in log_lines)
    assert any("image inspect" in line for line in log_lines)
    assert all("promtool" not in line for line in log_lines)
    assert all("assert_production_runtime_invariants" not in line for line in log_lines)
    assert all(" stop " not in line and " up " not in line for line in log_lines)


@pytest.mark.parametrize("inspect_payload", IMAGE_INSPECT_REJECTIONS)
def test_production_deploy_rejects_pulled_prometheus_identity_before_product_mutation(
    tmp_path: Path,
    inspect_payload: str,
) -> None:
    env, _project_dir, log_file, _bundle = _production_preflight_fixture(
        tmp_path,
        with_bundle=False,
    )
    env.update(
        {
            "IMAGE_REF": "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test",
            "TAG": "prod-vtest",
            "STUB_PROMETHEUS_IMAGE_INSPECT_JSON": inspect_payload,
        }
    )

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any(" pull prometheus" in line for line in log_lines)
    assert any("image inspect" in line for line in log_lines)
    assert all("promtool" not in line for line in log_lines)
    assert all("assert_production_runtime_invariants" not in line for line in log_lines)
    assert all(" stop " not in line and " up " not in line for line in log_lines)


def test_production_env_cannot_override_manifest_derived_prometheus_digest(
    tmp_path: Path,
) -> None:
    env, project_dir, log_file, _bundle = _production_preflight_fixture(
        tmp_path,
        with_bundle=False,
    )
    conflicting_digest = "sha256:" + "b" * 64
    with (project_dir / ".env").open("a", encoding="utf-8") as env_file:
        env_file.write(f"PROMETHEUS_PLATFORM_MANIFEST_DIGEST={conflicting_digest}\n")
    env.update(
        {
            "IMAGE_REF": "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test",
            "TAG": "prod-vtest",
            "STUB_PROMETHEUS_IMAGE_INSPECT_JSON": json.dumps(
                [
                    {
                        "Os": "linux",
                        "Architecture": "amd64",
                        "RepoDigests": [f"prom/prometheus@{conflicting_digest}"],
                    }
                ]
            ),
        }
    )

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "canonical platform digest" in completed.stderr
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any("image inspect" in line for line in log_lines)
    assert all("promtool" not in line for line in log_lines)
    assert all("assert_production_runtime_invariants" not in line for line in log_lines)


@pytest.mark.parametrize(
    "destination_variant",
    (
        "frontend-directory-symlink",
        "caddy-leaf-symlink",
        "scripts-directory-symlink",
        "redeploy-leaf-symlink",
    ),
)
def test_production_full_bundle_rejects_hostile_destination_before_docker(
    tmp_path: Path,
    destination_variant: str,
) -> None:
    env, project_dir, log_file, _bundle = _production_preflight_fixture(
        tmp_path,
        with_bundle=True,
    )
    external = tmp_path / f"external-{destination_variant}"
    if destination_variant == "frontend-directory-symlink":
        external.mkdir()
        (external / "sentinel").write_text("external-frontend\n", encoding="utf-8")
        hostile = project_dir / "frontend"
        hostile.symlink_to(external, target_is_directory=True)
        expected = (external / "sentinel").read_bytes()
    elif destination_variant == "caddy-leaf-symlink":
        external.write_text("external-caddy\n", encoding="utf-8")
        hostile = project_dir / "deploy" / "Caddyfile.production"
        hostile.symlink_to(external)
        expected = external.read_bytes()
    elif destination_variant == "scripts-directory-symlink":
        external.mkdir()
        (external / "sentinel").write_text("external-scripts\n", encoding="utf-8")
        hostile = project_dir / "scripts"
        hostile.symlink_to(external, target_is_directory=True)
        expected = (external / "sentinel").read_bytes()
    else:
        scripts_dir = project_dir / "scripts"
        scripts_dir.mkdir()
        external.write_text("external-helper\n", encoding="utf-8")
        hostile = scripts_dir / "redeploy_caddy.sh"
        hostile.symlink_to(external)
        expected = external.read_bytes()

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh"), "--preflight-only"],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert hostile.is_symlink()
    assert not log_file.exists()
    if external.is_dir():
        assert (external / "sentinel").read_bytes() == expected
    else:
        assert external.read_bytes() == expected
    assert list(project_dir.rglob(".pulseplate-*.tmp-*")) == []
    assert list(project_dir.rglob(".pulseplate-*.old-*")) == []


@pytest.mark.parametrize(
    "source_variant",
    (
        "bundle-parent-symlink",
        "frontend-nested-symlink",
        "frontend-nested-hardlink",
        "caddy-source-symlink",
        "redeploy-source-symlink",
    ),
)
def test_production_full_bundle_rejects_hostile_source_before_runtime_mutation(
    tmp_path: Path,
    source_variant: str,
) -> None:
    env, project_dir, log_file, shell_bundle_dir = _production_preflight_fixture(
        tmp_path,
        with_bundle=True,
    )
    assert shell_bundle_dir is not None
    external = tmp_path / f"external-{source_variant}"
    if source_variant == "bundle-parent-symlink":
        real_bundle = tmp_path / "real-shell-bundle"
        shell_bundle_dir.rename(real_bundle)
        shell_bundle_dir.symlink_to(real_bundle, target_is_directory=True)
        expected_path = real_bundle / "frontend" / "bundle-marker.txt"
    elif source_variant == "frontend-nested-symlink":
        external.write_text("external-frontend\n", encoding="utf-8")
        (shell_bundle_dir / "frontend" / "hostile-link").symlink_to(external)
        expected_path = external
    elif source_variant == "frontend-nested-hardlink":
        external.write_text("external-hardlink\n", encoding="utf-8")
        os.link(external, shell_bundle_dir / "frontend" / "hostile-hardlink")
        expected_path = external
    elif source_variant == "caddy-source-symlink":
        caddy = shell_bundle_dir / "deploy" / "Caddyfile.production"
        caddy.rename(external)
        caddy.symlink_to(external)
        expected_path = external
    else:
        redeploy = shell_bundle_dir / "scripts" / "redeploy_caddy.sh"
        redeploy.rename(external)
        redeploy.symlink_to(external)
        expected_path = external
    expected = expected_path.read_bytes()

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh"), "--preflight-only"],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert expected_path.read_bytes() == expected
    if log_file.exists():
        log_lines = log_file.read_text(encoding="utf-8").splitlines()
        assert all(
            " login " not in line
            and " pull " not in line
            and " stop " not in line
            and " up " not in line
            for line in log_lines
        )
    assert list(project_dir.rglob(".pulseplate-*.tmp-*")) == []
    assert list(project_dir.rglob(".pulseplate-*.old-*")) == []


@pytest.mark.parametrize(
    ("variant", "suffix", "expected_returncode"),
    (
        ("valid", 1, 0),
        ("traversal", 2, 1),
        ("absolute", 3, 1),
        ("non_normalized", 4, 1),
        ("duplicate", 5, 1),
        ("symlink", 6, 1),
        ("hardlink", 7, 1),
        ("fifo", 8, 1),
        ("unexpected", 9, 1),
        ("missing_manifest", 10, 1),
        ("oversized_archive", 11, 1),
    ),
)
def test_production_archive_preflight_is_bounded_and_extracts_nothing(
    tmp_path: Path,
    variant: str,
    suffix: int,
    expected_returncode: int,
) -> None:
    project_dir = tmp_path / "production"
    shell_bundle_dir = tmp_path / "bundle-source"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "docker.log"
    project_dir.mkdir()
    shell_bundle_dir.mkdir()
    bin_dir.mkdir()
    _write_production_host_contract(project_dir)
    _write_shell_bundle_contract(shell_bundle_dir)
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )

    archive_path = _canonical_test_archive_path(suffix)
    _write_shell_bundle_archive(archive_path, shell_bundle_dir, variant=variant)
    _write_executable(
        bin_dir / "docker",
        f'#!/usr/bin/env bash\nset -euo pipefail\nprintf \'docker %s\\n\' "$*" >> "{log_file}"\n',
    )
    _write_executable(bin_dir / "curl", "#!/usr/bin/env bash\nset -euo pipefail\n")

    env = os.environ.copy()
    env.update(
        {
            "DOCKER_BIN": str(bin_dir / "docker"),
            "PYTHON_BIN": sys.executable,
            "CURL_BIN": str(bin_dir / "curl"),
            "DEPLOY_DIR": str(project_dir),
            "ENV_FILE": str(project_dir / ".env"),
            "COMPOSE_FILE": CANONICAL_MANAGED_COMPOSE,
            "PRODUCTION_DOMAIN": "pulseplate.test",
            "SHELL_BUNDLE_ARCHIVE": str(archive_path),
        }
    )
    try:
        completed = subprocess.run(
            [str(REPO_ROOT / "scripts/deploy_production.sh"), "--preflight-only"],
            cwd=str(REPO_ROOT),
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == expected_returncode, completed.stderr
        assert not (project_dir / "frontend").exists()
        if expected_returncode == 0:
            assert log_file.is_file()
            assert "Production deploy preflight passed" in completed.stdout
        else:
            assert not log_file.exists()
            assert "archive" in completed.stderr.lower()
    finally:
        if archive_path.exists():
            archive_path.unlink()


@pytest.mark.parametrize(
    "destination_variant",
    (
        "compose-leaf-symlink",
        "prometheus-directory-symlink",
        "config-leaf-symlink",
        "manifest-leaf-symlink",
    ),
)
def test_production_contract_publication_rejects_destination_symlinks_before_docker(
    tmp_path: Path,
    destination_variant: str,
) -> None:
    project_dir = tmp_path / "production"
    shell_bundle_dir = tmp_path / "bundle-source"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "docker.log"
    project_dir.mkdir()
    shell_bundle_dir.mkdir()
    bin_dir.mkdir()
    _write_production_host_contract(project_dir)
    _write_shell_bundle_contract(shell_bundle_dir)
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )

    deploy_dir = project_dir / "deploy"
    compose_path = deploy_dir / "docker-compose.production.yaml"
    prometheus_dir = deploy_dir / "prometheus"
    config_path = prometheus_dir / "prometheus.yml"
    manifest_path = prometheus_dir / "image-manifest.json"
    external_referent = tmp_path / f"external-{destination_variant}"
    expected_external_files: dict[str, bytes] = {}

    if destination_variant == "compose-leaf-symlink":
        compose_path.rename(external_referent)
        expected_external_files[external_referent.name] = external_referent.read_bytes()
        compose_path.symlink_to(external_referent)
        symlink_path = compose_path
    elif destination_variant == "prometheus-directory-symlink":
        prometheus_dir.rename(external_referent)
        expected_external_files["prometheus.yml"] = (
            external_referent / "prometheus.yml"
        ).read_bytes()
        expected_external_files["image-manifest.json"] = (
            external_referent / "image-manifest.json"
        ).read_bytes()
        prometheus_dir.symlink_to(external_referent, target_is_directory=True)
        symlink_path = prometheus_dir
    elif destination_variant == "config-leaf-symlink":
        config_path.rename(external_referent)
        expected_external_files[external_referent.name] = external_referent.read_bytes()
        config_path.symlink_to(external_referent)
        symlink_path = config_path
    else:
        manifest_path.rename(external_referent)
        expected_external_files[external_referent.name] = external_referent.read_bytes()
        manifest_path.symlink_to(external_referent)
        symlink_path = manifest_path

    _write_executable(
        bin_dir / "docker",
        f'#!/usr/bin/env bash\nprintf \'docker %s\\n\' "$*" >> "{log_file}"\n',
    )
    _write_executable(bin_dir / "curl", "#!/usr/bin/env bash\nset -euo pipefail\n")
    env = os.environ.copy()
    env.update(
        {
            "DOCKER_BIN": str(bin_dir / "docker"),
            "CURL_BIN": str(bin_dir / "curl"),
            "DEPLOY_DIR": str(project_dir),
            "ENV_FILE": str(project_dir / ".env"),
            "COMPOSE_FILE": CANONICAL_MANAGED_COMPOSE,
            "PRODUCTION_DOMAIN": "pulseplate.test",
            "SHELL_BUNDLE_DIR": str(shell_bundle_dir),
        }
    )
    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh"), "--preflight-only"],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "destination" in completed.stderr or "Prometheus contract directory" in completed.stderr
    assert symlink_path.is_symlink()
    assert not log_file.exists()
    if external_referent.is_dir():
        for name, expected_bytes in expected_external_files.items():
            assert (external_referent / name).read_bytes() == expected_bytes
    else:
        assert external_referent.read_bytes() == expected_external_files[external_referent.name]
    assert list(deploy_dir.rglob(".pulseplate-*.tmp-*")) == []


def test_production_archive_full_deploy_preserves_server_local_state_and_orders_prometheus_last(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "production"
    shell_bundle_dir = tmp_path / "bundle-source"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    shell_bundle_dir.mkdir()
    bin_dir.mkdir()
    _write_production_host_contract(project_dir)
    _write_shell_bundle_contract(shell_bundle_dir)
    (shell_bundle_dir / "frontend" / "bundle-marker.txt").write_text(
        "archive-shell\n", encoding="utf-8"
    )
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )
    evidence_file = project_dir / "evidence" / "receipt.json"
    backup_file = project_dir / "backups" / "backup.dump"
    tsdb_sentinel = project_dir / "prometheus_data" / "sentinel"
    for path, value in (
        (evidence_file, "evidence\n"),
        (backup_file, "backup\n"),
        (tsdb_sentinel, "tsdb\n"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")
    secret_file = project_dir / "deploy" / "secrets" / "pulseplate_metrics_scrape_key"
    original_secret = secret_file.read_bytes()

    archive_path = _canonical_test_archive_path(12)
    _write_shell_bundle_archive(archive_path, shell_bundle_dir)
    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\n' "$*" >> "{log_file}"
case "$*" in
  *"ps -q app"*) printf 'app-id\n' ;;
esac
"""
    curl_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'curl %s\n' "$*" >> "{log_file}"
"""
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)
    _write_executable(bin_dir / "sleep", "#!/usr/bin/env bash\nset -euo pipefail\n")

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "DOCKER_BIN": str(bin_dir / "docker"),
            "CURL_BIN": str(bin_dir / "curl"),
            "DEPLOY_DIR": str(project_dir),
            "ENV_FILE": str(project_dir / ".env"),
            "COMPOSE_FILE": CANONICAL_MANAGED_COMPOSE,
            "IMAGE_REF": "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test",
            "TAG": "prod-vtest",
            "PRODUCTION_DOMAIN": "pulseplate.test",
            "SHELL_BUNDLE_ARCHIVE": str(archive_path),
            "HEALTH_MAX_ATTEMPTS": "1",
            "HEALTH_SLEEP_S": "0",
        }
    )
    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert METRICS_SECRET_SENTINEL not in completed.stdout
    assert METRICS_SECRET_SENTINEL not in completed.stderr
    assert not archive_path.exists()
    assert secret_file.read_bytes() == original_secret
    assert evidence_file.read_text(encoding="utf-8") == "evidence\n"
    assert backup_file.read_text(encoding="utf-8") == "backup\n"
    assert tsdb_sentinel.read_text(encoding="utf-8") == "tsdb\n"
    assert (project_dir / "frontend" / "bundle-marker.txt").read_text(
        encoding="utf-8"
    ) == "archive-shell\n"

    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert all(METRICS_SECRET_SENTINEL not in line for line in log_lines)
    prometheus_pull_index = _assert_log_index(
        log_lines,
        predicate=lambda line: " pull prometheus" in line,
        message="exact Prometheus pull missing",
    )
    image_inspect_index = _assert_log_index(
        log_lines,
        predicate=lambda line: line.startswith("docker image inspect "),
        message="pulled Prometheus identity validation missing",
    )
    promtool_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "promtool prometheus" in line,
        message="Prometheus config validation missing",
    )
    guard_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "assert_production_runtime_invariants(app=app)" in line,
        message="canonical app.main production invariant was not invoked",
    )
    migration_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "app alembic upgrade head" in line,
        message="migration command missing",
    )
    caddy_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "up -d --remove-orphans caddy" in line,
        message="Caddy start missing",
    )
    prometheus_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "up -d --pull never prometheus" in line,
        message="Prometheus start missing",
    )
    assert (
        prometheus_pull_index
        < image_inspect_index
        < promtool_index
        < guard_index
        < migration_index
        < caddy_index
        < prometheus_index
    )
    for forbidden in ("down -v", "volume rm", "volume prune", "prometheus_data rm"):
        assert all(forbidden not in line for line in log_lines)


def test_production_prometheus_failure_is_nonzero_after_product_and_preserves_state(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "production"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    bin_dir.mkdir()
    _write_production_host_contract(project_dir)
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )
    tsdb_sentinel = project_dir / "prometheus_data" / "sentinel"
    tsdb_sentinel.parent.mkdir()
    tsdb_sentinel.write_text("preserve\n", encoding="utf-8")

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\n' "$*" >> "{log_file}"
case "$*" in
  *"ps -q app"*) printf 'app-id\n' ;;
  *"up -d --pull never prometheus"*) exit 47 ;;
esac
"""
    curl_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'curl %s\n' "$*" >> "{log_file}"
"""
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)
    _write_executable(bin_dir / "sleep", "#!/usr/bin/env bash\nset -euo pipefail\n")

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "DOCKER_BIN": str(bin_dir / "docker"),
            "CURL_BIN": str(bin_dir / "curl"),
            "DEPLOY_DIR": str(project_dir),
            "ENV_FILE": str(project_dir / ".env"),
            "COMPOSE_FILE": CANONICAL_MANAGED_COMPOSE,
            "IMAGE_REF": "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test",
            "TAG": "prod-vtest",
            "PRODUCTION_DOMAIN": "pulseplate.test",
            "HEALTH_MAX_ATTEMPTS": "1",
            "HEALTH_SLEEP_S": "0",
        }
    )
    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 47
    assert "Prometheus failed to start; app and Caddy remain running" in completed.stderr
    assert tsdb_sentinel.read_text(encoding="utf-8") == "preserve\n"
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    app_index = next(
        index for index, line in enumerate(log_lines) if "up -d --remove-orphans app" in line
    )
    caddy_index = next(
        index for index, line in enumerate(log_lines) if "up -d --remove-orphans caddy" in line
    )
    prometheus_index = next(
        index for index, line in enumerate(log_lines) if "up -d --pull never prometheus" in line
    )
    assert app_index < caddy_index < prometheus_index
    for forbidden in ("down", "volume rm", "volume prune", "stop app", "stop caddy"):
        assert all(forbidden not in line for line in log_lines[prometheus_index + 1 :])


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


def test_postgres_backup_helper_uses_container_database_identity_when_host_env_is_absent(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "project"
    bin_dir = tmp_path / "bin"
    backup_dir = tmp_path / "backups"
    log_file = tmp_path / "docker.log"
    project_dir.mkdir()
    bin_dir.mkdir()
    backup_dir.mkdir()

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "{log_file}"
printf 'FAKE_BACKUP\n'
"""
    _write_executable(bin_dir / "docker", docker_stub)

    env = os.environ.copy()
    env.pop("POSTGRES_USER", None)
    env.pop("POSTGRES_DB", None)
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["PROJECT_DIR"] = str(project_dir)
    env["BACKUP_DIR"] = str(backup_dir)
    env["COMPOSE_FILE"] = "docker-compose.staging.yaml"

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
    assert "exec -T postgres sh -euc" in docker_call
    assert 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' in docker_call
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
    _write_production_host_contract(project_dir)
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
    env["COMPOSE_FILE"] = CANONICAL_MANAGED_COMPOSE
    env["CURL_BIN"] = str(bin_dir / "curl")
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
    _write_production_host_contract(project_dir)

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
"""
    _write_executable(bin_dir / "docker", docker_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["COMPOSE_FILE"] = CANONICAL_MANAGED_COMPOSE

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh"), "--preflight-only"],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert f"Missing production env file: {project_dir / 'deploy' / '.env'}" in completed.stderr
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
    (project_dir / "deploy").mkdir()
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
    env["COMPOSE_FILE"] = CANONICAL_MANAGED_COMPOSE
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
    assert "RESOLVED_COMPOSE_FILE does not exist: deploy/docker-compose.production.yaml" in (
        completed.stderr
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
    _write_production_host_contract(project_dir)
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
    _write_executable(docker_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", curl_stub)
    _write_executable(bin_dir / "sleep", sleep_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(docker_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = CANONICAL_MANAGED_COMPOSE
    env["CURL_BIN"] = str(bin_dir / "curl")
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
    _write_production_host_contract(project_dir)
    (project_dir / ".env").write_text(
        "\n".join(
            [
                "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate",  # pragma: allowlist secret
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _write_shell_bundle_contract(shell_bundle_dir)
    (shell_bundle_dir / "frontend" / "bundle-marker.txt").write_text(
        "frontend-sync\n", encoding="utf-8"
    )
    (shell_root / "frontend").mkdir()
    (shell_root / "frontend" / "outside-sentinel.txt").write_text(
        "outside-shell\n", encoding="utf-8"
    )
    (project_dir / "frontend").mkdir()
    (project_dir / "frontend" / "stale.txt").write_text("old-shell\n", encoding="utf-8")
    (project_dir / "scripts").mkdir()
    (project_dir / "scripts" / "diagnose_web.sh").write_text("stale-diagnose\n", encoding="utf-8")
    (project_dir / "scripts" / "redeploy_caddy.sh").write_text("stale-redeploy\n", encoding="utf-8")

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
    env["COMPOSE_FILE"] = CANONICAL_MANAGED_COMPOSE
    env["CURL_BIN"] = str(bin_dir / "curl")
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

    assert (project_dir / "frontend" / "bundle-marker.txt").read_text(
        encoding="utf-8"
    ) == "frontend-sync\n"
    assert (
        (project_dir / "deploy" / "Caddyfile.production")
        .read_text(encoding="utf-8")
        .startswith("pulseplate.test")
    )
    assert not (project_dir / "Caddyfile.production").exists()
    assert (shell_root / "frontend" / "outside-sentinel.txt").read_text(
        encoding="utf-8"
    ) == "outside-shell\n"
    assert (project_dir / "deploy" / "docker-compose.production.yaml").read_text(
        encoding="utf-8"
    ) == PRODUCTION_COMPOSE_TEXT
    published_config = project_dir / "deploy" / "prometheus" / "prometheus.yml"
    published_manifest = project_dir / "deploy" / "prometheus" / "image-manifest.json"
    assert published_config.read_text(encoding="utf-8") == PROMETHEUS_CONFIG_PATH.read_text(
        encoding="utf-8"
    )
    assert published_manifest.read_text(encoding="utf-8") == PROMETHEUS_MANIFEST_PATH.read_text(
        encoding="utf-8"
    )
    for published_path in (
        project_dir / "deploy" / "docker-compose.production.yaml",
        published_config,
        published_manifest,
        project_dir / "deploy" / "Caddyfile.production",
        project_dir / "frontend" / "bundle-marker.txt",
    ):
        assert stat.S_IMODE(published_path.stat().st_mode) == 0o644
    for helper_path in (
        project_dir / "scripts" / "diagnose_web.sh",
        project_dir / "scripts" / "redeploy_caddy.sh",
    ):
        assert stat.S_IMODE(helper_path.stat().st_mode) == 0o755
    assert list(project_dir.rglob(".pulseplate-*.tmp-*")) == []
    assert list(project_dir.rglob(".pulseplate-*.old-*")) == []
    assert not (project_dir / "frontend" / "stale.txt").exists()
    assert (project_dir / "scripts" / "diagnose_web.sh").read_text(
        encoding="utf-8"
    ) == "#!/usr/bin/env bash\nprintf 'bundle-diagnose\\n'\n"
    assert (project_dir / "scripts" / "redeploy_caddy.sh").read_text(
        encoding="utf-8"
    ) == "#!/usr/bin/env bash\nprintf 'bundle-redeploy\\n'\n"


def test_production_full_sync_cannot_republish_contracts_changed_after_validation(
    tmp_path: Path,
) -> None:
    env, project_dir, log_file, shell_bundle_dir = _production_preflight_fixture(
        tmp_path,
        with_bundle=True,
    )
    assert shell_bundle_dir is not None
    source_manifest = shell_bundle_dir / "deploy" / "prometheus" / "image-manifest.json"
    source_compose = shell_bundle_dir / "deploy" / "docker-compose.production.yaml"
    bin_dir = Path(env["DOCKER_BIN"]).parent
    tampered_manifest = '{"tampered":true}\n'
    tampered_compose = "services:\n  prometheus:\n    image: prom/prometheus:latest\n"
    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
case "$*" in
  *"config --services"*) printf 'app\\nworker\\ncaddy\\nprometheus\\n' ;;
  *"run --rm --no-deps app alembic upgrade head"*)
    printf '%s' '{tampered_manifest}' > "{source_manifest}"
    printf '%s' '{tampered_compose}' > "{source_compose}"
    ;;
  *"ps -q app"*) printf 'app-id\\n' ;;
esac
"""
    _write_executable(bin_dir / "docker", docker_stub)
    env.update(
        {
            "IMAGE_REF": "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:test",
            "TAG": "prod-vtest",
            "HEALTH_MAX_ATTEMPTS": "1",
            "HEALTH_SLEEP_S": "0",
        }
    )

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh")],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert source_manifest.read_text(encoding="utf-8") == tampered_manifest
    assert source_compose.read_text(encoding="utf-8") == tampered_compose
    assert (project_dir / "deploy" / "prometheus" / "image-manifest.json").read_text(
        encoding="utf-8"
    ) == PROMETHEUS_MANIFEST_PATH.read_text(encoding="utf-8")
    assert (project_dir / "deploy" / "docker-compose.production.yaml").read_text(
        encoding="utf-8"
    ) == PRODUCTION_COMPOSE_TEXT


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
    _write_production_host_contract(project_dir)
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )
    _write_shell_bundle_contract(shell_bundle_dir)
    (shell_bundle_dir / "frontend" / "bundle-marker.txt").write_text(
        "frontend-sync\n", encoding="utf-8"
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
    env.pop("COMPOSE_FILE", None)
    env["CURL_BIN"] = str(bin_dir / "curl")
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
    ) == PRODUCTION_COMPOSE_TEXT
    assert (project_dir / "frontend" / "bundle-marker.txt").read_text(
        encoding="utf-8"
    ) == "frontend-sync\n"
    assert (project_dir / "deploy" / "Caddyfile.production").is_file()
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
    shell_bundle_dir.mkdir()
    bin_dir.mkdir()
    _write_production_host_contract(project_dir)
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )
    _write_shell_bundle_contract(
        shell_bundle_dir,
        compose_text="services:\n  app:\n    image: ghcr.io/example/pulseplate:test\n",
    )
    (shell_bundle_dir / "frontend" / "bundle-marker.txt").write_text(
        "frontend-sync\n", encoding="utf-8"
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
    env["CURL_BIN"] = str(bin_dir / "curl")
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
    bin_dir.mkdir()
    _write_production_host_contract(project_dir)
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
    env["CURL_BIN"] = str(bin_dir / "curl")
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
    bin_dir.mkdir()
    _write_production_host_contract(project_dir)
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
    env["CURL_BIN"] = str(bin_dir / "curl")
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
    assert "COMPOSE_FILE must select one exact canonical production Compose identity" in (
        completed.stderr
    )


def test_deploy_production_exits_non_zero_when_migrations_fail(tmp_path: Path) -> None:
    project_dir = tmp_path / "production"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    bin_dir.mkdir()
    _write_production_host_contract(project_dir)
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
  *"compose --env-file "*"-f deploy/docker-compose.production.yaml ps -q app"*)
    printf 'app-id\\n'
    ;;
  *"inspect --format "*)
    printf 'healthy\\n'
    ;;
  *"compose --env-file "*"-f deploy/docker-compose.production.yaml run --rm --no-deps app alembic upgrade head"*)
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
    env["COMPOSE_FILE"] = CANONICAL_MANAGED_COMPOSE
    env["CURL_BIN"] = str(bin_dir / "curl")
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
    _write_production_host_contract(project_dir)
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )
    _write_shell_bundle_contract(shell_bundle_dir)
    (shell_bundle_dir / "frontend" / "bundle-marker.txt").write_text(
        "frontend-sync\n", encoding="utf-8"
    )
    (project_dir / "frontend").mkdir()
    (project_dir / "frontend" / "stale.txt").write_text("old-shell\n", encoding="utf-8")
    (project_dir / "scripts").mkdir()
    (project_dir / "scripts" / "diagnose_web.sh").write_text("stale-diagnose\n", encoding="utf-8")
    (project_dir / "scripts" / "redeploy_caddy.sh").write_text("stale-redeploy\n", encoding="utf-8")

    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\\n' "$*" >> "{log_file}"
case "$*" in
  *"compose --env-file "*"-f deploy/docker-compose.production.yaml run --rm --no-deps app alembic upgrade head"*)
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
    env["COMPOSE_FILE"] = CANONICAL_MANAGED_COMPOSE
    env["CURL_BIN"] = str(bin_dir / "curl")
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
    assert (project_dir / "frontend" / "stale.txt").read_text(encoding="utf-8") == "old-shell\n"
    assert not (project_dir / "frontend" / "bundle-marker.txt").exists()
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
    _write_production_host_contract(project_dir)
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
    env["COMPOSE_FILE"] = CANONICAL_MANAGED_COMPOSE
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
    _write_production_host_contract(
        project_dir,
        compose_text=(
            "services:\n  app:\n    depends_on:\n      postgres:\n"
            "        condition: service_healthy\n  postgres:\n    image: postgres:16\n"
        ),
    )
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
    )

    docker_stub = """#!/usr/bin/env bash
set -euo pipefail
case "$*" in
  *"config --services"*) printf 'app\npostgres\n' ;;
esac
"""
    _write_executable(bin_dir / "docker", docker_stub)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DOCKER_BIN"] = str(bin_dir / "docker")
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = CANONICAL_MANAGED_COMPOSE
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
    assert "Managed production Compose must not contain a local postgres service" in (
        completed.stderr
    )


def test_deploy_production_accepts_only_explicit_exact_self_hosted_database_contour(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "production"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "docker.log"
    project_dir.mkdir()
    bin_dir.mkdir()
    _write_production_host_contract(
        project_dir,
        compose_text=SELF_HOSTED_COMPOSE_PATH.read_text(encoding="utf-8"),
        self_hosted=True,
    )
    (project_dir / ".env").write_text(
        "\n".join(
            (
                "DATABASE_URL=postgresql+psycopg://stale:managed@db.example.com/db",  # pragma: allowlist secret
                "POSTGRES_DB=pulseplate",
                "POSTGRES_USER=pulseplate",
                "POSTGRES_PASSWORD=test-only",  # pragma: allowlist secret
            )
        )
        + "\n",
        encoding="utf-8",
    )
    docker_stub = f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\n' "$*" >> "{log_file}"
case "$*" in
  *"config --services"*) printf 'app\ncaddy\npostgres\nprometheus\nworker\n' ;;
esac
"""
    _write_executable(bin_dir / "docker", docker_stub)
    _write_executable(bin_dir / "curl", "#!/usr/bin/env bash\nset -euo pipefail\n")

    env = os.environ.copy()
    env.update(
        {
            "DOCKER_BIN": str(bin_dir / "docker"),
            "CURL_BIN": str(bin_dir / "curl"),
            "DEPLOY_DIR": str(project_dir),
            "ENV_FILE": str(project_dir / ".env"),
            "COMPOSE_FILE": CANONICAL_SELF_HOSTED_COMPOSE,
            "PRODUCTION_DOMAIN": "pulseplate.test",
        }
    )
    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh"), "--preflight-only"],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "Production deploy preflight passed" in completed.stdout

    env.pop("COMPOSE_FILE")
    env["PROD_DEPLOY_MODE"] = "self-hosted"
    completed = subprocess.run(
        [str(REPO_ROOT / "scripts/deploy_production.sh"), "--preflight-only"],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 1
    assert "RESOLVED_COMPOSE_FILE does not exist" in completed.stderr


def test_deploy_production_does_not_require_home_when_docker_bin_is_explicit(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "production"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    bin_dir.mkdir()
    _write_production_host_contract(project_dir)
    (project_dir / ".env").write_text(
        "DATABASE_URL=postgresql+psycopg://pulseplate:secret@db.example.com:25060/pulseplate\n",  # pragma: allowlist secret
        encoding="utf-8",
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
    env.pop("HOME", None)
    env["DEPLOY_DIR"] = str(project_dir)
    env["ENV_FILE"] = str(project_dir / ".env")
    env["COMPOSE_FILE"] = CANONICAL_MANAGED_COMPOSE
    env["CURL_BIN"] = str(bin_dir / "curl")
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
    static_css_calls = [
        line
        for line in log_output.splitlines()
        if "https://pulseplate.test/assets/index-test.css" in line
    ]
    assert static_css_calls
    assert all("CF-Access-Client-" not in line for line in static_css_calls)
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


def _staging_deploy_fixture(tmp_path: Path) -> tuple[dict[str, str], Path]:
    project_dir = tmp_path / "staging"
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "deploy.log"
    project_dir.mkdir()
    bin_dir.mkdir()
    (project_dir / "scripts" / "ops").mkdir(parents=True)
    (project_dir / "prometheus").mkdir()
    (project_dir / "secrets").mkdir()
    (project_dir / "secrets").chmod(0o700)
    (project_dir / "backups").mkdir()
    (project_dir / "docker-compose.staging.yaml").write_text(
        "services: {app: {}, caddy: {}}\n", encoding="utf-8"
    )
    (project_dir / "Caddyfile").write_text(":80 { respond ok }\n", encoding="utf-8")
    (project_dir / "prometheus" / "prometheus.yml").write_text(
        PROMETHEUS_CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (project_dir / "prometheus" / "image-manifest.json").write_text(
        PROMETHEUS_MANIFEST_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (project_dir / "secrets" / "pulseplate_metrics_scrape_key").write_text(
        METRICS_SECRET_SENTINEL, encoding="ascii"
    )
    (project_dir / "secrets" / "pulseplate_metrics_scrape_key").chmod(0o444)
    (project_dir / ".attested-digest-deploy-v1").write_text(
        "pulseplate-staging-attested-digest-v1", encoding="utf-8"
    )
    (project_dir / ".env").write_text(
        "\n".join(
            (
                "STAGING_DOMAIN=staging.example.com",
                "POSTGRES_USER=pulseplate",
                "POSTGRES_DB=pulseplate",
                "POSTGRES_PASSWORD=test-only",  # pragma: allowlist secret
                "DATABASE_URL=postgresql+psycopg://pulseplate:test-only@postgres/pulseplate",  # pragma: allowlist secret
                "GHCR_USER=pulseplate-ci",
                "GHCR_TOKEN=test-only-token",  # pragma: allowlist secret
                "STAGING_IMAGE_REF=ghcr.io/attacker/override:latest",
                "STAGING_CADDY_IMAGE_REF=ghcr.io/attacker/override:latest",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    (project_dir / ".env").chmod(0o600)
    _write_executable(
        project_dir / "scripts" / "ops" / "postgres_backup.sh",
        f"""#!/usr/bin/env bash
printf 'backup docker=%s args=%s\\n' "${{DOCKER_BIN:-}}" "$*" >> "{log_file}"
""",
    )
    _write_executable(
        bin_dir / "docker",
        f"""#!/usr/bin/env bash
set -euo pipefail
printf 'docker %s\n' "$*" >> "{log_file}"
printf 'env backend=%s caddy=%s config=%s\n' "${{STAGING_IMAGE_REF:-}}" "${{STAGING_CADDY_IMAGE_REF:-}}" "${{DOCKER_CONFIG:-}}" >> "{log_file}"
case "$*" in
  *"login ghcr.io"*"--password-stdin"*) cat >/dev/null ;;
  *"info --format"*"Architecture"*) printf 'amd64\n' ;;
  *"ps -q postgres"*) printf 'postgres-id\n' ;;
  *"inspect --format"*) printf 'healthy\n' ;;
  *"ps -q app"*) printf 'app-id\n' ;;
  *"run --rm --no-deps app alembic upgrade head"*)
    if [[ "${{STUB_MIGRATION_FAILURE:-0}}" == "1" ]]; then
      exit 42
    fi
    ;;
esac
""",
    )
    _write_executable(
        bin_dir / "stat",
        """#!/usr/bin/env bash
set -euo pipefail
case "${*: -1}" in
  *.attested-digest-deploy-v1) printf '0:0:644\\n' ;;
  *.env) printf '%s\\n' "${STUB_ENV_MODE:-600}" ;;
  *postgres_backup.sh) printf '%s\\n' "${STUB_HELPER_MODE:-755}" ;;
  */secrets) printf '%s\\n' "${STUB_SECRET_DIR_METADATA:-$EUID:700}" ;;
  *pulseplate_metrics_scrape_key) printf '%s\\n' "${STUB_SECRET_FILE_METADATA:-$EUID:444}" ;;
  *) exit 1 ;;
esac
""",
    )
    _write_executable(
        bin_dir / "curl",
        f'#!/usr/bin/env bash\nprintf \'curl %s\\n\' "$*" >> "{log_file}"\n',
    )
    _write_executable(bin_dir / "sleep", "#!/usr/bin/env bash\nexit 0\n")

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "PROJECT_DIR": str(project_dir),
            "ENV_FILE": str(project_dir / ".env"),
            "COMPOSE_FILE": str(project_dir / "docker-compose.staging.yaml"),
            "BACKUP_DIR": str(project_dir / "backups"),
            "BACKUP_HELPER": str(project_dir / "scripts" / "ops" / "postgres_backup.sh"),
            "STAGING_DEPLOY_MARKER": str(project_dir / ".attested-digest-deploy-v1"),
            "DOCKER_BIN": str(bin_dir / "docker"),
            "PYTHON_BIN": sys.executable,
            "CURL_BIN": str(bin_dir / "curl"),
            "STAT_BIN": str(bin_dir / "stat"),
            "STAGING_DOMAIN": "staging.example.com",
            "GHCR_USER": "pulseplate-ci",
            "GHCR_TOKEN": "test-only-token",  # pragma: allowlist secret
            "HEALTH_MAX_ATTEMPTS": "1",
            "HEALTH_SLEEP_S": "0",
        }
    )
    return env, log_file


@pytest.mark.parametrize(
    "arguments",
    (
        (),
        ("latest",),
        ("ghcr.io/katsiarynakavaleuskaya/pulseplate:abc", "caddy:2.11.4"),
        (
            "docker.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64,
            "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64,
        ),
        (
            "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "A" * 64,
            "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64,
        ),
        (
            "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64,
            "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64,
        ),
        (
            "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64,
            "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64,
            "unexpected",
        ),
    ),
)
def test_staging_deploy_rejects_unsafe_image_references_before_side_effects(
    tmp_path: Path,
    arguments: tuple[str, ...],
) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts" / "deploy.sh"), *arguments],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert not log_file.exists()


def test_staging_deploy_preflight_validates_contract_without_mutation(tmp_path: Path) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)
    backend_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64

    completed = subprocess.run(
        [
            str(REPO_ROOT / "scripts" / "deploy.sh"),
            "--preflight-only",
            backend_ref,
            caddy_ref,
        ],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any(line == "docker info --format {{.Architecture}}" for line in log_lines)
    assert any("compose --env-file" in line and "config --quiet" in line for line in log_lines)
    assert not any("login" in line or "pull" in line or "up -d" in line for line in log_lines)
    assert "Staging deploy preflight passed" in completed.stdout


@pytest.mark.parametrize(
    ("scheduler_mode_value", "expected_returncode"),
    (
        ("external # scheduler owner", 0),
        (" disabled\t# maintenance window", 0),
        ("external#not-a-compose-comment", 1),
        ('"external"', 1),
        ("'external'", 1),
        ("${SCHEDULER_MODE}", 1),
    ),
)
def test_staging_deploy_matches_bounded_compose_scheduler_mode_syntax(
    tmp_path: Path,
    scheduler_mode_value: str,
    expected_returncode: int,
) -> None:
    env, _log_file = _staging_deploy_fixture(tmp_path)
    env.pop("FOOD_UPDATE_SCHEDULER_MODE", None)
    env_file = Path(env["ENV_FILE"])
    with env_file.open("a", encoding="utf-8") as handle:
        handle.write(f"FOOD_UPDATE_SCHEDULER_MODE={scheduler_mode_value}\n")
    backend_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64

    completed = subprocess.run(
        [
            str(REPO_ROOT / "scripts" / "deploy.sh"),
            "--preflight-only",
            backend_ref,
            caddy_ref,
        ],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == expected_returncode, completed.stderr
    if expected_returncode == 0:
        assert "Staging deploy preflight passed" in completed.stdout
    else:
        assert "FOOD_UPDATE_SCHEDULER_MODE must be exactly external or disabled" in completed.stderr


def test_staging_deploy_preserves_backup_migration_caddy_order_and_cli_identity(
    tmp_path: Path,
) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)
    backend_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts" / "deploy.sh"), backend_ref, caddy_ref],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    login_index = _assert_log_index(
        log_lines, predicate=lambda line: "docker login ghcr.io" in line, message="missing login"
    )
    pull_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "compose " in line and " pull app caddy prometheus" in line,
        message="missing exact app, Caddy, and Prometheus pull",
    )
    image_inspect_index = _assert_log_index(
        log_lines,
        predicate=lambda line: line.startswith("docker image inspect "),
        message="missing pulled Prometheus platform manifest validation",
    )
    backup_index = _assert_log_index(
        log_lines, predicate=lambda line: line.startswith("backup "), message="missing backup"
    )
    postgres_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "compose " in line and " up -d postgres" in line,
        message="missing Postgres bootstrap",
    )
    quiesce_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "compose " in line and " stop caddy app" in line,
        message="missing app/Caddy quiesce",
    )
    migration_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "compose " in line
        and " run --rm --no-deps app alembic upgrade head" in line,
        message="missing one-shot migration",
    )
    app_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "compose " in line and " up -d --pull never app" in line,
        message="missing app start",
    )
    caddy_index = _assert_log_index(
        log_lines,
        predicate=lambda line: "compose " in line and " up -d --pull never caddy" in line,
        message="missing Caddy start",
    )
    assert (
        login_index
        < pull_index
        < image_inspect_index
        < postgres_index
        < backup_index
        < quiesce_index
        < migration_index
        < app_index
        < caddy_index
    )
    assert all("up -d --pull never postgres" not in line for line in log_lines)
    assert f"backup docker={env['DOCKER_BIN']}" in log_lines[backup_index]

    env_lines = [line for line in log_lines if line.startswith("env backend=")]
    assert env_lines
    assert all(f"backend={backend_ref}" in line for line in env_lines)
    assert all(f"caddy={caddy_ref}" in line for line in env_lines)
    docker_config = env_lines[-1].split(" config=", 1)[1]
    assert docker_config
    assert not Path(docker_config).exists()


def test_staging_deploy_migration_failure_keeps_app_and_caddy_stopped(tmp_path: Path) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)
    env["STUB_MIGRATION_FAILURE"] = "1"
    backend_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64

    completed = subprocess.run(
        [str(REPO_ROOT / "scripts" / "deploy.sh"), backend_ref, caddy_ref],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 42
    assert "Caddy and app remain stopped" in completed.stderr
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert any(" stop caddy app" in line for line in log_lines)
    assert any(" run --rm --no-deps app alembic upgrade head" in line for line in log_lines)
    assert not any(" up -d --pull never app" in line for line in log_lines)
    assert not any(" up -d --pull never caddy" in line for line in log_lines)


def test_staging_deploy_treats_env_file_as_data_and_drops_registry_credentials(
    tmp_path: Path,
) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)
    project_dir = Path(env["PROJECT_DIR"])
    command_marker = tmp_path / "env-was-executed"
    with (project_dir / ".env").open("a", encoding="utf-8") as handle:
        handle.write("COMPOSE_FILE=/tmp/attacker-compose.yaml\n")
        handle.write(f'ENV_EXECUTION_PROBE=$(touch "{command_marker}")\n')

    backend_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64
    completed = subprocess.run(
        [str(REPO_ROOT / "scripts" / "deploy.sh"), backend_ref, caddy_ref],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert not command_marker.exists()
    log_lines = log_file.read_text(encoding="utf-8").splitlines()
    assert all("/tmp/attacker-compose.yaml" not in line for line in log_lines)
    logout_index = _assert_log_index(
        log_lines,
        predicate=lambda line: line == "docker logout ghcr.io",
        message="missing registry logout",
    )
    backup_index = _assert_log_index(
        log_lines, predicate=lambda line: line.startswith("backup "), message="missing backup"
    )
    assert logout_index < backup_index


@pytest.mark.parametrize(
    "invalid_boundary",
    (
        "env-symlink",
        "env-mode",
        "compose-symlink",
        "caddy-symlink",
        "prometheus-config-symlink",
        "prometheus-manifest-symlink",
        "secret-dir-symlink",
        "secret-file-symlink",
        "secret-dir-mode",
        "secret-file-mode",
        "secret-dir-owner",
        "secret-file-owner",
        "helper-symlink",
        "helper-mode",
    ),
)
def test_staging_deploy_rejects_invalid_local_control_files_before_docker_side_effects(
    tmp_path: Path,
    invalid_boundary: str,
) -> None:
    env, log_file = _staging_deploy_fixture(tmp_path)
    project_dir = Path(env["PROJECT_DIR"])
    env_file = project_dir / ".env"
    compose_file = project_dir / "docker-compose.staging.yaml"
    caddyfile = project_dir / "Caddyfile"
    prometheus_config = project_dir / "prometheus" / "prometheus.yml"
    prometheus_manifest = project_dir / "prometheus" / "image-manifest.json"
    secret_dir = project_dir / "secrets"
    secret_file = secret_dir / "pulseplate_metrics_scrape_key"
    backup_helper = Path(env["BACKUP_HELPER"])

    if invalid_boundary == "env-symlink":
        real_env = project_dir / ".env.real"
        env_file.rename(real_env)
        env_file.symlink_to(real_env)
    elif invalid_boundary == "env-mode":
        env["STUB_ENV_MODE"] = "644"
    elif invalid_boundary == "compose-symlink":
        real_compose = compose_file.with_suffix(".real")
        compose_file.rename(real_compose)
        compose_file.symlink_to(real_compose)
    elif invalid_boundary == "caddy-symlink":
        real_caddyfile = caddyfile.with_suffix(".real")
        caddyfile.rename(real_caddyfile)
        caddyfile.symlink_to(real_caddyfile)
    elif invalid_boundary == "prometheus-config-symlink":
        real_config = prometheus_config.with_suffix(".real")
        prometheus_config.rename(real_config)
        prometheus_config.symlink_to(real_config)
    elif invalid_boundary == "prometheus-manifest-symlink":
        real_manifest = prometheus_manifest.with_suffix(".real")
        prometheus_manifest.rename(real_manifest)
        prometheus_manifest.symlink_to(real_manifest)
    elif invalid_boundary == "secret-dir-symlink":
        real_secret_dir = project_dir / "secrets.real"
        secret_dir.rename(real_secret_dir)
        secret_dir.symlink_to(real_secret_dir, target_is_directory=True)
    elif invalid_boundary == "secret-file-symlink":
        real_secret_file = secret_dir / "pulseplate_metrics_scrape_key.real"
        secret_file.rename(real_secret_file)
        secret_file.symlink_to(real_secret_file)
    elif invalid_boundary == "secret-dir-mode":
        env["STUB_SECRET_DIR_METADATA"] = f"{os.geteuid()}:755"
    elif invalid_boundary == "secret-file-mode":
        env["STUB_SECRET_FILE_METADATA"] = f"{os.geteuid()}:400"
    elif invalid_boundary == "secret-dir-owner":
        env["STUB_SECRET_DIR_METADATA"] = "999:700"
    elif invalid_boundary == "secret-file-owner":
        env["STUB_SECRET_FILE_METADATA"] = "999:444"
    elif invalid_boundary == "helper-symlink":
        real_helper = backup_helper.with_suffix(".real")
        backup_helper.rename(real_helper)
        backup_helper.symlink_to(real_helper)
    else:
        backup_helper.chmod(0o777)
        env["STUB_HELPER_MODE"] = "777"

    backend_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "a" * 64
    caddy_ref = "ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:" + "b" * 64
    completed = subprocess.run(
        [str(REPO_ROOT / "scripts" / "deploy.sh"), backend_ref, caddy_ref],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert not log_file.exists()


def test_staging_deploy_readiness_probe_has_per_request_timeout() -> None:
    deploy_script = (REPO_ROOT / "scripts" / "deploy.sh").read_text(encoding="utf-8")

    assert "urlopen('http://localhost:8000/ready', timeout=5).read()" in deploy_script


def test_obs1b_deploy_scripts_keep_canonical_guard_product_first_and_non_destructive() -> None:
    staging_script = (REPO_ROOT / "scripts" / "deploy.sh").read_text(encoding="utf-8")
    production_script = (REPO_ROOT / "scripts" / "deploy_production.sh").read_text(encoding="utf-8")
    canonical_guard = (
        "from app.main import app; from app.security.production_invariants import "
        "assert_production_runtime_invariants; assert_production_runtime_invariants(app=app)"
    )
    for script in (staging_script, production_script):
        assert canonical_guard in script
        assert "assert_production_runtime_invariants()" not in script
        assert "|| true" not in script
        assert "down -v" not in script
        assert "volume rm" not in script
        assert "volume prune" not in script
        assert 'cat "$METRICS_SECRET_FILE"' not in script
        assert 'source "$METRICS_SECRET_FILE"' not in script
        assert script.index(canonical_guard) < script.index("alembic upgrade head")
        assert "/bin/promtool check ready" in script
        assert "/bin/promtool check healthy" in script
    assert staging_script.index("up -d --pull never caddy") < staging_script.index(
        "up -d --pull never prometheus"
    )
    assert production_script.index("up -d --remove-orphans caddy") < production_script.index(
        "up -d --pull never prometheus"
    )
