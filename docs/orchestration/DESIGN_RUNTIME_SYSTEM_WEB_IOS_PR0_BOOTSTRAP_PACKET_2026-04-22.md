# Design Runtime System Web+iOS PR-0 Bootstrap Packet

**Version:** 2026-04-22 (`America/New_York`)
**Branch:** `codex/design-runtime-system-v1-packet`
**PR:** `#1497`
**Title:** `docs(design): add coordinator-first design runtime system web-ios runbook`

## Summary

This packet is the branch-scoped field contract for the bootstrap slice of the
design runtime system web+iOS epic line.

The repo already carries the governed design-runtime, design-bridge, and
post-bridge UI baselines on `main`. This PR does not reopen those lanes. It
adds the governing runbook, the branch-scoped packet, and one explicit backlog
anchor so the later executable slices run through one coordinator-owned
contract.

Evidence:
- `docs/design/DESIGN_AGENT_RUNTIME_PR_CHAIN.md`
- `docs/orchestration/DESIGN_BRIDGE_OPERATIONALIZATION_PACKET_2026-04-11.md`
- `docs/orchestration/UI_EPIC_PR_SERIES_RUNBOOK.md`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-design-runtime-system-web-ios-epic`

## Scope

### IN
- add the design runtime system web+iOS PR-series runbook
- add this branch-scoped bootstrap packet
- add one explicit backlog anchor for the new series
- lock PR order, role order, source precedence, review surfaces, validation,
  merge path, and cleanup path
- keep the slice minimal and process-level for `PR-0` only

### OUT
- runtime, API, OpenAPI, or client behavior changes
- reopening merged design-runtime or bridge-closeout work
- reopening or overtaking UI-epic-owned product surfaces without an explicit
  handoff/supersede record
- Figma writes, pushes, or mutation authority
- Tokens Studio export automation
- `figma-manifest` schema unification
- backend/UI rail widening
- implementation work for `PR-1` through `PR-8`

## Files

- `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR_SERIES_RUNBOOK.md`
- `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR0_BOOTSTRAP_PACKET_2026-04-22.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `docs/review/PR_1497_FIXED_MAPPING.md`

## Role Order

1. `agent-coordinator`
2. `creative-designer`
3. `frontend-engineer`
4. advisory `cursor-specialist-agent`
5. reviewer `architecture-specialist`
6. post-open mandatory `qa-engineer-agent -> bug-hunter`

This order is fixed for the lane unless a later packet explicitly updates it.
Future iOS-bearing slices may attach `build-ios-apps:*` skills, but those
skills do not replace the canonical role-agent order.

## Downstream Dependency

`PR-0` records this series as downstream of the existing UI epic line. Any
future slice that claims overlapping `Home`, `Plate`, `Progress`, `Weekly
Plan`, `Profile`, or `Paywall` ownership must first record an explicit handoff,
supersede decision, or narrower carve-out in its active packet and ledger
state.

## Source Precedence

This series freezes the full design source-precedence ladder as:

1. `repo/docs/tests/code`
2. code-native design runtime
3. `Figma Design + Code Connect`
4. `/tokens`
5. Storybook review-only lane
6. external/reference sources in `read_only`

Hard rules:
- `/tokens` stays the authoring source.
- `frontend/src/styles/tokens.css` stays the web runtime SoT.
- `frontend/src/styles/tokens.ts` is a helper mirror only.
- iOS token mirrors remain derived outputs.
- `docs/design/figma-manifest.json` stays bootstrap metadata in `PR-0`.

## Evidence Rules

- `PR-0` is docs-only, so evidence is repo-artifact validation plus current-head
  PR governance checks only.
- Later web slices are Storybook-first review only.
- Later iOS slices are simulator-first.
- Product routes, screenshots, and Figma frames are supporting evidence only;
  they do not replace repo-native review surfaces.
- Any future Figma-backed slice stays `read_only` until its active packet
  records `design_source`, `source_url`, `file_key_or_workspace`,
  `node_id_or_frame_id`, `target_surface`, `task_mode`, and the required
  `code_native_design_brief_path`.

## Validation

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `pre-commit run --all-files`
- docs-only file-scope check from `docs/policy/DOCS_ONLY_PR_POLICY.md`
- `make verify` remains required before merge-ready claims on the latest head,
  even though this slice is docs-only

## DoD

- the runbook exists and is consistent with merged design/runtime/bridge
  baseline state
- `PR-0` has a real branch-scoped packet file, not only a runbook
- the backlog anchor exists and explicitly points to this series rather than a
  generic placeholder
- source precedence, role order, PR order, and cleanup path are all frozen in
  repo-tracked docs
- downstream ownership with the existing UI epic is explicit, so later packets
  cannot silently reopen overlapping product surfaces
- the runbook and packet explicitly keep Storybook review-only, Figma
  fail-closed, token authoring repo-first, and backend/UI rail widening out of
  scope
- the canonical review artifact can be added without revising packet scope
- no runtime or client behavior changes are introduced
