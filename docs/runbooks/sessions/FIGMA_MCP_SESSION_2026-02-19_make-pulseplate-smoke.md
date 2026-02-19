# Figma MCP Session Evidence

## Session Metadata

- Date: 2026-02-19
- Operator: Codex agent + user session
- Branch: `docs/figma-mcp-session-smoke-evidence`
- Local source root: N/A (Make-source smoke focus)
- Target Figma source URL: `https://www.figma.com/make/<REDACTED_FILE_KEY>/PulsePlate_Web`
- Target node/frame: Make root node (`0:1`) and FigJam output canvas

## Preconditions Check

- `FIGMA_OAUTH_TOKEN` present: yes (authenticated `whoami` response)
- Token length check passed: not logged in this evidence file (security-safe policy)
- Figma MCP server visible in runtime: yes
- Figma tools callable: yes

## Execution

### Request 1 (identity/auth)

- Tool: `plugin-figma-figma.whoami`
- Result:
  - email: `l***@g***.com` (redacted)
  - handle: `K*** K***` (redacted)
  - plan: `Team (redacted)` (`pro`, seat `Full`)

### Request 2 (Make context extraction)

- Tool: `plugin-figma-figma.get_design_context`
- Arguments:
  - `fileKey=<REDACTED_FILE_KEY>`
  - `nodeId=0:1`
- Result:
  - returned Make source resources (including `src/app/App.tsx`)
  - confirmed live access to Make-backed code assets via MCP resource URIs

### Request 3 (diagram write smoke)

- Tool: `plugin-figma-figma.generate_diagram`
- Arguments:
  - `name="PulsePlate code-to-figma smoke"`
  - `mermaidSyntax` simple `code -> canvas -> iteration` flow
- Result:
  - diagram created successfully in FigJam
  - URL:
    [PulsePlate code-to-figma smoke](https://www.figma.com/online-whiteboard/create-diagram/580b99ea-ef7b-47b6-bf64-4f0283765f2c)

## Validation

- MCP auth status: pass
- Make context fetch status: pass
- Write operation to Figma (FigJam): pass
- Direct Make screenshot operation: fail (tool unsupported for Make in this runtime)

## Security Check

- Token value leaked: no
- Sensitive data in logs/comments: no

## Raw Evidence

- Call: `whoami`
  - Output line: user identity payload returned
  - Exit: success

- Call: `get_design_context(fileKey=<REDACTED_FILE_KEY>,nodeId=0:1)`
  - Output line:
    "This contains the resource links for all the source files in the
    Figma Make."
  - Exit: success

- Call: `generate_diagram(name,mermaidSyntax)`
  - Output line: returned FigJam diagram URL
  - Exit: success

## Known Limits / Next Action

- `generate_figma_design` (Claude Code to Figma Design push) is not currently exposed
  in this client tool list.
- For full "local web page -> Figma Design file" capture, next step is to run
  from a client/runtime where `generate_figma_design` is available and bind
  that output to this same evidence format.

## Follow-ups

- Next iteration variant: `design-file push smoke` (not only FigJam)
- Blockers: client capability mismatch for `generate_figma_design`
- Owner: current workspace operator
