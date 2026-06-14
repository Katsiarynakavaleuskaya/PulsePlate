import json
import re
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTEXT7_PACKAGE = "@upstash/context7-mcp"
CONTEXT7_PINNED_PACKAGE = "@upstash/context7-mcp@3.1.0"
EXACT_NUMERIC_VERSION = re.compile(r"\d+\.\d+\.\d+\Z")
PLAYWRIGHT_UNRESTRICTED_ENV = "PLAYWRIGHT_MCP_ALLOW_UNRESTRICTED_FILE_ACCESS"
TRUTHY_ENV_VALUES = {"1", "true", "yes", "on"}

MCP_EXAMPLE_PATHS = (
    REPO_ROOT / ".cursor/mcp.json.example",
    REPO_ROOT / ".kimi/mcp.json.example",
)
GOVERNED_MCP_DOC_PATHS = (REPO_ROOT / "docs/runbooks/OPENAI_EXTERNAL_DOCS_FRESHNESS_PILOT.md",)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _first_npx_package_arg(args: object) -> str | None:
    if not isinstance(args, list):
        return None
    for arg in args:
        if isinstance(arg, str) and arg and not arg.startswith("-"):
            return arg
    return None


def _is_exact_pinned_package_spec(spec: str) -> bool:
    spec_parts = spec.rsplit("@", 1)
    if len(spec_parts) != 2:
        return False

    package_name, version = spec_parts
    if not package_name:
        return False
    if package_name.startswith("@"):
        scope, slash, package = package_name.partition("/")
        if not scope or not slash or not package:
            return False
    elif "@" in package_name:
        return False
    return bool(EXACT_NUMERIC_VERSION.fullmatch(version))


def _is_truthy_env_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().casefold() in TRUTHY_ENV_VALUES
    if isinstance(value, int):
        return value != 0
    return False


def _playwright_unrestricted_env_is_truthy(server_config: dict[str, Any]) -> bool:
    env = server_config.get("env", {})
    if not isinstance(env, dict):
        return False
    return _is_truthy_env_value(env.get(PLAYWRIGHT_UNRESTRICTED_ENV))


def test_mcp_examples_do_not_enable_unrestricted_playwright_file_access() -> None:
    for path in MCP_EXAMPLE_PATHS:
        data = _load_json(path)
        playwright_args = data["mcpServers"]["playwright"]["args"]
        playwright_config = data["mcpServers"]["playwright"]

        assert "--allow-unrestricted-file-access" not in playwright_args, path
        assert not _playwright_unrestricted_env_is_truthy(playwright_config), path


def test_mcp_examples_pin_npx_mcp_packages() -> None:
    for path in MCP_EXAMPLE_PATHS:
        data = _load_json(path)
        for server_name, server_config in data["mcpServers"].items():
            if server_config.get("command") != "npx":
                continue

            package_arg = _first_npx_package_arg(server_config.get("args", []))
            assert package_arg, f"{path}:{server_name} has no npx package arg"
            assert _is_exact_pinned_package_spec(
                package_arg
            ), f"{path}:{server_name} package is not exactly pinned: {package_arg}"


def test_documented_context7_mcp_examples_pin_local_npx_package() -> None:
    for path in GOVERNED_MCP_DOC_PATHS:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if CONTEXT7_PACKAGE not in line:
                continue

            assert CONTEXT7_PINNED_PACKAGE in line, f"{path}:{line_number}: {line}"


@pytest.mark.parametrize(
    "package_spec",
    [
        "@modelcontextprotocol/server-github@2025.4.8",
        "@playwright/mcp@0.0.75",
        "@upstash/context7-mcp@3.1.0",
        "some-tool@1.2.3",
    ],
)
def test_exact_pinned_package_spec_accepts_numeric_versions(package_spec: str) -> None:
    assert _is_exact_pinned_package_spec(package_spec)


@pytest.mark.parametrize(
    "package_spec",
    [
        "@scope/pkg",
        "@scope/pkg@",
        "@scope/pkg@latest",
        "@scope/pkg@next",
        "@scope/pkg@^1.2.3",
        "@scope/pkg@~1.2.3",
        "@scope/pkg@>=1.2.3",
        "some-tool",
        "some-tool@latest",
        "some-tool@next",
        "some-tool@^1.2.3",
        "some@tool@1.2.3",
    ],
)
def test_exact_pinned_package_spec_rejects_unpinned_moving_or_range_versions(
    package_spec: str,
) -> None:
    assert not _is_exact_pinned_package_spec(package_spec)


def test_npx_package_arg_includes_unscoped_packages() -> None:
    assert _first_npx_package_arg(["-y", "some-tool@1.2.3"]) == "some-tool@1.2.3"


@pytest.mark.parametrize("value", [True, "1", "true", "TRUE", " yes ", "on", 1])
def test_playwright_unrestricted_env_truthy_values_are_rejected(value: object) -> None:
    assert _playwright_unrestricted_env_is_truthy({"env": {PLAYWRIGHT_UNRESTRICTED_ENV: value}})


@pytest.mark.parametrize("value", [False, "0", "false", "off", "", 0, None])
def test_playwright_unrestricted_env_falsey_values_are_allowed(value: object) -> None:
    assert not _playwright_unrestricted_env_is_truthy({"env": {PLAYWRIGHT_UNRESTRICTED_ENV: value}})
