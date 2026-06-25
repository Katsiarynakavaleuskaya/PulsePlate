from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any

import pytest

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration import (
    creative_code_patch_builder,
    creative_code_patch_executor,
    creative_code_patch_workspace,
)
from scripts.orchestration.creative_code_patch_builder import CreativeCodePatchBuilderError
from scripts.orchestration.creative_code_patch_contract import (
    CreativeCodePatchContractError,
    build_creative_code_patch_build_request,
    build_creative_code_patch_result,
    read_creative_code_patch_build_request,
    validate_creative_code_patch_build_request,
    validate_creative_code_patch_result,
)
from scripts.orchestration.creative_code_specification import (
    read_creative_code_specification_bundle,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_BUNDLE = REPO_ROOT / "docs/orchestration/contracts/creative_code_specification.v1.json"
REQUEST_SCHEMA = (
    REPO_ROOT / "docs/orchestration/contracts/creative_code_patch_request.v1.schema.json"
)
RESULT_SCHEMA = REPO_ROOT / "docs/orchestration/contracts/creative_code_patch_result.v1.schema.json"


def _git(repo: Path, *args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    git_binary = shutil.which("git")
    if not git_binary:
        raise AssertionError("git binary is required for creative-code patch tests.")
    if git_binary.endswith("/usr/libexec/git-core/git"):
        git_binary = "/usr/bin/git"
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    return subprocess.run(
        [git_binary, *args],
        cwd=str(repo),
        env=env,
        input=input_text,
        capture_output=True,
        text=True,
        check=True,
    )


def _init_patch_repo(tmp_path: Path, *, include_target_file: bool = True) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    (repo / "core" / "rag").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "docs" / "orchestration").mkdir(parents=True)
    (repo / ".gitignore").write_text("artifacts/\n", encoding="utf-8")
    if include_target_file:
        (repo / "core" / "rag" / "orchestration.py").write_text(
            "def value() -> int:\n    return 1\n",
            encoding="utf-8",
        )
    (repo / "tests" / "test_creative_code_patch_builder.py").write_text(
        "def test_placeholder() -> None:\n    assert True\n",
        encoding="utf-8",
    )
    (repo / "docs" / "orchestration" / "GOVERNED_CREATIVE_CODE_EXECUTION_CONTRACT.md").write_text(
        "# Contract\n",
        encoding="utf-8",
    )
    _git(tmp_path, "init", "--quiet", str(repo))
    _git(repo, "config", "user.email", "pulseplate@pm.me")
    _git(repo, "config", "user.name", "PulsePlate")
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "init")
    base_sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
    _git(repo, "update-ref", "refs/remotes/origin/main", base_sha)
    return repo, base_sha


def _patch_modules_to_repo(monkeypatch: pytest.MonkeyPatch, repo: Path) -> None:
    artifact_root = repo / "artifacts" / "orchestration" / "creative_code" / "patch_runs"
    monkeypatch.setattr(creative_code_patch_workspace, "REPO_ROOT", repo)
    monkeypatch.setattr(creative_code_patch_workspace, "ARTIFACT_ROOT", artifact_root)
    monkeypatch.setattr(creative_code_patch_builder, "REPO_ROOT", repo)


def _reference_bundle() -> dict[str, Any]:
    return read_creative_code_specification_bundle(REFERENCE_BUNDLE)


def _reference_request() -> dict[str, Any]:
    return _request_for_base("a" * 40)


def _reference_result() -> dict[str, Any]:
    return build_creative_code_patch_result(
        request=_reference_request(),
        changed_paths=["core/rag/orchestration.py"],
        patch_fingerprint="sha256:" + ("b" * 64),
        patch_bytes=128,
        diff_lines=8,
        runner_result={
            "experiment_id": "exp-pr2-reference",
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
        },
        checkout_destroyed=True,
        origin_removed=True,
        shared_tree_untouched=True,
    )


def _request_for_base(base_sha: str) -> dict[str, Any]:
    return build_creative_code_patch_build_request(
        source_bundle=_reference_bundle(),
        base_commit_sha=base_sha,
        approval_ref="PR-2-test-approval",
        allowed_existing_paths=["core/rag/orchestration.py"],
        allowed_new_paths=[],
        oracle_commands=["pytest -q tests/test_creative_code_patch_builder.py"],
        metrics=[
            "candidate patch stays inside allowlisted surface",
            "candidate patch preserves immutable oracle commands",
        ],
        budgets={
            "generation_attempts": 1,
            "generation_timeout_seconds": 60,
            "evaluation_timeout_seconds": 60,
            "max_changed_files": 3,
            "max_diff_lines": 200,
            "max_patch_bytes": 20000,
        },
    )


def test_reference_patch_contracts_validate_and_schema_is_closed() -> None:
    request = _reference_request()
    result = _reference_result()
    bundle = _reference_bundle()
    request_schema = json.loads(REQUEST_SCHEMA.read_text(encoding="utf-8"))
    result_schema = json.loads(RESULT_SCHEMA.read_text(encoding="utf-8"))

    assert validate_creative_code_patch_build_request(request, source_bundle=bundle) == request
    assert validate_creative_code_patch_result(result) == result
    assert request_schema["additionalProperties"] is False
    assert result_schema["additionalProperties"] is False
    assert request_schema["$defs"]["authority"]["additionalProperties"] is False
    assert request_schema["$defs"]["executor"]["additionalProperties"] is False
    assert result_schema["$defs"]["runner_summary"]["additionalProperties"] is False
    assert result_schema["$defs"]["authority"]["properties"]["write_repository"]["const"] is False
    assert result_schema["$defs"]["failure_class"]["enum"] == [
        None,
        "timeout",
        "oom",
        "metric_regression",
        "guard_failure",
        "policy_violation",
        "unchanged_result",
        "infra_flake",
    ]
    assert result_schema["properties"]["failure_class"]["$ref"].endswith("failure_class")
    assert result_schema["$defs"]["runner_summary"]["properties"]["failure_class"]["$ref"].endswith(
        "failure_class"
    )
    assert (
        result_schema["$defs"]["authority"]["properties"]["candidate_patch_generated"]["const"]
        is True
    )
    assert (
        result_schema["$defs"]["authority"]["properties"]["candidate_patch_evaluated"]["const"]
        is True
    )
    assert request_schema["properties"]["allowed_existing_paths"]["$ref"].endswith(
        "path_array_allow_empty"
    )


def test_patch_path_schemas_match_validator_for_forbidden_surfaces() -> None:
    request_schema = json.loads(REQUEST_SCHEMA.read_text(encoding="utf-8"))
    result_schema = json.loads(RESULT_SCHEMA.read_text(encoding="utf-8"))
    request_pattern = re.compile(request_schema["$defs"]["repo_path"]["pattern"])
    result_pattern = re.compile(result_schema["$defs"]["repo_path"]["pattern"])
    forbidden_paths = [
        "AGENTS.md",
        "RUNBOOK_AGENT.md",
        ".github/workflows/ci.yml",
        ".mypy_cache/cache.json",
        ".pytest_cache/v/cache/nodeids",
        ".ruff_cache/cache",
        ".venv/bin/python",
        "artifacts/orchestration/result.json",
        "build/output.txt",
        "dist/package.whl",
        "docs/orchestration/GOVERNED_CREATIVE_CODE_EXECUTION_CONTRACT.md",
        "docs/review/PR_2022_FIXED_MAPPING.md",
        "frontend/src/App.tsx",
        "ios/PulsePlate/App.swift",
        "node_modules/pkg/index.js",
        "scripts/ci/check.py",
        "tests/test_example.py",
        "worktrees/lane/file.py",
    ]
    allowed_path = "core/rag/orchestration.py"

    for path in forbidden_paths:
        assert not request_pattern.fullmatch(path), path
        assert not result_pattern.fullmatch(path), path
        request = _reference_request()
        request["allowed_existing_paths"] = [path]
        with pytest.raises(CreativeCodePatchContractError, match="forbidden patch surface"):
            validate_creative_code_patch_build_request(
                request,
                source_bundle=_reference_bundle(),
            )

    assert request_pattern.fullmatch(allowed_path)
    assert result_pattern.fullmatch(allowed_path)


def test_patch_request_allows_allowed_new_only_requests() -> None:
    request = build_creative_code_patch_build_request(
        source_bundle=_reference_bundle(),
        base_commit_sha="a" * 40,
        approval_ref="PR-2-test-approval",
        allowed_existing_paths=[],
        allowed_new_paths=["core/rag/orchestration.py"],
        oracle_commands=["pytest -q tests/test_creative_code_patch_builder.py"],
        metrics=["candidate patch supports allowed-new-only requests"],
        budgets={
            "generation_attempts": 1,
            "generation_timeout_seconds": 60,
            "evaluation_timeout_seconds": 60,
            "max_changed_files": 3,
            "max_diff_lines": 200,
            "max_patch_bytes": 20000,
        },
    )

    validated = validate_creative_code_patch_build_request(
        request,
        source_bundle=_reference_bundle(),
    )

    assert validated["allowed_existing_paths"] == []
    assert validated["allowed_new_paths"] == ["core/rag/orchestration.py"]


def test_patch_request_rejects_duplicate_keys(tmp_path: Path) -> None:
    duplicate = tmp_path / "request.json"
    duplicate.write_text('{"schema_version":"1.0","schema_version":"1.0"}', encoding="utf-8")

    with pytest.raises(CreativeCodePatchContractError, match="duplicate JSON key"):
        read_creative_code_patch_build_request(str(duplicate))


def test_patch_request_requires_human_admission_and_bundle_fingerprint() -> None:
    request = _reference_request()
    bundle = _reference_bundle()
    request["source_bundle_fingerprint"] = "sha256:" + "0" * 64

    with pytest.raises(CreativeCodePatchContractError, match="source_bundle_fingerprint"):
        validate_creative_code_patch_build_request(request, source_bundle=bundle)

    request = _reference_request()
    admission = request["human_admission"]
    assert isinstance(admission, dict)
    admission["decision"] = "pending"

    with pytest.raises(CreativeCodePatchContractError, match="approved_for_sandbox_generation"):
        validate_creative_code_patch_build_request(request, source_bundle=bundle)


def test_patch_result_rejects_truthy_strings_and_invalid_runner_fingerprint() -> None:
    result = _reference_result()
    result["workspace_summary"]["origin_removed"] = "true"

    with pytest.raises(CreativeCodePatchContractError, match="origin_removed"):
        validate_creative_code_patch_result(result)

    result = _reference_result()
    result["runner_summary"]["runner_error_present"] = True
    result["runner_summary"]["runner_error_fingerprint"] = "raw runner error"

    with pytest.raises(CreativeCodePatchContractError, match="runner_error_fingerprint"):
        validate_creative_code_patch_result(result)


def test_executor_builds_fixed_argv_and_strips_secret_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    captured: dict[str, Any] = {}

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured["args"] = args
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(
            args=args[0], returncode=0, stdout='{"ok": true}\n', stderr=""
        )

    monkeypatch.setattr(creative_code_patch_executor, "resolve_codex_binary", lambda: "/bin/codex")
    monkeypatch.setattr(creative_code_patch_executor.subprocess, "run", fake_run)
    openai_key_name = "OPENAI_" + "API_KEY"
    gh_token_name = "GH_" + "TOKEN"

    metadata = creative_code_patch_executor.run_codex_exec(
        checkout=checkout,
        prompt="build patch",
        timeout_seconds=5,
        env={
            "PATH": "/bin",
            "HOME": "/home/test",
            openai_key_name: "redacted",
            gh_token_name: "redacted",
            "CODEX_HOME": "/tmp/codex-home",
        },
    )

    argv = captured["args"][0]
    kwargs = captured["kwargs"]
    assert metadata["returncode"] == 0
    assert argv == [
        "/bin/codex",
        "exec",
        "--ignore-user-config",
        "-c",
        'approval_policy="never"',
        "-c",
        "sandbox_workspace_write.network_access=false",
        "-c",
        'web_search="disabled"',
        "-c",
        "apps._default.enabled=false",
        "--sandbox",
        "workspace-write",
        "--ephemeral",
        "--json",
        "--cd",
        str(checkout),
        "-",
    ]
    assert "build patch" not in argv
    assert kwargs["input"] == "build patch"
    assert "shell" not in kwargs
    assert openai_key_name not in kwargs["env"]
    assert gh_token_name not in kwargs["env"]
    assert "CODEX_HOME" not in kwargs["env"]


def test_binary_resolvers_return_absolute_executables_for_relative_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tools = tmp_path / "tools"
    tools.mkdir()
    codex = tools / "codex"
    git = tools / "git"
    codex.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    git.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    codex.chmod(0o755)
    git.chmod(0o755)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", "tools")

    assert creative_code_patch_executor.resolve_codex_binary() == str(codex.resolve())
    assert creative_code_patch_workspace.resolve_git_binary() == str(git.resolve())


def test_workspace_creates_detached_no_remote_checkout_and_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_dir = creative_code_patch_workspace.resolve_run_dir("workspace-test", create=True)

    summary = creative_code_patch_workspace.prepare_generation_checkout(
        run_dir=run_dir,
        base_commit_sha=base_sha,
    )
    checkout = creative_code_patch_workspace.generation_checkout(run_dir)

    assert summary["detached_base_sha"] == base_sha
    assert _git(checkout, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == "HEAD"
    assert _git(checkout, "remote").stdout.strip() == ""
    assert creative_code_patch_workspace.destroy_generation_checkout(run_dir) is True
    creative_code_patch_workspace.cleanup_run_dir("workspace-test")
    assert not run_dir.exists()


def test_patch_metadata_accepts_allowed_modified_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    bundle = _reference_bundle()
    request = _request_for_base(base_sha)
    run_dir = creative_code_patch_workspace.resolve_run_dir("patch-accept", create=True)
    creative_code_patch_workspace.prepare_generation_checkout(
        run_dir=run_dir, base_commit_sha=base_sha
    )
    checkout = creative_code_patch_workspace.generation_checkout(run_dir)
    (checkout / "core" / "rag" / "orchestration.py").write_text(
        "def value() -> int:\n    return 2\n",
        encoding="utf-8",
    )

    metadata = creative_code_patch_builder._patch_metadata(
        checkout=checkout,
        run_dir=run_dir,
        request=request,
        bundle=bundle,
    )

    assert metadata["changed_paths"] == ["core/rag/orchestration.py"]
    assert metadata["patch_fingerprint"].startswith("sha256:")
    assert (run_dir / "candidate.patch").is_file()


def test_patch_metadata_rejects_unapproved_untracked_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    request = _request_for_base(base_sha)
    run_dir = creative_code_patch_workspace.resolve_run_dir("patch-untracked", create=True)
    creative_code_patch_workspace.prepare_generation_checkout(
        run_dir=run_dir, base_commit_sha=base_sha
    )
    checkout = creative_code_patch_workspace.generation_checkout(run_dir)
    (checkout / "core" / "rag" / "extra.py").write_text("x = 1\n", encoding="utf-8")

    with pytest.raises(CreativeCodePatchBuilderError, match="untracked path is not allowed"):
        creative_code_patch_builder._patch_metadata(
            checkout=checkout,
            run_dir=run_dir,
            request=request,
            bundle=_reference_bundle(),
        )


def test_patch_metadata_rejects_symlink_mode_change(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    request = _request_for_base(base_sha)
    run_dir = creative_code_patch_workspace.resolve_run_dir("patch-symlink", create=True)
    creative_code_patch_workspace.prepare_generation_checkout(
        run_dir=run_dir, base_commit_sha=base_sha
    )
    checkout = creative_code_patch_workspace.generation_checkout(run_dir)
    target = checkout / "core" / "rag" / "orchestration.py"
    target.unlink()
    target.symlink_to("target.py")

    with pytest.raises(CreativeCodePatchBuilderError, match="forbidden"):
        creative_code_patch_builder._patch_metadata(
            checkout=checkout,
            run_dir=run_dir,
            request=request,
            bundle=_reference_bundle(),
        )


def test_patch_metadata_rejects_new_executable_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path, include_target_file=False)
    _patch_modules_to_repo(monkeypatch, repo)
    request = build_creative_code_patch_build_request(
        source_bundle=_reference_bundle(),
        base_commit_sha=base_sha,
        approval_ref="PR-2-test-approval",
        allowed_existing_paths=[],
        allowed_new_paths=["core/rag/orchestration.py"],
        oracle_commands=["pytest -q tests/test_creative_code_patch_builder.py"],
        metrics=["candidate patch rejects executable new files"],
        budgets={
            "generation_attempts": 1,
            "generation_timeout_seconds": 60,
            "evaluation_timeout_seconds": 60,
            "max_changed_files": 3,
            "max_diff_lines": 200,
            "max_patch_bytes": 20000,
        },
    )
    run_dir = creative_code_patch_workspace.resolve_run_dir("patch-executable", create=True)
    creative_code_patch_workspace.prepare_generation_checkout(
        run_dir=run_dir, base_commit_sha=base_sha
    )
    checkout = creative_code_patch_workspace.generation_checkout(run_dir)
    target = checkout / "core" / "rag" / "orchestration.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("#!/usr/bin/env python3\nprint('x')\n", encoding="utf-8")
    target.chmod(0o755)

    with pytest.raises(CreativeCodePatchBuilderError, match="forbidden mode"):
        creative_code_patch_builder._patch_metadata(
            checkout=checkout,
            run_dir=run_dir,
            request=request,
            bundle=_reference_bundle(),
        )


def test_evaluate_writes_sanitized_result_without_runner_leaks(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_dir = creative_code_patch_workspace.resolve_run_dir("eval-sanitize", create=True)
    request = _request_for_base(base_sha)
    state = {
        "run_id": "eval-sanitize",
        "request_id": request["request_id"],
        "source_bundle_id": request["source_bundle_id"],
        "selected_variant_id": request["selected_variant_id"],
        "base_commit_sha": base_sha,
        "workspace": {"origin_removed": True},
        "candidate_patch_generated": True,
        "checkout_destroyed": True,
    }
    patch_text = "diff --git a/core/rag/orchestration.py b/core/rag/orchestration.py\n"
    metadata = {
        "changed_paths": ["core/rag/orchestration.py"],
        "patch_fingerprint": fingerprint_payload({"candidate_patch": patch_text}),
        "patch_bytes": len(patch_text.encode("utf-8")),
        "diff_lines": len(patch_text.splitlines()),
    }
    creative_code_patch_workspace.write_json_atomic(run_dir / "request.json", request)
    creative_code_patch_workspace.write_json_atomic(
        run_dir / "source_bundle.json", _reference_bundle()
    )
    creative_code_patch_workspace.write_json_atomic(run_dir / "state.json", state)
    creative_code_patch_workspace.write_json_atomic(run_dir / "patch_metadata.json", metadata)
    (run_dir / "candidate.patch").write_text(patch_text, encoding="utf-8")

    def fake_evaluate_candidate(
        packet: dict[str, Any], candidate_patch_path: Path
    ) -> dict[str, Any]:
        return {
            "experiment_id": packet["experiment_id"],
            "runner_mode": "candidate_patch",
            "candidate_patch": str(candidate_patch_path),
            "status": "rejected",
            "failure_class": "guard_failure",
            "mutated_paths": ["core/rag/orchestration.py"],
            "oracle_results": [
                {
                    "command": "pytest -q tests/test_creative_code_patch_builder.py",
                    "returncode": 1,
                    "timed_out": False,
                    "truncated": False,
                    "stdout": "/Users/example/raw output sk-secretsecretsecret",
                    "stderr": "diff --git leak",
                    "cwd": "/Users/example/checkout",
                }
            ],
            "budget_observations": {
                "oracle_commands_configured": 1,
                "attempts": 1,
                "retries_consumed": 0,
                "runner_error": "/Users/example/ghp_secretsecretsecret",
            },
            "shared_tree_untouched": True,
        }

    monkeypatch.setattr(creative_code_patch_builder, "evaluate_candidate", fake_evaluate_candidate)

    result = creative_code_patch_builder.evaluate(run_id="eval-sanitize")
    encoded = json.dumps(result, sort_keys=True)

    assert result["status"] == "rejected"
    assert result["runner_summary"]["runner_error_present"] is True
    assert "/Users/example" not in encoded
    assert "sk-secret" not in encoded
    assert "diff --git leak" not in encoded


def test_evaluate_rejects_tampered_candidate_patch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_dir = creative_code_patch_workspace.resolve_run_dir("eval-tamper", create=True)
    request = _request_for_base(base_sha)
    original_patch = "diff --git a/core/rag/orchestration.py b/core/rag/orchestration.py\n"
    metadata = {
        "changed_paths": ["core/rag/orchestration.py"],
        "patch_fingerprint": fingerprint_payload({"candidate_patch": original_patch}),
        "patch_bytes": len(original_patch.encode("utf-8")),
        "diff_lines": len(original_patch.splitlines()),
    }
    state = {
        "run_id": "eval-tamper",
        "request_id": request["request_id"],
        "source_bundle_id": request["source_bundle_id"],
        "selected_variant_id": request["selected_variant_id"],
        "base_commit_sha": base_sha,
        "workspace": {"origin_removed": True},
        "candidate_patch_generated": True,
        "checkout_destroyed": True,
    }
    creative_code_patch_workspace.write_json_atomic(run_dir / "request.json", request)
    creative_code_patch_workspace.write_json_atomic(
        run_dir / "source_bundle.json", _reference_bundle()
    )
    creative_code_patch_workspace.write_json_atomic(run_dir / "state.json", state)
    creative_code_patch_workspace.write_json_atomic(run_dir / "patch_metadata.json", metadata)
    (run_dir / "candidate.patch").write_text(original_patch + "# tampered\n", encoding="utf-8")

    def fail_if_called(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("evaluate_candidate must not run for tampered patches")

    monkeypatch.setattr(creative_code_patch_builder, "evaluate_candidate", fail_if_called)

    with pytest.raises(CreativeCodePatchBuilderError, match="metadata does not match"):
        creative_code_patch_builder.evaluate(run_id="eval-tamper")


def test_prepare_rejects_non_empty_run_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "prepare-stale"
    run_dir = creative_code_patch_workspace.resolve_run_dir(run_id, create=True)
    (run_dir / "candidate.patch").write_text("stale\n", encoding="utf-8")
    request = _request_for_base(base_sha)
    bundle_path = tmp_path / "bundle.json"
    request_path = tmp_path / "request.json"
    bundle_path.write_text(json.dumps(_reference_bundle()), encoding="utf-8")
    request_path.write_text(json.dumps(request), encoding="utf-8")

    with pytest.raises(CreativeCodePatchBuilderError, match="run directory must be empty"):
        creative_code_patch_builder.prepare(
            spec_bundle_path=bundle_path,
            request_path=request_path,
            run_id=run_id,
        )


def test_cli_prepare_generate_evaluate_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, base_sha = _init_patch_repo(tmp_path)
    _patch_modules_to_repo(monkeypatch, repo)
    run_id = "cli-roundtrip"
    request = _request_for_base(base_sha)
    bundle_path = tmp_path / "bundle.json"
    request_path = tmp_path / "request.json"
    bundle_path.write_text(json.dumps(_reference_bundle()), encoding="utf-8")
    request_path.write_text(json.dumps(request), encoding="utf-8")

    def fake_run_codex_exec(
        *,
        checkout: Path,
        prompt: str,
        timeout_seconds: int,
    ) -> dict[str, int]:
        assert "local candidate patch" in prompt
        assert timeout_seconds == request["budgets"]["generation_timeout_seconds"]
        (checkout / "core" / "rag" / "orchestration.py").write_text(
            "def value() -> int:\n    return 3\n",
            encoding="utf-8",
        )
        return {"returncode": 0, "stdout_lines": 1, "stderr_lines": 0}

    def fake_evaluate_candidate(
        packet: dict[str, Any], candidate_patch_path: Path
    ) -> dict[str, Any]:
        assert packet["runner_mode"] == "candidate_patch"
        assert candidate_patch_path.name == "candidate.patch"
        return {
            "experiment_id": packet["experiment_id"],
            "runner_mode": "candidate_patch",
            "candidate_patch": str(candidate_patch_path),
            "status": "accepted",
            "failure_class": None,
            "mutated_paths": ["core/rag/orchestration.py"],
            "oracle_results": [{"returncode": 0, "timed_out": False, "truncated": False}],
            "budget_observations": {
                "oracle_commands_configured": 1,
                "attempts": 1,
                "retries_consumed": 0,
            },
            "shared_tree_untouched": True,
        }

    monkeypatch.setattr(creative_code_patch_builder, "run_codex_exec", fake_run_codex_exec)
    monkeypatch.setattr(creative_code_patch_builder, "evaluate_candidate", fake_evaluate_candidate)

    assert (
        creative_code_patch_builder.main(
            [
                "prepare",
                "--spec-bundle",
                str(bundle_path),
                "--request",
                str(request_path),
                "--run-dir",
                run_id,
            ]
        )
        == 0
    )
    assert creative_code_patch_builder.main(["generate", "--run-dir", run_id]) == 0
    assert creative_code_patch_builder.main(["evaluate", "--run-dir", run_id]) == 0
    run_dir = creative_code_patch_workspace.resolve_run_dir(run_id)
    result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    assert result["status"] == "accepted"
    assert result["authority"]["open_pull_request"] is False
    assert creative_code_patch_builder.main(["cleanup", "--run-dir", run_id]) == 0
    assert not run_dir.exists()
