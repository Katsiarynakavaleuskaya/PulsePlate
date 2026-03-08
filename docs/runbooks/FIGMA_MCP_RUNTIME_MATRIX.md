# Figma MCP Runtime Matrix

<!-- markdownlint-disable MD013 -->

This runbook clarifies which Figma MCP capabilities are available in the
current PulsePlate Codex runtime and what the project should assume when
agents perform `code/web -> Figma` work.

## Scope

### IN

- Runtime capability matrix for Figma MCP tools.
- Current Codex runtime baseline for PulsePlate.
- Fast verification checklist for `generate_figma_design`.

### OUT

- Product design decisions.
- App runtime changes.
- Non-Figma tool governance.

## Current Baseline

As of `2026-03-08`, the active Codex runtime for this repo is the primary
agent runtime and Figma MCP is live in-session:

- `whoami` succeeds
- `get_design_context` is callable
- `get_screenshot` is callable for supported Figma Design nodes
- `generate_diagram` is callable
- `generate_figma_design` is available in discovery mode in this Codex runtime

Project rule: treat this runtime baseline as authoritative unless a fresh
session check proves otherwise.

## Capability Matrix

| Runtime | Remote MCP auth (`whoami`) | Design context (`get_design_context`) | Screenshot (`get_screenshot`) | Diagram write (`generate_diagram`) | Design push (`generate_figma_design`) |
| --- | --- | --- | --- | --- | --- |
| Codex / GPT-5.4 Pro (primary PulsePlate runtime) | Yes | Yes | Yes for supported Design nodes | Yes | Discovery-gated |
| Any other MCP client | Verify per active session | Verify per active session | Verify per active session | Verify per active session | Verify per active session |

## Hard Rules

1. PulsePlate agents should assume `Codex / GPT-5.4 Pro` is the canonical
   runtime for Figma automation in this repo.
2. `generate_figma_design` must be treated as available only after discovery
   succeeds in the active session.
3. `Figma Make` remains ideation/reconciliation only. Canonical node-level
   mapping and Code Connect still require `Figma Design`.
4. If a future session loses `generate_figma_design`, downgrade gracefully to
   `context + screenshot + mapping` flow and record the capability gap in the
   session evidence.

## Canonical Codex Enablement Path (`generate_figma_design`)

1. Keep `.cursor/mcp.json` pointed at `https://mcp.figma.com/mcp`.
2. Ensure `FIGMA_OAUTH_TOKEN` is present in the environment that launches Codex.
3. Confirm runtime auth with `whoami`.
4. Call `generate_figma_design` without `outputMode` first to discover:
   - `newFile`
   - `existingFile`
   - `clipboard`
5. Use `existingFile` when adding captures to canonical PulsePlate design files.
6. Use `newFile` only for standalone exploratory captures.
7. Record capture choice and returned identifiers in the evidence template.

## Quick Verification

- `whoami` returns identity payload.
- `get_design_context(fileKey,nodeId)` returns context/resources.
- `generate_figma_design` returns capture options in discovery mode.
- One Design or clipboard capture path is documented for the active session.

## Security Notes

- Never store OAuth tokens in repository files.
- Keep only minimal evidence in docs and redact file keys if the doc is meant
  for broad sharing.
- Prefer canonical Figma URLs without tracking query params in long-lived docs.
