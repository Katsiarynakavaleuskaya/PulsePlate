#!/usr/bin/env python3
"""Compose admitted local oracle evidence and exact role-context delivery.

Receipts bind cooperative local observations. They grant no execution, review,
publication or merge authority and do not authenticate human/native execution.
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import sys
import tempfile
from typing import Any
import uuid
import zipfile

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration import experiment_runner_dispatch as dispatcher
from scripts.orchestration.creative_code_patch_workspace import exclusive_patch_run_lock
from scripts.orchestration.evidence_rail_applicability import (
    POLICY_VERSION as SELECTOR_POLICY,
    build_evidence_rail_applicability,
    read_task_packet_snapshot,
)
from scripts.orchestration.experiment_contract import (
    CONTRIBUTION_KINDS,
    ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE,
    validate_experiment_packet,
    validate_experiment_result,
    validate_contribution_attribution,
)
from scripts.orchestration.pr_evidence_sidecar import _kernel_rename_noreplace
from scripts.orchestration.evidence_rail_applicability import _validate_packet_projection
from scripts.orchestration.experiment_runner_pr_creative_context import (
    _require_safe_workflow_archive_member,
    _safe_workflow_file,
    _workflow_json_bytes,
)
from scripts.orchestration.experiment_runner_pr_creative_context_contract import (
    build_experiment_runner_pr_oracle_attachment,
    validate_experiment_runner_pr_oracle_attachment,
)

POLICY_VERSION = "pr_oracle_attachment.v1"
EVIDENCE_ROOT = REPO_ROOT / "artifacts/orchestration/experiments/results/oracle_attachments"
MAX_BYTES = 2 * 1024 * 1024
MAX_ARCHIVE_BYTES = 8 * MAX_BYTES
MAX_RUN_BYTES = 4 * MAX_BYTES
MAX_RETAINED_RUNS = 32
BUNDLE_FILES = (
    "request.json",
    "experiment_packet.json",
    "task_packet.json",
    "result.json",
    "snapshot.json",
    "attachment.json",
    "receipt.json",
)


class OracleEvidenceError(ValueError):
    """An admitted dependent operation lacks usable current evidence."""

    def __init__(
        self,
        message: str,
        *,
        lifecycle_state: str = "invalid_evidence",
        runner_failure_class: str | None = None,
    ) -> None:
        super().__init__(message)
        self.lifecycle_state = lifecycle_state
        self.runner_failure_class = runner_failure_class


def _raw(ref: str) -> bytes:
    raw: bytes = _safe_workflow_file(ref, maximum=MAX_BYTES)
    return raw


def _object(ref: str) -> dict[str, Any]:
    payload: dict[str, Any] = _workflow_json_bytes(_raw(ref), maximum=MAX_BYTES)
    return payload


def _ref(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _digest(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _private_directory(path: Path) -> None:
    dispatcher._reject_symlink_components(path)
    if path.exists():
        if not path.is_dir() or path.stat().st_mode & 0o777 != 0o700:
            raise OracleEvidenceError("Existing evidence directory has invalid private mode.")
        return
    path.mkdir(parents=True, mode=0o700)
    dispatcher._reject_symlink_components(path)
    if not path.is_dir():
        raise OracleEvidenceError("Evidence directory is unavailable.")


def _publish(path: Path, value: dict[str, Any]) -> None:
    _publish_bytes(path, (json.dumps(value, sort_keys=True, indent=2) + "\n").encode())


def _publish_bytes(path: Path, data: bytes, *, maximum: int = MAX_BYTES) -> None:
    """Publish bounded private bytes through the existing kernel no-replace owner."""

    if (
        path.parent.parent != EVIDENCE_ROOT
        or maximum not in {MAX_BYTES, MAX_ARCHIVE_BYTES}
        or len(data) > maximum
    ):
        raise OracleEvidenceError("Publication is outside its fixed evidence slot or byte bound.")
    dispatcher._reject_symlink_components(path.parent)
    descriptor, stage_name = tempfile.mkstemp(prefix=".oracle-stage-", dir=path.parent)
    stage = Path(stage_name)
    directory_fd = -1
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        _kernel_rename_noreplace(directory_fd, stage.name, directory_fd, path.name)
        os.fsync(directory_fd)
    finally:
        if directory_fd >= 0:
            os.close(directory_fd)
        stage.unlink(missing_ok=True)


def _execute_dispatch(arguments: list[str]) -> int:
    """Use the fixed owner in-process; its bounded operations retain finally cleanup."""

    captured = io.StringIO()
    with redirect_stdout(captured):
        status: int = dispatcher.main(arguments)
    if len(captured.getvalue()) > MAX_BYTES:
        raise OracleEvidenceError("Dispatcher summary exceeds its bound.")
    return status


def _manifest(packet: str, mode: str, owners: tuple[str, ...]) -> dict[str, Any]:
    from scripts.orchestration import qoder_dispatch_bridge

    argv = ["--packet", packet, "--mode", mode]
    for owner in owners:
        argv.extend(["--implementation-owner", owner])
    captured = io.StringIO()
    with redirect_stdout(captured):
        status = qoder_dispatch_bridge.main(argv)
    if status or len(captured.getvalue()) > MAX_BYTES:
        raise OracleEvidenceError("Canonical role dispatch did not validate.")
    manifest: dict[str, Any] = _workflow_json_bytes(captured.getvalue().encode(), maximum=MAX_BYTES)
    return manifest


def _selection(packet: str, order: int, mode: str, owners: tuple[str, ...]) -> dict[str, Any]:
    manifest = _manifest(packet, mode, owners)
    sequence = manifest["dispatch_sequence"]
    if type(order) is not int or order < 1 or order > len(sequence):
        raise OracleEvidenceError("Select one existing one-based dispatch occurrence.")
    row = sequence[order - 1]
    return {
        key: row[key] for key in ("order", "role_slug", "readonly", "implementation_owner_override")
    }


def _request(
    *,
    packet: str,
    experiment_packet: str,
    mode: str,
    owners: tuple[str, ...],
    backend: str,
    image: str,
    admitted_new_files: tuple[str, ...],
    checked_inputs: tuple[str, ...],
    contribution_kind: str = "none",
    coauthor_required: bool = False,
    coauthor_reason: str = "",
    material_root: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if material_root is None:
        raise OracleEvidenceError("Explicit distinct material checkout is required.")
    dispatcher._reject_symlink_components(material_root)
    if (
        not material_root.is_absolute()
        or material_root.resolve() != material_root
        or not material_root.is_dir()
        or material_root.is_relative_to(REPO_ROOT.resolve())
        or REPO_ROOT.resolve().is_relative_to(material_root)
    ):
        raise OracleEvidenceError("Material checkout must be canonical and distinct from controls.")
    task = read_task_packet_snapshot(packet)
    applicability = build_evidence_rail_applicability(task)
    if not any(
        rail == "experiment_runner" and treatment.value == "required"
        for rail, treatment, _ in applicability.treatments
    ):
        raise OracleEvidenceError("The canonical selector did not require oracle evidence.")
    experiment_bytes = _raw(experiment_packet)
    raw_experiment = _workflow_json_bytes(experiment_bytes, maximum=MAX_BYTES)
    budgets = raw_experiment.get("budgets")
    if not isinstance(budgets, dict) or any(
        type(value) is not int for key, value in budgets.items() if key != "stop_condition"
    ):
        raise OracleEvidenceError("Approved budgets require literal integers without bool aliases.")
    if len(set(owners)) != len(owners):
        raise OracleEvidenceError("Implementation owner flags must be unique.")
    attribution = validate_contribution_attribution(
        contribution_kind=contribution_kind,
        coauthor_required=coauthor_required,
        coauthor_reason=coauthor_reason,
    )
    experiment = validate_experiment_packet(raw_experiment)
    if experiment["runner_mode"] != ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE:
        raise OracleEvidenceError("The admitted experiment must be oracle-only.")
    if experiment["budgets"]["network_budget"] != 0:
        raise OracleEvidenceError("Oracle evidence requires network_budget=0.")
    if platform.system() == "Darwin" and backend != "apple-container":
        raise OracleEvidenceError("macOS requires explicit apple-container.")
    if backend not in dispatcher.CONTAINER_BACKENDS:
        raise OracleEvidenceError("Oracle evidence requires a strict container backend.")
    dispatcher.parse_image_reference(image)
    if len(set(checked_inputs)) != len(checked_inputs) or len(checked_inputs) > 32:
        raise OracleEvidenceError("Checked input references must be bounded and unique.")
    if any(
        not any(
            path == surface or path.startswith(surface.rstrip("/") + "/")
            for surface in experiment["mutable_candidate_surface"]
        )
        for path in admitted_new_files
    ):
        raise OracleEvidenceError("New-file admission exceeds the experiment context.")
    try:
        source_material = dispatcher.capture_source_material(material_root, admitted_new_files)
        tool_source = dispatcher.capture_source_material(REPO_ROOT.resolve())
    except (ValueError, dispatcher.DispatchError) as exc:
        raise OracleEvidenceError(
            "Exact raw material cannot be acquired.", lifecycle_state="material_unavailable"
        ) from exc
    if source_material["repository"].casefold() != tool_source["repository"].casefold():
        raise OracleEvidenceError("Material and trusted controls must name the same repository.")
    request = {
        "policy_version": POLICY_VERSION,
        "selector_policy_version": SELECTOR_POLICY,
        "task_packet_ref": task.packet_path,
        "task_packet_id": task.task_packet_id,
        "task_packet_fingerprint": task.task_packet_fingerprint,
        "experiment_packet_ref": experiment_packet,
        "experiment_packet_sha256": _digest(experiment_bytes),
        "experiment_packet_fingerprint": fingerprint_payload(experiment),
        "source_material": source_material,
        "material_root": str(material_root),
        "tool_root_binding": _digest(str(REPO_ROOT.resolve()).encode()),
        "tool_source": tool_source,
        "dispatch_mode": mode,
        "implementation_owners": sorted(owners),
        "backend": backend,
        "image": image,
        "checked_inputs": [
            {"ref": ref, "sha256": _digest(_raw(ref))} for ref in sorted(checked_inputs)
        ],
        "contribution": {
            "kind": attribution[0],
            "coauthor_required": attribution[1],
            "reason": attribution[2],
        },
    }
    return request, experiment


def _dependency_names(request: dict[str, Any]) -> dict[str, tuple[str, str]]:
    required_request = {
        "policy_version",
        "selector_policy_version",
        "task_packet_ref",
        "task_packet_id",
        "task_packet_fingerprint",
        "experiment_packet_ref",
        "experiment_packet_sha256",
        "experiment_packet_fingerprint",
        "source_material",
        "dispatch_mode",
        "implementation_owners",
        "backend",
        "image",
        "checked_inputs",
        "contribution",
    }
    if (
        set(request)
        not in (
            required_request,
            required_request | {"material_root", "tool_root_binding", "tool_source"},
        )
        or request["policy_version"] != POLICY_VERSION
        or request["selector_policy_version"] != SELECTOR_POLICY
    ):
        raise OracleEvidenceError("Frozen request shape or policy is invalid.")
    checked = request["checked_inputs"]
    new = request["source_material"]["admitted_new_files"]
    if (
        not isinstance(checked, list)
        or not isinstance(new, list)
        or len(checked) > 32
        or len(new) > 32
    ):
        raise OracleEvidenceError("Dependency inventory is malformed or over budget.")
    dependencies = {
        "experiment_packet.json": (
            request["experiment_packet_ref"],
            request["experiment_packet_sha256"],
        ),
        "task_packet.json": (request["task_packet_ref"], request["task_packet_fingerprint"]),
    }
    for index, row in enumerate(checked):
        if not isinstance(row, dict) or set(row) != {"ref", "sha256"}:
            raise OracleEvidenceError("Checked-input binding is malformed.")
        dependencies[f"checked-{index:02}.input"] = (row["ref"], row["sha256"])
    for index, row in enumerate(new):
        if (
            not isinstance(row, dict)
            or set(row) != {"path", "mode", "sha256"}
            or row["mode"] not in {"100644", "100755"}
        ):
            raise OracleEvidenceError("New-file binding is malformed.")
        dependencies[f"new-{index:02}.input"] = (row["path"], "sha256:" + row["sha256"])
    return dependencies


def _dependencies(request: dict[str, Any]) -> dict[str, bytes]:
    retained: dict[str, bytes] = {}
    for name, (ref, expected) in _dependency_names(request).items():
        raw = (
            dispatcher._material_file(Path(request["material_root"]), ref)
            if name.startswith("new-") and "material_root" in request
            else _raw(ref)
        )
        if _digest(raw) != expected:
            raise OracleEvidenceError(
                "An approved input dependency changed before retention.", lifecycle_state="stale"
            )
        retained[name] = raw
    return retained


def _attempt_names(receipt: dict[str, Any]) -> set[str]:
    count = receipt.get("attempts")
    if type(count) is not int or not 1 <= count <= 3:
        raise OracleEvidenceError("Attempt inventory is malformed or over budget.")
    return {
        name
        for index in range(1, count + 1)
        for name in (f"attempt-{index}.json", f"attempt-{index}.terminal.json")
    }


def _historical_bundle(
    files: dict[str, bytes],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Validate frozen internal lineage, without requiring current Git material."""

    try:
        request = _workflow_json_bytes(files["request.json"], maximum=MAX_BYTES)
        dependencies = _dependency_names(request)
        receipt = _workflow_json_bytes(files["receipt.json"], maximum=MAX_BYTES)
        expected_members = set(BUNDLE_FILES) | set(dependencies) | _attempt_names(receipt)
        if set(files) != expected_members or sum(map(len, files.values())) > MAX_RUN_BYTES:
            raise OracleEvidenceError("Frozen bundle inventory or byte budget is invalid.")
        required_receipt = {
            "schema_version",
            "authority",
            "request_fingerprint",
            "files",
            "attempts",
            "retries_consumed",
        }
        if (
            set(receipt) != required_receipt
            or receipt["schema_version"] != POLICY_VERSION
            or receipt["authority"] != "evidence_only"
            or not isinstance(receipt["files"], dict)
        ):
            raise OracleEvidenceError("Frozen receipt shape is invalid.")
        if receipt["files"] != {
            name: _digest(raw) for name, raw in files.items() if name != "receipt.json"
        } or receipt["request_fingerprint"] != fingerprint_payload(request):
            raise OracleEvidenceError("Frozen receipt does not bind every original member.")
        for name, (_, expected) in dependencies.items():
            if _digest(files[name]) != expected:
                raise OracleEvidenceError(
                    "Frozen input dependency differs from its approved binding."
                )
        task = _workflow_json_bytes(files["task_packet.json"], maximum=MAX_BYTES)
        _validate_packet_projection(task, filename_id=request["task_packet_id"])
        experiment = validate_experiment_packet(
            _workflow_json_bytes(files["experiment_packet.json"], maximum=MAX_BYTES)
        )
        if fingerprint_payload(experiment) != request["experiment_packet_fingerprint"]:
            raise OracleEvidenceError("Approved experiment semantics differ from the request.")
        if (
            type(receipt["attempts"]) is not int
            or type(receipt["retries_consumed"]) is not int
            or receipt["attempts"] != receipt["retries_consumed"] + 1
            or not 0 <= receipt["retries_consumed"] <= experiment["budgets"]["retry_budget"]
        ):
            raise OracleEvidenceError("Frozen retry observation exceeds its approved budget.")
        for index in range(1, receipt["attempts"] + 1):
            attempt = _workflow_json_bytes(files[f"attempt-{index}.json"], maximum=MAX_BYTES)
            terminal = _workflow_json_bytes(
                files[f"attempt-{index}.terminal.json"], maximum=MAX_BYTES
            )
            result_ref = terminal.get("result_ref", "")
            if not re.fullmatch(
                r"artifacts/orchestration/experiments/results/oracle-[0-9a-f]{32}\.json",
                result_ref,
            ):
                raise OracleEvidenceError("Owned attempt reference is invalid.")
            snapshot_ref = result_ref.removesuffix(".json") + ".snapshot.json"
            observations_ref = snapshot_ref.removesuffix(".json") + ".observations.json"
            if (
                attempt
                != {
                    "result_ref": result_ref,
                    "snapshot_ref": snapshot_ref,
                    "private_observations_ref": observations_ref,
                    "lifecycle_state": "running",
                }
                or terminal.get("private_observations_ref") != observations_ref
            ):
                raise OracleEvidenceError("Attempt source and terminal references differ.")
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", terminal.get("result_sha256", "")):
                raise OracleEvidenceError("Attempt result lacks its original byte binding.")
            final = index == receipt["attempts"]
            if (
                type(terminal.get("returncode")) is not int
                or terminal["returncode"] != (0 if final else 4)
                or terminal.get("runner_failure_class") != (None if final else "infra_flake")
            ):
                raise OracleEvidenceError("Attempt retry lineage is inconsistent.")
            if final and terminal["result_sha256"] != _digest(files["result.json"]):
                raise OracleEvidenceError("Attempt final result differs from its original bytes.")
            if final and not re.fullmatch(
                r"sha256:[0-9a-f]{64}", terminal.get("private_observations_sha256", "")
            ):
                raise OracleEvidenceError("Original private observations lack a byte binding.")
        result = _accepted(
            _workflow_json_bytes(files["result.json"], maximum=MAX_BYTES),
            experiment,
            _workflow_json_bytes(files["snapshot.json"], maximum=MAX_BYTES),
            request,
        )
        result_ref = _ref(
            EVIDENCE_ROOT / receipt["request_fingerprint"].removeprefix("sha256:") / "result.json"
        )
        attachment = validate_experiment_runner_pr_oracle_attachment(
            _workflow_json_bytes(files["attachment.json"], maximum=MAX_BYTES)
        )
        if attachment != _attachment(request, result, result_ref):
            raise OracleEvidenceError(
                "Frozen attachment does not bind its actual result and request."
            )
        return request, result, receipt
    except (KeyError, TypeError, AttributeError, IndexError, RecursionError) as exc:
        raise OracleEvidenceError("Malformed frozen evidence lineage.") from exc


def _bundle_bytes(directory: Path) -> dict[str, bytes]:
    try:
        request = _object(_ref(directory / "request.json"))
        receipt = _object(_ref(directory / "receipt.json"))
        members = set(BUNDLE_FILES) | set(_dependency_names(request)) | _attempt_names(receipt)
        return {name: _raw(_ref(directory / name)) for name in members}
    except (KeyError, TypeError, AttributeError, IndexError) as exc:
        raise OracleEvidenceError("Malformed linked dependency inventory.") from exc


def _accepted(
    result: dict[str, Any],
    experiment: dict[str, Any],
    proof: dict[str, Any],
    request: dict[str, Any],
) -> dict[str, Any]:
    result = validate_experiment_result(result)
    commands = [row["command"] for row in experiment["immutable_oracles"]]
    observations = result["budget_observations"]
    backend = result.get("execution_backend")
    configured = observations.get("configured_budgets")
    if not isinstance(configured, dict) or any(
        type(value) is not int for key, value in configured.items() if key != "stop_condition"
    ):
        raise OracleEvidenceError("Configured budget observations require literal integers.")
    if (
        result["status"] != "accepted"
        or result["failure_class"] is not None
        or result["experiment_id"] != experiment["experiment_id"]
        or result["runner_mode"] != ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE
        or not commands
        or [row["command"] for row in result["oracle_results"]] != commands
        or any(
            row["returncode"] != 0 or row["timed_out"] or row["stdout"] or row["stderr"]
            for row in result["oracle_results"]
        )
        or result["mutated_paths"]
        or result["shared_tree_untouched"] is not True
        or result["promotion_ready"] is not False
        or observations.get("configured_budgets") != experiment["budgets"]
        or observations.get("oracle_commands_configured") != len(commands)
        or observations.get("oracle_commands_executed") != len(commands)
        or type(observations.get("oracle_commands_configured")) is not int
        or type(observations.get("oracle_commands_executed")) is not int
        or type(observations.get("attempts")) is not int
        or observations["attempts"] != 1
        or type(observations.get("retries_consumed")) is not int
        or observations["retries_consumed"] != 0
        or not isinstance(backend, dict)
        or backend.get("preflight_status") != "passed"
        or backend.get("name") != request["backend"]
        or backend.get("image_digest") != dispatcher.parse_image_reference(request["image"]).digest
    ):
        raise OracleEvidenceError("Result does not prove the complete approved oracle execution.")
    contribution = request["contribution"]
    if (result["contribution_kind"], result["coauthor_required"], result["coauthor_reason"]) != (
        contribution["kind"],
        contribution["coauthor_required"],
        contribution["reason"],
    ):
        raise OracleEvidenceError(
            "Result attribution does not match the explicit material-use input."
        )
    expected_proof = {
        "schema_version",
        "authority",
        "source_material",
        "snapshot_diff_sha256",
        "copied_new_files",
        "experiment_packet_fingerprint",
        "result_fingerprint",
        "execution_backend",
        "result_projection",
        "snapshot_content_sha256",
    }
    if "tool_source" in request:
        expected_proof |= {"tool_source", "tool_snapshot_content_sha256"}
        if (
            proof.get("tool_source") != request["tool_source"]
            or proof.get("tool_snapshot_content_sha256")
            != request["tool_source"]["tracked_content_sha256"]
        ):
            raise OracleEvidenceError("Trusted control snapshot binding differs.")
    if (
        set(proof) != expected_proof
        or proof["schema_version"] != "experiment_runner_checked_snapshot.v1"
        or proof["authority"] != "evidence_only"
        or proof["source_material"] != request["source_material"]
        or proof["copied_new_files"] != request["source_material"]["admitted_new_files"]
        or proof["experiment_packet_fingerprint"] != fingerprint_payload(experiment)
        or proof["result_fingerprint"] != fingerprint_payload(result)
        or proof["execution_backend"] != backend
        or proof["result_projection"] != "sanitized_command_observations_v1"
        or proof["snapshot_content_sha256"] != request["source_material"]["tracked_content_sha256"]
        or not isinstance(proof["snapshot_diff_sha256"], str)
        or not re.fullmatch(r"[0-9a-f]{64}", proof["snapshot_diff_sha256"])
    ):
        raise OracleEvidenceError("Trusted checked-snapshot binding is missing or inconsistent.")
    return result


def _validate_oracle_evidence(
    ref: str,
    *,
    packet: str,
    selected_dispatch: dict[str, Any],
    mode: str,
    implementation_owners: tuple[str, ...] = (),
    material_root: Path | None = None,
) -> dict[str, Any]:
    """Reacquire the winning linked bytes and current source at consumption."""

    if material_root is None:
        raise OracleEvidenceError("Current consumption requires caller-admitted material root.")
    path = REPO_ROOT / ref
    if path.name != "receipt.json" or path.parent.parent != EVIDENCE_ROOT:
        raise OracleEvidenceError("Evidence must name a canonical immutable receipt.")
    files = _bundle_bytes(path.parent)
    request, result, receipt = _historical_bundle(files)
    if path.parent.name != receipt["request_fingerprint"].removeprefix("sha256:"):
        raise OracleEvidenceError("Request identity does not match its evidence slot.")
    if "material_root" not in request or "tool_source" not in request:
        raise OracleEvidenceError(
            "Historical evidence lacks current control provenance.", lifecycle_state="stale"
        )
    if material_root is not None and str(material_root) != request["material_root"]:
        raise OracleEvidenceError(
            "Material root differs from retained evidence.", lifecycle_state="stale"
        )
    current, _ = _request(
        material_root=material_root,
        packet=packet,
        experiment_packet=request["experiment_packet_ref"],
        mode=mode,
        owners=implementation_owners,
        backend=request["backend"],
        image=request["image"],
        admitted_new_files=tuple(
            row["path"] for row in request["source_material"]["admitted_new_files"]
        ),
        checked_inputs=tuple(row["ref"] for row in request["checked_inputs"]),
        contribution_kind=request["contribution"]["kind"],
        coauthor_required=request["contribution"]["coauthor_required"],
        coauthor_reason=request["contribution"]["reason"],
    )
    if current != request:
        raise OracleEvidenceError(
            "Oracle evidence is stale for the current material.", lifecycle_state="stale"
        )
    selected = _selection(packet, selected_dispatch["order"], mode, implementation_owners)
    if selected != selected_dispatch:
        raise OracleEvidenceError("Oracle delivery does not match the exact dispatch occurrence.")
    attachment = _attachment(request, result, _ref(path.parent / "result.json"))
    return {
        "authority": "evidence_only",
        "lifecycle_state": "validated",
        "receipt_fingerprint": fingerprint_payload(receipt),
        "source_material_fingerprint": fingerprint_payload(request["source_material"]),
        "selected_dispatch": selected,
        "attachment": attachment,
    }


def validate_oracle_evidence(
    ref: str,
    *,
    packet: str,
    selected_dispatch: dict[str, Any],
    mode: str,
    implementation_owners: tuple[str, ...] = (),
    material_root: Path | None = None,
) -> dict[str, Any]:
    """One public consumer boundary for malformed, linked and currentness failures."""

    try:
        return _validate_oracle_evidence(
            ref,
            packet=packet,
            selected_dispatch=selected_dispatch,
            mode=mode,
            implementation_owners=implementation_owners,
            material_root=material_root,
        )
    except (KeyError, TypeError, AttributeError, IndexError, RecursionError) as exc:
        raise OracleEvidenceError("Malformed linked oracle evidence.") from exc


def _attachment(request: dict[str, Any], result: dict[str, Any], result_ref: str) -> dict[str, Any]:
    source = request["source_material"]
    attachment: dict[str, Any] = build_experiment_runner_pr_oracle_attachment(
        source={
            "repository": source["repository"],
            "pr_number": None,
            "base_ref": "main",
            "base_sha": source["base_sha"],
            "head_sha": source["head_sha"],
            "task_packet_id": request["task_packet_id"],
            "generated_at_utc": None,
        },
        oracle_status="accepted",
        result_ref=result_ref,
        result_fingerprint=fingerprint_payload(result),
        coauthor_required=result["coauthor_required"],
    )
    return attachment


def ensure_oracle_evidence(
    *,
    packet: str,
    experiment_packet: str,
    role_context_order: int,
    mode: str,
    implementation_owners: tuple[str, ...] = (),
    backend: str,
    image: str,
    admitted_new_files: tuple[str, ...] = (),
    checked_inputs: tuple[str, ...] = (),
    contribution_kind: str = "none",
    coauthor_required: bool = False,
    coauthor_reason: str = "",
    material_root: Path | None = None,
) -> str:
    """Execute once for exact admitted inputs, or validate a retained winner."""

    if material_root is None:
        raise OracleEvidenceError("Explicit distinct material checkout is required.")
    selected = _selection(packet, role_context_order, mode, implementation_owners)

    def acquire_request() -> tuple[dict[str, Any], dict[str, Any]]:
        return _request(
            material_root=material_root,
            packet=packet,
            experiment_packet=experiment_packet,
            mode=mode,
            owners=implementation_owners,
            backend=backend,
            image=image,
            admitted_new_files=admitted_new_files,
            checked_inputs=checked_inputs,
            contribution_kind=contribution_kind,
            coauthor_required=coauthor_required,
            coauthor_reason=coauthor_reason,
        )

    request, experiment = acquire_request()
    _private_directory(EVIDENCE_ROOT)
    directory = EVIDENCE_ROOT / fingerprint_payload(request).removeprefix("sha256:")
    with exclusive_patch_run_lock(EVIDENCE_ROOT, label="oracle retention admission"):
        if not directory.exists():
            retained = [path for path in EVIDENCE_ROOT.iterdir() if path.name != "restores"]
            if any(
                path.is_symlink()
                or not path.is_dir()
                or not re.fullmatch(r"[0-9a-f]{64}", path.name)
                for path in retained
            ):
                raise OracleEvidenceError("Evidence retention inventory is invalid.")
            if len(retained) >= MAX_RETAINED_RUNS:
                raise OracleEvidenceError(
                    "Evidence capacity reached; retain and clean only verified owned runs."
                )
        _private_directory(directory)
    receipt_ref = _ref(directory / "receipt.json")
    with exclusive_patch_run_lock(directory, label="oracle evidence"):
        current, _ = acquire_request()
        if current != request:
            raise OracleEvidenceError(
                "Material changed before execution admission.", lifecycle_state="stale"
            )
        if (directory / "receipt.json").exists():
            validate_oracle_evidence(
                receipt_ref,
                packet=packet,
                selected_dispatch=selected,
                mode=mode,
                implementation_owners=implementation_owners,
                material_root=material_root,
            )
            return receipt_ref
        if any(directory.iterdir()):
            raise OracleEvidenceError(
                "Partial or interrupted evidence requires bounded owner recovery."
            )
        _publish(directory / "request.json", request)
        _publish(
            directory / "control.json",
            {
                "authority": "evidence_only",
                "lifecycle_state": "prepared",
                "request_fingerprint": fingerprint_payload(request),
            },
        )
        dependencies = _dependencies(request)
        if sum(len(raw) for raw in dependencies.values()) > MAX_RUN_BYTES:
            raise OracleEvidenceError("Frozen input dependencies exceed the retained byte budget.")
        for name, raw in dependencies.items():
            _publish_bytes(directory / name, raw)
        for attempt in range(experiment["budgets"]["retry_budget"] + 1):
            current, _ = acquire_request()
            if current != request:
                raise OracleEvidenceError(
                    "Material changed before execution attempt.", lifecycle_state="stale"
                )
            nonce = "oracle-" + uuid.uuid4().hex
            result_path = dispatcher.RESULT_ARTIFACT_DIR / (nonce + ".json")
            proof_path = dispatcher.RESULT_ARTIFACT_DIR / (nonce + ".snapshot.json")
            argv = [
                "run",
                "--material-root",
                str(material_root),
                "--packet",
                _ref(directory / "experiment_packet.json"),
                "--backend",
                backend,
                "--image",
                image,
                "--output",
                result_path.name,
                "--snapshot-proof-output",
                proof_path.name,
            ]
            for path in admitted_new_files:
                argv.extend(["--admitted-new-file", path])
            if contribution_kind != "none":
                argv.extend(
                    [
                        "--contribution-kind",
                        contribution_kind,
                        "--coauthor-required",
                        "--coauthor-reason",
                        coauthor_reason,
                    ]
                )
            _publish(
                directory / f"attempt-{attempt + 1}.json",
                {
                    "result_ref": _ref(result_path),
                    "snapshot_ref": _ref(proof_path),
                    "private_observations_ref": _ref(
                        proof_path.with_name(proof_path.stem + ".observations.json")
                    ),
                    "lifecycle_state": "running",
                },
            )
            try:
                status = _execute_dispatch(argv)
            except BaseException as exc:
                _publish(
                    directory / "failure.json",
                    {
                        "lifecycle_state": "interrupted",
                        "reason_class": type(exc).__name__,
                        "authority": "evidence_only",
                    },
                )
                raise
            if not result_path.exists():
                raise OracleEvidenceError("Strict execution did not retain a result.")
            result = validate_experiment_result(_object(_ref(result_path)))
            observation_path = proof_path.with_name(proof_path.stem + ".observations.json")
            _publish(
                directory / f"attempt-{attempt + 1}.terminal.json",
                {
                    "result_ref": _ref(result_path),
                    "result_sha256": _digest(_raw(_ref(result_path))),
                    "returncode": status,
                    "runner_failure_class": result["failure_class"],
                    "private_observations_ref": _ref(observation_path),
                    "private_observations_sha256": (
                        _digest(_raw(_ref(observation_path))) if observation_path.exists() else None
                    ),
                },
            )
            current, _ = acquire_request()
            if current != request:
                raise OracleEvidenceError(
                    "Source material changed during oracle execution.", lifecycle_state="stale"
                )
            if status == 0 and result["status"] == "accepted":
                if not observation_path.exists():
                    raise OracleEvidenceError("Accepted private observation provenance is missing.")
                proof = _object(_ref(proof_path))
                _accepted(result, experiment, proof, request)
                break
            if (
                result["failure_class"] != "infra_flake"
                or attempt >= experiment["budgets"]["retry_budget"]
            ):
                raise OracleEvidenceError(
                    "Strict oracle failed; original attempt evidence retained.",
                    lifecycle_state={
                        "capability_mismatch": "capability_unavailable",
                        "timeout": "timeout",
                    }.get(result["failure_class"], "oracle_failed"),
                    runner_failure_class=result["failure_class"],
                )
        current, _ = acquire_request()
        if current != request:
            raise OracleEvidenceError(
                "Source material changed during oracle execution.", lifecycle_state="stale"
            )
        _publish_bytes(directory / "result.json", _raw(_ref(result_path)))
        _publish_bytes(directory / "snapshot.json", _raw(_ref(proof_path)))
        _publish(
            directory / "attachment.json",
            _attachment(request, result, _ref(directory / "result.json")),
        )
        files = {
            name: _digest(_raw(_ref(directory / name)))
            for name in (*BUNDLE_FILES, *dependencies, *_attempt_names({"attempts": attempt + 1}))
            if name != "receipt.json"
        }
        _publish(
            directory / "receipt.json",
            {
                "schema_version": POLICY_VERSION,
                "authority": "evidence_only",
                "request_fingerprint": fingerprint_payload(request),
                "files": files,
                "attempts": attempt + 1,
                "retries_consumed": attempt,
            },
        )
        validate_oracle_evidence(
            receipt_ref,
            packet=packet,
            selected_dispatch=selected,
            mode=mode,
            implementation_owners=implementation_owners,
            material_root=material_root,
        )
    return receipt_ref


def render_pr_evidence(
    ref: str,
    *,
    packet: str,
    selected_dispatch: dict[str, Any],
    mode: str,
    implementation_owners: tuple[str, ...] = (),
    material_root: Path | None = None,
) -> str:
    """Prepare a local body projection; this function performs no publication."""

    validated = validate_oracle_evidence(
        ref,
        packet=packet,
        selected_dispatch=selected_dispatch,
        mode=mode,
        implementation_owners=implementation_owners,
        material_root=material_root,
    )
    return (
        "## Experiment Runner Evidence\n\nArtifact: "
        + str(Path(ref).parent / "result.json")
        + "\nLocal linkage: "
        + ref
        + "\nAuthority: evidence only; current-head review and merge gates remain required.\n"
        + "Material contribution declared: "
        + str(validated["attachment"]["coauthor_required"]).lower()
        + "\n"
    )


def _require_export_member(name: str, data: bytes) -> None:
    """Delegate private-text screening after recognizing closed authority metadata."""

    if name == "attachment.json":
        attachment = validate_experiment_runner_pr_oracle_attachment(
            _workflow_json_bytes(data, maximum=MAX_BYTES)
        )
        # The canonical validator already requires exact literal authority fields.
        # Its read_secrets=false capability is metadata, not a secret value.
        screening = {key: value for key, value in attachment.items() if key != "authority"}
        _require_safe_workflow_archive_member(name, json.dumps(screening).encode())
    else:
        _require_safe_workflow_archive_member(name, data)


def export_evidence(ref: str) -> tuple[str, str]:
    """Export one finite sanitized ordinary evidence bundle without overwrite."""

    directory = (REPO_ROOT / ref).parent
    if directory.parent != EVIDENCE_ROOT or Path(ref).name != "receipt.json":
        raise OracleEvidenceError("Export requires a canonical evidence receipt.")
    files = _bundle_bytes(directory)
    request, _, _ = _historical_bundle(files)
    # Transport retains screened references; immutable originals remain companions.
    companion_names = {"task_packet.json", "request.json"} | {
        name for name in _dependency_names(request) if name.startswith(("checked-", "new-"))
    }
    for name in sorted(companion_names):
        original = files.pop(name)
        projection = name.removesuffix(".json").removesuffix(".input") + "_dependency.json"
        files[projection] = json.dumps(
            {
                "ref": (
                    request["task_packet_ref"]
                    if name == "task_packet.json"
                    else _ref(directory / name)
                ),
                "sha256": _digest(original),
                "authority": "dependency_reference_only",
            },
            sort_keys=True,
        ).encode()
    for name, data in files.items():
        _require_export_member(name, data)
    manifest = {
        "schema_version": "pr_oracle_archive.v1",
        "authority": "transport_evidence_only",
        "files": {name: _digest(data) for name, data in files.items()},
    }
    output = directory / "oracle_evidence.zip"
    with exclusive_patch_run_lock(directory, label="oracle export"):
        if output.exists() or output.is_symlink():
            raise OracleEvidenceError("Existing archive is preserved; export is no-overwrite.")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
            for name, data in {
                **files,
                "manifest.json": json.dumps(manifest, sort_keys=True).encode(),
            }.items():
                info = zipfile.ZipInfo(name)
                info.external_attr = 0o600 << 16
                archive.writestr(info, data)
        if len(buffer.getvalue()) > MAX_ARCHIVE_BYTES:
            raise OracleEvidenceError("Archive exceeds its bound.")
        _publish_bytes(output, buffer.getvalue(), maximum=MAX_ARCHIVE_BYTES)
    return _ref(output), _digest(buffer.getvalue())


def verify_archive(archive_ref: str, expected_sha256: str, restore_ref: str) -> str:
    """Verify transport bytes and restore to a fresh owned leaf; no currentness claim."""

    raw = _safe_workflow_file(archive_ref, maximum=MAX_ARCHIVE_BYTES)
    if _digest(raw) != expected_sha256:
        raise OracleEvidenceError("Downloaded archive hash differs.")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        names = [i.filename for i in infos]
        fixed = (set(BUNDLE_FILES) - {"task_packet.json", "request.json"}) | {
            "task_packet_dependency.json",
            "manifest.json",
        }
        if (
            len(infos) > len(fixed) + 70
            or len(set(names)) != len(names)
            or not fixed.issubset(names)
            or any(
                name not in fixed
                and not re.fullmatch(
                    r"(?:(?:checked|new)-[0-9]{2}(?:\.input|_dependency\.json)|request(?:\.json|_dependency\.json)|attempt-[1-3](?:\.terminal)?\.json)",
                    name,
                )
                for name in names
            )
        ):
            raise OracleEvidenceError("Archive member inventory is unsafe.")
        if any(
            i.compress_type != zipfile.ZIP_STORED
            or i.is_dir()
            or i.file_size > MAX_BYTES
            or ((i.external_attr >> 16) & 0o170000) not in {0, 0o100000}
            for i in infos
        ):
            raise OracleEvidenceError("Archive member type or size is unsafe.")
        files = {i.filename: archive.read(i) for i in infos}
    manifest = _workflow_json_bytes(files.pop("manifest.json"), maximum=MAX_BYTES)
    if manifest != {
        "schema_version": "pr_oracle_archive.v1",
        "authority": "transport_evidence_only",
        "files": {name: _digest(data) for name, data in files.items()},
    }:
        raise OracleEvidenceError("Archive member digests differ.")
    for name, data in files.items():
        _require_export_member(name, data)
    # Derive the closed original inventory from the transported receipt before
    # opening any private companion. Archive projection refs never select readers.
    receipt = _workflow_json_bytes(files["receipt.json"], maximum=MAX_BYTES)
    if (
        set(receipt)
        != {
            "schema_version",
            "authority",
            "request_fingerprint",
            "files",
            "attempts",
            "retries_consumed",
        }
        or receipt["schema_version"] != POLICY_VERSION
        or receipt["authority"] != "evidence_only"
        or not isinstance(receipt["files"], dict)
        or not isinstance(receipt["request_fingerprint"], str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", receipt["request_fingerprint"]) is None
    ):
        raise OracleEvidenceError(
            "Original receipt inventory is malformed.", lifecycle_state="storage_pending"
        )
    original_names = set(receipt["files"]) | {"receipt.json"}
    required_originals = set(BUNDLE_FILES) | _attempt_names(receipt)
    if (
        not required_originals.issubset(original_names)
        or any(
            name not in required_originals
            and not re.fullmatch(r"(?:checked|new)-[0-9]{2}\.input", name)
            for name in original_names
        )
        or any(
            not isinstance(value, str) or re.fullmatch(r"sha256:[0-9a-f]{64}", value) is None
            for value in receipt["files"].values()
        )
    ):
        raise OracleEvidenceError(
            "Original member inventory is invalid.", lifecycle_state="storage_pending"
        )
    original_directory = EVIDENCE_ROOT / receipt["request_fingerprint"].removeprefix("sha256:")
    companions = {"task_packet.json"}
    legacy_task_ref = None
    if "request_dependency.json" in files:
        companions |= {"request.json"} | {
            name for name in original_names if name.startswith(("checked-", "new-"))
        }
    else:
        # Historical archives carry their complete screened request. Its bound
        # literal task ref remains the older companion API; no provenance upgrade.
        request_raw = files.get("request.json", b"")
        legacy_request = _workflow_json_bytes(request_raw, maximum=MAX_BYTES)
        if (
            _digest(request_raw) != receipt["files"]["request.json"]
            or fingerprint_payload(legacy_request) != receipt["request_fingerprint"]
        ):
            raise OracleEvidenceError(
                "Historical request binding differs.", lifecycle_state="storage_pending"
            )
        legacy_task_ref = _dependency_names(legacy_request)["task_packet.json"][0]
    projections = {
        name.removesuffix(".json").removesuffix(".input") + "_dependency.json": name
        for name in companions
    }
    if set(files) != (original_names - companions) | set(projections):
        raise OracleEvidenceError("Companion inventory differs.", lifecycle_state="storage_pending")
    admitted: dict[str, tuple[str, str]] = {}
    task_projection = _workflow_json_bytes(files["task_packet_dependency.json"], maximum=MAX_BYTES)
    for projection, original_name in projections.items():
        row = _workflow_json_bytes(files[projection], maximum=MAX_BYTES)
        expected_ref = _ref(original_directory / original_name)
        if (
            set(row) != {"ref", "sha256", "authority"}
            or row["authority"] != "dependency_reference_only"
            or row["sha256"] != receipt["files"][original_name]
            or (original_name != "task_packet.json" and row["ref"] != expected_ref)
        ):
            raise OracleEvidenceError(
                "Companion reference differs from original lineage.",
                lifecycle_state="storage_pending",
            )
        if original_name != "task_packet.json":
            admitted[original_name] = (expected_ref, row["sha256"])
    # The receipt permits just this derived canonical request slot read. Neither
    # the archive's request ref nor its task ref selects this acquisition.
    request_ref = _ref(original_directory / "request.json")
    try:
        request_raw = files["request.json"] if legacy_task_ref is not None else _raw(request_ref)
    except (OSError, ValueError) as exc:
        raise OracleEvidenceError(
            "Original request is unavailable.", lifecycle_state="storage_pending"
        ) from exc
    original_request = _workflow_json_bytes(request_raw, maximum=MAX_BYTES)
    if (
        _digest(request_raw) != receipt["files"]["request.json"]
        or fingerprint_payload(original_request) != receipt["request_fingerprint"]
    ):
        raise OracleEvidenceError(
            "Original request binding differs.", lifecycle_state="storage_pending"
        )
    task_id = original_request.get("task_packet_id")
    if not isinstance(task_id, str) or re.fullmatch(r"[0-9a-f]{12}", task_id) is None:
        raise OracleEvidenceError(
            "Original task identity is invalid.", lifecycle_state="storage_pending"
        )
    expected_task_ref = f"artifacts/orchestration/task_packets/{task_id}.json"
    if (
        original_request.get("task_packet_ref") != expected_task_ref
        or task_projection["ref"] != expected_task_ref
    ):
        raise OracleEvidenceError(
            "Companion reference differs from original lineage.", lifecycle_state="storage_pending"
        )
    original_dependencies = _dependency_names(original_request)
    if set(original_dependencies) | set(BUNDLE_FILES) | _attempt_names(receipt) != original_names:
        raise OracleEvidenceError(
            "Original dependency inventory differs.", lifecycle_state="storage_pending"
        )
    admitted["task_packet.json"] = (expected_task_ref, receipt["files"]["task_packet.json"])
    # All refs and all-and-only carriers are checked before remaining companion reads.
    validation_files = {name: raw for name, raw in files.items() if name not in projections}
    if "request.json" in admitted:
        admitted.pop("request.json")
        validation_files["request.json"] = request_raw
    for name, (ref, expected) in admitted.items():
        try:
            original = _raw(ref)
        except (OSError, ValueError) as exc:
            raise OracleEvidenceError(
                "Original companion is unavailable.", lifecycle_state="storage_pending"
            ) from exc
        if _digest(original) != expected:
            raise OracleEvidenceError(
                "Original companion differs.", lifecycle_state="storage_pending"
            )
        validation_files[name] = original
    try:
        _historical_bundle(validation_files)
    except OracleEvidenceError as exc:
        raise OracleEvidenceError(
            "Complete original restore lineage is unavailable.", lifecycle_state="storage_pending"
        ) from exc
    restore = REPO_ROOT / restore_ref
    restore_root = EVIDENCE_ROOT / "restores"
    if restore.parent != restore_root or not re.fullmatch(
        r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}", restore.name
    ):
        raise OracleEvidenceError("Restore requires a fresh leaf in the existing evidence root.")
    _private_directory(restore_root)
    with exclusive_patch_run_lock(restore_root, label="oracle restore admission"):
        retained = list(restore_root.iterdir())
        if any(
            leaf.is_symlink()
            or not leaf.is_dir()
            or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}", leaf.name)
            or leaf.stat().st_mode & 0o777 != 0o700
            for leaf in retained
        ):
            raise OracleEvidenceError("Restore inventory contains an unsafe resource.")
        if len(retained) >= MAX_RETAINED_RUNS:
            raise OracleEvidenceError(
                "Restore capacity reached; preserve existing verified resources."
            )
        dispatcher._reject_symlink_components(restore)
        restore.mkdir(mode=0o700)
    with exclusive_patch_run_lock(restore, label="oracle restore publication"):
        for name, data in validation_files.items():
            with (restore / name).open("xb") as handle:
                os.fchmod(handle.fileno(), 0o600)
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        validate_restored_bundle(restore_ref)
    return _ref(restore)


def validate_restored_bundle(restore_ref: str) -> dict[str, Any]:
    """Validate historical lineage in a fresh leaf, without promoting live evidence."""

    directory = REPO_ROOT / restore_ref
    if directory.parent != EVIDENCE_ROOT / "restores":
        raise OracleEvidenceError("Historical validation requires the owned restore root.")
    try:
        request, _, receipt = _historical_bundle(_bundle_bytes(directory))
    except (KeyError, TypeError, AttributeError, IndexError) as exc:
        raise OracleEvidenceError("Malformed restored bundle.") from exc
    return {
        "authority": "transport_evidence_only",
        "historical_lineage": "validated",
        "request_fingerprint": receipt["request_fingerprint"],
        "material_head_sha": request["source_material"]["head_sha"],
        "currentness_claim": False,
    }


def main(argv: list[str] | None = None) -> int:
    from scripts.orchestration.qoder_dispatch_bridge import DISPATCH_MODES

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=(
            "dispatch",
            "ensure",
            "validate",
            "body",
            "export",
            "verify-archive",
            "validate-restored",
        ),
    )
    parser.add_argument("--material-root", type=Path)
    parser.add_argument("--packet")
    parser.add_argument("--experiment-packet")
    parser.add_argument("--role-context-order", type=int)
    parser.add_argument("--mode", choices=DISPATCH_MODES, default="runtime")
    parser.add_argument("--implementation-owner", action="append", default=[])
    parser.add_argument("--backend", default="apple-container")
    parser.add_argument("--image")
    parser.add_argument("--admitted-new-file", action="append", default=[])
    parser.add_argument("--checked-input", action="append", default=[])
    parser.add_argument("--instruction-file", action="append", default=[])
    parser.add_argument("--oracle-evidence")
    parser.add_argument("--no-auto-oracle", action="store_true")
    parser.add_argument("--archive")
    parser.add_argument("--sha256")
    parser.add_argument("--restore-dir")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--contribution-kind", choices=CONTRIBUTION_KINDS, default="none")
    parser.add_argument("--coauthor-required", action="store_true")
    parser.add_argument("--coauthor-reason", default="")
    args = parser.parse_args(argv)
    try:
        if args.command == "export":
            output, digest = export_evidence(args.oracle_evidence)
            print(
                json.dumps(
                    {"archive": output, "sha256": digest, "storage_state": "storage_pending"}
                )
            )
            return 0
        if args.command == "verify-archive":
            print(verify_archive(args.archive, args.sha256, args.restore_dir))
            return 0
        if args.command == "validate-restored":
            print(json.dumps(validate_restored_bundle(args.restore_dir)))
            return 0
        if not args.packet or args.role_context_order is None:
            raise OracleEvidenceError("Canonical packet and exact occurrence are required.")
        if (
            args.command in {"ensure", "dispatch", "validate", "body"}
            and args.material_root is None
        ):
            raise OracleEvidenceError("Explicit distinct material checkout is required.")
        owners = tuple(args.implementation_owner)
        selected = _selection(args.packet, args.role_context_order, args.mode, owners)
        if args.command in {"validate", "body"} or args.no_auto_oracle:
            if not args.oracle_evidence:
                raise OracleEvidenceError(
                    "Disabled automatic transport still requires manual evidence.",
                    lifecycle_state="disabled",
                )
            ref = args.oracle_evidence
            validated = validate_oracle_evidence(
                ref,
                packet=args.packet,
                selected_dispatch=selected,
                mode=args.mode,
                implementation_owners=owners,
                material_root=args.material_root,
            )
        else:
            if args.oracle_evidence or not args.experiment_packet or not args.image:
                raise OracleEvidenceError(
                    "Automatic dispatch requires approved experiment and image inputs."
                )
            ref = ensure_oracle_evidence(
                material_root=args.material_root,
                packet=args.packet,
                experiment_packet=args.experiment_packet,
                role_context_order=args.role_context_order,
                mode=args.mode,
                implementation_owners=owners,
                backend=args.backend,
                image=args.image,
                admitted_new_files=tuple(args.admitted_new_file),
                checked_inputs=tuple(args.checked_input),
                contribution_kind=args.contribution_kind,
                coauthor_required=args.coauthor_required,
                coauthor_reason=args.coauthor_reason,
            )
            validated = validate_oracle_evidence(
                ref,
                packet=args.packet,
                selected_dispatch=selected,
                mode=args.mode,
                implementation_owners=owners,
                material_root=args.material_root,
            )
        if args.command == "dispatch":
            command = [
                sys.executable,
                "-I",
                str(REPO_ROOT / "scripts/orchestration/role_dispatch_bridge.py"),
                "--packet",
                args.packet,
                "--role-context-order",
                str(args.role_context_order),
                "--mode",
                args.mode,
                "--oracle-evidence",
                ref,
                "--oracle-material-root",
                str(args.material_root),
            ]
            for owner in owners:
                command.extend(["--implementation-owner", owner])
            for instruction in args.instruction_file:
                command.extend(["--instruction-file", instruction])
            if args.pretty:
                command.append("--pretty")
            try:
                result = dispatcher._run(command, cwd=REPO_ROOT, timeout=120)
            except dispatcher.DispatchError as exc:
                raise OracleEvidenceError("Exact bridge delivery failed.") from exc
            if result.returncode:
                raise OracleEvidenceError("Exact bridge delivery failed.")
            print(result.stdout, end="")
        elif args.command == "ensure":
            print(ref)
        elif args.command == "body":
            print(
                render_pr_evidence(
                    ref,
                    packet=args.packet,
                    selected_dispatch=selected,
                    mode=args.mode,
                    implementation_owners=owners,
                    material_root=args.material_root,
                ),
                end="",
            )
        else:
            print(json.dumps(validated, indent=2 if args.pretty else None))
        return 0
    except (OSError, ValueError, TypeError, KeyError, zipfile.BadZipFile) as exc:
        print(
            json.dumps(
                {
                    "component": "pr_oracle_attachment",
                    "lifecycle_state": (
                        "storage_pending"
                        if args.command in {"export", "verify-archive", "validate-restored"}
                        else (
                            exc.lifecycle_state
                            if isinstance(exc, OracleEvidenceError)
                            else "invalid_evidence"
                        )
                    ),
                    "runner_failure_class": (
                        exc.runner_failure_class if isinstance(exc, OracleEvidenceError) else None
                    ),
                    "error_class": type(exc).__name__,
                }
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
