"""Shared helpers for deterministic design-lane orchestration contracts.

RU: Общие константы и нормализация для packet-driven design lane.
EN: Shared constants and normalization helpers for packet-driven design lanes.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

DESIGN_SOURCE_CODE_NATIVE_BRIEF = "code_native_brief"
DESIGN_SOURCE_FIGMA_DESIGN = "figma_design"
DESIGN_SOURCE_FIGMA_MAKE = "figma_make"

FIGMA_DESIGN_SOURCES: tuple[str, ...] = (
    DESIGN_SOURCE_FIGMA_DESIGN,
    DESIGN_SOURCE_FIGMA_MAKE,
)
READ_ONLY_DESIGN_SOURCES: tuple[str, ...] = (
    "notion",
    "airweave",
    "penpot",
    "stitch_reference",
)
DESIGN_SOURCES: tuple[str, ...] = (
    DESIGN_SOURCE_CODE_NATIVE_BRIEF,
    *FIGMA_DESIGN_SOURCES,
    *READ_ONLY_DESIGN_SOURCES,
)
DESIGN_SOURCES_REQUIRING_CODE_NATIVE_BRIEF: tuple[str, ...] = (
    DESIGN_SOURCE_CODE_NATIVE_BRIEF,
    *FIGMA_DESIGN_SOURCES,
)
FIGMA_LANE_TOOLS: tuple[str, ...] = ("figma_native", "tokens_studio")
DESIGN_TASK_MODES: tuple[str, ...] = ("read_only", "verify", "implement", "sync")
DESIGN_EXECUTION_TASK_MODES: tuple[str, ...] = ("verify", "implement", "sync")
DESIGN_BLOCKERS: tuple[str, ...] = (
    "missing_design_trigger",
    "missing_design_metadata",
    "blocked_by_design_url",
    "blocked_by_node_id_capture",
    "blocked_by_plan",
    "stale",
)
DESIGN_LANE_MODES: tuple[str, ...] = (
    "disabled",
    "read_only",
    *DESIGN_EXECUTION_TASK_MODES,
)
DESIGN_PACKET_CONTRACT_FIELDS = frozenset(
    {
        "design_source",
        "source_url",
        "file_key_or_workspace",
        "node_id_or_frame_id",
        "target_surface",
        "task_mode",
        "figma_lane_tool",
        "blockers",
        "code_native_design_brief_required",
        "code_native_design_brief_path",
        "explicit_creation_mode",
    }
)
DESIGN_PACKET_TEXT_FIELDS: tuple[str, ...] = (
    "design_source",
    "source_url",
    "file_key_or_workspace",
    "node_id_or_frame_id",
    "target_surface",
    "task_mode",
    "figma_lane_tool",
    "code_native_design_brief_path",
)


@dataclass(frozen=True)
class DesignLanePacketProjection:
    """Frozen packet-local readiness projection with no execution authority."""

    mode: str
    blockers: tuple[str, ...]
    enabled: bool
    execution_ready: bool


def normalize_optional_text(value: str | None) -> str:
    """Return stripped text and reject internal C0/DEL controls."""

    if value is None:
        return ""
    normalized = value.strip()
    if any(ord(character) < 32 or ord(character) == 127 for character in normalized):
        raise ValueError("design text contains control characters")
    return normalized


def normalize_design_enum(
    *,
    field_name: str,
    value: str | None,
    allowed_values: tuple[str, ...],
) -> str:
    """Normalize optional design enum values and reject unsupported inputs."""

    normalized = normalize_optional_text(value)
    if not normalized:
        return ""
    if normalized not in allowed_values:
        supported = ", ".join(allowed_values)
        raise ValueError(f"Unsupported {field_name}: {value}. Supported: {supported}")
    return normalized


def dedupe_preserve_order(values: list[str]) -> list[str]:
    """Return a stable de-duplicated list."""

    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return deduped


def canonicalize_design_blockers(
    design_blockers: list[str] | tuple[str, ...],
) -> list[str]:
    """Return blockers in canonical vocabulary order for deterministic hashing."""

    blocker_rank = {blocker: index for index, blocker in enumerate(DESIGN_BLOCKERS)}
    max_rank = len(DESIGN_BLOCKERS)
    return sorted(
        dedupe_preserve_order(list(design_blockers)),
        key=lambda blocker: (blocker_rank.get(blocker, max_rank), blocker),
    )


def normalize_design_blockers(
    design_blockers: list[str] | tuple[str, ...],
) -> list[str]:
    """Normalize explicit design blockers against the canonical blocker set."""

    normalized: list[str] = []
    for blocker in design_blockers:
        normalized_blocker = normalize_design_enum(
            field_name="design_blocker",
            value=blocker,
            allowed_values=DESIGN_BLOCKERS,
        )
        if normalized_blocker:
            normalized.append(normalized_blocker)
    return canonicalize_design_blockers(normalized)


def design_trigger_present(
    *,
    design_source: str,
    source_url: str,
    file_key_or_workspace: str,
    node_id_or_frame_id: str,
    target_surface: str,
    task_mode: str,
    figma_lane_tool: str,
    code_native_design_brief_path: str,
    explicit_creation_mode: bool,
) -> bool:
    """Return True when explicit design-lane metadata is present."""

    return any(
        (
            design_source,
            source_url,
            file_key_or_workspace,
            node_id_or_frame_id,
            target_surface,
            task_mode,
            figma_lane_tool,
            code_native_design_brief_path,
            explicit_creation_mode,
        )
    )


def figma_packet_is_execution_ready(
    *,
    design_source: str,
    source_url: str,
    file_key_or_workspace: str,
    node_id_or_frame_id: str,
    target_surface: str,
    task_mode: str,
    figma_lane_tool: str,
    code_native_design_brief_path: str,
    explicit_creation_mode: bool,
) -> bool:
    """Return True when a Figma packet is complete enough for execution helpers."""

    if design_source not in FIGMA_DESIGN_SOURCES:
        return False
    if task_mode not in DESIGN_EXECUTION_TASK_MODES:
        return False
    if not target_surface or not figma_lane_tool or not code_native_design_brief_path:
        return False
    if explicit_creation_mode and task_mode == "implement":
        return True
    return bool(source_url and file_key_or_workspace and node_id_or_frame_id)


def _require_canonical_packet_text(value: Any) -> str:
    if type(value) is not str:
        raise ValueError("design packet text must be a canonical string")
    normalized = normalize_optional_text(cast(str, value))
    if value != normalized:
        raise ValueError("design packet text must be a canonical string")
    return normalized


def normalize_design_lane_packet_projection(
    *,
    design_lane_mode: Any,
    design_lane_contract: Any,
    design_lane_enabled: Any,
) -> DesignLanePacketProjection:
    """Validate one exact design packet projection without repairing it.

    ``execution_ready`` means only that the packet-local design contract is
    complete enough for its declared execution mode. It does not execute a
    role, authorize asset mutation, or infer human approval.
    """

    if type(design_lane_mode) is not str or design_lane_mode not in DESIGN_LANE_MODES:
        raise ValueError("design_lane_mode is not canonical")
    if type(design_lane_enabled) is not bool:
        raise ValueError("design_lane_enabled must be a boolean")
    if not isinstance(design_lane_contract, Mapping) or set(design_lane_contract) != set(
        DESIGN_PACKET_CONTRACT_FIELDS
    ):
        raise ValueError("design_lane_contract fields are not canonical")

    contract = cast(Mapping[str, Any], design_lane_contract)
    text = {
        field: _require_canonical_packet_text(contract.get(field))
        for field in DESIGN_PACKET_TEXT_FIELDS
    }
    design_source = text["design_source"]
    task_mode = text["task_mode"]
    figma_lane_tool = text["figma_lane_tool"]
    if design_source not in ("", *DESIGN_SOURCES):
        raise ValueError("design_source is not canonical")
    if task_mode not in ("", *DESIGN_TASK_MODES):
        raise ValueError("task_mode is not canonical")
    if figma_lane_tool not in ("", *FIGMA_LANE_TOOLS):
        raise ValueError("figma_lane_tool is not canonical")

    blocker_value = contract.get("blockers")
    if not isinstance(blocker_value, (list, tuple)):
        raise ValueError("design blockers must be a finite sequence")
    blockers = tuple(
        _require_canonical_packet_text(blocker) for blocker in cast(list[Any], blocker_value)
    )
    if any(not blocker or blocker not in DESIGN_BLOCKERS for blocker in blockers) or list(
        blockers
    ) != canonicalize_design_blockers(list(blockers)):
        raise ValueError("design blockers are not canonical")

    brief_required = contract.get("code_native_design_brief_required")
    explicit_creation_mode = contract.get("explicit_creation_mode")
    if type(brief_required) is not bool or type(explicit_creation_mode) is not bool:
        raise ValueError("design packet booleans are not canonical")
    if brief_required is not (design_source in DESIGN_SOURCES_REQUIRING_CODE_NATIVE_BRIEF):
        raise ValueError("code-native brief requirement contradicts design_source")
    if figma_lane_tool and design_source not in FIGMA_DESIGN_SOURCES:
        raise ValueError("figma_lane_tool contradicts design_source")

    trigger_present = design_trigger_present(
        design_source=design_source,
        source_url=text["source_url"],
        file_key_or_workspace=text["file_key_or_workspace"],
        node_id_or_frame_id=text["node_id_or_frame_id"],
        target_surface=text["target_surface"],
        task_mode=task_mode,
        figma_lane_tool=figma_lane_tool,
        code_native_design_brief_path=text["code_native_design_brief_path"],
        explicit_creation_mode=cast(bool, explicit_creation_mode),
    )
    if design_lane_enabled is not trigger_present:
        raise ValueError("design_lane_enabled contradicts the packet trigger")

    if not trigger_present:
        expected_contract = {
            "design_source": "",
            "source_url": "",
            "file_key_or_workspace": "",
            "node_id_or_frame_id": "",
            "target_surface": "",
            "task_mode": "",
            "figma_lane_tool": "",
            "blockers": ["missing_design_trigger"],
            "code_native_design_brief_required": False,
            "code_native_design_brief_path": "",
            "explicit_creation_mode": False,
        }
        comparable_contract = dict(contract)
        comparable_contract["blockers"] = list(blockers)
        if design_lane_mode != "disabled" or comparable_contract != expected_contract:
            raise ValueError("disabled design packet is not canonical")
        return DesignLanePacketProjection(
            mode="disabled",
            blockers=blockers,
            enabled=False,
            execution_ready=False,
        )

    if "missing_design_trigger" in blockers:
        raise ValueError("enabled design packet carries missing_design_trigger")
    required_blockers: set[str] = set()
    if not design_source or not text["target_surface"] or not task_mode:
        required_blockers.add("missing_design_metadata")
    if (
        design_source == DESIGN_SOURCE_CODE_NATIVE_BRIEF
        and not text["code_native_design_brief_path"]
    ):
        required_blockers.add("missing_design_metadata")
    if design_source in FIGMA_DESIGN_SOURCES:
        if not figma_lane_tool or not text["code_native_design_brief_path"]:
            required_blockers.add("missing_design_metadata")
        if not (explicit_creation_mode and task_mode == "implement"):
            if not text["source_url"] or not text["file_key_or_workspace"]:
                required_blockers.add("blocked_by_design_url")
            if (
                text["source_url"]
                and text["file_key_or_workspace"]
                and not text["node_id_or_frame_id"]
            ):
                required_blockers.add("blocked_by_node_id_capture")
    if not required_blockers.issubset(blockers):
        raise ValueError("design packet omits a required blocker")

    expected_mode = "read_only"
    if design_source not in READ_ONLY_DESIGN_SOURCES and task_mode and not blockers:
        expected_mode = task_mode
    if design_lane_mode != expected_mode:
        raise ValueError("design_lane_mode contradicts contract readiness")

    execution_ready = design_lane_mode in DESIGN_EXECUTION_TASK_MODES and not blockers
    if execution_ready and design_source in FIGMA_DESIGN_SOURCES:
        execution_ready = figma_packet_is_execution_ready(
            design_source=design_source,
            source_url=text["source_url"],
            file_key_or_workspace=text["file_key_or_workspace"],
            node_id_or_frame_id=text["node_id_or_frame_id"],
            target_surface=text["target_surface"],
            task_mode=task_mode,
            figma_lane_tool=figma_lane_tool,
            code_native_design_brief_path=text["code_native_design_brief_path"],
            explicit_creation_mode=cast(bool, explicit_creation_mode),
        )
    return DesignLanePacketProjection(
        mode=design_lane_mode,
        blockers=blockers,
        enabled=True,
        execution_ready=bool(execution_ready),
    )
