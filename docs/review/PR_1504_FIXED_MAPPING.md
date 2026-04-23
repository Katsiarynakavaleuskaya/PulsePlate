# PR 1504 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: babb035c1
Evidence: `frontend/src/components/ui/Checkbox.tsx`, `frontend/src/components/ui/RadioGroup.tsx`, `frontend/src/components/ui/Tooltip.tsx`, `frontend/src/components/ui/DropdownMenu.tsx`, `frontend/src/components/ui/__tests__/Checkbox.test.tsx`, `frontend/src/components/ui/__tests__/RadioGroup.test.tsx`, `frontend/src/components/ui/__tests__/Tooltip.test.tsx`, `frontend/src/components/ui/__tests__/DropdownMenu.test.tsx`
Reason: Mandatory `bug-hunter` review found four primitive API/a11y gaps: invalid `RadioGroup` error idrefs, tooltip `aria-describedby` overwrite, missing checkbox indeterminate support, and no link-capable dropdown menu item. Commit `babb035c1` fixed those surfaces and expanded targeted tests.

Disposition: FIXED
Commit: TBD
Evidence: `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR1_MISSING_GOVERNED_PRIMITIVES_PACKET_2026-04-23.md`, `frontend/src/components/ui/RadioGroup.tsx`, `frontend/src/components/ui/__tests__/RadioGroup.test.tsx`
Reason: Mandatory `qa-engineer-agent` review found PR size governance missing split justification and a radiogroup accessible-name gap. This follow-up commit adds the split justification and wires `aria-labelledby` to the radiogroup role.

## Merge Readiness

- [ ] All required checks pass
  Evidence target: `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:179-213`
- [ ] No unresolved review threads
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence target: `docs/orchestration/COORDINATOR_MERGE_READINESS_RULES.md:11-17`
- [x] Pre-commit green
  Evidence: `pre-commit run --all-files` passed locally before initial push.
- [ ] `make verify` green
  Evidence target: `AGENTS.md:5-16`
- [x] Mandatory post-open `qa-engineer-agent -> bug-hunter` pass completed
  Evidence target: `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:98-103`

Notes: This PR remains draft. Merge-readiness is intentionally not claimed.
