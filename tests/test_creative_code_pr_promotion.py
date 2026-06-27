from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any

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
    def __init__(self, base_sha: str = "a" * 40, *, remote_exists: bool = False) -> None:
        self.base_sha = base_sha
        self.remote_exists = remote_exists
        self.committed = False
        self.calls: list[list[str]] = []

    def rev_parse_origin_main(self) -> str:
        return self.base_sha

    def shared_status(self) -> str:
        return ""

    def remote_branch_exists(self, branch: str) -> bool:
        self.calls.append(["remote_branch_exists", branch])
        return self.remote_exists

    def local_branch_exists(self, branch: str, *, cwd: Path = REPO_ROOT) -> bool:
        self.calls.append(["local_branch_exists", branch])
        return False

    def remote_url(self) -> str:
        return "git@github.com:Katsiarynakavaleuskaya/PulsePlate.git"

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

    def current_login(self) -> str:
        self.calls.append(["api", "user"])
        return self.login

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

    with pytest.raises(CreativeCodePRPromotionError, match="patch_metadata changed paths"):
        creative_code_pr_promotion.plan(
            patch_run=run_id,
            promotion_id="promotion-pr3-metadata",
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

    github = FakeGitHub()
    receipt = creative_code_pr_promotion.promote(
        promotion_id="promotion-pr3-promote",
        git=FakeGit(),
        github=github,
    )

    assert receipt["pull_request_draft"] is False
    assert receipt["ready_for_review_operation_used"] is False
    assert receipt["merge_ready"] is False
    assert any(call[:2] == ["pr", "create"] for call in github.calls)
    assert not any(
        call[:2] in (["pr", "ready"], ["pr", "review"], ["pr", "merge"]) for call in github.calls
    )
