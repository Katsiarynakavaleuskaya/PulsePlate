from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any, cast

import pytest

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration import (
    creative_code_patch_builder,
    creative_code_patch_generation,
    creative_code_patch_workspace,
    creative_code_pr_promotion,
)
from scripts.orchestration.creative_code_patch_contract import (
    build_creative_code_patch_build_request,
    build_creative_code_patch_result,
)
from scripts.orchestration.creative_code_patch_builder import (
    CANDIDATE_PATCH_FILE,
    EXPERIMENT_PACKET_FILE,
    PATCH_METADATA_FILE,
    REQUEST_FILE,
    RESULT_FILE,
    SELECTED_VARIANT_FILE,
    SOURCE_BUNDLE_FILE,
)
from scripts.orchestration.creative_code_pr_promotion import CreativeCodePRPromotionError
from scripts.orchestration.creative_code_pr_promotion_contract import (
    CreativeCodePRPromotionContractError,
    build_creative_code_pr_promotion_approval,
    build_creative_code_pr_promotion_plan,
    build_creative_code_pr_promotion_receipt,
    build_creative_code_pr_promotion_validation as _build_validation_contract,
    promotion_plan_fingerprint,
    read_json_object,
    validate_creative_code_pr_promotion_approval,
    validate_creative_code_pr_promotion_plan,
    validate_creative_code_pr_promotion_receipt,
    validate_creative_code_pr_promotion_validation,
)
from scripts.orchestration.creative_code_specification import (
    read_creative_code_specification_bundle,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_BUNDLE = REPO_ROOT / "docs/orchestration/contracts/creative_code_specification.v1.json"
PLAN_SCHEMA = (
    REPO_ROOT / "docs/orchestration/contracts/creative_code_pr_promotion_plan.v1.schema.json"
)
VALIDATION_SCHEMA = (
    REPO_ROOT / "docs/orchestration/contracts/creative_code_pr_promotion_validation.v1.schema.json"
)
APPROVAL_SCHEMA = (
    REPO_ROOT / "docs/orchestration/contracts/creative_code_pr_promotion_approval.v1.schema.json"
)
RECEIPT_SCHEMA = (
    REPO_ROOT / "docs/orchestration/contracts/creative_code_pr_promotion_receipt.v1.schema.json"
)


def _reference_bundle() -> dict[str, Any]:
    return read_creative_code_specification_bundle(REFERENCE_BUNDLE)


def _reference_variant(bundle: dict[str, Any]) -> dict[str, Any]:
    selected_id = bundle["synthesis"]["selected_variant_id"]
    selected_fingerprint = bundle["synthesis"]["selected_variant_fingerprint"]
    for variant in bundle["variants"]:
        if (
            variant["variant_id"] == selected_id
            and variant["variant_fingerprint"] == selected_fingerprint
        ):
            return dict(variant)
    raise AssertionError("reference bundle selected variant missing")


def _candidate_patch() -> str:
    return """diff --git a/core/rag/orchestration.py b/core/rag/orchestration.py
index 8f11111..8f22222 100644
--- a/core/rag/orchestration.py
+++ b/core/rag/orchestration.py
@@ -1,2 +1,2 @@
 def value() -> int:
-    return 1
+    return 2
"""


def _request_for_base(base_sha: str) -> dict[str, Any]:
    return build_creative_code_patch_build_request(
        source_bundle=_reference_bundle(),
        base_commit_sha=base_sha,
        approval_ref="PR-3-test-approval",
        allowed_existing_paths=["core/rag/orchestration.py"],
        allowed_new_paths=[],
        oracle_commands=["pytest -q tests/test_creative_code_patch_builder.py"],
        metrics=["candidate patch remains reviewable after promotion"],
        budgets={
            "generation_attempts": 1,
            "generation_timeout_seconds": 60,
            "evaluation_timeout_seconds": 60,
            "max_changed_files": 3,
            "max_diff_lines": 200,
            "max_patch_bytes": 20000,
        },
    )


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def build_creative_code_pr_promotion_validation(**kwargs: Any) -> dict[str, Any]:
    """Build direct-evaluation validation evidence for synthetic contract fixtures."""

    return _build_validation_contract(
        **kwargs,
        oracle_evidence_source="direct_evaluation",
        oracle_executed_during_validation=True,
        oracle_result_fingerprint="sha256:" + ("a" * 64),
        experiment_packet_fingerprint="sha256:" + ("b" * 64),
        generation_gate_fingerprint=None,
        generation_receipt_fingerprint=None,
    )


def _patch_modules_to_repo(monkeypatch: pytest.MonkeyPatch, repo: Path) -> None:
    patch_root = repo / "artifacts" / "orchestration" / "creative_code" / "patch_runs"
    promotion_root = repo / "artifacts" / "orchestration" / "creative_code" / "promotions"
    creative_root = repo / "artifacts" / "orchestration" / "creative_code"
    monkeypatch.setattr(creative_code_patch_workspace, "REPO_ROOT", repo)
    monkeypatch.setattr(creative_code_patch_workspace, "ARTIFACT_ROOT", patch_root)
    monkeypatch.setattr(creative_code_patch_generation, "REPO_ROOT", repo)
    monkeypatch.setattr(creative_code_patch_generation, "CREATIVE_CODE_ROOT", creative_root)
    monkeypatch.setattr(
        creative_code_patch_generation,
        "PATCH_GENERATION_ROOT",
        creative_root / "patch_generation",
    )
    monkeypatch.setattr(creative_code_pr_promotion, "REPO_ROOT", repo)
    monkeypatch.setattr(creative_code_pr_promotion, "PROMOTION_ROOT", promotion_root)

    def fake_validate_finalized_dispatch_context(
        gate: dict[str, Any],
    ) -> tuple[Path, dict[str, Any]]:
        run_dir = patch_root / str(gate["run_id"])
        packet = json.loads((run_dir / EXPERIMENT_PACKET_FILE).read_text(encoding="utf-8"))
        return run_dir, packet

    monkeypatch.setattr(
        creative_code_patch_generation,
        "validate_finalized_dispatch_context",
        fake_validate_finalized_dispatch_context,
    )


def _generation_gate_fixture(
    *,
    request: dict[str, Any],
    bundle: dict[str, Any],
    run_id: str,
    run_ref: str,
) -> dict[str, Any]:
    allowed_paths = sorted(
        set(request["allowed_existing_paths"]) | set(request["allowed_new_paths"])
    )
    checks = {key: True for key in sorted(creative_code_patch_generation.GATE_CHECK_KEYS)}
    gate: dict[str, Any] = {
        "schema_version": creative_code_patch_generation.SCHEMA_VERSION,
        "artifact_type": creative_code_patch_generation.GATE_ARTIFACT_TYPE,
        "policy_version": creative_code_patch_generation.POLICY_VERSION,
        "gate_id": "pending",
        "idempotency_key": "pending",
        "admission_id": f"admission:{run_id}",
        "admission_fingerprint": fingerprint_payload({"admission": run_id}),
        "admission_ref": f"{run_ref}/admission.json",
        "request_id": request["request_id"],
        "request_fingerprint": fingerprint_payload(request),
        "request_ref": f"{run_ref}/{REQUEST_FILE}",
        "source_bundle_id": request["source_bundle_id"],
        "source_bundle_fingerprint": request["source_bundle_fingerprint"],
        "source_bundle_ref": f"{run_ref}/{SOURCE_BUNDLE_FILE}",
        "selected_variant_id": request["selected_variant_id"],
        "selected_variant_fingerprint": request["selected_variant_fingerprint"],
        "base_commit_sha": request["base_commit_sha"],
        "run_id": run_id,
        "state_fingerprint": fingerprint_payload({"run_id": run_id, "state": "prepared"}),
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
        "coordinator_advisory_hints_ref": None,
        "coordinator_advisory_hints_fingerprint": None,
        "checks": checks,
        "passed_checks": len(checks),
        "total_checks": len(checks),
        "next_action": "generate_candidate_then_evaluate_candidate",
        "authority": creative_code_patch_generation.default_generation_authority(),
        "sanitized": True,
    }
    creative_code_patch_generation._set_identity(
        gate,
        id_key="gate_id",
        asset_type=creative_code_patch_generation.GATE_ARTIFACT_TYPE,
    )
    return creative_code_patch_generation.validate_generation_gate(gate)


def _make_patch_run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    run_id: str = "patch-run",
    accepted: bool = True,
    generation_dir_name: str | None = None,
) -> tuple[Path, str, dict[str, Any]]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _patch_modules_to_repo(monkeypatch, repo)
    run_dir = patch_root = (
        repo / "artifacts" / "orchestration" / "creative_code" / "patch_runs" / run_id
    )
    patch_root.mkdir(parents=True)
    base_sha = "a" * 40
    request = _request_for_base(base_sha)
    bundle = _reference_bundle()
    variant = _reference_variant(bundle)
    patch_text = _candidate_patch()
    patch_fingerprint = fingerprint_payload({"candidate_patch": patch_text})
    experiment_packet = creative_code_patch_builder.build_pr2_experiment_packet(
        request=request,
        source_bundle=bundle,
        changed_paths=["core/rag/orchestration.py"],
        patch_fingerprint=patch_fingerprint,
    )
    runner_result = (
        _accepted_dispatch_fixture(experiment_packet)
        if accepted
        else {
            "experiment_id": experiment_packet["experiment_id"],
            "status": "rejected",
            "failure_class": "guard_failure",
            "mutated_paths": ["core/rag/orchestration.py"],
            "budget_observations": {
                "oracle_commands_configured": 1,
                "attempts": 1,
                "retries_consumed": 0,
            },
            "oracle_results": [],
            "shared_tree_untouched": True,
        }
    )
    result = build_creative_code_patch_result(
        request=request,
        changed_paths=["core/rag/orchestration.py"],
        patch_fingerprint=patch_fingerprint,
        patch_bytes=len(patch_text.encode("utf-8")),
        diff_lines=len(patch_text.splitlines()),
        runner_result=runner_result,
        checkout_destroyed=True,
        origin_removed=True,
        shared_tree_untouched=True,
        failure_class=None if accepted else "guard_failure",
    )
    _write_json(run_dir / REQUEST_FILE, request)
    _write_json(run_dir / SOURCE_BUNDLE_FILE, bundle)
    _write_json(run_dir / SELECTED_VARIANT_FILE, variant)
    _write_json(
        run_dir / PATCH_METADATA_FILE,
        {
            "changed_paths": ["core/rag/orchestration.py"],
            "changed_path_statuses": {"core/rag/orchestration.py": "M"},
            "patch_fingerprint": patch_fingerprint,
            "patch_bytes": len(patch_text.encode("utf-8")),
            "diff_lines": len(patch_text.splitlines()),
        },
    )
    _write_json(run_dir / RESULT_FILE, result)
    _write_json(run_dir / EXPERIMENT_PACKET_FILE, experiment_packet)
    (run_dir / CANDIDATE_PATCH_FILE).write_text(patch_text, encoding="utf-8")
    if accepted:
        generation_dir = creative_code_patch_generation.PATCH_GENERATION_ROOT / (
            generation_dir_name or run_id
        )
        gate_path = generation_dir / creative_code_patch_generation.GATE_FILENAME
        run_ref = run_dir.relative_to(repo).as_posix()
        gate = _generation_gate_fixture(
            request=request,
            bundle=bundle,
            run_id=run_id,
            run_ref=run_ref,
        )
        _write_json(gate_path, gate)
        receipt = creative_code_patch_generation._build_receipt(
            gate_path=gate_path,
            gate=gate,
            result=result,
        )
        _write_json(
            generation_dir / creative_code_patch_generation.RECEIPT_FILENAME,
            receipt,
        )
    return repo, run_id, result


def _generation_receipt_path(
    repo: Path,
    run_id: str,
    *,
    generation_dir_name: str | None = None,
) -> Path:
    return (
        repo
        / "artifacts"
        / "orchestration"
        / "creative_code"
        / "patch_generation"
        / (generation_dir_name or run_id)
        / creative_code_patch_generation.RECEIPT_FILENAME
    )


def _accepted_dispatch_fixture(packet: dict[str, Any]) -> dict[str, Any]:
    commands = [oracle["command"] for oracle in packet["immutable_oracles"]]
    return {
        "schema_version": "1.0",
        "experiment_id": packet["experiment_id"],
        "runner_mode": "candidate_patch",
        "candidate_patch": ".experiment-runner-input/candidate.patch",
        "candidate_patch_fingerprint": packet["candidate_patch_fingerprint"],
        "status": "accepted",
        "failure_class": None,
        "mutated_paths": list(packet["mutable_candidate_surface"]),
        "oracle_results": [
            {
                "command": command,
                "returncode": 0,
                "timed_out": False,
                "truncated": False,
                "stdout": "",
                "stderr": "",
                "cwd": "/workspace",
            }
            for command in commands
        ],
        "budget_observations": {
            "configured_budgets": dict(packet["budgets"]),
            "oracle_commands_configured": len(commands),
            "oracle_commands_executed": len(commands),
            "candidate_changed_files": len(packet["mutable_candidate_surface"]),
            "source_checkout_head_sha": packet["base_commit_sha"],
            "source_checkout_clean": True,
            "attempts": 1,
            "retries_consumed": 0,
        },
        "shared_tree_untouched": True,
        "promotion_ready": False,
        "contribution_kind": "none",
        "coauthor_required": False,
        "coauthor_reason": "",
        "execution_backend": {
            "name": "apple-container",
            "guest_platform": "linux_arm64",
            "runtime_version": "1.1.0",
            "image_digest": "sha256:" + ("a" * 64),
            "network_isolation": "apple_internal_no_dns_plus_linux_unshare",
            "preflight_status": "passed",
        },
    }


def _write_dispatch_fixture(
    repo: Path,
    run_id: str,
    *,
    result: dict[str, Any] | None = None,
) -> tuple[Path, dict[str, Any]]:
    run_dir = repo / "artifacts" / "orchestration" / "creative_code" / "patch_runs" / run_id
    packet = json.loads((run_dir / EXPERIMENT_PACKET_FILE).read_text(encoding="utf-8"))
    dispatch_result = result or _accepted_dispatch_fixture(packet)
    result_path = (
        repo / "artifacts" / "orchestration" / "experiments" / "results" / f"{run_id}.json"
    )
    _write_json(result_path, dispatch_result)
    return result_path, packet


class FakeGit:
    def __init__(
        self,
        base_sha: str = "a" * 40,
        *,
        remote_exists: bool = False,
        remote_exists_sequence: list[bool] | None = None,
        identity: tuple[str, str] | None = ("Katsiarynakavaleuskaya", "human@example.test"),
        verify_identity_failure: bool = False,
    ) -> None:
        self.base_sha = base_sha
        self.remote_exists = remote_exists
        self.remote_exists_sequence = list(remote_exists_sequence or [])
        self.identity = identity
        self.verify_identity_failure = verify_identity_failure
        self.committed = False
        self.calls: list[list[str]] = []

    def rev_parse_origin_main(self) -> str:
        return self.base_sha

    def shared_status(self) -> str:
        return ""

    def remote_branch_exists(self, branch: str) -> bool:
        self.calls.append(["remote_branch_exists", branch])
        if self.remote_exists_sequence:
            return self.remote_exists_sequence.pop(0)
        return self.remote_exists

    def local_branch_exists(self, branch: str, *, cwd: Path = REPO_ROOT) -> bool:
        self.calls.append(["local_branch_exists", branch])
        return False

    def remote_url(self) -> str:
        return "git@github.com:Katsiarynakavaleuskaya/PulsePlate.git"

    def human_identity(self) -> tuple[str, str]:
        self.calls.append(["human_identity"])
        if self.identity is None:
            raise CreativeCodePRPromotionError("human git identity is not configured.")
        creative_code_pr_promotion._reject_non_human_git_identity(
            name=self.identity[0],
            email=self.identity[1],
        )
        return self.identity

    def verify_commit_identity(
        self,
        *,
        cwd: Path,
        expected_name: str,
        expected_email: str,
    ) -> None:
        self.calls.append(["verify_commit_identity", expected_name, expected_email])
        if self.verify_identity_failure:
            raise CreativeCodePRPromotionError("promotion commit identity mismatch.")
        if self.identity != (expected_name, expected_email):
            raise CreativeCodePRPromotionError("promotion commit identity mismatch.")

    def push_upload_branch(self, *, cwd: Path, branch: str) -> None:
        self.calls.append(["push_upload_branch", branch])
        if self.remote_exists:
            raise CreativeCodePRPromotionError("target experiment branch already exists.")

    def run(
        self,
        args: list[str],
        *,
        cwd: Path,
        input_text: str | None = None,
        check: bool = True,
        timeout_seconds: int = 600,
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(args))
        stdout = ""
        if args[:2] == ["rev-parse", "HEAD"]:
            stdout = ("b" * 40 if self.committed else self.base_sha) + "\n"
        elif args[:2] == ["rev-parse", "origin/main"]:
            stdout = self.base_sha + "\n"
        elif args[:2] == ["status", "--porcelain=v1"]:
            stdout = ""
        elif args[:2] == ["diff", "--cached"]:
            stdout = "core/rag/orchestration.py\n"
        elif args[:2] == ["diff", "--binary"]:
            stdout = _candidate_patch()
        elif "commit" in args:
            self.committed = True
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=stdout, stderr="")


class FakeGates:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def run_fresh_oracle(self, *, experiment_packet: Path, candidate_patch: Path) -> dict[str, Any]:
        self.calls.append("fresh_oracle")
        return {
            "status": "accepted",
            "failure_class": None,
            "mutated_paths": ["core/rag/orchestration.py"],
            "budget_observations": {
                "oracle_commands_configured": 1,
                "oracle_commands_executed": 1,
            },
            "shared_tree_untouched": True,
        }

    def run_pre_commit(self, *, cwd: Path) -> None:
        self.calls.append("pre_commit")

    def run_validate_changed(self, *, cwd: Path) -> None:
        self.calls.append("validate_changed")


def _stub_validation_checkout(
    monkeypatch: pytest.MonkeyPatch,
    promotion_dir: Path,
) -> Path:
    def fake_prepare(**kwargs: Any) -> Path:
        checkout = promotion_dir / kwargs["dirname"]
        checkout.mkdir()
        return checkout

    monkeypatch.setattr(creative_code_pr_promotion, "_prepare_checkout", fake_prepare)
    monkeypatch.setattr(
        creative_code_pr_promotion,
        "_apply_patch_and_verify",
        lambda **_: None,
    )
    monkeypatch.setattr(
        creative_code_pr_promotion,
        "_ensure_patch_unchanged_after_gates",
        lambda **_: None,
    )
    return promotion_dir / creative_code_pr_promotion.VALIDATION_CHECKOUT


class FakeTTY:
    def __init__(self, text: str, *, tty: bool = True) -> None:
        self.text = text
        self.tty = tty

    def isatty(self) -> bool:
        return self.tty

    def readline(self) -> str:
        return self.text


class FakeStdout:
    def __init__(self, *, tty: bool = True) -> None:
        self.tty = tty
        self.lines: list[str] = []

    def isatty(self) -> bool:
        return self.tty

    def write(self, text: str) -> int:
        self.lines.append(text)
        return len(text)

    def flush(self) -> None:
        return None


class FakeGitHub:
    def __init__(self, *, login: str = "Katsiarynakavaleuskaya") -> None:
        self.login = login
        self.calls: list[list[str]] = []
        self.head_branch = ""
        self.created_refs: list[tuple[str, str]] = []
        self.deleted_refs: list[str] = []

    def current_login(self) -> str:
        self.calls.append(["api", "user"])
        return self.login

    def create_branch_ref(self, *, branch: str, commit_sha: str) -> None:
        self.calls.append(["api", "create-ref", branch, commit_sha])
        self.created_refs.append((branch, commit_sha))

    def delete_branch_ref(self, *, branch: str) -> bool:
        self.calls.append(["api", "delete-ref", branch])
        self.deleted_refs.append(branch)
        return True

    def create_pull_request(self, *, head_branch: str, title: str, body_file: Path) -> str:
        self.calls.append(["pr", "create", "--head", head_branch, "--title", title])
        assert "--draft" not in self.calls[-1]
        self.head_branch = head_branch
        return "https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/9999"

    def read_pull_request(self, *, pr_ref: str) -> dict[str, Any]:
        self.calls.append(["pr", "view", pr_ref])
        return {
            "number": 9999,
            "url": pr_ref,
            "state": "OPEN",
            "isDraft": False,
            "baseRefName": "main",
            "headRefName": self.head_branch,
            "headRefOid": "b" * 40,
        }


class FailingCreateRefGitHub(FakeGitHub):
    def create_branch_ref(self, *, branch: str, commit_sha: str) -> None:
        super().create_branch_ref(branch=branch, commit_sha=commit_sha)
        raise CreativeCodePRPromotionError("target ref already exists")


class AmbiguousUploadGit(FakeGit):
    def push_upload_branch(self, *, cwd: Path, branch: str) -> None:
        self.calls.append(["push_upload_branch", branch])
        raise creative_code_pr_promotion.TemporaryUploadBranchAmbiguousError(
            "temporary upload push did not create a new branch; cleanup required."
        )


class TimeoutUploadGit(FakeGit):
    def push_upload_branch(self, *, cwd: Path, branch: str) -> None:
        self.calls.append(["push_upload_branch", branch])
        raise subprocess.TimeoutExpired(cmd="git push", timeout=600)


class TimeoutDeleteGitHub(FakeGitHub):
    def delete_branch_ref(self, *, branch: str) -> bool:
        self.calls.append(["api", "delete-ref", branch])
        self.deleted_refs.append(branch)
        raise subprocess.TimeoutExpired(cmd="gh api delete", timeout=120)


def _write_ready_promotion_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    promotion_id: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], Path]:
    _repo, run_id, _result = _make_patch_run(monkeypatch, tmp_path)
    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id=promotion_id,
        git=FakeGit(),
    )
    plan = planned["plan"]
    validation = build_creative_code_pr_promotion_validation(
        promotion_id=promotion_id,
        plan_fingerprint=promotion_plan_fingerprint(plan),
        patch_fingerprint=plan["patch_fingerprint"],
        base_commit_sha=plan["base_commit_sha"],
        oracle_commands_configured=1,
        oracle_commands_executed=1,
    )
    approval = build_creative_code_pr_promotion_approval(
        promotion_id=promotion_id,
        plan_fingerprint=promotion_plan_fingerprint(plan),
        validation_fingerprint=validation["validation_fingerprint"],
        approved_by_login="Katsiarynakavaleuskaya",
        confirmed_patch_fingerprint=plan["patch_fingerprint"],
        confirmed_base_commit_sha=plan["base_commit_sha"],
        confirmed_target_branch=plan["target_head_branch"],
    )
    promotion_dir = Path(planned["promotion_dir"])
    _write_json(promotion_dir / creative_code_pr_promotion.VALIDATION_FILE, validation)
    _write_json(promotion_dir / creative_code_pr_promotion.APPROVAL_FILE, approval)
    return plan, validation, approval, promotion_dir


def test_pr3_schemas_are_closed() -> None:
    for schema_path in (PLAN_SCHEMA, VALIDATION_SCHEMA, APPROVAL_SCHEMA, RECEIPT_SCHEMA):
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        assert schema["additionalProperties"] is False

    plan_schema = json.loads(PLAN_SCHEMA.read_text(encoding="utf-8"))
    assert plan_schema["properties"]["pull_request_mode"]["const"] == "non_draft"
    assert (
        plan_schema["$defs"]["authority"]["properties"]["open_non_draft_pull_request"]["const"]
        is True
    )
    assert (
        plan_schema["$defs"]["authority"]["properties"]["open_draft_pull_request"]["const"] is False
    )
    assert plan_schema["$defs"]["authority"]["properties"]["merge"]["const"] is False
    receipt_schema = json.loads(RECEIPT_SCHEMA.read_text(encoding="utf-8"))
    open_receipt_properties = receipt_schema["allOf"][0]["then"]["properties"]
    assert open_receipt_properties["pull_request_number"]["minimum"] == 1
    assert open_receipt_properties["review_cycle_started"]["const"] is True
    assert open_receipt_properties["partial_failure"]["type"] == "null"
    validation_schema = json.loads(VALIDATION_SCHEMA.read_text(encoding="utf-8"))
    oracle_evidence = validation_schema["$defs"]["oracle_evidence"]
    assert oracle_evidence["properties"]["source"]["enum"] == [
        "direct_evaluation",
        "trusted_apple_dispatch",
    ]


def test_open_promotion_receipt_requires_pr_identity() -> None:
    with pytest.raises(
        CreativeCodePRPromotionContractError,
        match="open receipts require pull_request_number and pull_request_url",
    ):
        build_creative_code_pr_promotion_receipt(
            promotion_id="promotion-pr3-open-receipt",
            plan_fingerprint="sha256:" + "1" * 64,
            validation_fingerprint="sha256:" + "2" * 64,
            approval_id="evidence:approval",
            source_result_id="evidence:result",
            patch_fingerprint="sha256:" + "3" * 64,
            head_branch="experiment/open-receipt",
            commit_sha="b" * 40,
            pull_request_number=0,
            pull_request_url="",
            approved_by_login="Katsiarynakavaleuskaya",
        )


def test_valid_artifacts_round_trip_and_identity_drifts() -> None:
    plan = build_creative_code_pr_promotion_plan(
        promotion_id="promotion-pr3-test",
        source_result_id="evidence:result",
        source_request_id="evidence:request",
        source_bundle_id="evidence:bundle",
        source_bundle_fingerprint="sha256:" + "1" * 64,
        selected_variant_id="candidate:variant",
        selected_variant_fingerprint="sha256:" + "2" * 64,
        patch_fingerprint="sha256:" + "3" * 64,
        base_commit_sha="a" * 40,
        changed_paths=["core/rag/orchestration.py"],
        target_head_branch="experiment/variant-33333333",
        pull_request_title="experiment: variant",
        pull_request_body_fingerprint="sha256:" + "4" * 64,
    )
    validated = validate_creative_code_pr_promotion_plan(plan)
    assert validated == plan
    original_fingerprint = promotion_plan_fingerprint(plan)
    changed = dict(plan)
    changed["pull_request_title"] = "experiment: other"
    with pytest.raises(CreativeCodePRPromotionContractError, match="idempotency_key"):
        validate_creative_code_pr_promotion_plan(changed)
    assert promotion_plan_fingerprint(changed) != original_fingerprint

    validation = build_creative_code_pr_promotion_validation(
        promotion_id="promotion-pr3-test",
        plan_fingerprint=original_fingerprint,
        patch_fingerprint=plan["patch_fingerprint"],
        base_commit_sha=plan["base_commit_sha"],
        oracle_commands_configured=1,
        oracle_commands_executed=1,
    )
    assert validate_creative_code_pr_promotion_validation(validation) == validation
    approval = build_creative_code_pr_promotion_approval(
        promotion_id="promotion-pr3-test",
        plan_fingerprint=original_fingerprint,
        validation_fingerprint=validation["validation_fingerprint"],
        approved_by_login="Katsiarynakavaleuskaya",
        confirmed_patch_fingerprint=plan["patch_fingerprint"],
        confirmed_base_commit_sha=plan["base_commit_sha"],
        confirmed_target_branch=plan["target_head_branch"],
    )
    assert validate_creative_code_pr_promotion_approval(approval) == approval
    receipt = build_creative_code_pr_promotion_receipt(
        promotion_id="promotion-pr3-test",
        plan_fingerprint=original_fingerprint,
        validation_fingerprint=validation["validation_fingerprint"],
        approval_id=approval["approval_id"],
        source_result_id=plan["source_result_id"],
        patch_fingerprint=plan["patch_fingerprint"],
        head_branch=plan["target_head_branch"],
        commit_sha="b" * 40,
        pull_request_number=9999,
        pull_request_url="https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/9999",
        approved_by_login="Katsiarynakavaleuskaya",
    )
    assert validate_creative_code_pr_promotion_receipt(receipt) == receipt


def test_validation_contract_distinguishes_trusted_apple_dispatch() -> None:
    validation = _build_validation_contract(
        promotion_id="promotion-pr3-trusted-contract",
        plan_fingerprint="sha256:" + ("1" * 64),
        patch_fingerprint="sha256:" + ("2" * 64),
        base_commit_sha="a" * 40,
        oracle_commands_configured=1,
        oracle_commands_executed=1,
        oracle_evidence_source="trusted_apple_dispatch",
        oracle_executed_during_validation=False,
        oracle_result_fingerprint="sha256:" + ("3" * 64),
        experiment_packet_fingerprint="sha256:" + ("4" * 64),
        generation_gate_fingerprint="sha256:" + ("5" * 64),
        generation_receipt_fingerprint="sha256:" + ("6" * 64),
    )

    assert validation["oracle_evidence"]["source"] == "trusted_apple_dispatch"
    assert validation["oracle_evidence"]["executed_during_validation"] is False
    forged = json.loads(json.dumps(validation))
    forged["oracle_evidence"]["executed_during_validation"] = True
    with pytest.raises(
        CreativeCodePRPromotionContractError,
        match="without claiming execution during validation",
    ):
        validate_creative_code_pr_promotion_validation(forged)


def test_duplicate_json_keys_rejected(tmp_path: Path) -> None:
    duplicate = tmp_path / "plan.json"
    duplicate.write_text('{"schema_version":"1.0","schema_version":"1.0"}', encoding="utf-8")

    with pytest.raises(CreativeCodePRPromotionContractError, match="duplicate JSON key"):
        read_json_object(duplicate)


def test_promotion_state_rejects_duplicate_json_keys(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _patch_modules_to_repo(monkeypatch, repo)
    promotion_dir = creative_code_pr_promotion.resolve_promotion_dir("duplicate-state", create=True)
    state_path = promotion_dir / "promotion_state.json"
    state_path.write_text('{"schema_version":"1.0","schema_version":"1.0"}', encoding="utf-8")

    with pytest.raises(
        creative_code_patch_workspace.CreativeCodePatchWorkspaceError,
        match="duplicate key",
    ):
        creative_code_pr_promotion._load_state(promotion_dir)


def test_bool_like_strings_and_unknown_fields_rejected() -> None:
    plan = build_creative_code_pr_promotion_plan(
        promotion_id="promotion-pr3-test",
        source_result_id="evidence:result",
        source_request_id="evidence:request",
        source_bundle_id="evidence:bundle",
        source_bundle_fingerprint="sha256:" + "1" * 64,
        selected_variant_id="candidate:variant",
        selected_variant_fingerprint="sha256:" + "2" * 64,
        patch_fingerprint="sha256:" + "3" * 64,
        base_commit_sha="a" * 40,
        changed_paths=["core/rag/orchestration.py"],
        target_head_branch="experiment/variant-33333333",
        pull_request_title="experiment: variant",
        pull_request_body_fingerprint="sha256:" + "4" * 64,
    )
    with_extra = dict(plan)
    with_extra["extra"] = True
    with pytest.raises(CreativeCodePRPromotionContractError, match="unsupported fields"):
        validate_creative_code_pr_promotion_plan(with_extra)

    bad_bool = dict(plan)
    bad_bool["authority"] = dict(plan["authority"])
    bad_bool["authority"]["open_draft_pull_request"] = "false"
    with pytest.raises(CreativeCodePRPromotionContractError, match="open_draft_pull_request"):
        validate_creative_code_pr_promotion_plan(bad_bool)


def test_plan_accepts_only_accepted_pr2_result(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo, run_id, _result = _make_patch_run(monkeypatch, tmp_path, accepted=False)

    with pytest.raises(CreativeCodePRPromotionError, match="PR-2 result must be accepted"):
        creative_code_pr_promotion.plan(
            patch_run=run_id,
            promotion_id="promotion-pr3-test",
            git=FakeGit(),
        )


def test_plan_rejects_patch_metadata_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, run_id, _result = _make_patch_run(monkeypatch, tmp_path)
    metadata_path = (
        repo
        / "artifacts"
        / "orchestration"
        / "creative_code"
        / "patch_runs"
        / run_id
        / PATCH_METADATA_FILE
    )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["changed_paths"] = ["core/rag/other.py"]
    _write_json(metadata_path, metadata)

    with pytest.raises(CreativeCodePRPromotionError, match="changed_path_statuses"):
        creative_code_pr_promotion.plan(
            patch_run=run_id,
            promotion_id="promotion-pr3-metadata",
            git=FakeGit(),
        )


def test_plan_rejects_patch_metadata_status_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, run_id, _result = _make_patch_run(monkeypatch, tmp_path)
    metadata_path = (
        repo
        / "artifacts"
        / "orchestration"
        / "creative_code"
        / "patch_runs"
        / run_id
        / PATCH_METADATA_FILE
    )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["changed_path_statuses"]["core/rag/orchestration.py"] = "A"
    _write_json(metadata_path, metadata)

    with pytest.raises(CreativeCodePRPromotionError, match="changed_path_statuses"):
        creative_code_pr_promotion.plan(
            patch_run=run_id,
            promotion_id="promotion-pr3-status-metadata",
            git=FakeGit(),
        )


def test_plan_rejects_patch_metadata_extra_unsafe_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, run_id, _result = _make_patch_run(monkeypatch, tmp_path)
    metadata_path = (
        repo
        / "artifacts"
        / "orchestration"
        / "creative_code"
        / "patch_runs"
        / run_id
        / PATCH_METADATA_FILE
    )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["raw_prompt"] = "/Users/example diff --git Authorization: Bearer ghp_secret"
    _write_json(metadata_path, metadata)

    with pytest.raises(CreativeCodePRPromotionError, match="unsupported fields"):
        creative_code_pr_promotion.plan(
            patch_run=run_id,
            promotion_id="promotion-pr3-metadata-extra",
            git=FakeGit(),
        )


def test_plan_rejects_patch_metadata_allowed_unsafe_field(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, run_id, _result = _make_patch_run(monkeypatch, tmp_path)
    metadata_path = (
        repo
        / "artifacts"
        / "orchestration"
        / "creative_code"
        / "patch_runs"
        / run_id
        / PATCH_METADATA_FILE
    )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    unsafe_path = "core/ghs_secretsecretsecret.py"
    metadata["changed_paths"] = [unsafe_path]
    metadata["changed_path_statuses"] = {unsafe_path: "A"}
    _write_json(metadata_path, metadata)

    with pytest.raises(CreativeCodePRPromotionError, match="unsafe result text") as exc_info:
        creative_code_pr_promotion.plan(
            patch_run=run_id,
            promotion_id="promotion-pr3-metadata-allowed-unsafe-field",
            git=FakeGit(),
        )
    assert "ghs_secretsecretsecret" not in str(exc_info.value)


def test_plan_rejects_patch_metadata_extra_unsafe_key_without_echoing_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, run_id, _result = _make_patch_run(monkeypatch, tmp_path)
    metadata_path = (
        repo
        / "artifacts"
        / "orchestration"
        / "creative_code"
        / "patch_runs"
        / run_id
        / PATCH_METADATA_FILE
    )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    unsafe_key = "GH_TOKEN=ghs_secretsecretsecret"
    metadata[unsafe_key] = "ignored"
    _write_json(metadata_path, metadata)

    with pytest.raises(CreativeCodePRPromotionError, match="unsupported fields") as exc_info:
        creative_code_pr_promotion.plan(
            patch_run=run_id,
            promotion_id="promotion-pr3-metadata-extra-key",
            git=FakeGit(),
        )
    assert unsafe_key not in str(exc_info.value)
    assert "GH_TOKEN" not in str(exc_info.value)


def test_plan_rejects_patch_changed_paths_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, run_id, _result = _make_patch_run(monkeypatch, tmp_path)
    run_dir = repo / "artifacts" / "orchestration" / "creative_code" / "patch_runs" / run_id
    changed_patch = _candidate_patch().replace("core/rag/orchestration.py", "core/rag/other.py")
    changed_fingerprint = fingerprint_payload({"candidate_patch": changed_patch})
    request = json.loads((run_dir / REQUEST_FILE).read_text(encoding="utf-8"))
    runner_result = {
        "experiment_id": "exp-pr3-reference",
        "status": "accepted",
        "failure_class": None,
        "mutated_paths": ["core/rag/orchestration.py"],
        "budget_observations": {
            "oracle_commands_configured": 1,
            "attempts": 1,
            "retries_consumed": 0,
        },
        "oracle_results": [{"status": "passed"}],
        "shared_tree_untouched": True,
    }
    result = build_creative_code_patch_result(
        request=request,
        changed_paths=["core/rag/orchestration.py"],
        patch_fingerprint=changed_fingerprint,
        patch_bytes=len(changed_patch.encode("utf-8")),
        diff_lines=len(changed_patch.splitlines()),
        runner_result=runner_result,
        checkout_destroyed=True,
        origin_removed=True,
        shared_tree_untouched=True,
        failure_class=None,
    )
    _write_json(run_dir / RESULT_FILE, result)
    _write_json(
        run_dir / PATCH_METADATA_FILE,
        {
            "changed_paths": ["core/rag/orchestration.py"],
            "patch_fingerprint": changed_fingerprint,
            "patch_bytes": len(changed_patch.encode("utf-8")),
            "diff_lines": len(changed_patch.splitlines()),
        },
    )
    (run_dir / CANDIDATE_PATCH_FILE).write_text(changed_patch, encoding="utf-8")

    with pytest.raises(CreativeCodePRPromotionError, match="changed paths mismatch"):
        creative_code_pr_promotion.plan(
            patch_run=run_id,
            promotion_id="promotion-pr3-path-mismatch",
            git=FakeGit(),
        )


def test_plan_rejects_patch_paths_outside_request_allowlist(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, run_id, _result = _make_patch_run(monkeypatch, tmp_path)
    run_dir = repo / "artifacts" / "orchestration" / "creative_code" / "patch_runs" / run_id
    patch_text = _candidate_patch().replace("core/rag/orchestration.py", "core/rag/other.py")
    patch_fingerprint = fingerprint_payload({"candidate_patch": patch_text})
    request = json.loads((run_dir / REQUEST_FILE).read_text(encoding="utf-8"))
    result = build_creative_code_patch_result(
        request=request,
        changed_paths=["core/rag/other.py"],
        patch_fingerprint=patch_fingerprint,
        patch_bytes=len(patch_text.encode("utf-8")),
        diff_lines=len(patch_text.splitlines()),
        runner_result={
            "experiment_id": "exp-pr3-reference",
            "status": "accepted",
            "failure_class": None,
            "mutated_paths": ["core/rag/other.py"],
            "budget_observations": {
                "oracle_commands_configured": 1,
                "attempts": 1,
                "retries_consumed": 0,
            },
            "oracle_results": [{"status": "passed"}],
            "shared_tree_untouched": True,
        },
        checkout_destroyed=True,
        origin_removed=True,
        shared_tree_untouched=True,
        failure_class=None,
    )
    _write_json(run_dir / RESULT_FILE, result)
    _write_json(
        run_dir / PATCH_METADATA_FILE,
        {
            "changed_paths": ["core/rag/other.py"],
            "changed_path_statuses": {"core/rag/other.py": "M"},
            "patch_fingerprint": patch_fingerprint,
            "patch_bytes": len(patch_text.encode("utf-8")),
            "diff_lines": len(patch_text.splitlines()),
        },
    )
    (run_dir / CANDIDATE_PATCH_FILE).write_text(patch_text, encoding="utf-8")

    with pytest.raises(CreativeCodePRPromotionError, match="outside PR-2 request allowlist"):
        creative_code_pr_promotion.plan(
            patch_run=run_id,
            promotion_id="promotion-pr3-outside-allowlist",
            git=FakeGit(),
        )


def test_plan_writes_non_draft_artifact_and_rejects_existing_branch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _repo, run_id, result = _make_patch_run(monkeypatch, tmp_path)

    with pytest.raises(CreativeCodePRPromotionError, match="already exists"):
        creative_code_pr_promotion.plan(
            patch_run=run_id,
            promotion_id="promotion-pr3-test",
            git=FakeGit(remote_exists=True),
        )

    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id="promotion-pr3-ok",
        git=FakeGit(),
    )

    plan = planned["plan"]
    assert plan["pull_request_mode"] == "non_draft"
    assert plan["authority"]["open_non_draft_pull_request"] is True
    assert plan["authority"]["open_draft_pull_request"] is False
    assert plan["target_head_branch"].startswith("experiment/")
    body = (Path(planned["promotion_dir"]) / creative_code_pr_promotion.PR_BODY_FILE).read_text(
        encoding="utf-8"
    )
    assert result["patch_summary"]["patch_fingerprint"] in body
    assert "Merge readiness is not claimed." in body
    assert "diff --git" not in body
    assert "raw prompt" not in body.lower()
    assert "/Users/" not in body


def test_validation_uses_isolated_checkout_and_destroyed_on_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _repo, run_id, _result = _make_patch_run(monkeypatch, tmp_path)
    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id="promotion-pr3-validate",
        git=FakeGit(),
    )
    calls: list[str] = []

    def fake_prepare(**kwargs: Any) -> Path:
        calls.append(f"prepare:{kwargs['dirname']}")
        checkout = Path(planned["promotion_dir"]) / kwargs["dirname"]
        checkout.mkdir()
        return checkout

    def fake_apply(**kwargs: Any) -> None:
        calls.append("apply")

    def fake_patch_unchanged(**kwargs: Any) -> None:
        calls.append("patch_unchanged")

    def fake_destroy(_promotion_dir: Path, dirname: str) -> bool:
        calls.append(f"destroy:{dirname}")
        return True

    monkeypatch.setattr(creative_code_pr_promotion, "_prepare_checkout", fake_prepare)
    monkeypatch.setattr(creative_code_pr_promotion, "_apply_patch_and_verify", fake_apply)
    monkeypatch.setattr(
        creative_code_pr_promotion,
        "_ensure_patch_unchanged_after_gates",
        fake_patch_unchanged,
    )
    monkeypatch.setattr(creative_code_pr_promotion, "_destroy_checkout", fake_destroy)

    gates = FakeGates()
    validation = creative_code_pr_promotion.validate(
        promotion_id="promotion-pr3-validate",
        git=FakeGit(),
        gate_runner=gates,
    )

    assert validation["preopen_gates"]["pre_commit"] == "passed"
    assert validation["validation_checkout"]["used_throwaway_commit"] is True
    assert validation["oracle_evidence"]["source"] == "direct_evaluation"
    assert validation["oracle_evidence"]["executed_during_validation"] is True
    assert gates.calls == ["fresh_oracle", "pre_commit", "validate_changed"]
    assert calls == [
        "prepare:validation_checkout",
        "apply",
        "patch_unchanged",
        "destroy:validation_checkout",
    ]


def test_validation_accepts_exact_trusted_apple_dispatch_without_direct_evaluation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, run_id, _result = _make_patch_run(monkeypatch, tmp_path)
    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id="promotion-pr3-trusted-apple",
        git=FakeGit(),
    )
    result_path, packet = _write_dispatch_fixture(repo, run_id)
    _stub_validation_checkout(monkeypatch, Path(planned["promotion_dir"]))
    gates = FakeGates()

    validation = creative_code_pr_promotion.validate(
        promotion_id="promotion-pr3-trusted-apple",
        trusted_dispatch_result=result_path.relative_to(repo),
        trusted_generation_receipt=_generation_receipt_path(repo, run_id).relative_to(repo),
        git=FakeGit(),
        gate_runner=gates,
    )

    assert validation["oracle_evidence"]["oracle_commands_configured"] == len(
        packet["immutable_oracles"]
    )
    assert validation["oracle_evidence"]["oracle_commands_executed"] == len(
        packet["immutable_oracles"]
    )
    assert validation["oracle_evidence"]["source"] == "trusted_apple_dispatch"
    assert validation["oracle_evidence"]["executed_during_validation"] is False
    assert validation["oracle_evidence"]["generation_gate_fingerprint"] is not None
    assert validation["oracle_evidence"]["generation_receipt_fingerprint"] is not None
    assert gates.calls == ["pre_commit", "validate_changed"]


def test_validation_rejects_direct_packet_drift_during_gates(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, run_id, _result = _make_patch_run(
        monkeypatch,
        tmp_path,
        run_id="patch-run-direct-packet-drift",
    )
    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id="promotion-pr3-direct-packet-drift",
        git=FakeGit(),
    )
    run_dir = repo / "artifacts" / "orchestration" / "creative_code" / "patch_runs" / run_id
    packet_path = run_dir / EXPERIMENT_PACKET_FILE
    promotion_dir = Path(planned["promotion_dir"])
    checkout = _stub_validation_checkout(monkeypatch, promotion_dir)

    class MutatingGates(FakeGates):
        def run_pre_commit(self, *, cwd: Path) -> None:
            super().run_pre_commit(cwd=cwd)
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            packet["immutable_oracles"][0][
                "command"
            ] = "pytest -q tests/test_creative_code_patch_generation.py"
            _write_json(packet_path, packet)

    with pytest.raises(
        CreativeCodePRPromotionError,
        match="direct oracle experiment packet changed during validation",
    ):
        creative_code_pr_promotion.validate(
            promotion_id="promotion-pr3-direct-packet-drift",
            git=FakeGit(),
            gate_runner=MutatingGates(),
        )

    assert not checkout.exists()
    assert not (promotion_dir / creative_code_pr_promotion.VALIDATION_FILE).exists()


def test_validation_accepts_explicit_custom_generation_receipt_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    generation_dir_name = "custom-generation-output"
    repo, run_id, _result = _make_patch_run(
        monkeypatch,
        tmp_path,
        run_id="patch-run-custom-generation",
        generation_dir_name=generation_dir_name,
    )
    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id="promotion-pr3-custom-generation",
        git=FakeGit(),
    )
    result_path, _packet = _write_dispatch_fixture(repo, run_id)
    receipt_path = _generation_receipt_path(
        repo,
        run_id,
        generation_dir_name=generation_dir_name,
    )
    assert not _generation_receipt_path(repo, run_id).exists()
    _stub_validation_checkout(monkeypatch, Path(planned["promotion_dir"]))
    gates = FakeGates()

    creative_code_pr_promotion.validate(
        promotion_id="promotion-pr3-custom-generation",
        trusted_dispatch_result=result_path.relative_to(repo),
        trusted_generation_receipt=receipt_path.relative_to(repo),
        git=FakeGit(),
        gate_runner=gates,
    )

    assert gates.calls == ["pre_commit", "validate_changed"]


@pytest.mark.parametrize("provided_argument", ["dispatch", "receipt"])
def test_validation_rejects_unpaired_trusted_evidence_before_checkout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    provided_argument: str,
) -> None:
    repo, run_id, _result = _make_patch_run(
        monkeypatch,
        tmp_path,
        run_id=f"patch-run-unpaired-{provided_argument}",
    )
    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id=f"promotion-pr3-unpaired-{provided_argument}",
        git=FakeGit(),
    )
    result_path, _packet = _write_dispatch_fixture(repo, run_id)
    kwargs: dict[str, Any] = {
        (
            "trusted_dispatch_result"
            if provided_argument == "dispatch"
            else "trusted_generation_receipt"
        ): (
            result_path
            if provided_argument == "dispatch"
            else _generation_receipt_path(repo, run_id)
        )
    }
    prepare_calls: list[str] = []

    def fail_prepare(**_kwargs: Any) -> Path:
        prepare_calls.append("prepare")
        raise AssertionError("checkout must not be prepared")

    monkeypatch.setattr(creative_code_pr_promotion, "_prepare_checkout", fail_prepare)

    with pytest.raises(CreativeCodePRPromotionError, match="must be supplied together"):
        creative_code_pr_promotion.validate(
            promotion_id=f"promotion-pr3-unpaired-{provided_argument}",
            git=FakeGit(),
            gate_runner=FakeGates(),
            **kwargs,
        )

    promotion_dir = Path(planned["promotion_dir"])
    assert prepare_calls == []
    assert not (promotion_dir / creative_code_pr_promotion.VALIDATION_CHECKOUT).exists()
    assert not (promotion_dir / creative_code_pr_promotion.VALIDATION_FILE).exists()


def test_main_forwards_trusted_dispatch_result_as_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_validate(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return {}

    monkeypatch.setattr(creative_code_pr_promotion, "validate", fake_validate)

    exit_code = creative_code_pr_promotion.main(
        [
            "validate",
            "--promotion-id",
            "promotion-pr3-cli-forwarding",
            "--trusted-dispatch-result",
            "artifacts/orchestration/experiments/results/result.json",
            "--trusted-generation-receipt",
            "artifacts/orchestration/creative_code/patch_generation/custom/generation_receipt.json",
        ]
    )

    assert exit_code == 0
    assert captured == {
        "promotion_id": "promotion-pr3-cli-forwarding",
        "trusted_dispatch_result": Path("artifacts/orchestration/experiments/results/result.json"),
        "trusted_generation_receipt": Path(
            "artifacts/orchestration/creative_code/patch_generation/custom/"
            "generation_receipt.json"
        ),
    }


@pytest.mark.parametrize(
    ("path_case", "message"),
    [
        ("outside", "under patch generation artifacts"),
        ("symlink", "must not traverse symlinks"),
        ("wrong_name", "must be named generation_receipt.json"),
    ],
)
def test_validation_rejects_unsafe_generation_receipt_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    path_case: str,
    message: str,
) -> None:
    repo, run_id, _result = _make_patch_run(
        monkeypatch,
        tmp_path,
        run_id=f"patch-run-receipt-{path_case}",
    )
    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id=f"promotion-pr3-receipt-{path_case}",
        git=FakeGit(),
    )
    result_path, _packet = _write_dispatch_fixture(repo, run_id)
    valid_receipt = _generation_receipt_path(repo, run_id)
    if path_case == "outside":
        supplied_receipt = tmp_path / "outside" / creative_code_patch_generation.RECEIPT_FILENAME
        supplied_receipt.parent.mkdir()
        supplied_receipt.write_text(
            valid_receipt.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    elif path_case == "symlink":
        supplied_receipt = (
            creative_code_patch_generation.PATCH_GENERATION_ROOT
            / "linked"
            / creative_code_patch_generation.RECEIPT_FILENAME
        )
        supplied_receipt.parent.mkdir()
        supplied_receipt.symlink_to(valid_receipt)
    elif path_case == "wrong_name":
        supplied_receipt = valid_receipt.with_name("receipt.json")
        supplied_receipt.write_text(
            valid_receipt.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    else:  # pragma: no cover - parametrization is closed above.
        raise AssertionError(path_case)
    promotion_dir = Path(planned["promotion_dir"])
    checkout = _stub_validation_checkout(monkeypatch, promotion_dir)

    with pytest.raises(CreativeCodePRPromotionError, match=message):
        creative_code_pr_promotion.validate(
            promotion_id=f"promotion-pr3-receipt-{path_case}",
            trusted_dispatch_result=result_path,
            trusted_generation_receipt=supplied_receipt,
            git=FakeGit(),
            gate_runner=FakeGates(),
        )

    assert not checkout.exists()
    assert not (promotion_dir / creative_code_pr_promotion.VALIDATION_FILE).exists()


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("experiment_id", "failed Experiment Runner validation"),
        ("candidate_fingerprint", "candidate patch fingerprint does not match"),
        ("mutated_paths", "mutated paths do not match"),
        ("rejected", "must be accepted"),
        ("docker_backend", "passed Apple Container provenance"),
        ("attempts", "one attempt and zero retries"),
        ("retry", "one attempt and zero retries"),
        ("oracle_failure", "every configured oracle to pass"),
        ("shared_tree", "shared tree was untouched"),
    ],
)
def test_validation_rejects_unbound_trusted_dispatch_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    repo, run_id, _result = _make_patch_run(
        monkeypatch,
        tmp_path,
        run_id=f"patch-run-{mutation}",
    )
    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id=f"promotion-pr3-{mutation}",
        git=FakeGit(),
    )
    result_path, packet = _write_dispatch_fixture(repo, run_id)
    dispatch_result = json.loads(result_path.read_text(encoding="utf-8"))
    if mutation == "experiment_id":
        dispatch_result["experiment_id"] = "experiment:other"
    elif mutation == "candidate_fingerprint":
        dispatch_result["candidate_patch_fingerprint"] = "sha256:" + ("f" * 64)
    elif mutation == "mutated_paths":
        dispatch_result["mutated_paths"] = ["core/rag/other.py"]
    elif mutation == "rejected":
        dispatch_result["status"] = "rejected"
        dispatch_result["failure_class"] = "guard_failure"
        dispatch_result["oracle_results"][-1]["returncode"] = 1
    elif mutation == "docker_backend":
        dispatch_result["execution_backend"].update(
            {
                "name": "docker",
                "runtime_version": "29.6.1",
                "network_isolation": "docker_network_none_plus_linux_unshare",
            }
        )
    elif mutation == "attempts":
        dispatch_result["budget_observations"]["attempts"] = 2
    elif mutation == "retry":
        dispatch_result["budget_observations"]["retries_consumed"] = 1
    elif mutation == "oracle_failure":
        dispatch_result["oracle_results"][-1]["returncode"] = 1
    elif mutation == "shared_tree":
        dispatch_result["shared_tree_untouched"] = False
    else:  # pragma: no cover - parametrization is closed above.
        raise AssertionError(mutation)
    _write_json(result_path, dispatch_result)
    promotion_dir = Path(planned["promotion_dir"])
    checkout = _stub_validation_checkout(monkeypatch, promotion_dir)

    with pytest.raises(CreativeCodePRPromotionError, match=message):
        creative_code_pr_promotion.validate(
            promotion_id=f"promotion-pr3-{mutation}",
            trusted_dispatch_result=result_path.relative_to(repo),
            trusted_generation_receipt=_generation_receipt_path(
                repo,
                run_id,
            ).relative_to(repo),
            git=FakeGit(),
            gate_runner=FakeGates(),
        )

    assert not checkout.exists()
    assert not (promotion_dir / creative_code_pr_promotion.VALIDATION_FILE).exists()
    assert len(packet["immutable_oracles"]) == 1


@pytest.mark.parametrize(
    ("path_case", "message"),
    [
        ("outside", "under experiment results"),
        ("symlink", "must not traverse symlinks"),
        ("malformed", "unable to read trusted dispatch result safely"),
    ],
)
def test_validation_rejects_unsafe_trusted_dispatch_result_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    path_case: str,
    message: str,
) -> None:
    repo, run_id, _result = _make_patch_run(
        monkeypatch,
        tmp_path,
        run_id=f"patch-run-{path_case}",
    )
    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id=f"promotion-pr3-{path_case}",
        git=FakeGit(),
    )
    result_path, _packet = _write_dispatch_fixture(repo, run_id)
    if path_case == "outside":
        supplied_path = tmp_path / "outside.json"
        supplied_path.write_text(result_path.read_text(encoding="utf-8"), encoding="utf-8")
    elif path_case == "symlink":
        supplied_path = result_path.with_name("linked-result.json")
        supplied_path.symlink_to(result_path.name)
    elif path_case == "malformed":
        supplied_path = result_path
        supplied_path.write_text("{not-json", encoding="utf-8")
    else:  # pragma: no cover - parametrization is closed above.
        raise AssertionError(path_case)
    promotion_dir = Path(planned["promotion_dir"])
    checkout = _stub_validation_checkout(monkeypatch, promotion_dir)

    with pytest.raises(CreativeCodePRPromotionError, match=message):
        creative_code_pr_promotion.validate(
            promotion_id=f"promotion-pr3-{path_case}",
            trusted_dispatch_result=supplied_path,
            trusted_generation_receipt=_generation_receipt_path(repo, run_id),
            git=FakeGit(),
            gate_runner=FakeGates(),
        )

    assert not checkout.exists()
    assert not (promotion_dir / creative_code_pr_promotion.VALIDATION_FILE).exists()


def test_validation_rejects_forged_packet_and_matching_dispatch_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, run_id, _result = _make_patch_run(
        monkeypatch,
        tmp_path,
        run_id="patch-run-forged-packet",
    )
    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id="promotion-pr3-forged-packet",
        git=FakeGit(),
    )
    result_path, packet = _write_dispatch_fixture(repo, run_id)
    packet["immutable_oracles"][0]["command"] = "pytest -q tests/test_forged_oracle.py"
    run_dir = repo / "artifacts" / "orchestration" / "creative_code" / "patch_runs" / run_id
    _write_json(run_dir / EXPERIMENT_PACKET_FILE, packet)
    _write_json(result_path, _accepted_dispatch_fixture(packet))
    promotion_dir = Path(planned["promotion_dir"])
    checkout = _stub_validation_checkout(monkeypatch, promotion_dir)

    with pytest.raises(
        CreativeCodePRPromotionError,
        match="generation receipt experiment packet fingerprint is stale",
    ):
        creative_code_pr_promotion.validate(
            promotion_id="promotion-pr3-forged-packet",
            trusted_dispatch_result=result_path.relative_to(repo),
            trusted_generation_receipt=_generation_receipt_path(repo, run_id),
            git=FakeGit(),
            gate_runner=FakeGates(),
        )

    assert not checkout.exists()
    assert not (promotion_dir / creative_code_pr_promotion.VALIDATION_FILE).exists()


def test_validation_rejects_dispatch_result_not_finalized_into_pr2(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, run_id, _result = _make_patch_run(
        monkeypatch,
        tmp_path,
        run_id="patch-run-unfinalized-result",
    )
    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id="promotion-pr3-unfinalized-result",
        git=FakeGit(),
    )
    result_path, _packet = _write_dispatch_fixture(repo, run_id)
    dispatch_result = json.loads(result_path.read_text(encoding="utf-8"))
    dispatch_result["execution_backend"]["runtime_version"] = "1.1.1"
    _write_json(result_path, dispatch_result)
    promotion_dir = Path(planned["promotion_dir"])
    checkout = _stub_validation_checkout(monkeypatch, promotion_dir)

    with pytest.raises(
        CreativeCodePRPromotionError,
        match="does not match the result finalized into PR-2",
    ):
        creative_code_pr_promotion.validate(
            promotion_id="promotion-pr3-unfinalized-result",
            trusted_dispatch_result=result_path.relative_to(repo),
            trusted_generation_receipt=_generation_receipt_path(repo, run_id),
            git=FakeGit(),
            gate_runner=FakeGates(),
        )

    assert not checkout.exists()
    assert not (promotion_dir / creative_code_pr_promotion.VALIDATION_FILE).exists()


def test_validation_rejects_generation_receipt_without_canonical_gate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, run_id, _result = _make_patch_run(
        monkeypatch,
        tmp_path,
        run_id="patch-run-missing-generation-gate",
    )
    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id="promotion-pr3-missing-generation-gate",
        git=FakeGit(),
    )
    result_path, _packet = _write_dispatch_fixture(repo, run_id)
    receipt_path = _generation_receipt_path(repo, run_id)
    receipt_path.with_name(creative_code_patch_generation.GATE_FILENAME).unlink()
    promotion_dir = Path(planned["promotion_dir"])
    checkout = _stub_validation_checkout(monkeypatch, promotion_dir)

    with pytest.raises(
        CreativeCodePRPromotionError,
        match="unable to read generation gate safely",
    ):
        creative_code_pr_promotion.validate(
            promotion_id="promotion-pr3-missing-generation-gate",
            trusted_dispatch_result=result_path,
            trusted_generation_receipt=receipt_path,
            git=FakeGit(),
            gate_runner=FakeGates(),
        )

    assert not checkout.exists()
    assert not (promotion_dir / creative_code_pr_promotion.VALIDATION_FILE).exists()


def test_validation_rejects_coherently_forged_gate_and_receipt_sources(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, run_id, result = _make_patch_run(
        monkeypatch,
        tmp_path,
        run_id="patch-run-forged-gate-sources",
    )
    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id="promotion-pr3-forged-gate-sources",
        git=FakeGit(),
    )
    result_path, _packet = _write_dispatch_fixture(repo, run_id)
    receipt_path = _generation_receipt_path(repo, run_id)
    gate_path = receipt_path.with_name(creative_code_patch_generation.GATE_FILENAME)
    gate = creative_code_patch_generation._read_generation_gate(gate_path)
    gate["admission_id"] = "admission:forged"
    gate["admission_fingerprint"] = fingerprint_payload({"admission": "forged"})
    gate["admission_ref"] = "artifacts/orchestration/creative_code/admissions/forged.json"
    gate["state_fingerprint"] = fingerprint_payload({"state": "forged"})
    creative_code_patch_generation._set_identity(
        gate,
        id_key="gate_id",
        asset_type=creative_code_patch_generation.GATE_ARTIFACT_TYPE,
    )
    gate = creative_code_patch_generation.validate_generation_gate(gate)
    _write_json(gate_path, gate)
    _write_json(
        receipt_path,
        creative_code_patch_generation._build_receipt(
            gate_path=gate_path,
            gate=gate,
            result=result,
        ),
    )

    def reject_forged_context(
        supplied_gate: dict[str, Any],
    ) -> tuple[Path, dict[str, Any]]:
        assert supplied_gate["admission_id"] == "admission:forged"
        raise creative_code_patch_generation.CreativeCodePatchGenerationError(
            "generation gate admission_id no longer matches its source."
        )

    monkeypatch.setattr(
        creative_code_patch_generation,
        "validate_finalized_dispatch_context",
        reject_forged_context,
    )
    promotion_dir = Path(planned["promotion_dir"])
    checkout = _stub_validation_checkout(monkeypatch, promotion_dir)

    with pytest.raises(
        CreativeCodePRPromotionError,
        match="generation gate admission_id no longer matches its source",
    ):
        creative_code_pr_promotion.validate(
            promotion_id="promotion-pr3-forged-gate-sources",
            trusted_dispatch_result=result_path,
            trusted_generation_receipt=receipt_path,
            git=FakeGit(),
            gate_runner=FakeGates(),
        )

    assert not checkout.exists()
    assert not (promotion_dir / creative_code_pr_promotion.VALIDATION_FILE).exists()


def test_validation_rejects_generation_receipt_for_different_planned_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, run_id, _result = _make_patch_run(
        monkeypatch,
        tmp_path,
        run_id="patch-run-different-planned-result",
    )
    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id="promotion-pr3-different-planned-result",
        git=FakeGit(),
    )
    result_path, _packet = _write_dispatch_fixture(repo, run_id)
    run_dir = repo / "artifacts" / "orchestration" / "creative_code" / "patch_runs" / run_id
    dispatch_result = json.loads(result_path.read_text(encoding="utf-8"))
    dispatch_result["oracle_results"][0]["stdout"] = "different accepted execution"
    _write_json(result_path, dispatch_result)
    request = json.loads((run_dir / REQUEST_FILE).read_text(encoding="utf-8"))
    patch_text = (run_dir / CANDIDATE_PATCH_FILE).read_text(encoding="utf-8")
    replacement_result = build_creative_code_patch_result(
        request=request,
        changed_paths=["core/rag/orchestration.py"],
        patch_fingerprint=fingerprint_payload({"candidate_patch": patch_text}),
        patch_bytes=len(patch_text.encode("utf-8")),
        diff_lines=len(patch_text.splitlines()),
        runner_result=dispatch_result,
        checkout_destroyed=True,
        origin_removed=True,
        shared_tree_untouched=True,
        failure_class=None,
    )
    assert replacement_result["result_id"] != planned["plan"]["source_result_id"]
    _write_json(run_dir / RESULT_FILE, replacement_result)
    receipt_path = _generation_receipt_path(repo, run_id)
    gate_path = receipt_path.with_name(creative_code_patch_generation.GATE_FILENAME)
    gate = creative_code_patch_generation._read_generation_gate(gate_path)
    _write_json(
        receipt_path,
        creative_code_patch_generation._build_receipt(
            gate_path=gate_path,
            gate=gate,
            result=replacement_result,
        ),
    )
    promotion_dir = Path(planned["promotion_dir"])
    checkout = _stub_validation_checkout(monkeypatch, promotion_dir)

    with pytest.raises(
        CreativeCodePRPromotionError,
        match="does not match the planned PR-2 result",
    ):
        creative_code_pr_promotion.validate(
            promotion_id="promotion-pr3-different-planned-result",
            trusted_dispatch_result=result_path,
            trusted_generation_receipt=receipt_path,
            git=FakeGit(),
            gate_runner=FakeGates(),
        )

    assert not checkout.exists()
    assert not (promotion_dir / creative_code_pr_promotion.VALIDATION_FILE).exists()


def test_validation_rejects_trusted_dispatch_result_refinalization_after_plan(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, run_id, _result = _make_patch_run(
        monkeypatch,
        tmp_path,
        run_id="patch-run-fingerprint-drift",
    )
    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id="promotion-pr3-fingerprint-drift",
        git=FakeGit(),
    )
    result_path, _packet = _write_dispatch_fixture(repo, run_id)
    run_dir = repo / "artifacts" / "orchestration" / "creative_code" / "patch_runs" / run_id
    receipt_path = _generation_receipt_path(repo, run_id)
    promotion_dir = Path(planned["promotion_dir"])
    checkout = _stub_validation_checkout(monkeypatch, promotion_dir)

    class MutatingGates(FakeGates):
        def run_pre_commit(self, *, cwd: Path) -> None:
            super().run_pre_commit(cwd=cwd)
            dispatch_result = json.loads(result_path.read_text(encoding="utf-8"))
            dispatch_result["oracle_results"][0]["stdout"] = "post-gate evidence changed"
            _write_json(result_path, dispatch_result)

            request = json.loads((run_dir / REQUEST_FILE).read_text(encoding="utf-8"))
            patch_text = (run_dir / CANDIDATE_PATCH_FILE).read_text(encoding="utf-8")
            pr2_result = build_creative_code_patch_result(
                request=request,
                changed_paths=["core/rag/orchestration.py"],
                patch_fingerprint=fingerprint_payload({"candidate_patch": patch_text}),
                patch_bytes=len(patch_text.encode("utf-8")),
                diff_lines=len(patch_text.splitlines()),
                runner_result=dispatch_result,
                checkout_destroyed=True,
                origin_removed=True,
                shared_tree_untouched=True,
                failure_class=None,
            )
            _write_json(run_dir / RESULT_FILE, pr2_result)

            gate_path = receipt_path.with_name(creative_code_patch_generation.GATE_FILENAME)
            gate = creative_code_patch_generation._read_generation_gate(gate_path)
            _write_json(
                receipt_path,
                creative_code_patch_generation._build_receipt(
                    gate_path=gate_path,
                    gate=gate,
                    result=pr2_result,
                ),
            )

    with pytest.raises(
        CreativeCodePRPromotionError,
        match="does not match the planned PR-2 result",
    ):
        creative_code_pr_promotion.validate(
            promotion_id="promotion-pr3-fingerprint-drift",
            trusted_dispatch_result=result_path.relative_to(repo),
            trusted_generation_receipt=receipt_path,
            git=FakeGit(),
            gate_runner=MutatingGates(),
        )

    assert not checkout.exists()
    assert not (promotion_dir / creative_code_pr_promotion.VALIDATION_FILE).exists()


def test_validation_rejects_trusted_generation_gate_and_receipt_drift(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, run_id, _result = _make_patch_run(
        monkeypatch,
        tmp_path,
        run_id="patch-run-receipt-fingerprint-drift",
    )
    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id="promotion-pr3-receipt-fingerprint-drift",
        git=FakeGit(),
    )
    result_path, _packet = _write_dispatch_fixture(repo, run_id)
    run_dir = repo / "artifacts" / "orchestration" / "creative_code" / "patch_runs" / run_id
    result_before = fingerprint_payload(
        json.loads((run_dir / RESULT_FILE).read_text(encoding="utf-8"))
    )
    receipt_path = _generation_receipt_path(repo, run_id)
    gate_path = receipt_path.with_name(creative_code_patch_generation.GATE_FILENAME)
    receipt_before = fingerprint_payload(json.loads(receipt_path.read_text(encoding="utf-8")))
    promotion_dir = Path(planned["promotion_dir"])
    checkout = _stub_validation_checkout(monkeypatch, promotion_dir)

    class MutatingGates(FakeGates):
        def run_pre_commit(self, *, cwd: Path) -> None:
            super().run_pre_commit(cwd=cwd)
            gate = creative_code_patch_generation._read_generation_gate(gate_path)
            gate["admission_id"] = "admission:replacement"
            gate["admission_fingerprint"] = fingerprint_payload({"admission": "replacement"})
            gate["admission_ref"] = (
                "artifacts/orchestration/creative_code/admissions/replacement.json"
            )
            creative_code_patch_generation._set_identity(
                gate,
                id_key="gate_id",
                asset_type=creative_code_patch_generation.GATE_ARTIFACT_TYPE,
            )
            gate = creative_code_patch_generation.validate_generation_gate(gate)
            _write_json(gate_path, gate)
            result = json.loads((run_dir / RESULT_FILE).read_text(encoding="utf-8"))
            _write_json(
                receipt_path,
                creative_code_patch_generation._build_receipt(
                    gate_path=gate_path,
                    gate=gate,
                    result=result,
                ),
            )
            assert fingerprint_payload(result) == result_before
            assert (
                fingerprint_payload(json.loads(receipt_path.read_text(encoding="utf-8")))
                != receipt_before
            )

    with pytest.raises(
        CreativeCodePRPromotionError,
        match="trusted dispatch evidence changed during validation",
    ):
        creative_code_pr_promotion.validate(
            promotion_id="promotion-pr3-receipt-fingerprint-drift",
            trusted_dispatch_result=result_path,
            trusted_generation_receipt=receipt_path,
            git=FakeGit(),
            gate_runner=MutatingGates(),
        )

    assert not checkout.exists()
    assert not (promotion_dir / creative_code_pr_promotion.VALIDATION_FILE).exists()


def test_validation_rejects_generation_receipt_drift_from_canonical_gate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, run_id, _result = _make_patch_run(
        monkeypatch,
        tmp_path,
        run_id="patch-run-receipt-gate-drift",
    )
    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id="promotion-pr3-receipt-gate-drift",
        git=FakeGit(),
    )
    result_path, _packet = _write_dispatch_fixture(repo, run_id)
    run_dir = repo / "artifacts" / "orchestration" / "creative_code" / "patch_runs" / run_id
    result_fingerprint = fingerprint_payload(
        json.loads((run_dir / RESULT_FILE).read_text(encoding="utf-8"))
    )
    receipt_path = _generation_receipt_path(repo, run_id)
    gate_path = receipt_path.with_name(creative_code_patch_generation.GATE_FILENAME)
    gate_fingerprint = fingerprint_payload(
        creative_code_patch_generation._read_generation_gate(gate_path)
    )
    receipt = creative_code_patch_generation.validate_generation_receipt(
        json.loads(receipt_path.read_text(encoding="utf-8"))
    )
    receipt["admission_id"] = "admission:replacement"
    creative_code_patch_generation._set_identity(
        receipt,
        id_key="receipt_id",
        asset_type=creative_code_patch_generation.RECEIPT_ARTIFACT_TYPE,
    )
    _write_json(
        receipt_path,
        creative_code_patch_generation.validate_generation_receipt(receipt),
    )
    assert (
        fingerprint_payload(creative_code_patch_generation._read_generation_gate(gate_path))
        == gate_fingerprint
    )
    assert (
        fingerprint_payload(json.loads((run_dir / RESULT_FILE).read_text(encoding="utf-8")))
        == result_fingerprint
    )
    promotion_dir = Path(planned["promotion_dir"])
    checkout = _stub_validation_checkout(monkeypatch, promotion_dir)

    with pytest.raises(
        CreativeCodePRPromotionError,
        match="generation receipt admission_id does not match gate",
    ):
        creative_code_pr_promotion.validate(
            promotion_id="promotion-pr3-receipt-gate-drift",
            trusted_dispatch_result=result_path,
            trusted_generation_receipt=receipt_path,
            git=FakeGit(),
            gate_runner=FakeGates(),
        )

    assert not checkout.exists()
    assert not (promotion_dir / creative_code_pr_promotion.VALIDATION_FILE).exists()


def test_validation_capability_signal_cleans_checkout_without_artifact_or_leak(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _repo, run_id, _result = _make_patch_run(monkeypatch, tmp_path)
    git = cast(creative_code_pr_promotion.GitTransport, FakeGit())
    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id="promotion-pr3-capability-signal",
        git=git,
    )
    calls: list[str] = []
    canary = "/Users/example/ghp_capability_canary"

    def fake_prepare(**kwargs: Any) -> Path:
        dirname = kwargs["dirname"]
        assert isinstance(dirname, str)
        calls.append(f"prepare:{dirname}")
        checkout = Path(planned["promotion_dir"]) / dirname
        checkout.mkdir()
        return checkout

    def fake_apply(**kwargs: Any) -> None:
        calls.append("apply")

    def fake_destroy(_promotion_dir: Path, dirname: str) -> bool:
        calls.append(f"destroy:{dirname}")
        return True

    def raise_capability_signal(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise creative_code_pr_promotion.RunnerCapabilitySignal(canary)

    monkeypatch.setattr(creative_code_pr_promotion, "_prepare_checkout", fake_prepare)
    monkeypatch.setattr(creative_code_pr_promotion, "_apply_patch_and_verify", fake_apply)
    monkeypatch.setattr(creative_code_pr_promotion, "_destroy_checkout", fake_destroy)
    monkeypatch.setattr(
        creative_code_pr_promotion,
        "evaluate_candidate",
        raise_capability_signal,
    )

    with pytest.raises(
        CreativeCodePRPromotionError,
        match=(
            "^Fresh Experiment Runner capability unavailable; " "trusted dispatch is required\\.$"
        ),
    ) as exc_info:
        creative_code_pr_promotion.validate(
            promotion_id="promotion-pr3-capability-signal",
            git=git,
            gate_runner=creative_code_pr_promotion.GateRunner(),
        )

    assert exc_info.value.__cause__ is None
    assert canary not in str(exc_info.value)
    assert calls == [
        "prepare:validation_checkout",
        "apply",
        "destroy:validation_checkout",
    ]
    promotion_dir = Path(planned["promotion_dir"])
    assert not (promotion_dir / creative_code_pr_promotion.VALIDATION_FILE).exists()


def test_approval_requires_validation_tty_exact_phrase_and_actor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _repo, run_id, _result = _make_patch_run(monkeypatch, tmp_path)
    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id="promotion-pr3-approve",
        git=FakeGit(),
    )
    plan = planned["plan"]
    validation = build_creative_code_pr_promotion_validation(
        promotion_id="promotion-pr3-approve",
        plan_fingerprint=promotion_plan_fingerprint(plan),
        patch_fingerprint=plan["patch_fingerprint"],
        base_commit_sha=plan["base_commit_sha"],
        oracle_commands_configured=1,
        oracle_commands_executed=1,
    )
    promotion_dir = Path(planned["promotion_dir"])
    _write_json(promotion_dir / creative_code_pr_promotion.VALIDATION_FILE, validation)

    with pytest.raises(CreativeCodePRPromotionError, match="interactive TTY"):
        creative_code_pr_promotion.approve(
            promotion_id="promotion-pr3-approve",
            approved_by_login="Katsiarynakavaleuskaya",
            github=FakeGitHub(),
            stdin=FakeTTY("", tty=False),
            stdout=FakeStdout(),
        )

    phrase = (
        f"APPROVE NON-DRAFT PR {promotion_plan_fingerprint(plan)} {plan['patch_fingerprint'][7:15]}"
    )
    with pytest.raises(CreativeCodePRPromotionError, match="does not match"):
        creative_code_pr_promotion.approve(
            promotion_id="promotion-pr3-approve",
            approved_by_login="WrongActor",
            github=FakeGitHub(),
            stdin=FakeTTY(phrase),
            stdout=FakeStdout(),
        )

    approval = creative_code_pr_promotion.approve(
        promotion_id="promotion-pr3-approve",
        approved_by_login="Katsiarynakavaleuskaya",
        github=FakeGitHub(),
        stdin=FakeTTY(phrase),
        stdout=FakeStdout(),
    )

    assert approval["decision"] == "approve_non_draft_pr_creation"
    assert approval["confirmation_mode"] == "interactive_tty"
    assert approval["unattended_approval"] is False


def test_approval_rejects_validation_artifact_cross_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _repo, run_id, _result = _make_patch_run(monkeypatch, tmp_path)
    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id="promotion-pr3-stale-validation",
        git=FakeGit(),
    )
    plan = planned["plan"]
    validation = build_creative_code_pr_promotion_validation(
        promotion_id="promotion-pr3-stale-validation",
        plan_fingerprint=promotion_plan_fingerprint(plan),
        patch_fingerprint="sha256:" + "9" * 64,
        base_commit_sha=plan["base_commit_sha"],
        oracle_commands_configured=1,
        oracle_commands_executed=1,
    )
    promotion_dir = Path(planned["promotion_dir"])
    _write_json(promotion_dir / creative_code_pr_promotion.VALIDATION_FILE, validation)

    with pytest.raises(CreativeCodePRPromotionError, match="validation patch fingerprint"):
        creative_code_pr_promotion.approve(
            promotion_id="promotion-pr3-stale-validation",
            approved_by_login="Katsiarynakavaleuskaya",
            github=FakeGitHub(),
            stdin=FakeTTY(""),
            stdout=FakeStdout(),
        )


def test_github_transport_forbids_draft_ready_review_merge_and_auth_token() -> None:
    forbidden = [
        ["pr", "create", "--draft"],
        ["pr", "ready"],
        ["pr", "review"],
        ["pr", "merge"],
        ["pr", "close"],
        ["auth", "token"],
        ["api", "repos/x/y/pulls/1/reviews"],
        ["api", "repos/x/y/pulls/1/merge"],
    ]
    for args in forbidden:
        with pytest.raises(CreativeCodePRPromotionError):
            creative_code_pr_promotion._reject_forbidden_gh_args(args)


@pytest.mark.parametrize(
    "remote_url",
    [
        "git@github.com:Katsiarynakavaleuskaya/PulsePlate.git",
        "git@github.com:Katsiarynakavaleuskaya/PulsePlate",
        "ssh://git@github.com/Katsiarynakavaleuskaya/PulsePlate.git",
        "https://github.com/Katsiarynakavaleuskaya/PulsePlate",
        "https://github.com/Katsiarynakavaleuskaya/PulsePlate.git",
    ],
)
def test_validate_pulseplate_remote_url_accepts_canonical_forms(remote_url: str) -> None:
    assert (
        creative_code_pr_promotion.validate_pulseplate_remote_url(remote_url)
        == "Katsiarynakavaleuskaya/PulsePlate"
    )


@pytest.mark.parametrize(
    "remote_url",
    [
        "git@github.com:evil/Katsiarynakavaleuskaya/PulsePlate.git",
        "git@github.com:Katsiarynakavaleuskaya/PulsePlate.git/extra",
        "git@github.com:Katsiarynakavaleuskaya/PulsePlate.evil.git",
        "git@github.com:katsiarynakavaleuskaya/PulsePlate.git",
        "git@github.com:Katsiarynakavaleuskaya/pulseplate.git",
        "github.com:Katsiarynakavaleuskaya/PulsePlate.git",
        "git@github.com.evil:Katsiarynakavaleuskaya/PulsePlate.git",
        "ssh://bad@github.com/Katsiarynakavaleuskaya/PulsePlate.git",
        "ssh://github.com/Katsiarynakavaleuskaya/PulsePlate.git",
        "ssh://git@github.com/Katsiarynakavaleuskaya/pulseplate.git",
        "ssh://git@github.com:22/Katsiarynakavaleuskaya/PulsePlate.git",
        "ssh://git@github.com//Katsiarynakavaleuskaya/PulsePlate.git",
        "ssh://git@github.com/Katsiarynakavaleuskaya/PulsePlate.git/extra",
        "https://github.com.evil/Katsiarynakavaleuskaya/PulsePlate.git",
        "https://github.com/katsiarynakavaleuskaya/PulsePlate.git",
        "https://github.com/Katsiarynakavaleuskaya/PULSEPLATE.git",
        "https://github.com//Katsiarynakavaleuskaya/PulsePlate.git",
        "https://github.com/Katsiarynakavaleuskaya/PulsePlate.git/",
        "https://github.com/Katsiarynakavaleuskaya/PulsePlate.git?x=1",
        "https://token@github.com/Katsiarynakavaleuskaya/PulsePlate.git",
        "https://github.com/Katsiarynakavaleuskaya/PulsePlate.evil",
    ],
)
def test_validate_pulseplate_remote_url_rejects_spoofs(remote_url: str) -> None:
    with pytest.raises(CreativeCodePRPromotionError, match="origin remote"):
        creative_code_pr_promotion.validate_pulseplate_remote_url(remote_url)


def test_git_transport_contains_no_force_push_flag() -> None:
    source = (REPO_ROOT / "scripts/orchestration/creative_code_pr_promotion.py").read_text(
        encoding="utf-8"
    )

    assert "--force" not in source
    assert "--force-with-lease" not in source


def test_git_transport_ambiguous_upload_push_raises_cleanup_signal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[list[str]] = []

    def fake_run(
        self: creative_code_pr_promotion.GitTransport,
        args: list[str],
        *,
        cwd: Path,
        input_text: str | None = None,
        check: bool = True,
        timeout_seconds: int = 600,
    ) -> subprocess.CompletedProcess[str]:
        captured.append(args)
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="= refs/heads/experiment/promotion-upload-race\t[up to date]\n",
            stderr="",
        )

    monkeypatch.setattr(creative_code_pr_promotion.GitTransport, "run", fake_run)

    with pytest.raises(
        creative_code_pr_promotion.TemporaryUploadBranchAmbiguousError,
        match="cleanup required",
    ):
        creative_code_pr_promotion.GitTransport(git_binary="/bin/true").push_upload_branch(
            cwd=REPO_ROOT,
            branch="experiment/promotion-upload-race-aaaaaaaa-bbbbbbbbbb",
        )

    assert captured == [
        [
            "push",
            "--porcelain",
            "origin",
            "HEAD:refs/heads/experiment/promotion-upload-race-aaaaaaaa-bbbbbbbbbb",
        ]
    ]
    assert not any("--force" in token for command in captured for token in command)


def test_github_transport_create_branch_ref_uses_atomic_create_ref(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[list[str]] = []

    def fake_run(
        self: creative_code_pr_promotion.GitHubTransport,
        args: list[str],
        *,
        cwd: Path = REPO_ROOT,
        check: bool = True,
        timeout_seconds: int = 120,
    ) -> subprocess.CompletedProcess[str]:
        captured.append(args)
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(creative_code_pr_promotion.GitHubTransport, "run", fake_run)

    creative_code_pr_promotion.GitHubTransport(gh_binary="/bin/true").create_branch_ref(
        branch="experiment/create-ref",
        commit_sha="a" * 40,
    )

    assert captured == [
        [
            "api",
            "-X",
            "POST",
            "repos/Katsiarynakavaleuskaya/PulsePlate/git/refs",
            "-f",
            "ref=refs/heads/experiment/create-ref",
            "-f",
            f"sha={'a' * 40}",
        ]
    ]


def test_github_transport_create_branch_ref_validates_before_run() -> None:
    transport = creative_code_pr_promotion.GitHubTransport(gh_binary="/bin/true")

    with pytest.raises(CreativeCodePRPromotionContractError):
        transport.create_branch_ref(branch="main", commit_sha="a" * 40)
    with pytest.raises(CreativeCodePRPromotionError, match="commit SHA"):
        transport.create_branch_ref(branch="experiment/create-ref", commit_sha="abc")

    assert transport.calls == []


def test_github_transport_delete_branch_ref_is_temp_upload_only() -> None:
    transport = creative_code_pr_promotion.GitHubTransport(gh_binary="/bin/true")

    with pytest.raises(CreativeCodePRPromotionError, match="temporary branch"):
        transport.delete_branch_ref(branch="experiment/create-ref")

    assert transport.calls == []


def test_cleanup_temp_upload_ref_swallows_subprocess_timeout() -> None:
    github = TimeoutDeleteGitHub()

    assert (
        creative_code_pr_promotion._cleanup_temp_upload_ref(
            github,
            branch="experiment/promotion-upload-candidate-aaaaaaaa-bbbbbbbbbb",
        )
        is False
    )
    assert github.deleted_refs == ["experiment/promotion-upload-candidate-aaaaaaaa-bbbbbbbbbb"]


def test_no_pipeline_promote_or_notify_imports() -> None:
    source = (REPO_ROOT / "scripts/orchestration/creative_code_pr_promotion.py").read_text(
        encoding="utf-8"
    )
    forbidden_imports = (
        "import scripts.orchestration.experiment_pipeline",
        "import scripts.orchestration.experiment_promote",
        "import scripts.orchestration.experiment_notify",
        "from scripts.orchestration import experiment_pipeline",
        "from scripts.orchestration import experiment_promote",
        "from scripts.orchestration import experiment_notify",
    )
    for forbidden in forbidden_imports:
        assert forbidden not in source


def test_promotion_readback_requires_non_draft(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _repo, run_id, _result = _make_patch_run(monkeypatch, tmp_path)
    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id="promotion-pr3-promote",
        git=FakeGit(),
    )
    plan = planned["plan"]
    validation = build_creative_code_pr_promotion_validation(
        promotion_id="promotion-pr3-promote",
        plan_fingerprint=promotion_plan_fingerprint(plan),
        patch_fingerprint=plan["patch_fingerprint"],
        base_commit_sha=plan["base_commit_sha"],
        oracle_commands_configured=1,
        oracle_commands_executed=1,
    )
    approval = build_creative_code_pr_promotion_approval(
        promotion_id="promotion-pr3-promote",
        plan_fingerprint=promotion_plan_fingerprint(plan),
        validation_fingerprint=validation["validation_fingerprint"],
        approved_by_login="Katsiarynakavaleuskaya",
        confirmed_patch_fingerprint=plan["patch_fingerprint"],
        confirmed_base_commit_sha=plan["base_commit_sha"],
        confirmed_target_branch=plan["target_head_branch"],
    )
    promotion_dir = Path(planned["promotion_dir"])
    _write_json(promotion_dir / creative_code_pr_promotion.VALIDATION_FILE, validation)
    _write_json(promotion_dir / creative_code_pr_promotion.APPROVAL_FILE, approval)

    def fake_prepare(**kwargs: Any) -> Path:
        checkout = promotion_dir / kwargs["dirname"]
        checkout.mkdir(exist_ok=True)
        return checkout

    monkeypatch.setattr(creative_code_pr_promotion, "_prepare_checkout", fake_prepare)
    monkeypatch.setattr(creative_code_pr_promotion, "_apply_patch_and_verify", lambda **_: None)
    monkeypatch.setattr(creative_code_pr_promotion, "_destroy_checkout", lambda *_: True)
    monkeypatch.setattr(
        creative_code_pr_promotion,
        "_render_pr_body",
        lambda **_: "## Summary\nMerge readiness is not claimed.\n",
    )

    git = FakeGit()
    github = FakeGitHub()
    receipt = creative_code_pr_promotion.promote(
        promotion_id="promotion-pr3-promote",
        git=git,
        github=github,
    )

    upload_calls = [call for call in git.calls if call[:1] == ["push_upload_branch"]]
    assert len(upload_calls) == 1
    temp_upload_branch = upload_calls[0][1]
    assert temp_upload_branch.startswith("experiment/promotion-upload-")
    assert temp_upload_branch != plan["target_head_branch"]
    assert github.created_refs == [(plan["target_head_branch"], "b" * 40)]
    assert github.deleted_refs == [temp_upload_branch]
    assert receipt["pull_request_draft"] is False
    assert receipt["ready_for_review_operation_used"] is False
    assert receipt["merge_ready"] is False
    assert any(call[:2] == ["pr", "create"] for call in github.calls)
    assert not any(
        call[:2] in (["pr", "ready"], ["pr", "review"], ["pr", "merge"]) for call in github.calls
    )


def test_promote_rejects_non_human_git_identity_before_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _repo, run_id, _result = _make_patch_run(monkeypatch, tmp_path)
    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id="promotion-pr3-runner-identity",
        git=FakeGit(),
    )
    plan = planned["plan"]
    validation = build_creative_code_pr_promotion_validation(
        promotion_id="promotion-pr3-runner-identity",
        plan_fingerprint=promotion_plan_fingerprint(plan),
        patch_fingerprint=plan["patch_fingerprint"],
        base_commit_sha=plan["base_commit_sha"],
        oracle_commands_configured=1,
        oracle_commands_executed=1,
    )
    approval = build_creative_code_pr_promotion_approval(
        promotion_id="promotion-pr3-runner-identity",
        plan_fingerprint=promotion_plan_fingerprint(plan),
        validation_fingerprint=validation["validation_fingerprint"],
        approved_by_login="Katsiarynakavaleuskaya",
        confirmed_patch_fingerprint=plan["patch_fingerprint"],
        confirmed_base_commit_sha=plan["base_commit_sha"],
        confirmed_target_branch=plan["target_head_branch"],
    )
    promotion_dir = Path(planned["promotion_dir"])
    _write_json(promotion_dir / creative_code_pr_promotion.VALIDATION_FILE, validation)
    _write_json(promotion_dir / creative_code_pr_promotion.APPROVAL_FILE, approval)

    git = FakeGit(identity=("PulsePlate Experiment Runner", "pulseplate@pm.me"))
    github = FakeGitHub()
    with pytest.raises(CreativeCodePRPromotionError, match="human git identity"):
        creative_code_pr_promotion.promote(
            promotion_id="promotion-pr3-runner-identity",
            git=git,
            github=github,
        )

    assert not any("commit" in call or "push_upload_branch" in call for call in git.calls)
    assert not any(call[:2] == ["pr", "create"] for call in github.calls)


def test_promote_identity_verification_failure_writes_no_receipt_or_remote_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _repo, run_id, _result = _make_patch_run(monkeypatch, tmp_path)
    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id="promotion-pr3-identity-verify",
        git=FakeGit(),
    )
    plan = planned["plan"]
    validation = build_creative_code_pr_promotion_validation(
        promotion_id="promotion-pr3-identity-verify",
        plan_fingerprint=promotion_plan_fingerprint(plan),
        patch_fingerprint=plan["patch_fingerprint"],
        base_commit_sha=plan["base_commit_sha"],
        oracle_commands_configured=1,
        oracle_commands_executed=1,
    )
    approval = build_creative_code_pr_promotion_approval(
        promotion_id="promotion-pr3-identity-verify",
        plan_fingerprint=promotion_plan_fingerprint(plan),
        validation_fingerprint=validation["validation_fingerprint"],
        approved_by_login="Katsiarynakavaleuskaya",
        confirmed_patch_fingerprint=plan["patch_fingerprint"],
        confirmed_base_commit_sha=plan["base_commit_sha"],
        confirmed_target_branch=plan["target_head_branch"],
    )
    promotion_dir = Path(planned["promotion_dir"])
    _write_json(promotion_dir / creative_code_pr_promotion.VALIDATION_FILE, validation)
    _write_json(promotion_dir / creative_code_pr_promotion.APPROVAL_FILE, approval)

    def fake_prepare(**kwargs: Any) -> Path:
        checkout = promotion_dir / kwargs["dirname"]
        checkout.mkdir(exist_ok=True)
        return checkout

    monkeypatch.setattr(creative_code_pr_promotion, "_prepare_checkout", fake_prepare)
    monkeypatch.setattr(creative_code_pr_promotion, "_apply_patch_and_verify", lambda **_: None)
    monkeypatch.setattr(creative_code_pr_promotion, "_destroy_checkout", lambda *_: True)

    git = FakeGit(verify_identity_failure=True)
    github = FakeGitHub()
    with pytest.raises(CreativeCodePRPromotionError, match="identity mismatch"):
        creative_code_pr_promotion.promote(
            promotion_id="promotion-pr3-identity-verify",
            git=git,
            github=github,
        )

    assert not (promotion_dir / creative_code_pr_promotion.RECEIPT_FILE).exists()
    assert not any(call[:1] == ["push_upload_branch"] for call in git.calls)
    assert not any(call[:2] == ["pr", "create"] for call in github.calls)


def test_promote_rejects_stale_receipt_replay(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _repo, run_id, _result = _make_patch_run(monkeypatch, tmp_path)
    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id="promotion-pr3-stale-receipt",
        git=FakeGit(),
    )
    plan = planned["plan"]
    validation = build_creative_code_pr_promotion_validation(
        promotion_id="promotion-pr3-stale-receipt",
        plan_fingerprint=promotion_plan_fingerprint(plan),
        patch_fingerprint=plan["patch_fingerprint"],
        base_commit_sha=plan["base_commit_sha"],
        oracle_commands_configured=1,
        oracle_commands_executed=1,
    )
    approval = build_creative_code_pr_promotion_approval(
        promotion_id="promotion-pr3-stale-receipt",
        plan_fingerprint=promotion_plan_fingerprint(plan),
        validation_fingerprint=validation["validation_fingerprint"],
        approved_by_login="Katsiarynakavaleuskaya",
        confirmed_patch_fingerprint=plan["patch_fingerprint"],
        confirmed_base_commit_sha=plan["base_commit_sha"],
        confirmed_target_branch=plan["target_head_branch"],
    )
    stale_receipt = build_creative_code_pr_promotion_receipt(
        promotion_id="promotion-pr3-stale-receipt",
        plan_fingerprint=promotion_plan_fingerprint(plan),
        validation_fingerprint=validation["validation_fingerprint"],
        approval_id="evidence:stale-approval",
        source_result_id=plan["source_result_id"],
        patch_fingerprint=plan["patch_fingerprint"],
        head_branch=plan["target_head_branch"],
        commit_sha="b" * 40,
        pull_request_number=9999,
        pull_request_url="https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/9999",
        approved_by_login="Katsiarynakavaleuskaya",
    )
    promotion_dir = Path(planned["promotion_dir"])
    _write_json(promotion_dir / creative_code_pr_promotion.VALIDATION_FILE, validation)
    _write_json(promotion_dir / creative_code_pr_promotion.APPROVAL_FILE, approval)
    _write_json(promotion_dir / creative_code_pr_promotion.RECEIPT_FILE, stale_receipt)

    github = FakeGitHub()
    with pytest.raises(CreativeCodePRPromotionError, match="receipt approval_id"):
        creative_code_pr_promotion.promote(
            promotion_id="promotion-pr3-stale-receipt",
            git=FakeGit(),
            github=github,
        )

    assert github.calls == []


def test_promote_existing_receipt_requires_live_pr_readback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    plan, validation, approval, promotion_dir = _write_ready_promotion_artifacts(
        monkeypatch,
        tmp_path,
        promotion_id="promotion-pr3-existing-receipt-live",
    )
    existing_receipt = build_creative_code_pr_promotion_receipt(
        promotion_id="promotion-pr3-existing-receipt-live",
        plan_fingerprint=promotion_plan_fingerprint(plan),
        validation_fingerprint=validation["validation_fingerprint"],
        approval_id=approval["approval_id"],
        source_result_id=plan["source_result_id"],
        patch_fingerprint=plan["patch_fingerprint"],
        head_branch=plan["target_head_branch"],
        commit_sha="b" * 40,
        pull_request_number=9999,
        pull_request_url="https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/9999",
        approved_by_login="Katsiarynakavaleuskaya",
    )
    _write_json(promotion_dir / creative_code_pr_promotion.RECEIPT_FILE, existing_receipt)

    github = FakeGitHub()
    github.head_branch = plan["target_head_branch"]
    receipt = creative_code_pr_promotion.promote(
        promotion_id="promotion-pr3-existing-receipt-live",
        git=FakeGit(),
        github=github,
    )

    assert receipt == existing_receipt
    assert github.calls == [["pr", "view", existing_receipt["pull_request_url"]]]


def test_promote_rejects_existing_receipt_when_live_pr_readback_is_stale(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    plan, validation, approval, promotion_dir = _write_ready_promotion_artifacts(
        monkeypatch,
        tmp_path,
        promotion_id="promotion-pr3-existing-receipt-closed",
    )
    existing_receipt = build_creative_code_pr_promotion_receipt(
        promotion_id="promotion-pr3-existing-receipt-closed",
        plan_fingerprint=promotion_plan_fingerprint(plan),
        validation_fingerprint=validation["validation_fingerprint"],
        approval_id=approval["approval_id"],
        source_result_id=plan["source_result_id"],
        patch_fingerprint=plan["patch_fingerprint"],
        head_branch=plan["target_head_branch"],
        commit_sha="b" * 40,
        pull_request_number=9999,
        pull_request_url="https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/9999",
        approved_by_login="Katsiarynakavaleuskaya",
    )
    _write_json(promotion_dir / creative_code_pr_promotion.RECEIPT_FILE, existing_receipt)

    class ClosedReadbackGitHub(FakeGitHub):
        def read_pull_request(self, *, pr_ref: str) -> dict[str, Any]:
            self.calls.append(["pr", "view", pr_ref])
            return {
                "number": 9999,
                "url": pr_ref,
                "state": "CLOSED",
                "isDraft": False,
                "baseRefName": "main",
                "headRefName": plan["target_head_branch"],
                "headRefOid": "b" * 40,
            }

    github = ClosedReadbackGitHub()
    with pytest.raises(
        CreativeCodePRPromotionError,
        match="existing promotion receipt failed live PR readback verification",
    ):
        creative_code_pr_promotion.promote(
            promotion_id="promotion-pr3-existing-receipt-closed",
            git=FakeGit(),
            github=github,
        )

    assert github.calls == [["pr", "view", existing_receipt["pull_request_url"]]]


def test_promote_rejects_stale_patch_file_before_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, run_id, _result = _make_patch_run(monkeypatch, tmp_path)
    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id="promotion-pr3-stale-patch",
        git=FakeGit(),
    )
    plan = planned["plan"]
    validation = build_creative_code_pr_promotion_validation(
        promotion_id="promotion-pr3-stale-patch",
        plan_fingerprint=promotion_plan_fingerprint(plan),
        patch_fingerprint=plan["patch_fingerprint"],
        base_commit_sha=plan["base_commit_sha"],
        oracle_commands_configured=1,
        oracle_commands_executed=1,
    )
    approval = build_creative_code_pr_promotion_approval(
        promotion_id="promotion-pr3-stale-patch",
        plan_fingerprint=promotion_plan_fingerprint(plan),
        validation_fingerprint=validation["validation_fingerprint"],
        approved_by_login="Katsiarynakavaleuskaya",
        confirmed_patch_fingerprint=plan["patch_fingerprint"],
        confirmed_base_commit_sha=plan["base_commit_sha"],
        confirmed_target_branch=plan["target_head_branch"],
    )
    promotion_dir = Path(planned["promotion_dir"])
    _write_json(promotion_dir / creative_code_pr_promotion.VALIDATION_FILE, validation)
    _write_json(promotion_dir / creative_code_pr_promotion.APPROVAL_FILE, approval)
    patch_path = (
        repo
        / "artifacts"
        / "orchestration"
        / "creative_code"
        / "patch_runs"
        / run_id
        / CANDIDATE_PATCH_FILE
    )
    patch_path.write_text(_candidate_patch().replace("return 2", "return 3"), encoding="utf-8")

    git = FakeGit()
    github = FakeGitHub()
    with pytest.raises(CreativeCodePRPromotionError, match="candidate.patch changed"):
        creative_code_pr_promotion.promote(
            promotion_id="promotion-pr3-stale-patch",
            git=git,
            github=github,
        )

    assert not any("commit" in call or "push" in call for call in git.calls)
    assert not any(call[:2] == ["pr", "create"] for call in github.calls)


def test_promote_rejects_branch_that_appears_before_ref_create(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _repo, run_id, _result = _make_patch_run(monkeypatch, tmp_path)
    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id="promotion-pr3-branch-race",
        git=FakeGit(),
    )
    plan = planned["plan"]
    validation = build_creative_code_pr_promotion_validation(
        promotion_id="promotion-pr3-branch-race",
        plan_fingerprint=promotion_plan_fingerprint(plan),
        patch_fingerprint=plan["patch_fingerprint"],
        base_commit_sha=plan["base_commit_sha"],
        oracle_commands_configured=1,
        oracle_commands_executed=1,
    )
    approval = build_creative_code_pr_promotion_approval(
        promotion_id="promotion-pr3-branch-race",
        plan_fingerprint=promotion_plan_fingerprint(plan),
        validation_fingerprint=validation["validation_fingerprint"],
        approved_by_login="Katsiarynakavaleuskaya",
        confirmed_patch_fingerprint=plan["patch_fingerprint"],
        confirmed_base_commit_sha=plan["base_commit_sha"],
        confirmed_target_branch=plan["target_head_branch"],
    )
    promotion_dir = Path(planned["promotion_dir"])
    _write_json(promotion_dir / creative_code_pr_promotion.VALIDATION_FILE, validation)
    _write_json(promotion_dir / creative_code_pr_promotion.APPROVAL_FILE, approval)

    def fake_prepare(**kwargs: Any) -> Path:
        checkout = promotion_dir / kwargs["dirname"]
        checkout.mkdir(exist_ok=True)
        return checkout

    monkeypatch.setattr(creative_code_pr_promotion, "_prepare_checkout", fake_prepare)
    monkeypatch.setattr(creative_code_pr_promotion, "_apply_patch_and_verify", lambda **_: None)
    monkeypatch.setattr(creative_code_pr_promotion, "_destroy_checkout", lambda *_: True)

    git = FakeGit(remote_exists_sequence=[False, True])
    github = FakeGitHub()
    with pytest.raises(CreativeCodePRPromotionError, match="appeared before ref create"):
        creative_code_pr_promotion.promote(
            promotion_id="promotion-pr3-branch-race",
            git=git,
            github=github,
        )

    assert not any(call[:1] == ["push_upload_branch"] for call in git.calls)
    assert not any(call[:2] == ["pr", "create"] for call in github.calls)


def test_promote_create_ref_failure_cleans_temporary_upload_ref(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _repo, run_id, _result = _make_patch_run(monkeypatch, tmp_path)
    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id="promotion-pr3-create-ref-failure",
        git=FakeGit(),
    )
    plan = planned["plan"]
    validation = build_creative_code_pr_promotion_validation(
        promotion_id="promotion-pr3-create-ref-failure",
        plan_fingerprint=promotion_plan_fingerprint(plan),
        patch_fingerprint=plan["patch_fingerprint"],
        base_commit_sha=plan["base_commit_sha"],
        oracle_commands_configured=1,
        oracle_commands_executed=1,
    )
    approval = build_creative_code_pr_promotion_approval(
        promotion_id="promotion-pr3-create-ref-failure",
        plan_fingerprint=promotion_plan_fingerprint(plan),
        validation_fingerprint=validation["validation_fingerprint"],
        approved_by_login="Katsiarynakavaleuskaya",
        confirmed_patch_fingerprint=plan["patch_fingerprint"],
        confirmed_base_commit_sha=plan["base_commit_sha"],
        confirmed_target_branch=plan["target_head_branch"],
    )
    promotion_dir = Path(planned["promotion_dir"])
    _write_json(promotion_dir / creative_code_pr_promotion.VALIDATION_FILE, validation)
    _write_json(promotion_dir / creative_code_pr_promotion.APPROVAL_FILE, approval)

    def fake_prepare(**kwargs: Any) -> Path:
        checkout = promotion_dir / kwargs["dirname"]
        checkout.mkdir(exist_ok=True)
        return checkout

    monkeypatch.setattr(creative_code_pr_promotion, "_prepare_checkout", fake_prepare)
    monkeypatch.setattr(creative_code_pr_promotion, "_apply_patch_and_verify", lambda **_: None)
    monkeypatch.setattr(creative_code_pr_promotion, "_destroy_checkout", lambda *_: True)

    git = FakeGit()
    github = FailingCreateRefGitHub()
    with pytest.raises(CreativeCodePRPromotionError, match="target ref already exists"):
        creative_code_pr_promotion.promote(
            promotion_id="promotion-pr3-create-ref-failure",
            git=git,
            github=github,
        )

    upload_calls = [call for call in git.calls if call[:1] == ["push_upload_branch"]]
    assert len(upload_calls) == 1
    temp_upload_branch = upload_calls[0][1]
    assert github.created_refs == [(plan["target_head_branch"], "b" * 40)]
    assert github.deleted_refs == [temp_upload_branch]
    assert not any(call[:2] == ["pr", "create"] for call in github.calls)
    assert not (promotion_dir / creative_code_pr_promotion.RECEIPT_FILE).exists()


def test_promote_cleans_ambiguous_temp_upload_push(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _repo, run_id, _result = _make_patch_run(monkeypatch, tmp_path)
    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id="promotion-pr3-ambiguous-upload",
        git=FakeGit(),
    )
    plan = planned["plan"]
    validation = build_creative_code_pr_promotion_validation(
        promotion_id="promotion-pr3-ambiguous-upload",
        plan_fingerprint=promotion_plan_fingerprint(plan),
        patch_fingerprint=plan["patch_fingerprint"],
        base_commit_sha=plan["base_commit_sha"],
        oracle_commands_configured=1,
        oracle_commands_executed=1,
    )
    approval = build_creative_code_pr_promotion_approval(
        promotion_id="promotion-pr3-ambiguous-upload",
        plan_fingerprint=promotion_plan_fingerprint(plan),
        validation_fingerprint=validation["validation_fingerprint"],
        approved_by_login="Katsiarynakavaleuskaya",
        confirmed_patch_fingerprint=plan["patch_fingerprint"],
        confirmed_base_commit_sha=plan["base_commit_sha"],
        confirmed_target_branch=plan["target_head_branch"],
    )
    promotion_dir = Path(planned["promotion_dir"])
    _write_json(promotion_dir / creative_code_pr_promotion.VALIDATION_FILE, validation)
    _write_json(promotion_dir / creative_code_pr_promotion.APPROVAL_FILE, approval)

    def fake_prepare(**kwargs: Any) -> Path:
        checkout = promotion_dir / kwargs["dirname"]
        checkout.mkdir(exist_ok=True)
        return checkout

    monkeypatch.setattr(creative_code_pr_promotion, "_prepare_checkout", fake_prepare)
    monkeypatch.setattr(creative_code_pr_promotion, "_apply_patch_and_verify", lambda **_: None)
    monkeypatch.setattr(creative_code_pr_promotion, "_destroy_checkout", lambda *_: True)

    git = AmbiguousUploadGit()
    github = FakeGitHub()
    with pytest.raises(
        creative_code_pr_promotion.TemporaryUploadBranchAmbiguousError,
        match="cleanup required",
    ):
        creative_code_pr_promotion.promote(
            promotion_id="promotion-pr3-ambiguous-upload",
            git=git,
            github=github,
        )

    upload_calls = [call for call in git.calls if call[:1] == ["push_upload_branch"]]
    assert len(upload_calls) == 1
    temp_upload_branch = upload_calls[0][1]
    assert github.deleted_refs == [temp_upload_branch]
    assert not github.created_refs
    assert not any(call[:2] == ["pr", "create"] for call in github.calls)
    assert not (promotion_dir / creative_code_pr_promotion.RECEIPT_FILE).exists()


def test_promote_cleans_temp_upload_after_push_timeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _repo, run_id, _result = _make_patch_run(monkeypatch, tmp_path)
    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id="promotion-pr3-timeout-upload",
        git=FakeGit(),
    )
    plan = planned["plan"]
    validation = build_creative_code_pr_promotion_validation(
        promotion_id="promotion-pr3-timeout-upload",
        plan_fingerprint=promotion_plan_fingerprint(plan),
        patch_fingerprint=plan["patch_fingerprint"],
        base_commit_sha=plan["base_commit_sha"],
        oracle_commands_configured=1,
        oracle_commands_executed=1,
    )
    approval = build_creative_code_pr_promotion_approval(
        promotion_id="promotion-pr3-timeout-upload",
        plan_fingerprint=promotion_plan_fingerprint(plan),
        validation_fingerprint=validation["validation_fingerprint"],
        approved_by_login="Katsiarynakavaleuskaya",
        confirmed_patch_fingerprint=plan["patch_fingerprint"],
        confirmed_base_commit_sha=plan["base_commit_sha"],
        confirmed_target_branch=plan["target_head_branch"],
    )
    promotion_dir = Path(planned["promotion_dir"])
    _write_json(promotion_dir / creative_code_pr_promotion.VALIDATION_FILE, validation)
    _write_json(promotion_dir / creative_code_pr_promotion.APPROVAL_FILE, approval)

    def fake_prepare(**kwargs: Any) -> Path:
        checkout = promotion_dir / kwargs["dirname"]
        checkout.mkdir(exist_ok=True)
        return checkout

    monkeypatch.setattr(creative_code_pr_promotion, "_prepare_checkout", fake_prepare)
    monkeypatch.setattr(creative_code_pr_promotion, "_apply_patch_and_verify", lambda **_: None)
    monkeypatch.setattr(creative_code_pr_promotion, "_destroy_checkout", lambda *_: True)

    git = TimeoutUploadGit()
    github = FakeGitHub()
    with pytest.raises(subprocess.TimeoutExpired):
        creative_code_pr_promotion.promote(
            promotion_id="promotion-pr3-timeout-upload",
            git=git,
            github=github,
        )

    upload_calls = [call for call in git.calls if call[:1] == ["push_upload_branch"]]
    assert len(upload_calls) == 1
    temp_upload_branch = upload_calls[0][1]
    assert github.deleted_refs == [temp_upload_branch]
    assert not github.created_refs
    assert not any(call[:2] == ["pr", "create"] for call in github.calls)
    assert not (promotion_dir / creative_code_pr_promotion.RECEIPT_FILE).exists()


def test_promote_rejects_approval_artifact_cross_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _repo, run_id, _result = _make_patch_run(monkeypatch, tmp_path)
    planned = creative_code_pr_promotion.plan(
        patch_run=run_id,
        promotion_id="promotion-pr3-stale-approval",
        git=FakeGit(),
    )
    plan = planned["plan"]
    validation = build_creative_code_pr_promotion_validation(
        promotion_id="promotion-pr3-stale-approval",
        plan_fingerprint=promotion_plan_fingerprint(plan),
        patch_fingerprint=plan["patch_fingerprint"],
        base_commit_sha=plan["base_commit_sha"],
        oracle_commands_configured=1,
        oracle_commands_executed=1,
    )
    approval = build_creative_code_pr_promotion_approval(
        promotion_id="promotion-pr3-stale-approval",
        plan_fingerprint=promotion_plan_fingerprint(plan),
        validation_fingerprint=validation["validation_fingerprint"],
        approved_by_login="Katsiarynakavaleuskaya",
        confirmed_patch_fingerprint=plan["patch_fingerprint"],
        confirmed_base_commit_sha=plan["base_commit_sha"],
        confirmed_target_branch="experiment/other-33333333",
    )
    promotion_dir = Path(planned["promotion_dir"])
    _write_json(promotion_dir / creative_code_pr_promotion.VALIDATION_FILE, validation)
    _write_json(promotion_dir / creative_code_pr_promotion.APPROVAL_FILE, approval)

    github = FakeGitHub()
    with pytest.raises(CreativeCodePRPromotionError, match="approval target branch"):
        creative_code_pr_promotion.promote(
            promotion_id="promotion-pr3-stale-approval",
            git=FakeGit(),
            github=github,
        )

    assert github.calls == []
