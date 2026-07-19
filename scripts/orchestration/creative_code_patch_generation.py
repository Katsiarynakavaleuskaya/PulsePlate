#!/usr/bin/env python3
"""Gate and execute local PR-2 creative-code patch generation/evaluation."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from contextlib import contextmanager
import importlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tempfile
from typing import Any, Iterator, cast

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.evidence.fingerprints import build_asset_id, build_idempotency_key, fingerprint_payload
from scripts.orchestration import creative_code_patch_builder
from scripts.orchestration import creative_spec_patch_admission as admission_cli
from scripts.orchestration.creative_code_patch_contract import (
    CreativeCodePatchContractError,
    FAILURE_CLASSES,
    build_creative_code_patch_result,
    classify_failure_class_coherence,
    classify_terminal_outcome_coherence,
    read_creative_code_patch_build_request,
    read_creative_code_patch_result,
    validate_creative_code_patch_build_request,
    validate_creative_code_patch_result,
    validate_creative_code_patch_run_sidecars,
)
from scripts.orchestration.creative_code_patch_workspace import (
    CreativeCodePatchWorkspaceError,
    read_json,
    resolve_existing_run_dir,
    resolve_run_dir,
    resolve_run_file,
    shared_tree_status,
    verify_origin_main_base,
    write_json_atomic,
)
from scripts.orchestration.creative_code_specification import (
    CreativeCodeSpecificationError,
    validate_creative_code_specification_bundle,
)
from scripts.orchestration.experiment_contract import (
    DEFAULT_RUNNER_MODE,
    DEFAULT_STOP_CONDITION,
    validate_budget_payload,
    validate_capability_zero_attempt_observations,
    validate_experiment_packet,
    validate_experiment_result,
    validate_failure_retry_observations,
    validate_metrics,
)
from scripts.orchestration.experiment_runner import OOM_PATTERNS
from scripts.orchestration.experiment_runner_dispatch import (
    BLOCKER_CODES as TRUSTED_DISPATCH_PREFLIGHT_BLOCKERS,
    CONTAINER_BACKENDS as TRUSTED_DISPATCH_BACKENDS,
    MAX_RESULT_BYTES as TRUSTED_DISPATCH_RESULT_MAX_BYTES,
    RUNNER_CAPABILITY_ERROR as TRUSTED_DISPATCH_CAPABILITY_ERROR,
)
from scripts.orchestration.creative_spec_learning_rollup_contract import (
    CreativeSpecLearningRollupError,
    validate_coordinator_advisory_hints,
)
from scripts.orchestration.creative_spec_patch_admission_contract import (
    CreativeSpecPatchAdmissionError,
)

SCHEMA_VERSION = "1.0"
POLICY_VERSION = "creative-code-patch-generation-gate-v1"
GATE_ARTIFACT_TYPE = "creative_code_patch_generation_gate"
RECEIPT_ARTIFACT_TYPE = "creative_code_patch_generation_receipt"

CREATIVE_CODE_ROOT = REPO_ROOT / "artifacts" / "orchestration" / "creative_code"
PATCH_GENERATION_ROOT = CREATIVE_CODE_ROOT / "patch_generation"
GATE_FILENAME = "generation_gate.json"
RECEIPT_FILENAME = "generation_receipt.json"
TRUSTED_DISPATCH_CANDIDATE_PATCH_REFS = frozenset(
    {
        "candidate.patch",
        ".experiment-runner-input/candidate.patch",
    }
)
ORACLE_REQUIRED_FAILURE_CLASSES = frozenset(
    {"timeout", "oom", "metric_regression", "guard_failure"}
)
FAILING_ORACLE_REQUIRED_FAILURE_CLASSES = frozenset({"timeout", "oom", "guard_failure"})

VALIDATE_RUN_PLAN_SUCCESS_OUTPUT = "PASS: creative-code patch generation gate passed"
GENERATE_CANDIDATE_SUCCESS_OUTPUT = "PASS: creative-code patch generate/evaluate complete"
FINALIZE_DISPATCHED_RESULT_SUCCESS_OUTPUT = (
    "PASS: trusted dispatch result finalized into creative-code patch receipt"
)
VALIDATE_ARTIFACTS_SUCCESS_OUTPUT = "PASS: creative-code patch generation artifacts valid"

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SHA_RE = re.compile(r"^[a-f0-9]{40}$")
SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{12,}|gh[psoru]_[A-Za-z0-9_.-]{12,}|github_pat_|"
    r"xox[abprs]-|authorization:\s*bearer|private[_ -]?key|api[_ -]?key|"
    r"GH_TOKEN|GITHUB_TOKEN)",
    re.IGNORECASE,
)
LEAK_TEXT_RE = re.compile(
    r"(diff --git|^\+\+\+ |^--- |@@ |"
    r"raw[_ -]?(prompt|response|context|patch|review|body)|"
    r"chain[_ -]?of[_ -]?thought|provider[_ -]?payload|"
    r"oracle[_ -]?(stdout|stderr)|review[_ -]?thread[_ -]?body|"
    r"pull[_ -]?request[_ -]?body|file://|https?://|"
    r"/(?:Users|home|private/var|var/folders|tmp|etc|opt|usr|Volumes|mnt|root|"
    r"workspace|workspaces)(?:/|$)|~[/\\]|[A-Za-z]:[\\/]|\.venv/|\.git/|"
    r"worktrees([:/._-]|$)|github_pat_|gh[psoru]_|xox[abprs]-|"
    r"sk-[A-Za-z0-9_-]{12,}|GH_TOKEN|GITHUB_TOKEN)",
    re.IGNORECASE | re.MULTILINE,
)

GATE_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "gate_id",
        "idempotency_key",
        "admission_id",
        "admission_fingerprint",
        "admission_ref",
        "request_id",
        "request_fingerprint",
        "request_ref",
        "source_bundle_id",
        "source_bundle_fingerprint",
        "source_bundle_ref",
        "selected_variant_id",
        "selected_variant_fingerprint",
        "base_commit_sha",
        "run_id",
        "state_fingerprint",
        "budget_limits",
        "allowed_paths_fingerprint",
        "oracle_commands_fingerprint",
        "metrics_fingerprint",
        "immutable_oracles_fingerprint",
        "oracle_command_count",
        "metric_count",
        "immutable_oracle_count",
        "coordinator_advisory_hints_ref",
        "coordinator_advisory_hints_fingerprint",
        "checks",
        "passed_checks",
        "total_checks",
        "next_action",
        "authority",
        "sanitized",
    }
)
GATE_CHECK_KEYS = frozenset(
    {
        "admission_bindings_valid",
        "admission_prepared",
        "run_state_matches_admission",
        "run_artifacts_present",
        "selected_variant_matches_request",
        "base_matches_origin_main",
        "shared_tree_clean",
        "budgets_within_request_contract",
        "immutable_oracles_bound",
        "authority_within_pr2",
        "advisory_hints_non_authoritative",
        "no_preexisting_candidate_artifacts",
    }
)
BUDGET_LIMIT_KEYS = frozenset(
    {
        "generation_attempts",
        "generation_timeout_seconds",
        "evaluation_timeout_seconds",
        "max_changed_files",
        "max_diff_lines",
        "max_patch_bytes",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "receipt_id",
        "idempotency_key",
        "gate_id",
        "gate_fingerprint",
        "gate_ref",
        "admission_id",
        "admission_fingerprint",
        "admission_ref",
        "request_id",
        "request_fingerprint",
        "request_ref",
        "source_bundle_id",
        "source_bundle_fingerprint",
        "source_bundle_ref",
        "selected_variant_id",
        "selected_variant_fingerprint",
        "base_commit_sha",
        "run_id",
        "candidate_patch_ref",
        "patch_metadata_ref",
        "patch_metadata_fingerprint",
        "experiment_packet_ref",
        "experiment_packet_fingerprint",
        "result_ref",
        "result_id",
        "result_fingerprint",
        "status",
        "failure_class",
        "changed_paths",
        "patch_summary",
        "workspace_summary",
        "runner_summary",
        "promotion_ready",
        "checks",
        "passed_checks",
        "total_checks",
        "authority",
        "sanitized",
    }
)
RECEIPT_CHECK_KEYS = frozenset(
    {
        "gate_valid",
        "result_valid",
        "request_matches_gate",
        "candidate_patch_metadata_current",
        "experiment_packet_current",
        "sidecar_refs_bound_to_run",
        "workspace_proof_recorded",
        "promotion_not_ready",
        "authority_within_pr2",
    }
)
GATE_RECEIPT_PROVENANCE_KEYS = (
    "gate_id",
    "admission_id",
    "admission_fingerprint",
    "admission_ref",
    "request_id",
    "request_fingerprint",
    "request_ref",
    "source_bundle_id",
    "source_bundle_fingerprint",
    "source_bundle_ref",
    "selected_variant_id",
    "selected_variant_fingerprint",
    "base_commit_sha",
    "run_id",
)
RESULT_RECEIPT_PROVENANCE_KEYS = (
    "request_id",
    "source_bundle_id",
    "source_bundle_fingerprint",
    "selected_variant_id",
    "selected_variant_fingerprint",
    "base_commit_sha",
)
PATCH_SUMMARY_KEYS = frozenset({"patch_fingerprint", "patch_bytes", "diff_lines"})
PATCH_METADATA_KEYS = frozenset(
    {"changed_paths", "changed_path_statuses", "patch_fingerprint", "patch_bytes", "diff_lines"}
)
WORKSPACE_SUMMARY_KEYS = frozenset(
    {
        "detached_base_sha",
        "origin_removed",
        "checkout_destroyed",
        "shared_tree_untouched",
    }
)
RUNNER_SUMMARY_KEYS = frozenset(
    {
        "experiment_id",
        "status",
        "failure_class",
        "mutated_path_count",
        "oracle_commands_configured",
        "oracle_commands_executed",
        "attempts",
        "retries_consumed",
        "shared_tree_untouched",
        "runner_result_fingerprint",
        "runner_error_present",
        "runner_error_fingerprint",
    }
)
AUTHORITY_TRUE_KEYS = frozenset(
    {
        "emit_local_artifacts",
        "run_patch_builder_evaluate",
        "run_patch_builder_generate",
        "validate_generation_gate",
    }
)
AUTHORITY_FALSE_KEYS = frozenset(
    {
        "call_arbitrary_network",
        "call_product_runtime",
        "call_provider",
        "claim_merge_readiness",
        "create_branch",
        "edit_fixed_mapping",
        "merge",
        "modify_workflows",
        "open_draft_pr",
        "open_pull_request",
        "post_github_comment",
        "promote_candidate",
        "push_branch",
        "read_secrets",
        "release",
        "resolve_review_threads",
        "slack_github_authority_expansion",
        "use_semantic_cache",
        "write_graph_truth",
        "write_repository",
        "write_shared_worktree",
    }
)
AUTHORITY_KEYS = AUTHORITY_TRUE_KEYS | AUTHORITY_FALSE_KEYS


class CreativeCodePatchGenerationError(ValueError):
    """Raised when PR-2 generation/evaluation gating fails closed."""


class CreativeCodePatchGenerationGate:
    """Build and validate deterministic pre-generation gate artifacts."""

    @staticmethod
    def build(
        *,
        admission_path: Path,
        run_id: str,
        coordinator_advisory_hints_path: Path | None = None,
    ) -> dict[str, Any]:
        return build_generation_gate(
            admission_path=admission_path,
            run_id=run_id,
            coordinator_advisory_hints_path=coordinator_advisory_hints_path,
        )

    @staticmethod
    def validate(payload: Mapping[str, Any]) -> dict[str, Any]:
        return validate_generation_gate(payload)


def default_generation_authority() -> dict[str, bool]:
    """Return the only authority granted to the local generation gate."""

    return {key: key in AUTHORITY_TRUE_KEYS for key in sorted(AUTHORITY_KEYS)}


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _existing_components(path: Path) -> list[Path]:
    current_path = Path(path.anchor) if path.anchor else Path(".")
    parts = path.parts[1:] if path.anchor else path.parts
    components: list[Path] = []
    for part in parts:
        current_path = current_path / part
        if current_path.exists() or current_path.is_symlink():
            components.append(current_path)
    return components


def _reject_symlink_components(path: Path, *, label: str) -> None:
    for component in _existing_components(path):
        if component.is_symlink():
            raise CreativeCodePatchGenerationError(f"{label} must not traverse symlinks.")


def _ensure_generation_root() -> Path:
    _reject_symlink_components(PATCH_GENERATION_ROOT, label="patch generation root")
    PATCH_GENERATION_ROOT.mkdir(parents=True, exist_ok=True)
    _reject_symlink_components(PATCH_GENERATION_ROOT, label="patch generation root")
    root = PATCH_GENERATION_ROOT.resolve(strict=True)
    if not root.is_dir():
        raise CreativeCodePatchGenerationError("patch generation root must be a directory.")
    return root


def _resolve_output_dir(raw_output: str) -> Path:
    root = _ensure_generation_root()
    candidate = Path(raw_output)
    path = candidate if candidate.is_absolute() else REPO_ROOT / candidate
    _reject_symlink_components(path, label="output directory")
    resolved = path.resolve(strict=False)
    if not _is_relative_to(resolved, root):
        raise CreativeCodePatchGenerationError(
            "output directory must stay under creative-code patch generation artifacts."
        )
    if path.exists() or path.is_symlink():
        raise CreativeCodePatchGenerationError(
            "output directory already exists; remove the local artifact before rerun."
        )
    path.mkdir(parents=True, exist_ok=False)
    _reject_symlink_components(path, label="output directory")
    return path.resolve(strict=True)


def _default_output_dir(run_id: str) -> Path:
    _normalize_id(run_id, label="run_id")
    return PATCH_GENERATION_ROOT / run_id


def _repo_ref(path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise CreativeCodePatchGenerationError("artifact path must stay under repo root.") from exc


def _reject_duplicate_json_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise CreativeCodePatchGenerationError(
                "creative-code patch generation JSON has duplicate key."
            )
        seen.add(key)
        payload[key] = value
    return payload


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    resolved = admission_cli._resolve_repo_json_file(path, label=label)
    try:
        payload = json.loads(
            resolved.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_object_keys,
        )
    except CreativeCodePatchGenerationError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CreativeCodePatchGenerationError(f"unable to read {label}.") from exc
    if not isinstance(payload, dict):
        raise CreativeCodePatchGenerationError(f"{label} must be a JSON object.")
    return payload


def _read_pinned_json_object(
    path: Path,
    *,
    trusted_root: Path,
    label: str,
    max_bytes: int,
) -> dict[str, Any]:
    """Read one contained JSON object through root-relative no-follow descriptors."""

    try:
        root_relative = trusted_root.relative_to(REPO_ROOT)
        relative = path.relative_to(trusted_root)
    except ValueError as exc:
        raise CreativeCodePatchGenerationError(
            f"{label} must stay under its trusted root."
        ) from exc
    parts = relative.parts
    if (
        not parts
        or any(part in {"", ".", ".."} for part in parts)
        or any(part in {"", ".", ".."} for part in root_relative.parts)
    ):
        raise CreativeCodePatchGenerationError(f"{label} must use a safe relative path.")
    nofollow = getattr(os, "O_NOFOLLOW", None)
    directory = getattr(os, "O_DIRECTORY", None)
    if not isinstance(nofollow, int) or not isinstance(directory, int):
        raise CreativeCodePatchGenerationError(
            f"{label} no-follow reads are unavailable on this platform."
        )
    directory_flags = os.O_RDONLY | directory | nofollow | getattr(os, "O_CLOEXEC", 0)
    file_flags = os.O_RDONLY | os.O_NONBLOCK | nofollow | getattr(os, "O_CLOEXEC", 0)
    descriptor = -1
    file_descriptor = -1
    try:
        descriptor = os.open(REPO_ROOT, directory_flags)
        for component in (*root_relative.parts, *parts[:-1]):
            child = os.open(component, directory_flags, dir_fd=descriptor)
            previous = descriptor
            descriptor = child
            try:
                os.close(previous)
            except OSError:
                os.close(child)
                descriptor = -1
                raise
        file_descriptor = os.open(parts[-1], file_flags, dir_fd=descriptor)
        file_info = os.fstat(file_descriptor)
        if not stat.S_ISREG(file_info.st_mode):
            raise CreativeCodePatchGenerationError(f"{label} must be a regular file.")
        if file_info.st_size > max_bytes:
            raise CreativeCodePatchGenerationError(f"{label} exceeds the maximum size.")
        with os.fdopen(file_descriptor, "rb") as handle:
            file_descriptor = -1
            raw_bytes = handle.read(max_bytes + 1)
        if len(raw_bytes) > max_bytes:
            raise CreativeCodePatchGenerationError(f"{label} exceeds the maximum size.")
        payload = json.loads(
            raw_bytes.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_json_object_keys,
        )
    except CreativeCodePatchGenerationError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, NotImplementedError) as exc:
        raise CreativeCodePatchGenerationError(f"unable to read {label} safely.") from exc
    finally:
        active_error = sys.exc_info()[1]
        close_error: OSError | None = None
        for active_descriptor in (file_descriptor, descriptor):
            if active_descriptor >= 0:
                try:
                    os.close(active_descriptor)
                except OSError as exc:
                    if close_error is None:
                        close_error = exc
        if active_error is None and close_error is not None:
            raise CreativeCodePatchGenerationError(
                f"{label} descriptor cleanup failed."
            ) from close_error
    if not isinstance(payload, dict):
        raise CreativeCodePatchGenerationError(f"{label} must be a JSON object.")
    return payload


def _read_pinned_dispatch_json_object(path: Path) -> dict[str, Any]:
    """Read a trusted dispatch result through a no-follow, root-relative descriptor."""

    result_root = REPO_ROOT / "artifacts" / "orchestration" / "experiments" / "results"
    try:
        path.relative_to(result_root)
    except ValueError as exc:
        raise CreativeCodePatchGenerationError(
            "trusted dispatch result must stay under experiment results."
        ) from exc
    return _read_pinned_json_object(
        path,
        trusted_root=result_root,
        label="trusted dispatch result",
        max_bytes=TRUSTED_DISPATCH_RESULT_MAX_BYTES,
    )


def _write_json_new(path: Path, payload: Mapping[str, Any]) -> None:
    """Publish one JSON artifact without replacing a concurrent writer."""

    temp_path: Path | None = None
    temp_fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as temp_file:
            json.dump(dict(payload), temp_file, sort_keys=True, indent=2)
            temp_file.write("\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
        try:
            os.link(temp_path, path, follow_symlinks=False)
        except FileExistsError as exc:
            raise CreativeCodePatchGenerationError("output artifact already exists.") from exc
        except OSError as exc:
            raise CreativeCodePatchGenerationError(
                "output artifact could not be published without replacement."
            ) from exc
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass


@contextmanager
def _exclusive_finalize_lock(run_dir: Path) -> Iterator[None]:
    """Serialize cooperative finalizers for one generated patch run."""

    try:
        fcntl_module = importlib.import_module("fcntl")
    except ModuleNotFoundError as exc:
        raise CreativeCodePatchGenerationError(
            "trusted dispatch finalization locking is unavailable on this platform."
        ) from exc
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_CLOEXEC", 0)
    lock_fd = -1
    try:
        try:
            lock_fd = os.open(run_dir, flags)
        except OSError as exc:
            raise CreativeCodePatchGenerationError(
                "trusted dispatch finalization lock could not be acquired."
            ) from exc
        try:
            fcntl_module.flock(
                lock_fd,
                fcntl_module.LOCK_EX | fcntl_module.LOCK_NB,
            )
        except BlockingIOError as exc:
            raise CreativeCodePatchGenerationError(
                "trusted dispatch finalization is already in progress."
            ) from exc
        except OSError as exc:
            raise CreativeCodePatchGenerationError(
                "trusted dispatch finalization lock could not be acquired."
            ) from exc
        yield
    finally:
        active_error = sys.exc_info()[1]
        cleanup_error: OSError | None = None
        if lock_fd >= 0:
            try:
                os.close(lock_fd)
            except OSError as exc:
                cleanup_error = exc
        if active_error is None and cleanup_error is not None:
            raise CreativeCodePatchGenerationError(
                "trusted dispatch finalization lock cleanup failed."
            ) from cleanup_error


def _resolve_existing_receipt_ref(ref: str, *, label: str) -> Path:
    path = REPO_ROOT / ref
    _reject_symlink_components(path, label=label)
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise CreativeCodePatchGenerationError(f"{label} must exist.") from exc
    root = (REPO_ROOT / "artifacts" / "orchestration" / "creative_code").resolve(strict=False)
    if not _is_relative_to(resolved, root):
        raise CreativeCodePatchGenerationError(f"{label} must stay under creative-code artifacts.")
    if not resolved.is_file():
        raise CreativeCodePatchGenerationError(f"{label} must be a file.")
    return resolved


def _normalize_id(value: Any, *, label: str) -> str:
    if not isinstance(value, str):
        raise CreativeCodePatchGenerationError(f"{label} must be a string.")
    normalized = value.strip()
    if not normalized or not ID_RE.fullmatch(normalized):
        raise CreativeCodePatchGenerationError(f"{label} must be a safe identifier.")
    return normalized


def _normalize_optional_fingerprint(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    return _normalize_fingerprint(value, label=label)


def _normalize_sha(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise CreativeCodePatchGenerationError(f"{label} must be a 40-char git SHA.")
    return value


def _normalize_fingerprint(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise CreativeCodePatchGenerationError(f"{label} must be a sha256 digest.")
    return value


def _normalize_bool(value: Any, *, expected: bool, label: str) -> bool:
    if not isinstance(value, bool) or value != expected:
        raise CreativeCodePatchGenerationError(f"{label} must be {expected}.")
    return value


def _normalize_int(value: Any, *, min_value: int, max_value: int, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise CreativeCodePatchGenerationError(f"{label} must be an integer.")
    if not min_value <= value <= max_value:
        raise CreativeCodePatchGenerationError(
            f"{label} must be between {min_value} and {max_value}."
        )
    return value


def _require_exact_keys(
    payload: Mapping[str, Any],
    expected_keys: frozenset[str],
    *,
    label: str,
) -> None:
    actual = set(payload)
    missing = sorted(expected_keys - actual)
    extra = sorted(actual - expected_keys)
    if missing:
        raise CreativeCodePatchGenerationError(
            f"{label} is missing required fields: {', '.join(missing)}"
        )
    if extra:
        raise CreativeCodePatchGenerationError(f"{label} has unsupported fields.")


def _normalize_repo_ref(value: Any, *, label: str, required_suffix: str) -> str:
    if not isinstance(value, str):
        raise CreativeCodePatchGenerationError(f"{label} must be a string.")
    text = value.strip()
    if any(ord(character) < 32 or ord(character) == 127 for character in text):
        raise CreativeCodePatchGenerationError(f"{label} must not contain control characters.")
    if not text or text.startswith(("/", "~")) or "\\" in text or SCHEME_RE.match(text):
        raise CreativeCodePatchGenerationError(f"{label} must be a repo-relative artifact ref.")
    path = PurePosixPath(text)
    if not path.parts or "." in path.parts or ".." in path.parts:
        raise CreativeCodePatchGenerationError(f"{label} must not contain traversal segments.")
    ref = path.as_posix()
    if not ref.startswith("artifacts/orchestration/creative_code/"):
        raise CreativeCodePatchGenerationError(f"{label} must stay under creative-code artifacts.")
    if not ref.endswith(required_suffix):
        raise CreativeCodePatchGenerationError(f"{label} must end with {required_suffix}.")
    return ref


def _normalize_optional_json_ref(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    return _normalize_repo_ref(value, label=label, required_suffix=".json")


def _normalize_authority(raw_authority: Any, *, label: str) -> dict[str, bool]:
    if not isinstance(raw_authority, dict):
        raise CreativeCodePatchGenerationError(f"{label} must be a JSON object.")
    expected = default_generation_authority()
    _require_exact_keys(raw_authority, frozenset(expected), label=label)
    normalized: dict[str, bool] = {}
    for key in sorted(expected):
        value = raw_authority.get(key)
        if value is not expected[key]:
            raise CreativeCodePatchGenerationError(f"{label}.{key} must be {expected[key]}.")
        normalized[key] = expected[key]
    return normalized


def _reject_payload_safety(value: Any, *, label: str) -> None:
    if isinstance(value, str):
        if SECRET_RE.search(value) or LEAK_TEXT_RE.search(value):
            raise CreativeCodePatchGenerationError(f"{label} contains unsafe text.")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _reject_payload_safety(item, label=f"{label}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_payload_safety(item, label=f"{label}.{key}")


def _normalize_checks(
    raw_checks: Any,
    *,
    expected_keys: frozenset[str],
    label: str,
) -> dict[str, bool]:
    if not isinstance(raw_checks, dict):
        raise CreativeCodePatchGenerationError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_checks, expected_keys, label=label)
    normalized: dict[str, bool] = {}
    for key in sorted(expected_keys):
        normalized[key] = _normalize_bool(raw_checks[key], expected=True, label=f"{label}.{key}")
    return normalized


def _normalize_budget_limits(raw_budgets: Any) -> dict[str, int]:
    if not isinstance(raw_budgets, dict):
        raise CreativeCodePatchGenerationError("budget_limits must be a JSON object.")
    _require_exact_keys(raw_budgets, BUDGET_LIMIT_KEYS, label="budget_limits")
    return {
        "generation_attempts": _normalize_int(
            raw_budgets["generation_attempts"],
            min_value=1,
            max_value=1,
            label="budget_limits.generation_attempts",
        ),
        "generation_timeout_seconds": _normalize_int(
            raw_budgets["generation_timeout_seconds"],
            min_value=1,
            max_value=600,
            label="budget_limits.generation_timeout_seconds",
        ),
        "evaluation_timeout_seconds": _normalize_int(
            raw_budgets["evaluation_timeout_seconds"],
            min_value=1,
            max_value=600,
            label="budget_limits.evaluation_timeout_seconds",
        ),
        "max_changed_files": _normalize_int(
            raw_budgets["max_changed_files"],
            min_value=1,
            max_value=5,
            label="budget_limits.max_changed_files",
        ),
        "max_diff_lines": _normalize_int(
            raw_budgets["max_diff_lines"],
            min_value=1,
            max_value=800,
            label="budget_limits.max_diff_lines",
        ),
        "max_patch_bytes": _normalize_int(
            raw_budgets["max_patch_bytes"],
            min_value=1,
            max_value=524288,
            label="budget_limits.max_patch_bytes",
        ),
    }


def _set_identity(payload: dict[str, Any], *, id_key: str, asset_type: str) -> None:
    payload[id_key] = "pending"
    payload["idempotency_key"] = "pending"
    fingerprint = fingerprint_payload(
        {key: payload[key] for key in sorted(payload) if key not in {id_key, "idempotency_key"}}
    )
    upstream_ids = (
        str(payload.get("admission_id", "")),
        str(payload.get("request_id", "")),
        str(payload.get("base_commit_sha", "")),
        str(payload.get("run_id", "")),
    )
    payload[id_key] = build_asset_id(
        asset_type=asset_type,
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint,
        upstream_ids=upstream_ids,
    )
    payload["idempotency_key"] = build_idempotency_key(
        asset_type=asset_type,
        rail="control_plane",
        version=SCHEMA_VERSION,
        policy_version=POLICY_VERSION,
        fingerprint=fingerprint,
        upstream_ids=upstream_ids,
    )


def _require_clean_shared_tree() -> None:
    status = shared_tree_status()
    if status.strip():
        raise CreativeCodePatchGenerationError(
            "shared worktree must be clean before creative-code patch generation."
        )


def _candidate_artifact_paths(run_dir: Path) -> tuple[Path, Path, Path, Path]:
    return (
        resolve_run_file(run_dir, creative_code_patch_builder.CANDIDATE_PATCH_FILE),
        resolve_run_file(run_dir, creative_code_patch_builder.PATCH_METADATA_FILE),
        resolve_run_file(run_dir, creative_code_patch_builder.EXPERIMENT_PACKET_FILE),
        resolve_run_file(run_dir, creative_code_patch_builder.RESULT_FILE),
    )


def _require_no_preexisting_candidate_artifacts(run_dir: Path) -> None:
    for path in _candidate_artifact_paths(run_dir):
        if path.exists() or path.is_symlink():
            raise CreativeCodePatchGenerationError(
                f"pre-generation run already contains {path.name}."
            )


def _read_admission_context(
    admission_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    admission, request, bundle, _finalize_receipt, _human_admission = (
        admission_cli._read_admission_with_sources(admission_path)
    )
    normalized_request = validate_creative_code_patch_build_request(request, source_bundle=bundle)
    normalized_bundle = validate_creative_code_specification_bundle(bundle)
    return admission, normalized_request, normalized_bundle


def _read_hints(path: Path | None) -> tuple[str | None, str | None]:
    if path is None:
        return None, None
    hints = validate_coordinator_advisory_hints(
        _read_json_object(path, label="coordinator advisory hints")
    )
    hints_ref = _repo_ref(admission_cli._resolve_repo_json_file(path, label="coordinator hints"))
    return hints_ref, fingerprint_payload(hints)


def _load_prepared_run(
    *,
    admission: Mapping[str, Any],
    request: Mapping[str, Any],
    bundle: Mapping[str, Any],
    run_id: str,
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    builder_prepare = cast(Mapping[str, Any], admission["builder_prepare"])
    if builder_prepare["prepared"] is not True:
        raise CreativeCodePatchGenerationError("admission must be prepared before generation.")
    if builder_prepare["run_id"] != run_id:
        raise CreativeCodePatchGenerationError("run_id does not match prepared admission.")
    run_dir = resolve_run_dir(run_id, create=False)
    state = read_json(resolve_run_file(run_dir, creative_code_patch_builder.STATE_FILE))
    run_request = read_json(resolve_run_file(run_dir, creative_code_patch_builder.REQUEST_FILE))
    run_bundle = read_json(
        resolve_run_file(run_dir, creative_code_patch_builder.SOURCE_BUNDLE_FILE)
    )
    selected_variant = read_json(
        resolve_run_file(run_dir, creative_code_patch_builder.SELECTED_VARIANT_FILE)
    )
    if (
        not isinstance(state, dict)
        or not isinstance(run_request, dict)
        or not isinstance(run_bundle, dict)
        or not isinstance(selected_variant, dict)
    ):
        raise CreativeCodePatchGenerationError("prepared run artifacts must be JSON objects.")
    normalized_run_request = validate_creative_code_patch_build_request(
        run_request,
        source_bundle=run_bundle,
    )
    normalized_run_bundle = validate_creative_code_specification_bundle(run_bundle)
    if normalized_run_request != request:
        raise CreativeCodePatchGenerationError("prepared run request does not match admission.")
    if normalized_run_bundle != bundle:
        raise CreativeCodePatchGenerationError(
            "prepared run source bundle does not match admission."
        )
    expected_state = {
        "run_id": run_id,
        "request_id": request["request_id"],
        "source_bundle_id": request["source_bundle_id"],
        "selected_variant_id": request["selected_variant_id"],
        "base_commit_sha": request["base_commit_sha"],
    }
    for key, expected in expected_state.items():
        if state.get(key) != expected:
            raise CreativeCodePatchGenerationError(f"prepared run state {key} does not match.")
    if state.get("candidate_patch_generated") is not False:
        raise CreativeCodePatchGenerationError("prepared run already generated candidate patch.")
    if state.get("candidate_patch_evaluated") is not False:
        raise CreativeCodePatchGenerationError("prepared run already evaluated candidate patch.")
    if builder_prepare["state_fingerprint"] != fingerprint_payload(state):
        raise CreativeCodePatchGenerationError("prepared run state fingerprint does not match.")
    if selected_variant.get("variant_id") != request["selected_variant_id"]:
        raise CreativeCodePatchGenerationError("selected variant id does not match request.")
    if selected_variant.get("variant_fingerprint") != request["selected_variant_fingerprint"]:
        raise CreativeCodePatchGenerationError(
            "selected variant fingerprint does not match request."
        )
    for filename in (
        creative_code_patch_builder.REQUEST_FILE,
        creative_code_patch_builder.SOURCE_BUNDLE_FILE,
        creative_code_patch_builder.SELECTED_VARIANT_FILE,
        creative_code_patch_builder.STATE_FILE,
    ):
        if not resolve_run_file(run_dir, filename).is_file():
            raise CreativeCodePatchGenerationError(f"prepared run is missing {filename}.")
    _require_no_preexisting_candidate_artifacts(run_dir)
    return run_dir, state, selected_variant


def build_generation_gate(
    *,
    admission_path: Path,
    run_id: str,
    coordinator_advisory_hints_path: Path | None = None,
) -> dict[str, Any]:
    """Build the fail-closed local gate required before candidate generation."""

    admission_path = admission_cli._resolve_repo_json_file(
        admission_path, label="creative spec patch admission"
    )
    admission, request, bundle = _read_admission_context(admission_path)
    verify_origin_main_base(request["base_commit_sha"])
    _require_clean_shared_tree()
    run_dir, state, _selected_variant = _load_prepared_run(
        admission=admission,
        request=request,
        bundle=bundle,
        run_id=run_id,
    )
    hints_ref, hints_fingerprint = _read_hints(coordinator_advisory_hints_path)
    allowed_paths = sorted(
        set(request["allowed_existing_paths"]) | set(request["allowed_new_paths"])
    )
    checks = {key: True for key in sorted(GATE_CHECK_KEYS)}
    gate: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": GATE_ARTIFACT_TYPE,
        "policy_version": POLICY_VERSION,
        "gate_id": "pending",
        "idempotency_key": "pending",
        "admission_id": admission["admission_id"],
        "admission_fingerprint": fingerprint_payload(admission),
        "admission_ref": _repo_ref(admission_path),
        "request_id": request["request_id"],
        "request_fingerprint": fingerprint_payload(request),
        "request_ref": admission["patch_request"]["request_ref"],
        "source_bundle_id": request["source_bundle_id"],
        "source_bundle_fingerprint": request["source_bundle_fingerprint"],
        "source_bundle_ref": admission["patch_request"]["source_bundle_ref"],
        "selected_variant_id": request["selected_variant_id"],
        "selected_variant_fingerprint": request["selected_variant_fingerprint"],
        "base_commit_sha": request["base_commit_sha"],
        "run_id": run_id,
        "state_fingerprint": fingerprint_payload(state),
        "budget_limits": dict(request["budgets"]),
        "allowed_paths_fingerprint": fingerprint_payload({"allowed_paths": allowed_paths}),
        "oracle_commands_fingerprint": fingerprint_payload(
            {"oracle_commands": request["oracle_commands"]}
        ),
        "metrics_fingerprint": fingerprint_payload({"metrics": request["metrics"]}),
        "immutable_oracles_fingerprint": fingerprint_payload(
            {"immutable_oracles": bundle["immutable_oracles"]}
        ),
        "oracle_command_count": len(request["oracle_commands"]),
        "metric_count": len(request["metrics"]),
        "immutable_oracle_count": len(bundle["immutable_oracles"]),
        "coordinator_advisory_hints_ref": hints_ref,
        "coordinator_advisory_hints_fingerprint": hints_fingerprint,
        "checks": checks,
        "passed_checks": len(checks),
        "total_checks": len(checks),
        "next_action": "generate_candidate_then_evaluate_candidate",
        "authority": default_generation_authority(),
        "sanitized": True,
    }
    # Resolve containment for static analyzers and ensure run_dir is under patch artifacts.
    resolve_run_dir(run_dir.name, create=False)
    _set_identity(gate, id_key="gate_id", asset_type=GATE_ARTIFACT_TYPE)
    return validate_generation_gate(gate)


def validate_generation_gate(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate sanitized pre-generation gate metadata."""

    label = "CreativeCodePatchGenerationGate"
    _require_exact_keys(payload, GATE_KEYS, label=label)
    checks = _normalize_checks(
        payload["checks"], expected_keys=GATE_CHECK_KEYS, label=f"{label}.checks"
    )
    budget_limits = _normalize_budget_limits(payload["budget_limits"])
    normalized = {
        "schema_version": _normalize_const(
            payload.get("schema_version"), SCHEMA_VERSION, label=f"{label}.schema_version"
        ),
        "artifact_type": _normalize_const(
            payload.get("artifact_type"), GATE_ARTIFACT_TYPE, label=f"{label}.artifact_type"
        ),
        "policy_version": _normalize_const(
            payload.get("policy_version"), POLICY_VERSION, label=f"{label}.policy_version"
        ),
        "gate_id": _normalize_id(payload.get("gate_id"), label=f"{label}.gate_id"),
        "idempotency_key": _normalize_id(
            payload.get("idempotency_key"), label=f"{label}.idempotency_key"
        ),
        "admission_id": _normalize_id(payload.get("admission_id"), label=f"{label}.admission_id"),
        "admission_fingerprint": _normalize_fingerprint(
            payload.get("admission_fingerprint"), label=f"{label}.admission_fingerprint"
        ),
        "admission_ref": _normalize_repo_ref(
            payload.get("admission_ref"), label=f"{label}.admission_ref", required_suffix=".json"
        ),
        "request_id": _normalize_id(payload.get("request_id"), label=f"{label}.request_id"),
        "request_fingerprint": _normalize_fingerprint(
            payload.get("request_fingerprint"), label=f"{label}.request_fingerprint"
        ),
        "request_ref": _normalize_repo_ref(
            payload.get("request_ref"), label=f"{label}.request_ref", required_suffix=".json"
        ),
        "source_bundle_id": _normalize_id(
            payload.get("source_bundle_id"), label=f"{label}.source_bundle_id"
        ),
        "source_bundle_fingerprint": _normalize_fingerprint(
            payload.get("source_bundle_fingerprint"), label=f"{label}.source_bundle_fingerprint"
        ),
        "source_bundle_ref": _normalize_repo_ref(
            payload.get("source_bundle_ref"),
            label=f"{label}.source_bundle_ref",
            required_suffix=".json",
        ),
        "selected_variant_id": _normalize_id(
            payload.get("selected_variant_id"), label=f"{label}.selected_variant_id"
        ),
        "selected_variant_fingerprint": _normalize_fingerprint(
            payload.get("selected_variant_fingerprint"),
            label=f"{label}.selected_variant_fingerprint",
        ),
        "base_commit_sha": _normalize_sha(
            payload.get("base_commit_sha"), label=f"{label}.base_commit_sha"
        ),
        "run_id": _normalize_id(payload.get("run_id"), label=f"{label}.run_id"),
        "state_fingerprint": _normalize_fingerprint(
            payload.get("state_fingerprint"), label=f"{label}.state_fingerprint"
        ),
        "budget_limits": budget_limits,
        "allowed_paths_fingerprint": _normalize_fingerprint(
            payload.get("allowed_paths_fingerprint"), label=f"{label}.allowed_paths_fingerprint"
        ),
        "oracle_commands_fingerprint": _normalize_fingerprint(
            payload.get("oracle_commands_fingerprint"),
            label=f"{label}.oracle_commands_fingerprint",
        ),
        "metrics_fingerprint": _normalize_fingerprint(
            payload.get("metrics_fingerprint"), label=f"{label}.metrics_fingerprint"
        ),
        "immutable_oracles_fingerprint": _normalize_fingerprint(
            payload.get("immutable_oracles_fingerprint"),
            label=f"{label}.immutable_oracles_fingerprint",
        ),
        "oracle_command_count": _normalize_int(
            payload.get("oracle_command_count"),
            min_value=1,
            max_value=20,
            label=f"{label}.oracle_command_count",
        ),
        "metric_count": _normalize_int(
            payload.get("metric_count"),
            min_value=1,
            max_value=20,
            label=f"{label}.metric_count",
        ),
        "immutable_oracle_count": _normalize_int(
            payload.get("immutable_oracle_count"),
            min_value=1,
            max_value=20,
            label=f"{label}.immutable_oracle_count",
        ),
        "coordinator_advisory_hints_ref": _normalize_optional_json_ref(
            payload.get("coordinator_advisory_hints_ref"),
            label=f"{label}.coordinator_advisory_hints_ref",
        ),
        "coordinator_advisory_hints_fingerprint": _normalize_optional_fingerprint(
            payload.get("coordinator_advisory_hints_fingerprint"),
            label=f"{label}.coordinator_advisory_hints_fingerprint",
        ),
        "checks": checks,
        "passed_checks": _normalize_int(
            payload.get("passed_checks"),
            min_value=len(GATE_CHECK_KEYS),
            max_value=len(GATE_CHECK_KEYS),
            label=f"{label}.passed_checks",
        ),
        "total_checks": _normalize_int(
            payload.get("total_checks"),
            min_value=len(GATE_CHECK_KEYS),
            max_value=len(GATE_CHECK_KEYS),
            label=f"{label}.total_checks",
        ),
        "next_action": _normalize_const(
            payload.get("next_action"),
            "generate_candidate_then_evaluate_candidate",
            label=f"{label}.next_action",
        ),
        "authority": _normalize_authority(payload.get("authority"), label=f"{label}.authority"),
        "sanitized": _normalize_bool(
            payload.get("sanitized"), expected=True, label=f"{label}.sanitized"
        ),
    }
    if bool(normalized["coordinator_advisory_hints_ref"]) != bool(
        normalized["coordinator_advisory_hints_fingerprint"]
    ):
        raise CreativeCodePatchGenerationError(
            "coordinator advisory hints ref/fingerprint must both be present or both be null."
        )
    _reject_payload_safety(normalized, label=label)
    expected = dict(normalized)
    _set_identity(expected, id_key="gate_id", asset_type=GATE_ARTIFACT_TYPE)
    if normalized["gate_id"] != expected["gate_id"]:
        raise CreativeCodePatchGenerationError("gate_id does not match generation gate content.")
    if normalized["idempotency_key"] != expected["idempotency_key"]:
        raise CreativeCodePatchGenerationError(
            "idempotency_key does not match generation gate content."
        )
    return normalized


def _normalize_const(value: Any, expected: str, *, label: str) -> str:
    if value != expected:
        raise CreativeCodePatchGenerationError(f"{label} must equal {expected!r}.")
    return expected


def _validate_gate_context(gate_path: Path) -> tuple[Path, dict[str, Any]]:
    resolved_gate = admission_cli._resolve_repo_json_file(gate_path, label="generation gate")
    gate = validate_generation_gate(_read_json_object(resolved_gate, label="generation gate"))
    expected_gate = build_generation_gate(
        admission_path=REPO_ROOT / gate["admission_ref"],
        run_id=gate["run_id"],
        coordinator_advisory_hints_path=(
            REPO_ROOT / gate["coordinator_advisory_hints_ref"]
            if gate["coordinator_advisory_hints_ref"]
            else None
        ),
    )
    if expected_gate != gate:
        raise CreativeCodePatchGenerationError("generation gate is stale.")
    return resolved_gate, gate


def _require_base_and_tree_for_step(base_commit_sha: str) -> None:
    verify_origin_main_base(base_commit_sha)
    _require_clean_shared_tree()


def _build_receipt(
    *,
    gate_path: Path,
    gate: Mapping[str, Any],
    result: Mapping[str, Any],
    require_result_file: bool = True,
) -> dict[str, Any]:
    run_dir = resolve_run_dir(str(gate["run_id"]), create=False)
    candidate_patch, patch_metadata, experiment_packet, result_path = _candidate_artifact_paths(
        run_dir
    )
    required_artifacts = [candidate_patch, patch_metadata, experiment_packet]
    if require_result_file:
        required_artifacts.append(result_path)
    for artifact in required_artifacts:
        if not artifact.exists() or not artifact.is_file():
            raise CreativeCodePatchGenerationError(f"missing generated artifact: {artifact.name}")
    source_bundle = validate_creative_code_specification_bundle(
        read_json(resolve_run_file(run_dir, creative_code_patch_builder.SOURCE_BUNDLE_FILE))
    )
    request = validate_creative_code_patch_build_request(
        read_creative_code_patch_build_request(
            str(resolve_run_file(run_dir, creative_code_patch_builder.REQUEST_FILE))
        ),
        source_bundle=source_bundle,
    )
    metadata = _normalize_patch_metadata(read_json(patch_metadata), label="patch metadata")
    experiment_packet_payload = _read_experiment_packet(experiment_packet)
    _validate_experiment_packet_matches_result(
        experiment_packet_payload=experiment_packet_payload,
        request=request,
        source_bundle=source_bundle,
        result=result,
    )
    expected_patch_summary = {
        "patch_fingerprint": result["patch_summary"]["patch_fingerprint"],
        "patch_bytes": result["patch_summary"]["patch_bytes"],
        "diff_lines": result["patch_summary"]["diff_lines"],
    }
    for key, expected in expected_patch_summary.items():
        if metadata.get(key) != expected:
            raise CreativeCodePatchGenerationError("patch metadata does not match result summary.")
    if sorted(metadata.get("changed_paths", [])) != sorted(result["changed_paths"]):
        raise CreativeCodePatchGenerationError("patch metadata changed paths do not match result.")
    checks = {key: True for key in sorted(RECEIPT_CHECK_KEYS)}
    receipt: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": RECEIPT_ARTIFACT_TYPE,
        "policy_version": POLICY_VERSION,
        "receipt_id": "pending",
        "idempotency_key": "pending",
        "gate_id": gate["gate_id"],
        "gate_fingerprint": fingerprint_payload(dict(gate)),
        "gate_ref": _repo_ref(gate_path),
        "admission_id": gate["admission_id"],
        "admission_fingerprint": gate["admission_fingerprint"],
        "admission_ref": gate["admission_ref"],
        "request_id": gate["request_id"],
        "request_fingerprint": gate["request_fingerprint"],
        "request_ref": gate["request_ref"],
        "source_bundle_id": gate["source_bundle_id"],
        "source_bundle_fingerprint": gate["source_bundle_fingerprint"],
        "source_bundle_ref": gate["source_bundle_ref"],
        "selected_variant_id": gate["selected_variant_id"],
        "selected_variant_fingerprint": gate["selected_variant_fingerprint"],
        "base_commit_sha": gate["base_commit_sha"],
        "run_id": gate["run_id"],
        "candidate_patch_ref": _repo_ref(candidate_patch),
        "patch_metadata_ref": _repo_ref(patch_metadata),
        "patch_metadata_fingerprint": fingerprint_payload(metadata),
        "experiment_packet_ref": _repo_ref(experiment_packet),
        "experiment_packet_fingerprint": fingerprint_payload(experiment_packet_payload),
        "result_ref": _repo_ref(result_path),
        "result_id": result["result_id"],
        "result_fingerprint": fingerprint_payload(dict(result)),
        "status": result["status"],
        "failure_class": result["failure_class"],
        "changed_paths": list(result["changed_paths"]),
        "patch_summary": dict(result["patch_summary"]),
        "workspace_summary": dict(result["workspace_summary"]),
        "runner_summary": dict(result["runner_summary"]),
        "promotion_ready": result["promotion_ready"],
        "checks": checks,
        "passed_checks": len(checks),
        "total_checks": len(checks),
        "authority": default_generation_authority(),
        "sanitized": True,
    }
    _set_identity(receipt, id_key="receipt_id", asset_type=RECEIPT_ARTIFACT_TYPE)
    return validate_generation_receipt(receipt)


def validate_generation_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate sanitized generation/evaluation receipt metadata."""

    label = "CreativeCodePatchGenerationReceipt"
    _require_exact_keys(payload, RECEIPT_KEYS, label=label)
    checks = _normalize_checks(
        payload["checks"],
        expected_keys=RECEIPT_CHECK_KEYS,
        label=f"{label}.checks",
    )
    patch_summary = _normalize_patch_summary(payload["patch_summary"])
    workspace_summary = _normalize_workspace_summary(payload["workspace_summary"])
    runner_summary = _normalize_runner_summary(payload["runner_summary"])
    normalized = {
        "schema_version": _normalize_const(
            payload.get("schema_version"), SCHEMA_VERSION, label=f"{label}.schema_version"
        ),
        "artifact_type": _normalize_const(
            payload.get("artifact_type"), RECEIPT_ARTIFACT_TYPE, label=f"{label}.artifact_type"
        ),
        "policy_version": _normalize_const(
            payload.get("policy_version"), POLICY_VERSION, label=f"{label}.policy_version"
        ),
        "receipt_id": _normalize_id(payload.get("receipt_id"), label=f"{label}.receipt_id"),
        "idempotency_key": _normalize_id(
            payload.get("idempotency_key"), label=f"{label}.idempotency_key"
        ),
        "gate_id": _normalize_id(payload.get("gate_id"), label=f"{label}.gate_id"),
        "gate_fingerprint": _normalize_fingerprint(
            payload.get("gate_fingerprint"), label=f"{label}.gate_fingerprint"
        ),
        "gate_ref": _normalize_repo_ref(
            payload.get("gate_ref"), label=f"{label}.gate_ref", required_suffix=".json"
        ),
        "admission_id": _normalize_id(payload.get("admission_id"), label=f"{label}.admission_id"),
        "admission_fingerprint": _normalize_fingerprint(
            payload.get("admission_fingerprint"), label=f"{label}.admission_fingerprint"
        ),
        "admission_ref": _normalize_repo_ref(
            payload.get("admission_ref"), label=f"{label}.admission_ref", required_suffix=".json"
        ),
        "request_id": _normalize_id(payload.get("request_id"), label=f"{label}.request_id"),
        "request_fingerprint": _normalize_fingerprint(
            payload.get("request_fingerprint"), label=f"{label}.request_fingerprint"
        ),
        "request_ref": _normalize_repo_ref(
            payload.get("request_ref"), label=f"{label}.request_ref", required_suffix=".json"
        ),
        "source_bundle_id": _normalize_id(
            payload.get("source_bundle_id"), label=f"{label}.source_bundle_id"
        ),
        "source_bundle_fingerprint": _normalize_fingerprint(
            payload.get("source_bundle_fingerprint"), label=f"{label}.source_bundle_fingerprint"
        ),
        "source_bundle_ref": _normalize_repo_ref(
            payload.get("source_bundle_ref"),
            label=f"{label}.source_bundle_ref",
            required_suffix=".json",
        ),
        "selected_variant_id": _normalize_id(
            payload.get("selected_variant_id"), label=f"{label}.selected_variant_id"
        ),
        "selected_variant_fingerprint": _normalize_fingerprint(
            payload.get("selected_variant_fingerprint"),
            label=f"{label}.selected_variant_fingerprint",
        ),
        "base_commit_sha": _normalize_sha(
            payload.get("base_commit_sha"), label=f"{label}.base_commit_sha"
        ),
        "run_id": _normalize_id(payload.get("run_id"), label=f"{label}.run_id"),
        "candidate_patch_ref": _normalize_repo_ref(
            payload.get("candidate_patch_ref"),
            label=f"{label}.candidate_patch_ref",
            required_suffix=".patch",
        ),
        "patch_metadata_ref": _normalize_repo_ref(
            payload.get("patch_metadata_ref"),
            label=f"{label}.patch_metadata_ref",
            required_suffix=".json",
        ),
        "patch_metadata_fingerprint": _normalize_fingerprint(
            payload.get("patch_metadata_fingerprint"),
            label=f"{label}.patch_metadata_fingerprint",
        ),
        "experiment_packet_ref": _normalize_repo_ref(
            payload.get("experiment_packet_ref"),
            label=f"{label}.experiment_packet_ref",
            required_suffix=".json",
        ),
        "experiment_packet_fingerprint": _normalize_fingerprint(
            payload.get("experiment_packet_fingerprint"),
            label=f"{label}.experiment_packet_fingerprint",
        ),
        "result_ref": _normalize_repo_ref(
            payload.get("result_ref"), label=f"{label}.result_ref", required_suffix=".json"
        ),
        "result_id": _normalize_id(payload.get("result_id"), label=f"{label}.result_id"),
        "result_fingerprint": _normalize_fingerprint(
            payload.get("result_fingerprint"), label=f"{label}.result_fingerprint"
        ),
        "status": _normalize_status(payload.get("status")),
        "failure_class": payload.get("failure_class"),
        "changed_paths": _normalize_path_list(
            payload.get("changed_paths"), label=f"{label}.changed_paths"
        ),
        "patch_summary": patch_summary,
        "workspace_summary": workspace_summary,
        "runner_summary": runner_summary,
        "promotion_ready": _normalize_bool(
            payload.get("promotion_ready"), expected=False, label=f"{label}.promotion_ready"
        ),
        "checks": checks,
        "passed_checks": _normalize_int(
            payload.get("passed_checks"),
            min_value=len(RECEIPT_CHECK_KEYS),
            max_value=len(RECEIPT_CHECK_KEYS),
            label=f"{label}.passed_checks",
        ),
        "total_checks": _normalize_int(
            payload.get("total_checks"),
            min_value=len(RECEIPT_CHECK_KEYS),
            max_value=len(RECEIPT_CHECK_KEYS),
            label=f"{label}.total_checks",
        ),
        "authority": _normalize_authority(payload.get("authority"), label=f"{label}.authority"),
        "sanitized": _normalize_bool(
            payload.get("sanitized"), expected=True, label=f"{label}.sanitized"
        ),
    }
    failure_class = normalized["failure_class"]
    if failure_class is not None and (
        not isinstance(failure_class, str) or failure_class not in FAILURE_CLASSES
    ):
        raise CreativeCodePatchGenerationError("receipt failure_class is unsupported.")
    coherence_violation = classify_terminal_outcome_coherence(
        status=cast(str, normalized["status"]),
        failure_class=failure_class,
        runner_status=runner_summary["status"],
        runner_failure_class=runner_summary["failure_class"],
        runner_oracle_commands_configured=runner_summary["oracle_commands_configured"],
        runner_oracle_commands_executed=runner_summary["oracle_commands_executed"],
        runner_shared_tree_untouched=runner_summary["shared_tree_untouched"],
        workspace_summary=workspace_summary,
    )
    if coherence_violation == "accepted_with_failure_class":
        raise CreativeCodePatchGenerationError("accepted receipt must not have failure_class.")
    if coherence_violation == "rejected_without_failure_class":
        raise CreativeCodePatchGenerationError("rejected receipt requires failure_class.")
    if coherence_violation == "accepted_with_nonaccepted_runner":
        raise CreativeCodePatchGenerationError(
            "accepted receipt requires an accepted runner summary."
        )
    if coherence_violation == "accepted_without_runner_proof":
        raise CreativeCodePatchGenerationError(
            "accepted receipt requires complete runner oracle and shared-tree proof."
        )
    if coherence_violation == "accepted_without_workspace_proof":
        raise CreativeCodePatchGenerationError("accepted receipt requires full workspace proof.")
    if coherence_violation == "rejected_capability_without_runner_proof":
        raise CreativeCodePatchGenerationError(
            "capability_mismatch receipts require a rejected runner summary."
        )
    if coherence_violation == "rejected_failure_mismatch":
        raise CreativeCodePatchGenerationError(
            "rejected receipt and runner summary failure_class values must match."
        )
    for observed_failure, failure_label in (
        (failure_class, "CreativeCodePatchGenerationReceipt.runner_summary"),
        (runner_summary["failure_class"], "runner_summary"),
    ):
        try:
            validate_failure_retry_observations(
                failure_class=observed_failure,
                attempts=runner_summary["attempts"],
                retries_consumed=runner_summary["retries_consumed"],
                label=failure_label,
            )
        except ValueError as exc:
            raise CreativeCodePatchGenerationError(str(exc)) from exc
    try:
        validate_capability_zero_attempt_observations(
            failure_class=runner_summary["failure_class"],
            attempts=runner_summary["attempts"],
            mutated_path_count=runner_summary["mutated_path_count"],
            oracle_commands_executed=runner_summary["oracle_commands_executed"],
            label="runner_summary",
        )
    except ValueError as exc:
        raise CreativeCodePatchGenerationError(str(exc)) from exc
    if workspace_summary["detached_base_sha"] != normalized["base_commit_sha"]:
        raise CreativeCodePatchGenerationError(
            "workspace_summary.detached_base_sha must match base_commit_sha."
        )
    _reject_payload_safety(normalized, label=label)
    expected = dict(normalized)
    _set_identity(expected, id_key="receipt_id", asset_type=RECEIPT_ARTIFACT_TYPE)
    if normalized["receipt_id"] != expected["receipt_id"]:
        raise CreativeCodePatchGenerationError("receipt_id does not match receipt content.")
    if normalized["idempotency_key"] != expected["idempotency_key"]:
        raise CreativeCodePatchGenerationError("idempotency_key does not match receipt content.")
    return normalized


def _normalize_status(value: Any) -> str:
    if value not in {"accepted", "rejected"}:
        raise CreativeCodePatchGenerationError("receipt status must be accepted or rejected.")
    return cast(str, value)


def _normalize_path_list(value: Any, *, label: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise CreativeCodePatchGenerationError(f"{label} must be a non-empty array.")
    normalized: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        path = _normalize_patch_path(item, label=f"{label}[{index}]")
        if path in seen:
            raise CreativeCodePatchGenerationError(f"{label} must not contain duplicates.")
        seen.add(path)
        normalized.append(path)
    return normalized


def _normalize_patch_path(value: Any, *, label: str) -> str:
    if not isinstance(value, str):
        raise CreativeCodePatchGenerationError(f"{label} must be a string.")
    text = value.strip()
    if not text or text.startswith(("/", "~")) or "\\" in text or SCHEME_RE.match(text):
        raise CreativeCodePatchGenerationError(f"{label} must be a repo-relative path.")
    path = PurePosixPath(text)
    if not path.parts or "." in path.parts or ".." in path.parts:
        raise CreativeCodePatchGenerationError(f"{label} must not contain traversal segments.")
    return path.as_posix()


def _normalize_patch_summary(raw_summary: Any) -> dict[str, Any]:
    if not isinstance(raw_summary, dict):
        raise CreativeCodePatchGenerationError("patch_summary must be a JSON object.")
    _require_exact_keys(raw_summary, PATCH_SUMMARY_KEYS, label="patch_summary")
    return {
        "patch_fingerprint": _normalize_fingerprint(
            raw_summary["patch_fingerprint"], label="patch_summary.patch_fingerprint"
        ),
        "patch_bytes": _normalize_int(
            raw_summary["patch_bytes"],
            min_value=1,
            max_value=524288,
            label="patch_summary.patch_bytes",
        ),
        "diff_lines": _normalize_int(
            raw_summary["diff_lines"],
            min_value=1,
            max_value=800,
            label="patch_summary.diff_lines",
        ),
    }


def _normalize_patch_metadata(raw_metadata: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(raw_metadata, dict):
        raise CreativeCodePatchGenerationError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_metadata, PATCH_METADATA_KEYS, label=label)
    changed_paths = _normalize_path_list(
        raw_metadata["changed_paths"], label=f"{label}.changed_paths"
    )
    raw_statuses = raw_metadata["changed_path_statuses"]
    if not isinstance(raw_statuses, dict):
        raise CreativeCodePatchGenerationError(f"{label}.changed_path_statuses must be an object.")
    if set(raw_statuses) != set(changed_paths):
        raise CreativeCodePatchGenerationError(
            f"{label}.changed_path_statuses must match changed_paths."
        )
    changed_path_statuses: dict[str, str] = {}
    for path in changed_paths:
        status = raw_statuses[path]
        if status not in {"A", "M"}:
            raise CreativeCodePatchGenerationError(
                f"{label}.changed_path_statuses values must be A or M."
            )
        changed_path_statuses[path] = status
    normalized = {
        "changed_paths": changed_paths,
        "changed_path_statuses": changed_path_statuses,
        "patch_fingerprint": _normalize_fingerprint(
            raw_metadata["patch_fingerprint"], label=f"{label}.patch_fingerprint"
        ),
        "patch_bytes": _normalize_int(
            raw_metadata["patch_bytes"],
            min_value=1,
            max_value=524288,
            label=f"{label}.patch_bytes",
        ),
        "diff_lines": _normalize_int(
            raw_metadata["diff_lines"],
            min_value=1,
            max_value=800,
            label=f"{label}.diff_lines",
        ),
    }
    _reject_payload_safety(normalized, label=label)
    return normalized


def _normalize_workspace_summary(raw_summary: Any) -> dict[str, Any]:
    if not isinstance(raw_summary, dict):
        raise CreativeCodePatchGenerationError("workspace_summary must be a JSON object.")
    _require_exact_keys(raw_summary, WORKSPACE_SUMMARY_KEYS, label="workspace_summary")
    return {
        "detached_base_sha": _normalize_sha(
            raw_summary["detached_base_sha"], label="workspace_summary.detached_base_sha"
        ),
        "origin_removed": _normalize_any_bool(
            raw_summary["origin_removed"], label="workspace_summary.origin_removed"
        ),
        "checkout_destroyed": _normalize_any_bool(
            raw_summary["checkout_destroyed"], label="workspace_summary.checkout_destroyed"
        ),
        "shared_tree_untouched": _normalize_any_bool(
            raw_summary["shared_tree_untouched"], label="workspace_summary.shared_tree_untouched"
        ),
    }


def _normalize_runner_summary(raw_summary: Any) -> dict[str, Any]:
    if not isinstance(raw_summary, dict):
        raise CreativeCodePatchGenerationError("runner_summary must be a JSON object.")
    _require_exact_keys(raw_summary, RUNNER_SUMMARY_KEYS, label="runner_summary")
    failure_class = raw_summary["failure_class"]
    if failure_class is not None and not isinstance(failure_class, str):
        raise CreativeCodePatchGenerationError(
            "runner_summary.failure_class must be null or string."
        )
    if failure_class is not None and failure_class not in FAILURE_CLASSES:
        raise CreativeCodePatchGenerationError("runner_summary.failure_class is unsupported.")
    status = _normalize_status(raw_summary["status"])
    coherence_violation = classify_failure_class_coherence(
        status=status,
        failure_class=failure_class,
    )
    if coherence_violation == "accepted_with_failure_class":
        raise CreativeCodePatchGenerationError(
            "accepted runner summaries must not have failure_class."
        )
    if coherence_violation == "rejected_without_failure_class":
        raise CreativeCodePatchGenerationError("rejected runner summaries require failure_class.")
    error_fingerprint = raw_summary["runner_error_fingerprint"]
    if error_fingerprint is not None:
        error_fingerprint = _normalize_fingerprint(
            error_fingerprint,
            label="runner_summary.runner_error_fingerprint",
        )
    attempts = _normalize_int(
        raw_summary["attempts"], min_value=0, max_value=3, label="runner_summary.attempts"
    )
    retries_consumed = _normalize_int(
        raw_summary["retries_consumed"],
        min_value=0,
        max_value=2,
        label="runner_summary.retries_consumed",
    )
    return {
        "experiment_id": _normalize_id(
            raw_summary["experiment_id"], label="runner_summary.experiment_id"
        ),
        "status": status,
        "failure_class": failure_class,
        "mutated_path_count": _normalize_int(
            raw_summary["mutated_path_count"],
            min_value=0,
            max_value=5,
            label="runner_summary.mutated_path_count",
        ),
        "oracle_commands_configured": _normalize_int(
            raw_summary["oracle_commands_configured"],
            min_value=0,
            max_value=20,
            label="runner_summary.oracle_commands_configured",
        ),
        "oracle_commands_executed": _normalize_int(
            raw_summary["oracle_commands_executed"],
            min_value=0,
            max_value=20,
            label="runner_summary.oracle_commands_executed",
        ),
        "attempts": attempts,
        "retries_consumed": retries_consumed,
        "shared_tree_untouched": _normalize_any_bool(
            raw_summary["shared_tree_untouched"], label="runner_summary.shared_tree_untouched"
        ),
        "runner_result_fingerprint": _normalize_fingerprint(
            raw_summary["runner_result_fingerprint"],
            label="runner_summary.runner_result_fingerprint",
        ),
        "runner_error_present": _normalize_any_bool(
            raw_summary["runner_error_present"], label="runner_summary.runner_error_present"
        ),
        "runner_error_fingerprint": error_fingerprint,
    }


def _normalize_any_bool(value: Any, *, label: str) -> bool:
    if not isinstance(value, bool):
        raise CreativeCodePatchGenerationError(f"{label} must be a boolean.")
    return value


def _validate_result_matches_gate(result: Mapping[str, Any], gate: Mapping[str, Any]) -> None:
    for key in (
        "request_id",
        "source_bundle_id",
        "source_bundle_fingerprint",
        "selected_variant_id",
        "selected_variant_fingerprint",
        "base_commit_sha",
    ):
        if result[key] != gate[key]:
            raise CreativeCodePatchGenerationError(f"result {key} does not match generation gate.")


def _expected_experiment_budgets(request: Mapping[str, Any]) -> dict[str, int | str]:
    """Return the PR-2 evaluation budget envelope derived from the build request."""

    return {
        **validate_budget_payload(
            creative_code_patch_builder.build_pr2_experiment_budget_overrides(request)
        ),
        "stop_condition": DEFAULT_STOP_CONDITION,
    }


REPLAY_VOLATILE_EXPERIMENT_PACKET_FIELDS = frozenset(
    {
        "recommended_agents",
        "routing_context",
    }
)


def _stable_experiment_packet_semantics(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Exclude advisory telemetry projections from replay semantic equality."""

    return {
        key: value
        for key, value in packet.items()
        if key not in REPLAY_VOLATILE_EXPERIMENT_PACKET_FIELDS
    }


def _validate_experiment_packet_matches_result(
    *,
    experiment_packet_payload: Mapping[str, Any],
    request: Mapping[str, Any],
    source_bundle: dict[str, Any],
    result: Mapping[str, Any],
) -> None:
    """Fail closed when the current experiment packet no longer matches evaluation evidence."""

    runner_summary = result["runner_summary"]
    if experiment_packet_payload["experiment_id"] != runner_summary["experiment_id"]:
        raise CreativeCodePatchGenerationError(
            "generation receipt experiment packet experiment_id is stale."
        )
    if sorted(experiment_packet_payload["mutable_candidate_surface"]) != sorted(
        result["changed_paths"]
    ):
        raise CreativeCodePatchGenerationError(
            "generation receipt experiment packet mutable surface is stale."
        )

    packet_oracle_commands = [
        oracle["command"] for oracle in experiment_packet_payload["immutable_oracles"]
    ]
    if packet_oracle_commands != request["oracle_commands"]:
        raise CreativeCodePatchGenerationError(
            "generation receipt experiment packet immutable oracles are stale."
        )
    if len(packet_oracle_commands) != runner_summary["oracle_commands_configured"]:
        raise CreativeCodePatchGenerationError(
            "generation receipt experiment packet oracle count is stale."
        )
    if runner_summary["oracle_commands_executed"] > len(packet_oracle_commands):
        raise CreativeCodePatchGenerationError(
            "generation receipt runner oracle executions exceed configured packet oracles."
        )
    packet_patch_fingerprint = experiment_packet_payload.get("candidate_patch_fingerprint")
    result_patch_summary = result.get("patch_summary")
    result_patch_fingerprint = (
        result_patch_summary.get("patch_fingerprint")
        if isinstance(result_patch_summary, Mapping)
        else None
    )
    if packet_patch_fingerprint != result_patch_fingerprint:
        raise CreativeCodePatchGenerationError(
            "generation receipt experiment packet candidate patch fingerprint is stale."
        )

    if experiment_packet_payload["budgets"] != _expected_experiment_budgets(request):
        raise CreativeCodePatchGenerationError(
            "generation receipt experiment packet budgets are stale."
        )

    try:
        expected_metrics = validate_metrics(request["metrics"])
    except (AttributeError, TypeError, ValueError) as exc:
        raise CreativeCodePatchGenerationError(
            "generation receipt request metrics are invalid."
        ) from exc
    if experiment_packet_payload["metrics"] != expected_metrics:
        raise CreativeCodePatchGenerationError(
            "generation receipt experiment packet metrics are stale."
        )
    expected_packet = creative_code_patch_builder.build_pr2_experiment_packet(
        request=request,
        source_bundle=source_bundle,
        changed_paths=list(result["changed_paths"]),
        patch_fingerprint=str(experiment_packet_payload["candidate_patch_fingerprint"]),
    )
    if _stable_experiment_packet_semantics(
        experiment_packet_payload
    ) != _stable_experiment_packet_semantics(expected_packet):
        raise CreativeCodePatchGenerationError(
            "generation receipt experiment packet semantics are stale."
        )


def _validate_receipt_matches_gate(
    receipt: Mapping[str, Any], gate: Mapping[str, Any], gate_path: Path
) -> None:
    if receipt["gate_ref"] != _repo_ref(gate_path):
        raise CreativeCodePatchGenerationError("generation receipt gate_ref does not match gate.")
    if receipt["gate_fingerprint"] != fingerprint_payload(dict(gate)):
        raise CreativeCodePatchGenerationError(
            "generation receipt gate fingerprint does not match gate."
        )
    for key in GATE_RECEIPT_PROVENANCE_KEYS:
        if receipt[key] != gate[key]:
            raise CreativeCodePatchGenerationError(f"generation receipt {key} does not match gate.")


def _read_experiment_packet(path: Path) -> dict[str, Any]:
    raw_packet = read_json(path)
    if not isinstance(raw_packet, dict):
        raise CreativeCodePatchGenerationError("experiment packet must be a JSON object.")
    try:
        packet = validate_experiment_packet(raw_packet)
    except ValueError as exc:
        raise CreativeCodePatchGenerationError(str(exc)) from exc
    _reject_payload_safety(packet, label="experiment_packet")
    return cast(dict[str, Any], packet)


def _validate_receipt_linked_artifacts(receipt: Mapping[str, Any]) -> None:
    run_dir = resolve_existing_run_dir(str(receipt["run_id"]))
    (
        expected_candidate_patch,
        expected_patch_metadata,
        expected_experiment_packet,
        expected_result,
    ) = _candidate_artifact_paths(run_dir)
    expected_request = resolve_run_file(run_dir, creative_code_patch_builder.REQUEST_FILE)
    expected_source_bundle = resolve_run_file(
        run_dir,
        creative_code_patch_builder.SOURCE_BUNDLE_FILE,
    )
    expected_selected_variant = resolve_run_file(
        run_dir,
        creative_code_patch_builder.SELECTED_VARIANT_FILE,
    )
    expected_refs = {
        "candidate_patch_ref": _repo_ref(expected_candidate_patch),
        "patch_metadata_ref": _repo_ref(expected_patch_metadata),
        "experiment_packet_ref": _repo_ref(expected_experiment_packet),
        "result_ref": _repo_ref(expected_result),
    }
    mismatched_refs = [
        key for key, expected_ref in expected_refs.items() if receipt[key] != expected_ref
    ]
    if mismatched_refs:
        raise CreativeCodePatchGenerationError(
            "generation receipt sidecar refs must point to the receipt run_id: "
            + ", ".join(sorted(mismatched_refs))
        )
    candidate_patch = _resolve_existing_receipt_ref(
        str(receipt["candidate_patch_ref"]),
        label="candidate_patch_ref",
    )
    patch_metadata = _resolve_existing_receipt_ref(
        str(receipt["patch_metadata_ref"]),
        label="patch_metadata_ref",
    )
    experiment_packet = _resolve_existing_receipt_ref(
        str(receipt["experiment_packet_ref"]),
        label="experiment_packet_ref",
    )
    result_path = _resolve_existing_receipt_ref(str(receipt["result_ref"]), label="result_ref")
    if candidate_patch.name != creative_code_patch_builder.CANDIDATE_PATCH_FILE:
        raise CreativeCodePatchGenerationError("candidate_patch_ref must point to candidate.patch.")
    if patch_metadata.name != creative_code_patch_builder.PATCH_METADATA_FILE:
        raise CreativeCodePatchGenerationError(
            "patch_metadata_ref must point to patch_metadata.json."
        )
    if experiment_packet.name != creative_code_patch_builder.EXPERIMENT_PACKET_FILE:
        raise CreativeCodePatchGenerationError(
            "experiment_packet_ref must point to experiment_packet.json."
        )
    if result_path.name != creative_code_patch_builder.RESULT_FILE:
        raise CreativeCodePatchGenerationError("result_ref must point to result.json.")
    try:
        patch_text = candidate_patch.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CreativeCodePatchGenerationError("candidate patch could not be read.") from exc
    actual_patch_summary = {
        "patch_fingerprint": fingerprint_payload({"candidate_patch": patch_text}),
        "patch_bytes": len(patch_text.encode("utf-8")),
        "diff_lines": len(patch_text.splitlines()),
    }
    if actual_patch_summary != receipt["patch_summary"]:
        raise CreativeCodePatchGenerationError("candidate patch does not match receipt summary.")
    try:
        source_bundle = validate_creative_code_specification_bundle(
            read_json(expected_source_bundle)
        )
        request = validate_creative_code_patch_build_request(
            read_creative_code_patch_build_request(str(expected_request)),
            source_bundle=source_bundle,
        )
        selected_variant = read_json(expected_selected_variant)
        if not isinstance(selected_variant, dict):
            raise CreativeCodePatchGenerationError("selected variant must be a JSON object.")
        metadata = _normalize_patch_metadata(read_json(patch_metadata), label="patch metadata")
        experiment_packet_payload = _read_experiment_packet(experiment_packet)
        result = validate_creative_code_patch_result(
            read_creative_code_patch_result(str(result_path))
        )
    except (CreativeCodePatchContractError, CreativeCodeSpecificationError) as exc:
        raise CreativeCodePatchGenerationError(str(exc)) from exc
    if fingerprint_payload(metadata) != receipt["patch_metadata_fingerprint"]:
        raise CreativeCodePatchGenerationError(
            "generation receipt patch metadata fingerprint is stale."
        )
    if fingerprint_payload(experiment_packet_payload) != receipt["experiment_packet_fingerprint"]:
        raise CreativeCodePatchGenerationError(
            "generation receipt experiment packet fingerprint is stale."
        )
    if fingerprint_payload(result) != receipt["result_fingerprint"]:
        raise CreativeCodePatchGenerationError("generation receipt result fingerprint is stale.")
    try:
        validate_creative_code_patch_run_sidecars(
            request=request,
            result=result,
            patch_text=patch_text,
            selected_variant=selected_variant,
            patch_metadata=metadata,
            require_accepted=result["status"] == "accepted",
        )
    except CreativeCodePatchContractError as exc:
        raise CreativeCodePatchGenerationError(str(exc)) from exc
    _validate_experiment_packet_matches_result(
        experiment_packet_payload=experiment_packet_payload,
        request=request,
        source_bundle=source_bundle,
        result=result,
    )
    if result["result_id"] != receipt["result_id"]:
        raise CreativeCodePatchGenerationError("generation receipt result id is stale.")
    for key in RESULT_RECEIPT_PROVENANCE_KEYS:
        if result[key] != receipt[key]:
            raise CreativeCodePatchGenerationError(f"generation receipt result {key} is stale.")
    if result["status"] != receipt["status"]:
        raise CreativeCodePatchGenerationError("generation receipt status is stale.")
    if result["failure_class"] != receipt["failure_class"]:
        raise CreativeCodePatchGenerationError("generation receipt failure_class is stale.")
    if result["promotion_ready"] != receipt["promotion_ready"]:
        raise CreativeCodePatchGenerationError("generation receipt promotion_ready is stale.")
    if result["patch_summary"] != receipt["patch_summary"]:
        raise CreativeCodePatchGenerationError("generation receipt patch summary is stale.")
    if sorted(result["changed_paths"]) != sorted(receipt["changed_paths"]):
        raise CreativeCodePatchGenerationError("generation receipt changed paths are stale.")
    if result["workspace_summary"] != receipt["workspace_summary"]:
        raise CreativeCodePatchGenerationError("generation receipt workspace summary is stale.")
    if result["runner_summary"] != receipt["runner_summary"]:
        raise CreativeCodePatchGenerationError("generation receipt runner summary is stale.")
    for key, expected in receipt["patch_summary"].items():
        if metadata.get(key) != expected:
            raise CreativeCodePatchGenerationError("patch metadata does not match receipt summary.")
    if sorted(metadata.get("changed_paths", [])) != sorted(receipt["changed_paths"]):
        raise CreativeCodePatchGenerationError("patch metadata changed paths do not match receipt.")


def validate_generation_receipt_linked_artifacts(receipt: Mapping[str, Any]) -> None:
    """Validate that a generation receipt still binds to its local PR-2 sidecars."""

    _validate_receipt_linked_artifacts(receipt)


def _resolve_dispatch_result(path: Path) -> Path:
    """Resolve one trusted dispatcher result under the local experiment result rail."""

    canonical_result_root = REPO_ROOT / "artifacts" / "orchestration" / "experiments" / "results"
    _reject_symlink_components(canonical_result_root, label="trusted dispatch result root")
    candidate = path if path.is_absolute() else REPO_ROOT / path
    _reject_symlink_components(candidate, label="trusted dispatch result")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise CreativeCodePatchGenerationError("trusted dispatch result must exist.") from exc
    result_root = canonical_result_root.resolve(strict=False)
    if not _is_relative_to(resolved, result_root) or not resolved.is_file():
        raise CreativeCodePatchGenerationError(
            "trusted dispatch result must be a file under experiment results."
        )
    if resolved.suffix != ".json":
        raise CreativeCodePatchGenerationError("trusted dispatch result must be JSON.")
    return resolved


def _reconstruct_pre_generation_state(state: Mapping[str, Any]) -> dict[str, Any]:
    """Return the prepared-state projection originally bound by the generation gate."""

    prepared = dict(state)
    prepared["candidate_patch_generated"] = False
    prepared["candidate_patch_evaluated"] = False
    prepared.pop("patch_metadata", None)
    prepared.pop("checkout_destroyed", None)
    return prepared


def _validate_stored_gate_sources_after_generation(
    gate: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Revalidate immutable gate sources without pretending the run is still ungenerated."""

    admission_path = REPO_ROOT / str(gate["admission_ref"])
    admission, request, bundle = _read_admission_context(admission_path)
    expected_bindings: dict[str, Any] = {
        "admission_id": admission["admission_id"],
        "admission_fingerprint": fingerprint_payload(admission),
        "admission_ref": _repo_ref(admission_path),
        "request_id": request["request_id"],
        "request_fingerprint": fingerprint_payload(request),
        "request_ref": admission["patch_request"]["request_ref"],
        "source_bundle_id": request["source_bundle_id"],
        "source_bundle_fingerprint": request["source_bundle_fingerprint"],
        "source_bundle_ref": admission["patch_request"]["source_bundle_ref"],
        "selected_variant_id": request["selected_variant_id"],
        "selected_variant_fingerprint": request["selected_variant_fingerprint"],
        "base_commit_sha": request["base_commit_sha"],
        "budget_limits": dict(request["budgets"]),
        "allowed_paths_fingerprint": fingerprint_payload(
            {
                "allowed_paths": sorted(
                    set(request["allowed_existing_paths"]) | set(request["allowed_new_paths"])
                )
            }
        ),
        "oracle_commands_fingerprint": fingerprint_payload(
            {"oracle_commands": request["oracle_commands"]}
        ),
        "metrics_fingerprint": fingerprint_payload({"metrics": request["metrics"]}),
        "immutable_oracles_fingerprint": fingerprint_payload(
            {"immutable_oracles": bundle["immutable_oracles"]}
        ),
        "oracle_command_count": len(request["oracle_commands"]),
        "metric_count": len(request["metrics"]),
        "immutable_oracle_count": len(bundle["immutable_oracles"]),
    }
    for key, expected in expected_bindings.items():
        if gate[key] != expected:
            raise CreativeCodePatchGenerationError(
                f"generation gate {key} no longer matches its source."
            )
    hints_ref = gate["coordinator_advisory_hints_ref"]
    if hints_ref:
        actual_hints_ref, actual_hints_fingerprint = _read_hints(REPO_ROOT / hints_ref)
        if (
            actual_hints_ref != hints_ref
            or actual_hints_fingerprint != gate["coordinator_advisory_hints_fingerprint"]
        ):
            raise CreativeCodePatchGenerationError(
                "generation gate coordinator advisory hints are stale."
            )
    return request, bundle


def _load_generated_dispatch_context(
    gate: Mapping[str, Any],
    *,
    allow_partial_publication: bool = False,
) -> tuple[
    Path,
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    str,
]:
    """Load and validate the exact generated run awaiting trusted dispatch intake."""

    request, bundle = _validate_stored_gate_sources_after_generation(gate)
    run_dir = resolve_existing_run_dir(str(gate["run_id"]))
    state = read_json(resolve_run_file(run_dir, creative_code_patch_builder.STATE_FILE))
    run_request = read_json(resolve_run_file(run_dir, creative_code_patch_builder.REQUEST_FILE))
    run_bundle = read_json(
        resolve_run_file(run_dir, creative_code_patch_builder.SOURCE_BUNDLE_FILE)
    )
    selected_variant = read_json(
        resolve_run_file(run_dir, creative_code_patch_builder.SELECTED_VARIANT_FILE)
    )
    if not all(
        isinstance(payload, dict) for payload in (state, run_request, run_bundle, selected_variant)
    ):
        raise CreativeCodePatchGenerationError("generated run artifacts must be JSON objects.")
    normalized_run_request = validate_creative_code_patch_build_request(
        cast(dict[str, Any], run_request),
        source_bundle=cast(dict[str, Any], run_bundle),
    )
    normalized_run_bundle = validate_creative_code_specification_bundle(
        cast(dict[str, Any], run_bundle)
    )
    if normalized_run_request != request or normalized_run_bundle != bundle:
        raise CreativeCodePatchGenerationError(
            "generated run request or source bundle no longer matches the gate."
        )
    state = cast(dict[str, Any], state)
    selected_variant = cast(dict[str, Any], selected_variant)
    expected_state_fields = {
        "run_id": gate["run_id"],
        "request_id": gate["request_id"],
        "source_bundle_id": gate["source_bundle_id"],
        "selected_variant_id": gate["selected_variant_id"],
        "base_commit_sha": gate["base_commit_sha"],
    }
    for key, expected in expected_state_fields.items():
        if state.get(key) != expected:
            raise CreativeCodePatchGenerationError(f"generated run state {key} is stale.")
    if state.get("candidate_patch_generated") is not True:
        raise CreativeCodePatchGenerationError("candidate patch has not been generated.")
    candidate_patch_evaluated = state.get("candidate_patch_evaluated")
    if not isinstance(candidate_patch_evaluated, bool):
        raise CreativeCodePatchGenerationError("candidate patch evaluated state must be boolean.")
    if candidate_patch_evaluated and not allow_partial_publication:
        raise CreativeCodePatchGenerationError("candidate patch is already evaluated.")
    if state.get("checkout_destroyed") is not True:
        raise CreativeCodePatchGenerationError("generation checkout destruction is not proven.")
    workspace = state.get("workspace")
    if not isinstance(workspace, dict) or workspace.get("origin_removed") is not True:
        raise CreativeCodePatchGenerationError("generation checkout origin removal is not proven.")
    if fingerprint_payload(_reconstruct_pre_generation_state(state)) != gate["state_fingerprint"]:
        raise CreativeCodePatchGenerationError(
            "generated run state no longer derives from the gate-bound prepared state."
        )
    if (
        selected_variant.get("variant_id") != gate["selected_variant_id"]
        or selected_variant.get("variant_fingerprint") != gate["selected_variant_fingerprint"]
    ):
        raise CreativeCodePatchGenerationError("selected variant no longer matches the gate.")
    if selected_variant != creative_code_patch_builder._selected_variant(normalized_run_bundle):
        raise CreativeCodePatchGenerationError(
            "selected variant no longer matches the validated source bundle."
        )
    candidate_patch, metadata_path, packet_path, result_path = _candidate_artifact_paths(run_dir)
    if (result_path.exists() or result_path.is_symlink()) and not allow_partial_publication:
        raise CreativeCodePatchGenerationError("creative-code patch result already exists.")
    if allow_partial_publication and candidate_patch_evaluated and not result_path.exists():
        raise CreativeCodePatchGenerationError(
            "evaluated candidate state requires a published result."
        )
    for artifact in (candidate_patch, metadata_path, packet_path):
        if not artifact.exists() or not artifact.is_file():
            raise CreativeCodePatchGenerationError(
                f"generated dispatch intake is missing {artifact.name}."
            )
    try:
        patch_text = candidate_patch.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CreativeCodePatchGenerationError("candidate patch could not be read.") from exc
    metadata = _normalize_patch_metadata(read_json(metadata_path), label="patch metadata")
    actual_summary = {
        "patch_fingerprint": fingerprint_payload({"candidate_patch": patch_text}),
        "patch_bytes": len(patch_text.encode("utf-8")),
        "diff_lines": len(patch_text.splitlines()),
    }
    if any(metadata[key] != value for key, value in actual_summary.items()):
        raise CreativeCodePatchGenerationError("candidate patch metadata is stale.")
    if state.get("patch_metadata") != metadata:
        raise CreativeCodePatchGenerationError("generated run state patch metadata is stale.")
    packet = _read_experiment_packet(packet_path)
    if packet.get("candidate_patch_fingerprint") != actual_summary["patch_fingerprint"]:
        raise CreativeCodePatchGenerationError(
            "experiment packet candidate patch fingerprint is stale."
        )
    return run_dir, state, request, bundle, packet, patch_text


def _validate_dispatch_result_binding(
    *,
    dispatch_result: dict[str, Any],
    packet: Mapping[str, Any],
    changed_paths: list[str],
    patch_fingerprint: str,
) -> dict[str, Any]:
    """Require trusted, one-attempt dispatcher evidence for the exact PR-2 packet."""

    try:
        result = cast(dict[str, Any], validate_experiment_result(dispatch_result))
    except (TypeError, ValueError) as exc:
        raise CreativeCodePatchGenerationError(
            "trusted dispatch result failed Experiment Runner validation."
        ) from exc
    if result["runner_mode"] != DEFAULT_RUNNER_MODE:
        raise CreativeCodePatchGenerationError(
            "trusted dispatch result must use candidate_patch runner mode."
        )
    if result["candidate_patch"] not in TRUSTED_DISPATCH_CANDIDATE_PATCH_REFS:
        raise CreativeCodePatchGenerationError(
            "trusted dispatch result candidate marker is invalid."
        )
    if (
        result["promotion_ready"] is not False
        or result["contribution_kind"] != "none"
        or result["coauthor_required"] is not False
        or result["coauthor_reason"] != ""
    ):
        raise CreativeCodePatchGenerationError(
            "trusted candidate dispatch result must not claim promotion or material attribution."
        )
    if (
        packet.get("candidate_patch_fingerprint") != patch_fingerprint
        or result.get("candidate_patch_fingerprint") != patch_fingerprint
    ):
        raise CreativeCodePatchGenerationError(
            "trusted dispatch result candidate patch fingerprint does not match."
        )
    failure_class = result["failure_class"]
    backend = result.get("execution_backend")
    preflight_status = backend.get("preflight_status") if isinstance(backend, dict) else None
    preflight_passed_container = (
        isinstance(backend, dict)
        and backend.get("name") in TRUSTED_DISPATCH_BACKENDS
        and preflight_status == "passed"
    )
    failed_preflight_capability = (
        failure_class == "capability_mismatch" and preflight_status == "failed"
    )
    if not isinstance(backend, dict) or not (
        preflight_passed_container or failed_preflight_capability
    ):
        raise CreativeCodePatchGenerationError(
            "trusted dispatch result requires valid backend provenance."
        )
    if result["experiment_id"] != packet["experiment_id"]:
        raise CreativeCodePatchGenerationError(
            "trusted dispatch result experiment_id does not match the generated packet."
        )
    mutated_paths = sorted(result["mutated_paths"])
    if mutated_paths not in ([], sorted(changed_paths)):
        raise CreativeCodePatchGenerationError(
            "trusted dispatch result mutated paths do not match the generated candidate."
        )
    if failure_class == "unchanged_result":
        raise CreativeCodePatchGenerationError(
            "trusted dispatch finalization does not support unchanged_result for a generated patch."
        )
    if failure_class == "infra_flake":
        raise CreativeCodePatchGenerationError(
            "trusted dispatch finalization does not publish transient infra_flake results."
        )
    if failure_class == "metric_regression":
        raise CreativeCodePatchGenerationError(
            "trusted dispatch finalization does not support metric_regression "
            "without structured metric evidence."
        )
    if (
        result["status"] == "accepted" or failure_class in ORACLE_REQUIRED_FAILURE_CLASSES
    ) and mutated_paths != sorted(changed_paths):
        raise CreativeCodePatchGenerationError(
            "oracle-evaluated trusted dispatch result must bind every candidate path."
        )
    observations = result["budget_observations"]
    if observations.get("configured_budgets") != packet["budgets"]:
        raise CreativeCodePatchGenerationError(
            "trusted dispatch result configured budgets do not match the packet."
        )
    if observations.get("oracle_commands_configured") != len(packet["immutable_oracles"]):
        raise CreativeCodePatchGenerationError(
            "trusted dispatch result configured oracle count does not match the packet."
        )
    attempts = observations.get("attempts")
    allowed_attempts = (
        {0, 1} if failure_class in {"capability_mismatch", "policy_violation"} else {1}
    )
    if attempts not in allowed_attempts or observations.get("retries_consumed") != 0:
        if allowed_attempts == {1}:
            raise CreativeCodePatchGenerationError(
                "trusted dispatch result must record one attempt and zero retries."
            )
        raise CreativeCodePatchGenerationError(
            "pre-oracle trusted dispatch result must record zero or one attempt "
            "and zero retries."
        )
    if (
        result["status"] == "accepted" or failure_class in ORACLE_REQUIRED_FAILURE_CLASSES
    ) and "runner_error" in observations:
        raise CreativeCodePatchGenerationError(
            "accepted and oracle-derived trusted dispatch results must not carry runner_error."
        )
    if failure_class in {"capability_mismatch", "policy_violation"} and (
        mutated_paths
        or result["oracle_results"]
        or observations.get("oracle_commands_executed") != 0
    ):
        raise CreativeCodePatchGenerationError(
            "pre-oracle trusted dispatch rejection must not claim mutation or oracle evidence."
        )
    if failure_class == "capability_mismatch":
        runner_error = observations.get("runner_error")
        if preflight_status == "failed":
            if runner_error not in TRUSTED_DISPATCH_PREFLIGHT_BLOCKERS:
                raise CreativeCodePatchGenerationError(
                    "failed-preflight capability_mismatch requires a supported blocker code."
                )
        elif runner_error != TRUSTED_DISPATCH_CAPABILITY_ERROR:
            raise CreativeCodePatchGenerationError(
                "post-preflight capability_mismatch requires the canonical runner signal."
            )
    if failure_class == "policy_violation":
        runner_error = observations.get("runner_error")
        if not isinstance(runner_error, str) or not runner_error.strip():
            raise CreativeCodePatchGenerationError(
                "policy_violation trusted dispatch rejection requires explanatory runner evidence."
            )
    oracle_commands = [item["command"] for item in result["oracle_results"]]
    configured_commands = [item["command"] for item in packet["immutable_oracles"]]
    if oracle_commands != configured_commands[: len(oracle_commands)]:
        raise CreativeCodePatchGenerationError(
            "trusted dispatch result oracle commands do not match the packet."
        )
    if result["status"] == "accepted":
        if oracle_commands != configured_commands or any(
            item["returncode"] != 0 or item["timed_out"] for item in result["oracle_results"]
        ):
            raise CreativeCodePatchGenerationError(
                "accepted trusted dispatch result requires every configured oracle to pass."
            )
    elif failure_class in ORACLE_REQUIRED_FAILURE_CLASSES:
        if not result["oracle_results"]:
            raise CreativeCodePatchGenerationError(
                "oracle-derived trusted dispatch rejection requires executed oracle evidence."
            )
        if failure_class == "timeout":
            timed_out_oracles = [item for item in result["oracle_results"] if item["timed_out"]]
            if not timed_out_oracles:
                raise CreativeCodePatchGenerationError(
                    "timeout trusted dispatch rejection requires timed-out oracle evidence."
                )
            if any(item["returncode"] == 0 for item in timed_out_oracles):
                raise CreativeCodePatchGenerationError(
                    "timeout trusted dispatch rejection requires a nonzero return code."
                )
        elif failure_class in FAILING_ORACLE_REQUIRED_FAILURE_CLASSES:
            if any(item["timed_out"] for item in result["oracle_results"]):
                raise CreativeCodePatchGenerationError(
                    "timed-out oracle evidence must use the timeout failure class."
                )
            if not any(item["returncode"] != 0 for item in result["oracle_results"]):
                raise CreativeCodePatchGenerationError(
                    "oracle-derived trusted dispatch rejection requires failing oracle evidence."
                )
            if failure_class == "oom":
                first_failing_oracle = next(
                    item for item in result["oracle_results"] if item["returncode"] != 0
                )
                if not any(
                    pattern.search(
                        f"{first_failing_oracle['stdout']}\n{first_failing_oracle['stderr']}"
                    )
                    for pattern in OOM_PATTERNS
                ):
                    raise CreativeCodePatchGenerationError(
                        "oom trusted dispatch rejection requires OOM-specific evidence "
                        "from the first failing oracle."
                    )
    if result["shared_tree_untouched"] is not True:
        raise CreativeCodePatchGenerationError(
            "trusted dispatch result must prove the shared tree was untouched."
        )
    return result


def _finalize_dispatched_result_locked(
    args: argparse.Namespace,
    *,
    gate_path: Path,
    gate: dict[str, Any],
) -> int:
    receipt_path = gate_path.parent / RECEIPT_FILENAME
    if receipt_path.exists() or receipt_path.is_symlink():
        raise CreativeCodePatchGenerationError("generation receipt already exists.")
    _require_base_and_tree_for_step(gate["base_commit_sha"])
    run_dir, state, request, bundle, packet, patch_text = _load_generated_dispatch_context(
        gate,
        allow_partial_publication=True,
    )
    metadata_path = resolve_run_file(run_dir, creative_code_patch_builder.PATCH_METADATA_FILE)
    metadata = _normalize_patch_metadata(read_json(metadata_path), label="patch metadata")
    selected_variant = read_json(
        resolve_run_file(run_dir, creative_code_patch_builder.SELECTED_VARIANT_FILE)
    )
    if not isinstance(selected_variant, dict):
        raise CreativeCodePatchGenerationError("selected variant must be a JSON object.")
    dispatch_path = _resolve_dispatch_result(args.dispatch_result)
    dispatch_result = _validate_dispatch_result_binding(
        dispatch_result=_read_pinned_dispatch_json_object(dispatch_path),
        packet=packet,
        changed_paths=list(metadata["changed_paths"]),
        patch_fingerprint=str(metadata["patch_fingerprint"]),
    )
    result = build_creative_code_patch_result(
        request=request,
        changed_paths=list(metadata["changed_paths"]),
        patch_fingerprint=str(metadata["patch_fingerprint"]),
        patch_bytes=int(metadata["patch_bytes"]),
        diff_lines=int(metadata["diff_lines"]),
        runner_result=dispatch_result,
        checkout_destroyed=True,
        origin_removed=True,
        shared_tree_untouched=True,
    )
    try:
        validate_creative_code_patch_run_sidecars(
            request=request,
            result=result,
            patch_text=patch_text,
            selected_variant=selected_variant,
            patch_metadata=metadata,
            require_accepted=result["status"] == "accepted",
        )
    except CreativeCodePatchContractError as exc:
        raise CreativeCodePatchGenerationError(str(exc)) from exc
    _validate_result_matches_gate(result, gate)
    _validate_experiment_packet_matches_result(
        experiment_packet_payload=packet,
        request=request,
        source_bundle=bundle,
        result=result,
    )
    receipt = _build_receipt(
        gate_path=gate_path,
        gate=gate,
        result=result,
        require_result_file=False,
    )
    result_path = resolve_run_file(run_dir, creative_code_patch_builder.RESULT_FILE, for_write=True)
    partial_result_exists = result_path.exists()
    if partial_result_exists:
        partial_result = _read_pinned_json_object(
            result_path,
            trusted_root=run_dir,
            label="partial creative-code patch result",
            max_bytes=TRUSTED_DISPATCH_RESULT_MAX_BYTES,
        )
        if partial_result != result:
            raise CreativeCodePatchGenerationError(
                "partial creative-code patch result does not match trusted dispatch evidence."
            )
    _require_base_and_tree_for_step(gate["base_commit_sha"])
    (
        current_run_dir,
        current_state,
        current_request,
        current_bundle,
        current_packet,
        current_patch_text,
    ) = _load_generated_dispatch_context(
        gate,
        allow_partial_publication=True,
    )
    if (
        current_run_dir != run_dir
        or current_state != state
        or current_request != request
        or current_bundle != bundle
        or current_packet != packet
        or current_patch_text != patch_text
    ):
        raise CreativeCodePatchGenerationError(
            "generated dispatch context changed before result publication."
        )
    current_dispatch_result = _validate_dispatch_result_binding(
        dispatch_result=_read_pinned_dispatch_json_object(dispatch_path),
        packet=current_packet,
        changed_paths=list(metadata["changed_paths"]),
        patch_fingerprint=str(metadata["patch_fingerprint"]),
    )
    if current_dispatch_result != dispatch_result:
        raise CreativeCodePatchGenerationError(
            "trusted dispatch result changed before result publication."
        )
    current_partial_result_exists = result_path.exists()
    if current_partial_result_exists != partial_result_exists:
        raise CreativeCodePatchGenerationError(
            "partial creative-code patch result changed before publication."
        )
    if current_partial_result_exists:
        current_partial_result = _read_pinned_json_object(
            result_path,
            trusted_root=run_dir,
            label="partial creative-code patch result",
            max_bytes=TRUSTED_DISPATCH_RESULT_MAX_BYTES,
        )
        if current_partial_result != result:
            raise CreativeCodePatchGenerationError(
                "partial creative-code patch result changed before publication."
            )
    original_state = dict(state)
    result_written = False
    state_written = False

    def remove_matching_receipt() -> None:
        if not receipt_path.exists() or receipt_path.is_symlink():
            return
        current_receipt = _read_pinned_json_object(
            receipt_path,
            trusted_root=receipt_path.parent,
            label="rollback generation receipt",
            max_bytes=TRUSTED_DISPATCH_RESULT_MAX_BYTES,
        )
        if current_receipt == receipt:
            receipt_path.unlink()

    try:
        if not partial_result_exists:
            _write_json_new(result_path, result)
            result_written = True
        if state["candidate_patch_evaluated"] is not True:
            state["candidate_patch_evaluated"] = True
            write_json_atomic(
                resolve_run_file(
                    run_dir,
                    creative_code_patch_builder.STATE_FILE,
                    for_write=True,
                ),
                state,
            )
            state_written = True
        _write_json_new(receipt_path, receipt)
    except Exception as publication_error:
        rollback_errors: list[str] = []
        rollback_actions = (
            (
                "receipt removal",
                remove_matching_receipt,
            ),
            (
                "state restoration",
                lambda: (
                    write_json_atomic(
                        resolve_run_file(
                            run_dir,
                            creative_code_patch_builder.STATE_FILE,
                            for_write=True,
                        ),
                        original_state,
                    )
                    if state_written
                    else None
                ),
            ),
            (
                "result removal",
                lambda: (
                    result_path.unlink()
                    if result_written and result_path.exists() and not result_path.is_symlink()
                    else None
                ),
            ),
        )
        for label, rollback in rollback_actions:
            try:
                rollback()
            except Exception as rollback_error:
                rollback_errors.append(f"{label}: {rollback_error.__class__.__name__}")
        if rollback_errors:
            raise CreativeCodePatchGenerationError(
                "dispatch result publication failed and rollback was incomplete: "
                + "; ".join(rollback_errors)
            ) from publication_error
        if isinstance(publication_error, CreativeCodePatchGenerationError):
            raise publication_error
        raise CreativeCodePatchGenerationError(
            "dispatch result publication failed after complete rollback."
        ) from publication_error
    print(FINALIZE_DISPATCHED_RESULT_SUCCESS_OUTPUT)
    print(_repo_ref(receipt_path))
    return 0


def _finalize_dispatched_result(args: argparse.Namespace) -> int:
    gate_path = admission_cli._resolve_repo_json_file(args.gate, label="generation gate")
    gate = validate_generation_gate(_read_json_object(gate_path, label="generation gate"))
    run_dir = resolve_existing_run_dir(str(gate["run_id"]))
    with _exclusive_finalize_lock(run_dir):
        return _finalize_dispatched_result_locked(
            args,
            gate_path=gate_path,
            gate=gate,
        )


def _validate_run_plan(args: argparse.Namespace) -> int:
    output_dir = _resolve_output_dir(args.output_dir or str(_default_output_dir(args.run_id)))
    try:
        gate = build_generation_gate(
            admission_path=args.admission,
            run_id=args.run_id,
            coordinator_advisory_hints_path=args.coordinator_advisory_hints,
        )
        gate_path = output_dir / GATE_FILENAME
        _write_json_new(gate_path, gate)
    except Exception:
        if not any(output_dir.iterdir()):
            shutil.rmtree(output_dir)
        raise
    print(VALIDATE_RUN_PLAN_SUCCESS_OUTPUT)
    print(_repo_ref(gate_path))
    return 0


def _generate_candidate(args: argparse.Namespace) -> int:
    gate_path, gate = _validate_gate_context(args.gate)
    receipt_path = gate_path.parent / RECEIPT_FILENAME
    if receipt_path.exists() or receipt_path.is_symlink():
        raise CreativeCodePatchGenerationError("generation receipt already exists.")
    _require_base_and_tree_for_step(gate["base_commit_sha"])
    creative_code_patch_builder.generate(run_id=gate["run_id"])
    _require_base_and_tree_for_step(gate["base_commit_sha"])
    result = creative_code_patch_builder.evaluate(run_id=gate["run_id"])
    result_path = resolve_run_file(
        resolve_run_dir(gate["run_id"], create=False),
        creative_code_patch_builder.RESULT_FILE,
    )
    validated_result = validate_creative_code_patch_result(
        read_creative_code_patch_result(str(result_path))
    )
    if validated_result != result:
        raise CreativeCodePatchGenerationError("evaluated result does not match result artifact.")
    _validate_result_matches_gate(validated_result, gate)
    receipt = _build_receipt(gate_path=gate_path, gate=gate, result=validated_result)
    _write_json_new(receipt_path, receipt)
    print(GENERATE_CANDIDATE_SUCCESS_OUTPUT)
    print(_repo_ref(receipt_path))
    return 0


def _validate_artifacts(args: argparse.Namespace) -> int:
    gate_path = admission_cli._resolve_repo_json_file(args.gate, label="generation gate")
    gate = validate_generation_gate(_read_json_object(gate_path, label="generation gate"))
    if args.receipt is not None:
        receipt = validate_generation_receipt(
            _read_json_object(args.receipt, label="generation receipt")
        )
        _validate_receipt_matches_gate(receipt, gate, gate_path)
        _validate_receipt_linked_artifacts(receipt)
    print(VALIDATE_ARTIFACTS_SUCCESS_OUTPUT)
    return 0


def _summarize_result(args: argparse.Namespace) -> int:
    receipt = validate_generation_receipt(
        _read_json_object(args.receipt, label="generation receipt")
    )
    summary = {
        "artifact_type": RECEIPT_ARTIFACT_TYPE,
        "receipt_id": receipt["receipt_id"],
        "gate_id": receipt["gate_id"],
        "request_id": receipt["request_id"],
        "run_id": receipt["run_id"],
        "base_commit_sha": receipt["base_commit_sha"],
        "status": receipt["status"],
        "failure_class": receipt["failure_class"],
        "promotion_ready": False,
        "authority_boundary": "pr2_local_candidate_generation_only",
        "not_merge_readiness_evidence": True,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="creative_code_patch_generation",
        description="Gate and execute local PR-2 creative-code candidate generation.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_plan = subparsers.add_parser("validate-run-plan")
    validate_plan.add_argument("--admission", type=Path, required=True)
    validate_plan.add_argument("--run-id", required=True)
    validate_plan.add_argument("--coordinator-advisory-hints", type=Path)
    validate_plan.add_argument("--output-dir")
    validate_plan.set_defaults(func=_validate_run_plan)

    generate = subparsers.add_parser("generate-candidate")
    generate.add_argument("--gate", type=Path, required=True)
    generate.set_defaults(func=_generate_candidate)

    finalize_dispatch = subparsers.add_parser("finalize-dispatched-result")
    finalize_dispatch.add_argument("--gate", type=Path, required=True)
    finalize_dispatch.add_argument("--dispatch-result", type=Path, required=True)
    finalize_dispatch.set_defaults(func=_finalize_dispatched_result)

    validate = subparsers.add_parser("validate-artifacts")
    validate.add_argument("--gate", type=Path, required=True)
    validate.add_argument("--receipt", type=Path)
    validate.set_defaults(func=_validate_artifacts)

    summarize = subparsers.add_parser("summarize-result")
    summarize.add_argument("--receipt", type=Path, required=True)
    summarize.set_defaults(func=_summarize_result)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        return int(args.func(args))
    except (
        CreativeCodePatchGenerationError,
        CreativeCodePatchContractError,
        CreativeCodePatchWorkspaceError,
        CreativeSpecPatchAdmissionError,
        CreativeSpecLearningRollupError,
        admission_cli.CreativeSpecPatchAdmissionCliError,
        creative_code_patch_builder.CreativeCodePatchBuilderError,
    ) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
