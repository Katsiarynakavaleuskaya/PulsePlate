<!-- markdownlint-disable MD013 -->
# Figma Design URL + Node ID Capture Protocol (H+P+Pr)

**Date:** February 19, 2026
**Scope:** unblock Code Connect activation for Home + Plate + Progress CTA mappings

## 1) Purpose

Provide a deterministic way to complete the missing dependency:
`Design file URL + node IDs` for CTA mappings.

## 2) Constraint (why this protocol is required)

Current source is a **Figma Make** file (`<FIGMA_MAKE_FILE_ID>`).
MCP tools for Code Connect (`get_code_connect_suggestions`, `get_metadata`,
`get_code_connect_map`) are supported for **Figma Design** files only.

Therefore, this dependency cannot be auto-closed from Make context alone.

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

1. `get_metadata(fileKey=<fileKey>, nodeId=<nodeId>)`
2. `get_code_connect_suggestions(fileKey=<fileKey>, nodeId=<nodeId>)`

If both succeed for all P0 rows, blocker is cleared and activation may proceed via:
`docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md`

## 4) P0 Capture Table (fill-in contract)

| Button/CTA ID | Design URL | fileKey | nodeId | Captured by | Date | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `web.home.open_setup` | `https://www.figma.com/design/umcCk7TtO760DJ3N6M7mvh/PulsePlate-Design-System?node-id=1-72` | `umcCk7TtO760DJ3N6M7mvh` | `1:72` | OpenClaw (browser capture) | 2026-02-19 | validated |
| `web.plate.premium_gate_cta` | `https://www.figma.com/design/umcCk7TtO760DJ3N6M7mvh/PulsePlate-Design-System` | `umcCk7TtO760DJ3N6M7mvh` | TBD | OpenClaw (browser search) | 2026-02-19 | blocked_by_node_id_capture |
| `web.progress.export_pdf` | `https://www.figma.com/design/umcCk7TtO760DJ3N6M7mvh/PulsePlate-Design-System` | `umcCk7TtO760DJ3N6M7mvh` | TBD | OpenClaw (browser search) | 2026-02-19 | blocked_by_node_id_capture |
| `ios.plate.issue_action_dynamic` | `https://www.figma.com/design/umcCk7TtO760DJ3N6M7mvh/PulsePlate-Design-System` | `umcCk7TtO760DJ3N6M7mvh` | TBD | OpenClaw (browser search) | 2026-02-19 | blocked_by_node_id_capture |

**Capture note (2026-02-19):** in public browser session, `Find` with scope `All pages` returned `No results in this file` for `web.plate.premium_gate_cta`, `web.progress.export_pdf`, and `ios.plate.issue_action_dynamic`; only `web.home.open_setup` resolved to `node-id=1-72`.

**Clear note:** Design URL exists, node IDs missing in design file.

## Next action for designer

Add/restore the following node names in Design file `umcCk7TtO760DJ3N6M7mvh` and provide selection URLs with node IDs:

- `web.plate.premium_gate_cta`
- `web.progress.export_pdf`
- `ios.plate.issue_action_dynamic`

## 5) Done Criteria

Dependency is considered closed only when:

1. Design URL is recorded in repo docs.
2. All four P0 rows have non-`TBD` `fileKey` and `nodeId`.
3. MCP verification succeeds for all four rows.
4. Mapping registry status is updated out of `blocked_by_node_id_capture` / `missing_node_id`.

## 6) Canonical links

- `docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md`
- `docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md`
- `docs/figma/FIGMA_MAKE_SYNC_AUDIT_HPP.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
<!-- markdownlint-enable MD013 -->
