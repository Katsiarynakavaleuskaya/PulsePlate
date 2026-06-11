"""Tests for orchestration-only shadow reuse telemetry."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.orchestration.shadow_reuse_telemetry import (
    SHADOW_REUSE_FIELD,
    build_shadow_reuse_telemetry,
    collect_previous_task_packet_candidates,
    resolve_current_head_sha,
)

HEAD_A = "a" * 40
HEAD_B = "b" * 40


def _packet(*, task_packet_id: str, goal: str) -> dict[str, object]:
    return {
        "schema_version": "2.0",
        "task_packet_id": task_packet_id,
        "goal": goal,
        "task_class": "Orchestration",
        "domain": "orchestration",
        "cluster": "ops",
        "candidate_paths": ["scripts/orchestration/task_bootstrap.py"],
        "primary_agent": "agent-coordinator",
        "secondary_agents": ["security-auditor"],
        "reviewer": "architecture-specialist",
        "requested_agents": ["agent-coordinator", "architecture-specialist"],
        "required_context": ["AGENTS.md", "RUNBOOK_AGENT.md"],
        "context_pack_compression": {"context_pack_id": "ctx-pack:111111111111111111111111"},
        "provider_model_tier_routing": {
            "telemetry_id": "provider-model-tier:111111111111111111111111"
        },
        "pr_phase": "pre_open",
    }


def _prior_packet(*, task_packet_id: str, goal: str, head_sha: str) -> dict[str, object]:
    packet = _packet(task_packet_id=task_packet_id, goal=goal)
    packet[SHADOW_REUSE_FIELD] = build_shadow_reuse_telemetry(
        packet=packet,
        current_head_sha=head_sha,
    )
    return packet


def test_first_packet_on_head_records_shadow_miss() -> None:
    telemetry = build_shadow_reuse_telemetry(
        packet=_packet(task_packet_id="current", goal="Review coordinator packet reuse"),
        current_head_sha=HEAD_A,
        previous_packets=[],
    )

    assert telemetry["semantic_cache_gate_status"] == "closed"
    assert telemetry["runtime_allowed"] is False
    assert telemetry["implementation_allowed"] is False
    assert telemetry["cache_read_allowed"] is False
    assert telemetry["cache_write_allowed"] is False
    assert telemetry["serving_allowed"] is False
    assert telemetry["reuse_summary"]["decision"] == "miss"
    assert telemetry["reuse_summary"]["checked_previous_packet_count"] == 0
    assert "no_same_head_candidates" in telemetry["reason_codes"]


def test_repeated_same_head_packet_records_exact_shadow_hit() -> None:
    prior = _prior_packet(
        task_packet_id="stable-packet",
        goal="Review coordinator packet reuse",
        head_sha=HEAD_A,
    )
    telemetry = build_shadow_reuse_telemetry(
        packet=_packet(task_packet_id="stable-packet", goal="Review coordinator packet reuse"),
        current_head_sha=HEAD_A,
        previous_packets=[prior],
    )

    summary = telemetry["reuse_summary"]
    assert summary["decision"] == "hit"
    assert summary["matched_packet_id"] == "stable-packet"
    assert summary["match_mode"] == "exact"
    assert summary["score_bps"] == 10000
    assert summary["exact_reuse_count"] == 1
    assert summary["fuzzy_reuse_count"] == 0
    assert summary["estimated_reusable_context_token_count"] > 0
    assert summary["provider_calls_avoided_count"] == 0
    assert summary["cost_saved_microunits"] == 0


def test_reordered_same_head_packet_records_fuzzy_shadow_hit() -> None:
    prior = _prior_packet(
        task_packet_id="prior-fuzzy",
        goal="coordinate reviewer task packet reuse",
        head_sha=HEAD_A,
    )
    telemetry = build_shadow_reuse_telemetry(
        packet=_packet(
            task_packet_id="current-fuzzy", goal="reviewer task packet coordinate reuse"
        ),
        current_head_sha=HEAD_A,
        previous_packets=[prior],
    )

    summary = telemetry["reuse_summary"]
    assert summary["decision"] == "hit"
    assert summary["matched_packet_id"] == "prior-fuzzy"
    assert summary["match_mode"] in {"fuzzy_reordered_tokens", "fuzzy_near_duplicate"}
    assert summary["fuzzy_reuse_count"] == 1


def test_different_head_sha_is_hard_shadow_miss() -> None:
    prior = _prior_packet(
        task_packet_id="other-head",
        goal="Review coordinator packet reuse",
        head_sha=HEAD_B,
    )
    telemetry = build_shadow_reuse_telemetry(
        packet=_packet(task_packet_id="current", goal="Review coordinator packet reuse"),
        current_head_sha=HEAD_A,
        previous_packets=[prior],
    )

    summary = telemetry["reuse_summary"]
    assert summary["decision"] == "miss"
    assert summary["checked_previous_packet_count"] == 0
    assert summary["skipped_previous_packet_count"] == 1
    assert "no_same_head_candidates" in telemetry["reason_codes"]


def test_shadow_telemetry_excludes_raw_payload_paths_and_runtime_authority() -> None:
    raw_goal = "Raw prompt /Users/example/project secret sk-test response should not leak"
    telemetry = build_shadow_reuse_telemetry(
        packet=_packet(task_packet_id="sensitive", goal=raw_goal),
        current_head_sha="BAD-HEAD",
        previous_packets=[],
    )
    serialized = json.dumps(telemetry, sort_keys=True).lower()

    assert raw_goal.lower() not in serialized
    assert "/users/" not in serialized
    assert "sk-test" not in serialized
    assert "raw_prompt" not in serialized
    assert "raw query" not in serialized
    assert "normalized_query" not in serialized
    assert "token_sort_key" not in serialized
    assert "response_fingerprint" not in serialized
    assert "bad-head" not in serialized
    assert telemetry["reuse_summary"]["evaluation_allowed"] is False
    assert telemetry["same_head_partition"]["head_sha"] == ""
    assert telemetry["runtime_allowed"] is False
    assert telemetry["serving_allowed"] is False


def test_collect_previous_task_packet_candidates_is_bounded_and_redacted(tmp_path: Path) -> None:
    repo_root = tmp_path
    packet_dir = repo_root / "artifacts" / "orchestration" / "task_packets"
    packet_dir.mkdir(parents=True)
    valid = _prior_packet(task_packet_id="prior", goal="Review packet reuse", head_sha=HEAD_A)
    (packet_dir / "01-valid.json").write_text(json.dumps(valid), encoding="utf-8")
    (packet_dir / "02-current.json").write_text(
        json.dumps(_packet(task_packet_id="current", goal="skip me")),
        encoding="utf-8",
    )
    (packet_dir / "03-large.json").write_text("{" + (" " * 20_000) + "}", encoding="utf-8")
    (packet_dir / "04-malformed.json").write_text("{not-json", encoding="utf-8")

    packets, stats = collect_previous_task_packet_candidates(
        task_packet_dir=packet_dir,
        repo_root=repo_root,
        current_task_packet_id="current",
        max_files=10,
        max_file_bytes=10_000,
    )

    assert [packet["task_packet_id"] for packet in packets] == ["prior"]
    assert stats["candidate_files_loaded"] == 1
    assert stats["candidate_files_skipped"] == 3
    assert "path" not in json.dumps(stats, sort_keys=True).lower()


def test_collect_previous_task_packet_candidates_caps_scanned_files(tmp_path: Path) -> None:
    repo_root = tmp_path
    packet_dir = repo_root / "artifacts" / "orchestration" / "task_packets"
    packet_dir.mkdir(parents=True)
    for index in range(5):
        packet = _prior_packet(
            task_packet_id=f"prior-{index}",
            goal=f"Review packet reuse {index}",
            head_sha=HEAD_A,
        )
        (packet_dir / f"{index:02d}-prior.json").write_text(
            json.dumps(packet),
            encoding="utf-8",
        )

    packets, stats = collect_previous_task_packet_candidates(
        task_packet_dir=packet_dir,
        repo_root=repo_root,
        max_files=3,
        max_file_bytes=10_000,
    )

    assert [packet["task_packet_id"] for packet in packets] == [
        "prior-0",
        "prior-1",
        "prior-2",
    ]
    assert stats["candidate_files_seen"] == 3
    assert stats["candidate_files_loaded"] == 3
    assert stats["candidate_files_skipped"] == 2
    assert "prior-3" not in json.dumps(stats, sort_keys=True)
    assert "path" not in json.dumps(stats, sort_keys=True).lower()


def test_resolve_current_head_sha_reads_loose_git_ref(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    git_dir = repo_root / ".git"
    ref_dir = git_dir / "refs" / "heads"
    ref_dir.mkdir(parents=True)
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (ref_dir / "main").write_text(f"{HEAD_A}\n", encoding="utf-8")

    assert resolve_current_head_sha(repo_root) == HEAD_A


def test_resolve_current_head_sha_reads_worktree_common_ref(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    common_dir = tmp_path / "main.git"
    worktree_dir = common_dir / "worktrees" / "shadow"
    (common_dir / "refs" / "heads").mkdir(parents=True)
    worktree_dir.mkdir(parents=True)
    repo_root.mkdir()
    (repo_root / ".git").write_text(f"gitdir: {worktree_dir}\n", encoding="utf-8")
    (worktree_dir / "HEAD").write_text("ref: refs/heads/shadow\n", encoding="utf-8")
    (worktree_dir / "commondir").write_text("../..\n", encoding="utf-8")
    (common_dir / "refs" / "heads" / "shadow").write_text(f"{HEAD_B}\n", encoding="utf-8")

    assert resolve_current_head_sha(repo_root) == HEAD_B


def test_resolve_current_head_sha_rejects_unsafe_ref(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    git_dir = repo_root / ".git"
    git_dir.mkdir(parents=True)
    (git_dir / "HEAD").write_text("ref: ../outside\n", encoding="utf-8")

    assert resolve_current_head_sha(repo_root) is None
