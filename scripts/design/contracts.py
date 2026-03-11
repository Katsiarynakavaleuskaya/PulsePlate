from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

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

REQUIRED_INSTRUCTION_FIELDS = {
    "screen_id",
    "page",
    "platform",
    "surface",
    "layout_pattern",
    "primary_components",
    "supporting_components",
    "states",
    "dimensions",
    "background_token",
    "token_constraints",
    "governance_checks",
    "context_version",
    "instructions",
}

RAW_HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")


def load_vocabulary_components() -> list[dict[str, Any]]:
    return json.loads(VOCABULARY_PATH.read_text(encoding="utf-8"))


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
        value = str(instruction.get(field_name, "")).strip()
        if not value:
            errors.append(f"Empty {field_name}")

    for field_name in (
        "primary_components",
        "supporting_components",
        "states",
        "token_constraints",
    ):
        value = instruction.get(field_name)
        if not isinstance(value, list) or not value:
            errors.append(f"{field_name} must be a non-empty list")

    valid_components = canonical_component_names()
    for field_name in ("primary_components", "supporting_components"):
        for component_name in instruction.get(field_name, []):
            if component_name not in valid_components:
                errors.append(f"Unknown canonical component in {field_name}: {component_name}")

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

        if item_type == "create_frame":
            frame_count += 1
            if "background" not in item:
                errors.append("create_frame missing background")

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

    if frame_count != 1:
        errors.append(f"Instruction must contain exactly one create_frame, got {frame_count}")

    return errors
