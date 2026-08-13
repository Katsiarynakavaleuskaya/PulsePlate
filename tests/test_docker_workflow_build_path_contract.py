"""Regression guards for the Docker workflow build-path consolidation contract."""

from __future__ import annotations

from datetime import date
from hashlib import sha3_256
import json
from pathlib import Path
from urllib.parse import urlparse

from fastapi.testclient import TestClient
import pytest
import yaml

from scripts.ci import fetch_docker_source_artifacts as docker_sources

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
BACKEND_PYTHON_BASE_IMAGE = (
    "python:3.13.14-slim-bookworm"
    "@sha256:9d7f287598e1a5a978c015ee176d8216435aaf335ed69ac3c38dd1bbb10e8d64"
)
EXPECTED_BACKEND_PYTHON_FROM_LINES = (
    f"FROM {BACKEND_PYTHON_BASE_IMAGE} AS builder",
    f"FROM {BACKEND_PYTHON_BASE_IMAGE} AS sqlite-builder",
    f"FROM {BACKEND_PYTHON_BASE_IMAGE} AS runtime-base",
)
EXPECTED_DOCKER_SOURCE_PREP_BUILD_STEPS = {
    ("build.yml", "build", "Build Docker image (local, for tests)"),
    ("build.yml", "publish", "Build Docker image for publish scan"),
    ("trivy.yml", "build", "Build Docker image (production target)"),
    ("cd.yml", "build", "Build & Push backend image (staging)"),
    ("cd.yml", "build-production", "Build & Push image (production)"),
}


def _load_workflow(path: Path) -> dict[str, object]:
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(workflow, dict)
    return workflow


def _step_names(job: dict[str, object]) -> list[str]:
    steps = job.get("steps")
    assert isinstance(steps, list)
    names: list[str] = []
    for step in steps:
        assert isinstance(step, dict)
        name = step.get("name")
        if isinstance(name, str):
            names.append(name)
    return names


def _step_by_name(job: dict[str, object], step_name: str) -> dict[str, object]:
    steps = job.get("steps")
    assert isinstance(steps, list)
    for step in steps:
        assert isinstance(step, dict)
        if step.get("name") == step_name:
            return step
    raise AssertionError(f"missing step {step_name!r}")


def _step_index(job: dict[str, object], step_name: str) -> int:
    return _step_names(job).index(step_name)


def _root_context_docker_build_steps(
    workflow: dict[str, object],
) -> list[tuple[str, dict[str, object], str]]:
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    build_steps: list[tuple[str, dict[str, object], str]] = []
    for job_name, job in jobs.items():
        assert isinstance(job_name, str)
        if not isinstance(job, dict):
            continue
        steps = job.get("steps")
        if not isinstance(steps, list):
            continue
        for step in steps:
            assert isinstance(step, dict)
            uses = step.get("uses")
            if not (isinstance(uses, str) and uses.startswith("docker/build-push-action@")):
                continue
            step_with = step.get("with")
            assert isinstance(
                step_with,
                dict,
            ), f"{job_name}/{step.get('name')} must define docker build inputs"
            context = step_with.get("context")
            if context != ".":
                # Frontend/Caddy builds do not consume the backend SQLite source bundle.
                continue
            step_name = step.get("name")
            assert isinstance(step_name, str)
            build_steps.append((job_name, job, step_name))
    return build_steps


def _docker_source_manifest(
    *,
    payload: bytes = b"sqlite source",
    review_by: str = "2026-06-28",
    filename: str = "sqlite-autoconf-3530200.tar.gz",
    url: str = "https://sqlite.org/2026/sqlite-autoconf-3530200.tar.gz",
) -> dict[str, object]:
    digest = sha3_256(payload).hexdigest()
    return {
        "schema_version": 1,
        "generated_at": "2026-06-14",
        "review_by": review_by,
        "artifacts": [
            {
                "name": "sqlite-autoconf",
                "version": "3530200",
                "filename": filename,
                "url": url,
                "sha3_256_parts": [digest[index : index + 8] for index in range(0, len(digest), 8)],
            }
        ],
    }


def _write_docker_source_manifest(tmp_path: Path, manifest: dict[str, object]) -> Path:
    manifest_path = tmp_path / "docker_source_artifacts.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


def test_removed_duplicate_docker_pr_workflows() -> None:
    """PR-time production image validation stays in the canonical Docker workflow."""
    assert not (WORKFLOWS_DIR / "docker-image.yml").exists()
    assert not (WORKFLOWS_DIR / "docker-openapi-smoke.yml").exists()


def test_build_workflow_owns_docker_validation_contract() -> None:
    """Build workflow keeps runtime, telemetry, budget, and OpenAPI smoke checks together."""
    workflow = _load_workflow(WORKFLOWS_DIR / "build.yml")
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)

    build_job = jobs["build"]
    assert isinstance(build_job, dict)
    step_names = _step_names(build_job)

    assert "Build Docker image (local, for tests)" in step_names
    assert "Check Docker runtime dependency surface" in step_names
    assert "Collect Docker image telemetry" in step_names
    assert "Enforce Docker image budget" in step_names
    assert "Test Docker image" in step_names

    test_step = next(
        step
        for step in build_job["steps"]
        if isinstance(step, dict) and step.get("name") == "Test Docker image"
    )
    build_step = next(
        step
        for step in build_job["steps"]
        if isinstance(step, dict) and step.get("name") == "Build Docker image (local, for tests)"
    )
    build_step_with = build_step["with"]
    assert isinstance(build_step_with, dict)
    assert build_step_with["target"] == "production"
    assert build_step_with["load"] is True
    assert build_step_with["push"] is False
    assert build_step_with["provenance"] is False

    run_script = test_step["run"]
    assert isinstance(run_script, str)
    assert "openapi.json" in run_script
    assert "/api/v1/bmi" in run_script
    assert (
        'assert "/api/v1/bodyfat" not in paths, '
        '"/api/v1/bodyfat must not leak into canonical OpenAPI"'
    ) in run_script


def test_build_workflow_does_not_expose_github_token_to_pr_baseline_script() -> None:
    """PR builds must not pass workflow tokens to checked-out baseline code."""
    workflow = _load_workflow(WORKFLOWS_DIR / "build.yml")
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    build_job = jobs["build"]
    assert isinstance(build_job, dict)
    steps = build_job["steps"]
    assert isinstance(steps, list)

    fallback_step = next(
        step
        for step in steps
        if isinstance(step, dict)
        and step.get("name") == "Use checked-in Docker image telemetry baseline on pull requests"
    )
    assert fallback_step["if"] == "github.event_name == 'pull_request'"
    fallback_run = fallback_step["run"]
    assert isinstance(fallback_run, str)
    assert "fetch_docker_image_baseline.py" not in fallback_run
    assert "GH_TOKEN" not in fallback_step.get("env", {})
    assert "GITHUB_TOKEN" not in fallback_step.get("env", {})

    resolve_step = next(
        step
        for step in steps
        if isinstance(step, dict) and step.get("name") == "Resolve Docker image telemetry baseline"
    )
    assert resolve_step["if"] == "github.event_name != 'pull_request'"
    resolve_env = resolve_step["env"]
    assert isinstance(resolve_env, dict)
    assert resolve_env["GH_TOKEN"] == "${{ secrets.GITHUB_TOKEN }}"
    assert resolve_env["GITHUB_TOKEN"] == "${{ secrets.GITHUB_TOKEN }}"


def test_production_dockerfile_prunes_package_manager_surface() -> None:
    """Production target removes package-manager, gzip, ACL/attr, and Perl runtime packages."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    production_section = dockerfile.split("FROM runtime-base AS production", 1)[1]
    production_section = production_section.split("FROM production AS staging", 1)[0]
    pruning_block = production_section.split(
        "# SECURITY: production-package-pruning-start",
        1,
    )[
        1
    ].split("# SECURITY: production-package-pruning-end", 1)[0]

    assert "dpkg --purge --force-depends --force-remove-essential" in pruning_block
    assert "perl_module_packages=" in pruning_block
    assert "'perl-modules-*'" in pruning_block
    assert (
        "for package in apt gzip gpgv libacl1 libattr1 libgnutls30 "
        "libsqlite3-0 perl-base ${perl_module_packages}; do"
    ) in pruning_block
    for package in (
        "apt",
        "gzip",
        "gpgv",
        "libacl1",
        "libattr1",
        "libgnutls30",
        "libsqlite3-0",
        "perl-base",
    ):
        assert f"        {package} \\" in pruning_block
        assert f" {package} " in pruning_block
    assert "dpkg-query -W -f='${db:Status-Abbrev}'" in pruning_block
    assert "for binary in gzip gunzip zcat" in pruning_block
    assert 'command -v "${binary}"' in pruning_block
    assert "import gzip" in pruning_block
    assert "gzip.compress(payload, mtime=0)" in pruning_block
    assert "import ssl" in pruning_block
    assert "import sqlite3" in pruning_block
    assert "expected >= 3.53.2" in pruning_block


def test_build_workflow_blocks_removed_acl_attr_runtime_packages() -> None:
    """Docker runtime surface guard fails if removed packages return."""
    workflow = _load_workflow(WORKFLOWS_DIR / "build.yml")
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    build_job = jobs["build"]
    assert isinstance(build_job, dict)

    surface_step = _step_by_name(build_job, "Check Docker runtime dependency surface")
    run_script = surface_step["run"]
    assert isinstance(run_script, str)

    for package in ("gzip", "libacl1", "libattr1"):
        assert f"--blocked-debian-package {package}" in run_script


def test_dockerfile_pins_all_backend_python_stages_to_one_oci_index() -> None:
    """All external Python stages use the same immutable, ordered base."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    trivyignore = (REPO_ROOT / ".trivyignore").read_text(encoding="utf-8")
    python_from_lines = tuple(
        line.strip()
        for line in dockerfile.splitlines()
        if line.lstrip().casefold().startswith("from ") and "python" in line.casefold()
    )

    assert len(python_from_lines) == 3
    assert python_from_lines == EXPECTED_BACKEND_PYTHON_FROM_LINES
    assert "3.13.13" not in dockerfile
    assert f"FROM {BACKEND_PYTHON_BASE_IMAGE.partition('@')[0]} AS" not in dockerfile
    assert BACKEND_PYTHON_BASE_IMAGE.partition("@")[0] in trivyignore
    assert "3.13.13" not in trivyignore


def test_dockerfile_builds_verified_sqlite_runtime_library() -> None:
    """Dockerfile builds pre-fetched SQLite 3.53.2 before removing Debian SQLite."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    dockerignore = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
    sqlite_builder_section = dockerfile.split("AS sqlite-builder", 1)[1]
    sqlite_builder_section = sqlite_builder_section.split("FROM python", 1)[0]
    runtime_base_section = dockerfile.split(
        f"FROM {BACKEND_PYTHON_BASE_IMAGE} AS runtime-base",
        1,
    )[1]
    runtime_base_section = runtime_base_section.split("COPY --from=builder", 1)[0]

    assert 'ARG SQLITE_AUTOCONF_VERSION="3530200"' in dockerfile
    assert "SQLite source pins are intentionally mirrored" in dockerfile
    assert "Docker COPY source paths are literal" in dockerfile
    checksum_parts = (
        "025328da",
        "165109f4",
        "8abccc6e",
        "74785080",
        "60804412",
        "bed2bd81",
        "d47e98ba",
        "1b72983b",
    )
    for index, checksum_part in enumerate(checksum_parts, start=1):
        assert f'ARG SQLITE_AUTOCONF_SHA3_256_PART_{index}="{checksum_part}"' in dockerfile
    assert len("".join(checksum_parts)) == 64
    assert 'os.environ[f"SQLITE_AUTOCONF_SHA3_256_PART_{index}"]' in sqlite_builder_section
    assert "urlopen" not in sqlite_builder_section
    assert "urllib" not in sqlite_builder_section
    assert "https://sqlite.org" not in sqlite_builder_section
    assert "COPY build/docker-sources/sqlite-autoconf-3530200.tar.gz" in sqlite_builder_section
    assert "!build/docker-sources/sqlite-autoconf-*.tar.gz" in dockerignore
    assert "sha3_256(payload).hexdigest()" in sqlite_builder_section
    assert "SQLite source SHA3 mismatch" in sqlite_builder_section
    assert "./configure --prefix=/usr/local --disable-static --enable-shared" in dockerfile
    assert "COPY --from=sqlite-builder /usr/local/lib/libsqlite3.so*" in runtime_base_section
    assert "/etc/ld.so.conf.d/00-pulseplate-local-sqlite.conf" in runtime_base_section
    assert "ldconfig" in runtime_base_section
    assert "import sqlite3" in runtime_base_section
    assert "expected >= 3.53.2" in runtime_base_section


def test_docker_source_artifact_manifest_pins_sqlite_source() -> None:
    """Docker source-artifact manifest pins approved SQLite source with SHA3 parts."""
    manifest = json.loads(
        (REPO_ROOT / "scripts/ci/docker_source_artifacts.json").read_text(encoding="utf-8")
    )
    artifacts = manifest["artifacts"]
    assert manifest["schema_version"] == 1
    assert manifest["generated_at"] == "2026-08-13"
    assert manifest["review_by"] == "2026-08-27"
    assert len(artifacts) == 1

    artifact = artifacts[0]
    parsed_url = urlparse(artifact["url"])
    assert artifact["name"] == "sqlite-autoconf"
    assert artifact["version"] == "3530200"
    assert artifact["filename"] == "sqlite-autoconf-3530200.tar.gz"
    assert parsed_url.scheme == "https"
    assert parsed_url.hostname == "sqlite.org"
    assert parsed_url.path == "/2026/sqlite-autoconf-3530200.tar.gz"
    assert artifact["sha3_256_parts"] == [
        "025328da",
        "165109f4",
        "8abccc6e",
        "74785080",
        "60804412",
        "bed2bd81",
        "d47e98ba",
        "1b72983b",
    ]
    assert len("".join(artifact["sha3_256_parts"])) == 64


def test_docker_source_artifact_manifest_review_window_is_inclusive() -> None:
    """The checked-in manifest remains valid through its exact review-by date."""
    manifest_path = REPO_ROOT / "scripts/ci/docker_source_artifacts.json"

    assert docker_sources.load_manifest(manifest_path, today=date(2026, 8, 27))
    with pytest.raises(RuntimeError, match="review_by is stale: 2026-08-27"):
        docker_sources.load_manifest(manifest_path, today=date(2026, 8, 28))


def test_docker_source_artifact_loader_rejects_stale_review_dates(tmp_path: Path) -> None:
    manifest_path = _write_docker_source_manifest(
        tmp_path,
        _docker_source_manifest(review_by="2026-06-13"),
    )

    with pytest.raises(RuntimeError, match="review_by is stale"):
        docker_sources.load_manifest(manifest_path, today=date(2026, 6, 14))


def test_docker_source_artifact_loader_rejects_unsafe_source_metadata(tmp_path: Path) -> None:
    bad_host_manifest = _write_docker_source_manifest(
        tmp_path,
        _docker_source_manifest(url="https://example.com/sqlite-autoconf-3530200.tar.gz"),
    )
    with pytest.raises(RuntimeError, match="source URL must use https"):
        docker_sources.load_manifest(bad_host_manifest, today=date(2026, 6, 14))

    bad_filename_manifest = _write_docker_source_manifest(
        tmp_path,
        _docker_source_manifest(filename="../sqlite-autoconf-3530200.tar.gz"),
    )
    with pytest.raises(RuntimeError, match="safe basename"):
        docker_sources.load_manifest(bad_filename_manifest, today=date(2026, 6, 14))


def test_docker_source_artifact_fetcher_verifies_sha3_and_reuses_existing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = b"verified sqlite source artifact"
    manifest_path = _write_docker_source_manifest(
        tmp_path, _docker_source_manifest(payload=payload)
    )
    artifact = docker_sources.load_manifest(manifest_path, today=date(2026, 6, 14))[0]
    output_dir = tmp_path / "docker-sources"
    calls: list[tuple[str, int]] = []

    class _Response:
        def read(self) -> bytes:
            return payload

    def _urlopen(url: str, *, timeout: int) -> _Response:
        calls.append((url, timeout))
        return _Response()

    monkeypatch.setattr(docker_sources, "urlopen", _urlopen)
    output_path = docker_sources._write_verified_artifact(artifact, output_dir)

    assert output_path == output_dir / "sqlite-autoconf-3530200.tar.gz"
    assert output_path.read_bytes() == payload
    assert output_path.stat().st_mode & 0o777 == 0o644
    assert calls == [("https://sqlite.org/2026/sqlite-autoconf-3530200.tar.gz", 60)]

    def _unexpected_urlopen(_url: str, *, timeout: int) -> _Response:
        raise AssertionError("verified artifact should be reused without a network call")

    monkeypatch.setattr(docker_sources, "urlopen", _unexpected_urlopen)
    reused_path = docker_sources._write_verified_artifact(artifact, output_dir)

    assert reused_path == output_path
    assert output_path.read_bytes() == payload


def test_docker_source_artifact_fetcher_rejects_digest_mismatches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path = _write_docker_source_manifest(
        tmp_path,
        _docker_source_manifest(payload=b"expected sqlite source artifact"),
    )
    artifact = docker_sources.load_manifest(manifest_path, today=date(2026, 6, 14))[0]

    class _Response:
        def read(self) -> bytes:
            return b"tampered sqlite source artifact"

    monkeypatch.setattr(docker_sources, "urlopen", lambda _url, *, timeout: _Response())

    with pytest.raises(RuntimeError, match="SHA3 mismatch"):
        docker_sources._write_verified_artifact(artifact, tmp_path / "docker-sources")

    assert not (tmp_path / "docker-sources" / "sqlite-autoconf-3530200.tar.gz").exists()


def test_docker_build_workflows_prefetch_source_artifacts_before_build() -> None:
    """Docker workflows prepare source artifacts explicitly before image build actions."""
    checked_steps: set[tuple[str, str, str]] = set()

    for workflow_name in ("build.yml", "trivy.yml", "cd.yml"):
        workflow = _load_workflow(WORKFLOWS_DIR / workflow_name)
        for job_name, job, build_step_name in _root_context_docker_build_steps(workflow):
            prepare_step = _step_by_name(job, "Prepare Docker source artifacts")
            prepare_run = prepare_step["run"]
            assert isinstance(prepare_run, str)
            assert "set -euo pipefail" in prepare_run
            assert "python3 scripts/ci/fetch_docker_source_artifacts.py" in prepare_run
            assert _step_index(job, "Prepare Docker source artifacts") < _step_index(
                job,
                build_step_name,
            )
            checked_steps.add((workflow_name, job_name, build_step_name))

    assert EXPECTED_DOCKER_SOURCE_PREP_BUILD_STEPS <= checked_steps


def test_makefile_docker_build_targets_prefetch_source_artifacts() -> None:
    """Local Docker Make targets prepare source artifacts before Docker builds."""
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    assert "docker-source-artifacts: ## Prepare verified Docker source artifacts" in makefile
    assert "$(DEV_PYTHON) scripts/ci/fetch_docker_source_artifacts.py" in makefile
    assert (
        "docker-build: ensure-python-proxy docker-source-artifacts ## Build production Docker image"
        in makefile
    )
    assert (
        "docker-build-dev: ensure-python-proxy docker-source-artifacts ## Build development Docker image"
        in makefile
    )


def test_runtime_base_requires_fixed_bookworm_glibc_line() -> None:
    """Runtime base fails closed if libc stays below the CVE-2025-8058 fix."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    runtime_base_section = dockerfile.split(
        f"FROM {BACKEND_PYTHON_BASE_IMAGE} AS runtime-base",
        1,
    )[1]
    runtime_base_section = runtime_base_section.split("COPY --from=builder", 1)[0]

    assert "libc-bin" in runtime_base_section
    assert "libc6" in runtime_base_section
    assert 'dpkg --compare-versions "${version}" ge "2.36-9+deb12u13"' in runtime_base_section
    assert "below fixed glibc line 2.36-9+deb12u13" in runtime_base_section


def test_docker_runtime_surface_guard_blocks_perl_runtime_packages() -> None:
    """Docker workflows fail if production keeps Perl runtime packages."""
    for workflow_name, image_ref in (
        ("build.yml", "pulseplate:test"),
        ("trivy.yml", "pulseplate:trivy-scan-${{ github.sha }}"),
    ):
        workflow = _load_workflow(WORKFLOWS_DIR / workflow_name)
        jobs = workflow["jobs"]
        assert isinstance(jobs, dict)
        build_job = jobs["build"]
        assert isinstance(build_job, dict)
        step = _step_by_name(build_job, "Check Docker runtime dependency surface")
        run_script = step["run"]
        assert isinstance(run_script, str)

        assert f"--image {image_ref}" in run_script
        assert "--blocked-debian-package apt" in run_script
        assert "--blocked-debian-package gzip" in run_script
        assert "--blocked-debian-package gpgv" in run_script
        assert "--blocked-debian-package libacl1" in run_script
        assert "--blocked-debian-package libattr1" in run_script
        assert "--blocked-debian-package libgnutls30" in run_script
        assert "--blocked-debian-package libsqlite3-0" in run_script
        assert "--blocked-debian-package perl-base" in run_script
        assert "--blocked-debian-prefix perl-modules-" in run_script


def test_docker_entrypoint_keeps_bodyfat_hidden_but_routable() -> None:
    """Docker entrypoint serves app.main while preserving bodyfat compatibility."""
    from app.main import app

    client = TestClient(app)
    openapi_response = client.get("/openapi.json")
    assert openapi_response.headers.get("content-type", "").startswith("application/json")
    openapi_paths = openapi_response.json()["paths"]

    assert "/api/v1/bodyfat" not in openapi_paths
    response = client.post(
        "/api/v1/bodyfat",
        json={
            "gender": "male",
            "age": 30,
            "waist_cm": 80.0,
            "neck_cm": 38.0,
            "height_m": 1.75,
            "weight_kg": 75.0,
        },
    )

    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("application/json")
    assert {"labels", "lang", "median", "methods"} <= response.json().keys()


def test_trivy_workflow_is_main_push_image_security_lane() -> None:
    """Trivy scans production images on main pushes, schedule, and manual dispatch."""
    workflow = _load_workflow(WORKFLOWS_DIR / "trivy.yml")
    on_section = workflow.get("on", workflow.get(True))
    assert isinstance(on_section, dict)
    push = on_section["push"]
    assert isinstance(push, dict)
    assert push["branches"] == ["main"]
    assert "pull_request" not in on_section
    assert "pull_request_target" not in on_section
    assert "schedule" in on_section
    assert "workflow_dispatch" in on_section

    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    build_job = jobs["build"]
    assert isinstance(build_job, dict)
    scan_step = next(
        step
        for step in build_job["steps"]
        if isinstance(step, dict) and step.get("name") == "Run Trivy vulnerability scanner"
    )
    scan_step_with = scan_step["with"]
    assert isinstance(scan_step_with, dict)
    assert scan_step_with["scan-type"] == "image"
    assert scan_step_with["exit-code"] == "1"
    assert scan_step_with["severity"] == "CRITICAL,HIGH"
    assert scan_step_with["limit-severities-for-sarif"] is True
    assert scan_step_with["ignore-unfixed"] is True
    assert scan_step_with["trivyignores"] == ".trivyignore"
    assert scan_step_with["ignore-policy"] == ".trivy-ignore-policy.rego"
    assert "continue-on-error" not in scan_step
    assert "Fail when Trivy SARIF is missing" in _step_names(build_job)


def test_publish_image_scan_fails_closed() -> None:
    """Publish path image scan blocks HIGH/CRITICAL findings and missing SARIF."""
    workflow = _load_workflow(WORKFLOWS_DIR / "build.yml")
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    publish_job = jobs["publish"]
    assert isinstance(publish_job, dict)
    publish_steps = publish_job["steps"]
    assert isinstance(publish_steps, list)
    build_scan_step = _step_by_name(publish_job, "Build Docker image for publish scan")
    image_ref_step = _step_by_name(publish_job, "Set image ref for SBOM and image scan")
    publish_surface_step = _step_by_name(
        publish_job, "Check Docker publish runtime dependency surface"
    )
    scan_step = _step_by_name(
        publish_job,
        "Run Trivy vulnerability scanner (image scan, fail-closed)",
    )
    fail_sarif_step = _step_by_name(publish_job, "Fail when Trivy image SARIF is missing")
    upload_sarif_step = _step_by_name(publish_job, "Upload Trivy image scan results")
    login_step = _step_by_name(publish_job, "Log in to GHCR")
    push_step = _step_by_name(publish_job, "Push scanned Docker image")
    sbom_step = _step_by_name(publish_job, "Generate SBOM")
    provenance_step = _step_by_name(publish_job, "Attest Docker image provenance")
    attestation_step = _step_by_name(publish_job, "Attest Docker image SBOM")

    assert _step_index(publish_job, "Build Docker image for publish scan") < _step_index(
        publish_job, "Set image ref for SBOM and image scan"
    )
    assert _step_index(publish_job, "Set image ref for SBOM and image scan") < _step_index(
        publish_job, "Check Docker publish runtime dependency surface"
    )
    assert _step_index(
        publish_job, "Check Docker publish runtime dependency surface"
    ) < _step_index(publish_job, "Run Trivy vulnerability scanner (image scan, fail-closed)")
    assert _step_index(
        publish_job, "Run Trivy vulnerability scanner (image scan, fail-closed)"
    ) < _step_index(publish_job, "Fail when Trivy image SARIF is missing")
    assert _step_index(publish_job, "Fail when Trivy image SARIF is missing") < _step_index(
        publish_job, "Upload Trivy image scan results"
    )
    assert _step_index(publish_job, "Upload Trivy image scan results") < _step_index(
        publish_job, "Log in to GHCR"
    )
    assert _step_index(publish_job, "Log in to GHCR") < _step_index(
        publish_job, "Push scanned Docker image"
    )
    assert _step_index(publish_job, "Push scanned Docker image") < _step_index(
        publish_job, "Generate SBOM"
    )

    build_scan_with = build_scan_step["with"]
    assert isinstance(build_scan_with, dict)
    assert build_scan_step["id"] == "docker-build-scan"
    assert build_scan_with["target"] == "production"
    assert build_scan_with["platforms"] == "linux/amd64"
    assert build_scan_with["push"] is False
    assert build_scan_with["load"] is True
    assert build_scan_with["provenance"] is False
    assert "sbom" not in build_scan_with
    assert build_scan_with["tags"] == "${{ steps.meta.outputs.tags }}"
    assert build_scan_with["labels"] == "${{ steps.meta.outputs.labels }}"
    assert (
        "PULSEPLATE_REQUIREMENTS_FILE=requirements-docker-runtime.txt"
        in build_scan_with["build-args"]
    )
    assert "pp_py_index=PULSEPLATE_PYTHON_INDEX_URL" in build_scan_with["secret-envs"]
    assert "pp_py_host=PULSEPLATE_PYTHON_TRUSTED_HOST" in build_scan_with["secret-envs"]

    for step in publish_steps[: _step_index(publish_job, "Fail when Trivy image SARIF is missing")]:
        assert isinstance(step, dict)
        if step.get("uses") == "docker/build-push-action@d08e5c354a6adb9ed34480a06d141179aa583294":
            step_with = step.get("with")
            assert isinstance(step_with, dict)
            assert step_with["push"] is False

    assert "GITHUB_TOKEN" not in build_scan_step.get("env", {})
    assert "GITHUB_TOKEN" not in publish_surface_step.get("env", {})
    assert "GITHUB_TOKEN" not in scan_step.get("env", {})
    assert login_step["uses"].startswith("docker/login-action@")
    assert _step_index(publish_job, "Log in to GHCR") > _step_index(
        publish_job, "Fail when Trivy image SARIF is missing"
    )

    image_ref_run = image_ref_step["run"]
    assert isinstance(image_ref_run, str)
    assert "sha-${{ github.sha }}" in image_ref_run

    publish_surface_run = publish_surface_step["run"]
    assert isinstance(publish_surface_run, str)
    assert "check_docker_runtime_dependency_surface.py" in publish_surface_run
    assert publish_surface_step["env"] == {"IMAGE_REF": "${{ steps.image-ref.outputs.ref }}"}
    assert '--image "${IMAGE_REF}"' in publish_surface_run
    assert "steps.image-ref.outputs.ref" not in publish_surface_run
    assert "--blocked-debian-package gzip" in publish_surface_run
    for package in (
        "apt",
        "gpgv",
        "libacl1",
        "libattr1",
        "libgnutls30",
        "libsqlite3-0",
        "perl-base",
    ):
        assert f"--blocked-debian-package {package}" in publish_surface_run
    assert "--blocked-debian-prefix perl-modules-" in publish_surface_run
    assert "docker-publish-runtime-dependency-surface.json" in publish_surface_run

    scan_step_with = scan_step["with"]
    assert isinstance(scan_step_with, dict)
    assert scan_step_with["scan-type"] == "image"
    assert scan_step_with["image-ref"] == "${{ steps.image-ref.outputs.ref }}"
    assert scan_step_with["exit-code"] == "1"
    assert scan_step_with["severity"] == "CRITICAL,HIGH"
    assert scan_step_with["limit-severities-for-sarif"] is True
    assert scan_step_with["trivyignores"] == ".trivyignore"
    assert scan_step_with["ignore-policy"] == ".trivy-ignore-policy.rego"
    assert "continue-on-error" not in scan_step
    assert fail_sarif_step["if"] == "${{ always() }}"

    assert upload_sarif_step["if"] == "${{ always() && hashFiles('trivy-image.sarif') != '' }}"
    assert push_step["id"] == "docker-build-push"
    push_run = push_step["run"]
    assert isinstance(push_run, str)
    assert "docker image push" in push_run
    assert "steps.meta.outputs.tags" in push_run
    assert "steps.image-ref.outputs.ref" in push_run
    assert "grep -F -m1" in push_run
    assert "GITHUB_OUTPUT" in push_run
    assert "digest=${digest}" in push_run

    assert sbom_step["with"]["image"] == "${{ steps.image-ref.outputs.ref }}"
    assert (
        provenance_step["with"]["subject-digest"] == "${{ steps.docker-build-push.outputs.digest }}"
    )
    assert (
        attestation_step["with"]["subject-digest"]
        == "${{ steps.docker-build-push.outputs.digest }}"
    )
