from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, cast

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VOCABULARY_PATH = PROJECT_ROOT / "docs" / "design" / "ui_component_vocabulary.json"
INSTRUCTION_DIR = PROJECT_ROOT / "scripts" / "design" / "instructions"
MANIFEST_PATH = PROJECT_ROOT / "docs" / "design" / "figma-manifest.json"

SUPPORTED_SCREENS = (
    "ios.home",
    "ios.plate",
    "ios.progress",
    "web.home",
    "web.plate",
    "web.progress",
)

SUPPORTED_INSTRUCTION_TYPES = {
    "create_frame",
    "create_button",
}

SUPPORTED_LAYOUT_ARCHETYPES = {
    "content_shell",
    "dashboard_shell",
    "hero_shell",
}

REQUIRED_INSTRUCTION_FIELDS = {
    "screen_id",
    "page",
    "platform",
    "surface",
    "layout_pattern",
    "layout_archetype",
    "primary_components",
    "supporting_components",
    "states",
    "sections",
    "component_hierarchy",
    "dimensions",
    "background_token",
    "token_constraints",
    "governance_checks",
    "context_version",
    "instructions",
}

REQUIRED_SECTION_FIELDS = {
    "section_id",
    "name",
    "role",
    "component_ids",
}

REQUIRED_COMPONENT_NODE_FIELDS = {
    "component_id",
    "canonical_component",
    "section_id",
    "parent_component_id",
    "hierarchy_level",
    "semantic_role",
    "source_ref",
}

RAW_HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")


def load_vocabulary_components() -> list[dict[str, Any]]:
    payload = json.loads(VOCABULARY_PATH.read_text(encoding="utf-8"))
    return cast(list[dict[str, Any]], payload)


def canonical_component_names() -> set[str]:
    return {str(component["canonical_name"]) for component in load_vocabulary_components()}


def instruction_path_for_screen(screen_id: str) -> Path:
    return INSTRUCTION_DIR / f"{screen_id.replace('.', '_')}.json"


def has_raw_hex(value: str) -> bool:
    return bool(RAW_HEX_RE.search(value))


def validate_instruction_contract(instruction: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    missing_fields = REQUIRED_INSTRUCTION_FIELDS.difference(instruction)
    if missing_fields:
        errors.append("Missing required instruction field(s): " + ", ".join(sorted(missing_fields)))
        return errors

    screen_id = str(instruction["screen_id"])
    if screen_id not in SUPPORTED_SCREENS:
        errors.append(f"Unsupported screen_id: {screen_id}")

    for field_name in ("surface", "layout_pattern", "background_token", "context_version"):
        raw_value = instruction.get(field_name, "")
        value = str(raw_value).strip()
        if not value:
            errors.append(f"Empty {field_name}")

    layout_archetype = str(instruction.get("layout_archetype", "")).strip()
    if not layout_archetype:
        errors.append("Empty layout_archetype")
    elif layout_archetype not in SUPPORTED_LAYOUT_ARCHETYPES:
        errors.append(f"Unsupported layout_archetype: {layout_archetype}")

    for field_name in (
        "primary_components",
        "supporting_components",
        "states",
        "token_constraints",
    ):
        list_value = instruction.get(field_name)
        if not isinstance(list_value, list) or not list_value:
            errors.append(f"{field_name} must be a non-empty list")

    valid_components = canonical_component_names()
    for field_name in ("primary_components", "supporting_components"):
        for component_name in instruction.get(field_name, []):
            if component_name not in valid_components:
                errors.append(f"Unknown canonical component in {field_name}: {component_name}")

    sections_value = instruction.get("sections", [])
    section_ids: set[str] = set()
    section_component_map: dict[str, list[str]] = {}
    if not isinstance(sections_value, list) or not sections_value:
        errors.append("sections must be a non-empty list")
    else:
        for index, section in enumerate(sections_value):
            if not isinstance(section, dict):
                errors.append(f"sections[{index}] must be an object")
                continue

            missing_section_fields = REQUIRED_SECTION_FIELDS.difference(section)
            if missing_section_fields:
                errors.append(
                    "sections[{index}] missing field(s): {fields}".format(
                        index=index,
                        fields=", ".join(sorted(missing_section_fields)),
                    )
                )
                continue

            section_id = str(section.get("section_id", "")).strip()
            if not section_id:
                errors.append(f"sections[{index}] missing section_id")
                continue
            if section_id in section_ids:
                errors.append(f"Duplicate section_id: {section_id}")
                continue

            component_ids = section.get("component_ids")
            if not isinstance(component_ids, list) or not component_ids:
                errors.append(f"sections[{index}] must define non-empty component_ids")
                continue

            section_ids.add(section_id)
            section_component_map[section_id] = [
                str(component_id) for component_id in component_ids
            ]

    hierarchy_value = instruction.get("component_hierarchy", [])
    component_ids: set[str] = set()
    component_nodes: dict[str, dict[str, Any]] = {}
    root_component_count = 0
    if not isinstance(hierarchy_value, list) or not hierarchy_value:
        errors.append("component_hierarchy must be a non-empty list")
    else:
        for index, node in enumerate(hierarchy_value):
            if not isinstance(node, dict):
                errors.append(f"component_hierarchy[{index}] must be an object")
                continue

            missing_node_fields = REQUIRED_COMPONENT_NODE_FIELDS.difference(node)
            if missing_node_fields:
                errors.append(
                    "component_hierarchy[{index}] missing field(s): {fields}".format(
                        index=index,
                        fields=", ".join(sorted(missing_node_fields)),
                    )
                )
                continue

            component_id = str(node.get("component_id", "")).strip()
            canonical_component = str(node.get("canonical_component", "")).strip()
            node_section_id = str(node.get("section_id", "")).strip()
            semantic_role = str(node.get("semantic_role", "")).strip()
            source_ref = str(node.get("source_ref", "")).strip()
            parent_component_id = node.get("parent_component_id")
            hierarchy_level = node.get("hierarchy_level")

            if not component_id:
                errors.append(f"component_hierarchy[{index}] missing component_id")
                continue
            if component_id in component_ids:
                errors.append(f"Duplicate component_id: {component_id}")
                continue
            if not semantic_role:
                errors.append(f"component_hierarchy[{index}] missing semantic_role")
            if not source_ref:
                errors.append(f"component_hierarchy[{index}] missing source_ref")
            if not isinstance(hierarchy_level, int) or hierarchy_level < 0:
                errors.append(f"component_hierarchy[{index}] hierarchy_level must be integer >= 0")
            if canonical_component not in valid_components:
                errors.append(
                    f"Unknown canonical component in component_hierarchy: {canonical_component}"
                )
            if section_ids and node_section_id not in section_ids:
                errors.append(
                    "Unknown section_id for component_hierarchy node "
                    f"{component_id}: {node_section_id}"
                )

            if parent_component_id in (None, ""):
                root_component_count += 1
            elif not isinstance(parent_component_id, str):
                errors.append(
                    "component_hierarchy[{index}] parent_component_id must be null or string".format(
                        index=index
                    )
                )

            component_ids.add(component_id)
            component_nodes[component_id] = {
                "canonical_component": canonical_component,
                "section_id": node_section_id,
                "parent_component_id": parent_component_id,
                "hierarchy_level": hierarchy_level,
            }

        for component_id, node in component_nodes.items():
            parent_component_id = node.get("parent_component_id")
            if isinstance(parent_component_id, str) and parent_component_id not in component_ids:
                errors.append(
                    "Unknown parent_component_id for component_hierarchy node "
                    f"{component_id}: {parent_component_id}"
                )
            parent_node = (
                component_nodes.get(parent_component_id)
                if isinstance(parent_component_id, str)
                else None
            )
            if (
                parent_node is not None
                and isinstance(parent_node.get("hierarchy_level"), int)
                and isinstance(node.get("hierarchy_level"), int)
                and node["hierarchy_level"] <= parent_node["hierarchy_level"]
            ):
                errors.append(
                    "component_hierarchy node must have hierarchy_level greater than parent: "
                    f"{component_id}"
                )

        if root_component_count != 1:
            errors.append(
                "component_hierarchy must contain exactly one root component, "
                f"got {root_component_count}"
            )

        for section_id, referenced_component_ids in section_component_map.items():
            for component_id in referenced_component_ids:
                if component_id not in component_ids:
                    errors.append(
                        "sections reference unknown component_id: "
                        f"{section_id} -> {component_id}"
                    )

    background_token = str(instruction.get("background_token", ""))
    if has_raw_hex(background_token):
        errors.append(f"Raw hex color used in background_token: {background_token}")

    token_constraints = instruction.get("token_constraints", [])
    for token_value in token_constraints:
        token_text = str(token_value).strip()
        if not token_text:
            errors.append("Empty token_constraints entry")
        elif has_raw_hex(token_text):
            errors.append(f"Raw hex color used in token_constraints: {token_text}")

    instructions_list = instruction.get("instructions", [])
    if not isinstance(instructions_list, list) or not instructions_list:
        errors.append("instructions must be a non-empty list")
        return errors

    frame_count = 0
    for index, item in enumerate(instructions_list):
        if not isinstance(item, dict):
            errors.append(f"instructions[{index}] must be an object")
            continue

        item_type = str(item.get("type", "")).strip()
        if item_type not in SUPPORTED_INSTRUCTION_TYPES:
            errors.append(f"Unsupported instruction type: {item_type or '<empty>'}")
            continue

        item_name = str(item.get("name", "")).strip()
        if not item_name:
            errors.append(f"{item_type} at instructions[{index}] missing name")

        component_id = str(item.get("component_id", "")).strip()
        if not component_id:
            errors.append(f"{item_type} at instructions[{index}] missing component_id")
        elif component_ids and component_id not in component_ids:
            errors.append(
                f"{item_type} at instructions[{index}] references unknown component_id: {component_id}"
            )

        item_section_id = str(item.get("section_id", "")).strip()
        if not item_section_id:
            errors.append(f"{item_type} at instructions[{index}] missing section_id")
        elif section_ids and item_section_id not in section_ids:
            errors.append(
                f"{item_type} at instructions[{index}] references unknown section_id: {item_section_id}"
            )

        order_value = item.get("order")
        if not isinstance(order_value, int) or order_value < 0:
            errors.append(f"{item_type} at instructions[{index}] must define integer order >= 0")

        hierarchy_level = item.get("hierarchy_level")
        if not isinstance(hierarchy_level, int) or hierarchy_level < 0:
            errors.append(f"{item_type} at instructions[{index}] must define hierarchy_level >= 0")

        parent_component_id = item.get("parent_component_id")
        if parent_component_id not in (None, "") and (
            not isinstance(parent_component_id, str) or parent_component_id not in component_ids
        ):
            errors.append(
                f"{item_type} at instructions[{index}] references unknown parent_component_id"
            )

        if item_type == "create_frame":
            frame_count += 1
            if "background" not in item:
                errors.append("create_frame missing background")
            if parent_component_id not in (None, ""):
                errors.append("create_frame must not define parent_component_id")

        if item_type == "create_button":
            cta_key = str(item.get("cta_key", "")).strip()
            if not cta_key:
                errors.append(f"Button {item_name or index} missing cta_key")

            button_states = item.get("states")
            if not isinstance(button_states, list) or not button_states:
                errors.append(f"Button {item_name or index} missing states list")

            canonical_component = str(item.get("canonical_component", "")).strip()
            if canonical_component != "button":
                errors.append(f"Button {item_name or index} must set canonical_component=button")

            hierarchy_node = component_nodes.get(component_id)
            if hierarchy_node and hierarchy_node.get("canonical_component") != "button":
                errors.append(
                    f"Button {item_name or index} must reference a button component_hierarchy node"
                )

    if frame_count != 1:
        errors.append(f"Instruction must contain exactly one create_frame, got {frame_count}")

    return errors
