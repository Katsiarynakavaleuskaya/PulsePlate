<!-- markdownlint-disable MD013 -->
# Kimi Prototype Intake Modernization Bridge Protocol

## Summary

This protocol governs how PulsePlate can use the current Kimi prototype as read-only evidence for modern product and visual direction.

It is a docs/governance bridge only. It does not authorize runtime web, iOS, backend, OpenAPI, generated client, Storybook, Figma, Canva, Code Connect, asset, token, deploy, App Store, Cloudflare, billing, auth, StoreKit, HealthKit, screenshot, video, or binary changes.

## Evidence Inputs

Current read-only evidence records for this lane are:

| Evidence id | Source name | Source URL / locator | Captured at | Owner | Reviewer | Artifact class | Access notes | Status | Repo evidence anchors | Allowed use |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `kimi-page-2026-05-13` | Kimi published page | `https://7zngnnxxihim6.kimi.page/` | `2026-05-13` | `@katsiaryna_kavaleuskaya` | `agent-coordinator` | `page` | operator-provided public URL | `read_only` | `docs/design/REFERENCE_MANIFEST_SCHEMA.md`, `docs/design/REFERENCE_SCORECARD.md` | Inspect product/visual direction and user-facing flow ideas |
| `kimi-drive-folder-2026-05-13` | Kimi Drive prototype folder | `https://drive.google.com/drive/folders/1kVBP5Gjolmg_RUiorx5B_biw51ueGwXe` | `2026-05-13` | `@katsiaryna_kavaleuskaya` | `agent-coordinator` | `drive_folder` | connector visibility status `access_not_verified` | `read_only` | `docs/design/REFERENCE_MANIFEST_SCHEMA.md`, `docs/design/REFERENCE_SCORECARD.md` | Record available artifact inventory, not file contents as repo truth |
| `kimi-desktop-bundle-2026-05-13` | Kimi desktop code bundle | Kimi chat `PulsePlate сайт`, published preview `v30`, `All files` bundle | `2026-05-13` | `@katsiaryna_kavaleuskaya` | `agent-coordinator` | `code_bundle` | desktop context observed through operator-opened Kimi app; bundle hash `unspecified` | `read_only` | `docs/design/REFERENCE_MANIFEST_SCHEMA.md`, `docs/design/REFERENCE_SCORECARD.md` | Inspect generated structure and evidence names without executing, vendoring, or copying |
| `figma-reference-file-2026-05-13` | Figma reference file | `2JDwOByQIbcPgp93FDzHii` | `2026-05-13` | `@katsiaryna_kavaleuskaya` | `agent-coordinator` | `figma_frame` | node mappings `unspecified` unless repo-confirmed | `read_only` | `docs/orchestration/DESIGN_INTELLIGENCE_WEB_IOS_RUNBOOK.md` | Compare existing repo-governed design intent only |
| `canva-unspecified-2026-05-13` | Canva or other design tools | `unspecified` until operator provides a concrete artifact | `2026-05-13` | `@katsiaryna_kavaleuskaya` | `agent-coordinator` | `document` | no concrete artifact confirmed | `read_only` | `docs/design/REFERENCE_MANIFEST_SCHEMA.md` | No authority until a later repo-reviewed contract scopes a narrower use |

Known Drive/Kimi bundle inventory observed for this lane includes the `app` folder and image artifacts such as `site_v7_full.png`, `site_hero.png`, and `onboarding_debug.png`. Those names are evidence metadata only; they do not make screenshots, generated code, or assets canonical.

## Source Of Truth Boundary

Kimi prototype artifacts, Google Drive files, Figma frames, Canva files, screenshots, generated briefs, generated code, and external design notes are evidence/reference inputs only. They do not become PulsePlate product truth, runtime truth, OpenAPI truth, backend truth, token truth, component truth, App Store truth, or implementation authority unless a later repo-reviewed contract explicitly promotes a narrower artifact.

Canonical authority remains:

1. Repo code, docs, tests, reviewed contracts, and merge governance.
2. Backend/OpenAPI for product and runtime contract truth.
3. `/tokens` as token authoring truth.
4. Generated mirrors as derived runtime artifacts.
5. UI vocabulary and component contract docs.
6. Implemented web and iOS components as thin clients over repo/backend truth.

Unknown values must remain `unspecified`. Do not infer component ownership, token names, Figma node mapping, visual thresholds, accessibility thresholds, Code Connect status, platform readiness, or runtime file anchors from prototype artifacts.

## Intake Record Contract

Every current or future Kimi evidence record must be compatible with `docs/design/REFERENCE_MANIFEST_SCHEMA.md` and include these fields before it can influence a brief:

| Field | Meaning | Unknown value |
| --- | --- | --- |
| `evidence_id` | Stable repo-local id | `unspecified` |
| `reference_id` | Manifest-compatible stable repo-local id | `unspecified` |
| `source_name` | Human source label | `unspecified` |
| `source_url` | Kimi, Drive, Figma, or other locator | `unspecified` |
| `captured_at` | Evidence capture date/time | `unspecified` |
| `artifact_class` | `page`, `drive_folder`, `code_bundle`, `screenshot`, `figma_frame`, or `document` | `unspecified` |
| `owner` | Operator or lane owner | `unspecified` |
| `reviewer` | Role agent or human reviewer | `unspecified` |
| `allowed_use` | Read-only purpose | `read_only` |
| `status` | `read_only`, `normalized`, `candidate_for_brief`, or `rejected` | `read_only` |
| `product_category` | Manifest product category such as wellness, SaaS, ecommerce, coaching, or analytics | `unspecified` |
| `platform` | Manifest platform array such as `web`, `ios`, `android`, `desktop`, `cross_platform`, or `unknown` | `unspecified` |
| `surface_type` | Manifest surface array such as landing, dashboard, onboarding, paywall, or settings | `unspecified` |
| `visual_archetype` | Normalized visual pattern, not vendor wording | `unspecified` |
| `palette_archetype` | Derived palette family, not copied color values | `unspecified` |
| `typography_archetype` | Derived type hierarchy pattern | `unspecified` |
| `spacing_density` | `compact`, `balanced`, `comfortable`, `editorial`, or `unknown` | `unspecified` |
| `radius_profile` | `sharp`, `subtle`, `medium`, `soft`, `pill`, `mixed`, or `unknown` | `unspecified` |
| `component_patterns` | Normalized component patterns observed | `unspecified` |
| `layout_patterns` | Normalized layout patterns observed | `unspecified` |
| `motion_notes` | Motion pattern and reduced-motion risk notes | `unspecified` |
| `normalization_notes` | How observations map into PulsePlate vocabulary | `unspecified` |
| `forbidden_copy_elements` | Code, assets, layouts, copy, or claims that must not be copied | `unspecified` |
| `mapped_pulseplate_components` | Repo-confirmed component vocabulary or registry anchors | `unspecified` |
| `repo_evidence_anchors` | Repo docs/tests/contracts supporting any promotion | `unspecified` |
| `wellness_safety_notes` | Wellness-only claim review | `unspecified` |
| `accessibility_notes` | Contrast, focus, motion, keyboard, touch, readability risks | `unspecified` |
| `security_privacy_notes` | Secret, PII, internal URL, bundle, or external-write risks | `unspecified` |
| `license_status` | External artifact license or permission status | `unspecified` |
| `attribution_required` | Whether attribution is required before any brief promotion | `unspecified` |
| `legal_copy_risks` | Copy, layout, claim, or asset reuse risks | `unspecified` |
| `monetization_notes` | Conversion/paywall/pricing signal notes without copying claims | `unspecified` |
| `icon-silhouette-check` | Manifest guard status: `required`, `passed`, `not_applicable`, or `blocked` | `required` |
| `design-guard` | Manifest guard status: `required`, `passed`, `not_applicable`, or `blocked` | `required` |
| `adopt_adapt_reject_decision` | Deterministic scorecard decision: `adopt`, `adapt`, or `reject` | `unspecified` |

`status=candidate_for_brief` is forbidden unless every required field in `docs/design/REFERENCE_MANIFEST_SCHEMA.md` is complete, including `adopt_adapt_reject_decision`, `license_status`, `attribution_required`, `legal_copy_risks`, forbidden-copy elements, normalization notes, mapped PulsePlate components, repo evidence anchors, `product_category`, `platform`, `surface_type`, visual/palette/typography archetypes, component/layout patterns, `monetization_notes`, `icon-silhouette-check`, and `design-guard`. `reject` decisions cannot influence a brief. Incomplete evidence stays `read_only` or `normalized`.

## Modernization Extraction

Kimi may contribute only normalized metadata:

- visual archetype,
- palette and typography direction without copied token values,
- spacing density and layout rhythm,
- component and layout patterns in PulsePlate vocabulary,
- motion and reduced-motion risk notes,
- accessibility risk notes,
- monetization or activation framing without copied pricing truth,
- wellness and legal-copy risk notes.

The default useful decision is `adapt`, not copy. `reject` is mandatory when the useful direction cannot be separated from protected assets, copied layout, unsupported medical or diagnostic claims, legal risk, poor accessibility, secret/PII exposure, or runtime architecture drift.

No Kimi-generated code, component structure, styling, copy, assets, images, token values, route shape, package configuration, generated bundle, or layout may be copied directly into PulsePlate.

## Normalization Bridge

The bridge from Kimi evidence to implementation is:

1. Capture evidence metadata with provenance and `read_only` status.
2. Extract normalized direction through the reference manifest and scorecard controls.
3. Map only verified patterns into PulsePlate UI vocabulary.
4. Map implementation candidates into the design component contract registry.
5. Require bridge coverage inventory for repo vocabulary, web runtime, iOS runtime, Storybook review, Figma reference, Penpot reference, and Code Connect traceability.
6. Require fail-closed visual regression and accessibility regression decisions.
7. Define token/runtime parity boundary before any web or iOS implementation.
8. Open later bounded web/iOS implementation slices only after the previous gates exist; missing prerequisite gates are blockers, not `DEFERRED` permission to proceed.

Screenshots, Kimi output, Storybook stories, Figma nodes, prompt review, or desktop previews are not substitutes for repo-reviewed visual or accessibility regression decisions.

The first machine-readable registry gate is `docs/orchestration/contracts/design_component_registry.v1.json`, validated by `scripts/design/design_component_registry.py`. The next machine-readable bridge gate is `docs/orchestration/contracts/design_bridge_coverage_inventory.v1.json`, validated by `scripts/design/design_bridge_coverage_inventory.py`. Kimi-derived candidates must map through these repo-owned gates before any visual regression lane, accessibility regression lane, token/runtime parity boundary, or web/iOS implementation slice. Missing registry or bridge coverage is a blocker, not permission to copy from Kimi.

Compatibility wording for the existing docs guard: Kimi-derived candidates must map through this registry before any bridge coverage inventory, visual regression lane, accessibility regression lane, token/runtime parity boundary, or web/iOS implementation slice.

GPT-5.5 / OpenRouter remains the primary coding and governance model for repo changes in this lane. Kimi may provide bounded design review only; it must not own implementation or edit repo code.

## Security And External Tool Boundaries

This protocol forbids:

- Kimi, Drive, Figma, Canva, App Store Connect, Cloudflare, Supabase, or deploy writes;
- broad scraping, crawling, or download-all behavior;
- executing, installing, vendoring, or importing generated Kimi bundles;
- committing screenshots, videos, binary assets, downloaded bundles, or generated design exports;
- copying prompts, comments, logs, screenshots, or metadata without secret/PII/internal URL review;
- using external artifacts to resolve review threads, edit fixed mapping, mark merge-readiness, or bypass current-head CI.

Allowed evidence collection is limited to operator-provided URLs, connector metadata, current desktop context, and repo-local docs. The evidence record must preserve provenance and access notes.

## Docs-Only Diff Guard

Kimi bridge work must start from an isolated clean worktree based on `origin/main`. Do not switch the root checkout, edit unrelated `worktrees/...` lanes in place, or use a shared virtual environment from another worktree.

This lane may touch only this protocol, scoped orchestration routing docs (`docs/orchestration/AGENTS.md`), design workflow/template pointers, the backlog ledger pointer, focused deterministic docs guards, and the post-open fixed-mapping artifact after a PR number exists.

The PR must stop if the diff includes runtime web, iOS, backend, OpenAPI, token, generated mirror, Storybook config, CI workflow, package/config, screenshot, video, binary asset, downloaded bundle, deploy, App Store, Cloudflare, billing, auth, StoreKit, or HealthKit paths.

`docs/review/PR_<N>_FIXED_MAPPING.md` must not be created before a PR number exists. Discussion-thread and merge-readiness checkboxes must remain unchecked until review disposition, current-head checks, mandatory wait-window, Agent Run Summary evidence, and strict merge-readiness wrapper evidence exist.

## Agent And Review Order

Pre-open role order for this lane is coordinator-owned:

1. `agent-coordinator`
2. `creative-designer`
3. `cursor-specialist-agent`
4. `architecture-specialist`
5. `security-auditor`
6. `qa-engineer-agent`
7. `frontend-engineer`
8. `bug-hunter`

If `task_bootstrap.py` or `agent-coordinator` expands the role order, the expanded order becomes mandatory. No declared role agent may be skipped without a coordinator update.

Post-open review remains mandatory:

1. `qa-engineer-agent`
2. `bug-hunter`
3. `security-auditor`
4. `pulseplate-pr-review`
5. `pulseplate-premortem-risk-review`
6. Codex Security plugin diff scan

After the first bot review, rerun on current head:

1. `agent-coordinator`
2. `qa-engineer-agent`
3. `bug-hunter`
4. `security-auditor`
5. `pulseplate-premortem-risk-review`
6. `pulseplate-pr-review`
7. Codex Security plugin diff scan

Before merge readiness, the local Agent Run Summary must exist under `artifacts/agent_runs/`. PR body text or fixed mapping entries may reference that local evidence, but they must not replace it. The artifact is local-only evidence and must not be committed.

## Future Implementation Sequence

Future web/iOS modernization work must proceed in this order:

1. Component contract registry.
2. Bridge coverage inventory.
3. Visual regression lane.
4. Accessibility regression lane.
5. Token/runtime parity boundary.
6. Later web+iOS implementation slices.

Web and iOS slices must stay thin over backend/OpenAPI and repo contracts. Tokens change only through `/tokens` plus generated mirrors and parity gates. Component changes must use repo component contracts, Storybook review where applicable, and accessibility validation.

## Premortem Controls

The premortem must inspect the actual docs/tests diff before PR opening and again after the first bot-review cycle.

Minimum findings to close before readiness:

- Kimi source-of-truth drift,
- unverified Drive or desktop bundle evidence,
- runtime, token, generated mirror, or external write scope creep,
- direct-copy or legal-copy risk,
- visual or accessibility gate bypass,
- wellness-only claim drift,
- secret/PII/internal URL leakage from prototype artifacts,
- fixed-mapping or PR-body governance misuse.

Real findings must be fixed in docs/tests before mapping. Mapping is evidence after fix or formal decision; it is not the fix.
