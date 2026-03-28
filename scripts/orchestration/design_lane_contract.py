"""Shared helpers for deterministic design-lane orchestration contracts.

RU: Общие константы и нормализация для packet-driven design lane.
EN: Shared constants and normalization helpers for packet-driven design lanes.
"""

from __future__ import annotations

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


def normalize_optional_text(value: str | None) -> str:
    """Return a stripped optional string."""

    if value is None:
        return ""
    return value.strip()


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
    return sorted(
        dedupe_preserve_order(list(design_blockers)),
        key=lambda blocker: blocker_rank[blocker],
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
