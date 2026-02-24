<!-- markdownlint-disable MD013 MD033 -->

# Pull Request

## Summary

P2 visual polish: Tab Bar Active Trail Micro-Motion for web navigation.
Adds motion spec + prompt-pack alignment for subtle active-tab feedback with reduced-motion fallback.

- [x] I reviewed `docs/ENGINEERING_LESSONS.md` and followed repo policies.
- [x] Select one change type:
  - [ ] Bug fix
  - [x] Feature
  - [ ] Refactor
  - [x] Docs
- [x] Linked docs:
  - `docs/design/VISUAL_ELEMENT_PROMPT_CATALOG.md` (Element 08)
  - `docs/design/VISUAL_IMPLEMENTATION_MAP.md`
  - `docs/sora/prompts/hpp/p2_expressive/tab_bar_active_trail_micro_motion__tabbar__v1.0.md`

## Risk & Impact

- [x] User-facing change
- [ ] Data model/migration
- [ ] Security-sensitive
- [ ] Performance-sensitive

## Test Plan

- [ ] Unit tests updated/added (if UI implementation code is included)
- [ ] Integration/slow tests (if applicable)
- [x] Manual verification steps defined
  - Verify active/inactive/pressed/focus-visible tab states
  - Verify reduced-motion static fallback
  - Verify no visual distraction on Home/Plate/Progress flows

## CI Gates

- [ ] PR tests green (lint, type, unit)
- [ ] Diff coverage >= 97% on changed lines

## Visual Scope

- Prompt pack:
  - `docs/sora/prompts/hpp/p2_expressive/tab_bar_active_trail_micro_motion__tabbar__v1.0.md`
- Frontend path:
  - `frontend/src/components/TabBar.tsx`
- PR template base:
  - `.github/PULL_REQUEST_TEMPLATE/visuals.md`

## Prompt and Governance Checks

- [x] Prompt pack version set (`v1.0`)
- [x] Negative prompt constraints preserved
- [x] Matches `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md`
- [x] Matches `docs/sora/VISUAL_GOVERNANCE_INDEX.md`
- [x] Matches `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md`
- [x] Token policy aligned with `docs/design/TOKENS_SOT.md`

## Quality and Safety

- [ ] `docs/sora/SORA_STYLE_QA_CHECKLIST.md` pass documented on generated outputs
- [ ] `docs/design/LUXURY_UI_REVIEW_CHECKLIST.md` pass documented
- [x] Wellness-safe semantics confirmed (non-clinical)
- [x] No manipulative urgency/fear framing

## Marketing and GTM Notes

- ASO assets impacted: potential navigation polish screenshots (post-implementation)
- Product Hunt/social assets impacted: optional micro-motion demo clip
- Campaign dependency: none (keep behind feature toggle if rollout staged)

## Discussion Thread Pass

- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed

### Fixed in Commit Mapping

- No actionable review comments

## Merge Readiness (Mandatory)

- [ ] PR is non-draft only when truly ready for merge
- [ ] All required checks are green on latest commit
- [ ] No unresolved review threads
- [ ] No actionable bot comments remain unmapped
- [ ] Wait-window completed after latest bot/review activity

## Deferred / Follow-ups

- [ ] Ledger item(s): <link or None>
- [ ] GitHub issue(s): <link> (if any)

## Notes

Rollback / Feature flag:

- How to revert: revert PR commit(s) that integrate motion states
- Feature flag/toggle: recommended for gradual rollout of motion behavior

<!-- markdownlint-enable MD013 MD033 -->
