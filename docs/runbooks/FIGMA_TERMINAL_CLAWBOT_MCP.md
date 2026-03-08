# Figma Terminal Clawbot MCP Runbook

## Purpose

Define a deterministic setup for `terminal -> Figma MCP -> design iteration`,
with optional Clawbot orchestration for repetitive flows.

## Direct Answer: Is Figma MCP Already Connected On The Site?

No. Figma MCP is not "enabled on the website" as a global site switch.
It is connected per client runtime (Codex, Cursor, or other MCP client)
via MCP config + OAuth/auth session.

- If `whoami` works in your MCP client, runtime connection is active.
- Website access alone does not mean MCP tools are active in terminal.

## Current PulsePlate Baseline

- Workspace MCP config exists: `.cursor/mcp.json`
- Active remote endpoint: `https://mcp.figma.com/mcp`
- Verified tools in this runtime include:
  - `whoami`
  - `get_design_context`
  - `generate_diagram`
  - `get_screenshot` (for supported Design nodes)
  - `generate_figma_design` discovery flow

## Scope

### In

- Terminal-to-Figma Make context extraction.
- Design iteration loop with node targeting and variant comparison.
- Optional Clawbot role as orchestrator.
- Security-safe operational practices.

### Out

- Auto-deploying frontend to production from Figma.
- Storing secrets in repository files.
- Treating non-canonical tools as Source of Truth.

## Required Agents (Coordinator-First)

- `agent-coordinator`: routing, quality gates, synthesis.
- `architecture-specialist`: integration contracts and failure modes.
- `creative-designer`: variant and UX iteration strategy.
- `frontend-engineer`: implementation diffs and component mapping.
- `security-auditor`: token/redaction policy.
- `bug-hunter` or `qa`: deterministic verification and regressions.

## Integration Contracts

### Contract A: Runtime Capability

- `whoami` must succeed before any design-context call.
- `get_design_context(fileKey,nodeId)` is required for Make flow.
- `generate_figma_design` must be checked in discovery mode before live capture.
- `get_screenshot` is design-node dependent; do not block Make-only flows on it.

### Contract B: Input Format

- Figma Make URL:
  - `https://www.figma.com/make/<FILE_KEY>/<NAME>?...`
- Required parsing:
  - `fileKey = <FILE_KEY>`
  - default `nodeId = 0:1` when root-level context is intended

### Contract C: Output Artifacts

- One short execution log per session.
- One implementation action list linked to frontend paths.
- One risk and rollback note for UI changes.

## Full Implementation Plan

1. Verify runtime auth with `whoami`.
2. Parse Make URL and extract `fileKey`.
3. Pull context with `get_design_context(fileKey, nodeId)`.
4. Select target component set for iteration (hero, cards, CTA, etc.).
5. Create 2 variants (A/B) and record decision criteria.
6. Map variant to concrete frontend file edits.
7. Validate with deterministic tests/lint for touched files.
8. Log evidence and next actions.

## Optional Clawbot Bridge

Use Clawbot only as an orchestration layer, not as a source of truth.

- Clawbot responsibilities:
  - invoke MCP sequence in the correct order
  - enforce required fields (`fileKey`, `nodeId`)
  - store session summary in docs
- Clawbot must not:
  - write secrets to repo
  - bypass agent-coordinator routing
  - claim unavailable MCP tools are available

## Deterministic Session Template

1. Input:
   - Figma URL
   - `nodeId` (or `0:1`)
2. Calls:
   - `whoami`
   - `get_design_context`
   - `get_screenshot` when node type supports it
   - `generate_figma_design` discovery call when capture is needed
   - `generate_diagram` (optional for flow visualization)
3. Output:
   - target files list
   - minimal diff plan
   - verification checklist

## Verification Checklist

- MCP auth pass (`whoami` returns user).
- Design context pass (`get_design_context` returns resources).
- Expected runtime limits acknowledged (for Make screenshot constraints).
- No secrets committed in git diff.
- Frontend changes validated by tests/lint when code is modified.

## Security Notes

- Never commit OAuth tokens or API keys.
- Redact user email, file keys, and URLs with sensitive parameters in docs.
- Store only minimal operational evidence needed for audit.
- If token leakage is suspected:
  - rotate token immediately
  - invalidate active sessions
  - document incident and remediation in `docs/security/`

## Marketing And GTM Notes

- Fast code-to-design loop reduces time-to-iteration for paywall/onboarding.
- Use variant comparison in each cycle to improve conversion experiments.
- Keep assets and messaging synchronized with product tiers (FREE/PRO/VIP).

## Next Actions For This Workspace

1. Continue using the current Figma MCP runtime for Make context extraction.
2. Use `generate_figma_design` discovery first, then choose `existingFile`,
   `newFile`, or `clipboard` explicitly.
3. Keep this runbook aligned with `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`.
