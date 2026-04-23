from __future__ import annotations

from typing import Any, TypedDict, cast

PULSEPLATE_CANVAS_V1 = "pulseplate_canvas_v1"
CANVAS_ARTIFACT_VERSION = PULSEPLATE_CANVAS_V1


class CanvasSection(TypedDict):
    section_id: str
    name: str
    role: str
    component_ids: list[str]


class CanvasNode(TypedDict):
    component_id: str
    canonical_component: str
    section_id: str
    parent_component_id: str | None
    hierarchy_level: int
    semantic_role: str
    source_ref: str


class CanvasRenderOp(TypedDict):
    op: str
    instruction_type: str
    name: str
    component_id: str
    canonical_component: str
    section_id: str
    parent_component_id: str | None
    hierarchy_level: int
    semantic_role: str
    order: int
    cta_key: str | None
    states: list[str]


class InteractionContract(TypedDict):
    interaction_mode: str
    checkpoint_policy: str
    adaptation_scope: list[str]
    modality_hints: list[str]
    explanation_strategy: str


class PulsePlateCanvasArtifact(TypedDict):
    canvas_version: str
    screen_id: str
    platform: str
    surface: str
    layout_archetype: str
    layout_pattern: str
    dimensions: dict[str, int]
    background_token: str
    token_constraints: list[str]
    interaction_contract: InteractionContract
    sections: list[CanvasSection]
    nodes: list[CanvasNode]
    render_ops: list[CanvasRenderOp]


def _normalize_token_constraints(raw_value: Any) -> list[str]:
    """Normalize token constraints without turning malformed strings into char arrays."""

    if not isinstance(raw_value, list):
        return []

    return [str(token) for token in raw_value]


def _build_interaction_contract(instruction: dict[str, Any]) -> InteractionContract:
    interaction_contract = instruction["interaction_contract"]
    if not isinstance(interaction_contract, dict):
        raise ValueError("interaction_contract must be an object")

    adaptation_scope = interaction_contract.get("adaptation_scope")
    modality_hints = interaction_contract.get("modality_hints")
    if not isinstance(adaptation_scope, list) or not isinstance(modality_hints, list):
        raise ValueError("interaction_contract list fields must be lists")

    return {
        "interaction_mode": str(interaction_contract["interaction_mode"]),
        "checkpoint_policy": str(interaction_contract["checkpoint_policy"]),
        "adaptation_scope": [str(scope) for scope in adaptation_scope],
        "modality_hints": [str(hint) for hint in modality_hints],
        "explanation_strategy": str(interaction_contract["explanation_strategy"]),
    }


def _build_sections(instruction: dict[str, Any]) -> list[CanvasSection]:
    sections = instruction.get("sections", [])
    return [
        {
            "section_id": str(section["section_id"]),
            "name": str(section["name"]),
            "role": str(section["role"]),
            "component_ids": [str(component_id) for component_id in section["component_ids"]],
        }
        for section in sections
        if isinstance(section, dict)
    ]


def _build_nodes(instruction: dict[str, Any]) -> list[CanvasNode]:
    hierarchy = instruction.get("component_hierarchy", [])
    return [
        {
            "component_id": str(node["component_id"]),
            "canonical_component": str(node["canonical_component"]),
            "section_id": str(node["section_id"]),
            "parent_component_id": cast(str | None, node.get("parent_component_id")),
            "hierarchy_level": int(node["hierarchy_level"]),
            "semantic_role": str(node["semantic_role"]),
            "source_ref": str(node["source_ref"]),
        }
        for node in hierarchy
        if isinstance(node, dict)
    ]


def _build_render_ops(instruction: dict[str, Any]) -> list[CanvasRenderOp]:
    instructions = instruction.get("instructions", [])
    return [
        {
            "op": {
                "create_frame": "materialize_frame",
                "create_button": "materialize_button",
            }.get(str(item["type"]), "materialize_component"),
            "instruction_type": str(item["type"]),
            "name": str(item["name"]),
            "component_id": str(item["component_id"]),
            "canonical_component": str(item["canonical_component"]),
            "section_id": str(item["section_id"]),
            "parent_component_id": cast(str | None, item.get("parent_component_id")),
            "hierarchy_level": int(item["hierarchy_level"]),
            "semantic_role": str(item["semantic_role"]),
            "order": int(item["order"]),
            "cta_key": (None if item.get("cta_key") in (None, "") else str(item.get("cta_key"))),
            "states": (
                [str(state) for state in item.get("states", [])]
                if isinstance(item.get("states", []), list)
                else []
            ),
        }
        for item in instructions
        if isinstance(item, dict)
    ]


def build_canvas_artifact(instruction: dict[str, Any]) -> PulsePlateCanvasArtifact:
    """Materialize the canonical code-native canvas artifact from one instruction payload."""

    return {
        "canvas_version": PULSEPLATE_CANVAS_V1,
        "screen_id": str(instruction["screen_id"]),
        "platform": str(instruction["platform"]),
        "surface": str(instruction["surface"]),
        "layout_archetype": str(instruction["layout_archetype"]),
        "layout_pattern": str(instruction["layout_pattern"]),
        "dimensions": cast(dict[str, int], instruction["dimensions"]),
        "background_token": str(instruction["background_token"]),
        "token_constraints": _normalize_token_constraints(instruction.get("token_constraints", [])),
        "interaction_contract": _build_interaction_contract(instruction),
        "sections": _build_sections(instruction),
        "nodes": _build_nodes(instruction),
        "render_ops": _build_render_ops(instruction),
    }


def derive_render_plan(canvas_artifact: PulsePlateCanvasArtifact) -> list[dict[str, Any]]:
    """Keep the legacy render-plan shape as a derived compatibility field."""

    return [
        {
            "op": render_op["op"],
            "instruction_type": render_op["instruction_type"],
            "name": render_op["name"],
            "component_id": render_op["component_id"],
            "canonical_component": render_op["canonical_component"],
            "section_id": render_op["section_id"],
            "parent_component_id": render_op["parent_component_id"],
            "hierarchy_level": render_op["hierarchy_level"],
            "semantic_role": render_op["semantic_role"],
            "order": render_op["order"],
            "states": list(render_op["states"]),
        }
        for render_op in canvas_artifact["render_ops"]
    ]


def build_render_plan_from_canvas(
    canvas_artifact: PulsePlateCanvasArtifact,
) -> list[dict[str, Any]]:
    """Compatibility wrapper for runtime callers already using the old helper name."""

    return derive_render_plan(canvas_artifact)
