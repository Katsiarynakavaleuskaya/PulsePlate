# Figma MCP Runtime Matrix

<!-- markdownlint-disable MD013 -->

This runbook clarifies which Figma MCP capabilities are available by runtime.
It is the canonical "why it works here and not there" reference.

## Scope

### IN

- Runtime capability matrix for Figma MCP tools.
- Exact path to enable `generate_figma_design`.
- Fast verification checklist.

### OUT

- Product design decisions.
- App runtime changes.
- Figma org governance details.

## Capability Matrix

| Runtime | Remote MCP auth (`whoami`) | Make context (`get_design_context`) | Diagram write (`generate_diagram`) | Design push (`generate_figma_design`) |
| --- | --- | --- | --- | --- |
| Cursor/Codex (this workspace MCP bridge) | Yes | Yes | Yes | No (tool not exposed) |
| Claude Code + remote Figma MCP | Yes | Yes | Yes | Yes (supported path) |

## Hard Rule

If the active tool list does not include `generate_figma_design`, direct
`code -> Figma Design` push is not possible in that runtime.

Do not treat this as a bug in project code. It is a client capability gap.

## Canonical Enablement Path (`generate_figma_design`)

1. Use Claude Code runtime.
2. Configure remote Figma MCP endpoint:
   - `https://mcp.figma.com/mcp`
3. Run OAuth flow in Claude Code (`/mcp` -> `figma` -> `Authenticate`).
4. Start local app server for the target page.
5. Prompt with explicit target:
   - `Start a local server for my app and capture the UI in <Figma Design file URL>.`
6. In capture toolbar, use:
   - `Entire screen` for full-page state.
   - `Select element` for focused state captures.
7. Save generated output and record evidence in session runbook.

## Quick Verification

- `whoami` returns identity payload.
- `get_design_context(fileKey,nodeId)` returns context/resources.
- `generate_figma_design` appears in tool list.
- One capture to Figma Design file succeeds.

## Security Notes

- Never store OAuth token in repository files.
- Keep only minimal evidence in docs (redacted identifiers, no raw secrets).
- Prefer canonical Figma URLs without tracking query params in long-lived docs.
