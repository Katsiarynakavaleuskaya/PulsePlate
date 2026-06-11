"""Metadata-only shadow reuse telemetry for orchestration task packets.

This module is intentionally non-serving. It reads prior local task-packet
artifacts as shadow candidates, builds SC-G2 exact/fuzzy records only in memory,
and emits redacted telemetry for repeated coordinator/reviewer packet shape on
the same Git head.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import json
from pathlib import Path
import re
from typing import TypeAlias

from core.ai.cache_observability import (
    build_token_economy_estimate,
    to_stable_mapping as cache_observability_to_stable_mapping,
)
from core.ai.exact_fuzzy_cache import (
    MATCH_DECISION_HIT,
    MATCH_MODE_EXACT,
    ExactFuzzyCacheLookupRequest,
    ExactFuzzyMatchPolicy,
    build_exact_fuzzy_lineage,
    create_exact_fuzzy_cache_record,
    match_exact_fuzzy_records,
)
from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration.context_pack import REPO_ROOT

JsonScalar: TypeAlias = str | int | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]

SHADOW_REUSE_POLICY_VERSION = "orchestration-shadow-reuse-v1"
SHADOW_REUSE_FIELD = "orchestration_shadow_reuse_telemetry"
SHADOW_REUSE_AUTHORITY_BOUNDARY = "metadata_only_non_serving"
SEMANTIC_CACHE_GATE_STATUS = "closed"
SHADOW_REUSE_SURFACE = "orchestration_packet"
SHADOW_REUSE_PROVIDER_KEY = "provider:orchestration-local"
SHADOW_REUSE_MODEL_KEY = "model:bootstrap"
SHADOW_REUSE_USER_TIER = "internal"
SHADOW_REUSE_TRANSPARENCY_NOTICE_ID = "notice:orchestration-shadow-reuse:v1"
ESTIMATE_ALGORITHM_VERSION = "heuristic-chars-div4-v1"
COST_ESTIMATE_POLICY_VERSION = "zero-serving-cost-v1"
DETERMINISTIC_PRODUCED_AT = "1970-01-01T00:00:00Z"
MAX_TASK_PACKET_ARTIFACTS = 50
MAX_TASK_PACKET_ARTIFACT_BYTES = 256_000

_HEAD_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def resolve_current_head_sha(repo_root: Path = REPO_ROOT) -> str | None:
    """Resolve the current Git HEAD SHA from read-only local Git metadata."""

    git_dir = _resolve_git_metadata_dir(repo_root)
    if git_dir is None:
        return None
    return _resolve_head_sha_from_git_dir(git_dir)


def _resolve_git_metadata_dir(repo_root: Path) -> Path | None:
    dot_git = repo_root / ".git"
    try:
        if dot_git.is_dir():
            return dot_git.resolve()
        if not dot_git.is_file():
            return None
        content = dot_git.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    prefix = "gitdir:"
    if not content.startswith(prefix):
        return None
    raw_git_dir = content[len(prefix) :].strip()
    if not raw_git_dir:
        return None
    candidate = Path(raw_git_dir)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    try:
        resolved = candidate.resolve()
    except OSError:
        return None
    return resolved if resolved.is_dir() else None


def _resolve_head_sha_from_git_dir(git_dir: Path) -> str | None:
    head = _read_git_metadata_file(git_dir / "HEAD")
    if head is None:
        return None
    direct_sha = _normalize_head_sha(head.strip())
    if direct_sha is not None:
        return direct_sha
    ref_prefix = "ref:"
    if not head.startswith(ref_prefix):
        return None
    ref_name = head[len(ref_prefix) :].strip()
    ref_parts = _safe_git_ref_parts(ref_name)
    if ref_parts is None:
        return None

    candidate_dirs = [git_dir]
    common_dir = _resolve_common_git_dir(git_dir)
    if common_dir is not None and common_dir != git_dir:
        candidate_dirs.append(common_dir)
    for candidate_dir in candidate_dirs:
        ref_sha = _read_git_metadata_file(candidate_dir.joinpath(*ref_parts))
        normalized = _normalize_head_sha(ref_sha.strip() if ref_sha else None)
        if normalized is not None:
            return normalized
    return _resolve_packed_ref_sha(
        ref_name=ref_name,
        candidate_dirs=candidate_dirs,
    )


def _resolve_common_git_dir(git_dir: Path) -> Path | None:
    raw_common_dir = _read_git_metadata_file(git_dir / "commondir")
    if raw_common_dir is None:
        return None
    candidate = Path(raw_common_dir.strip())
    if not candidate.is_absolute():
        candidate = git_dir / candidate
    try:
        resolved = candidate.resolve()
    except OSError:
        return None
    return resolved if resolved.is_dir() else None


def _resolve_packed_ref_sha(*, ref_name: str, candidate_dirs: Sequence[Path]) -> str | None:
    for candidate_dir in candidate_dirs:
        packed_refs = _read_git_metadata_file(candidate_dir / "packed-refs")
        if packed_refs is None:
            continue
        for raw_line in packed_refs.splitlines():
            line = raw_line.strip()
            if not line or line.startswith(("#", "^")):
                continue
            sha, _, packed_ref = line.partition(" ")
            if packed_ref.strip() == ref_name:
                normalized = _normalize_head_sha(sha)
                if normalized is not None:
                    return normalized
    return None


def _read_git_metadata_file(path: Path) -> str | None:
    try:
        if not path.is_file() or path.is_symlink():
            return None
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None


def _safe_git_ref_parts(ref_name: str) -> tuple[str, ...] | None:
    candidate = Path(ref_name)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    if not ref_name.startswith("refs/"):
        return None
    parts = tuple(part for part in candidate.parts if part)
    if len(parts) < 3 or any(part in {".", ".."} for part in parts):
        return None
    return parts


def collect_previous_task_packet_candidates(
    *,
    task_packet_dir: Path,
    repo_root: Path = REPO_ROOT,
    current_task_packet_id: str | None = None,
    max_files: int = MAX_TASK_PACKET_ARTIFACTS,
    max_file_bytes: int = MAX_TASK_PACKET_ARTIFACT_BYTES,
) -> tuple[list[dict[str, JsonValue]], dict[str, JsonValue]]:
    """Load bounded prior packet artifacts as local shadow candidates."""

    stats: dict[str, JsonValue] = {
        "status": "not_found",
        "candidate_files_seen": 0,
        "candidate_files_loaded": 0,
        "candidate_files_skipped": 0,
        "max_files": max_files,
        "max_file_bytes": max_file_bytes,
    }
    if max_files < 0 or max_file_bytes < 0:
        raise ValueError("max_files and max_file_bytes must be non-negative")

    packet_dir = task_packet_dir.resolve()
    repo_root = repo_root.resolve()
    if not packet_dir.exists():
        return [], stats
    try:
        packet_dir.relative_to(repo_root)
    except ValueError:
        stats["status"] = "outside_repo"
        return [], stats

    packets: list[dict[str, JsonValue]] = []
    seen = 0
    skipped = 0
    for path in sorted(packet_dir.glob("*.json")):
        if seen >= max_files:
            skipped += 1
            continue
        seen += 1
        try:
            resolved = path.resolve()
            resolved.relative_to(packet_dir)
            resolved.relative_to(repo_root)
            if path.is_symlink():
                skipped += 1
                continue
            stat = path.stat()
            if stat.st_size > max_file_bytes:
                skipped += 1
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
            skipped += 1
            continue
        if not isinstance(payload, dict):
            skipped += 1
            continue
        task_packet_id = _string_or_empty(payload.get("task_packet_id"))
        if current_task_packet_id and task_packet_id == current_task_packet_id:
            skipped += 1
            continue
        packets.append(dict(payload))

    stats["status"] = "loaded"
    stats["candidate_files_seen"] = seen
    stats["candidate_files_loaded"] = len(packets)
    stats["candidate_files_skipped"] = skipped
    return packets, stats


def build_shadow_reuse_telemetry(
    *,
    packet: Mapping[str, object],
    current_head_sha: str | None,
    previous_packets: Iterable[Mapping[str, object]] = (),
    artifact_scan: Mapping[str, object] | None = None,
) -> dict[str, JsonValue]:
    """Build redacted non-serving shadow reuse telemetry for a task packet."""

    head_sha = _normalize_head_sha(current_head_sha)
    current_summary = _packet_summary(packet)
    previous_summaries = tuple(_packet_summary(candidate) for candidate in previous_packets)
    scan = _safe_artifact_scan(artifact_scan)
    reason_codes: list[str] = [
        "semantic_cache_gate_closed",
        "metadata_only",
        "non_serving",
        "no_provider_call",
        "no_cache_read",
        "no_cache_write",
    ]

    if head_sha is None:
        reason_codes.append("head_unavailable")
        return _telemetry_mapping(
            packet=current_summary,
            head_sha=None,
            evaluation_allowed=False,
            decision="miss",
            matched_packet_id=None,
            match_mode=None,
            score_bps=None,
            checked_previous_packet_count=0,
            skipped_previous_packet_count=len(previous_summaries),
            estimated_reusable_context_tokens=0,
            artifact_scan=scan,
            reason_codes=reason_codes,
        )

    scoped_candidates: list[Mapping[str, JsonValue]] = []
    skipped = 0
    for summary in previous_summaries:
        candidate_head = _candidate_head_sha(summary)
        if candidate_head != head_sha:
            skipped += 1
            continue
        scoped_candidates.append(summary)

    if not scoped_candidates:
        reason_codes.append("no_same_head_candidates")
        return _telemetry_mapping(
            packet=current_summary,
            head_sha=head_sha,
            evaluation_allowed=True,
            decision="miss",
            matched_packet_id=None,
            match_mode=None,
            score_bps=None,
            checked_previous_packet_count=0,
            skipped_previous_packet_count=skipped,
            estimated_reusable_context_tokens=0,
            artifact_scan=scan,
            reason_codes=reason_codes,
        )

    current_request = _lookup_request_for_summary(current_summary, head_sha=head_sha)
    candidate_records = []
    record_to_packet_id: dict[str, str] = {}
    for candidate in scoped_candidates:
        record = _record_for_summary(candidate, head_sha=head_sha)
        candidate_records.append(record)
        record_to_packet_id[record.record_id] = _string_or_empty(candidate.get("task_packet_id"))

    lookup_result = match_exact_fuzzy_records(
        request=current_request,
        candidate_records=candidate_records,
        policy=ExactFuzzyMatchPolicy(
            policy_version=SHADOW_REUSE_POLICY_VERSION,
            token_jaccard_min_bps=6500,
            sequence_ratio_min_bps=8000,
            max_token_count_delta=12,
        ),
    )
    if lookup_result.decision != MATCH_DECISION_HIT:
        reason_codes.extend(lookup_result.reason_codes)
        return _telemetry_mapping(
            packet=current_summary,
            head_sha=head_sha,
            evaluation_allowed=True,
            decision="miss",
            matched_packet_id=None,
            match_mode=None,
            score_bps=None,
            checked_previous_packet_count=lookup_result.checked_record_count,
            skipped_previous_packet_count=skipped,
            estimated_reusable_context_tokens=0,
            artifact_scan=scan,
            reason_codes=reason_codes,
        )

    matched_packet_id = record_to_packet_id.get(lookup_result.matched_record_id or "")
    estimated_tokens = _estimated_reusable_context_tokens(current_summary)
    reason_codes.extend(lookup_result.reason_codes)
    reason_codes.append("estimate_only_token_savings")
    return _telemetry_mapping(
        packet=current_summary,
        head_sha=head_sha,
        evaluation_allowed=True,
        decision="hit",
        matched_packet_id=matched_packet_id,
        match_mode=lookup_result.match_mode,
        score_bps=lookup_result.score_bps,
        checked_previous_packet_count=lookup_result.checked_record_count,
        skipped_previous_packet_count=skipped,
        estimated_reusable_context_tokens=estimated_tokens,
        artifact_scan=scan,
        reason_codes=reason_codes,
    )


def _telemetry_mapping(
    *,
    packet: Mapping[str, JsonValue],
    head_sha: str | None,
    evaluation_allowed: bool,
    decision: str,
    matched_packet_id: str | None,
    match_mode: str | None,
    score_bps: int | None,
    checked_previous_packet_count: int,
    skipped_previous_packet_count: int,
    estimated_reusable_context_tokens: int,
    artifact_scan: Mapping[str, JsonValue],
    reason_codes: Sequence[str],
) -> dict[str, JsonValue]:
    deduped_reasons = list(dict.fromkeys(reason_codes))
    economy = build_token_economy_estimate(
        surface=SHADOW_REUSE_SURFACE,
        route_type="orchestration_shadow_reuse",
        provider_label="orchestration-local",
        model_label="bootstrap",
        token_estimate_version=ESTIMATE_ALGORITHM_VERSION,
        prompt_input_chars=0,
        prompt_output_chars=0,
        prompt_input_tokens_estimate=0,
        prompt_output_tokens_estimate=0,
        baseline_context_tokens_estimate=estimated_reusable_context_tokens,
        candidate_context_tokens_estimate=(
            0 if decision == "hit" else estimated_reusable_context_tokens
        ),
        tokens_saved_estimate=estimated_reusable_context_tokens if decision == "hit" else 0,
        orchestration_fanout_multiplier=max(1, _int_value(packet.get("role_count"))),
        provider_calls_avoided_count=0,
        cost_saved_microunits=0,
        cost_estimate_policy_version=COST_ESTIMATE_POLICY_VERSION,
        currency_code="XXX",
        reason_codes=deduped_reasons,
        produced_at=DETERMINISTIC_PRODUCED_AT,
    )
    economy_mapping = cache_observability_to_stable_mapping(economy)
    safe_reason_codes: list[JsonValue] = [reason for reason in deduped_reasons]
    packet_fingerprint = _fingerprint(
        {
            "candidate_path_count": packet.get("candidate_path_count", 0),
            "domain": packet.get("domain", ""),
            "required_context_count": packet.get("required_context_count", 0),
            "role_fingerprint": packet.get("role_fingerprint", ""),
            "task_class": packet.get("task_class", ""),
        }
    )
    telemetry_id = f"shadow-reuse:{_fingerprint([packet_fingerprint, head_sha, decision])[:24]}"
    head_partition: dict[str, JsonValue] = {
        "status": "available" if head_sha else "unavailable",
        "head_sha": head_sha or "",
        "partition_id": f"shadow-head:{_fingerprint(head_sha or 'head-unavailable')[:24]}",
    }
    return {
        "telemetry_id": telemetry_id,
        "policy_version": SHADOW_REUSE_POLICY_VERSION,
        "authority_boundary": SHADOW_REUSE_AUTHORITY_BOUNDARY,
        "semantic_cache_gate_status": SEMANTIC_CACHE_GATE_STATUS,
        "runtime_allowed": False,
        "implementation_allowed": False,
        "cache_read_allowed": False,
        "cache_write_allowed": False,
        "serving_allowed": False,
        "same_head_partition": head_partition,
        "packet_identity": {
            "task_packet_id": _string_or_empty(packet.get("task_packet_id")),
            "packet_input_fingerprint": packet_fingerprint,
            "context_pack_id": _string_or_empty(packet.get("context_pack_id")),
            "provider_model_routing_telemetry_id": _string_or_empty(
                packet.get("provider_model_routing_telemetry_id")
            ),
        },
        "reuse_summary": {
            "evaluation_allowed": evaluation_allowed,
            "decision": decision,
            "matched_packet_id": matched_packet_id or "",
            "match_mode": match_mode or "",
            "score_bps": score_bps or 0,
            "checked_previous_packet_count": checked_previous_packet_count,
            "skipped_previous_packet_count": skipped_previous_packet_count,
            "exact_reuse_count": 1 if match_mode == MATCH_MODE_EXACT else 0,
            "fuzzy_reuse_count": 1 if decision == "hit" and match_mode != MATCH_MODE_EXACT else 0,
            "estimated_reusable_context_token_count": estimated_reusable_context_tokens,
            "token_economy_estimate_id": _string_or_empty(economy_mapping["estimate_id"]),
            "tokens_saved_estimate": _int_value(economy_mapping["tokens_saved_estimate"]),
            "provider_calls_avoided_count": 0,
            "cost_saved_microunits": 0,
        },
        "artifact_scan": dict(artifact_scan),
        "reason_codes": safe_reason_codes,
    }


def _packet_summary(packet: Mapping[str, object]) -> dict[str, JsonValue]:
    compression = packet.get("context_pack_compression")
    provider = packet.get("provider_model_tier_routing")
    telemetry = packet.get(SHADOW_REUSE_FIELD)
    return {
        "task_packet_id": _string_or_empty(packet.get("task_packet_id")),
        "task_class": _string_or_empty(packet.get("task_class")),
        "domain": _string_or_empty(packet.get("domain")),
        "cluster": _string_or_empty(packet.get("cluster")),
        "pr_phase": _string_or_empty(packet.get("pr_phase")),
        "candidate_path_count": len(_string_sequence(packet.get("candidate_paths"))),
        "required_context_count": len(_string_sequence(packet.get("required_context"))),
        "requested_agent_count": len(_string_sequence(packet.get("requested_agents"))),
        "role_count": len(
            set(
                [
                    _string_or_empty(packet.get("primary_agent")),
                    _string_or_empty(packet.get("reviewer")),
                    *_string_sequence(packet.get("secondary_agents")),
                ]
            )
            - {""}
        ),
        "context_pack_id": _mapping_string(compression, "context_pack_id"),
        "provider_model_routing_telemetry_id": _mapping_string(provider, "telemetry_id"),
        "role_fingerprint": _fingerprint(
            {
                "primary_agent": _string_or_empty(packet.get("primary_agent")),
                "reviewer": _string_or_empty(packet.get("reviewer")),
                "secondary_agents": _string_sequence(packet.get("secondary_agents")),
                "requested_agents": _string_sequence(packet.get("requested_agents")),
            }
        ),
        "query_material": _query_material(packet),
        "head_sha": _extract_head_sha(telemetry),
    }


def _query_material(packet: Mapping[str, object]) -> str:
    material = {
        "candidate_paths": _string_sequence(packet.get("candidate_paths")),
        "goal": _string_or_empty(packet.get("goal")),
        "pr_phase": _string_or_empty(packet.get("pr_phase")),
        "primary_agent": _string_or_empty(packet.get("primary_agent")),
        "requested_agents": _string_sequence(packet.get("requested_agents")),
        "reviewer": _string_or_empty(packet.get("reviewer")),
        "secondary_agents": _string_sequence(packet.get("secondary_agents")),
        "task_class": _string_or_empty(packet.get("task_class")),
    }
    return json.dumps(material, sort_keys=True, separators=(",", ":"))


def _lookup_request_for_summary(
    summary: Mapping[str, JsonValue],
    *,
    head_sha: str,
) -> ExactFuzzyCacheLookupRequest:
    return ExactFuzzyCacheLookupRequest(
        surface=SHADOW_REUSE_SURFACE,
        raw_query=_string_or_empty(summary.get("query_material")) or "empty-packet",
        context_fingerprint=_context_fingerprint(summary),
        source_fingerprints=(_head_fingerprint(head_sha),),
        policy_version=SHADOW_REUSE_POLICY_VERSION,
        provider_key=SHADOW_REUSE_PROVIDER_KEY,
        model_key=SHADOW_REUSE_MODEL_KEY,
        user_tier=SHADOW_REUSE_USER_TIER,
        transparency_notice_id=SHADOW_REUSE_TRANSPARENCY_NOTICE_ID,
    )


def _record_for_summary(
    summary: Mapping[str, JsonValue],
    *,
    head_sha: str,
):
    lineage = build_exact_fuzzy_lineage(
        eval_event_ids=(),
        admission_decision_id=None,
        promotion_ids=(),
        replay_entry_ids=(),
        source_fingerprints=(_head_fingerprint(head_sha),),
        policy_version=SHADOW_REUSE_POLICY_VERSION,
    )
    return create_exact_fuzzy_cache_record(
        surface=SHADOW_REUSE_SURFACE,
        raw_query=_string_or_empty(summary.get("query_material")) or "empty-packet",
        context_fingerprint=_context_fingerprint(summary),
        provider_key=SHADOW_REUSE_PROVIDER_KEY,
        model_key=SHADOW_REUSE_MODEL_KEY,
        user_tier=SHADOW_REUSE_USER_TIER,
        transparency_notice_id=SHADOW_REUSE_TRANSPARENCY_NOTICE_ID,
        lineage=lineage,
        response_fingerprint=_packet_response_fingerprint(summary),
        safety_flags=("metadata_only", "non_serving", "semantic_cache_gate_closed"),
    )


def _safe_artifact_scan(artifact_scan: Mapping[str, object] | None) -> dict[str, JsonValue]:
    if artifact_scan is None:
        artifact_scan = {}
    return {
        "status": _safe_status(artifact_scan.get("status"), default="not_scanned"),
        "candidate_files_seen": _int_value(artifact_scan.get("candidate_files_seen")),
        "candidate_files_loaded": _int_value(artifact_scan.get("candidate_files_loaded")),
        "candidate_files_skipped": _int_value(artifact_scan.get("candidate_files_skipped")),
        "max_files": _int_value(artifact_scan.get("max_files"), default=MAX_TASK_PACKET_ARTIFACTS),
        "max_file_bytes": _int_value(
            artifact_scan.get("max_file_bytes"),
            default=MAX_TASK_PACKET_ARTIFACT_BYTES,
        ),
    }


def _normalize_head_sha(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = value.strip()
    if not _HEAD_SHA_RE.match(candidate):
        return None
    return candidate


def _candidate_head_sha(summary: Mapping[str, JsonValue]) -> str | None:
    return _normalize_head_sha(_string_or_empty(summary.get("head_sha")))


def _extract_head_sha(value: object) -> str:
    if not isinstance(value, Mapping):
        return ""
    partition = value.get("same_head_partition")
    if not isinstance(partition, Mapping):
        return ""
    return _normalize_head_sha(_string_or_empty(partition.get("head_sha"))) or ""


def _context_fingerprint(summary: Mapping[str, JsonValue]) -> str:
    return str(
        fingerprint_payload(
            {
                "candidate_path_count": summary.get("candidate_path_count", 0),
                "domain": summary.get("domain", ""),
                "pr_phase": summary.get("pr_phase", ""),
                "required_context_count": summary.get("required_context_count", 0),
                "role_fingerprint": summary.get("role_fingerprint", ""),
                "task_class": summary.get("task_class", ""),
            }
        )
    )


def _packet_response_fingerprint(summary: Mapping[str, JsonValue]) -> str:
    return str(
        fingerprint_payload(
            {
                "context_pack_id": summary.get("context_pack_id", ""),
                "provider_model_routing_telemetry_id": summary.get(
                    "provider_model_routing_telemetry_id",
                    "",
                ),
                "task_packet_id": summary.get("task_packet_id", ""),
            }
        )
    )


def _head_fingerprint(head_sha: str) -> str:
    return str(fingerprint_payload({"git_head_sha": head_sha}))


def _estimated_reusable_context_tokens(summary: Mapping[str, JsonValue]) -> int:
    context_count = _int_value(summary.get("required_context_count"))
    path_count = _int_value(summary.get("candidate_path_count"))
    role_count = max(1, _int_value(summary.get("role_count")))
    return max(0, (context_count * 32 + path_count * 16) * role_count)


def _fingerprint(value: object) -> str:
    return str(fingerprint_payload(_json_safe(value)))[7:]


def _json_safe(value: object) -> JsonValue:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int):
        return value
    return str(value)


def _string_sequence(value: object) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return sorted({item.strip() for item in value if isinstance(item, str) and item.strip()})


def _mapping_string(value: object, key: str) -> str:
    if not isinstance(value, Mapping):
        return ""
    return _string_or_empty(value.get(key))


def _string_or_empty(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _int_value(value: object, *, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int) and value >= 0:
        return value
    return default


def _safe_status(value: object, *, default: str) -> str:
    raw = _string_or_empty(value)
    if raw and re.match(r"^[A-Za-z0-9_.:-]+$", raw):
        return raw
    return default
