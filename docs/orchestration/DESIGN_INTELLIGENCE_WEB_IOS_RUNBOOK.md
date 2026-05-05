<!-- markdownlint-disable MD013 -->
# Design Intelligence Web+iOS Runbook

**Date:** 2026-05-05
**Branch:** `docs/design-intelligence-wave-v1`
**Status:** PR-0 bootstrap contract
**Mode:** docs-only governance; no runtime UI, iOS, token, backend, Figma, Storybook config, or external asset mutation

## Summary

This runbook opens the reference-driven design intelligence wave for PulsePlate web and iOS.

The wave lets future agents compare PulsePlate implemented surfaces against strong real-world UI/UX references while keeping repo code, docs, tests, `/tokens`, generated mirrors, and governed design contracts as the source of truth.

PR-0 does not redesign PulsePlate. It creates the policy and packet layer needed before future automation can ingest references, score them, normalize them into PulsePlate vocabulary, and promote implementation briefs safely.

## Current Source-Of-Truth Model

Source precedence for this wave is fixed:

1. Repo code, docs, tests, backend contracts, and merge governance.
2. `/tokens` as the design-token authoring source.
3. Generated runtime mirrors derived from `/tokens`:
   - `frontend/src/styles/tokens.css`
   - `frontend/src/styles/tokens.ts`
   - `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift`
4. Canonical UI vocabulary and component contracts:
   - `docs/design/UI_COMPONENT_VOCABULARY.md`
   - `docs/design/ui_component_vocabulary.json`
5. Implemented web and iOS components as thin clients over backend truth.
6. Storybook as review/documentation evidence only.
7. Figma as design-intent/review evidence only.
8. External references as read-only benchmark inputs only.

Hard rule: external references, Storybook, Figma, prompt outputs, and future DESIGN.md files cannot override repo truth unless a reviewed PR promotes a specific normalized decision into repo contracts.

## Why The Prior Design-Runtime Train Is Closed

The previous design runtime system web+iOS train is complete through PR-8 and is recorded in `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-design-runtime-system-web-ios-epic`.

That train established governed primitives, product tokens, web shell convergence, iOS token adoption, accessibility/state/motion contracts, Figma manifest hardening, and Storybook parity surfaces.

This design intelligence wave is separate. It starts after the closed train and adds reference-intake governance, scoring, DESIGN.md bootstrap semantics, and future automation controls. It does not reopen PR-0 through PR-8, imply an undocumented design-runtime PR-9, or claim ownership of runtime screens without a later packet.

## Figma Role

Figma file `2JDwOByQIbcPgp93FDzHii` remains design-intent and review evidence only.

Read-only inspection baseline for PR-0:

| Page | Node id | PR-0 role |
| --- | --- | --- |
| `01_Components` | `6:3` | Component/design-system intent inventory |
| `27_Runtime_Surface_Register` | `256:2` | Runtime surface classification reference |
| `28_Runtime_Presentation_Board` | `263:2` | Presentation evidence reference |
| `29_Runtime_Visual_Companions` | `298:2` | Visual comparison/reference inventory |
| `31_Design_System_Runtime_Product_Canon` | `1096:2` | Internal product-canon review evidence |

Allowed:

- Read-only Figma MCP inspection and screenshots for evidence.
- Referencing node ids in repo docs.
- Recording drift, uncertainty, and promotion blockers.

Forbidden:

- Figma writes.
- Prototype link creation.
- Page creation, rename, deletion, or component-set mutation.
- Code Connect mapping writes.
- Treating Figma pages as runtime authority.

Control implemented for premortem risk: every Figma-derived note must stay in `read_only` or `reference_only` status until a later PR promotes a normalized repo decision.

## Storybook Role

Storybook is a review and documentation lane for implemented web components.

Allowed:

- Build and inspect Storybook as evidence for existing components.
- Require Storybook evidence in future web implementation PRs.
- Use Storybook to document component states and accessibility review coverage.

Forbidden:

- Treating Storybook stories as token authoring source.
- Creating runtime truth from Storybook-only examples.
- Changing Storybook config in PR-0.

Control implemented for premortem risk: Storybook may validate implemented consumers, but cannot author tokens, canonical layouts, product rules, billing truth, or backend-derived state.

## `/tokens` Role

`/tokens` remains the canonical repo authoring source for design tokens.

Generated mirrors are derived outputs and must not be edited by hand:

- `frontend/src/styles/tokens.css`
- `frontend/src/styles/tokens.ts`
- `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift`

Future DESIGN.md, reference scoring, and design briefs must consume token truth from `/tokens`, generated mirrors, and current component contracts. If a reference implies a token delta, the future PR must define the token change explicitly and run the token parity gates.

Control implemented for premortem risk: DESIGN.md must be generated or drift-checked from repo token/component truth and cannot become a manual second source of truth.

## External Reference Role

External references include Refero Styles, `nexu-io/open-design`, VibeUI, Stitch/DESIGN.md examples, Google DESIGN.md materials, and similar corpora.

Allowed:

- Read-only benchmark review.
- Derived metadata such as palette archetype, spacing density, component anatomy, layout pattern, accessibility risk, monetization framing, and legal-copy risk.
- Normalization into PulsePlate vocabulary before future brief generation.
- Scoring through `docs/design/REFERENCE_SCORECARD.md`.

Forbidden:

- Copying external screenshots, assets, brands, layouts, proprietary components, copy, or visual identity.
- Importing external service credentials.
- Adding a crawler in PR-0.
- Treating external references as repo truth.

Reference-specific policy:

- Refero Styles: read-only reference corpus for palette, typography, spacing, radius, component anatomy, density, page composition, and DESIGN.md-style outputs. Not a copy source.
- `nexu-io/open-design`: read-only open design corpus / ingestion reference. Use only derived metadata and normalized features.
- VibeUI: inspiration and market-scan input only. No direct implementation dependency.
- Google Stitch / DESIGN.md: use the idea of an agent-readable contract. PulsePlate DESIGN.md must be generated or drift-checked from repo truth.
- OpenAI GPT-5.5 guidance: prompts should specify target state, constraints, available data, output format, and validation gates instead of over-scripting low-level steps.
- GEPA / Nous-style prompt evolution: future prompt/rubric optimization only, over curated fixtures. It must not mutate production UI, tokens, or runtime code.

Control implemented for premortem risk: every external reference must pass the manifest schema and scorecard before it can influence a future implementation brief.

## Forbidden Actions

PR-0 forbids:

- Web redesign.
- iOS redesign.
- Figma mutation.
- External asset import.
- Reference crawler or broad scraping.
- GEPA implementation.
- Semantic design scoring runtime.
- New frontend components.
- `/tokens` changes.
- Token regeneration.
- Generated token mirror edits.
- Storybook config changes.
- Backend, OpenAPI, billing, auth, compliance, StoreKit, App Store release, or deployment changes.
- Unsupported medical, clinical, treatment, therapy, or crisis-support claims.

Future implementation PRs also forbid thin-client violations and product truth movement into web or iOS clients unless a later packet explicitly scopes and proves the contract change.

## PR Train

| PR | Title | Purpose |
| --- | --- | --- |
| PR-0 | `docs(design): open reference-driven design intelligence wave for web and iOS` | Docs-only governance, reference policy, schema, scorecard, DESIGN.md bootstrap |
| PR-1 | `feat(design): generate PulsePlate DESIGN.md from token and component contracts` | Generated or drift-checked DESIGN.md from repo truth |
| PR-2 | `feat(design): add external reference manifest and normalization tooling` | Manifest files and normalization helpers |
| PR-3 | `feat(design): add screen evidence pack for web and iOS review surfaces` | Evidence packs for implemented surfaces |
| PR-4 | `feat(design): add deterministic design scorecard checks` | Deterministic scorecard validation |
| PR-5 | `feat(frontend): align web launch shell to design intelligence brief` | Bounded web implementation after accepted brief |
| PR-6 | `feat(ios): add iOS design parity audit and bounded visual sync` | Bounded iOS audit/sync with App Store-safe evidence |
| PR-7 | `feat(orchestration): add design-agent workflow and PR template` | Design-agent workflow and PR template |
| PR-8 | `docs(research): add GEPA-compatible prompt/rubric evolution lane` | Future prompt/rubric eval lane only |

No later PR may start until PR-0 lands and `main` is synced and healthy.

## Agent Routing

Coordinator-first route:

1. `agent-coordinator`
2. `creative-designer`
3. `frontend-engineer`
4. `architecture-specialist`
5. `security-auditor`
6. `data-scientist-agent` advisory for scoring/rubric design
7. `ml-engineer-agent` advisory for future GEPA/eval layer
8. `qa-engineer-agent`
9. `bug-hunter`

Bootstrap note: the current repo inventory does not register `ios-engineer` or `accessibility-reviewer` as canonical routable agent slugs. iOS and accessibility review obligations remain covered through `frontend-engineer`, `architecture-specialist`, `qa-engineer-agent`, `bug-hunter`, repo iOS scoped instructions, and future App Store/accessibility evidence gates.

Skills:

- Required repo gates: `pulseplate-workflow`, `pulseplate-gates`, `pulseplate-guards`.
- Design governance: `pulseplate-design-launch-system`.
- Premortem: `pulseplate-premortem-risk-review`.
- PR governance: `pulseplate-pr-review`, `agents-md`, `create-pr` when opening.
- Figma plugin: read-only evidence only.
- GitHub plugin/CLI: PR creation, current-head checks, review governance.

## Validation Gates

PR-0 local narrow bundle:

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
python3 scripts/orchestration/task_bootstrap.py ... --pr-phase pre_open
python3 -m pytest -q --confcutdir=tests/guards tests/guards/test_wellness_language_blockers_guard.py
python3 -m pytest -q --noconftest tests/test_philosophy_validator.py
markdownlint docs/orchestration/DESIGN_INTELLIGENCE_WEB_IOS_RUNBOOK.md \
  docs/orchestration/DESIGN_INTELLIGENCE_PR0_PACKET_2026-05-05.md \
  docs/design/REFERENCE_MANIFEST_SCHEMA.md \
  docs/design/REFERENCE_SCORECARD.md \
  docs/design/PULSEPLATE_DESIGN_MD_BOOTSTRAP.md
make design-guard
npm --prefix frontend run tokens:check
npm --prefix frontend run build-storybook
make validate-changed
non_docs="$(git diff --name-only origin/main...HEAD | rg -v "\.md$|README\.md$|AGENTS\.md$|RUNBOOK_AGENT\.md$|DEPLOYMENT\.md$" || true)"
test -z "$non_docs"
pre-commit run --all-files
git status --short
```

If `npm --prefix frontend run build-storybook` creates `frontend/storybook-static/`, remove that untracked local artifact before continuing.

Full local `make verify` is intentionally not run for PR-0 by operator machine-budget decision. This does not create a merge-ready claim. Merge readiness still depends on current-head CI, fixed mapping, review-bot pass/no-actionables, unresolved thread disposition, and the mandatory wait-window.

These validation commands are the canonical PR-0 local bundle for this wave. The PR-0 packet references this runbook for the shared source-of-truth hierarchy, forbidden-action list, validation bundle, and premortem controls so those controls do not drift between documents.

The wellness-language blocker and philosophy-validator tests are blocking gates for this lane. They keep PR-0 copy and future LLM-derived design briefs inside wellness-only, trust-safe product boundaries before any reference output can influence product work.

## Promotion Rules

A reference may influence future implementation only when all are true:

- A manifest entry exists and is valid under `docs/design/REFERENCE_MANIFEST_SCHEMA.md`.
- The scorecard has an `adopt`, `adapt`, or `reject` decision with rationale.
- External source license and copy-risk fields are explicit.
- All external terms are normalized into `docs/design/UI_COMPONENT_VOCABULARY.md` and existing repo components where possible.
- Any token, component, layout, or copy delta is promoted in a future PR with deterministic evidence.
- Future implementation PRs include screenshot, Storybook, accessibility, and platform evidence appropriate to the surface.

No reference may directly write runtime code, tokens, Figma, or generated mirrors.

## Rollback / Risk Model

Rollback is a docs-only revert of PR-0. No runtime state, token mirror, backend, iOS, Figma, external asset, or deployment rollback is required.

Risk controls:

- Shadow SoT risk is controlled by source precedence and promotion rules.
- Copy risk is controlled by manifest fields, forbidden copy elements, and scorecard rejection paths.
- DESIGN.md drift is controlled by generated/drift-checked future DESIGN.md requirements.
- Figma and Storybook authority drift is controlled by read-only/review-only role definitions.
- Web/iOS implementation drift is controlled by later thin-client and App Store-safe evidence gates.
- GEPA metric drift is controlled by deferring GEPA to curated prompt/rubric fixtures only.
