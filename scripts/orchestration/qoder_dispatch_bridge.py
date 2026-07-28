#!/usr/bin/env python3
"""Compatibility facade for the PulsePlate role dispatch manifest generator.

Reads a governance packet's role order (or explicit CLI role slugs), loads
agent definitions from ``.cursor/agents/<slug>.md``, resolves context maps
and routing metadata, and outputs a JSON dispatch manifest suitable for
Codex, Kimi, Qoder-compatible, or other native subagent transports.

This file keeps the historical ``qoder_dispatch_bridge.py`` entrypoint working.
The canonical runtime-agnostic CLI is ``role_dispatch_bridge.py``.

Usage examples::

    # From a governance packet
    python3 scripts/orchestration/qoder_dispatch_bridge.py \\
        --packet docs/orchestration/packets/my_task.md

    # Explicit roles
    python3 scripts/orchestration/qoder_dispatch_bridge.py \\
        --roles agent-coordinator architecture-specialist philosophy-agent \\
        --mode analysis --pretty
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import re
import sys
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path
from typing import Any, cast, Dict, Iterable, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.orchestration.requested_agents import (
    IMPLEMENTATION_OWNER_SLUGS,
    MANDATORY_POST_OPEN_ORDER,
    normalize_implementation_owner_slugs,
)
from scripts.orchestration.bootstrap_sync_policy import (
    INVARIANT_CHANGE_CLASSES,
    classify_invariant_review,
)
from scripts.orchestration.creative_pilot_workspace_contract import (
    CreativePilotContractError,
    load_json_strict as load_creative_pilot_json_strict,
    validate_task_pilot_context,
)

PR_PHASE_NONE = "none"
PR_PHASE_PRE_OPEN = "pre_open"
PR_PHASE_POST_OPEN_REVIEW = "post_open_review"
PR_PHASE_MERGE_READY = "merge_ready"
PR_PHASES = (
    PR_PHASE_NONE,
    PR_PHASE_PRE_OPEN,
    PR_PHASE_POST_OPEN_REVIEW,
    PR_PHASE_MERGE_READY,
)
INVARIANT_REVIEW_SCHEMA_VERSION = "invariant_review.v1"
INVARIANT_REVIEW_STATES = frozenset({"not_required", "required_pending"})
CURRENT_TASK_PACKET_SCHEMA_VERSION = "3.1"
MANIFEST_SCHEMA_VERSION = "2.0"
MANIFEST_CONTRACT_VERSION = "pulseplate.role-dispatch-manifest/v2"

# ---------------------------------------------------------------------------
# Optional imports with graceful fallback
# ---------------------------------------------------------------------------

_routing_graph: Optional[Dict[str, Any]] = None
_routing_loader_available = False

try:
    from scripts.orchestration.routing_graph_loader import load_routing_graph

    _routing_loader_available = True
except Exception:  # pragma: no cover – optional dependency
    _routing_loader_available = False


def _ensure_routing_graph() -> Dict[str, Any]:
    """Lazy-load the routing graph, caching the result."""
    global _routing_graph
    if _routing_graph is not None:
        return _routing_graph

    if _routing_loader_available:
        try:
            _routing_graph = {
                domain: {
                    "cluster": route.cluster,
                    "primary": route.primary,
                    "secondary": route.secondary,
                    "reviewer": route.reviewer,
                }
                for domain, route in load_routing_graph().items()
            }
            return _routing_graph
        except Exception:
            _routing_graph = None  # fall through to markdown fallback

    # Fallback: parse the markdown table directly
    _routing_graph = _parse_routing_graph_fallback()
    return _routing_graph


def _primary_slugs_from_routing(routing: Dict[str, Any]) -> set[str]:
    """Collect agent slugs that appear as domain primary or secondary."""
    slugs: set[str] = set()
    for route_info in routing.values():
        for key in ("primary", "secondary"):
            agent = route_info.get(key)
            if not agent:
                continue
            slug = str(agent).strip()
            if slug:
                slugs.add(slug)
    return slugs


def _reviewer_slugs_from_routing(routing: Dict[str, Any]) -> set[str]:
    """Collect agent slugs that appear in the ``reviewer`` column."""
    slugs: set[str] = set()
    for route_info in routing.values():
        agent = route_info.get("reviewer")
        if not agent:
            continue
        slug = str(agent).strip()
        if slug:
            slugs.add(slug)
    return slugs


def _dispatch_is_reviewer_slot(
    slug: str,
    order_idx: int,
    total_roles: int,
    *,
    primary_slugs: set[str],
    reviewer_slugs: set[str],
) -> bool:
    """Infer whether this position should use Qoder ``CodeReview`` typing.

    - Any graph **reviewer** that never appears as primary/secondary is always
      a reviewer slot (e.g. ``architecture-specialist``).
    - Agents that are both primary-capable and reviewers are treated as
      reviewers only when they are the **last** role in a multi-role dispatch
      (typical merge / security review tail), not when solo lead.
    """
    # Explicit routing-graph reviewer (not primary-capable) -> always reviewer
    if slug in reviewer_slugs and slug not in primary_slugs:
        return True

    # Name-based detection: slugs containing auditor/reviewer/review keywords
    _REVIEWER_KEYWORDS = ("auditor", "reviewer", "review")
    is_reviewer_by_name = any(kw in slug for kw in _REVIEWER_KEYWORDS)

    # Graph-aware or name-based reviewer in tail position
    if slug in reviewer_slugs or is_reviewer_by_name:
        return total_roles >= 2 and order_idx == total_roles and order_idx > 1

    return False


def _depends_on_previous(
    slug: str,
    agent_def: Dict[str, Any],
    previous_slug: Optional[str],
    chained_successors: Optional[set[str]] = None,
) -> bool:
    """Return whether this dispatch item must wait for the previous item."""
    if previous_slug is None:
        return False
    if chained_successors and slug in chained_successors:
        return True
    if agent_def.get("depends_on_previous"):
        return True
    # The mandatory post-open review pass is sequential:
    # qa-engineer-agent -> bug-hunter -> security-auditor.
    if slug == "bug-hunter":
        return previous_slug in {"qa-engineer-agent", "bug-hunter"}
    if slug == "security-auditor":
        return previous_slug in {"bug-hunter", "security-auditor"}
    return False


def _parse_routing_graph_fallback() -> Dict[str, Any]:
    """Standalone parser for AGENT_ROUTING_GRAPH.md § 4 table."""
    graph_path = REPO_ROOT / "docs" / "orchestration" / "AGENT_ROUTING_GRAPH.md"
    if not graph_path.is_file():
        return {}

    lines = graph_path.read_text(encoding="utf-8").splitlines()
    routes: Dict[str, Any] = {}
    in_section = False
    header_found = False

    for line in lines:
        stripped = line.strip()
        if "4. Domains" in stripped and stripped.startswith("##"):
            in_section = True
            continue
        if in_section and stripped.startswith("## "):
            break
        if not in_section:
            continue
        if not stripped.startswith("|"):
            continue
        # Skip delimiter rows
        content = stripped.replace("|", "").strip()
        if content and set(content) <= {"-", ":", " "}:
            header_found = True
            continue
        if not header_found:
            # This is the header row – skip it
            header_found = False
            continue
        cols = [c.strip() for c in stripped.split("|") if c.strip()]
        if len(cols) < 5:
            continue
        domain, cluster, primary, secondary, reviewer = (
            cols[0].lower(),
            cols[1],
            cols[2],
            cols[3],
            cols[4],
        )
        if domain.startswith("-"):
            continue
        routes[domain] = {
            "cluster": cluster,
            "primary": primary,
            "secondary": secondary or None,
            "reviewer": reviewer,
        }

    return routes


# ---------------------------------------------------------------------------
# YAML frontmatter parser (no hard dependency on PyYAML)
# ---------------------------------------------------------------------------


def _parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter from agent markdown.

    Returns (metadata_dict, markdown_body).
    Falls back to manual key:value parsing if ``yaml`` is unavailable.
    """
    if not text.startswith("---"):
        return {}, text

    end_idx = text.find("---", 3)
    if end_idx == -1:
        return {}, text

    raw_fm = text[3:end_idx].strip()
    body = text[end_idx + 3 :].strip()

    # Try PyYAML first without creating a hard typed dependency.
    try:
        yaml_module = import_module("yaml")
        meta = yaml_module.safe_load(raw_fm)
        if isinstance(meta, dict):
            return meta, body
    except Exception:
        meta = None  # yaml unavailable or parse failed; use manual fallback

    # Manual fallback
    meta = {}  # noqa: F841 – reassignment for fallback path
    for line in raw_fm.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value.lower() == "true":
            meta[key] = True
        elif value.lower() == "false":
            meta[key] = False
        else:
            meta[key] = value

    return meta, body


# ---------------------------------------------------------------------------
# Agent definition loader
# ---------------------------------------------------------------------------


def _load_agent_definition(slug: str) -> Optional[Dict[str, Any]]:
    """Load and parse a single agent definition from ``.cursor/agents/<slug>.md``."""
    agent_path = REPO_ROOT / ".cursor" / "agents" / f"{slug}.md"
    if not agent_path.is_file():
        return None

    text = agent_path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)

    return {
        "slug": slug,
        "name": meta.get("name", slug),
        "model": meta.get("model", ""),
        "description": meta.get("description", ""),
        "readonly": bool(meta.get("readonly", False)),
        "readonly_explicit": "readonly" in meta,
        "depends_on_previous": bool(meta.get("depends_on_previous", False)),
        "body": body,
        "definition_path": str(agent_path.relative_to(REPO_ROOT)),
    }


# ---------------------------------------------------------------------------
# Context-map parser
# ---------------------------------------------------------------------------

_CONTEXT_AGENT_HEADER_RE = re.compile(
    r"^###\s+.*\(`([a-z][a-z0-9-]+)`\)",
    re.IGNORECASE,
)


def _parse_context_map() -> Dict[str, List[str]]:
    """Parse ``docs/orchestration/AGENT_CONTEXT_MAP.md`` for per-agent context paths."""
    context_map_path = REPO_ROOT / "docs" / "orchestration" / "AGENT_CONTEXT_MAP.md"
    if not context_map_path.is_file():
        return {}

    lines = context_map_path.read_text(encoding="utf-8").splitlines()
    result: Dict[str, List[str]] = {}
    current_slug: Optional[str] = None

    for line in lines:
        m = _CONTEXT_AGENT_HEADER_RE.match(line.strip())
        if m:
            current_slug = m.group(1)
            result.setdefault(current_slug, [])
            continue
        if current_slug is None:
            continue
        if line.strip().startswith("##") and not line.strip().startswith("###"):
            current_slug = None
            continue
        # Capture backtick-quoted paths
        for path_match in re.finditer(r"`([^`]+(?:\.\w+|/\w+)[^`]*)`", line):
            candidate = path_match.group(1)
            # Keep path-shaped backtick tokens (repo paths and markdown/python refs).
            if "/" in candidate or candidate.endswith(".md") or candidate.endswith(".py"):
                # Strip line-range suffixes like :12-24
                cleaned = re.sub(r":\d+(-\d+)?$", "", candidate)
                if cleaned not in result[current_slug]:
                    result[current_slug].append(cleaned)

    return result


# ---------------------------------------------------------------------------
# Qoder subagent type resolution
# ---------------------------------------------------------------------------


def resolve_qoder_type(
    agent_def: Dict[str, Any],
    mode: str,
    is_reviewer: bool,
    implementation_owners: Optional[Iterable[str]] = None,
) -> str:
    """Map an agent definition + task mode to a Qoder subagent type.

    Type mapping:
    - ``CodeReview`` — reviewers
    - ``Research``   — readonly agents, analysis/docs-only modes
    - ``Verify``     — QA/bug-hunting agents
    - ``Coding``     — implementation agents in runtime mode
    - ``Browser``    — frontend in runtime mode (UI validation)
    """
    # mode=review forces CodeReview for all agents
    if mode == "review":
        return "CodeReview"

    slug = agent_def.get("slug") or agent_def.get("name", "")
    explicit_owners = normalize_implementation_owner_slugs(implementation_owners)

    if slug in ("qa-engineer-agent", "bug-hunter"):
        return "Verify"

    if is_reviewer:
        return "CodeReview"

    if mode == "runtime" and slug in explicit_owners and slug in IMPLEMENTATION_OWNER_SLUGS:
        if slug == "frontend-engineer":
            return "Browser"
        return "Coding"

    if agent_def.get("readonly") or mode in ("analysis", "docs-only"):
        return "Research"

    # Specific mode-dependent check first (frontend runtime → Browser)
    if slug == "frontend-engineer" and mode == "runtime":
        return "Browser"

    # Then generic implementation roles
    if slug in IMPLEMENTATION_OWNER_SLUGS:
        return "Coding"

    return "Research"  # Safe fallback


# ---------------------------------------------------------------------------
# Packet parser – extract role order from governance packet markdown
# ---------------------------------------------------------------------------

_ROLE_SLUG_RE = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")
_BRACKET_GROUP_RE = re.compile(r"\[([^\]]+)\]")
_ROLE_ORDER_FIELD_RE = re.compile(
    r"\b(?:required\s+)?(?:role|agent|dispatch)\s+order\b",
    re.IGNORECASE,
)


def _strip_inline_code_token(value: str) -> str:
    """Normalize Markdown inline-code role tokens."""
    return value.strip().strip("`").strip()


def _known_role_slugs_from_text(text: str, known: set[str]) -> List[str]:
    """Extract known role slugs from text while preserving order."""
    slugs: List[str] = []
    for candidate in _ROLE_SLUG_RE.findall(text):
        if candidate in known and (not slugs or slugs[-1] != candidate):
            slugs.append(candidate)
    return slugs


def _validated_dispatch_role_order(
    payload: Dict[str, Any],
    *,
    spawnable_roles: List[str],
) -> Optional[List[str]]:
    """Validate the fail-closed invariant-review dispatch order when present."""

    invariant_review_present = "invariant_review" in payload
    invariant_review = payload.get("invariant_review")
    invariant_review_state: str | None = None
    if not invariant_review_present:
        if payload.get("schema_version") == CURRENT_TASK_PACKET_SCHEMA_VERSION:
            raise ValueError("task packet schema 3.1 requires invariant_review metadata")
        automation_flags = payload.get("automation_flags")
        if isinstance(automation_flags, dict) and (
            "invariant_class_review_required" in automation_flags
        ):
            raise ValueError("current invariant-class packets require invariant_review metadata")
        candidate_paths = payload.get("candidate_paths")
        raw_pr_phase = payload.get("pr_phase")
        bounded_trigger_required = False
        if raw_pr_phase in {PR_PHASE_NONE, PR_PHASE_PRE_OPEN} and isinstance(candidate_paths, list):
            try:
                bounded_trigger_required = classify_invariant_review(
                    candidate_paths=candidate_paths
                ).required
            except ValueError:
                # True legacy packets predate the strict path contract. Current
                # packets are rejected above by their automation marker.
                bounded_trigger_required = False
        if bounded_trigger_required:
            raise ValueError(
                "opening-phase bounded invariant trigger requires invariant_review metadata"
            )
    if invariant_review_present:
        if not isinstance(invariant_review, dict):
            raise ValueError("invariant_review must be a JSON object when present")
        if invariant_review.get("schema_version") != INVARIANT_REVIEW_SCHEMA_VERSION:
            raise ValueError("invariant_review metadata requires invariant_review.v1")
        raw_state = invariant_review.get("state")
        if not isinstance(raw_state, str) or raw_state not in INVARIANT_REVIEW_STATES:
            raise ValueError("invariant_review state must be not_required or required_pending")
        invariant_review_state = raw_state
        if invariant_review.get("implementation_authority") is not False:
            raise ValueError("invariant review must not grant implementation authority")
        if invariant_review.get("merge_authority") is not False:
            raise ValueError("invariant review must not grant merge authority")
        raw_change_classes = invariant_review.get("change_classes")
        if not isinstance(raw_change_classes, list) or any(
            not isinstance(change_class, str) or change_class not in INVARIANT_CHANGE_CLASSES
            for change_class in raw_change_classes
        ):
            raise ValueError("invariant_review change_classes must use the closed class list")
        canonical_change_classes = [
            change_class
            for change_class in INVARIANT_CHANGE_CLASSES
            if change_class in raw_change_classes
        ]
        if raw_change_classes != canonical_change_classes:
            raise ValueError(
                "invariant_review change_classes must be unique and canonically ordered"
            )
        trigger_evidence = invariant_review.get("trigger_evidence")
        if not isinstance(trigger_evidence, list):
            raise ValueError("invariant_review trigger_evidence must be a JSON list")
        candidate_paths = payload.get("candidate_paths")
        if not isinstance(candidate_paths, list) or any(
            not isinstance(candidate_path, str) for candidate_path in candidate_paths
        ):
            raise ValueError("invariant_review requires candidate_paths as a string list")
        explicit_classes: List[str] = []
        for evidence_row in trigger_evidence:
            if not isinstance(evidence_row, dict):
                raise ValueError("invariant_review trigger_evidence rows must be JSON objects")
            change_class = evidence_row.get("change_class")
            source = evidence_row.get("source")
            if not isinstance(change_class, str) or change_class not in INVARIANT_CHANGE_CLASSES:
                raise ValueError("invariant_review trigger_evidence uses an unknown change_class")
            if source == "explicit":
                if set(evidence_row) != {"change_class", "source"}:
                    raise ValueError(
                        "explicit invariant_review evidence must not contain path or extra fields"
                    )
                explicit_classes.append(change_class)
            elif source == "bounded_path_hint":
                if set(evidence_row) != {"change_class", "source", "path"} or not isinstance(
                    evidence_row.get("path"), str
                ):
                    raise ValueError(
                        "bounded invariant_review evidence requires exactly one string path"
                    )
            else:
                raise ValueError("invariant_review trigger_evidence uses an unknown source")
        canonical_decision = classify_invariant_review(
            candidate_paths=candidate_paths,
            explicit_classes=explicit_classes,
        )
        canonical_evidence = [
            evidence_row.to_mapping() for evidence_row in canonical_decision.trigger_evidence
        ]
        if raw_change_classes != list(canonical_decision.change_classes) or (
            trigger_evidence != canonical_evidence
        ):
            raise ValueError(
                "invariant_review classes and evidence must match the canonical classifier"
            )
        raw_pr_phase = payload.get("pr_phase")
        if not isinstance(raw_pr_phase, str) or raw_pr_phase not in PR_PHASES:
            raise ValueError("invariant_review requires a valid pr_phase")
        opening_phase = raw_pr_phase in {PR_PHASE_NONE, PR_PHASE_PRE_OPEN}
        has_active_trigger = bool(raw_change_classes or trigger_evidence)
        if opening_phase and has_active_trigger and raw_state != "required_pending":
            raise ValueError("opening-phase invariant triggers require required_pending review")
        if (
            opening_phase
            and raw_state == "required_pending"
            and not (raw_change_classes and trigger_evidence)
        ):
            raise ValueError(
                "required_pending invariant review requires classes and trigger evidence"
            )
        if not opening_phase and raw_state != "not_required":
            raise ValueError("post-open invariant review state must be not_required")
        required_roles = invariant_review.get("required_roles")
        if raw_state == "not_required" and required_roles != []:
            raise ValueError("not_required invariant review must not require roles")

    review_requires_order = invariant_review_state == "required_pending"
    role_dispatch_contract = payload.get("role_agent_dispatch_contract")
    if not isinstance(role_dispatch_contract, dict):
        if review_requires_order:
            raise ValueError(
                "required_pending invariant review requires role_agent_dispatch_contract"
            )
        return None
    if "dispatch_role_order" not in role_dispatch_contract:
        if review_requires_order:
            raise ValueError("required_pending invariant review requires dispatch_role_order")
        return None

    raw_order = role_dispatch_contract["dispatch_role_order"]
    if not isinstance(raw_order, list) or not raw_order:
        raise ValueError("dispatch_role_order must be a non-empty JSON list")
    dispatch_order: List[str] = []
    for raw_slug in raw_order:
        if not isinstance(raw_slug, str):
            raise ValueError("dispatch_role_order entries must be strings")
        if raw_slug != raw_slug.strip() or not _ROLE_SLUG_RE.fullmatch(raw_slug):
            raise ValueError(
                f"dispatch_role_order contains a non-canonical role slug: {raw_slug!r}"
            )
        dispatch_order.append(raw_slug)
    if len(dispatch_order) != len(set(dispatch_order)):
        raise ValueError("dispatch_role_order must not contain duplicate roles")
    if dispatch_order[0] != "agent-coordinator":
        raise ValueError("dispatch_role_order must start with agent-coordinator")
    if Counter(dispatch_order) != Counter(spawnable_roles):
        raise ValueError("dispatch_role_order must exactly match spawnable native bridge bindings")

    if not isinstance(invariant_review, dict):
        raise ValueError("dispatch_role_order requires invariant_review metadata")
    if invariant_review.get("schema_version") != INVARIANT_REVIEW_SCHEMA_VERSION:
        raise ValueError("dispatch_role_order requires invariant_review.v1")
    if invariant_review.get("state") != "required_pending":
        raise ValueError("dispatch_role_order requires required_pending invariant review")
    if invariant_review.get("required_roles") != [
        "logic-agent",
        "philosophy-agent",
    ]:
        raise ValueError(
            "required_pending invariant review requires logic-agent then philosophy-agent"
        )
    if dispatch_order[:3] != [
        "agent-coordinator",
        "logic-agent",
        "philosophy-agent",
    ]:
        raise ValueError(
            "dispatch_role_order must start agent-coordinator -> logic-agent " "-> philosophy-agent"
        )
    if payload.get("pr_phase") not in {PR_PHASE_NONE, PR_PHASE_PRE_OPEN}:
        raise ValueError("invariant review dispatch is limited to opening PR phases")
    if payload.get("creative_pilot_context") is not None:
        raise ValueError("invariant review dispatch cannot be combined with creative pilot context")
    return dispatch_order


def _parse_json_packet_roles(payload: Dict[str, Any]) -> List[str]:
    """Extract ordered role slugs from a task_bootstrap JSON packet."""
    bridge = payload.get("native_subagent_bridge")
    if not isinstance(bridge, dict):
        return []

    ordered: List[str] = []

    def binding_is_spawnable(value: Any, *, default_when_unspecified: bool) -> bool:
        if not isinstance(value, dict):
            return False
        dispatch_contract = value.get("dispatch_contract")
        if dispatch_contract is None:
            return default_when_unspecified
        if not isinstance(dispatch_contract, dict):
            return False
        return not (
            dispatch_contract.get("advisory_only")
            or dispatch_contract.get("spawn_with_native_subagent") is False
        )

    def add_slug(value: Any, *, default_when_unspecified: bool = True) -> None:
        if not binding_is_spawnable(value, default_when_unspecified=default_when_unspecified):
            return
        slug = str(value.get("repo_agent_slug", "")).strip()
        if slug:
            ordered.append(slug)

    primary = bridge.get("primary")
    if not isinstance(primary, dict):
        return []
    if not binding_is_spawnable(primary, default_when_unspecified=True):
        return []
    if not str(primary.get("repo_agent_slug", "")).strip():
        return []
    add_slug(primary)
    secondary_items = bridge.get("secondary")
    if isinstance(secondary_items, list):
        for item in secondary_items:
            add_slug(item)
    advisory_items = bridge.get("advisory")
    if isinstance(advisory_items, list):
        for item in advisory_items:
            add_slug(item, default_when_unspecified=False)
    add_slug(bridge.get("reviewer"))
    if not ordered:
        return []
    dispatch_role_order = _validated_dispatch_role_order(
        payload,
        spawnable_roles=ordered,
    )
    if dispatch_role_order is not None:
        return dispatch_role_order
    requested_agents = payload.get("requested_agents")
    if isinstance(requested_agents, list):
        available_counts: Dict[str, int] = {}
        for slug in ordered:
            available_counts[slug] = available_counts.get(slug, 0) + 1

        requested_ordered: List[str] = []
        for value in requested_agents:
            slug = str(value).strip()
            if available_counts.get(slug, 0) > 0:
                requested_ordered.append(slug)
                available_counts[slug] -= 1

        if requested_ordered:
            remaining_counts = dict(available_counts)
            remaining_ordered: List[str] = []
            for slug in ordered:
                if remaining_counts.get(slug, 0) > 0:
                    remaining_ordered.append(slug)
                    remaining_counts[slug] -= 1
            ordered = [*requested_ordered, *remaining_ordered]
    if ordered[0] == "agent-coordinator":
        return ordered
    if "agent-coordinator" in ordered:
        coordinator_index = ordered.index("agent-coordinator")
        return [
            "agent-coordinator",
            *ordered[:coordinator_index],
            *ordered[coordinator_index + 1 :],
        ]
    return ["agent-coordinator", *ordered]


def _json_packet_has_dispatch_role_order(packet_path: Path) -> bool:
    """Return whether a JSON packet declares the canonical dispatch order."""

    payload = _load_json_packet(packet_path)
    if payload is None:
        return False
    role_dispatch_contract = payload.get("role_agent_dispatch_contract")
    return isinstance(role_dispatch_contract, dict) and (
        "dispatch_role_order" in role_dispatch_contract
    )


def _load_json_packet(packet_path: Path) -> Optional[Dict[str, Any]]:
    """Return JSON packet payload when the packet is a JSON object."""
    try:
        payload = json.loads(packet_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _json_packet_has_requested_order(packet_path: Path) -> bool:
    """Return whether a JSON packet carries an explicit requested role order."""

    try:
        resolved_packet_path = packet_path.resolve(strict=True)
        resolved_packet_path.relative_to(REPO_ROOT.resolve())
    except (OSError, RuntimeError, ValueError):
        return False
    payload = _load_json_packet(resolved_packet_path)
    if payload is None:
        return False
    requested_order = _requested_agent_order_from_payload(payload)
    return bool(requested_order)


def _requested_agent_order_from_payload(payload: Dict[str, Any]) -> Optional[List[str]]:
    """Return validated requested-agent slugs, or None for malformed payloads."""

    requested_agents = payload.get("requested_agents")
    if not isinstance(requested_agents, list):
        return None
    requested_order: List[str] = []
    for raw_agent in requested_agents:
        if not isinstance(raw_agent, str):
            return None
        slug = raw_agent.strip()
        if not slug:
            continue
        if not _ROLE_SLUG_RE.fullmatch(slug):
            return None
        requested_order.append(slug)
    return requested_order


def _json_payload_requested_order_preserves_mandatory_tail(payload: Dict[str, Any]) -> bool:
    """Return whether requested order can bypass post-open tail normalization.

    The QA -> bug-hunter -> security-auditor tail is a post-open / merge-ready
    invariant. Pre-open packets preserve the bootstrap/requested custom-role
    order exactly so explicitly requested agents are not silently reordered.
    """

    requested_order = _requested_agent_order_from_payload(payload)
    if requested_order is None:
        return False

    pr_phase = str(payload.get("pr_phase", "")).strip().lower()
    if pr_phase == PR_PHASE_PRE_OPEN:
        return True

    try:
        qa_index = requested_order.index("qa-engineer-agent")
        bug_index = requested_order.index("bug-hunter")
        security_index = requested_order.index("security-auditor")
    except ValueError:
        return False
    return bug_index == qa_index + 1 and security_index == bug_index + 1


def _json_packet_requested_order_preserves_mandatory_tail(packet_path: Path) -> bool:
    """Return whether a JSON packet can safely override mandatory tail normalization."""

    try:
        resolved_packet_path = packet_path.resolve(strict=True)
        resolved_packet_path.relative_to(REPO_ROOT.resolve())
    except (OSError, RuntimeError, ValueError):
        return False
    payload = _load_json_packet(resolved_packet_path)
    if payload is None:
        return False
    return _json_payload_requested_order_preserves_mandatory_tail(payload)


def _json_packet_runtime_implementation_owners(packet_path: Path) -> set[str]:
    """Return implementation owners explicitly granted by a JSON task packet."""

    try:
        resolved_packet_path = packet_path.resolve(strict=True)
        resolved_packet_path.relative_to(REPO_ROOT.resolve())
    except (OSError, RuntimeError, ValueError):
        return set()
    payload = _load_json_packet(resolved_packet_path)
    if payload is None:
        return set()

    bridge = payload.get("native_subagent_bridge")
    if not isinstance(bridge, dict):
        return set()
    secondary_bindings = bridge.get("secondary", [])
    if not isinstance(secondary_bindings, list):
        secondary_bindings = []
    owner_slugs: list[str] = []
    for binding in [bridge.get("primary"), *secondary_bindings]:
        if not isinstance(binding, dict):
            continue
        slug = str(binding.get("repo_agent_slug", "")).strip().lower()
        if slug not in IMPLEMENTATION_OWNER_SLUGS or slug in owner_slugs:
            continue
        if binding.get("execution_mode") != "read_write":
            continue
        owner_slugs.append(slug)
    bridge_owner_slugs = set(owner_slugs)

    role_dispatch_contract = payload.get("role_agent_dispatch_contract")
    if isinstance(role_dispatch_contract, dict):
        contract_owners = role_dispatch_contract.get("runtime_implementation_owners")
        if isinstance(contract_owners, list):
            normalized_contract_owners: set[str] = normalize_implementation_owner_slugs(
                contract_owners
            )
            return normalized_contract_owners.intersection(bridge_owner_slugs)

    return bridge_owner_slugs


def _parse_packet_roles(packet_path: Path) -> List[str]:
    """Extract ordered role slugs from a governance packet.

    Looks for:
    1. A task_bootstrap JSON packet with ``native_subagent_bridge``.
    2. A ``## Coordinator Role Order`` section with numbered/bulleted slugs.
    3. Fallback: any numbered list containing agent slugs.
    """
    if not packet_path.is_file():
        print(f"FAIL: Packet file not found: {packet_path}", file=sys.stderr)
        sys.exit(1)
    try:
        resolved_packet_path = packet_path.resolve(strict=True)
        resolved_packet_path.relative_to(REPO_ROOT.resolve())
    except (OSError, RuntimeError, ValueError):
        print(
            f"FAIL: Packet file must stay under repo root: {packet_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    json_payload = _load_json_packet(resolved_packet_path)
    if json_payload is not None:
        return _parse_json_packet_roles(json_payload)

    text = resolved_packet_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Strategy 1: dedicated section
    slugs = _extract_roles_from_section(lines, "Coordinator Role Order")
    if slugs:
        return slugs

    # Strategy 2: look for "Role Order" or "Agent Order" sections
    for heading_fragment in ("Role Order", "Agent Order", "Dispatch Order"):
        slugs = _extract_roles_from_section(lines, heading_fragment)
        if slugs:
            return slugs

    # Strategy 3: scan for numbered list items containing agent slugs
    known_agents = _list_known_agent_slugs()
    ordered: List[str] = []
    in_fence = False
    capture_continuation = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            capture_continuation = False
            continue
        if in_fence:
            continue
        if not stripped or stripped.startswith("##"):
            capture_continuation = False
            continue
        is_list_item = bool(re.match(r"^\d+\.\s+", stripped) or stripped.startswith("- "))
        if capture_continuation and not is_list_item:
            for slug in _known_role_slugs_from_text(stripped, known_agents):
                if not ordered or ordered[-1] != slug:
                    ordered.append(slug)
            continue
        capture_continuation = False
        if is_list_item and _ROLE_ORDER_FIELD_RE.search(stripped):
            capture_continuation = True
        if is_list_item:
            for slug in _known_role_slugs_from_text(stripped, known_agents):
                if not ordered or ordered[-1] != slug:
                    ordered.append(slug)

    return ordered


def _extract_roles_from_section(lines: List[str], heading_fragment: str) -> List[str]:
    """Extract role slugs from a markdown section matching the heading fragment."""
    in_section = False
    in_fence = False
    slugs: List[str] = []
    known = _list_known_agent_slugs()

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if stripped.startswith("##") and heading_fragment.lower() in stripped.lower():
            in_section = True
            continue
        if in_section and stripped.startswith("## "):
            break
        if not in_section:
            continue
        for candidate in _known_role_slugs_from_text(stripped, known):
            if not slugs or slugs[-1] != candidate:
                slugs.append(candidate)

    return slugs


def _extract_chain_successors(lines: List[str]) -> set[str]:
    """Extract slugs that are successors in explicit ``a -> b`` chain notation."""
    known = _list_known_agent_slugs()
    successors: set[str] = set()
    in_fence = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or "->" not in stripped:
            continue
        slugs = _known_role_slugs_from_text(stripped, known)
        if len(slugs) >= 2:
            successors.update(slugs[1:])

    return successors


def _list_known_agent_slugs() -> set[str]:
    """Return the set of agent slugs that have definition files."""
    agents_dir = REPO_ROOT / ".cursor" / "agents"
    if not agents_dir.is_dir():
        return set()
    return {p.stem for p in agents_dir.glob("*.md") if p.stem != "AGENTS"}


def _extract_bracket_groups(lines: List[str]) -> List[List[str]]:
    """Extract parallelizable groups from bracket notation ``[slug-a, slug-b]``.

    Returns a list of groups, where each group is a list of slugs that should
    run in parallel.
    """
    known = _list_known_agent_slugs()
    groups: List[List[str]] = []
    in_fence = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for match in _BRACKET_GROUP_RE.finditer(stripped):
            inner = match.group(1)
            slugs = [_strip_inline_code_token(s) for s in inner.split(",")]
            valid_slugs = [s for s in slugs if s in known]
            if len(valid_slugs) >= 2:
                groups.append(valid_slugs)

    return groups


# ---------------------------------------------------------------------------
# Parallelization heuristic
# ---------------------------------------------------------------------------


def _detect_parallel_groups(
    dispatch_items: List[Dict[str, Any]],
    routing: Dict[str, Any],
) -> List[List[str]]:
    """Detect groups of agents that can run in parallel.

    Heuristic: readonly agents with different domains can be parallelized.
    """
    # Build a slug -> domain map
    slug_domain: Dict[str, str] = {}
    for domain, route_info in routing.items():
        for role_key in ("primary", "secondary", "reviewer"):
            agent = route_info.get(role_key)
            if agent:
                slug_domain.setdefault(agent, domain)

    readonly_items = [
        item
        for item in dispatch_items
        if item.get("readonly")
        and not item.get("depends_on_previous")
        and item.get("role_slug") != "agent-coordinator"
        and item.get("qoder_subagent_type") != "Verify"
    ]
    slug_counts: Dict[str, int] = {}
    for item in readonly_items:
        slug = item["role_slug"]
        slug_counts[slug] = slug_counts.get(slug, 0) + 1
    readonly_items = [item for item in readonly_items if slug_counts[item["role_slug"]] == 1]

    if len(readonly_items) < 2:
        return []

    # Group by domain
    domain_groups: Dict[str, List[str]] = {}
    for item in readonly_items:
        domain = slug_domain.get(item["role_slug"], "unknown")
        domain_groups.setdefault(domain, []).append(item["role_slug"])

    # Agents in different domains can be parallelized
    if len(domain_groups) >= 2:
        parallel_group = [slug for slugs in domain_groups.values() for slug in slugs]
        return [parallel_group] if len(parallel_group) >= 2 else []

    return []


def _validated_bracket_groups(
    bracket_groups: List[List[str]],
    dispatch_items: List[Dict[str, Any]],
) -> List[List[str]]:
    """Keep only packet bracket groups that match runnable independent dispatch items."""
    dispatch_by_slug = {item["role_slug"]: item for item in dispatch_items}
    ambiguous_slugs = {
        item["role_slug"]
        for item in dispatch_items
        if sum(1 for candidate in dispatch_items if candidate["role_slug"] == item["role_slug"]) > 1
    }
    validated: List[List[str]] = []

    for group in bracket_groups:
        if len(set(group)) != len(group):
            continue
        unique_group = list(dict.fromkeys(group))
        if len(unique_group) < 2:
            continue
        if any(slug in ambiguous_slugs for slug in unique_group):
            continue
        group_items = [dispatch_by_slug.get(slug) for slug in unique_group]
        if any(item is None for item in group_items):
            continue
        if any(item.get("depends_on_previous") for item in group_items if item is not None):
            continue
        if any(not item.get("readonly") for item in group_items if item is not None):
            continue
        if any(
            item.get("qoder_subagent_type") == "Verify" for item in group_items if item is not None
        ):
            continue
        if any(
            item.get("role_slug") == "agent-coordinator" for item in group_items if item is not None
        ):
            continue
        validated.append(unique_group)

    return validated


# ---------------------------------------------------------------------------
# Skill recommendation (simple heuristic)
# ---------------------------------------------------------------------------

_SKILL_MAP: Dict[str, List[str]] = {
    "agent-coordinator": ["pulseplate-workflow"],
    "architecture-specialist": ["pulseplate-workflow"],
    "backend-engineer": ["pulseplate-workflow"],
    "frontend-engineer": ["pulseplate-workflow", "vercel-react-best-practices"],
    "security-auditor": ["pulseplate-workflow", "pulseplate-pr-review"],
    "qa-engineer-agent": ["pulseplate-workflow", "pulseplate-pr-review"],
    "bug-hunter": ["pulseplate-workflow", "pulseplate-pr-review"],
}


def _recommend_skills(slug: str) -> List[str]:
    """Return recommended skills for an agent slug."""
    return list(_SKILL_MAP.get(slug, ["pulseplate-workflow"]))


# ---------------------------------------------------------------------------
# Manifest builder
# ---------------------------------------------------------------------------


def _enforce_mandatory_post_open_order(role_slugs: List[str]) -> List[str]:
    """Keep the canonical post-open QA -> bug-hunter -> security pass adjacent."""

    if "qa-engineer-agent" not in role_slugs or "bug-hunter" not in role_slugs:
        return role_slugs

    mandatory_tail = ("bug-hunter", "security-auditor")
    ordered = [slug for slug in role_slugs if slug not in mandatory_tail]
    insert_at = ordered.index("qa-engineer-agent") + 1
    ordered[insert_at:insert_at] = [
        *["bug-hunter"] * role_slugs.count("bug-hunter"),
        *["security-auditor"] * role_slugs.count("security-auditor"),
    ]
    return ordered


def _explicit_roles_need_pr_phase(role_slugs: List[str]) -> bool:
    """Return whether explicit roles are ambiguous without a PR phase."""

    if any(slug not in role_slugs for slug in MANDATORY_POST_OPEN_ORDER):
        return False
    return _enforce_mandatory_post_open_order(list(role_slugs)) != role_slugs


def build_dispatch_manifest(
    *,
    role_slugs: List[str],
    mode: str,
    packet_source: Optional[str] = None,
    bracket_groups: Optional[List[List[str]]] = None,
    chained_successors: Optional[set[str]] = None,
    enforce_mandatory_post_open_tail: bool = True,
    implementation_owners: Optional[Iterable[str]] = None,
    creative_pilot_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the full JSON dispatch manifest for the given role order."""
    if creative_pilot_context is not None:
        try:
            creative_pilot_context = validate_task_pilot_context(creative_pilot_context)
        except CreativePilotContractError as exc:
            raise ValueError(f"invalid creative_pilot_context: {exc}") from exc
    context_map = _parse_context_map()
    routing = _ensure_routing_graph()
    primary_slugs = _primary_slugs_from_routing(routing)
    reviewer_slugs = _reviewer_slugs_from_routing(routing)

    dispatch_sequence: List[Dict[str, Any]] = []
    missing_agents: List[str] = []
    loaded_agents: List[Tuple[str, Dict[str, Any]]] = []
    if enforce_mandatory_post_open_tail:
        role_slugs = _enforce_mandatory_post_open_order(role_slugs)

    for slug in role_slugs:
        agent_def = _load_agent_definition(slug)
        if agent_def is None:
            missing_agents.append(slug)
            continue
        loaded_agents.append((slug, agent_def))

    total_roles = len(loaded_agents)
    previous_slug: Optional[str] = None

    explicit_implementation_owners = normalize_implementation_owner_slugs(implementation_owners)

    for order_idx, (slug, agent_def) in enumerate(loaded_agents, start=1):
        is_reviewer = _dispatch_is_reviewer_slot(
            slug,
            order_idx,
            total_roles,
            primary_slugs=primary_slugs,
            reviewer_slugs=reviewer_slugs,
        )
        qoder_type = resolve_qoder_type(
            agent_def,
            mode,
            is_reviewer,
            implementation_owners=explicit_implementation_owners,
        )
        context_paths = context_map.get(slug, [])
        skills = _recommend_skills(slug)

        implementation_owner_override = (
            mode == "runtime"
            and slug in explicit_implementation_owners
            and slug in IMPLEMENTATION_OWNER_SLUGS
            and qoder_type in ("Browser", "Coding", "Verify")
        )
        # Derive readonly: use agent frontmatter if explicitly set, else infer from Qoder type
        if implementation_owner_override:
            readonly = False
        elif agent_def.get("readonly_explicit"):
            readonly = agent_def["readonly"]
        else:
            readonly = qoder_type in ("Research", "CodeReview", "Verify")

        # System prompt excerpt: first 500 chars of body
        body_excerpt = agent_def["body"][:500] if agent_def["body"] else ""

        item: Dict[str, Any] = {
            "order": order_idx,
            "role_slug": slug,
            "qoder_subagent_type": qoder_type,
            "agent_definition_path": agent_def["definition_path"],
            "required_context_paths": context_paths,
            "recommended_skills": skills,
            "mode": mode,
            "system_prompt_excerpt": body_excerpt,
            "description": agent_def["description"],
            "readonly": readonly,
            "implementation_owner_override": implementation_owner_override,
            "constraints": [],
            "depends_on_previous": _depends_on_previous(
                slug, agent_def, previous_slug, chained_successors
            ),
        }
        if creative_pilot_context is not None:
            matching = [row for row in creative_pilot_context["assignments"] if row["role"] == slug]
            if len(matching) != 1:
                raise ValueError(
                    f"creative pilot dispatch requires exactly one assignment for {slug}"
                )
            item["creative_pilot_assignment"] = matching[0]
            item["readonly"] = True
            item["implementation_owner_override"] = False
        dispatch_sequence.append(item)
        previous_slug = slug

    if missing_agents:
        print(
            f"WARNING: Agent definitions not found for: {', '.join(missing_agents)}",
            file=sys.stderr,
        )

    manifest: Dict[str, Any] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "manifest_contract_version": MANIFEST_CONTRACT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "packet_source": packet_source or "",
        "mode": mode,
        "dispatch_sequence": dispatch_sequence,
        "parallelizable_groups": [],
        "parallel_execution_allowed": False,
        "parallel_execution_reason": (
            "Role-agent dispatch is a hard gate and must follow dispatch_sequence order."
        ),
        "post_open_role_gates": list(MANDATORY_POST_OPEN_ORDER),
        "mandatory_post_open": list(MANDATORY_POST_OPEN_ORDER),
        "mandatory_post_open_gates": list(MANDATORY_POST_OPEN_ORDER),
        "mandatory_post_open_role_agents": list(MANDATORY_POST_OPEN_ORDER),
        "compatibility_aliases": {
            "mandatory_post_open": {
                "canonical_fields": ["post_open_role_gates"],
                "fail_closed": True,
            },
            "mandatory_post_open_role_agents": {
                "canonical_fields": ["post_open_role_gates"],
                "fail_closed": True,
            },
            "mandatory_post_open_gates": {
                "canonical_fields": ["post_open_role_gates"],
                "fail_closed": True,
            },
        },
        "missing_agents": missing_agents,
    }
    if creative_pilot_context is not None:
        manifest["creative_pilot_context"] = {
            key: creative_pilot_context[key]
            for key in (
                "schema_version",
                "workspace_id",
                "workspace_intent_fingerprint",
                "workspace_revision_fingerprint",
                "phase",
                "dispatch_input_fingerprint",
                "authority",
            )
        }

    return manifest


def _load_creative_pilot_context(packet_path: Path) -> Optional[Dict[str, Any]]:
    if packet_path.suffix != ".json":
        return None
    try:
        payload = load_creative_pilot_json_strict(packet_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, CreativePilotContractError) as exc:
        raise ValueError(f"invalid strict JSON task packet: {exc}") from exc
    context = payload.get("creative_pilot_context") if isinstance(payload, dict) else None
    if context is None:
        return None
    if not isinstance(context, dict):
        raise ValueError("creative_pilot_context must be an object")
    if payload.get("pr_phase") in {PR_PHASE_POST_OPEN_REVIEW, PR_PHASE_MERGE_READY}:
        raise ValueError(
            "creative pilot dispatch cannot be combined with post-open or merge-ready PR phases"
        )
    try:
        return cast(Dict[str, Any], validate_task_pilot_context(context))
    except CreativePilotContractError as exc:
        raise ValueError(f"invalid creative_pilot_context: {exc}") from exc


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="role_dispatch_bridge",
        description=(
            "Generate a JSON role dispatch manifest from a governance packet "
            "or explicit role list."
        ),
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--packet",
        type=str,
        default=None,
        help="Path to governance packet markdown file.",
    )
    source.add_argument(
        "--roles",
        nargs="+",
        metavar="SLUG",
        default=None,
        help="Explicit ordered list of role slugs.",
    )

    parser.add_argument(
        "--mode",
        choices=("analysis", "docs-only", "runtime", "review"),
        default="analysis",
        help="Task mode (default: analysis).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (default: stdout).",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        default=False,
        help="Pretty-print JSON output.",
    )
    parser.add_argument(
        "--pr-phase",
        choices=PR_PHASES,
        default=PR_PHASE_NONE,
        help=(
            "Optional PR lifecycle phase. Explicit --roles post-open review dispatch "
            "enforces the mandatory QA -> bug-hunter -> security-auditor order."
        ),
    )
    parser.add_argument(
        "--implementation-owner",
        action="append",
        choices=sorted(IMPLEMENTATION_OWNER_SLUGS),
        default=[],
        help=(
            "Explicit runtime write-capable implementation owner. Repeat for multiple "
            "owners. Required to route a frontmatter-readonly implementation role to "
            "Browser/Coding in runtime mode."
        ),
    )

    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint."""
    args = _parse_args(argv)

    # Resolve role slugs
    packet_source: Optional[str] = None
    packet_bracket_groups: Optional[List[List[str]]] = None
    packet_chained_successors: Optional[set[str]] = None
    enforce_mandatory_post_open_tail = True
    if args.packet:
        packet_path = Path(args.packet)
        if not packet_path.is_absolute():
            packet_path = (REPO_ROOT / packet_path).resolve()
        enforce_mandatory_post_open_tail = not (
            _json_packet_requested_order_preserves_mandatory_tail(packet_path)
        )
        try:
            role_slugs = _parse_packet_roles(packet_path)
        except ValueError as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            return 1
        # Extract bracket-notation parallelizable groups from packet
        packet_lines = packet_path.read_text(encoding="utf-8").splitlines()
        packet_bracket_groups = _extract_bracket_groups(packet_lines) or None
        packet_chained_successors = _extract_chain_successors(packet_lines) or None
        if _json_packet_has_dispatch_role_order(packet_path):
            packet_chained_successors = set(role_slugs[1:])
            enforce_mandatory_post_open_tail = False
        try:
            packet_source = str(packet_path.relative_to(REPO_ROOT))
        except ValueError:
            packet_source = str(packet_path)
        if not role_slugs:
            print(
                f"FAIL: No agent role slugs found in packet: {packet_path}",
                file=sys.stderr,
            )
            return 1
        try:
            creative_pilot_context = _load_creative_pilot_context(packet_path)
        except ValueError as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            return 1
        if creative_pilot_context is not None:
            role_slugs = [row["role"] for row in creative_pilot_context["assignments"]]
            enforce_mandatory_post_open_tail = False
    else:
        role_slugs = list(args.roles)
        creative_pilot_context = None
        if args.pr_phase in {PR_PHASE_POST_OPEN_REVIEW, PR_PHASE_MERGE_READY}:
            missing_post_open_roles = [
                slug for slug in MANDATORY_POST_OPEN_ORDER if slug not in role_slugs
            ]
            if missing_post_open_roles:
                print(
                    "FAIL: --pr-phase post_open_review/merge_ready requires role slugs: "
                    + ", ".join(MANDATORY_POST_OPEN_ORDER)
                    + ". Missing: "
                    + ", ".join(missing_post_open_roles),
                    file=sys.stderr,
                )
                return 1
            enforce_mandatory_post_open_tail = True
        elif args.pr_phase == PR_PHASE_NONE and _explicit_roles_need_pr_phase(role_slugs):
            print(
                "FAIL: explicit --roles contains the full mandatory post-open role set "
                "out of order. Pass --pr-phase pre_open to preserve coordinator "
                "pre-open order, or --pr-phase post_open_review/merge_ready to "
                "enforce qa-engineer-agent -> bug-hunter -> security-auditor.",
                file=sys.stderr,
            )
            return 1
        else:
            enforce_mandatory_post_open_tail = False

    if not role_slugs:
        print("FAIL: No role slugs provided.", file=sys.stderr)
        return 1
    implementation_owner_slugs = normalize_implementation_owner_slugs(args.implementation_owner)
    if implementation_owner_slugs and not args.packet:
        print(
            "FAIL: --implementation-owner requires --packet so runtime ownership "
            "stays tied to coordinator-governed dispatch evidence.",
            file=sys.stderr,
        )
        return 1
    if implementation_owner_slugs and args.packet:
        allowed_owner_slugs = _json_packet_runtime_implementation_owners(packet_path)
        ungranted_owner_slugs = sorted(implementation_owner_slugs - allowed_owner_slugs)
        if ungranted_owner_slugs:
            print(
                "FAIL: --implementation-owner not granted by packet for: "
                + ", ".join(ungranted_owner_slugs)
                + ". Use the packet role_agent_dispatch_contract.dispatch_manifest_command.",
                file=sys.stderr,
            )
            return 1

    # Build manifest
    manifest = build_dispatch_manifest(
        role_slugs=role_slugs,
        mode=args.mode,
        packet_source=packet_source,
        bracket_groups=packet_bracket_groups,
        chained_successors=packet_chained_successors,
        enforce_mandatory_post_open_tail=enforce_mandatory_post_open_tail,
        implementation_owners=implementation_owner_slugs,
        creative_pilot_context=creative_pilot_context,
    )
    if manifest.get("missing_agents"):
        print(
            "FAIL: Agent definitions not found for: "
            + ", ".join(str(slug) for slug in manifest["missing_agents"]),
            file=sys.stderr,
        )
        return 1

    # Output
    indent = 2 if args.pretty else None
    json_output = json.dumps(manifest, ensure_ascii=False, indent=indent, sort_keys=False)

    if args.output:
        out_path = Path(args.output)
        if not out_path.is_absolute():
            out_path = (REPO_ROOT / out_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json_output + "\n", encoding="utf-8")
        print(f"Manifest written to: {out_path}", file=sys.stderr)
    else:
        print(json_output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
