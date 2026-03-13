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

As of `2026-03-12`, the active Codex runtime for this repo is the primary
agent runtime and Figma MCP is live in-session (`docs/runbooks/sessions/FIGMA_MCP_SESSION_2026-03-11_ios-prototype-check.md:23-63`,
`docs/runbooks/sessions/FIGMA_MCP_SESSION_2026-03-11_ios-prototype-check.md:168-243`):

- `whoami` succeeds (`docs/runbooks/sessions/FIGMA_MCP_SESSION_2026-03-11_ios-prototype-check.md:23-29`)
- `get_design_context` stays on the active-session verification checklist and
  must be re-verified before use in a new run
- `get_screenshot` is callable for supported Figma Design nodes (`docs/runbooks/sessions/FIGMA_MCP_SESSION_2026-03-11_ios-prototype-check.md:80-88`,
  `docs/runbooks/sessions/FIGMA_MCP_SESSION_2026-03-11_ios-prototype-check.md:231-241`)
- `generate_diagram` stays on the active-session verification checklist and
  must be re-verified before use in a new run
- `generate_figma_design` is available in discovery mode in this Codex runtime
  (`docs/runbooks/sessions/FIGMA_MCP_SESSION_2026-03-11_ios-prototype-check.md:53-63`)
- `generate_figma_design` discovery returns `newFile`, `existingFile`, and
  `clipboard` (`docs/runbooks/sessions/FIGMA_MCP_SESSION_2026-03-11_ios-prototype-check.md:53-63`)
- `generate_figma_design` completed a full local HTML -> new Figma file flow for
  `ios prototype v2` (`AhyS6u4dZXMRHVUDO3Cfn6`)
  (`docs/runbooks/sessions/FIGMA_MCP_SESSION_2026-03-11_ios-prototype-check.md:168-229`)
- `existingFile` completed follow-up screen imports into the same file
  (`docs/runbooks/sessions/FIGMA_MCP_SESSION_2026-03-11_ios-prototype-check.md:243-301`)
- Code Connect checks remain separately blocked on the current workspace seat
  even when core MCP auth succeeds
  (`docs/runbooks/sessions/FIGMA_MCP_SESSION_2026-03-11_ios-prototype-check.md:42-51`)

Project rule: treat this runtime baseline as authoritative unless a fresh
session check proves otherwise.

## Capability Matrix

| Runtime | Remote MCP auth (`whoami`) | Design context (`get_design_context`) | Screenshot (`get_screenshot`) | Diagram write (`generate_diagram`) | Design push (`generate_figma_design`) |
| --- | --- | --- | --- | --- | --- |
| Codex / GPT-5.4 Pro (primary PulsePlate runtime) | Yes | Verify in active session | Yes for supported Design nodes | Verify in active session | Yes, verified for local HTML capture |
| Any other MCP client | Verify per active session | Verify per active session | Verify per active session | Verify per active session | Verify per active session |

## Hard Rules

1. PulsePlate agents should assume `Codex / GPT-5.4 Pro` is the canonical
   runtime for Figma automation in this repo.
2. `generate_figma_design` must be treated as available only after discovery
   succeeds in the active session.
3. `Figma Make` remains ideation/reconciliation only. Canonical node-level
   mapping and Code Connect still require `Figma Design`.
4. Raw captured prototype files are `reference_only` until they are normalized
   into stable screen/frame boundaries with repo-tracked `fileKey` + `nodeId`
   evidence (`docs/architecture/ADR_PENPOT_STORYBOOK_BRIDGE_FALLBACK_SEAM_2026-03-07.md:41-58`,
   `docs/roadmap/BACKLOG_LEDGER.md:1091-1117`).
5. A normalized prototype file may be promoted to implementation reference once
   it has:
   - one stable frame per screen
   - recorded `fileKey` + `nodeId` map
   - visual QA evidence from `get_screenshot`
   (`docs/roadmap/BACKLOG_LEDGER.md:1111-1117`,
   `docs/runbooks/sessions/FIGMA_MCP_SESSION_2026-03-11_ios-prototype-check.md:243-301`)
6. If a future session loses `generate_figma_design`, downgrade gracefully to
   `context + screenshot + mapping` flow and record the capability gap in the
   session evidence.

## Canonical Codex Enablement Path (`generate_figma_design`)

1. Follow [`FIGMA_MCP_CODEX.md`](FIGMA_MCP_CODEX.md) and configure
   `~/.codex/config.toml` to point at `https://mcp.figma.com/mcp`.
2. Ensure `FIGMA_OAUTH_TOKEN` is present in the environment that launches Codex.
3. Confirm runtime auth with `whoami`.
4. Call `generate_figma_design` without `outputMode` first to discover:
   - `newFile`
   - `existingFile`
   - `clipboard`
5. Use `existingFile` when adding captures to canonical PulsePlate design files.
6. Use `newFile` for standalone exploratory captures or when reconciling a raw
   prototype into a fresh implementation-safe file.
7. If discovery returns a raw prototype file such as `ios prototype`, treat it
   as intake/reference until duplicated scroll captures are split into one
   stable frame per screen (`docs/architecture/ADR_PENPOT_STORYBOOK_BRIDGE_FALLBACK_SEAM_2026-03-07.md:41-58`,
   `docs/roadmap/BACKLOG_LEDGER.md:1091-1117`).
8. Record capture choice and returned identifiers in the evidence template.
9. When HTML capture auto-generates non-canonical frame names, record the
   canonical screen ID -> `nodeId` mapping in repo docs instead of treating the
   file as unnamed (`docs/runbooks/sessions/FIGMA_MCP_SESSION_2026-03-11_ios-prototype-check.md:243-301`,
   `docs/roadmap/BACKLOG_LEDGER.md:1111-1117`).

## Quick Verification

- Verify `whoami` returns the identity payload.
- Confirm `get_design_context(fileKey,nodeId)` returns the context/resources.
- Ensure `generate_figma_design` returns capture options in discovery mode.
- Code Connect capability is checked separately from core MCP auth.
- One Design or clipboard capture path is documented for the active session.

## Security Notes

- Never store OAuth tokens in repository files.
- Keep only minimal evidence in docs and redact file keys if the doc is meant
  for broad sharing.
- Prefer canonical Figma URLs without tracking query params in long-lived docs.
