# PR 1504 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: babb035c1
Evidence: `frontend/src/components/ui/Checkbox.tsx`, `frontend/src/components/ui/RadioGroup.tsx`, `frontend/src/components/ui/Tooltip.tsx`, `frontend/src/components/ui/DropdownMenu.tsx`, `frontend/src/components/ui/__tests__/Checkbox.test.tsx`, `frontend/src/components/ui/__tests__/RadioGroup.test.tsx`, `frontend/src/components/ui/__tests__/Tooltip.test.tsx`, `frontend/src/components/ui/__tests__/DropdownMenu.test.tsx`
Reason: Mandatory `bug-hunter` review found four primitive API/a11y gaps: invalid `RadioGroup` error idrefs, tooltip `aria-describedby` overwrite, missing checkbox indeterminate support, and no link-capable dropdown menu item. Commit `babb035c1` fixed those surfaces and expanded targeted tests.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1504 -> babb035c1

Disposition: FIXED
Commit: 6eb383fad
Evidence: `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR1_MISSING_GOVERNED_PRIMITIVES_PACKET_2026-04-23.md`, `frontend/src/components/ui/RadioGroup.tsx`, `frontend/src/components/ui/__tests__/RadioGroup.test.tsx`
Reason: Mandatory `qa-engineer-agent` review found PR size governance missing split justification and a radiogroup accessible-name gap. This follow-up commit adds the split justification and wires `aria-labelledby` to the radiogroup role.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1504 -> 6eb383fad

Disposition: FIXED
Commit: 4fb326f52
Evidence: `frontend/src/components/ui/DropdownMenu.tsx`, `frontend/src/components/ui/RadioGroup.tsx`, `frontend/src/components/ui/fieldState.ts`, `frontend/src/components/ui/Select.tsx`, `frontend/src/components/ui/Textarea.tsx`, `frontend/src/components/ui/Checkbox.tsx`, `frontend/src/components/ui/__tests__/RadioGroup.test.tsx`
Reason: Sourcery and Codex post-ready reviews found Headless UI `MenuItem` render-prop drift (`focus` vs `active`), duplicated invalid-state helpers, redundant radiogroup role semantics, and an optional-legend unlabeled group path. Commit `4fb326f52` switches menu styling to `active`, extracts shared invalid-state handling, relies on native `fieldset`/`legend`, and makes `legend` required.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1504#discussion_r3131365659 -> 4fb326f52
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1504#discussion_r3131365664 -> 4fb326f52
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1504#discussion_r3131393172 -> 4fb326f52
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1504#pullrequestreview-4163091179 -> 4fb326f52

Disposition: FIXED
Commit: 6d139bd3b
Evidence: `docs/review/PR_1504_FIXED_MAPPING.md`, `docs/roadmap/BACKLOG_LEDGER.md`, `frontend/src/components/design-system/ExperiencePanels.tsx`, `frontend/src/components/ui/DropdownMenu.tsx`, `frontend/src/components/ui/RadioGroup.tsx`, `frontend/src/components/ui/Tooltip.tsx`, `frontend/src/components/ui/fieldState.ts`, `frontend/src/components/ui/__tests__/DropdownMenu.test.tsx`, `frontend/src/components/ui/__tests__/RadioGroup.test.tsx`, `frontend/src/components/ui/__tests__/Tabs.test.tsx`, `frontend/src/components/ui/__tests__/Tooltip.test.tsx`
Reason: CodeRabbit post-open review found premature merge-readiness checkboxes, missing mock cleanup/return types, separator semantics, incomplete `aria-invalid` token handling, missing radio invalid propagation, persistent tooltip idref risk, and typed-state/test assertion gaps. Commit `6d139bd3b` fixes those surfaces and re-runs `pre-commit run --all-files`, `npm run build`, and the targeted primitive test bundle.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1504#discussion_r3131623394 -> 6d139bd3b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1504#discussion_r3131623398 -> 6d139bd3b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1504#discussion_r3131623430 -> 6d139bd3b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1504#discussion_r3131623444 -> 6d139bd3b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1504#discussion_r3131623467 -> 6d139bd3b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1504#pullrequestreview-4163397266 -> 6d139bd3b

Disposition: NOT-A-BUG
Evidence: `frontend/src/components/ui/*.tsx` exports are typed React component contracts; `pre-commit run --all-files`, `cd frontend && npm run build`, and targeted primitive Vitest/a11y coverage passed locally.
Reason: CodeRabbit issue comment warning for generic docstring coverage is not a repo merge gate for these frontend TSX primitives and would add noisy comments rather than improve governed component behavior. Repo-local quality gates and explicit type/test coverage are the binding PR-1 evidence.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1504#issuecomment-4304646486

Disposition: FIXED
Commit: 6a5cc359e
Evidence: `frontend/src/components/design-system/ExperiencePanels.tsx`, `frontend/src/components/ui/Checkbox.stories.tsx`, `frontend/src/components/ui/RadioGroup.stories.tsx`
Reason: CodeRabbit follow-up review requested explicit story event types and checked narrowing instead of direct union casts in showcase handlers. Commit `6a5cc359e` adds `ChangeEvent` annotations and value guards before state updates.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1504#pullrequestreview-4164259363 -> 6a5cc359e

## Merge Readiness

- [x] All required checks pass
  Evidence: Current-head CI for `3923ec1bf` passed all substantive required jobs; only the pre-final merge-readiness gate was red before this readiness artifact update.
- [x] No unresolved review threads
  Evidence: GitHub GraphQL review-thread query returned no unresolved threads after Sourcery, Codex, and CodeRabbit dispositions were mapped.
- [x] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: Sourcery, Codex, and CodeRabbit inline comments are mapped above; CodeRabbit issue-level docstring warning is classified as NOT-A-BUG with repo-gate evidence.
- [x] Pre-commit green
  Evidence: `pre-commit run --all-files` passed locally before the latest push; pre-push hooks also passed on `3923ec1bf`.
- [x] `make verify` green
  Evidence: `make verify` passed locally on 2026-04-23 with verify-env, flake8, mypy, smoke tests, full coverage run, and diff-cover.
- [x] Mandatory post-open `qa-engineer-agent -> bug-hunter` pass completed
  Evidence: Post-open QA and bug-hunter findings are mapped above to `babb035c1`, `6eb383fad`, `4fb326f52`, and `6d139bd3b`.

Notes: Coordinator moved this lane to merge-ready evidence collection after local `make verify`, current-head CI, review-thread disposition, and bot-actionable mapping were complete. Final merge still requires the strict merge-ready wrapper to pass on the post-artifact-update head.
