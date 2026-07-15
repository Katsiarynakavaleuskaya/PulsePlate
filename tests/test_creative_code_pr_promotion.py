from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any, cast

import pytest

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration import creative_code_patch_workspace, creative_code_pr_promotion
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
    build_creative_code_pr_promotion_validation,
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


def _patch_modules_to_repo(monkeypatch: pytest.MonkeyPatch, repo: Path) -> None:
    patch_root = repo / "artifacts" / "orchestration" / "creative_code" / "patch_runs"
    promotion_root = repo / "artifacts" / "orchestration" / "creative_code" / "promotions"
    monkeypatch.setattr(creative_code_patch_workspace, "REPO_ROOT", repo)
    monkeypatch.setattr(creative_code_patch_workspace, "ARTIFACT_ROOT", patch_root)
    monkeypatch.setattr(creative_code_pr_promotion, "REPO_ROOT", repo)
    monkeypatch.setattr(creative_code_pr_promotion, "PROMOTION_ROOT", promotion_root)


def _make_patch_run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    run_id: str = "patch-run",
    accepted: bool = True,
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
    runner_result = {
        "experiment_id": "exp-pr3-reference",
        "status": "accepted" if accepted else "rejected",
        "failure_class": None if accepted else "guard_failure",
        "mutated_paths": ["core/rag/orchestration.py"],
        "budget_observations": {
            "oracle_commands_configured": 1,
            "attempts": 1,
            "retries_consumed": 0,
        },
        "oracle_results": [{"status": "passed"}] if accepted else [],
        "shared_tree_untouched": True,
    }
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
    _write_json(
        run_dir / EXPERIMENT_PACKET_FILE,
        {
            "experiment_id": "exp-pr3-reference",
            "runner_mode": "candidate_patch",
            "immutable_oracles": ["pytest -q tests/test_creative_code_patch_builder.py"],
            "mutable_candidate_surface": ["core/rag/orchestration.py"],
            "budgets": {"retry_budget": 0, "stop_condition": "all_oracles_pass"},
        },
    )
    (run_dir / CANDIDATE_PATCH_FILE).write_text(patch_text, encoding="utf-8")
    return repo, run_id, result


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

    validation = creative_code_pr_promotion.validate(
        promotion_id="promotion-pr3-validate",
        git=FakeGit(),
        gate_runner=FakeGates(),
    )

    assert validation["preopen_gates"]["pre_commit"] == "passed"
    assert validation["validation_checkout"]["used_throwaway_commit"] is True
    assert calls == [
        "prepare:validation_checkout",
        "apply",
        "patch_unchanged",
        "destroy:validation_checkout",
    ]


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
