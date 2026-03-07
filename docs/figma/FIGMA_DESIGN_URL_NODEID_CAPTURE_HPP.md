<!-- markdownlint-disable MD013 -->
# Figma Design URL + Node ID Capture Protocol (H+P+Pr)

**Date:** March 7, 2026
**Scope:** unblock Code Connect activation for Home + Plate + Progress CTA mappings

## 1) Purpose

Provide a deterministic way to complete the missing dependency:
`Design file URL + node IDs` for CTA mappings.

## 2) Constraint (why this protocol is required)

Current source is a **Figma Make** file (`<FIGMA_MAKE_FILE_ID>`).
MCP tools for Code Connect (`get_code_connect_suggestions`, `get_metadata`,
`get_code_connect_map`) are supported for **Figma Design** files only.

Therefore, this dependency cannot be auto-closed from Make context alone.

Additional blocker discovered on March 7, 2026:
`get_code_connect_suggestions(...)` currently fails for this workspace because
Code Connect requires a **Full or Dev seat on Organization or Enterprise** per
<https://help.figma.com/hc/en-us/articles/23920389749655-Code-Connect> and
<https://developers.figma.com/docs/figma-mcp-server/skill-code-connect-components/>.
Current MCP `whoami` reports only a `Full` seat on `pro`
(`docs/figma/orchestration/sessions/2026-03-07_code_connect_blocker_evidence/01_MCP_STATUS.md:3`).

## 3) Capture Procedure

### Step 1: obtain Design file URL

1. Open the canonical Make file:
   `https://www.figma.com/make/<FIGMA_MAKE_FILE_ID>/Untitled`
2. Open the corresponding **Figma Design** file used for component mapping.
3. Copy the Design URL in format:
   `https://www.figma.com/design/<fileKey>/<fileName>?node-id=<nodeId>`
4. Record it in:
   `docs/roadmap/BACKLOG_LEDGER.md`

RU: нужен именно `figma.com/design/...`, не `figma.com/make/...`.

### Step 2: capture node IDs for P0 CTA set

For each P0 CTA, select the exact design layer in Figma Design and copy selection link.

Required P0 CTA rows:

- `web.home.open_setup`
- `web.plate.premium_gate_cta`
- `web.progress.export_pdf`
- `ios.plate.issue_action_dynamic`

Expected node format: `123:456`.

### Step 3: write captured values to mapping registry

Update:
`docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md`

Set per-row:

- `Design File Key` = extracted `<fileKey>`
- `Node ID` = captured node ID
- `Status` = `validated` (after visual/component match check)

### Step 4: verify with MCP (activation-ready check)

After Step 3, run MCP checks:

1. `whoami` confirms a Code Connect-capable seat (Full or Dev seat in Organization/Enterprise).
2. `get_metadata(fileKey=<fileKey>, nodeId=<nodeId>)`
3. `get_code_connect_suggestions(fileKey=<fileKey>, nodeId=<nodeId>)`

If all three succeed for all P0 rows, blocker is cleared and activation may proceed via:
`docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md`

## 4) P0 Capture Table (fill-in contract)

| Button/CTA ID | Design URL | fileKey | nodeId | Captured by | Date | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `web.home.open_setup` | `https://www.figma.com/design/umcCk7TtO760DJ3N6M7mvh/PulsePlate-Design-System?node-id=1-72` | `umcCk7TtO760DJ3N6M7mvh` | `1:72` (stale) | OpenClaw (browser capture, invalidated by MCP re-check) | 2026-03-07 | stale |
| `web.plate.premium_gate_cta` | `https://www.figma.com/design/umcCk7TtO760DJ3N6M7mvh/PulsePlate-Design-System` | `umcCk7TtO760DJ3N6M7mvh` | TBD | OpenClaw (browser search) | 2026-02-19 | blocked_by_node_id_capture |
| `web.progress.export_pdf` | `https://www.figma.com/design/umcCk7TtO760DJ3N6M7mvh/PulsePlate-Design-System` | `umcCk7TtO760DJ3N6M7mvh` | TBD | OpenClaw (browser search) | 2026-02-19 | blocked_by_node_id_capture |
| `ios.plate.issue_action_dynamic` | `https://www.figma.com/design/umcCk7TtO760DJ3N6M7mvh/PulsePlate-Design-System` | `umcCk7TtO760DJ3N6M7mvh` | TBD | OpenClaw (browser search) | 2026-02-19 | blocked_by_node_id_capture |

**Capture note (2026-02-19):** in public browser session, `Find` with scope `All pages` returned `No results in this file` for `web.plate.premium_gate_cta`, `web.progress.export_pdf`, and `ios.plate.issue_action_dynamic`; only `web.home.open_setup` resolved to `node-id=1-72`.

**Refresh note (2026-03-07):**

- MCP `get_metadata(fileKey="umcCk7TtO760DJ3N6M7mvh", nodeId="1:72")` now returns `The node ID provided was invalid`, so the prior `web.home.open_setup` capture is no longer activation-safe (`docs/figma/orchestration/sessions/2026-03-07_code_connect_blocker_evidence/01_MCP_STATUS.md:6`).
- MCP `get_metadata(fileKey="umcCk7TtO760DJ3N6M7mvh", nodeId="96:33")` succeeds, which confirms the Design file key is current but the accessible MCP root is a spec/index frame, not the old `1:72` CTA node (`docs/figma/orchestration/sessions/2026-03-07_code_connect_blocker_evidence/01_MCP_STATUS.md:8`).
- MCP `get_code_connect_suggestions(...)` is blocked at plan level until a Full
  or Dev seat in an Organization or Enterprise plan is available
  (`docs/figma/orchestration/sessions/2026-03-07_code_connect_blocker_evidence/01_MCP_STATUS.md:4`, `docs/figma/orchestration/sessions/2026-03-07_code_connect_blocker_evidence/01_MCP_STATUS.md:6`).

**Clear note:** Design URL exists, but the P0 set still lacks four current activation-safe node IDs and Code Connect remains blocked by seat/plan (`docs/figma/orchestration/sessions/2026-03-07_code_connect_blocker_evidence/01_MCP_STATUS.md:6`, `docs/figma/orchestration/sessions/2026-03-07_code_connect_blocker_evidence/01_MCP_STATUS.md:10`).

## Next action for designer

Re-capture/add the following node names in Design file `umcCk7TtO760DJ3N6M7mvh` and provide selection URLs with current node IDs:

- `web.home.open_setup`
- `web.plate.premium_gate_cta`
- `web.progress.export_pdf`
- `ios.plate.issue_action_dynamic`

## 5) Done Criteria

### Capture complete

Capture dependency is considered closed when:

1. Design URL is recorded in repo docs.
2. All four P0 rows have current, non-stale `fileKey` and `nodeId`.
3. Mapping registry status is updated out of `blocked_by_node_id_capture` /
   `missing_node_id` / `stale`.

### Activation unblocked

Code Connect activation is unblocked only when, in addition:

1. A Code Connect-capable Figma seat is available (`whoami` +
   `get_code_connect_suggestions` no longer plan-blocked).
2. MCP verification succeeds for all four rows.

## 6) Canonical links

- `docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md`
- `docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md`
- `docs/figma/FIGMA_MAKE_SYNC_AUDIT_HPP.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
<!-- markdownlint-enable MD013 -->
