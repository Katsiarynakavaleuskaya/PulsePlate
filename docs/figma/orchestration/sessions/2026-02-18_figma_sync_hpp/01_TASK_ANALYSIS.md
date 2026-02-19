# 01 Task Analysis (Figma Sync H+P+Pr)

- context_version: 2026-02-18 / commit `162ad6ef`
- source mode: Make-only (`<FIGMA_MAKE_FILE_ID>`) until Design URL exists
- primary objective: reconcile Figma Make updates with Git SoT and prepare Code Connect bridge to existing site
- fixed scope: Home + Plate + Progress + linked CTA flows only

## Domain lanes

- Coordinator: scope lock, conflict resolution, final synthesis
- Figma MCP: Make snapshot (guidelines, components, styles)
- Frontend: web runtime surface mapping
- iOS: iOS runtime surface mapping
- Accessibility: target size/contrast/focus conflict audit
- Sora/Brand: anti-drift and prompt-safety consistency
- Security: no secrets/internal URLs in bridge flows

## Inputs reviewed

- `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md`
- `docs/figma/PULSEPLATE_FIGMA_AI_GOVERNANCE_INDEX.md`
- `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`
- `frontend/src/config/routes.ts:23`
- `docs/roadmap/BACKLOG_LEDGER.md:1643`

## Expected outputs

- Make sync audit doc
- Code Connect bridge runbook
- 23-row mapping candidates registry
- blocker recorded in backlog
