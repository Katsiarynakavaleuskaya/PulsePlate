#!/usr/bin/env python3
"""Closed local state core for the Prometheus gRPC derivative candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TypeVar, cast

import yaml

if TYPE_CHECKING or __package__:
    from scripts.ci import _prometheus_derivative_transport as transport
else:
    import _prometheus_derivative_transport as transport
SCHEMA = "pulseplate.prometheus_derivative_candidate.v1"
RECEIPT_SCHEMA = "pulseplate.prometheus_derivative_candidate_receipt.v1"
SCRIPT_VERSION = "1.0.0"
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
    "cc2e6d651d38b798a61dbab60c657cc0e4fd29579dcd6a73501840e1f55a2790"  # pragma: allowlist secret
)
EXPECTED_SELECTOR_SHA256 = (
    "06e312ed9efe5ec96a582e7a1ee1291dc02c451f773fb6756fb411ef18ece457"  # pragma: allowlist secret
)
PUBLICATION_INPUT_ENV = "PULSEPLATE_PROMETHEUS_GHCR_TOKEN"
PUBLICATION_REPOSITORY = "ghcr.io/katsiarynakavaleuskaya/pulseplate"
PUBLICATION_TAG_PREFIX = "prometheus-grpc-v1.83.1"
APPLE_BUILDER_REFERENCE = "ghcr.io/apple/container-builder-shim/builder:0.12.0"
APPLE_BUILDER_INDEX_DIGEST = (
    "sha256:edf820e05c3374485390e7fe3669f1b6b429eda502a6d174a456647fb9ed26fe"
)
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_RECEIPT_BYTES = 1_048_576
MAX_EXECUTABLE_BYTES = 256 * 1024 * 1024
MAX_OCI_ARCHIVE_BYTES = 4 * 1024 * 1024 * 1024
MAX_DATABASE_BYTES = 2 * 1024 * 1024 * 1024
MAX_OCI_MEMBERS = 4096
MAX_OCI_METADATA_BYTES = 4 * 1024 * 1024
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
APPLE_BUILDER_CPUS = 4
APPLE_BUILDER_MEMORY = "6G"
APPLE_BUILDER_MEMORY_BYTES = 6 * 1024 * 1024 * 1024
APPLE_BUILD_RESOURCES = (
    "--platform",
    PLATFORM,
    "--cpus",
    str(APPLE_BUILDER_CPUS),
    "--memory",
    APPLE_BUILDER_MEMORY,
)
APPLE_BUILD_MODE = ("--no-cache", "--progress", "plain")
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
            "trivy": ("trivy", "--version"),
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
    git, container, trivy = (observed[name] for name in ("git_head", "container", "trivy"))
    head, tree = observed["git_head"].stdout, observed["git_tree"].stdout
    if not re.fullmatch(r"[0-9a-f]{40}", head) or not re.fullmatch(r"[0-9a-f]{40}", tree):
        raise _hold("git_identity_invalid")
    if container.stdout != "container CLI version 1.1.0 (build: release, commit: 5973b9c)":
        raise _hold("container_identity_invalid")
    if not trivy.stdout.splitlines() or trivy.stdout.splitlines()[0] != "Version: 0.74.0":
        raise _hold("trivy_identity_invalid")
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
        "trivy_path": str(trivy.path),
        "trivy_sha256": trivy.sha256,
        "trivy_version": "0.74.0",
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
    def verify_two_builds(self, spec: Mapping[str, object]) -> tuple[object, object, object]: ...


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

    def _builder_observation(self) -> dict[str, str]:
        container = self.identity["container_path"]
        result = _transport_call(
            transport.run_process,
            self._plan((container, "builder", "status", "--format", "json"), 60),
        )
        if result.returncode != 0:
            raise _hold("apple_builder_identity_unavailable")
        value = _parse_json(result.stdout, code="apple_builder_identity_invalid")
        if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], dict):
            raise _hold("apple_builder_identity_invalid")
        configuration = value[0].get("configuration")
        image = configuration.get("image") if isinstance(configuration, dict) else None
        descriptor = image.get("descriptor") if isinstance(image, dict) else None
        platform_value = configuration.get("platform") if isinstance(configuration, dict) else None
        resources = configuration.get("resources") if isinstance(configuration, dict) else None
        if (
            not isinstance(image, dict)
            or not isinstance(descriptor, dict)
            or image.get("reference") != APPLE_BUILDER_REFERENCE
            or descriptor.get("digest") != APPLE_BUILDER_INDEX_DIGEST
            or not isinstance(platform_value, dict)
            or platform_value.get("os") != "linux"
            or platform_value.get("architecture") != "arm64"
            or not isinstance(configuration, dict)
            or configuration.get("rosetta") is not True
        ):
            raise _hold("apple_builder_identity_invalid")
        if (
            not isinstance(resources, dict)
            or resources.get("cpus") != APPLE_BUILDER_CPUS
            or resources.get("memoryInBytes") != APPLE_BUILDER_MEMORY_BYTES
        ):
            raise _hold("apple_builder_resources_invalid")
        normalized = {
            "reference": image["reference"],
            "digest": descriptor["digest"],
            "media_type": descriptor.get("mediaType"),
            "platform": platform_value,
            "rosetta": True,
            "resources": {
                "cpus": resources["cpus"],
                "memoryInBytes": resources["memoryInBytes"],
            },
        }
        return {
            "builder_image_digest": APPLE_BUILDER_INDEX_DIGEST,
            "builder_status_sha256": sha256_digest(canonical_json(normalized)),
        }

    def _build(self, tag: str, *, keep_local: bool = False) -> tuple[BuildEvidence, Path]:
        builder_before = self._builder_observation()
        temporary = tempfile.TemporaryDirectory(prefix="pulseplate-prometheus-build-")
        self.temporary.append(temporary)
        root, container = Path(temporary.name), self.identity["container_path"]
        context = root / "context"
        context.mkdir(mode=0o700)
        recipe = context / "Containerfile"
        _transport_call(
            transport.write_private_file,
            recipe,
            _read_regular(self.repo_root / CONTAINERFILE_RELATIVE),
        )
        archive = root / "candidate.oci.tar"
        argv = (
            container,
            "build",
            "--file",
            str(recipe),
            "--tag",
            tag,
            *APPLE_BUILD_RESOURCES,
            *APPLE_BUILD_MODE,
            "--build-arg",
            "SOURCE_DATE_EPOCH=1788079847",
            str(context),
        )
        save_prefix = (container, "image", "save", "--platform", PLATFORM, "--output")
        save_argv = (*save_prefix, str(archive), tag)
        lifecycle = transport.LocalImageBuildPlan(
            self._plan((container, "image", "list", "--quiet"), 120),
            self._plan(argv),
            self._plan(save_argv, 600),
            self._plan((container, "image", "delete", tag), 120),
            tag,
            keep_local,
        )
        observed = _transport_call(
            transport.execute_local_image_build_observation,
            lifecycle,
            archive,
            tuple(BUILD_OUTPUT_FIELDS),
            reserved_prefix="PULSEPLATE_",
            max_archive_bytes=MAX_OCI_ARCHIVE_BYTES,
            max_members=MAX_OCI_MEMBERS,
            max_metadata_bytes=MAX_OCI_METADATA_BYTES,
            code="apple_build_failed",
        )
        if keep_local:
            self.loaded_ref = tag
        result, evidence = _transport_call(
            transport.merge_build_observation,
            observed,
            BUILD_OUTPUT_FIELDS,
            ("module_graph_count", "ui_file_count", "ui_total_bytes"),
        )
        if result.returncode != 0:
            raise _hold("apple_build_failed")
        builder_after = self._builder_observation()
        if builder_after != builder_before:
            raise _hold("apple_builder_identity_drift")
        evidence = {**evidence, **builder_after}
        accepted, dependency = _build_evidence(evidence), self.spec["dependency"]
        if not isinstance(dependency, dict) or (
            accepted["source_archive_sha256"] != self.spec["source_archive_sha256"]
            or accepted["pnpm_binary_sha256"] != self.spec["pnpm_binary_sha256"]
            or accepted["transformed_go_mod_sha256"] != dependency["transformed_go_mod_sha256"]
            or accepted["transformed_go_sum_sha256"] != dependency["transformed_go_sum_sha256"]
        ):
            raise _hold("build_observation_drift")
        return accepted, archive

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

    def verify_two_builds(self, spec: Mapping[str, object]) -> tuple[object, object, object]:
        if spec != self.spec:
            raise _hold("prebuild_spec_drift")
        first, archive = self._build("pulseplate-prometheus:verify-one")
        second, _archive = self._build("pulseplate-prometheus:verify-two")
        return first, second, self._scan(archive)

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
        build, archive = self._build(candidate_ref, keep_local=True)
        scan = self._scan(archive)
        return {
            "tag_state": "absent" if self.observe(candidate_ref) is None else "present",
            "build_evidence": build,
            "scan_evidence": scan,
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
        if self.loaded_ref is not None:
            container = self.identity["container_path"]
            deleted = _transport_call(
                transport.run_process,
                self._plan((container, "image", "delete", self.loaded_ref), 120),
                code="local_image_cleanup_failed",
            )
            if deleted.returncode != 0:
                raise _hold("local_image_cleanup_failed")
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
) -> dict[str, object]:
    authorization_tuple = {
        "schema": f"{SCHEMA}.publication-tuple",
        "repository": "Katsiarynakavaleuskaya/PulsePlate",
        "candidate_id": candidate_id,
        "execution_identity": spec["execution_identity"],
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
            expected = {
                "candidate_ref": local["candidate_ref"] if local else None,
                "idempotency_key": local["idempotency_key"] if local else None,
                "single_write_limit": 1,
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
            first_raw, second_raw, scan_raw = self.build_adapter.verify_two_builds(self.spec)
        except transport.TransportError as exc:
            raise _hold("build_adapter_failed") from exc
        first = _build_evidence(first_raw)
        second = _build_evidence(second_raw)
        scan = _scan_evidence(scan_raw)
        if canonical_json(first) != canonical_json(second):
            raise _hold("path_independent_build_mismatch")
        self.store.append("10-build-one", {"ordinal": 1, "evidence": first})
        self.store.append("20-build-two", {"ordinal": 2, "evidence": first})
        local = _stage30_payload(
            self.candidate_id,
            self.spec,
            first,
            scan,
            self.store.link("20-build-two"),
            _stage2_observation(self.repo_root, self.spec),
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
                required = {"tag_state", "build_evidence", "scan_evidence"}
                if not isinstance(preflight, dict) or set(preflight) != required:
                    raise _hold("publication_preflight_invalid")
                if preflight["tag_state"] != "absent":
                    raise _hold("preexisting_or_ambiguous_tag")
                if (
                    _build_evidence(preflight["build_evidence"]) != expected
                    or _scan_evidence(preflight["scan_evidence"]) != expected_scan
                ):
                    raise _hold("publication_preflight_mismatch")
                self._assert_bindings()
                _stage2_observation(self.repo_root, self.spec)
                created = self.store.append(
                    "50-write-intent",
                    {
                        "candidate_ref": local["candidate_ref"],
                        "idempotency_key": local["idempotency_key"],
                        "single_write_limit": 1,
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
        controller = CandidateController(_repo_root())
        if arguments.command == "freeze":
            result: object = {"created": controller.freeze(), **controller.status()}
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
