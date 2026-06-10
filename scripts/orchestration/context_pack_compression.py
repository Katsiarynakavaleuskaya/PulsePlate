"""Deterministic metadata-only context-pack compression helpers.

This module builds advisory orchestration context-compression telemetry. It
never stores raw prompt/context text, never calls providers, and never opens
semantic-cache runtime serving.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
from types import MappingProxyType
from typing import TypeAlias

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration.context_pack import REPO_ROOT, normalize_repo_path

JsonScalar: TypeAlias = str | int | bool | None
JsonValue: TypeAlias = (
    JsonScalar | list["JsonValue"] | tuple["JsonValue", ...] | Mapping[str, "JsonValue"]
)

CONTEXT_COMPRESSION_POLICY_VERSION = "semantic-context-compression-o2-v1"
CONTEXT_COMPRESSION_ESTIMATE_ALGORITHM_VERSION = "heuristic-chars-div4-v1"
CONTEXT_COMPRESSION_AUTHORITY_BOUNDARY = "metadata_only_non_serving"

NODE_CHANGED_FILE = "changed_file"
NODE_CONTRACT = "contract"
NODE_TEST = "test"
NODE_AGENT_RULE = "agent_rule"
NODE_REVIEW_ARTIFACT = "review_artifact"
NODE_ROADMAP = "roadmap"
NODE_TYPES = frozenset(
    {
        NODE_CHANGED_FILE,
        NODE_CONTRACT,
        NODE_TEST,
        NODE_AGENT_RULE,
        NODE_REVIEW_ARTIFACT,
        NODE_ROADMAP,
    }
)

EDGE_REQUIRES = "requires"
EDGE_VALIDATES = "validates"
EDGE_CONSTRAINS = "constrains"
EDGE_DOCUMENTS = "documents"
EDGE_REVIEWS = "reviews"
EDGE_TYPES = frozenset(
    {
        EDGE_REQUIRES,
        EDGE_VALIDATES,
        EDGE_CONSTRAINS,
        EDGE_DOCUMENTS,
        EDGE_REVIEWS,
    }
)

REASON_GATE_CLOSED = "gate_closed"
REASON_METADATA_ONLY = "metadata_only"
REASON_REQUIRED_CONTEXT_PRESERVED = "required_context_preserved"
REASON_DUPLICATE_CONTEXT_REFERENCE = "duplicate_context_reference"
REASON_ESTIMATE_ONLY = "estimate_only"
REASON_NO_CONTEXT_REDUCTION = "no_context_reduction"
REASON_MISSING_CONTEXT_FILE = "missing_context_file"
REASON_GRAPH_LIMIT_TRUNCATED = "graph_limit_truncated"
REASON_COMPRESSION_LIMIT_EXCEEDED = "compression_limit_exceeded"

MAX_NODES = 200
MAX_EDGES = 1000
MAX_METADATA_BYTES = 4096
MAX_STRING_LENGTH = 512
MAX_METADATA_DEPTH = 8

_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_NODE_ID_RE = re.compile(r"^(?:ctx-node|ctx-edge|ctx-pack|ctx-estimate):[0-9a-f]{24}$")
_FINGERPRINT_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_PATH_RE = re.compile(
    r"(?:(?:^|[\s=(;,]|:(?!//))(?:/|~[/\\]|[A-Za-z]:[\\/]|\\\\)|(?:^|[\s=(:;,])file://)"
)
_UNSAFE_METADATA_RE = re.compile(
    r"raw[_ -]?(?:query|prompt|response|answer|context)"
    r"|normalized[_ -]?query"
    r"|provider[_ -]?payload"
    r"|context[_ -]?snippet"
    r"|prompt"
    r"|response"
    r"|answer"
    r"|secret"
    r"|credential"
    r"|authorization"
    r"|api[_ -]?key"
    r"|bearer"
    r"|cookie"
    r"|set-cookie"
    r"|session[_ -]?id"
    r"|x-api-key"
    r"|private[_ -]?key"
    r"|sk-[a-z0-9]"
    r"|gh[pousr]_[a-z0-9._-]+"
    r"|github_pat_[a-z0-9._-]+"
    r"|xox[baprs]-[a-z0-9._-]+"
    r"|[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}"
    r"|\+?\d[\d ()-]{7,}\d"
    r"|healthkit"
    r"|diagnosis"
    r"|symptom"
    r"|medical"
    r"|account[_ -]?(?:id|truth)"
    r"|billing[_ -]?truth"
    r"|entitlement[_ -]?truth"
    r"|coaching[_ -]?state"
    r"|user[_ -]?health"
    r"|cheap[_ -]?model"
    r"|downgraded[_ -]?model"
    r"|fallback[_ -]?model[_ -]?for[_ -]?review"
    r"|cache[_ -]?hit"
    r"|served[_ -]?hit"
    r"|provider[_ -]?call[_ -]?avoided"
    r"|production[_ -]?(?:cost|roi)[_ -]?(?:saved|claim)"
    r"|merge[_ -]?readiness[_ -]?(?:claim|evidence)"
    r"|runtime[_ -]?enabled",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ContextGraphNode:
    """Safe context graph node for orchestration packet metadata."""

    node_id: str
    node_type: str
    path: str
    path_fingerprint: str
    token_estimate: int
    required: bool
    metadata: Mapping[str, JsonValue]

    def __post_init__(self) -> None:
        object.__setattr__(self, "node_id", _validate_derived_id("node_id", self.node_id))
        if self.node_type not in NODE_TYPES:
            raise ValueError("node_type contains unsupported value")
        object.__setattr__(self, "path", _validate_repo_relative_path(self.path))
        object.__setattr__(
            self,
            "path_fingerprint",
            _validate_fingerprint("path_fingerprint", self.path_fingerprint),
        )
        object.__setattr__(
            self,
            "token_estimate",
            _validate_non_negative_int("token_estimate", self.token_estimate),
        )
        if not isinstance(self.required, bool):
            raise ValueError("required must be boolean")
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True)
class ContextGraphEdge:
    """Safe context graph edge for non-authoritative orchestration metadata."""

    edge_id: str
    source: str
    target: str
    edge_type: str
    metadata: Mapping[str, JsonValue]

    def __post_init__(self) -> None:
        object.__setattr__(self, "edge_id", _validate_derived_id("edge_id", self.edge_id))
        object.__setattr__(self, "source", _validate_derived_id("source", self.source))
        object.__setattr__(self, "target", _validate_derived_id("target", self.target))
        if self.edge_type not in EDGE_TYPES:
            raise ValueError("edge_type contains unsupported value")
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True)
class ContextCompressionEstimate:
    """Deterministic estimate-only token reduction metadata."""

    estimate_id: str
    baseline_context_chars_estimate: int
    candidate_context_chars_estimate: int
    baseline_context_tokens_estimate: int
    candidate_context_tokens_estimate: int
    tokens_saved_estimate: int
    orchestration_fanout_multiplier: int
    fanout_tokens_saved_estimate: int
    token_estimate_version: str
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "estimate_id",
            _validate_derived_id("estimate_id", self.estimate_id),
        )
        for name in (
            "baseline_context_chars_estimate",
            "candidate_context_chars_estimate",
            "baseline_context_tokens_estimate",
            "candidate_context_tokens_estimate",
            "tokens_saved_estimate",
            "orchestration_fanout_multiplier",
            "fanout_tokens_saved_estimate",
        ):
            object.__setattr__(self, name, _validate_non_negative_int(name, getattr(self, name)))
        object.__setattr__(
            self,
            "token_estimate_version",
            _validate_token("token_estimate_version", self.token_estimate_version),
        )
        object.__setattr__(
            self,
            "reason_codes",
            _normalize_required_unique_tokens("reason_codes", self.reason_codes),
        )
        if (
            self.fanout_tokens_saved_estimate
            != self.tokens_saved_estimate * self.orchestration_fanout_multiplier
        ):
            raise ValueError(
                "fanout_tokens_saved_estimate must equal tokens_saved_estimate "
                "times orchestration_fanout_multiplier"
            )


@dataclass(frozen=True)
class CompressedContextPack:
    """Additive advisory context-compression metadata for task packets."""

    context_pack_id: str
    policy_version: str
    authority_boundary: str
    required_context: tuple[str, ...]
    selected_context_refs: tuple[Mapping[str, JsonValue], ...]
    omitted_duplicate_refs: tuple[Mapping[str, JsonValue], ...]
    graph_nodes: tuple[ContextGraphNode, ...]
    graph_edges: tuple[ContextGraphEdge, ...]
    estimate: ContextCompressionEstimate
    reason_codes: tuple[str, ...]
    metadata: Mapping[str, JsonValue]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "context_pack_id",
            _validate_derived_id("context_pack_id", self.context_pack_id),
        )
        object.__setattr__(
            self,
            "policy_version",
            _validate_token("policy_version", self.policy_version),
        )
        if self.authority_boundary != CONTEXT_COMPRESSION_AUTHORITY_BOUNDARY:
            raise ValueError("authority_boundary must be metadata_only_non_serving")
        required_context = tuple(
            _validate_repo_relative_path(path) for path in self.required_context
        )
        object.__setattr__(self, "required_context", tuple(sorted(dict.fromkeys(required_context))))
        object.__setattr__(
            self,
            "selected_context_refs",
            _freeze_mapping_tuple("selected_context_refs", self.selected_context_refs),
        )
        object.__setattr__(
            self,
            "omitted_duplicate_refs",
            _freeze_mapping_tuple("omitted_duplicate_refs", self.omitted_duplicate_refs),
        )
        nodes = tuple(sorted(self.graph_nodes, key=lambda item: item.node_id))
        edges = tuple(sorted(self.graph_edges, key=lambda item: item.edge_id))
        if len(nodes) > MAX_NODES:
            raise ValueError("graph_nodes exceeds maximum")
        if len(edges) > MAX_EDGES:
            raise ValueError("graph_edges exceeds maximum")
        _require_unique("graph_nodes", [node.node_id for node in nodes])
        _require_unique("graph_edges", [edge.edge_id for edge in edges])
        node_ids = {node.node_id for node in nodes}
        for edge in edges:
            if edge.source not in node_ids or edge.target not in node_ids:
                raise ValueError("graph_edges must reference existing graph_nodes")
        if not isinstance(self.estimate, ContextCompressionEstimate):
            raise ValueError("estimate must be ContextCompressionEstimate")
        object.__setattr__(self, "graph_nodes", nodes)
        object.__setattr__(self, "graph_edges", edges)
        object.__setattr__(
            self,
            "reason_codes",
            _normalize_required_unique_tokens("reason_codes", self.reason_codes),
        )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


def build_context_pack_compression(
    *,
    candidate_paths: Sequence[str],
    required_context: Sequence[str],
    pr_phase: str,
    domain: str,
    cluster: str,
    primary_agent: str,
    reviewer: str,
    secondary_agents: Sequence[str] = (),
    requested_agents: Sequence[str] = (),
    policy_version: str = CONTEXT_COMPRESSION_POLICY_VERSION,
    orchestration_fanout_multiplier: int = 1,
    repo_root: Path = REPO_ROOT,
) -> CompressedContextPack:
    """Build deterministic context-pack compression metadata.

    The returned pack is advisory metadata. It does not remove required context
    from the task packet and does not authorize runtime cache behavior.
    """

    normalized_policy_version = _validate_token("policy_version", policy_version)
    normalized_candidate_paths = _normalize_path_sequence("candidate_paths", candidate_paths)
    normalized_required_context, duplicate_context = _normalize_path_sequence_with_duplicates(
        "required_context",
        required_context,
    )
    normalized_pr_phase = _validate_token("pr_phase", pr_phase)
    normalized_domain = _validate_token("domain", domain)
    normalized_cluster = _validate_token("cluster", cluster)
    normalized_primary_agent = _validate_role_token("primary_agent", primary_agent)
    normalized_reviewer = _validate_role_token("reviewer", reviewer)
    normalized_secondaries = _normalize_unique_role_tokens("secondary_agents", secondary_agents)
    normalized_requested = _normalize_unique_role_tokens("requested_agents", requested_agents)
    fanout = max(
        1,
        _validate_non_negative_int(
            "orchestration_fanout_multiplier",
            orchestration_fanout_multiplier,
        ),
    )

    candidate_path_set = set(normalized_candidate_paths)
    included_required_paths = normalized_required_context[:MAX_NODES]
    remaining_node_budget = max(0, MAX_NODES - len(included_required_paths))
    included_candidate_paths = tuple(
        path for path in normalized_candidate_paths if path not in set(included_required_paths)
    )[:remaining_node_budget]
    graph_truncated = len(included_required_paths) < len(normalized_required_context) or len(
        included_candidate_paths
    ) < len(
        [path for path in normalized_candidate_paths if path not in set(included_required_paths)]
    )

    nodes_by_path: dict[str, ContextGraphNode] = {}
    for path in included_candidate_paths:
        nodes_by_path[path] = _build_node(
            path=path,
            required=False,
            candidate=True,
            repo_root=repo_root,
        )
    for path in included_required_paths:
        nodes_by_path[path] = _build_node(
            path=path,
            required=True,
            candidate=path in candidate_path_set,
            repo_root=repo_root,
        )

    nodes = tuple(nodes_by_path[path] for path in sorted(nodes_by_path))
    edges, edges_truncated = _build_edges(
        candidate_nodes=[nodes_by_path[path] for path in included_candidate_paths],
        required_nodes=[nodes_by_path[path] for path in included_required_paths],
    )
    selected_refs = tuple(
        _context_ref_mapping_for_path(
            path=path,
            node=nodes_by_path.get(path),
            repo_root=repo_root,
            status="retained" if path in nodes_by_path else "retained_without_graph_node",
            reason_code=(
                REASON_REQUIRED_CONTEXT_PRESERVED
                if path in nodes_by_path
                else REASON_GRAPH_LIMIT_TRUNCATED
            ),
        )
        for path in normalized_required_context
    )
    omitted_refs = tuple(
        _context_ref_mapping_for_path(
            path=path,
            node=nodes_by_path.get(path),
            repo_root=repo_root,
            status="duplicate_reference",
            reason_code=REASON_DUPLICATE_CONTEXT_REFERENCE,
        )
        for path in duplicate_context
    )

    baseline_chars = sum(
        _safe_context_char_count(path, repo_root=repo_root) for path in normalized_required_context
    )
    candidate_metadata_payload: JsonValue = {
        "authority_boundary": CONTEXT_COMPRESSION_AUTHORITY_BOUNDARY,
        "graph_edges": [dict(to_stable_mapping(edge)) for edge in edges],
        "graph_nodes": [dict(to_stable_mapping(node)) for node in nodes],
        "omitted_duplicate_refs": [_json_safe_copy(ref) for ref in omitted_refs],
        "policy_version": normalized_policy_version,
        "required_context": list(normalized_required_context),
        "selected_context_refs": [_json_safe_copy(ref) for ref in selected_refs],
    }
    candidate_chars = len(_canonical_json_text(candidate_metadata_payload))
    baseline_tokens = _estimate_tokens(baseline_chars)
    candidate_tokens = _estimate_tokens(candidate_chars)
    tokens_saved = max(0, baseline_tokens - candidate_tokens)
    estimate_reason_codes = {
        REASON_ESTIMATE_ONLY,
        REASON_METADATA_ONLY,
    }
    if tokens_saved == 0:
        estimate_reason_codes.add(REASON_NO_CONTEXT_REDUCTION)
    if any(not (repo_root / path).is_file() for path in normalized_required_context):
        estimate_reason_codes.add(REASON_MISSING_CONTEXT_FILE)
    if graph_truncated or edges_truncated:
        estimate_reason_codes.add(REASON_COMPRESSION_LIMIT_EXCEEDED)
    estimate_reason_code_values: list[JsonValue] = list(sorted(estimate_reason_codes))
    estimate_payload: JsonValue = {
        "baseline_context_chars_estimate": baseline_chars,
        "candidate_context_chars_estimate": candidate_chars,
        "baseline_context_tokens_estimate": baseline_tokens,
        "candidate_context_tokens_estimate": candidate_tokens,
        "fanout_tokens_saved_estimate": tokens_saved * fanout,
        "orchestration_fanout_multiplier": fanout,
        "reason_codes": estimate_reason_code_values,
        "token_estimate_version": CONTEXT_COMPRESSION_ESTIMATE_ALGORITHM_VERSION,
        "tokens_saved_estimate": tokens_saved,
    }
    estimate = ContextCompressionEstimate(
        estimate_id=f"ctx-estimate:{fingerprint_payload(estimate_payload)[7:31]}",
        baseline_context_chars_estimate=baseline_chars,
        candidate_context_chars_estimate=candidate_chars,
        baseline_context_tokens_estimate=baseline_tokens,
        candidate_context_tokens_estimate=candidate_tokens,
        tokens_saved_estimate=tokens_saved,
        orchestration_fanout_multiplier=fanout,
        fanout_tokens_saved_estimate=tokens_saved * fanout,
        token_estimate_version=CONTEXT_COMPRESSION_ESTIMATE_ALGORITHM_VERSION,
        reason_codes=tuple(sorted(estimate_reason_codes)),
    )
    pack_reason_code_set = {
        REASON_GATE_CLOSED,
        REASON_METADATA_ONLY,
        REASON_REQUIRED_CONTEXT_PRESERVED,
        REASON_ESTIMATE_ONLY,
        *(REASON_DUPLICATE_CONTEXT_REFERENCE for _ in omitted_refs),
    }
    if graph_truncated:
        pack_reason_code_set.add(REASON_GRAPH_LIMIT_TRUNCATED)
    if graph_truncated or edges_truncated:
        pack_reason_code_set.add(REASON_COMPRESSION_LIMIT_EXCEEDED)
    pack_reason_codes = tuple(sorted(pack_reason_code_set))
    pack_payload: JsonValue = {
        "authority_boundary": CONTEXT_COMPRESSION_AUTHORITY_BOUNDARY,
        "candidate_paths": normalized_candidate_paths,
        "cluster": normalized_cluster,
        "domain": normalized_domain,
        "estimate": dict(to_stable_mapping(estimate)),
        "graph_edges": [dict(to_stable_mapping(edge)) for edge in edges],
        "graph_nodes": [dict(to_stable_mapping(node)) for node in nodes],
        "policy_version": normalized_policy_version,
        "pr_phase": normalized_pr_phase,
        "primary_agent": normalized_primary_agent,
        "reason_codes": list(pack_reason_codes),
        "requested_agents": list(normalized_requested),
        "required_context": list(normalized_required_context),
        "reviewer": normalized_reviewer,
        "secondary_agents": list(normalized_secondaries),
    }
    return CompressedContextPack(
        context_pack_id=f"ctx-pack:{fingerprint_payload(pack_payload)[7:31]}",
        policy_version=normalized_policy_version,
        authority_boundary=CONTEXT_COMPRESSION_AUTHORITY_BOUNDARY,
        required_context=normalized_required_context,
        selected_context_refs=selected_refs,
        omitted_duplicate_refs=omitted_refs,
        graph_nodes=nodes,
        graph_edges=edges,
        estimate=estimate,
        reason_codes=pack_reason_codes,
        metadata={
            "cluster": normalized_cluster,
            "domain": normalized_domain,
            "pr_phase": normalized_pr_phase,
            "primary_agent": normalized_primary_agent,
            "reviewer": normalized_reviewer,
            "secondary_agent_count": len(normalized_secondaries),
            "requested_agent_count": len(normalized_requested),
            "graph_limit_truncated": graph_truncated,
            "edge_limit_truncated": edges_truncated,
            "selected_context_ref_count": len(selected_refs),
            "required_context_count": len(normalized_required_context),
        },
    )


def to_stable_mapping(value: object) -> Mapping[str, JsonValue]:
    """Return a deterministic JSON-ready mapping for compression records."""

    if isinstance(value, ContextGraphNode):
        return _freeze_mapping(
            {
                "metadata": _json_safe_copy(value.metadata),
                "node_id": value.node_id,
                "node_type": value.node_type,
                "path": value.path,
                "path_fingerprint": value.path_fingerprint,
                "required": value.required,
                "token_estimate": value.token_estimate,
            }
        )
    if isinstance(value, ContextGraphEdge):
        return _freeze_mapping(
            {
                "edge_id": value.edge_id,
                "edge_type": value.edge_type,
                "metadata": _json_safe_copy(value.metadata),
                "source": value.source,
                "target": value.target,
            }
        )
    if isinstance(value, ContextCompressionEstimate):
        return _freeze_mapping(
            {
                "baseline_context_chars_estimate": value.baseline_context_chars_estimate,
                "baseline_context_tokens_estimate": value.baseline_context_tokens_estimate,
                "candidate_context_chars_estimate": value.candidate_context_chars_estimate,
                "candidate_context_tokens_estimate": value.candidate_context_tokens_estimate,
                "estimate_id": value.estimate_id,
                "fanout_tokens_saved_estimate": value.fanout_tokens_saved_estimate,
                "orchestration_fanout_multiplier": value.orchestration_fanout_multiplier,
                "reason_codes": list(value.reason_codes),
                "token_estimate_version": value.token_estimate_version,
                "tokens_saved_estimate": value.tokens_saved_estimate,
            }
        )
    if isinstance(value, CompressedContextPack):
        return _freeze_mapping(
            {
                "authority_boundary": value.authority_boundary,
                "context_pack_id": value.context_pack_id,
                "estimate": dict(to_stable_mapping(value.estimate)),
                "graph_edges": [dict(to_stable_mapping(edge)) for edge in value.graph_edges],
                "graph_nodes": [dict(to_stable_mapping(node)) for node in value.graph_nodes],
                "metadata": _json_safe_copy(value.metadata),
                "omitted_duplicate_refs": [
                    _json_safe_copy(ref) for ref in value.omitted_duplicate_refs
                ],
                "policy_version": value.policy_version,
                "reason_codes": list(value.reason_codes),
                "required_context": list(value.required_context),
                "selected_context_refs": [
                    _json_safe_copy(ref) for ref in value.selected_context_refs
                ],
            }
        )
    raise ValueError(f"unsupported stable mapping value: {type(value).__name__}")


def _build_node(
    *,
    path: str,
    required: bool,
    candidate: bool = False,
    repo_root: Path,
) -> ContextGraphNode:
    normalized_path = _validate_repo_relative_path(path)
    path_fingerprint = fingerprint_payload({"path": normalized_path})
    token_estimate = _estimate_tokens(
        _safe_context_char_count(normalized_path, repo_root=repo_root)
    )
    node_type = _classify_node_type(normalized_path)
    payload: JsonValue = {
        "node_type": node_type,
        "path_fingerprint": path_fingerprint,
        "candidate": candidate,
        "required": required,
    }
    if required and candidate:
        status = "required_and_candidate"
    elif required:
        status = "required"
    else:
        status = "candidate"
    return ContextGraphNode(
        node_id=f"ctx-node:{fingerprint_payload(payload)[7:31]}",
        node_type=node_type,
        path=normalized_path,
        path_fingerprint=path_fingerprint,
        token_estimate=token_estimate,
        required=required,
        metadata={"candidate": candidate, "status": status},
    )


def _build_edges(
    *,
    candidate_nodes: Sequence[ContextGraphNode],
    required_nodes: Sequence[ContextGraphNode],
) -> tuple[tuple[ContextGraphEdge, ...], bool]:
    edges: list[ContextGraphEdge] = []
    for candidate in candidate_nodes:
        for required in required_nodes:
            if len(edges) >= MAX_EDGES:
                return tuple(sorted(edges, key=lambda edge: edge.edge_id)), True
            edge_type = _edge_type_for(candidate, required)
            payload: JsonValue = {
                "edge_type": edge_type,
                "source": candidate.node_id,
                "target": required.node_id,
            }
            edges.append(
                ContextGraphEdge(
                    edge_id=f"ctx-edge:{fingerprint_payload(payload)[7:31]}",
                    source=candidate.node_id,
                    target=required.node_id,
                    edge_type=edge_type,
                    metadata={"reason": "explicit_context_dependency"},
                )
            )
    return tuple(sorted(edges, key=lambda edge: edge.edge_id)), False


def _edge_type_for(candidate: ContextGraphNode, required: ContextGraphNode) -> str:
    if candidate.node_type == NODE_TEST:
        return EDGE_VALIDATES
    if required.node_type == NODE_AGENT_RULE:
        return EDGE_CONSTRAINS
    if required.node_type in {NODE_CONTRACT, NODE_ROADMAP}:
        return EDGE_DOCUMENTS
    if required.node_type == NODE_REVIEW_ARTIFACT:
        return EDGE_REVIEWS
    return EDGE_REQUIRES


def _classify_node_type(path: str) -> str:
    if path.endswith("AGENTS.md") or path == "RUNBOOK_AGENT.md":
        return NODE_AGENT_RULE
    if path.startswith("tests/"):
        return NODE_TEST
    if path.startswith("docs/review/"):
        return NODE_REVIEW_ARTIFACT
    if path.startswith("docs/roadmap/"):
        return NODE_ROADMAP
    if path.startswith("docs/orchestration/contracts/") or path.startswith("docs/orchestration/"):
        return NODE_CONTRACT
    return NODE_CHANGED_FILE


def _context_ref_mapping(
    *,
    path: str,
    node: ContextGraphNode,
    status: str,
    reason_code: str,
) -> Mapping[str, JsonValue]:
    return _freeze_mapping(
        {
            "node_id": node.node_id,
            "path": path,
            "path_fingerprint": node.path_fingerprint,
            "reason_code": _validate_token("reason_code", reason_code),
            "status": _validate_token("status", status),
            "token_estimate": node.token_estimate,
        }
    )


def _context_ref_mapping_for_path(
    *,
    path: str,
    node: ContextGraphNode | None,
    repo_root: Path,
    status: str,
    reason_code: str,
) -> Mapping[str, JsonValue]:
    if node is not None:
        return _context_ref_mapping(
            path=path,
            node=node,
            status=status,
            reason_code=reason_code,
        )
    normalized_path = _validate_repo_relative_path(path)
    return _freeze_mapping(
        {
            "node_id": None,
            "path": normalized_path,
            "path_fingerprint": fingerprint_payload({"path": normalized_path}),
            "reason_code": _validate_token("reason_code", reason_code),
            "status": _validate_token("status", status),
            "token_estimate": _estimate_tokens(
                _safe_context_char_count(normalized_path, repo_root=repo_root)
            ),
        }
    )


def _safe_context_char_count(path: str, *, repo_root: Path) -> int:
    normalized_path = _validate_repo_relative_path(path)
    target = repo_root / normalized_path
    try:
        resolved = target.resolve()
        resolved.relative_to(repo_root.resolve())
    except (OSError, ValueError) as exc:
        raise ValueError("path must stay inside repo") from exc
    if not target.is_file():
        return len(normalized_path)
    try:
        return target.stat().st_size
    except OSError:
        return len(normalized_path)


def _reference_char_count(ref: Mapping[str, JsonValue]) -> int:
    return sum(len(str(value)) for value in ref.values())


def _estimate_tokens(char_count: int) -> int:
    normalized = _validate_non_negative_int("char_count", char_count)
    if normalized == 0:
        return 0
    return max(1, math.ceil(normalized / 4))


def _normalize_path_sequence(name: str, values: Sequence[str]) -> tuple[str, ...]:
    normalized, _duplicates = _normalize_path_sequence_with_duplicates(name, values)
    return normalized


def _normalize_path_sequence_with_duplicates(
    name: str,
    values: Sequence[str],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if not isinstance(values, Sequence) or isinstance(values, str):
        raise ValueError(f"{name} must be a sequence")
    seen: set[str] = set()
    deduped: list[str] = []
    duplicates: list[str] = []
    for raw in values:
        normalized = _validate_repo_relative_path(raw)
        if normalized in seen:
            duplicates.append(normalized)
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return tuple(sorted(deduped)), tuple(sorted(duplicates))


def _validate_repo_relative_path(raw_path: str | Path) -> str:
    if isinstance(raw_path, Path):
        raw = raw_path.as_posix()
    elif isinstance(raw_path, str):
        raw = raw_path.strip()
    else:
        raise ValueError("path must be a string")
    if not raw:
        raise ValueError("path must be non-empty")
    if _PATH_RE.search(raw) or "\\" in raw:
        raise ValueError("path contains unsafe metadata")
    normalized: str = normalize_repo_path(raw)
    candidate = Path(normalized)
    if candidate.is_absolute() or normalized.startswith("../") or "/../" in normalized:
        raise ValueError("path must stay inside repo")
    if normalized in {".", ".."} or ".." in candidate.parts:
        raise ValueError("path must stay inside repo")
    if normalized.startswith(".env") or "/.env" in normalized:
        raise ValueError("path contains unsafe metadata")
    return normalized


def _freeze_metadata(value: Mapping[str, JsonValue]) -> Mapping[str, JsonValue]:
    copied = _json_safe_copy(value)
    if not isinstance(copied, dict):
        raise ValueError("metadata must be a mapping")
    _validate_metadata_is_safe(copied)
    _validate_metadata_budget(copied)
    frozen = _deep_freeze_json(copied)
    if not isinstance(frozen, Mapping):
        raise ValueError("metadata must be a mapping")
    return frozen


def _freeze_mapping(value: Mapping[str, JsonValue]) -> Mapping[str, JsonValue]:
    return MappingProxyType(dict(sorted(value.items())))


def _freeze_mapping_tuple(
    name: str,
    values: Sequence[Mapping[str, JsonValue]],
) -> tuple[Mapping[str, JsonValue], ...]:
    if not isinstance(values, Sequence):
        raise ValueError(f"{name} must be a sequence")
    frozen: list[Mapping[str, JsonValue]] = []
    for value in values:
        if not isinstance(value, Mapping):
            raise ValueError(f"{name} must contain mappings")
        frozen.append(_freeze_metadata(value))
    return tuple(frozen)


def _deep_freeze_json(value: JsonValue) -> JsonValue:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _deep_freeze_json(item) for key, item in sorted(value.items())}
        )
    if isinstance(value, list | tuple):
        return tuple(_deep_freeze_json(item) for item in value)
    return value


def _json_safe_copy(value: JsonValue | Mapping[str, JsonValue]) -> JsonValue:
    if isinstance(value, Mapping):
        return {str(key): _json_safe_copy(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [_json_safe_copy(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe_copy(item) for item in value]
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, int):
        return value
    raise ValueError(f"metadata contains unsupported value: {type(value).__name__}")


def _validate_metadata_is_safe(value: JsonValue, *, path: str = "metadata", depth: int = 0) -> None:
    if depth > MAX_METADATA_DEPTH:
        raise ValueError("metadata exceeds maximum depth")
    if isinstance(value, dict):
        for key, item in value.items():
            _validate_safe_metadata_string(f"{path}.key", key)
            _validate_metadata_is_safe(item, path=f"{path}.{key}", depth=depth + 1)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _validate_metadata_is_safe(item, path=f"{path}[{index}]", depth=depth + 1)
    elif isinstance(value, str):
        _validate_safe_metadata_string(path, value)


def _validate_metadata_budget(value: Mapping[str, JsonValue]) -> None:
    serialized = _canonical_json_text(value)
    if len(serialized) > MAX_METADATA_BYTES:
        raise ValueError("metadata exceeds maximum size")


def _validate_safe_metadata_string(name: str, value: str) -> None:
    if len(value) > MAX_STRING_LENGTH:
        raise ValueError(f"{name} exceeds maximum length")
    if _FINGERPRINT_RE.match(value) or _NODE_ID_RE.match(value):
        return
    if _UNSAFE_METADATA_RE.search(value) or _PATH_RE.search(value):
        raise ValueError(f"{name} contains unsafe metadata")


def _validate_token(name: str, value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must be non-empty")
    if len(normalized) > MAX_STRING_LENGTH:
        raise ValueError(f"{name} exceeds maximum length")
    if any(char.isspace() for char in normalized):
        raise ValueError(f"{name} must not contain whitespace")
    if not _TOKEN_RE.match(normalized):
        raise ValueError(f"{name} contains unsupported characters")
    if _UNSAFE_METADATA_RE.search(normalized) or _PATH_RE.search(normalized):
        raise ValueError(f"{name} contains unsafe metadata")
    return normalized


def _validate_role_token(name: str, value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must be non-empty")
    if len(normalized) > MAX_STRING_LENGTH:
        raise ValueError(f"{name} exceeds maximum length")
    if any(char.isspace() for char in normalized):
        raise ValueError(f"{name} must not contain whitespace")
    if not _TOKEN_RE.match(normalized):
        raise ValueError(f"{name} contains unsupported characters")
    if _PATH_RE.search(normalized):
        raise ValueError(f"{name} contains unsafe metadata")
    return normalized


def _normalize_unique_tokens(name: str, values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({_validate_token(name, value) for value in values}))


def _normalize_unique_role_tokens(name: str, values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({_validate_role_token(name, value) for value in values}))


def _normalize_required_unique_tokens(name: str, values: Iterable[str]) -> tuple[str, ...]:
    normalized = _normalize_unique_tokens(name, values)
    if not normalized:
        raise ValueError(f"{name} must be non-empty")
    return normalized


def _validate_derived_id(name: str, value: str) -> str:
    normalized = value.strip()
    if not _NODE_ID_RE.match(normalized):
        raise ValueError(f"{name} must be deterministic context id")
    return normalized


def _validate_fingerprint(name: str, value: str) -> str:
    normalized = value.strip()
    if not _FINGERPRINT_RE.match(normalized):
        raise ValueError(f"{name} must be sha256 fingerprint")
    return normalized


def _validate_non_negative_int(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


def _require_unique(name: str, values: Sequence[str]) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{name} must be unique")


def _canonical_json_text(value: JsonValue | Mapping[str, JsonValue]) -> str:
    return json.dumps(
        _json_safe_copy(value),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
