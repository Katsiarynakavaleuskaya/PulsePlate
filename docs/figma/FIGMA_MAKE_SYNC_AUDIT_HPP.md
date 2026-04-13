<!-- markdownlint-disable MD013 -->
# Figma Make Sync Audit (H+P+Pr)

**Date:** March 12, 2026
**Scope:** Home + Plate + Progress (Web + iOS) and linked CTA flows
**Source mode:** Make-only (`<FIGMA_MAKE_FILE_ID>`) until Design URL is provided
**Context version:** 2026-02-18 / commit `162ad6ef`

## 1) Purpose

This audit reconciles current Figma Make updates with Git source-of-truth artifacts and records implementation blockers for Code Connect activation.

Primary SoT references:

- `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md`
- `docs/figma/PULSEPLATE_FIGMA_AI_GOVERNANCE_INDEX.md`
- `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`
- `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md`
- `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md`
- `frontend/src/config/routes.ts:23`
- `frontend/src/pages/Home.tsx:34`
- `ios/PulsePlate/Views/HomeView.swift:57`

## 2) Baseline Snapshot (Evidence)

- Figma MCP auth check is mandatory in the activation workflow (`whoami` gate).
  Evidence: `docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md:14`
- Active Make file pointer exists in backlog: `docs/roadmap/BACKLOG_LEDGER.md:1643`.
- Make-only sync loop explicitly requires `get_design_context(fileKey=<FIGMA_MAKE_FILE_ID>, nodeId=0:1)` before reconciliation.
  Evidence: `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md:139`
- Project CTA behavior SoT remains matrix-driven: `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md:59`.
- Production-domain baseline re-check on March 12, 2026 shows repo-backed
  runtime still serving `pulseplate.app`, `www.pulseplate.app` returning `525`,
  and the Figma custom-domain attempt warning about a conflicting apex `AAAA`
  record. Evidence:
  `docs/figma/orchestration/sessions/2026-03-12_domain_canonicalization/01_BASELINE_STATUS.md:6`

## 3) Aligned

1. Scope lock is consistent with H+P+Pr governance.
Evidence: `docs/figma/PULSEPLATE_FIGMA_AI_GOVERNANCE_INDEX.md:40`, `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md:5`
2. Naming contract is aligned to `PP/<Platform>/<Screen>/<Component>/<State>`.
Evidence: `docs/figma/FIGMA_AI_HANDOFF_CHECKLIST.md:19`, `docs/figma/PULSEPLATE_FIGMA_AI_GOVERNANCE_INDEX.md:74`
3. CTA registry list in governance matches matrix coverage expectations.
Evidence: `docs/figma/PULSEPLATE_FIGMA_AI_GOVERNANCE_INDEX.md:139`, `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md:59`
4. Safety framing remains wellness-first and no-diagnostic in canonical Git docs.
Evidence: `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md:129`, `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:317`

## 4) Conflicts

### 4.1 Palette Governance Conflict (Gold treatment)

- Make guideline snapshot includes Gold `#D4AF37` as canonical palette member.
- Git anti-drift references treat purple/gold drift as forbidden unless explicitly constrained to contextual accents.
Evidence: `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:154`, `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:324`, `docs/figma/PULSEPLATE_FIGMA_AI_GOVERNANCE_INDEX.md:63`

Risk: visual drift between Make-driven assets and in-product style lock.

### 4.2 Accessibility Target Size Conflict (Web)

- Make guideline snapshot references web minimum target of 44px.
- Project visual system lock for this stream sets web minimum to 48x48 CSS px.
Evidence: `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md:104`, `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md:111`

Risk: inconsistent component sizing and QA ambiguity for tap/click comfort.

### 4.3 Architecture Divergence (Make shell vs runtime site)

- Make `App.tsx` uses view toggles and localStorage bootstrap flow not present in canonical route/runtime architecture.
- Production web runtime uses route registry + auth wrappers + tab bar contract.
Evidence: `frontend/src/App.tsx:1`, `frontend/src/config/routes.ts:23`, `frontend/src/pages/Home.tsx:34`, `frontend/src/pages/Plate.tsx:37`

Risk: generated components map to non-canonical entry points.

### 4.4 Production Domain Ownership Conflict

- The repo-backed production contract still owns `pulseplate.app` and `www.pulseplate.app`.
- The current Figma custom-domain setup attempts to attach `pulseplate.app`
  while warning about a conflicting apex `AAAA` record.
- `www.pulseplate.app` currently fails TLS (`525`), which is consistent with
  mixed or incomplete ownership between Cloudflare/app runtime and the Figma
  custom-domain attempt.
Evidence:
`docs/figma/orchestration/sessions/2026-03-12_domain_canonicalization/01_BASELINE_STATUS.md:5`,
`deploy/Caddyfile.production:1`,
`deploy/docker-compose.production.yaml:1`

Risk: production traffic can drift between incompatible ownership models and
break TLS or redirect behavior before any design sync work even starts.

## 5) Missing for Implementation

1. No Design file URL or node IDs for node-level Code Connect.
2. `Figma Node ID` still `TBD` across matrix rows.
Evidence: `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md:59`
3. Mapping registry exists for 23 CTA IDs:
   `docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md`.
4. No status lifecycle tracking (`candidate -> validated -> active`) in current handoff contract.

## 6) Action Required

| Priority | Item | Owner | DoD | Target PR |
| --- | --- | --- | --- | --- |
| P0 | Resolve web target-size conflict (44 vs 48) by declaring one canonical value in figma docs and Make sync contracts | Coordinator + Accessibility | One value in all figma docs; conflict note closed in this audit | Docs PR (this stream) |
| P0 | Introduce Code Connect bridge runbook with blocker protocol for missing Design URL | Coordinator + FE | `FIGMA_CODE_CONNECT_BRIDGE_HPP.md` merged and linked from runbook/governance | Docs PR (this stream) |
| P1 | Create 23-CTA mapping candidate registry for existing site surfaces | FE + iOS + Design | Every CTA row has surface path, status, and gap note | Docs PR (this stream) |
| P1 | Add Code Connect map status requirement into handoff checklist | Coordinator | Checklist includes mapping status verification gates | Docs PR (this stream) |
| P0 | Canonicalize production-domain ownership to the repo-backed runtime and move any Figma-hosted preview to a dedicated subdomain | Coordinator + FE + Deploy | `pulseplate.app` + `www` remain app-owned, TLS is healthy for both names, and Figma preview no longer competes for root ownership | Domain + Infra PR |
| P2 | Activate node-level mappings after Design URL available | Design + FE + iOS | P0 CTA nodes mapped and verified with `get_code_connect_map` | Follow-up mapping PR |

## 7) Blockers

### Blocker B1 — Missing Design URL + node IDs

- Description: Code Connect activation cannot proceed past candidate stage without Design file key/node IDs.
- Tracking: add backlog dependency item in `docs/roadmap/BACKLOG_LEDGER.md`.
- Temporary mode: Make-only reconciliation + candidate mapping only.

### Blocker B2 — Production-domain ownership drift

- Description: `pulseplate.app` is the repo-canonical production host, but the
  current Figma custom-domain attempt still competes for root-domain setup and
  `www` TLS is currently unhealthy.
- Tracking: keep production-domain ownership remediation separate from Code
  Connect activation and complete it first.
- Temporary mode: use Figma as source/reconciliation only; if a public Figma
  preview is needed, move it to a dedicated non-production subdomain.

## 8) Decision Log

- 2026-02-18: Locked source mode to Make-only until Design URL is provided.
- 2026-02-18: Locked integration direction to Code Connect bridge (not embed).
- 2026-02-18: Locked requirement that all 23 CTA IDs must be represented in mapping candidates.
- 2026-03-12: Locked `pulseplate.app` and `www.pulseplate.app` to repo-canonical production ownership; Figma remains a design/source lane, not the production host.


## 9) Delta — April 13, 2026 (post-PR #1407, docs-only)

This section is intentionally delta-only. It does not reopen the authority model
already fixed in `PR #1407` and the current reconciliation packets.

### 9.1 Authority unchanged

- Web/design-system execution authority remains
  `2JDwOByQIbcPgp93FDzHii` (`canonical_execution`).
- The legacy `PulsePlate_v3` file `qJBtE5J6efmavcHCm6SF0O` remains
  `reference_only`, including the user-supplied link targeting `node-id=16:4`.
- Repo code, docs, tests, and token/component mirrors still win whenever repo
  and Figma disagree.

Evidence:

- `docs/figma/FIGMA_WEB_IOS_AUTHORITY_RECONCILIATION_PACKET.md:57-73`
- `docs/figma/PULSEPLATE_V3_DESIGN_SYSTEM_RECONCILIATION.md:36-54`
- `docs/review/PR_1407_FIXED_MAPPING.md:38-41`
- `docs/figma/orchestration/sessions/2026-04-13_phase1_delta_audit.md:12-18`

### 9.2 Live canonical / aligned surfaces

1. `2JDwOByQIbcPgp93FDzHii` node `174:116` (`Shell Parity Boundary Board`)
   remains aligned and should be kept as boundary evidence, not redesigned into
   fake web/iOS parity.
2. The clean-file phase structure remains valid for `Foundations + Components +
   Welcome Gate`; this audit does not change the Phase 1 page contract.
3. Mirror-safe repo-backed lanes remain the same as the canonical mapping set:
   `PP/Shared/Button/*`, `PP/Shared/Input/*`,
   `PP/Shared/FormField/*`, `PP/Shared/Card/*`,
   `PP/Shared/Dialog/*`, `PP/Shared/Toggle/*`,
   `PP/Shared/SegmentedControl/*`, `PP/State/Empty/*`,
   `PP/State/Skeleton/*`, `PP/Web/Navigation/TabBar/*`,
   `PP/Branding/PulsePlateLogo/*`, `PP/Branding/FitChef/*`.

Evidence:

- `docs/figma/PULSEPLATE_V3_DESIGN_SYSTEM_RECONCILIATION.md:25-32`
- `docs/figma/PULSEPLATE_V3_DESIGN_SYSTEM_RECONCILIATION.md:191-205`

### 9.3 Reference-only / stale surfaces

1. `qJBtE5J6efmavcHCm6SF0O` node `16:4` resolves to `03_iOS_Onboarding` and is
   useful as provenance only; it must not become an execution target.
2. Storybook surfaces still expose legacy node references that point at
   reference-only/stale boards rather than the clean execution lane.
3. Any discrepancy between `qJBtE5J6efmavcHCm6SF0O` and current repo/runtime
   truth remains a repo-or-canonical-file issue, not a request to promote the
   legacy file.

Evidence:

- `docs/figma/PULSEPLATE_V3_DESIGN_SYSTEM_RECONCILIATION.md:43-48`
- `frontend/src/components/design-system/DesignSystemOverview.tsx:28-39`
- `frontend/src/components/design-system/CanonBoards.tsx:232-235`
- `frontend/src/components/design-system/CanonBoards.tsx:347-350`

### 9.4 Working matrix for Phase 1 follow-up split

| Classification | Surface | Evidence | Next action |
| --- | --- | --- | --- |
| aligned / keep | `2JD...` node `174:116` (`Shell Parity Boundary Board`) | `docs/figma/orchestration/sessions/2026-04-13_phase1_delta_audit.md:12-18`; authority packets above | keep as canonical boundary board |
| aligned / mirror-safe | repo-backed canonical shared/component lanes from `PP/Shared/Button/*` through `PP/Branding/FitChef/*` | `docs/figma/PULSEPLATE_V3_DESIGN_SYSTEM_RECONCILIATION.md:191-205` | update Figma only as a mirror of repo SoT |
| reference-only | `qJBtE5J6efmavcHCm6SF0O` / `node-id=16:4` | `docs/figma/orchestration/sessions/2026-04-13_phase1_delta_audit.md:12-18`; `docs/figma/PULSEPLATE_V3_DESIGN_SYSTEM_RECONCILIATION.md:38-54` | keep for provenance only |
| update code first | `DesignSystemOverview` stale `Figma node 96:33` badge | `frontend/src/components/design-system/DesignSystemOverview.tsx:33-39` | replace stale reference with current authority wording in a repo drift PR |
| update code first | `CanonBoards` stale `35:148` / `61:77` subtitles | `frontend/src/components/design-system/CanonBoards.tsx:232-235`, `frontend/src/components/design-system/CanonBoards.tsx:347-350` | retarget or de-stale Storybook evidence in a repo drift PR |
| update code first | `PremiumGate` legacy CTA styling debt | `frontend/src/components/PremiumGate.tsx:48-57` | normalize to governed primitives/tokens before Figma mirror work |
| update code first | `VipBadge` purple gradient drift | `frontend/src/components/VipBadge.tsx:20-24` | remove forbidden drift in repo before any canonical Figma sync |
| repo-first missing primitive | `PP/Shared/Select/*`, `Textarea/*`, `Checkbox/*`, `RadioGroup/*`, `Alert/*`, `Tooltip/*` | `docs/figma/PULSEPLATE_V3_DESIGN_SYSTEM_RECONCILIATION.md:206-211` | add governed repo primitives first; Figma must not invent canon |
| repo-first vocabulary decision | `PP/Shared/StepRail/*` | `docs/figma/PULSEPLATE_V3_DESIGN_SYSTEM_RECONCILIATION.md:212-213` | decide vocabulary/ownership in repo packet first |

### 9.5 Ledger / follow-up status

One new backlog item is opened by this delta for the repo-first remediation
cluster that should not stay narrative-only:

- `docs/roadmap/BACKLOG_LEDGER.md:1859-1895`
- `docs/roadmap/BACKLOG_LEDGER.md:1898-1913`
- `docs/roadmap/BACKLOG_LEDGER.md:1915-1941`

Ledger mapping after this update is:

- `PremiumGate` and `VipBadge` remain covered by the cited Phase 1 execution
  ledger item as known blockers.
- `DesignSystemOverview`, `CanonBoards`, missing shared primitives, and the
  `StepRail` vocabulary decision are now tracked by the new repo-first drift
  cleanup item.
- `update Figma`, `reference_only`, and `aligned / keep` rows remain
  classification/evidence outcomes rather than direct implementation claims.

### 9.6 Audit guardrails for the next PRs

- Do not treat placeholder, hold, reserved, or legacy-reference frames as
  shippable authority.
- Do not repair repo/runtime drift by drawing cleaner fiction in Figma.
- Do not let missing repo primitives become Figma-only component inventions.

<!-- markdownlint-enable MD013 -->
