# MCP Code Connect Blocker Evidence (2026-03-07)

## Session Summary

- `whoami` result: authenticated workspace reports `plan=pro`, `seat=Full`.
- `get_metadata(fileKey="umcCk7TtO760DJ3N6M7mvh", nodeId="1:72")` result:
  `The node ID provided was invalid`.
- `get_metadata(fileKey="umcCk7TtO760DJ3N6M7mvh", nodeId="96:33")` result:
  success; the accessible MCP root is a spec/index frame.
- `get_code_connect_suggestions(...)` result: blocked by plan/seat for current
  workspace.

## Canonical Follow-up Links

- `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md`
- `docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
