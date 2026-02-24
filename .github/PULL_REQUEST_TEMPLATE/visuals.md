<!-- markdownlint-disable MD003 MD022 MD032 MD033 MD041 -->

---
name: Visual Update
about: Design/system visual assets, prompts, and UI integration
labels: [design, frontend, sora]
---

# feat(visuals): <scope>

## Summary

- What visual element is updated and why.
- Product surface(s): Home / Plate / Progress / Setup / BMI / Pro / EnterKey.
- Linked source: `docs/design/VISUAL_ELEMENT_PROMPT_CATALOG.md`.

## Visual Scope

- Prompt pack file(s):
  - `docs/sora/prompts/hpp/<path>/<file>.md`
- Frontend integration path(s):
  - `frontend/src/...`
- Figma source references (if available):
  - `figma_design_url`
  - `figma_file_key`
  - `figma_node_id`

## Prompt and Governance Checks

- [ ] Prompt pack version set (`v1.0`, `v1.1`, etc.)
- [ ] Negative prompt constraints preserved
- [ ] Matches `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md`
- [ ] Matches `docs/sora/VISUAL_GOVERNANCE_INDEX.md`
- [ ] Matches `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md`
- [ ] Token policy aligned with `docs/design/TOKENS_SOT.md`

## Implementation Notes

- [ ] Reduced-motion fallback defined (if animation/motion is used)
- [ ] Readability verified (mobile + desktop)
- [ ] Small-size clarity verified (24/32 px where relevant)
- [ ] No raw-hex drift outside allowed token files

## Quality and Safety

- [ ] `docs/sora/SORA_STYLE_QA_CHECKLIST.md` pass documented
- [ ] `docs/design/LUXURY_UI_REVIEW_CHECKLIST.md` pass documented
- [ ] Wellness-safe (non-clinical) semantics confirmed
- [ ] No manipulative urgency/fear framing

## Marketing and GTM Notes

- ASO assets impacted: <yes/no + where>
- Product Hunt/social assets impacted: <yes/no + where>
- Campaign dependency: <if any>

## Test Plan

- [ ] Visual snapshot/screenshots attached
- [ ] Frontend checks run (if UI code changed)
  - [ ] `cd frontend && npm run lint`
  - [ ] `cd frontend && npm test`
  - [ ] `cd frontend && npm run build`
- [ ] Manual flow checks listed (state by state)

## Discussion Thread Pass
- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed

### Fixed in Commit Mapping
- `<review-comment-url>` -> `<commit-sha>`
- No actionable review comments

## Deferred / Follow-ups
- [ ] Ledger item(s): <link or None>
- [ ] GitHub issue(s): <link> (if any)

👉 Base PR policy template: [pull_request_template.md](../pull_request_template.md)

<!-- markdownlint-enable MD003 MD022 MD032 MD033 MD041 -->
