from __future__ import annotations

import json
import re
import shutil
import subprocess
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TOKENS_CSS = REPO_ROOT / "frontend" / "src" / "styles" / "tokens.css"
TOKENS_TS = REPO_ROOT / "frontend" / "src" / "styles" / "tokens.ts"
SWIFT_GENERATED = REPO_ROOT / "ios" / "PulsePlate" / "DesignSystem" / "DesignTokens.generated.swift"
SWIFT_FACADE = REPO_ROOT / "ios" / "PulsePlate" / "DesignSystem" / "DesignTokens.swift"
SWIFT_ASSET_BRIDGE = REPO_ROOT / "ios" / "PulsePlate" / "Extensions" / "Color+Assets.swift"
TOKENS_CORE_COLOR = REPO_ROOT / "tokens" / "00_core" / "color.json"
TOKENS_SEMANTIC_COLOR = REPO_ROOT / "tokens" / "10_semantic" / "color.json"
TOKENS_PRODUCT_COLOR = REPO_ROOT / "tokens" / "20_product" / "color.json"
TOKENS_IOS_PLATFORM = REPO_ROOT / "tokens" / "30_platform" / "ios.json"

CSS_VAR_RE = re.compile(r"--(?P<name>[a-z0-9-]+):\s*(?P<value>[^;]+);", re.IGNORECASE)
CSS_VAR_REF_RE = re.compile(r"var\(--(?P<name>[a-z0-9-]+)\)", re.IGNORECASE)
HEX_RE = re.compile(r"#[0-9a-fA-F]{6}")
TS_ENTRY_RE = re.compile(r"(?P<key>[A-Za-z0-9]+|\"[^\"]+\"):\s*(?P<value>[^,\n]+)")
SWIFT_ASSET_RE = re.compile(r'static let (?P<key>\w+) = "(?P<asset>[^"]+)"')
SWIFT_COLOR_TOKEN_RE = re.compile(r"static let (?P<key>\w+) = (?P<value>.+)")
TOKEN_REFERENCE_RE = re.compile(r"\{(?P<path>[^}]+)\}")

CSS_BRAND_KEYS = {
    "navy": "pp-navy",
    "blue": "pp-blue",
    "green": "pp-green",
    "red": "pp-red",
    "gold": "pp-gold",
}
WEB_SEMANTIC_KEYS = {
    "success": "color-success",
    "warning": "color-warning",
    "error": "color-error",
    "info": "color-info",
}
SWIFT_PUBLIC_SEMANTIC_KEYS = {
    "success",
    "warning",
    "error",
    "info",
    "textPrimary",
    "textSecondary",
    "textTertiary",
    "surface",
    "surfaceElevated",
    "surfaceHighlight",
    "strokeSubtle",
    "primary",
    "primaryForeground",
}

PRODUCT_TOKEN_REFERENCE_RE = re.compile(
    r"productColors|ProductColor|--product-color-|product\.color"
)
PRODUCT_TOKEN_ALLOWED_REFERENCE_PATHS = {
    Path("frontend/scripts/build-tokens.mjs"),
    Path("frontend/src/styles/tokens.css"),
    Path("frontend/src/styles/tokens.ts"),
    Path("ios/PulsePlate/DesignSystem/DesignTokens.generated.swift"),
    Path("tests/test_design_token_parity.py"),
}
PRODUCT_TOKEN_ALLOWED_REFERENCE_DIRS = {
    Path("docs"),
    Path("tokens"),
}


def _tracked_repo_files() -> list[Path]:
    git_path = shutil.which("git")
    assert git_path is not None, "git is required for tracked-file parity checks"
    result = subprocess.run(
        [git_path, "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return [REPO_ROOT / line for line in result.stdout.splitlines() if line]


def _deep_merge(left: dict, right: dict) -> dict:
    merged = dict(left)
    for key, value in right.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalize_hex(value: str) -> str:
    match = HEX_RE.search(value)
    if match is None:
        raise AssertionError(f"Expected hex value, got: {value!r}")
    return match.group(0).upper()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_token_authoring_tree() -> dict:
    payload: dict = {}
    for path in sorted((REPO_ROOT / "tokens").glob("**/*.json")):
        payload = _deep_merge(payload, _load_json(path))
    return payload


def _token_payload_value(payload: dict) -> object:
    if "$value" in payload:
        return payload["$value"]
    if "value" in payload:
        return payload["value"]
    return payload


def _token_path(payload: dict, reference: str) -> object:
    current: object = payload
    for segment in reference.split("."):
        assert isinstance(current, dict), f"Token reference cannot descend into {current!r}"
        current = current[segment]
    assert isinstance(
        current, dict
    ), f"Token reference did not resolve to a token object: {reference}"
    return _token_payload_value(current)


def _resolve_token_reference(payload: dict, value: object) -> object:
    current = value
    visited: set[str] = set()
    while isinstance(current, str):
        match = re.fullmatch(r"\{(.+)\}", current)
        if match is None:
            return current

        reference = match.group(1)
        if reference in visited:
            raise AssertionError(f"Cyclic token reference detected: {reference}")
        visited.add(reference)
        current = _token_path(payload, reference)
    return current


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


def _extract_ts_product_palette() -> dict[str, dict[str, str]]:
    text = _read_text(TOKENS_TS)
    source_palette = _source_product_palette()
    product_block = _extract_block(text, "export const productColors =")
    product_values: dict[str, dict[str, str]] = {}

    for family, roles in source_palette.items():
        family_block = _extract_block(product_block, f"{family}:")
        product_values[family] = {}
        for match in TS_ENTRY_RE.finditer(family_block):
            key = match.group("key").strip('"')
            if key not in roles:
                continue
            product_values[family][key] = _normalize_hex(match.group("value").strip())

    return product_values


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
        if key not in SWIFT_PUBLIC_SEMANTIC_KEYS:
            continue

        semantic_values[key] = match.group("value").strip()

    return semantic_values


def _extract_swift_product_palette() -> dict[str, str]:
    product_block = _extract_block(_read_text(SWIFT_GENERATED), "enum ProductColor")
    return {
        match.group("key"): match.group("value").strip()
        for line in product_block.splitlines()
        if (match := SWIFT_COLOR_TOKEN_RE.fullmatch(line.strip())) is not None
    }


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
    return {key: _normalize_hex(payload[key]["$value"]) for key in WEB_SEMANTIC_KEYS}


def _source_product_palette() -> dict[str, dict[str, str]]:
    authoring_tree = _load_token_authoring_tree()
    product_payload = _load_json(TOKENS_PRODUCT_COLOR)["product"]["color"]
    return {
        family: {
            role: _normalize_hex(
                str(_resolve_token_reference(authoring_tree, role_payload["$value"]))
            )
            for role, role_payload in roles.items()
        }
        for family, roles in product_payload.items()
    }


def _source_product_reference_map() -> dict[str, dict[str, str]]:
    product_payload = _load_json(TOKENS_PRODUCT_COLOR)["product"]["color"]
    reference_map: dict[str, dict[str, str]] = {}

    for family, roles in product_payload.items():
        reference_map[family] = {}
        for role, role_payload in roles.items():
            reference = role_payload["$value"]
            match = TOKEN_REFERENCE_RE.fullmatch(reference)
            assert match is not None, f"Product token must alias an existing token: {family}.{role}"
            reference_map[family][role] = match.group("path")

    return reference_map


def _source_product_css_mapping() -> dict[str, str]:
    product_payload = _load_json(TOKENS_PRODUCT_COLOR)["product"]["color"]
    return {
        f"{family}.{role}": f"product-color-{family}-{_css_role_name(role)}"
        for family, roles in product_payload.items()
        for role in roles
    }


def _css_role_name(role: str) -> str:
    return re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", role).lower()


def _css_variable_for_reference(reference: str) -> str:
    parts = reference.split(".")
    if parts[:2] == ["semantic", "color"]:
        return f"var(--color-{'-'.join(_css_role_name(part) for part in parts[2:])})"
    if parts[:2] == ["color", "brand"]:
        return f"var(--pp-{'-'.join(_css_role_name(part) for part in parts[2:])})"
    if parts[:2] == ["color", "scale"]:
        return f"var(--color-{'-'.join(_css_role_name(part) for part in parts[2:])})"
    raise AssertionError(f"Unsupported product token reference for CSS alias: {reference}")


def _source_product_css_aliases() -> dict[str, str]:
    return {
        f"{family}.{role}": _css_variable_for_reference(reference)
        for family, roles in _source_product_reference_map().items()
        for role, reference in roles.items()
    }


def _swift_color_expression_from_source(value: str) -> str:
    if value.startswith("Color."):
        return value

    normalized = value.upper()
    for brand_name, brand_hex in _source_brand_palette().items():
        if normalized == brand_hex:
            return f"Brand.{brand_name}"

    if normalized == "#FFFFFF":
        return "Color.white"

    return f'Color(hex: "{normalized}")'


def _source_swift_semantic_palette() -> dict[str, str]:
    semantic_payload = _load_json(TOKENS_SEMANTIC_COLOR)["semantic"]["color"]
    ios_payload = _load_json(TOKENS_IOS_PLATFORM)["platform"]["ios"]["semantic"]

    swift_values = {
        key: _swift_color_expression_from_source(semantic_payload[key]["$value"])
        for key in ("success", "warning", "error", "info", "primary", "primaryForeground")
    }
    swift_values.update(
        {
            key: ios_payload[key]["$value"]
            for key in (
                "textPrimary",
                "textSecondary",
                "textTertiary",
                "surface",
                "surfaceElevated",
                "surfaceHighlight",
                "strokeSubtle",
            )
        }
    )
    return swift_values


def _source_swift_product_palette() -> dict[str, str]:
    return {
        f"{family}{role[:1].upper()}{role[1:]}": _swift_color_expression_from_source(value)
        for family, roles in _source_product_palette().items()
        for role, value in roles.items()
    }


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
    assert _extract_css_palette(WEB_SEMANTIC_KEYS) == source_palette
    assert _extract_ts_semantic_palette() == source_palette


def test_tokens_source_product_palette_matches_css_and_ts() -> None:
    source_palette = _source_product_palette()
    css_palette = _extract_css_palette(_source_product_css_mapping())
    assert {
        family: {role: css_palette[f"{family}.{role}"] for role in roles}
        for family, roles in source_palette.items()
    } == source_palette
    assert _extract_ts_product_palette() == source_palette


def test_product_tokens_are_aliases_and_css_preserves_aliases() -> None:
    variables = _extract_css_variables()
    css_mapping = _source_product_css_mapping()
    expected_aliases = _source_product_css_aliases()

    assert {
        token_name: variables[css_var] for token_name, css_var in css_mapping.items()
    } == expected_aliases


def test_product_tokens_are_not_consumed_outside_token_runtime_surfaces() -> None:
    blocked_references: list[str] = []

    for path in _tracked_repo_files():
        relative_path = path.relative_to(REPO_ROOT)
        if not path.is_file():
            continue
        if relative_path in PRODUCT_TOKEN_ALLOWED_REFERENCE_PATHS:
            continue
        if any(
            relative_path.is_relative_to(directory)
            for directory in PRODUCT_TOKEN_ALLOWED_REFERENCE_DIRS
        ):
            continue

        text = path.read_text(encoding="utf-8", errors="ignore")
        if PRODUCT_TOKEN_REFERENCE_RE.search(text):
            blocked_references.append(str(relative_path))

    assert blocked_references == []


def test_ios_asset_palette_matches_source_brand_palette() -> None:
    assert _extract_ios_asset_palette() == _source_brand_palette()


def test_generated_swift_brand_assets_match_ios_platform_contract() -> None:
    assert _extract_swift_brand_assets() == _source_ios_assets()


def test_generated_swift_semantic_palette_matches_source_tokens() -> None:
    assert _extract_swift_semantic_palette() == _source_swift_semantic_palette()


def test_generated_swift_product_palette_matches_source_tokens() -> None:
    assert _extract_swift_product_palette() == _source_swift_product_palette()


def test_facade_routes_public_tokens_through_generated_layer() -> None:
    facade = _read_text(SWIFT_FACADE)
    assert "GeneratedDesignTokens.Brand.navy" in facade
    assert "GeneratedDesignTokens.Spacing.buttonPaddingMedium" in facade
    assert "GeneratedDesignTokens.Motion.fast" in facade
    for token_name in sorted(SWIFT_PUBLIC_SEMANTIC_KEYS):
        assert f"GeneratedDesignTokens.ColorToken.{token_name}" in facade


def test_swift_asset_extension_routes_heart_to_brand_red() -> None:
    extension_text = _read_text(SWIFT_ASSET_BRIDGE)
    assert "static let heart = PPDesignTokens.Brand.red" in extension_text


def test_token_build_script_is_deterministic() -> None:
    tracked_paths = [TOKENS_CSS, TOKENS_TS, SWIFT_GENERATED]
    before = {path: _read_text(path) for path in tracked_paths}
    node_path = shutil.which("node")
    if node_path is None:
        pytest.skip("Node.js is required for token parity checks")
    if not (REPO_ROOT / "frontend" / "node_modules" / "style-dictionary").exists():
        pytest.skip("Token parity determinism test requires frontend/style-dictionary toolchain")

    snapshots: list[dict[Path, str]] = []
    for _ in range(2):
        result = subprocess.run(
            [node_path, "frontend/scripts/build-tokens.mjs"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr or result.stdout
        snapshots.append({path: _read_text(path) for path in tracked_paths})

    assert snapshots[0] == before
    assert snapshots[0] == snapshots[1]
