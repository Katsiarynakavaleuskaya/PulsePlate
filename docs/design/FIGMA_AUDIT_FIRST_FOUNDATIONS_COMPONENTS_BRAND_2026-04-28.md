# Figma Audit First: Foundations, Components, Brand (2026-04-28)

Status: `Reference-only design audit`
Figma file: `2JDwOByQIbcPgp93FDzHii`
Scope: `00_Foundation_Tokens` (`6:2`), `01_Components` (`6:3`), `02_Brand_Assets` (`6:4`)

## Coordinator packet

- Task packet: `artifacts/orchestration/task_packets/03c58042e193.json` (local artifact, not committed)
- `design_source`: `figma_design`
- `target_surface`: `design_system_readiness`
- `task_mode`: `verify`
- `figma_lane_tool`: `figma_native`
- Role order requested: `agent-coordinator`, `creative-designer`, `frontend-engineer`, `qa-engineer-agent -> bug-hunter`
- Mandatory post-open lane: `qa-engineer-agent -> bug-hunter` is required for this design runtime system web+iOS series to prevent orchestration drift.

## Repo source of truth

- Token authoring source: `/tokens`
- Web runtime token mirror: `frontend/src/styles/tokens.css`
- Web typed mirror: `frontend/src/styles/tokens.ts`
- iOS token mirrors: `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift`, `ios/PulsePlate/DesignSystem/DesignTokens.swift`
- Figma remains a design-intent/reference lane; no runtime asset or component promotion is authorized by this audit.

## Findings and fixes

### 00_Foundation_Tokens

- Fixed Figma token labels from board-local names such as `PP/Brand/navy` and `PP/Semantic/primary` to repo token names such as `--pp-navy` and `--color-primary`.
- Added a Figma coverage note for repo tokens that are part of the runtime SoT but were not visible on the board: `--pp-red`, `--color-warning`, `--color-info`.
- Post-fix QA: required token text coverage passed; no legacy `PP/Brand/*` or `PP/Semantic/*` labels remain.

### 01_Components

- Verified the existing Figma RuntimeSet nodes:
  - `PP/Shared/Button/RuntimeSet`
  - `PP/Shared/Input/RuntimeSet`
  - `PP/Shared/FormField/RuntimeSet`
- `FormField` remains Figma reference coverage only here; this audit does not promote or assert a dedicated repo component API.
- No Figma-only review surfaces were promoted into repo primitives.
- No web or iOS component code was changed in this pass.

### 02_Brand_Assets

- Verified current board counts:
  - `assetIdCount=30`
  - `riskTitleCount=30`
  - `riskCount=30`
  - `6 APPROVED-SEED`
  - `21 CANDIDATE`
  - `3 REFERENCE-ONLY`
  - `0 NEEDS-REWORK`
- Verified summary text: `Current batch: 30 assets · 6 APPROVED-SEED · 21 CANDIDATE · 3 REFERENCE-ONLY · 0 NEEDS-REWORK`.
- Reconciled stale repo evidence docs that still claimed one `NEEDS-REWORK` slot.

## Follow-up boundary

- Web implementation remains a separate follow-up aligned with the web shell / PR-4 line.
- iOS receives this audit map only; no SwiftUI mutation was made.
- Missing runtime component work should be tracked through backlog or a future packet, not silently created during this Figma audit pass.
