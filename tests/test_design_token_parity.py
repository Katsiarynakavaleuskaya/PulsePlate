from __future__ import annotations

import json
import re
import subprocess
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOKENS_CSS = REPO_ROOT / "frontend" / "src" / "styles" / "tokens.css"
TOKENS_TS = REPO_ROOT / "frontend" / "src" / "styles" / "tokens.ts"
SWIFT_GENERATED = REPO_ROOT / "ios" / "PulsePlate" / "DesignSystem" / "DesignTokens.generated.swift"
SWIFT_FACADE = REPO_ROOT / "ios" / "PulsePlate" / "DesignSystem" / "DesignTokens.swift"
SWIFT_ASSET_BRIDGE = REPO_ROOT / "ios" / "PulsePlate" / "Extensions" / "Color+Assets.swift"
TOKENS_CORE_COLOR = REPO_ROOT / "tokens" / "00_core" / "color.json"
TOKENS_SEMANTIC_COLOR = REPO_ROOT / "tokens" / "10_semantic" / "color.json"
TOKENS_IOS_PLATFORM = REPO_ROOT / "tokens" / "30_platform" / "ios.json"

CSS_VAR_RE = re.compile(r"--(?P<name>[a-z0-9-]+):\s*(?P<value>[^;]+);", re.IGNORECASE)
CSS_VAR_REF_RE = re.compile(r"var\(--(?P<name>[a-z0-9-]+)\)", re.IGNORECASE)
HEX_RE = re.compile(r"#[0-9a-fA-F]{6}")
TS_ENTRY_RE = re.compile(r"(?P<key>[A-Za-z0-9]+|\"[^\"]+\"):\s*(?P<value>[^,\n]+)")
SWIFT_ASSET_RE = re.compile(r'static let (?P<key>\w+) = "(?P<asset>[^"]+)"')
SWIFT_COLOR_TOKEN_RE = re.compile(r"static let (?P<key>\w+) = (?P<value>.+)")

CSS_BRAND_KEYS = {
    "navy": "pp-navy",
    "blue": "pp-blue",
    "green": "pp-green",
    "red": "pp-red",
    "gold": "pp-gold",
}
SEMANTIC_KEYS = {
    "success": "color-success",
    "warning": "color-warning",
    "error": "color-error",
    "info": "color-info",
}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalize_hex(value: str) -> str:
    match = HEX_RE.search(value)
    if match is None:
        raise AssertionError(f"Expected hex value, got: {value!r}")
    return match.group(0).upper()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_block(text: str, marker: str) -> str:
    marker_index = text.index(marker)
    start_index = text.index("{", marker_index)
    depth = 0

    for index in range(start_index, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start_index + 1 : index]

    raise AssertionError(f"Unterminated block for marker: {marker}")


def _extract_css_variables() -> dict[str, str]:
    root_block = _extract_block(_read_text(TOKENS_CSS), ":root")
    return {
        match.group("name"): match.group("value").strip()
        for match in CSS_VAR_RE.finditer(root_block)
    }


def _resolve_css_value(value: str, variables: dict[str, str]) -> str:
    current = value.strip()
    visited: set[str] = set()

    while True:
        var_match = CSS_VAR_REF_RE.fullmatch(current)
        if var_match is None:
            return current

        var_name = var_match.group("name")
        if var_name in visited:
            raise AssertionError(f"Cyclic CSS variable reference detected: {var_name}")
        visited.add(var_name)
        current = variables[var_name].strip()


def _extract_css_palette(mapping: dict[str, str]) -> dict[str, str]:
    variables = _extract_css_variables()
    return {
        token_name: _normalize_hex(_resolve_css_value(variables[css_var], variables))
        for token_name, css_var in mapping.items()
    }


def _extract_ts_simple_object(marker: str) -> dict[str, str]:
    block = _extract_block(_read_text(TOKENS_TS), marker)
    parsed: dict[str, str] = {}
    for match in TS_ENTRY_RE.finditer(block):
        key = match.group("key").strip('"')
        parsed[key] = match.group("value").strip()
    return parsed


def _extract_ts_brand_palette() -> dict[str, str]:
    return {
        key: _normalize_hex(value)
        for key, value in _extract_ts_simple_object("export const canonicalBrand =").items()
    }


def _extract_ts_semantic_palette() -> dict[str, str]:
    brand_palette = _extract_ts_brand_palette()
    semantic_block = _extract_block(
        _extract_block(_read_text(TOKENS_TS), "export const colors ="),
        "semantic:",
    )
    semantic_values: dict[str, str] = {}

    for match in TS_ENTRY_RE.finditer(semantic_block):
        key = match.group("key").strip('"')
        raw_value = match.group("value").strip()
        brand_match = re.fullmatch(r"canonicalBrand\.(\w+)", raw_value)
        if brand_match is not None:
            semantic_values[key] = brand_palette[brand_match.group(1)]
            continue
        semantic_values[key] = _normalize_hex(raw_value)

    return semantic_values


def _extract_swift_brand_assets() -> dict[str, str]:
    asset_block = _extract_block(_read_text(SWIFT_GENERATED), "enum BrandAsset")
    return {
        match.group("key"): match.group("asset") for match in SWIFT_ASSET_RE.finditer(asset_block)
    }


def _extract_swift_semantic_palette() -> dict[str, str]:
    color_block = _extract_block(_read_text(SWIFT_GENERATED), "enum ColorToken")
    semantic_values: dict[str, str] = {}

    for line in color_block.splitlines():
        match = SWIFT_COLOR_TOKEN_RE.fullmatch(line.strip())
        if match is None:
            continue

        key = match.group("key")
        if key not in SEMANTIC_KEYS:
            continue

        raw_value = match.group("value")
        brand_match = re.fullmatch(r"Brand\.(\w+)", raw_value)
        if brand_match is not None:
            semantic_values[key] = _source_brand_palette()[brand_match.group(1)]
            continue
        semantic_values[key] = _normalize_hex(raw_value)

    return semantic_values


def _component_to_byte(raw_value: str) -> int:
    value = Decimal(str(raw_value))
    if value <= 1:
        return int((value * Decimal(255)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _asset_universal_hex(path: Path) -> str:
    payload = _load_json(path)
    for color_entry in payload.get("colors", []):
        if color_entry.get("appearances"):
            continue

        components = color_entry["color"]["components"]
        red = _component_to_byte(components["red"])
        green = _component_to_byte(components["green"])
        blue = _component_to_byte(components["blue"])
        return f"#{red:02X}{green:02X}{blue:02X}"

    raise AssertionError(f"No universal color found in asset: {path}")


def _source_brand_palette() -> dict[str, str]:
    payload = _load_json(TOKENS_CORE_COLOR)["color"]["brand"]
    return {key: _normalize_hex(payload[key]["$value"]) for key in CSS_BRAND_KEYS}


def _source_semantic_palette() -> dict[str, str]:
    payload = _load_json(TOKENS_SEMANTIC_COLOR)["semantic"]["color"]
    return {key: _normalize_hex(payload[key]["$value"]) for key in SEMANTIC_KEYS}


def _source_ios_assets() -> dict[str, str]:
    payload = _load_json(TOKENS_IOS_PLATFORM)["platform"]["ios"]["asset"]
    return {key: value["$value"] for key, value in payload.items()}


def _extract_ios_asset_palette() -> dict[str, str]:
    assets_root = REPO_ROOT / "ios" / "PulsePlate" / "Assets.xcassets"
    palette: dict[str, str] = {}

    for token_name, asset_name in _source_ios_assets().items():
        asset_path = assets_root / f"{asset_name}.colorset" / "Contents.json"
        palette[token_name] = _asset_universal_hex(asset_path)

    return palette


def test_tokens_source_brand_palette_matches_css() -> None:
    assert _extract_css_palette(CSS_BRAND_KEYS) == _source_brand_palette()


def test_tokens_source_brand_palette_matches_typescript_mirror() -> None:
    assert _extract_ts_brand_palette() == _source_brand_palette()


def test_tokens_source_semantic_palette_matches_css_and_ts() -> None:
    source_palette = _source_semantic_palette()
    assert _extract_css_palette(SEMANTIC_KEYS) == source_palette
    assert _extract_ts_semantic_palette() == source_palette


def test_ios_asset_palette_matches_source_brand_palette() -> None:
    assert _extract_ios_asset_palette() == _source_brand_palette()


def test_generated_swift_brand_assets_match_ios_platform_contract() -> None:
    assert _extract_swift_brand_assets() == _source_ios_assets()


def test_generated_swift_semantic_palette_matches_source_tokens() -> None:
    assert _extract_swift_semantic_palette() == _source_semantic_palette()


def test_facade_routes_public_tokens_through_generated_layer() -> None:
    facade = _read_text(SWIFT_FACADE)
    assert "GeneratedDesignTokens.Brand.navy" in facade
    assert "GeneratedDesignTokens.ColorToken.warning" in facade
    assert "GeneratedDesignTokens.Spacing.buttonPaddingMedium" in facade
    assert "GeneratedDesignTokens.Motion.fast" in facade


def test_swift_asset_extension_routes_heart_to_brand_red() -> None:
    extension_text = _read_text(SWIFT_ASSET_BRIDGE)
    assert "static let heart = PPDesignTokens.Brand.red" in extension_text


def test_token_build_script_is_deterministic() -> None:
    tracked_paths = [TOKENS_CSS, TOKENS_TS, SWIFT_GENERATED]
    before = {path: _read_text(path) for path in tracked_paths}

    for _ in range(2):
        result = subprocess.run(
            ["node", "frontend/scripts/build-tokens.mjs"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr or result.stdout

    after = {path: _read_text(path) for path in tracked_paths}
    assert after == before
