import json
from pathlib import Path


MCP_EXAMPLES = (
    Path(".cursor/mcp.json.example"),
    Path(".kimi/mcp.json.example"),
)


def test_mcp_examples_do_not_enable_unrestricted_playwright_file_access() -> None:
    for path in MCP_EXAMPLES:
        data = json.loads(path.read_text())
        playwright_args = data["mcpServers"]["playwright"]["args"]

        assert "--allow-unrestricted-file-access" not in playwright_args, path


def test_mcp_examples_pin_npx_mcp_packages() -> None:
    for path in MCP_EXAMPLES:
        data = json.loads(path.read_text())
        for server_name, server_config in data["mcpServers"].items():
            if server_config.get("command") != "npx":
                continue

            args = server_config["args"]
            package_args = [
                arg for arg in args if isinstance(arg, str) and arg.startswith("@")
            ]
            assert package_args, f"{path}:{server_name} has no scoped package arg"
            assert all(not arg.endswith("@latest") for arg in package_args), (
                f"{path}:{server_name} uses an unpinned @latest package"
            )
            assert all(arg.count("@") >= 2 for arg in package_args), (
                f"{path}:{server_name} package is not version-pinned"
            )
