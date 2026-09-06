#!/usr/bin/env python3
"""Closed cloud-build and local publication controller for one Prometheus candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TypedDict, TypeVar, cast

import yaml

if TYPE_CHECKING or __package__:
    from scripts.ci import _prometheus_derivative_transport as transport
else:
    import _prometheus_derivative_transport as transport
SCHEMA = "pulseplate.prometheus_derivative_candidate.v1"
RECEIPT_SCHEMA = "pulseplate.prometheus_derivative_candidate_receipt.v1"
SCRIPT_VERSION = "1.1.0"
PLATFORM = "linux/amd64"
CONTAINERFILE_RELATIVE = "deploy/prometheus/Containerfile"
SELECTOR_RELATIVE = "deploy/prometheus/image-manifest.json"
TRANSPORT_RELATIVE = "scripts/ci/_prometheus_derivative_transport.py"
RUNTIME_CONSUMER_RELATIVES = (
    "deploy/docker-compose.staging.yaml",
    "deploy/docker-compose.production.yaml",
    "deploy/docker-compose.production.selfhosted.yaml",
)
OFFICIAL_RUNTIME_REF = (
    "prom/prometheus@sha256:"
    "84f0d46e960e86b6965d2e4d99a06f92f176dd75a31ead99126a009891e00f22"  # pragma: allowlist secret
)
EXPECTED_CONTAINERFILE_SHA256 = (
    "b5f6caa104fcf1c4767ef3a13a62a4cf7b58b064beb3dcdf410f08c189e3fe97"  # pragma: allowlist secret
)
EXPECTED_SELECTOR_SHA256 = (
    "06e312ed9efe5ec96a582e7a1ee1291dc02c451f773fb6756fb411ef18ece457"  # pragma: allowlist secret
)
PUBLICATION_INPUT_ENV = "PULSEPLATE_PROMETHEUS_GHCR_TOKEN"
PUBLICATION_REPOSITORY = "ghcr.io/katsiarynakavaleuskaya/pulseplate"
PUBLICATION_TAG_PREFIX = "prometheus-grpc-v1.83.1"
REPOSITORY = "Katsiarynakavaleuskaya/PulsePlate"
REPOSITORY_ID = 1043311030
WORKFLOW_RELATIVE = ".github/workflows/build.yml"
CLOUD_JOB = "prometheus-candidate"
CLOUD_REFERENCE_PREFIX = "docker.io/library/pulseplate-prometheus:verify-"
ORDINARY_JOBS = ("build", "security-scan", "publish")
CLOUD_PROFILE = {
    "runner": "ubuntu-24.04",
    "platform": PLATFORM,
    "python": "3.13.14",
    "pyyaml": "6.0.3",
    "checkout": "de0fac2e4500dabe0009e67214ff5f5447ce83dd",
    "setup_python": "a309ff8b426b58ec0e2a45f0f869d46889d02405",
    "upload_artifact": "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
    "buildx_version": "0.37.0",
    "buildx_sha256": "ae43fa08c796b44efc86d7a63c55f73f7c35f3101188dea7bf93bcd6f99577ba",
    "buildkit_version": "v0.33.0",
    "buildkit_ref": "moby/buildkit@sha256:a461e7f0ce921972028acfbed628d45663d83e67ac1230722c2b34cf72760a0d",
    "buildkit_config_digest": "sha256:41f915d3a122bca46b3da83160cd805697b0faa1bf30b0c0de851eb78f992c70",
    "trivy_version": "0.74.0",
    "trivy_archive_sha256": "2ae6fe3ee734b7fdf11335663e18c75ea12dccc76062f09f164a3b0f8be4371a",
    "trivy_sha256": "d89bcc6510a267f11b773398cbf1be5520ce39f9e8b6633178c4487f05b7d791",
    "source_date_epoch": "1788079847",
    "builds": 2,
    "no_cache": True,
    "cpus": 4,
    "memory_bytes": 6 * 1024 * 1024 * 1024,
    "node_heap_mib": 2048,
    "gomaxprocs": 2,
    "gomemlimit": "3GiB",
    "go_parallelism": 1,
}
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_RECEIPT_BYTES = 1_048_576
MAX_EXECUTABLE_BYTES = 256 * 1024 * 1024
MAX_OCI_ARCHIVE_BYTES = 4 * 1024 * 1024 * 1024
MAX_DATABASE_BYTES = 2 * 1024 * 1024 * 1024
MAX_OCI_MEMBERS = 4096
MAX_OCI_METADATA_BYTES = 4 * 1024 * 1024
CLOUD_MEMBERS = {
    "candidate.oci.tar": MAX_OCI_ARCHIVE_BYTES,
    "build-one.json": MAX_RECEIPT_BYTES,
    "build-two.json": MAX_RECEIPT_BYTES,
    "observations.json": MAX_RECEIPT_BYTES,
    "trivy-report.json": MAX_FILE_BYTES,
}
MAX_CLOUD_ZIP_BYTES = sum(CLOUD_MEMBERS.values()) + MAX_FILE_BYTES


class OCILimits(TypedDict):
    max_archive_bytes: int
    max_members: int
    max_metadata_bytes: int


OCI_LIMITS = OCILimits(
    max_archive_bytes=MAX_OCI_ARCHIVE_BYTES,
    max_members=MAX_OCI_MEMBERS,
    max_metadata_bytes=MAX_OCI_METADATA_BYTES,
)
SHA256_RE = re.compile(r"sha256:[0-9a-f]{64}")
HEX_SHA256_RE = re.compile(r"[0-9a-f]{64}")
RECEIPT_ORDER = (
    "00-spec",
    "10-build-one",
    "20-build-two",
    "30-local-verification",
    "40-publication-authorization",
    "50-write-intent",
    "60-push-result",
    "70-remote-verification",
    "80-final-receipt",
)
RECEIPT_FILES = {stage: f"{stage}.json" for stage in RECEIPT_ORDER}
SCAN_FIELDS = {
    "trivy_version",
    "trivy_executable_sha256",
    "database_identity_sha256",
    "database_updated_at",
    "report_sha256",
    "coverage_sha256",
    "covered_targets",
    "high_count",
    "critical_count",
}
BUILD_OUTPUT_FIELDS = {
    "PULSEPLATE_SOURCE_ARCHIVE_SHA256": "source_archive_sha256",
    "PULSEPLATE_PNPM_BINARY_SHA256": "pnpm_binary_sha256",
    "PULSEPLATE_UI_FILE_COUNT": "ui_file_count",
    "PULSEPLATE_UI_TOTAL_BYTES": "ui_total_bytes",
    "PULSEPLATE_UI_INVENTORY_SHA256": "ui_path_inventory_sha256",
    "PULSEPLATE_UI_TREE_SHA256": "ui_content_tree_sha256",
    "PULSEPLATE_GZIP_TREE_SHA256": "gzip_tree_sha256",
    "PULSEPLATE_EMBED_GO_SHA256": "embed_go_sha256",
    "PULSEPLATE_TRANSFORMED_GO_MOD_SHA256": "transformed_go_mod_sha256",
    "PULSEPLATE_TRANSFORMED_GO_SUM_SHA256": "transformed_go_sum_sha256",
    "PULSEPLATE_MODULE_GRAPH_SHA256": "module_graph_sha256",
    "PULSEPLATE_MODULE_GRAPH_COUNT": "module_graph_count",
    "PULSEPLATE_PROMETHEUS_BINARY_SHA256": "prometheus_sha256",
    "PULSEPLATE_PROMTOOL_BINARY_SHA256": "promtool_sha256",
}
OCI_FIELDS = {"platform", "manifest_digest", "config_digest", "layer_digests"}
BUILDER_FIELDS = {"builder_image_digest", "builder_status_sha256"}
EVIDENCE_FIELDS = set(BUILD_OUTPUT_FIELDS.values()) | OCI_FIELDS | BUILDER_FIELDS
TRIVY_SCAN_SCOPE = ("--scanners", "vuln,secret", "--pkg-types", "os,library")
TRIVY_SCAN_POLICY = ("--severity", "HIGH,CRITICAL", "--exit-code", "1")
REQUIRED_TRIVY_TARGETS = (
    "os-packages",
    "prometheus-go-binary",
    "promtool-go-binary",
)
ALLOWED_ACTIONS = frozenset(
    {"freeze", "status", "verify-local", "show-publication-tuple", "authorize", "publish"}
)
_T = TypeVar("_T")


class CandidateHold(RuntimeError):
    """A stable fail-closed outcome."""


_hold = CandidateHold


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _state_root(repo_root: Path) -> Path:
    return repo_root / "artifacts" / "security_lab" / "prometheus_derivative_candidate" / "v1"


def canonical_json(value: object) -> bytes:
    try:
        serialized = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError, RecursionError) as exc:
        raise _hold("canonical_json_invalid") from exc
    return (serialized + "\n").encode("ascii")


def sha256_digest(payload: bytes) -> str:
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _reject_duplicate_keys(pairs: Sequence[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _hold("duplicate_json_key")
        result[key] = value
    return result


def _parse_json(payload: bytes, *, code: str) -> object:
    try:
        return json.loads(
            payload,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda _value: (_ for _ in ()).throw(_hold(code)),
        )
    except CandidateHold:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise _hold(code) from exc


def _transport_call(
    function: Callable[..., _T],
    *args: object,
    code: str = "external_mechanism_failed",
    **kwargs: object,
) -> _T:
    try:
        return function(*args, **kwargs)
    except transport.TransportError as exc:
        raise _hold(code) from exc


def _read_regular(path: Path, *, expected_mode: int | None = None) -> bytes:
    try:
        payload: bytes = transport.read_regular(
            path, max_bytes=MAX_FILE_BYTES, expected_mode=expected_mode
        )
        return payload
    except transport.TransportError as exc:
        raise _hold("safe_read_failed") from exc


def _ensure_private_directory(path: Path) -> None:
    try:
        if not path.exists():
            os.mkdir(path, 0o700)
        metadata = os.lstat(path)
    except OSError as exc:
        raise _hold("private_directory_unavailable") from exc
    if not stat.S_ISDIR(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise _hold("unsafe_private_directory")


def _ensure_private_tree(repo_root: Path, candidate_directory: Path) -> None:
    artifacts = repo_root / "artifacts"
    try:
        os.mkdir(artifacts, 0o700)
    except FileExistsError:
        pass
    except OSError as exc:
        raise _hold("artifacts_directory_unavailable") from exc
    try:
        metadata = os.lstat(artifacts)
    except OSError as exc:
        raise _hold("artifacts_directory_unavailable") from exc
    if not stat.S_ISDIR(metadata.st_mode):
        raise _hold("artifacts_directory_unsafe")
    root = _state_root(repo_root)
    for directory in (root.parents[1], root.parent, root, candidate_directory):
        _ensure_private_directory(directory)


def _atomic_no_replace(path: Path, payload: bytes) -> bool:
    if len(payload) > MAX_RECEIPT_BYTES:
        raise _hold("receipt_too_large")
    if path.exists() or path.is_symlink():
        if _read_regular(path, expected_mode=0o600) == payload:
            return False
        raise _hold("divergent_receipt")
    temporary: Path | None = None
    stage_identity: tuple[int, int] | None = None
    created = False
    try:
        descriptor, name = tempfile.mkstemp(prefix=".receipt-stage-", dir=path.parent.parent)
        temporary = Path(name)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        staged = temporary.lstat()
        stage_identity = (staged.st_dev, staged.st_ino)
        try:
            _transport_call(
                transport.atomic_rename_noreplace,
                temporary,
                path,
                code="receipt_write_failed",
            )
            created = True
        except FileExistsError:
            if _read_regular(path, expected_mode=0o600) != payload:
                raise _hold("divergent_receipt")
    except CandidateHold:
        raise
    except OSError as exc:
        raise _hold("receipt_write_failed") from exc
    finally:
        if temporary is not None and stage_identity is not None:
            try:
                metadata = temporary.lstat()
                if (metadata.st_dev, metadata.st_ino) == stage_identity:
                    temporary.unlink()
            except (FileNotFoundError, OSError):
                pass
    if not created:
        return False
    final = os.lstat(path)
    if (
        not stat.S_ISREG(final.st_mode)
        or stat.S_IMODE(final.st_mode) != 0o600
        or final.st_nlink != 1
    ):
        raise _hold("receipt_write_unsafe")
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)
    return True


def _binding(relative_path: str, payload: bytes) -> dict[str, object]:
    return {
        "path": relative_path,
        "size": len(payload),
        "sha256": sha256_digest(payload),
    }


def _source_bytes(repo_root: Path) -> tuple[bytes, bytes]:
    containerfile = _read_regular(repo_root / CONTAINERFILE_RELATIVE)
    selector = _read_regular(repo_root / SELECTOR_RELATIVE)
    if hashlib.sha256(containerfile).hexdigest() != EXPECTED_CONTAINERFILE_SHA256:
        raise _hold("containerfile_drift")
    if hashlib.sha256(selector).hexdigest() != EXPECTED_SELECTOR_SHA256:
        raise _hold("selector_drift")
    selector_value = _parse_json(selector, code="selector_json_invalid")
    if (
        not isinstance(selector_value, dict)
        or selector_value.get("runtime_ref") != OFFICIAL_RUNTIME_REF
    ):
        raise _hold("selector_contract_drift")
    return containerfile, selector


def _runtime_consumers(repo_root: Path) -> dict[str, dict[str, object]]:
    bindings: dict[str, dict[str, object]] = {}
    for relative_path in RUNTIME_CONSUMER_RELATIVES:
        payload = _read_regular(repo_root / relative_path)
        try:
            document = yaml.safe_load(payload)
        except yaml.YAMLError as exc:
            raise _hold("runtime_consumer_yaml_invalid") from exc
        if not isinstance(document, dict):
            raise _hold("runtime_consumer_invalid")
        services = document.get("services")
        service = services.get("prometheus") if isinstance(services, dict) else None
        if (
            not isinstance(service, dict)
            or service.get("image") != OFFICIAL_RUNTIME_REF
            or service.get("platform") != PLATFORM
        ):
            raise _hold("runtime_consumer_drift")
        bindings[relative_path] = _binding(relative_path, payload)
    return bindings


ExecutionIdentity = Mapping[str, str]


def resolve_execution_identity(repo_root: Path) -> ExecutionIdentity:
    if os.environ.get("CONTAINER_HOST"):
        raise _hold("container_host_override_forbidden")
    environment = {
        key: value
        for key, value in os.environ.items()
        if key in {"PATH", "HOME", "TMPDIR", "LANG", "LC_ALL"}
    }
    observed = _transport_call(
        transport.observe_programs,
        {
            "git_head": ("git", "rev-parse", "HEAD"),
            "git_tree": ("git", "rev-parse", "HEAD^{tree}"),
            "container": ("container", "--version"),
            "container_system": ("container", "system", "version", "--format", "json"),
            "gh": ("gh", "--version"),
        },
        repo_root,
        environment,
        timeout_seconds=30,
        max_output_bytes=65_536,
        max_program_bytes=MAX_EXECUTABLE_BYTES,
        code="execution_identity_command_failed",
    )
    if any(fact.returncode != 0 for fact in observed.values()):
        raise _hold("execution_identity_command_failed")
    git, container, gh = (observed[name] for name in ("git_head", "container", "gh"))
    head, tree = observed["git_head"].stdout, observed["git_tree"].stdout
    if not re.fullmatch(r"[0-9a-f]{40}", head) or not re.fullmatch(r"[0-9a-f]{40}", tree):
        raise _hold("git_identity_invalid")
    if container.stdout != "container CLI version 1.1.0 (build: release, commit: 5973b9c)":
        raise _hold("container_identity_invalid")
    script = repo_root / "scripts" / "ci" / "prometheus_derivative_candidate.py"
    transport_path = repo_root / TRANSPORT_RELATIVE
    interpreter = Path(sys.executable).resolve()
    system_identity = _parse_json(
        observed["container_system"].stdout.encode("utf-8"),
        code="container_system_identity_invalid",
    )
    if (
        not isinstance(system_identity, list)
        or len(system_identity) != 2
        or not all(isinstance(entry, dict) for entry in system_identity)
        or not all(isinstance(entry.get("appName"), str) for entry in system_identity)
    ):
        raise _hold("container_system_identity_invalid")
    by_name = {entry["appName"]: entry for entry in system_identity}
    if (
        set(by_name) != {"container", "container-apiserver"}
        or by_name["container"].get("version") != "1.1.0"
        or by_name["container"].get("buildType") != "release"
        or by_name["container"].get("commit")
        != "5973b9cc626a3e7a499bb316a958237ebe14e2ed"  # pragma: allowlist secret
        or by_name["container-apiserver"].get("buildType") != "release"
        or "version 1.1.0" not in str(by_name["container-apiserver"].get("version"))
    ):
        raise _hold("container_system_identity_invalid")
    return {
        "git_head": head,
        "git_tree": tree,
        "git_path": str(git.path),
        "git_sha256": git.sha256,
        "script_path": "scripts/ci/prometheus_derivative_candidate.py",
        "script_sha256": _transport_call(
            transport.hash_regular,
            script,
            max_bytes=MAX_EXECUTABLE_BYTES,
            code="script_identity_invalid",
        ),
        "script_version": SCRIPT_VERSION,
        "transport_path": TRANSPORT_RELATIVE,
        "transport_sha256": _transport_call(
            transport.hash_regular,
            transport_path,
            max_bytes=MAX_EXECUTABLE_BYTES,
            code="transport_identity_invalid",
        ),
        "python_path": str(interpreter),
        "python_sha256": _transport_call(
            transport.hash_regular,
            interpreter,
            max_bytes=MAX_EXECUTABLE_BYTES,
            executable=True,
            code="python_identity_invalid",
        ),
        "python_version": f"{sys.implementation.name}-{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "container_path": str(container.path),
        "container_sha256": container.sha256,
        "container_version": "1.1.0",
        "container_release_commit": "5973b9c",
        "container_system_sha256": sha256_digest(canonical_json(system_identity)),
        "gh_path": str(gh.path),
        "gh_sha256": gh.sha256,
        "gh_version": gh.stdout,
    }


def build_spec(repo_root: Path, identity: ExecutionIdentity) -> dict[str, object]:
    containerfile, selector = _source_bytes(repo_root)
    return {
        "schema": f"{SCHEMA}.prebuild-spec",
        "state": "unbuilt-unpublished-unselected-nondeployable",
        "platform": PLATFORM,
        "source_revision": "09fdfcd2659dd9c816e9e23c992fc161c0091757",  # pragma: allowlist secret
        "source_archive_sha256": (
            "ecca5c5c74ca7436bee52c081e3cae1346d56a23cffba3f7a9d1012a0733665d"  # pragma: allowlist secret
        ),
        "dependency": {
            "identity": "google.golang.org/grpc",
            "before": "v1.83.0",
            "after": "v1.83.1",
            "additional_movements_allowed": False,
            "transformed_go_mod_sha256": (
                "a95d4c90bc9b6b55f9668e5d7042e991c121775d98fac25372859a1044a85010"  # pragma: allowlist secret
            ),
            "transformed_go_sum_sha256": (
                "3f9a08ac142b242f300a5958f0f8b864f0deb9dcf8dfd770ebaba49b2e32dc0a"  # pragma: allowlist secret
            ),
        },
        "pnpm_binary_sha256": "e5e29eb103e73729ed4115f0e939fb376386dd0d76db56b12459524041f922a0",  # pragma: allowlist secret
        "execution_identity": dict(identity),
        "repository": REPOSITORY,
        "workflow": _binding(WORKFLOW_RELATIVE, _read_regular(repo_root / WORKFLOW_RELATIVE)),
        "cloud_profile": dict(CLOUD_PROFILE),
        "isolated_no_cache_builds": 2,
        "publication": {
            "repository": PUBLICATION_REPOSITORY,
            "tag_prefix": PUBLICATION_TAG_PREFIX,
            "push_limit": 1,
        },
        "containerfile": _binding(CONTAINERFILE_RELATIVE, containerfile),
        "runtime_selector": _binding(SELECTOR_RELATIVE, selector),
        "runtime_consumers": _runtime_consumers(repo_root),
        "allowed_actions": sorted(ALLOWED_ACTIONS),
    }


BuildEvidence = dict[str, object]
ScanEvidence = dict[str, object]


class BuildAdapter(Protocol):
    def verify_two_builds(self, spec: Mapping[str, object]) -> tuple[object, ...]: ...


class PublicationAdapter(Protocol):
    def preflight(self, payload: Mapping[str, object]) -> object: ...

    def observe(self, candidate_ref: str) -> object: ...

    def process_plans(self, candidate_ref: str) -> tuple[transport.ProcessPlan, ...]: ...

    def close(self) -> None: ...


def _build_evidence(value: object) -> BuildEvidence:
    if not isinstance(value, dict) or set(value) != EVIDENCE_FIELDS:
        raise _hold("build_evidence_invalid")
    layers = value["layer_digests"]
    if not isinstance(layers, list) or not layers:
        raise _hold("build_evidence_invalid")
    counts = {"module_graph_count", "ui_file_count", "ui_total_bytes"}
    for field, raw in value.items():
        if field in {"platform", "layer_digests"}:
            continue
        if field in counts:
            valid = isinstance(raw, int) and not isinstance(raw, bool) and raw > 0
        else:
            pattern = (
                SHA256_RE
                if field in {"manifest_digest", "config_digest"} | BUILDER_FIELDS
                else HEX_SHA256_RE
            )
            valid = isinstance(raw, str) and pattern.fullmatch(raw) is not None
        if not valid:
            raise _hold("build_evidence_invalid")
    if value["platform"] != PLATFORM or not all(
        isinstance(item, str) and SHA256_RE.fullmatch(item) for item in layers
    ):
        raise _hold("build_evidence_invalid")
    return dict(value)


def _report_build_mismatch(first: BuildEvidence, second: BuildEvidence) -> None:
    first, second = _build_evidence(first), _build_evidence(second)
    for field in sorted(EVIDENCE_FIELDS):
        if first[field] == second[field]:
            continue
        rendered: list[str] = []
        for value in (first[field], second[field]):
            if isinstance(value, list):
                rendered.append(f"count={len(value)} {sha256_digest(canonical_json(value))}")
            elif isinstance(value, int):
                rendered.append(str(value) if value.bit_length() <= 64 else "count-exceeds-uint64")
            else:
                rendered.append(str(value))
        print(f"Build mismatch {field}: first={rendered[0]} second={rendered[1]}", file=sys.stderr)


def _scan_evidence(value: object) -> ScanEvidence:
    if not isinstance(value, dict) or set(value) != SCAN_FIELDS:
        raise _hold("scan_evidence_invalid")
    if value["trivy_version"] != "0.74.0":
        raise _hold("scan_evidence_invalid")
    for field in (
        "trivy_executable_sha256",
        "database_identity_sha256",
        "report_sha256",
        "coverage_sha256",
    ):
        raw = value[field]
        if not isinstance(raw, str) or SHA256_RE.fullmatch(raw) is None:
            raise _hold("scan_evidence_invalid")
    updated_at = value["database_updated_at"]
    covered_targets = value["covered_targets"]
    if not isinstance(updated_at, str) or not isinstance(covered_targets, list):
        raise _hold("scan_evidence_invalid")
    try:
        parsed_updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise _hold("scan_evidence_invalid") from exc
    if parsed_updated_at.tzinfo is None:
        raise _hold("scan_evidence_invalid")
    if covered_targets != list(REQUIRED_TRIVY_TARGETS):
        raise _hold("scan_coverage_incomplete")
    for field in ("high_count", "critical_count"):
        count = value[field]
        if not isinstance(count, int) or isinstance(count, bool) or count != 0:
            raise _hold("scan_findings_present")
    return dict(value)


def _normalize_trivy_report(value: object) -> tuple[list[dict[str, object]], list[str]]:
    if not isinstance(value, dict) or not isinstance(value.get("Results"), list):
        raise _hold("trivy_report_invalid")
    normalized: list[dict[str, object]] = []
    covered: set[str] = set()
    for row in value["Results"]:
        if not isinstance(row, dict):
            raise _hold("trivy_report_invalid")
        row_class, row_type, target = row.get("Class"), row.get("Type"), row.get("Target")
        if not all(isinstance(item, str) for item in (row_class, row_type, target)):
            raise _hold("trivy_report_invalid")
        if row_class == "os-pkgs":
            logical_target = "os-packages"
        elif row_class == "lang-pkgs" and row_type == "gobinary":
            binary = Path(cast(str, target)).name
            if binary not in {"prometheus", "promtool"}:
                raise _hold("trivy_report_target_invalid")
            logical_target = f"{binary}-go-binary"
        else:
            raise _hold("trivy_report_target_invalid")
        covered.add(logical_target)
        packages = row.get("Packages")
        if (
            not isinstance(packages, list)
            or not packages
            or any(
                not isinstance(package, dict)
                or not isinstance(package.get("Name"), str)
                or not package["Name"]
                or not isinstance(package.get("Version"), str)
                or not package["Version"]
                for package in packages
            )
        ):
            raise _hold("trivy_package_coverage_incomplete")
        findings: list[dict[str, object]] = []
        for collection, identity_field in (
            ("Vulnerabilities", "VulnerabilityID"),
            ("Secrets", "RuleID"),
        ):
            raw_findings = row.get(collection) or []
            if not isinstance(raw_findings, list):
                raise _hold("trivy_report_invalid")
            for finding in raw_findings:
                if not isinstance(finding, dict):
                    raise _hold("trivy_report_invalid")
                severity, identity = finding.get("Severity"), finding.get(identity_field)
                if severity not in {"HIGH", "CRITICAL"} or not isinstance(identity, str):
                    raise _hold("trivy_report_invalid")
                findings.append(
                    {
                        "kind": collection,
                        "id": identity,
                        "package": finding.get("PkgName", ""),
                        "installed": finding.get("InstalledVersion", ""),
                        "fixed": finding.get("FixedVersion", ""),
                        "severity": severity,
                    }
                )
        normalized.append(
            {
                "target": logical_target,
                "class": row_class,
                "type": row_type,
                "findings": sorted(findings, key=lambda item: canonical_json(item)),
                "packages_sha256": sha256_digest(
                    canonical_json(
                        sorted(
                            [
                                {"name": package["Name"], "version": package["Version"]}
                                for package in packages
                            ],
                            key=lambda item: canonical_json(item),
                        )
                    )
                ),
            }
        )
    targets = sorted(covered)
    if targets != list(REQUIRED_TRIVY_TARGETS):
        raise _hold("trivy_scan_coverage_incomplete")
    return sorted(normalized, key=lambda item: canonical_json(item)), targets


def _fresh_database_timestamp(
    database: Mapping[str, object], *, now: datetime | None = None
) -> str:
    updated_at = database.get("UpdatedAt")
    if not isinstance(updated_at, str):
        raise _hold("trivy_database_identity_missing")
    try:
        updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise _hold("trivy_database_identity_missing") from exc
    observed_now = now or datetime.now(timezone.utc)
    if updated.tzinfo is None or not (-300 <= (observed_now - updated).total_seconds() <= 172_800):
        raise _hold("trivy_database_stale")
    return updated.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _material(spec: Mapping[str, object]) -> dict[str, object]:
    identity = cast(Mapping[str, str], spec["execution_identity"])
    return {
        **{
            key: spec[key]
            for key in (
                "containerfile",
                "runtime_selector",
                "runtime_consumers",
                "workflow",
                "cloud_profile",
                "repository",
            )
        },
        **{
            key: identity[key]
            for key in ("git_head", "git_tree", "script_sha256", "transport_sha256")
        },
    }


def _timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise _hold("cloud_timestamp_invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise _hold("cloud_timestamp_invalid") from exc
    if parsed.tzinfo is None:
        raise _hold("cloud_timestamp_invalid")
    return parsed


def _provenance(value: object, spec: Mapping[str, object]) -> dict[str, object]:
    fields = {
        "repository_id",
        "head_sha",
        "workflow_id",
        "run_id",
        "attempt",
        "job_id",
        "artifact_id",
        "artifact_name",
        "artifact_digest",
        "started_at",
        "completed_at",
        "artifact_created_at",
        "expires_at",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise _hold("cloud_provenance_invalid")
    if any(
        type(value[key]) is not int or value[key] <= 0
        for key in ("repository_id", "workflow_id", "run_id", "attempt", "job_id", "artifact_id")
    ):
        raise _hold("cloud_provenance_invalid")
    if (
        value["repository_id"] != REPOSITORY_ID
        or value["attempt"] != 1
        or value["head_sha"] != cast(Mapping[str, str], spec["execution_identity"])["git_head"]
        or value["artifact_name"] != f"{CLOUD_JOB}-{value['run_id']}-1-{CLOUD_JOB}"
        or not isinstance(value["artifact_digest"], str)
        or SHA256_RE.fullmatch(value["artifact_digest"]) is None
        or not (
            _timestamp(value["started_at"])
            <= _timestamp(value["artifact_created_at"])
            <= _timestamp(value["completed_at"])
            < _timestamp(value["expires_at"])
        )
    ):
        raise _hold("cloud_provenance_invalid")
    return dict(value)


def _cloud_tool_evidence(value: object) -> dict[str, str]:
    expected = {
        "python_version": str(CLOUD_PROFILE["python"]),
        "platform": PLATFORM,
        "buildx_version": str(CLOUD_PROFILE["buildx_version"]),
        "buildx_sha256": f"sha256:{CLOUD_PROFILE['buildx_sha256']}",
        "trivy_version": str(CLOUD_PROFILE["trivy_version"]),
        "trivy_sha256": f"sha256:{CLOUD_PROFILE['trivy_sha256']}",
    }
    observed_fields = {
        "python_sha256",
        "git_sha256",
        "git_version",
        "docker_sha256",
        "docker_client_version",
        "docker_server_version",
        "docker_api_version",
    }
    if (
        not isinstance(value, dict)
        or set(value) != set(expected) | observed_fields
        or any(value.get(key) != item for key, item in expected.items())
        or any(
            not isinstance(item, str)
            or not item
            or len(item) > 512
            or any(ord(character) < 32 for character in item)
            for item in value.values()
        )
        or any(SHA256_RE.fullmatch(value[key]) is None for key in value if key.endswith("_sha256"))
    ):
        raise _hold("cloud_tools_invalid")
    return dict(value)


def _require_cloud_import_name(oci: transport.OCIResult, reference: str) -> None:
    annotations = oci.annotations or {}
    if (
        "com.apple.containerization.image.name" in annotations
        or annotations.get("io.containerd.image.name") != reference
    ):
        raise _hold("cloud_import_reference_invalid")


def _cloud_setup(repo_root: Path, root: Path) -> tuple[ExecutionIdentity, dict[str, str]]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if key in {"PATH", "TMPDIR", "LANG", "LC_ALL"}
    }
    environment.update({"HOME": str(root), "DOCKER_CONFIG": str(root / ".docker")})
    downloads = {
        "buildx": (
            f"https://github.com/docker/buildx/releases/download/v{CLOUD_PROFILE['buildx_version']}/"
            f"buildx-v{CLOUD_PROFILE['buildx_version']}.linux-amd64",
            "buildx_sha256",
        ),
        "trivy.tar.gz": (
            f"https://github.com/aquasecurity/trivy/releases/download/v{CLOUD_PROFILE['trivy_version']}/"
            f"trivy_{CLOUD_PROFILE['trivy_version']}_Linux-64bit.tar.gz",
            "trivy_archive_sha256",
        ),
    }
    for name, (url, digest_key) in downloads.items():
        _size, digest = _transport_call(
            transport.download_file,
            url,
            root / name,
            headers={},
            redirect_domains=("githubusercontent.com",),
            max_bytes=MAX_EXECUTABLE_BYTES,
            timeout_seconds=60,
        )
        if digest != f"sha256:{CLOUD_PROFILE[digest_key]}":
            raise _hold("cloud_tool_download_mismatch")
    tar = _transport_call(transport.resolve_program, "tar")
    unpacked = _transport_call(
        transport.run_process,
        transport.ProcessPlan(
            (
                str(tar),
                "-xzf",
                str(root / "trivy.tar.gz"),
                "--no-same-owner",
                "--no-same-permissions",
                "-C",
                str(root),
                "trivy",
            ),
            repo_root,
            environment,
            120,
            MAX_RECEIPT_BYTES,
        ),
    )
    if unpacked.returncode:
        raise _hold("cloud_tool_unpack_failed")
    for name in ("buildx", "trivy"):
        if (
            _transport_call(transport.hash_regular, root / name, max_bytes=MAX_EXECUTABLE_BYTES)
            != f"sha256:{CLOUD_PROFILE[name + '_sha256']}"
        ):
            raise _hold("cloud_tool_download_mismatch")
        (root / name).chmod(0o700)
    commands = {
        "git": ("git", "--version"),
        "git_head": ("git", "rev-parse", "HEAD"),
        "git_tree": ("git", "rev-parse", "HEAD^{tree}"),
        "docker": ("docker", "version", "--format", "{{json .}}"),
        "buildx": (str(root / "buildx"), "version"),
        "trivy": (str(root / "trivy"), "--version"),
    }
    observed = _transport_call(
        transport.observe_programs,
        commands,
        repo_root,
        environment,
        timeout_seconds=60,
        max_output_bytes=65536,
        max_program_bytes=MAX_EXECUTABLE_BYTES,
    )
    if any(row.returncode for row in observed.values()):
        raise _hold("cloud_tool_observation_failed")
    docker = _parse_json(observed["docker"].stdout.encode(), code="cloud_docker_invalid")
    if (
        not isinstance(docker, dict)
        or not isinstance(docker.get("Client"), dict)
        or not isinstance(docker.get("Server"), dict)
    ):
        raise _hold("cloud_docker_invalid")
    interpreter = Path(sys.executable).resolve()
    identity = {key: observed[key].stdout for key in ("git_head", "git_tree")}
    for key in ("git", "docker", "buildx", "trivy"):
        identity.update(
            {key + "_path": str(observed[key].path), key + "_sha256": observed[key].sha256}
        )
    identity.update(
        {
            "script_sha256": _transport_call(
                transport.hash_regular,
                repo_root / "scripts/ci/prometheus_derivative_candidate.py",
                max_bytes=MAX_EXECUTABLE_BYTES,
            ),
            "transport_sha256": _transport_call(
                transport.hash_regular,
                repo_root / TRANSPORT_RELATIVE,
                max_bytes=MAX_EXECUTABLE_BYTES,
            ),
            "python_path": str(interpreter),
            "python_sha256": _transport_call(
                transport.hash_regular, interpreter, max_bytes=MAX_EXECUTABLE_BYTES, executable=True
            ),
            "trivy_version": "0.74.0",
        }
    )
    if (
        not observed["buildx"].stdout.startswith(
            f"github.com/docker/buildx v{CLOUD_PROFILE['buildx_version']} "
        )
        or not observed["trivy"].stdout.splitlines()
        or observed["trivy"].stdout.splitlines()[0] != "Version: 0.74.0"
    ):
        raise _hold("cloud_tool_version_mismatch")
    tools = _cloud_tool_evidence(
        {
            **{
                key: identity[key]
                for key in (
                    "python_sha256",
                    "git_sha256",
                    "docker_sha256",
                    "buildx_sha256",
                    "trivy_sha256",
                )
            },
            "python_version": ".".join(str(part) for part in sys.version_info[:3]),
            "git_version": observed["git"].stdout,
            "docker_client_version": docker["Client"].get("Version"),
            "docker_server_version": docker["Server"].get("Version"),
            "docker_api_version": docker["Server"].get("ApiVersion"),
            "platform": f"{docker['Server'].get('Os')}/{docker['Server'].get('Arch')}",
            "buildx_version": str(CLOUD_PROFILE["buildx_version"]),
            "trivy_version": "0.74.0",
        }
    )
    identity["cloud_tools_sha256"] = sha256_digest(canonical_json(tools))
    return identity, tools


def execute_cloud(repo_root: Path) -> dict[str, object]:
    """Candidate-only remote execution: no local publication identity or receipt store."""
    head = os.environ.get("PROMETHEUS_CANDIDATE_HEAD_SHA", "")
    digest = os.environ.get("PROMETHEUS_CANDIDATE_SPEC_DIGEST", "")
    run_id, attempt = os.environ.get("GITHUB_RUN_ID", ""), os.environ.get("GITHUB_RUN_ATTEMPT", "")
    if (
        sys.platform != "linux"
        or os.uname().machine != "x86_64"
        or os.environ.get("GITHUB_REPOSITORY") != REPOSITORY
        or os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
        or os.environ.get("GITHUB_JOB") != CLOUD_JOB
        or os.environ.get("GITHUB_ACTIONS") != "true"
        or re.fullmatch(r"[0-9a-f]{40}", head) is None
        or head != os.environ.get("GITHUB_SHA")
        or SHA256_RE.fullmatch(digest) is None
        or not run_id.isdecimal()
        or int(run_id) <= 0
        or attempt != "1"
        or yaml.__version__ != CLOUD_PROFILE["pyyaml"]
    ):
        raise _hold("cloud_execution_context_invalid")
    output = repo_root / "artifacts/security_lab/prometheus_cloud_result"
    for directory in (output.parents[1], output.parent):
        _ensure_private_directory(directory)
    output.mkdir(mode=0o700)
    with tempfile.TemporaryDirectory(prefix="pulseplate-cloud-tools-") as temporary:
        identity, tools = _cloud_setup(repo_root, Path(temporary))
        if identity["git_head"] != head:
            raise _hold("cloud_checkout_mismatch")
        spec = build_spec(repo_root, identity)
        adapter = ExactAdapters(repo_root, identity, spec)
        try:
            reference = CLOUD_REFERENCE_PREFIX + digest[7:]
            first, archive = adapter._build(1, reference)
            second, _second_archive = adapter._build(2, reference)
            if first != second:
                _report_build_mismatch(first, second)
                raise _hold("path_independent_build_mismatch")
            scan = adapter._scan(archive)
            if build_spec(repo_root, identity) != spec:
                raise _hold("cloud_material_drift")
            observations = {
                "material": _material(spec),
                "spec_digest": digest,
                "run": {"id": int(run_id), "attempt": 1, "job": CLOUD_JOB},
                "tools": tools,
                "scan": scan,
            }
            for name, value in (
                ("build-one.json", first),
                ("build-two.json", second),
                ("observations.json", observations),
            ):
                _transport_call(transport.write_private_file, output / name, canonical_json(value))
            for name in ("candidate.oci.tar", "trivy-report.json"):
                _transport_call(
                    transport.copy_private_file,
                    archive.parent / name,
                    output / name,
                    max_bytes=CLOUD_MEMBERS[name],
                )
        finally:
            adapter.close()
    return {"state": "cloud-candidate-verified-unpublished", "spec_digest": digest}


class ExactAdapters:
    def __init__(
        self, repo_root: Path, identity: ExecutionIdentity, spec: Mapping[str, object]
    ) -> None:
        self.repo_root, self.identity, self.spec = repo_root, identity, spec
        session = tempfile.TemporaryDirectory(prefix="pulseplate-prometheus-session-")
        self.temporary: list[tempfile.TemporaryDirectory[str]] = [session]
        session_root = Path(session.name)
        self.private_home = session_root / "home"
        self.private_home.mkdir(mode=0o700)
        self.trivy_cache = session_root / "trivy-cache"
        self.trivy_cache.mkdir(mode=0o700)
        self.loaded_ref: str | None = None
        self.cloud_archive: Path | None = None

    def _env(self) -> dict[str, str]:
        allowed = {"PATH", "TMPDIR", "LANG", "LC_ALL"}
        environment = {key: value for key, value in os.environ.items() if key in allowed}
        environment.update(
            {
                "HOME": str(self.private_home),
                "XDG_CONFIG_HOME": str(self.private_home / ".config"),
                "DOCKER_CONFIG": str(self.private_home / ".docker"),
                "TRIVY_CACHE_DIR": str(self.trivy_cache),
            }
        )
        return environment

    def _plan(self, argv: Sequence[str], timeout: int = 7200) -> transport.ProcessPlan:
        return transport.ProcessPlan(tuple(argv), self.repo_root, self._env(), timeout, 8_388_608)

    def _github_env(self) -> dict[str, str]:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not token:
            raise _hold("github_auth_required")
        return {**self._env(), "GH_TOKEN": token, "GITHUB_TOKEN": token}

    def _api(self, endpoint: str, payload: Mapping[str, object] | None = None) -> dict[str, object]:
        argv = (
            self.identity["gh_path"],
            "api",
            "--hostname",
            "github.com",
            "--method",
            "POST" if payload is not None else "GET",
            "-H",
            "X-GitHub-Api-Version: 2026-03-10",
            f"repos/{REPOSITORY}/{endpoint}",
        )
        result = _transport_call(
            transport.run_process,
            transport.ProcessPlan(
                (*argv, "--input", "-") if payload is not None else argv,
                self.repo_root,
                self._github_env(),
                60,
                MAX_RECEIPT_BYTES,
            ),
            stdin=canonical_json(payload) if payload is not None else None,
        )
        value = _parse_json(result.stdout, code="github_response_invalid")
        if result.returncode or not isinstance(value, dict):
            raise _hold("github_response_invalid")
        return value

    def verify_two_builds(self, spec: Mapping[str, object]) -> tuple[object, ...]:
        if spec != self.spec:
            raise _hold("prebuild_spec_drift")
        authenticated = _transport_call(
            transport.run_process,
            transport.ProcessPlan(
                (self.identity["gh_path"], "auth", "status", "--hostname", "github.com"),
                self.repo_root,
                self._github_env(),
                30,
                65536,
            ),
        )
        if authenticated.returncode:
            raise _hold("github_auth_required")
        pr = self._api("pulls/2347")
        head = pr.get("head")
        if (
            pr.get("state") != "open"
            or not isinstance(head, dict)
            or head.get("sha") != self.identity["git_head"]
            or not isinstance(head.get("ref"), str)
            or not isinstance(head.get("repo"), dict)
            or head["repo"].get("id") != REPOSITORY_ID
            or head["repo"].get("full_name") != REPOSITORY
        ):
            raise _hold("cloud_live_head_mismatch")
        workflow = self._api("actions/workflows/build.yml")
        if (
            workflow.get("path") != WORKFLOW_RELATIVE
            or workflow.get("state") != "active"
            or type(workflow.get("id")) is not int
        ):
            raise _hold("cloud_workflow_mismatch")
        dispatched = self._api(
            "actions/workflows/build.yml/dispatches",
            {
                "ref": head["ref"],
                "inputs": {
                    "mode": CLOUD_JOB,
                    "candidate_head_sha": self.identity["git_head"],
                    "candidate_spec_digest": sha256_digest(canonical_json(spec)),
                },
            },
        )
        run_id = dispatched.get("workflow_run_id")
        if (
            type(run_id) is not int
            or run_id <= 0
            or dispatched.get("run_url")
            != f"https://api.github.com/repos/{REPOSITORY}/actions/runs/{run_id}"
            or dispatched.get("html_url")
            != f"https://github.com/{REPOSITORY}/actions/runs/{run_id}"
        ):
            raise _hold("cloud_dispatch_uncertain_no_retry")
        for _ in range(120):
            run = self._api(f"actions/runs/{run_id}")
            for field in ("repository", "head_repository"):
                repository = run.get(field)
                if not isinstance(repository, dict) or repository.get("id") != REPOSITORY_ID:
                    raise _hold("cloud_run_repository_mismatch")
            if any(
                run.get(key) != value
                for key, value in {
                    "id": run_id,
                    "head_sha": self.identity["git_head"],
                    "head_branch": head["ref"],
                    "workflow_id": workflow["id"],
                    "path": WORKFLOW_RELATIVE,
                    "event": "workflow_dispatch",
                    "run_attempt": 1,
                }.items()
            ):
                raise _hold("cloud_run_identity_mismatch")
            if run.get("status") == "completed":
                break
            if run.get("status") not in {
                "queued",
                "in_progress",
                "waiting",
                "pending",
                "requested",
            }:
                raise _hold("cloud_run_status_invalid")
            print(f"Cloud candidate run {run_id}: {run['status']}", file=sys.stderr, flush=True)
            time.sleep(60)
        else:
            raise _hold("cloud_run_pending")
        if run.get("conclusion") != "success":
            raise _hold("cloud_run_failed")
        census = self._api(f"actions/runs/{run_id}/attempts/1/jobs?per_page=100")
        jobs = census.get("jobs")
        if (
            not isinstance(jobs, list)
            or census.get("total_count") != 4
            or len(jobs) != 4
            or any(
                not isinstance(job, dict)
                or not isinstance(job.get("name"), str)
                or type(job.get("id")) is not int
                or job["id"] <= 0
                for job in jobs
            )
            or len({job["id"] for job in jobs}) != 4
            or {job.get("name") for job in jobs} != {CLOUD_JOB, *ORDINARY_JOBS}
        ):
            raise _hold("cloud_jobs_incomplete")
        for job in jobs:
            if (
                job.get("run_id") != run_id
                or job.get("head_sha") != self.identity["git_head"]
                or job.get("run_attempt") != 1
                or type(job.get("run_attempt")) is not int
                or job.get("status") != "completed"
                or job.get("conclusion") != ("success" if job["name"] == CLOUD_JOB else "skipped")
            ):
                raise _hold("cloud_job_not_admitted")
        producer = next(job for job in jobs if job["name"] == CLOUD_JOB)
        listing = self._api(f"actions/runs/{run_id}/artifacts?per_page=100")
        artifacts = listing.get("artifacts")
        if (
            listing.get("total_count") != 1
            or not isinstance(artifacts, list)
            or len(artifacts) != 1
            or not isinstance(artifacts[0], dict)
        ):
            raise _hold("cloud_artifacts_incomplete")
        artifact = artifacts[0]
        source = artifact.get("workflow_run")
        if (
            not isinstance(source, dict)
            or any(
                source.get(key) != expected
                for key, expected in {
                    "id": run_id,
                    "repository_id": REPOSITORY_ID,
                    "head_repository_id": REPOSITORY_ID,
                    "head_sha": self.identity["git_head"],
                    "head_branch": head["ref"],
                }.items()
            )
            or artifact.get("expired") is not False
            or type(artifact.get("size_in_bytes")) is not int
            or not 0 < artifact["size_in_bytes"] <= MAX_CLOUD_ZIP_BYTES
        ):
            raise _hold("cloud_artifact_identity_invalid")
        provenance = _provenance(
            {
                "repository_id": REPOSITORY_ID,
                "head_sha": self.identity["git_head"],
                "workflow_id": workflow["id"],
                "run_id": run_id,
                "attempt": 1,
                "job_id": producer.get("id"),
                "artifact_id": artifact.get("id"),
                "artifact_name": artifact.get("name"),
                "artifact_digest": artifact.get("digest"),
                "started_at": producer.get("started_at"),
                "completed_at": producer.get("completed_at"),
                "artifact_created_at": artifact.get("created_at"),
                "expires_at": artifact.get("expires_at"),
            },
            spec,
        )
        if _timestamp(provenance["expires_at"]) <= datetime.now(timezone.utc):
            raise _hold("cloud_artifact_expired")
        support = _state_root(self.repo_root).parent
        _ensure_private_directory(support.parent)
        _ensure_private_directory(support)
        temporary = tempfile.TemporaryDirectory(prefix="cloud-download-", dir=support)
        self.temporary.append(temporary)
        root, archive = Path(temporary.name), Path(temporary.name) / "artifact.zip"
        size, digest = _transport_call(
            transport.download_file,
            f"https://api.github.com/repos/{REPOSITORY}/actions/artifacts/{artifact['id']}/zip",
            archive,
            headers={
                "Authorization": f"Bearer {self._github_env()['GH_TOKEN']}",
                "X-GitHub-Api-Version": "2026-03-10",
            },
            redirect_domains=("blob.core.windows.net",),
            max_bytes=MAX_CLOUD_ZIP_BYTES,
            timeout_seconds=60,
        )
        if digest != artifact["digest"] or size != artifact["size_in_bytes"]:
            raise _hold("cloud_artifact_digest_mismatch")
        extracted = root / "verified"
        _transport_call(
            transport.extract_zip_members,
            archive,
            extracted,
            CLOUD_MEMBERS,
            max_archive_bytes=MAX_CLOUD_ZIP_BYTES,
        )
        observations = _parse_json(
            _read_regular(extracted / "observations.json"), code="cloud_output_invalid"
        )
        if (
            not isinstance(observations, dict)
            or set(observations) != {"material", "spec_digest", "run", "tools", "scan"}
            or observations["material"] != _material(spec)
            or observations["spec_digest"] != sha256_digest(canonical_json(spec))
            or observations["run"] != {"id": run_id, "attempt": 1, "job": CLOUD_JOB}
        ):
            raise _hold("cloud_output_identity_mismatch")
        first, second = (
            _build_evidence(
                _parse_json(_read_regular(extracted / name), code="cloud_output_invalid")
            )
            for name in ("build-one.json", "build-two.json")
        )
        scan = _scan_evidence(observations["scan"])
        report, targets = _normalize_trivy_report(
            _parse_json(_read_regular(extracted / "trivy-report.json"), code="cloud_output_invalid")
        )
        _fresh_database_timestamp({"UpdatedAt": scan["database_updated_at"]})
        oci = _transport_call(
            transport.parse_oci_archive, extracted / "candidate.oci.tar", **OCI_LIMITS
        )
        _require_cloud_import_name(
            oci, CLOUD_REFERENCE_PREFIX + sha256_digest(canonical_json(spec))[7:]
        )
        tools = _cloud_tool_evidence(observations["tools"])
        expected_source = {**spec, **cast(dict[str, object], spec["dependency"])}
        if (
            first != second
            or transport.oci_mapping(oci) != _oci_fields(first)
            or first["builder_status_sha256"] != sha256_digest(canonical_json(tools))
            or first["builder_image_digest"] != str(CLOUD_PROFILE["buildkit_ref"]).split("@")[1]
            or any(
                first[field] != expected_source[field]
                for field in (
                    "source_archive_sha256",
                    "pnpm_binary_sha256",
                    "transformed_go_mod_sha256",
                    "transformed_go_sum_sha256",
                )
            )
            or scan["trivy_executable_sha256"] != f"sha256:{CLOUD_PROFILE['trivy_sha256']}"
            or scan["report_sha256"] != sha256_digest(canonical_json(report))
            or scan["coverage_sha256"] != sha256_digest(canonical_json(targets))
            or any(row["findings"] for row in report)
        ):
            raise _hold("cloud_evidence_mismatch")
        final_pr = self._api("pulls/2347")
        final_head = final_pr.get("head")
        if (
            final_pr.get("state") != "open"
            or not isinstance(final_head, dict)
            or any(final_head.get(key) != head[key] for key in ("sha", "ref"))
        ):
            raise _hold("cloud_live_head_mismatch")
        self.cloud_archive = extracted / "candidate.oci.tar"
        return first, second, scan, provenance

    def _run_json(self, argv: Sequence[str]) -> dict[str, object]:
        result = _transport_call(transport.run_process, self._plan(argv, 120))
        value = _parse_json(result.stdout, code="tool_observation_invalid")
        if result.returncode or not isinstance(value, dict):
            raise _hold("tool_observation_invalid")
        return value

    def _builder_observation(self, name: str) -> dict[str, str]:
        for program in ("docker", "buildx", "trivy", "python"):
            if (
                _transport_call(
                    transport.hash_regular,
                    Path(self.identity[program + "_path"]),
                    max_bytes=MAX_EXECUTABLE_BYTES,
                    executable=True,
                )
                != self.identity[program + "_sha256"]
            ):
                raise _hold("cloud_tool_identity_drift")
        bootstrap = _transport_call(
            transport.run_process,
            self._plan((self.identity["buildx_path"], "inspect", name, "--bootstrap"), 120),
        )
        if bootstrap.returncode:
            sys.stderr.buffer.write(bootstrap.stderr[-4096:])
            raise _hold("cloud_builder_bootstrap_failed")
        # Buildx 0.37 inspect is text-only; ls exposes the canonical Builder JSON.
        template = "{{if eq .Name " + json.dumps(name) + "}}{{json .Builder}}{{end}}"
        node = self._run_json((self.identity["buildx_path"], "ls", "--format", template))
        status = self._run_json(
            (
                self.identity["docker_path"],
                "inspect",
                "--format",
                "{{json .}}",
                f"buildx_buildkit_{name}0",
            )
        )
        nodes = node.get("Nodes")
        state, configuration, resources = (
            status.get(key) for key in ("State", "Config", "HostConfig")
        )
        if (
            node.get("Name") != name
            or node.get("Err")
            or node.get("Driver") != "docker-container"
            or not isinstance(nodes, list)
            or len(nodes) != 1
            or not isinstance(nodes[0], dict)
            or nodes[0].get("Name") != f"{name}0"
            or nodes[0].get("Err")
            or nodes[0].get("Status") != "running"
            or nodes[0].get("Version") != CLOUD_PROFILE["buildkit_version"]
            or not isinstance(state, dict)
            or state.get("Running") is not True
            or not isinstance(resources, dict)
            or not isinstance(configuration, dict)
            or configuration.get("Image") != CLOUD_PROFILE["buildkit_ref"]
            or status.get("Image") != CLOUD_PROFILE["buildkit_config_digest"]
        ):
            raise _hold("cloud_builder_identity_invalid")
        if (
            resources.get("Memory") != CLOUD_PROFILE["memory_bytes"]
            or resources.get("CpuPeriod") != 100000
            or resources.get("CpuQuota") != 400000
        ):
            raise _hold("cloud_builder_resources_invalid")
        return {
            "builder_image_digest": str(CLOUD_PROFILE["buildkit_ref"]).split("@")[1],
            "builder_status_sha256": self.identity["cloud_tools_sha256"],
        }

    def _build(self, ordinal: int, reference: str) -> tuple[BuildEvidence, Path]:
        if sys.platform != "linux" or os.uname().machine != "x86_64":
            raise _hold("cloud_native_linux_required")
        temporary = tempfile.TemporaryDirectory(prefix=f"pulseplate-cloud-{ordinal}-")
        self.temporary.append(temporary)
        root, buildx = Path(temporary.name), self.identity["buildx_path"]
        context = root / "context"
        context.mkdir(mode=0o700)
        recipe, archive = context / "Containerfile", root / "candidate.oci.tar"
        _transport_call(
            transport.write_private_file,
            recipe,
            _read_regular(self.repo_root / CONTAINERFILE_RELATIVE),
        )
        name = f"pp-prometheus-{ordinal}"
        created = _transport_call(
            transport.run_process,
            self._plan(
                (
                    buildx,
                    "create",
                    "--name",
                    name,
                    "--driver",
                    "docker-container",
                    "--buildkitd-flags",
                    "",
                    "--driver-opt",
                    f"image={CLOUD_PROFILE['buildkit_ref']}",
                    "--driver-opt",
                    f"memory={CLOUD_PROFILE['memory_bytes']}",
                    "--driver-opt",
                    "cpu-period=100000",
                    "--driver-opt",
                    "cpu-quota=400000",
                ),
                120,
            ),
        )
        if created.returncode:
            raise _hold("cloud_builder_create_failed")
        try:
            before = self._builder_observation(name)
            result = _transport_call(
                transport.run_process,
                self._plan(
                    (
                        buildx,
                        "build",
                        "--builder",
                        name,
                        "--file",
                        str(recipe),
                        "--platform",
                        PLATFORM,
                        "--no-cache",
                        "--progress",
                        "plain",
                        "--provenance=false",
                        "--sbom=false",
                        "--build-arg",
                        f"SOURCE_DATE_EPOCH={CLOUD_PROFILE['source_date_epoch']}",
                        "--output",
                        f"type=oci,dest={archive},name={reference},oci-mediatypes=true,rewrite-timestamp=true",
                        str(context),
                    )
                ),
            )
            if result.returncode:
                sys.stderr.buffer.write(result.stderr[-65536:])
                raise _hold("cloud_build_failed")
            observed = _transport_call(
                transport.collect_build_observation,
                result,
                archive,
                tuple(BUILD_OUTPUT_FIELDS),
                reserved_prefix="PULSEPLATE_",
                **OCI_LIMITS,
            )
            _require_cloud_import_name(observed[2], reference)
            _result, evidence = transport.merge_build_observation(
                observed,
                BUILD_OUTPUT_FIELDS,
                ("module_graph_count", "ui_file_count", "ui_total_bytes"),
            )
            if self._builder_observation(name) != before:
                raise _hold("cloud_builder_identity_drift")
            accepted = _build_evidence({**evidence, **before})
            dependency = cast(dict[str, object], self.spec["dependency"])
            expected = {**self.spec, **dependency}
            if any(
                accepted[field] != expected[field]
                for field in (
                    "source_archive_sha256",
                    "pnpm_binary_sha256",
                    "transformed_go_mod_sha256",
                    "transformed_go_sum_sha256",
                )
            ):
                raise _hold("build_observation_drift")
            return accepted, archive
        finally:
            deleted = _transport_call(transport.run_process, self._plan((buildx, "rm", name), 120))
            if deleted.returncode:
                raise _hold("cloud_builder_cleanup_failed")

    def _scan(self, archive: Path) -> ScanEvidence:
        trivy, report = self.identity["trivy_path"], archive.parent / "trivy-report.json"
        layout = archive.parent / "candidate-oci-layout"
        _transport_call(
            transport.extract_oci_layout,
            archive,
            layout,
            max_archive_bytes=MAX_OCI_ARCHIVE_BYTES,
            max_members=MAX_OCI_MEMBERS,
            max_metadata_bytes=MAX_OCI_METADATA_BYTES,
            code="oci_layout_extract_failed",
        )
        ignore = archive.parent / "empty.ignore"
        _transport_call(transport.write_private_file, ignore, b"")
        version_plan = self._plan((trivy, "--version", "--format", "json"), 60)
        scan_argv = (
            trivy,
            "image",
            "--config",
            "/dev/null",
            "--input",
            str(layout),
            *TRIVY_SCAN_SCOPE,
            "--list-all-pkgs",
            "--ignorefile",
            str(ignore),
            *TRIVY_SCAN_POLICY,
            "--format",
            "json",
            "--output",
            str(report),
        )
        scan_result, report_value = _transport_call(
            transport.execute_json_observation,
            self._plan(scan_argv, 1200),
            report,
            max_bytes=MAX_FILE_BYTES,
        )
        version = _transport_call(transport.run_process, version_plan)
        version_value = _transport_call(transport.parse_json_bytes, version.stdout)
        if version.returncode != 0:
            raise _hold("trivy_version_failed")
        if not isinstance(version_value, dict) or not isinstance(
            version_value.get("VulnerabilityDB"), dict
        ):
            raise _hold("trivy_database_identity_missing")
        normalized_report, covered_targets = _normalize_trivy_report(report_value)
        database = version_value["VulnerabilityDB"]
        database_path = self.trivy_cache / "db" / "trivy.db"
        severities = [
            finding["severity"]
            for row in normalized_report
            for finding in cast(list[dict[str, object]], row["findings"])
        ]
        value = {
            "trivy_version": self.identity["trivy_version"],
            "trivy_executable_sha256": self.identity["trivy_sha256"],
            "database_updated_at": _fresh_database_timestamp(database),
            "database_identity_sha256": _transport_call(
                transport.hash_regular, database_path, max_bytes=MAX_DATABASE_BYTES
            ),
            "report_sha256": sha256_digest(canonical_json(normalized_report)),
            "coverage_sha256": sha256_digest(canonical_json(covered_targets)),
            "covered_targets": covered_targets,
            "high_count": severities.count("HIGH"),
            "critical_count": severities.count("CRITICAL"),
        }
        accepted = _scan_evidence(value)
        if scan_result.returncode != 0:
            raise _hold("trivy_execution_failed")
        return accepted

    def _registry(self, candidate_ref: str) -> transport.RegistryPlan:
        prefix = f"{PUBLICATION_REPOSITORY}:"
        if not candidate_ref.startswith(prefix):
            raise _hold("candidate_ref_invalid")
        return transport.RegistryPlan(
            "ghcr.io",
            "katsiarynakavaleuskaya/pulseplate",
            "repository:katsiarynakavaleuskaya/pulseplate:pull",
            candidate_ref.removeprefix(prefix),
            "application/vnd.oci.image.manifest.v1+json",
            30,
            8_388_608,
            ("ghcr.io", "pkg-containers.githubusercontent.com"),
        )

    def observe(self, candidate_ref: str) -> object:
        observed = _transport_call(transport.observe_registry, self._registry(candidate_ref))
        return None if observed is None else dict(transport.oci_mapping(observed))

    def preflight(self, payload: Mapping[str, object]) -> object:
        candidate_ref = payload["candidate_ref"]
        if not isinstance(candidate_ref, str):
            raise _hold("candidate_ref_invalid")
        build, _second, scan, provenance = self.verify_two_builds(self.spec)
        fresh = _provenance(provenance, self.spec)
        initial = _provenance(payload.get("cloud_provenance"), self.spec)
        if fresh["run_id"] == initial["run_id"] or _timestamp(fresh["started_at"]) < _timestamp(
            initial["completed_at"]
        ):
            raise _hold("cloud_run_reuse_forbidden")
        if build != payload["build_evidence"] or scan != payload["scan_evidence"]:
            raise _hold("publication_preflight_mismatch")
        if self.cloud_archive is None:
            raise _hold("cloud_archive_missing")
        container = self.identity["container_path"]
        source = CLOUD_REFERENCE_PREFIX + sha256_digest(canonical_json(self.spec))[7:]
        archive = self.cloud_archive.parent / "loaded.oci.tar"
        lifecycle = transport.LocalImageLoadPlan(
            self._plan((container, "image", "list", "--format", "json"), 120),
            self._plan((container, "image", "load", "--input", str(self.cloud_archive)), 600),
            self._plan((container, "image", "tag", source, candidate_ref), 120),
            self._plan(
                (
                    container,
                    "image",
                    "save",
                    "--platform",
                    PLATFORM,
                    "--output",
                    str(archive),
                    candidate_ref,
                ),
                600,
            ),
            self._plan((container, "image", "delete", source), 120),
            self._plan((container, "image", "delete", candidate_ref), 120),
            source,
            candidate_ref,
        )
        loaded = _transport_call(
            transport.execute_local_image_load, lifecycle, archive, **OCI_LIMITS
        )
        self.loaded_ref = candidate_ref
        if transport.oci_mapping(loaded) != _oci_fields(cast(BuildEvidence, build)):
            raise _hold("local_load_content_drift")
        return {
            "tag_state": "absent" if self.observe(candidate_ref) is None else "present",
            "build_evidence": build,
            "scan_evidence": scan,
            "cloud_provenance": provenance,
        }

    def process_plans(self, candidate_ref: str) -> tuple[transport.ProcessPlan, ...]:
        container = self.identity["container_path"]
        return (
            self._plan(
                (
                    container,
                    "registry",
                    "login",
                    "--password-stdin",
                    "--username",
                    "Katsiarynakavaleuskaya",
                    "ghcr.io",
                ),
                60,
            ),
            self._plan((container, "image", "push", "--platform", PLATFORM, candidate_ref)),
            self._plan((container, "registry", "logout", "ghcr.io"), 60),
        )

    def close(self) -> None:
        try:
            if self.loaded_ref is not None:
                container = self.identity["container_path"]
                _transport_call(
                    transport.delete_local_image,
                    self._plan((container, "image", "list", "--format", "json"), 120),
                    self._plan((container, "image", "delete", self.loaded_ref), 120),
                    self.loaded_ref,
                    code="local_image_cleanup_failed",
                )
                self.loaded_ref = None
        finally:
            for temporary in self.temporary:
                temporary.cleanup()


def _stage2_observation(repo_root: Path, spec: Mapping[str, object]) -> dict[str, bool]:
    _containerfile, selector = _source_bytes(repo_root)
    consumers = _runtime_consumers(repo_root)
    if (
        _binding(SELECTOR_RELATIVE, selector) != spec.get("runtime_selector")
        or consumers != spec.get("runtime_consumers")
        or spec.get("allowed_actions") != sorted(ALLOWED_ACTIONS)
    ):
        raise _hold("stage2_binding_drift")
    return {
        "candidate_selected": False,
        "runtime_selector_updated": False,
        "deployment_performed": "deploy" in ALLOWED_ACTIONS,
        "t0_activated": "t0" in ALLOWED_ACTIONS,
    }


def _stage30_payload(
    candidate_id: str,
    spec: Mapping[str, object],
    evidence: BuildEvidence,
    scan: ScanEvidence,
    chain_head: Mapping[str, str],
    stage2: Mapping[str, bool],
    provenance: Mapping[str, object],
) -> dict[str, object]:
    authorization_tuple = {
        "schema": f"{SCHEMA}.publication-tuple",
        "repository": "Katsiarynakavaleuskaya/PulsePlate",
        "candidate_id": candidate_id,
        "execution_identity": spec["execution_identity"],
        "workflow": spec["workflow"],
        "cloud_profile": spec["cloud_profile"],
        "cloud_provenance": dict(provenance),
        "containerfile": spec["containerfile"],
        "runtime_selector": spec["runtime_selector"],
        "runtime_consumers": spec["runtime_consumers"],
        "build_evidence": dict(evidence),
        "scan_evidence": dict(scan),
        "destination": PUBLICATION_REPOSITORY,
        "state_chain_head_at_30": dict(chain_head),
        "single_write_limit": 1,
        **stage2,
    }
    tuple_sha256 = hashlib.sha256(canonical_json(authorization_tuple)).hexdigest()
    candidate_ref = f"{PUBLICATION_REPOSITORY}:{PUBLICATION_TAG_PREFIX}-{tuple_sha256}"
    expected_line = f"AUTHORIZE_PROMETHEUS_CANDIDATE_PUSH {tuple_sha256} {candidate_ref}"
    return {
        "comparison": "path-independent-content-equal",
        "build_evidence": dict(evidence),
        "scan_evidence": dict(scan),
        "authorization_tuple": authorization_tuple,
        "cloud_provenance": dict(provenance),
        "tuple_sha256": tuple_sha256,
        "idempotency_key": f"sha256:{tuple_sha256}",
        "candidate_ref": candidate_ref,
        "expected_authorization_line": expected_line,
    }


def _oci_fields(evidence: BuildEvidence) -> dict[str, object]:
    value = evidence
    return {
        "platform": value["platform"],
        "manifest_digest": value["manifest_digest"],
        "config_digest": value["config_digest"],
        "layer_digests": value["layer_digests"],
    }


def _final_payload(
    local: Mapping[str, object] | None, stage2: Mapping[str, bool]
) -> dict[str, object]:
    return {
        "state": "published-unselected-nondeployable",
        "tuple_sha256": local["tuple_sha256"] if local else None,
        "candidate_ref": local["candidate_ref"] if local else None,
        **stage2,
    }


class ReceiptStore:
    def __init__(self, repo_root: Path, candidate_id: str, spec: Mapping[str, object]) -> None:
        if SHA256_RE.fullmatch(candidate_id) is None:
            raise _hold("candidate_id_invalid")
        self.repo_root = repo_root
        self.candidate_id = candidate_id
        self.spec = dict(spec)
        self.directory = _state_root(repo_root) / candidate_id

    def _validate_semantics(self, chain: Mapping[str, Mapping[str, object]]) -> None:
        if "00-spec" in chain and chain["00-spec"]["payload"] != {"spec": self.spec}:
            raise _hold("spec_receipt_invalid")
        first: BuildEvidence | None = None
        expected: dict[str, object]
        if "10-build-one" in chain:
            payload = chain["10-build-one"]["payload"]
            if not isinstance(payload, dict) or payload.get("ordinal") != 1:
                raise _hold("build_receipt_invalid")
            first = _build_evidence(payload.get("evidence"))
            if set(payload) != {"ordinal", "evidence"}:
                raise _hold("build_receipt_invalid")
        if "20-build-two" in chain:
            expected = {"ordinal": 2, "evidence": dict(first) if first else None}
            if chain["20-build-two"]["payload"] != expected:
                raise _hold("build_receipt_invalid")
        local: dict[str, object] | None = None
        if "30-local-verification" in chain:
            payload = chain["30-local-verification"]["payload"]
            if not isinstance(payload, dict):
                raise _hold("local_verification_receipt_invalid")
            scan = _scan_evidence(payload.get("scan_evidence"))
            previous = chain["30-local-verification"]["previous"]
            if not isinstance(previous, dict) or first is None:
                raise _hold("local_verification_receipt_invalid")
            local = _stage30_payload(
                self.candidate_id,
                self.spec,
                first,
                scan,
                previous,
                _stage2_observation(self.repo_root, self.spec),
                _provenance(payload.get("cloud_provenance"), self.spec),
            )
            if payload != local:
                raise _hold("local_verification_receipt_invalid")
        if "40-publication-authorization" in chain:
            expected = {
                "kind": "exact-stdin-one-line",
                "confirmation_line": local["expected_authorization_line"] if local else None,
                "tuple_sha256": local["tuple_sha256"] if local else None,
                "candidate_ref": local["candidate_ref"] if local else None,
                "idempotency_key": local["idempotency_key"] if local else None,
            }
            if chain["40-publication-authorization"]["payload"] != expected:
                raise _hold("publication_authorization_invalid")
        if "50-write-intent" in chain:
            intent = cast(dict[str, object], chain["50-write-intent"]["payload"])
            fresh = _provenance(intent.get("cloud_provenance"), self.spec)
            initial = cast(dict[str, object], local["cloud_provenance"]) if local else {}
            if fresh["run_id"] == initial.get("run_id") or _timestamp(
                fresh["started_at"]
            ) < _timestamp(initial.get("completed_at")):
                raise _hold("cloud_run_reuse_forbidden")
            expected = {
                "candidate_ref": local["candidate_ref"] if local else None,
                "idempotency_key": local["idempotency_key"] if local else None,
                "single_write_limit": 1,
                "cloud_provenance": fresh,
            }
            if chain["50-write-intent"]["payload"] != expected:
                raise _hold("write_intent_invalid")
        if "60-push-result" in chain:
            allowed = (
                {"mode": "creator", "push_invoked": True, "remote_truth": False},
                {"mode": "reconciliation", "push_invoked": False, "remote_truth": False},
            )
            if chain["60-push-result"]["payload"] not in allowed:
                raise _hold("push_result_invalid")
        if "70-remote-verification" in chain:
            expected = {
                "access": "anonymous",
                "oci": _oci_fields(first) if first else None,
                "tuple_sha256": local["tuple_sha256"] if local else None,
                "candidate_ref": local["candidate_ref"] if local else None,
            }
            if chain["70-remote-verification"]["payload"] != expected:
                raise _hold("remote_verification_invalid")
        if "80-final-receipt" in chain:
            expected = _final_payload(local, _stage2_observation(self.repo_root, self.spec))
            if chain["80-final-receipt"]["payload"] != expected:
                raise _hold("final_receipt_invalid")

    def load(self) -> dict[str, dict[str, object]]:
        if not self.directory.exists():
            return {}
        _ensure_private_directory(self.directory)
        entries = {entry.name for entry in self.directory.iterdir()}
        if not entries.issubset(set(RECEIPT_FILES.values())):
            raise _hold("unknown_receipt")
        present = [stage for stage in RECEIPT_ORDER if RECEIPT_FILES[stage] in entries]
        if present != list(RECEIPT_ORDER[: len(present)]):
            raise _hold("receipt_prefix_gap")
        chain: dict[str, dict[str, object]] = {}
        previous: dict[str, str] | None = None
        for stage in present:
            raw = _read_regular(self.directory / RECEIPT_FILES[stage], expected_mode=0o600)
            record = _parse_json(raw, code="receipt_json_invalid")
            if not isinstance(record, dict) or set(record) != {
                "schema",
                "candidate_id",
                "stage",
                "previous",
                "payload",
            }:
                raise _hold("receipt_envelope_invalid")
            if (
                record["schema"] != RECEIPT_SCHEMA
                or record["candidate_id"] != self.candidate_id
                or record["stage"] != stage
                or record["previous"] != previous
                or not isinstance(record["payload"], dict)
            ):
                raise _hold("receipt_envelope_invalid")
            chain[stage] = record
            previous = {"file": RECEIPT_FILES[stage], "sha256": sha256_digest(raw)}
        self._validate_semantics(chain)
        return chain

    def append(self, stage: str, payload: Mapping[str, object]) -> bool:
        if stage not in RECEIPT_ORDER:
            raise _hold("unknown_stage")
        _ensure_private_tree(self.repo_root, self.directory)
        chain = self.load()
        index = RECEIPT_ORDER.index(stage)
        if any(required not in chain for required in RECEIPT_ORDER[:index]):
            raise _hold("receipt_prefix_gap")
        previous = None
        if index:
            previous_raw = _read_regular(
                self.directory / RECEIPT_FILES[RECEIPT_ORDER[index - 1]],
                expected_mode=0o600,
            )
            previous = {
                "file": RECEIPT_FILES[RECEIPT_ORDER[index - 1]],
                "sha256": sha256_digest(previous_raw),
            }
        record = {
            "schema": RECEIPT_SCHEMA,
            "candidate_id": self.candidate_id,
            "stage": stage,
            "previous": previous,
            "payload": dict(payload),
        }
        created = _atomic_no_replace(self.directory / RECEIPT_FILES[stage], canonical_json(record))
        self.load()
        return created

    def link(self, stage: str) -> dict[str, str]:
        if stage not in self.load():
            raise _hold("receipt_link_missing")
        raw = _read_regular(self.directory / RECEIPT_FILES[stage], expected_mode=0o600)
        return {"file": RECEIPT_FILES[stage], "sha256": sha256_digest(raw)}


class CandidateController:
    def __init__(
        self,
        repo_root: Path,
        *,
        identity_provider: Callable[[Path], ExecutionIdentity] = resolve_execution_identity,
        build_adapter: BuildAdapter | None = None,
        publication_adapter: PublicationAdapter | None = None,
    ) -> None:
        self.repo_root = repo_root
        self.identity_provider = identity_provider
        self.identity = identity_provider(repo_root)
        self.spec = build_spec(repo_root, self.identity)
        self.candidate_id = sha256_digest(canonical_json(self.spec))
        self.store = ReceiptStore(repo_root, self.candidate_id, self.spec)
        if build_adapter is None and publication_adapter is None:
            exact = ExactAdapters(repo_root, self.identity, self.spec)
            self.build_adapter: BuildAdapter = exact
            self.publication_adapter: PublicationAdapter = exact
        elif build_adapter is not None and publication_adapter is not None:
            self.build_adapter = build_adapter
            self.publication_adapter = publication_adapter
        else:
            raise _hold("adapter_set_incomplete")

    def _assert_bindings(self) -> None:
        if build_spec(self.repo_root, self.identity_provider(self.repo_root)) != self.spec:
            raise _hold("prebuild_spec_drift")

    def freeze(self) -> bool:
        self._assert_bindings()
        return self.store.append("00-spec", {"spec": self.spec})

    def verify_local(self) -> dict[str, object]:
        self.freeze()
        chain = self.store.load()
        if "30-local-verification" in chain:
            return cast(dict[str, object], chain["30-local-verification"]["payload"]).copy()
        try:
            observations = self.build_adapter.verify_two_builds(self.spec)
        except transport.TransportError as exc:
            raise _hold("build_adapter_failed") from exc
        if not isinstance(observations, tuple) or len(observations) != 4:
            raise _hold("cloud_observations_incomplete")
        first_raw, second_raw, scan_raw, provenance_raw = observations
        first = _build_evidence(first_raw)
        second = _build_evidence(second_raw)
        scan = _scan_evidence(scan_raw)
        provenance = _provenance(provenance_raw, self.spec)
        if canonical_json(first) != canonical_json(second):
            raise _hold("path_independent_build_mismatch")
        self._assert_bindings()
        self.store.append("10-build-one", {"ordinal": 1, "evidence": first})
        self.store.append("20-build-two", {"ordinal": 2, "evidence": first})
        local = _stage30_payload(
            self.candidate_id,
            self.spec,
            first,
            scan,
            self.store.link("20-build-two"),
            _stage2_observation(self.repo_root, self.spec),
            provenance,
        )
        self.store.append("30-local-verification", local)
        return local

    def local_payload(self) -> dict[str, object]:
        self._assert_bindings()
        chain = self.store.load()
        if "30-local-verification" not in chain:
            raise _hold("local_verification_required")
        return cast(dict[str, object], chain["30-local-verification"]["payload"]).copy()

    def show_publication_tuple(self) -> dict[str, object]:
        local = self.local_payload()
        return {
            key: local[key]
            for key in (
                "authorization_tuple",
                "tuple_sha256",
                "idempotency_key",
                "candidate_ref",
                "expected_authorization_line",
            )
        }

    def authorize(self, operator_line: str) -> bool:
        local = self.local_payload()
        if operator_line != local["expected_authorization_line"]:
            raise _hold("stale_or_invalid_authorization")
        return self.store.append(
            "40-publication-authorization",
            {
                "kind": "exact-stdin-one-line",
                "confirmation_line": operator_line,
                "tuple_sha256": local["tuple_sha256"],
                "candidate_ref": local["candidate_ref"],
                "idempotency_key": local["idempotency_key"],
            },
        )

    @staticmethod
    def _credential_after_intent() -> bytes:
        raw = os.environ.get(PUBLICATION_INPUT_ENV)
        if (
            not isinstance(raw, str)
            or not raw
            or len(raw) > 16_384
            or raw != raw.strip()
            or any(character in raw for character in ("\x00", "\r", "\n"))
        ):
            raise _hold("publication_credential_unavailable")
        return raw.encode()

    def publish_or_reconcile(self) -> dict[str, object]:
        self._assert_bindings()
        chain = self.store.load()
        if "40-publication-authorization" not in chain:
            raise _hold("publication_authorization_required")
        if "80-final-receipt" in chain:
            return cast(dict[str, object], chain["80-final-receipt"]["payload"]).copy()
        local = self.local_payload()
        expected = _build_evidence(local["build_evidence"])
        expected_scan = _scan_evidence(local["scan_evidence"])
        created = False
        try:
            if "50-write-intent" not in chain:
                preflight = self.publication_adapter.preflight(local)
                required = {"tag_state", "build_evidence", "scan_evidence", "cloud_provenance"}
                if not isinstance(preflight, dict) or set(preflight) != required:
                    raise _hold("publication_preflight_invalid")
                if preflight["tag_state"] != "absent":
                    raise _hold("preexisting_or_ambiguous_tag")
                if (
                    _build_evidence(preflight["build_evidence"]) != expected
                    or _scan_evidence(preflight["scan_evidence"]) != expected_scan
                ):
                    raise _hold("publication_preflight_mismatch")
                provenance = _provenance(preflight["cloud_provenance"], self.spec)
                initial = cast(dict[str, object], local["cloud_provenance"])
                if provenance["run_id"] == initial["run_id"] or _timestamp(
                    provenance["started_at"]
                ) < _timestamp(initial["completed_at"]):
                    raise _hold("cloud_run_reuse_forbidden")
                self._assert_bindings()
                _stage2_observation(self.repo_root, self.spec)
                created = self.store.append(
                    "50-write-intent",
                    {
                        "candidate_ref": local["candidate_ref"],
                        "idempotency_key": local["idempotency_key"],
                        "single_write_limit": 1,
                        "cloud_provenance": provenance,
                    },
                )
            if created:
                login, push, logout = self.publication_adapter.process_plans(
                    str(local["candidate_ref"])
                )
                credential = self._credential_after_intent()
                try:
                    transport.login_push_logout(login, push, logout, credential)
                except transport.TransportError as exc:
                    raise _hold("credentialed_publication_failed") from exc
                finally:
                    credential = b""
                self.store.append(
                    "60-push-result",
                    {"mode": "creator", "push_invoked": True, "remote_truth": False},
                )
            chain = self.store.load()
            observed = self.publication_adapter.observe(str(local["candidate_ref"]))
            if observed != _oci_fields(expected):
                raise _hold("remote_evidence_mismatch")
            if "60-push-result" not in chain:
                self.store.append(
                    "60-push-result",
                    {"mode": "reconciliation", "push_invoked": False, "remote_truth": False},
                )
            self.store.append(
                "70-remote-verification",
                {
                    "access": "anonymous",
                    "oci": observed,
                    "tuple_sha256": local["tuple_sha256"],
                    "candidate_ref": local["candidate_ref"],
                },
            )
            self._assert_bindings()
            stage2 = _stage2_observation(self.repo_root, self.spec)
            terminal = _final_payload(local, stage2)
            self.store.append("80-final-receipt", terminal)
            return terminal
        except transport.TransportError as exc:
            raise _hold("publication_adapter_failed") from exc
        finally:
            self.publication_adapter.close()

    def status(self) -> dict[str, object]:
        self._assert_bindings()
        chain = self.store.load()
        return {
            "schema": f"{SCHEMA}.status",
            "candidate_id": self.candidate_id,
            "completed_stage": next(reversed(chain), None),
            "receipt_count": len(chain),
        }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("freeze")
    commands.add_parser("status")
    commands.add_parser("verify-local")
    commands.add_parser("show-publication-tuple")
    commands.add_parser("authorize")
    commands.add_parser("publish-or-reconcile")
    commands.add_parser("cloud-execute")
    return parser


def _read_operator_line() -> str:
    raw = sys.stdin.buffer.read(16_385)
    if len(raw) > 16_384 or raw.count(b"\n") != 1 or not raw.endswith(b"\n") or b"\r" in raw:
        raise _hold("operator_confirmation_not_one_line")
    try:
        return raw[:-1].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise _hold("operator_confirmation_invalid") from exc


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "cloud-execute":
            result = execute_cloud(_repo_root())
            sys.stdout.buffer.write(canonical_json(result))
            return 0
        controller = CandidateController(_repo_root())
        if arguments.command == "freeze":
            result = {"created": controller.freeze(), **controller.status()}
        elif arguments.command == "status":
            result = controller.status()
        elif arguments.command == "verify-local":
            result = controller.verify_local()
        elif arguments.command == "show-publication-tuple":
            result = controller.show_publication_tuple()
        elif arguments.command == "authorize":
            result = {"created": controller.authorize(_read_operator_line())}
        elif arguments.command == "publish-or-reconcile":
            result = controller.publish_or_reconcile()
        else:
            raise _hold("unsupported_command")
    except (CandidateHold, transport.TransportError) as exc:
        print(f"HOLD:{exc}", file=sys.stderr)
        return 1
    sys.stdout.buffer.write(canonical_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
