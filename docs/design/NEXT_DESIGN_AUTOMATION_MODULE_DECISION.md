<!-- markdownlint-disable MD013 -->
# Next Design Automation Module Decision

## Summary

This decision packet selects the next PulsePlate design automation lane after the landed Design Intelligence PR-8.

The selected next lane is the **Icon Asset Validator / App Store asset guard lane**.

This document is a process decision only. It does not implement the selected lane, does not create an undocumented PR-9 implementation train, and does not mutate runtime web, runtime iOS, backend, OpenAPI, `/tokens`, generated mirrors, Figma, Canva, Storybook config, screenshots, videos, traces, or external assets.

## Current PR-6 Status (for implementation planning)

- This PR implements the **Icon Asset Validator / App Store asset guard lane** implementation slice only.
- Scope is deliberately limited to repo-local validation, tests, and governance updates.
- No runtime UI, screenshot generation, StoreKit changes, network uploads, or asset uploads are included.
- Figma/Canva/Storybook are evidence/reference only unless explicitly promoted by a future packet.

## Current Repo Truth

The Design Intelligence wave has landed through PR-8:

- PR-0 through PR-4 created the governance, DESIGN.md, reference manifest, screen evidence pack, and deterministic scorecard layers.
- PR-5 accepted the current web launch shell with deferred minor follow-up.
- PR-6 audited iOS visual parity and recorded no broad redesign lane.
- PR-7 added the repeatable design-agent workflow and PR template.
- PR-8 added a GEPA-compatible prompt/rubric evolution lane as research/eval/process-only.

The runbook says the Design Intelligence wave does not imply an undocumented design-runtime PR-9 or runtime ownership without a later packet. Therefore the next action is a coordinator-owned selection packet, not an implementation PR.

Repo code/docs/tests, `/tokens` as token authoring truth, generated mirrors as derived artifacts, UI vocabulary, backend/OpenAPI contracts, and runtime code remain canonical. DESIGN.md, decision packets, research docs, Figma, Canva, Storybook, evidence packs, scorecards, templates, and prompt outputs remain evidence/reference/process layers only.

## Candidate Modules

The candidates come from the landed design-agent workflow module classification:

## Comparison Matrix

| Candidate | Repo fit | Risk | Implementation cost | Evidence dependencies | Relation to design system | SoT drift risk | Readiness now |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Icon Asset Validator / App Store asset guard lane | Strong. It is already classified as a release/design asset guard module and aligns with App Store asset backlog follow-up. | Medium because release assets touch public submission quality, but the lane can stay deterministic and repo-local. | Medium. Future work can be bounded to validators, manifests, tests, and release docs. | Existing App Store asset workflow, Fastlane metadata, screenshot tests, validators, and backlog items. | Guards released visual assets without changing token or runtime design truth. | Low if the future lane validates repo-owned assets only and does not write to App Store Connect, Figma, or Canva. | Highest. Repo already has P1 App Store asset follow-up tracking. |
| Launch Copy Compliance Linter | Good fit for wellness-safe launch copy. | Medium because wording can become compliance-sensitive. | Medium. Needs copy surfaces and blocked-claim policy alignment. | Wellness language policy, metadata docs, launch copy surfaces. | Protects launch communication, not component visuals. | Medium because copy checks can be mistaken for product/compliance truth unless tied back to repo policy. | Ready later after asset guard boundary is selected. |
| Marketing Asset Pack Compiler | Useful later for GTM packaging. | Medium-high because compilers can accidentally imply asset generation or external write authority. | Higher. Requires approved copy/design truth and asset packaging boundaries. | Approved design/copy truth, release asset lanes, compliance gates. | Downstream of asset/copy governance. | High until asset and copy sources are locked by prior guarded lanes. | Not first; depends on earlier guard lanes. |
| Button / Component Drift Inspector expansion | Useful for component parity. | Medium because it could drift into runtime redesign or Storybook config changes. | Medium-high. Needs Storybook/vocabulary parity scope and deterministic comparisons. | PR-4 scorecards, UI vocabulary, Storybook review surfaces. | Closest to component design system governance. | Medium because Storybook/evidence surfaces must remain review evidence only. | Defer until a concrete runtime/component drift gap is identified. |
| Adjacent design-agent research lane | Useful for future agent quality. | Medium because research outputs can be mistaken for truth. | Low-medium if docs-only. | PR-7 workflow and PR-8 GEPA lane. | Process layer only. | Medium-high unless the lane repeats PR-8's non-canonical research boundary. | Not the next practical product-quality lane. |

## Selected Next Lane

The selected next lane is **Icon Asset Validator / App Store asset guard lane**.

The future implementation PR should be a release/design asset guard PR, not a generic Design Intelligence PR-9 and not a broad App Store release implementation.

Suggested future branch shape:

- `feat/design-icon-asset-validator-v1`

Suggested future title shape:

- `feat(design): add icon asset validator guard`

Exact future branch/title must still be confirmed by its own coordinator packet.

## Why This Lane Is Next

The Icon Asset Validator / App Store asset guard lane is next because it has the clearest combination of repo fit, readiness, and bounded implementation surface:

- The design-agent workflow already classifies Icon Asset Validator as a release/design asset guard module.
- The backlog already tracks App Store asset rollout and PR 1147 asset workflow alignment follow-ups.
- The lane can be deterministic and repo-local.
- It improves release-facing quality without changing runtime UI, product truth, backend contracts, `/tokens`, generated mirrors, Figma, Canva, or Storybook config.
- It is downstream of PR-7 workflow governance and PR-8 research boundaries, but does not require GEPA or prompt evolution to proceed.

## Deferred Lanes

The following lanes are deferred and require their own future coordinator packet before any implementation:

- Launch Copy Compliance Linter.
- Marketing Asset Pack Compiler.
- Button / Component Drift Inspector expansion.
- Adjacent design-agent research lane.

Deferral does not mean rejection. It means these lanes are not first after PR-8 and must not be smuggled into the Icon Asset Validator lane.

## Future Implementation Boundary

A future Icon Asset Validator implementation PR may touch only explicitly scoped release/design asset governance surfaces, such as:

- App icon or release asset manifest validation docs.
- Deterministic validator scripts or tests for repo-owned asset metadata.
- Release/design asset runbooks and backlog tracking.
- Existing App Store asset workflow docs when needed for validator integration.

It must not touch:

- Runtime web or iOS UI.
- Backend, OpenAPI, billing, auth, StoreKit, HealthKit, or product logic.
- `/tokens`.
- Generated mirrors, including frontend token mirrors or `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift`.
- Figma or Canva writes.
- Storybook config.
- Screenshots, videos, traces, binary assets, or external asset generation unless a future release asset packet explicitly scopes them.
- GEPA runtime, online optimization, prompt self-modification, or live product prompt mutation.

## Risks

- The selection could be misread as permission to implement asset validation in this PR.
- The future lane could widen into App Store upload, screenshot generation, or release-ops activation.
- App Store asset governance could be confused with runtime design truth.
- External design tools could be treated as sources of truth instead of evidence/reference layers.

Controls:

- This PR remains docs/test-only.
- The selected lane requires a separate future packet and PR.
- Repo truth and `/tokens` precedence are restated here and guarded by tests.
- Deferred lanes are explicit.

## Rollback / If Selection Changes Later

Rollback is a docs-only revert of this decision packet and its test/ledger update.

If the selected next lane changes later, the replacement PR must:

- cite this decision,
- explain the changed repo evidence,
- update the backlog,
- preserve the source-of-truth hierarchy,
- keep implementation separate from the decision unless a new packet explicitly scopes implementation.
