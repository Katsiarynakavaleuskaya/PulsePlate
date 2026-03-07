# Penpot + Storybook Bridge

**Date:** March 7, 2026
**Scope:** canonical minimal design handoff path for web review and low-cost design collaboration

## Purpose

Define the canonical minimal workflow for design handoff without making
`Figma + Code Connect` a gating dependency.

This bridge keeps PulsePlate repo-native:

- visual review stays Storybook-first
- tokens stay in repo
- Penpot is used as an optional design/inspect surface, not as runtime source of truth

## Source Of Truth

1. Runtime tokens: `frontend/src/styles/tokens.css`
2. Type-safe token exports: `frontend/src/styles/tokens.ts`
3. Canonical web preview: `frontend/.storybook/` plus co-located Storybook docs
   under `frontend/src/**/*.stories.tsx`, `frontend/src/**/*.mdx`, and curated
   entries in `frontend/src/stories/`
4. Runtime components: `frontend/src/components/`
5. CTA behavior contract: `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`

Evidence: `frontend/src/styles/tokens.css:8`, `frontend/src/styles/tokens.ts:12`,
`frontend/.storybook/main.ts:4`, `frontend/.storybook/main.ts:5`,
`frontend/src/stories/PulsePlateDesignSystemGuidelines.mdx:7`,
`frontend/src/components/design-system/DesignSystemOverview.tsx:8`,
`docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md:59`.

Penpot is a design collaboration layer only. It does not replace repo SoT.

## When To Use This Bridge

Use this workflow when at least one of these is true:

- Figma Code Connect is blocked by plan/seat
- Design team wants a lower-cost inspect/share surface
- We need visual parity review without node-level Code Connect activation
- We want a design tool that can reference Storybook exports and repo tokens

For web review, this is the default path even when Figma remains available.

## Canonical Workflow

### 1. Build the review surface in repo first

- Implement or update the target UI in `frontend/`
- Add or update Storybook stories/MDX docs
- Verify with:
  - `cd frontend && npm run build`
  - `cd frontend && npm run build-storybook`

### 2. Use Penpot as design/inspect layer

- Recreate or import the target screen/component in Penpot
- Keep naming aligned with repo contracts:
  - `PP/Web/...`
  - `PP/iOS/...`
  - `PP/Shared/...`
- Store only visual/layout intent in Penpot:
  - structure
  - spacing
  - icon placement
  - annotation
  - state review

### 3. Mirror repo tokens into Penpot styles

- Mirror canonical PulsePlate colors from `tokens.css`
- Mirror spacing/radius/type scale from `tokens.ts` / `tokens.css`
- Do not introduce Penpot-only colors or spacing values that drift from repo SoT

### 4. Map Penpot review back to repo evidence

For each reviewed CTA/component, record:

- component path
- story path or MDX page
- CTA ID if applicable
- Penpot board/page reference
- screenshot/export link if needed for audit

### 5. Verify in repo, not in the design tool

Release confidence comes from:

- Storybook preview
- frontend tests
- build output
- token SoT review

Penpot approval alone is not enough to claim implementation readiness.

## Deliverables

Minimum acceptable handoff packet:

- Storybook story or MDX entry
- repo component path
- token alignment note
- Penpot page/frame reference
- CTA mapping note if the surface is interactive

## Tooling Policy

### Required now

- No new frontend packages are required for the baseline bridge
- Existing Storybook stack is sufficient

### Optional later

Only add Storybook token/documentation addons if current MDX stories become
insufficient for review. Do not add them preemptively.

## Non-negotiable Rules

- No raw hex drift from repo token SoT
- No design-only component names that break PulsePlate naming rules
- No claims of Code Connect activation when using the Penpot bridge path
- No new runtime dependency on Penpot exports

## Acceptance Criteria

1. Storybook remains the canonical web review surface.
2. Repo token SoT remains canonical.
3. Penpot is documented as an optional design/inspect layer, not runtime SoT.
4. Interactive surfaces still point back to CTA contracts in repo docs.
5. The workflow works without Figma Organization/Enterprise upgrade.

## Exit Criteria For Optional Code Connect

Owning ADR: `docs/architecture/ADR_PENPOT_STORYBOOK_BRIDGE_FALLBACK_SEAM_2026-03-07.md`.
Canonical backlog items:

- `docs/roadmap/BACKLOG_LEDGER.md` → `Penpot + Storybook fallback bridge for design handoff`
- `docs/roadmap/BACKLOG_LEDGER.md` → `Design file URL + node IDs required for Code Connect activation (H+P+Pr)`

Penpot remains the required low-cost fallback until all of these are true:

1. `get_code_connect_suggestions(...)` is no longer blocked by plan/seat.
2. Current CTA node IDs are re-captured under
   `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md`.
3. The mapping registry advances critical CTA rows out of
   `blocked_by_node_id_capture` / `blocked_by_plan`.
4. `get_code_connect_map(...)` returns the expected active mappings for the
   pilot CTA set.

Once those conditions are met, Penpot becomes optional inspect/docs support
rather than the required fallback bridge defined in
`docs/architecture/ADR_PENPOT_STORYBOOK_BRIDGE_FALLBACK_SEAM_2026-03-07.md`.
