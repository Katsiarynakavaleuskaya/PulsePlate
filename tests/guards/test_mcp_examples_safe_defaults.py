import json
import re
import shlex
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTEXT7_PACKAGE = "@upstash/context7-mcp"
CONTEXT7_PINNED_PACKAGE = "@upstash/context7-mcp@3.1.0"
EXACT_NUMERIC_VERSION = re.compile(r"\d+\.\d+\.\d+\Z")
PYTHON_PACKAGE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\Z")
CONTEXT7_PACKAGE_TOKEN = re.compile(r"@upstash/context7-mcp(?:@[A-Za-z0-9_.~^<>=!*+-]+)?")
PLAYWRIGHT_UNRESTRICTED_ENV = "PLAYWRIGHT_MCP_ALLOW_UNRESTRICTED_FILE_ACCESS"
TRUTHY_ENV_VALUES = {"1", "true", "yes", "on"}
CURSOR_ENV_READ_COMMANDS = {"awk", "cat", "grep", "head", "less", "more", "rg", "sed", "tail"}
CURSOR_ENV_INPUT_REDIRECT_OPERATORS = {"<", "0<"}
CURSOR_ENV_OUTPUT_REDIRECT_OPERATORS = {">", ">>", "2>", "2>>", "&>", ">&", "1>", "1>>"}
NPM_INSTALL_COMMANDS = {
    "add",
    "i",
    "in",
    "ins",
    "inst",
    "insta",
    "instal",
    "install",
    "isnt",
    "isnta",
    "isntal",
    "isntall",
}

MCP_EXAMPLE_PATHS = (
    REPO_ROOT / "mcp-config.json",
    REPO_ROOT / ".cursor/mcp.json.example",
    REPO_ROOT / ".kimi/mcp.json.example",
)
OPENCODE_MCP_EXAMPLE_PATHS = (REPO_ROOT / "opencode.json",)
GOVERNED_MCP_DOC_PATHS = (REPO_ROOT / "docs/runbooks/OPENAI_EXTERNAL_DOCS_FRESHNESS_PILOT.md",)
GOVERNED_MCP_SCRIPT_PATHS = (REPO_ROOT / "mcp-setup.sh",)


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


def _is_exact_pinned_python_package_spec(spec: str) -> bool:
    spec_parts = spec.rsplit("==", 1)
    if len(spec_parts) != 2:
        return False

    package_name, version = spec_parts
    if not PYTHON_PACKAGE_NAME.fullmatch(package_name):
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


def _npm_install_package_args(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return []
    try:
        parts = shlex.split(stripped)
    except ValueError:
        return []
    if len(parts) < 3 or parts[0] != "npm" or parts[1] not in NPM_INSTALL_COMMANDS:
        return []

    packages: list[str] = []
    skip_next = False
    options_with_value = {
        "--cache",
        "--prefix",
        "--registry",
        "--tag",
        "--userconfig",
    }
    for arg in parts[2:]:
        if skip_next:
            skip_next = False
            continue
        if arg == "--":
            continue
        if arg.startswith("-"):
            if arg in options_with_value:
                skip_next = True
            continue
        packages.append(arg)
    return packages


def _context7_package_tokens(line: str) -> list[str]:
    return CONTEXT7_PACKAGE_TOKEN.findall(line)


def _is_cursor_env_path(token: str) -> bool:
    normalized = token.strip("\"'")
    return normalized in {
        "~/.cursor/.env",
        "$HOME/.cursor/.env",
        "${HOME}/.cursor/.env",
    }


def _script_line_reads_cursor_env(line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return False
    try:
        parts = shlex.split(stripped, comments=True)
    except ValueError:
        return False
    if not parts:
        return False

    command = Path(parts[0]).name
    if command not in CURSOR_ENV_READ_COMMANDS:
        return False

    skip_next = False
    input_redirect = False
    for arg in parts[1:]:
        if skip_next:
            if input_redirect and _is_cursor_env_path(arg):
                return True
            skip_next = False
            input_redirect = False
            continue
        if arg in CURSOR_ENV_INPUT_REDIRECT_OPERATORS:
            skip_next = True
            input_redirect = True
            continue
        if arg in CURSOR_ENV_OUTPUT_REDIRECT_OPERATORS:
            skip_next = True
            continue
        if arg.startswith("<") and _is_cursor_env_path(arg[1:]):
            return True
        if _is_cursor_env_path(arg):
            return True
    return False


def _opencode_npx_command_args(path: Path) -> list[tuple[str, list[str]]]:
    data = _load_json(path)
    mcp_servers = data.get("mcp", {})
    if not isinstance(mcp_servers, dict):
        return []

    npx_servers: list[tuple[str, list[str]]] = []
    for server_name, server_config in mcp_servers.items():
        if not isinstance(server_config, dict):
            continue

        command = server_config.get("command")
        if isinstance(command, list) and command[:1] == ["npx"]:
            npx_servers.append((server_name, command[1:]))
    return npx_servers


def test_mcp_examples_do_not_enable_unrestricted_playwright_file_access() -> None:
    playwright_examples = 0
    for path in MCP_EXAMPLE_PATHS:
        data = _load_json(path)
        playwright_config = data["mcpServers"].get("playwright")
        if playwright_config is None:
            continue

        playwright_examples += 1
        playwright_args = playwright_config["args"]
        assert "--allow-unrestricted-file-access" not in playwright_args, path
        assert not _playwright_unrestricted_env_is_truthy(playwright_config), path
    assert playwright_examples > 0, "no governed Playwright MCP examples found"


def test_mcp_examples_pin_mcp_packages() -> None:
    matches = 0
    for path in MCP_EXAMPLE_PATHS:
        data = _load_json(path)
        for server_name, server_config in data["mcpServers"].items():
            command = server_config.get("command")
            if command == "npx":
                matches += 1
                package_arg = _first_npx_package_arg(server_config.get("args", []))
                assert package_arg, f"{path}:{server_name} has no npx package arg"
                assert _is_exact_pinned_package_spec(
                    package_arg
                ), f"{path}:{server_name} package is not exactly pinned: {package_arg}"
                continue
            if command != "uvx":
                continue

            matches += 1
            package_arg = _first_npx_package_arg(server_config.get("args", []))
            assert package_arg, f"{path}:{server_name} has no uvx package arg"
            assert _is_exact_pinned_python_package_spec(
                package_arg
            ), f"{path}:{server_name} Python package is not exactly pinned: {package_arg}"
    for path in OPENCODE_MCP_EXAMPLE_PATHS:
        for server_name, command_args in _opencode_npx_command_args(path):
            matches += 1
            package_arg = _first_npx_package_arg(command_args)
            assert package_arg, f"{path}:{server_name} has no npx package arg"
            assert _is_exact_pinned_package_spec(
                package_arg
            ), f"{path}:{server_name} package is not exactly pinned: {package_arg}"
    assert matches > 0, "no governed npx/uvx MCP server examples found"


def test_documented_context7_mcp_examples_pin_local_npx_package() -> None:
    for path in GOVERNED_MCP_DOC_PATHS:
        matches = 0
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for package_token in _context7_package_tokens(line):
                matches += 1
                assert package_token == CONTEXT7_PINNED_PACKAGE, (
                    f"{path}:{line_number}: Context7 package is not exactly pinned: "
                    f"{package_token}"
                )
        assert matches > 0, f"{path}: no governed Context7 npx package examples found"


def test_mcp_setup_script_does_not_install_unpinned_npm_packages() -> None:
    for path in GOVERNED_MCP_SCRIPT_PATHS:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for package_arg in _npm_install_package_args(line):
                assert _is_exact_pinned_package_spec(
                    package_arg
                ), f"{path}:{line_number}: package is not exactly pinned: {package_arg}"


def test_mcp_setup_script_does_not_read_existing_env_file() -> None:
    for path in GOVERNED_MCP_SCRIPT_PATHS:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            assert not _script_line_reads_cursor_env(line), f"{path}:{line_number}: {line}"


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


@pytest.mark.parametrize(
    "package_spec",
    [
        "mcp-server-openai==0.1.4",
        "some_tool==1.2.3",
        "some-tool==1.2.3",
    ],
)
def test_exact_pinned_python_package_spec_accepts_numeric_versions(package_spec: str) -> None:
    assert _is_exact_pinned_python_package_spec(package_spec)


@pytest.mark.parametrize(
    "package_spec",
    [
        "mcp-server-openai",
        "mcp-server-openai==",
        "mcp-server-openai==latest",
        "mcp-server-openai>=0.1.4",
        "mcp-server-openai~=0.1.4",
        "mcp-server-openai^0.1.4",
        "-mcp-server-openai==0.1.4",
    ],
)
def test_exact_pinned_python_package_spec_rejects_unpinned_tags_or_ranges(
    package_spec: str,
) -> None:
    assert not _is_exact_pinned_python_package_spec(package_spec)


def test_npx_package_arg_includes_unscoped_packages() -> None:
    assert _first_npx_package_arg(["-y", "some-tool@1.2.3"]) == "some-tool@1.2.3"


def test_npm_install_package_args_include_unscoped_packages() -> None:
    assert _npm_install_package_args("npm install -g some-tool@1.2.3") == ["some-tool@1.2.3"]


@pytest.mark.parametrize("install_command", ["install", "i", "add", "in", "ins", "inst"])
def test_npm_install_package_args_include_install_aliases(install_command: str) -> None:
    assert _npm_install_package_args(f"npm {install_command} -g some-tool@1.2.3") == [
        "some-tool@1.2.3"
    ]


def test_context7_package_tokens_reject_mixed_pinned_and_unpinned_mentions() -> None:
    line = 'args = ["-y", "@upstash/context7-mcp@3.1.0", "@upstash/context7-mcp"]'
    package_tokens = _context7_package_tokens(line)
    assert package_tokens == ["@upstash/context7-mcp@3.1.0", "@upstash/context7-mcp"]
    assert any(package_token != CONTEXT7_PINNED_PACKAGE for package_token in package_tokens)


@pytest.mark.parametrize(
    "line",
    [
        "cat ~/.cursor/.env",
        'cat "$HOME/.cursor/.env"',
        "sed -n '1,5p' ~/.cursor/.env",
        "grep OPENAI ~/.cursor/.env",
        "tail -n 5 ${HOME}/.cursor/.env",
        "cat < ~/.cursor/.env",
        "sed -n '1,5p' < ~/.cursor/.env",
        "cat <~/.cursor/.env",
    ],
)
def test_cursor_env_reader_detection_rejects_equivalent_dump_commands(line: str) -> None:
    assert _script_line_reads_cursor_env(line)


@pytest.mark.parametrize(
    "line",
    [
        "cat > ~/.cursor/.env << EOF",
        "cp ~/.cursor/.env ~/.cursor/.env.backup.$(date +%Y%m%d_%H%M%S)",
        "chmod 600 ~/.cursor/.env",
    ],
)
def test_cursor_env_reader_detection_allows_writes_and_backups(line: str) -> None:
    assert not _script_line_reads_cursor_env(line)


@pytest.mark.parametrize("value", [True, "1", "true", "TRUE", " yes ", "on", 1])
def test_playwright_unrestricted_env_truthy_values_are_rejected(value: object) -> None:
    assert _playwright_unrestricted_env_is_truthy({"env": {PLAYWRIGHT_UNRESTRICTED_ENV: value}})


@pytest.mark.parametrize("value", [False, "0", "false", "off", "", 0, None])
def test_playwright_unrestricted_env_falsey_values_are_allowed(value: object) -> None:
    assert not _playwright_unrestricted_env_is_truthy({"env": {PLAYWRIGHT_UNRESTRICTED_ENV: value}})
