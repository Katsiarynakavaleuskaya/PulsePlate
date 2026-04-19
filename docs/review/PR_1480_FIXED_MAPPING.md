# PR #1480 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:58-60`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact is created immediately after lane setup per repo governance.
Record every new review or bot disposition here before resolving threads on
GitHub.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1480
Disposition: NOT-A-BUG
Evidence: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1480`
Reason: At artifact initialization time the live PR surface had no actionable human or bot review threads yet; any later actionables must be appended here before thread resolution.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1480#pullrequestreview-4136381333 -> f8cfa3a999787e161caeadb9bd8d5378e705f970
Disposition: FIXED
Evidence: `requirements-dev.in:29`
Reason: Sourcery requested a stricter mypy constraint so future lock refreshes cannot drift back to the broken `1.20.1` patch; the exact pin landed in commit `f8cfa3a999787e161caeadb9bd8d5378e705f970`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1480#pullrequestreview-4136383224 -> f8cfa3a999787e161caeadb9bd8d5378e705f970
Disposition: FIXED
Evidence: `requirements-dev.in:29`
Reason: cubic identified that `~=1.20.0` still permits `1.20.1`; the exact pin landed in commit `f8cfa3a999787e161caeadb9bd8d5378e705f970`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1480#discussion_r3107311707 -> f8cfa3a999787e161caeadb9bd8d5378e705f970
Disposition: FIXED
Evidence: `requirements-dev.in:29`
Reason: cubic inline review requested `mypy==1.20.0`; the exact pin landed in commit `f8cfa3a999787e161caeadb9bd8d5378e705f970`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1480#discussion_r3107312193 -> f8cfa3a999787e161caeadb9bd8d5378e705f970
Disposition: FIXED
Evidence: `requirements-dev.in:29`
Reason: Codex inline review raised the same recurrence risk; the exact pin landed in commit `f8cfa3a999787e161caeadb9bd8d5378e705f970`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1480#pullrequestreview-4136437409
Disposition: NOT-A-BUG
Evidence: `docs/orchestration/DEPENDABOT_PR_1480_FRONTEND_CI_MYPY_HOTFIX_PACKET_2026-04-19.md:12-34`; `docs/orchestration/DEPENDABOT_PR_1480_FRONTEND_CI_MYPY_HOTFIX_PACKET_2026-04-19.md:36-56`
Reason: The current packet already contains the requested file:line evidence anchors and the canonical lane ordering; CodeRabbit's own latest review state marks these items as addressed across commits `46fe391b5..b9e970fae`, so the live document is now correct.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1480#discussion_r3107379709
Disposition: NOT-A-BUG
Evidence: `docs/orchestration/DEPENDABOT_PR_1480_FRONTEND_CI_MYPY_HOTFIX_PACKET_2026-04-19.md:12-34`
Reason: The packet's `Current Truth` section now includes explicit file:line evidence pointers for each asserted fact, so no additional packet change is required.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1480#discussion_r3107379711
Disposition: NOT-A-BUG
Evidence: `docs/orchestration/DEPENDABOT_PR_1480_FRONTEND_CI_MYPY_HOTFIX_PACKET_2026-04-19.md:38-56`
Reason: The packet already reconciles the lane to the canonical `agent-coordinator -> backend-engineer -> security-auditor` ordering while preserving the mandatory `qa-engineer-agent -> bug-hunter` post-open pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1480#pullrequestreview-4136490743 -> d2b45c36438d3bd13068c5f2f74ee291c023217c
Disposition: FIXED
Evidence: `docs/review/PR_1480_FIXED_MAPPING.md:107-110`
Reason: cubic identified a real contradiction between the pending canonical `## Merge Readiness` checklist and the earlier note that said validation had already passed; commit `d2b45c36438d3bd13068c5f2f74ee291c023217c` removed that conflicting merge-readiness claim.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1480#discussion_r3107441386 -> d2b45c36438d3bd13068c5f2f74ee291c023217c
Disposition: FIXED
Evidence: `docs/review/PR_1480_FIXED_MAPPING.md:107-110`
Reason: cubic found the same merge-readiness contradiction on the inline note at line 103; commit `d2b45c36438d3bd13068c5f2f74ee291c023217c` replaced it with a neutral statement that defers final truth to the checklist above.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1480#pullrequestreview-4136602523 -> 096ddf9c413032055cd56d690f509676c21bc6b8
Disposition: FIXED
Evidence: `docs/review/PR_1480_FIXED_MAPPING.md:86-109`
Reason: CodeRabbit's review summary reported that the `## Notes` block still contained unsupported truth claims; commit `096ddf9c413032055cd56d690f509676c21bc6b8` rewrote that section to use only evidence-backed bullets with explicit `file:line` anchors.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1480#discussion_r3107562893 -> 096ddf9c413032055cd56d690f509676c21bc6b8
Disposition: FIXED
Evidence: `docs/review/PR_1480_FIXED_MAPPING.md:86-109`
Reason: The inline CodeRabbit finding requested `file:line` anchors for the factual claims in `## Notes`; commit `096ddf9c413032055cd56d690f509676c21bc6b8` added those anchors and removed the uncited live-session assertions.

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Current-head CI is green for PR branch head
  Evidence: pending
- [ ] Required checks complete (no pending jobs)
  Evidence: pending
- [ ] All review threads resolved on GitHub after disposition updates
  Evidence: pending
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: pending
- [ ] Pre-commit green on latest pushed head
  Evidence: pending
- [ ] `make verify` green on latest pushed head
  Evidence: pending

## Notes

- The pre-remediation PR metadata snapshot for this lane is preserved in the
  coordinator packet's `Current Truth` block.
  Evidence:
  `docs/orchestration/DEPENDABOT_PR_1480_FRONTEND_CI_MYPY_HOTFIX_PACKET_2026-04-19.md:10-17`
- Current-head CI triage must ignore superseded cancelled runs and stale runs;
  only the latest current-head view from the strict merge tooling is canonical.
  Evidence: `RUNBOOK_AGENT.md:448-450`;
  `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-163`
- This lane remains a narrow mypy hotfix; no adjacent dependency or CI redesign
  is in scope.
  Evidence:
  `docs/orchestration/DEPENDABOT_PR_1480_FRONTEND_CI_MYPY_HOTFIX_PACKET_2026-04-19.md:3-8`;
  `docs/orchestration/DEPENDABOT_PR_1480_FRONTEND_CI_MYPY_HOTFIX_PACKET_2026-04-19.md:58-74`
- The failure path addressed by this lane is the Frontend CI backend-dependency
  install step, and the remediation is the exact mypy rollback / pin.
  Evidence: `.github/workflows/frontend-ci.yml:121`; `requirements-dev.in:29`;
  `requirements-dev.txt:110`; `requirements-lock.txt:227`
- Validation commands for the lane are fixed by the packet, while merge truth is
  recorded only in the checklist above after the latest head is revalidated.
  Evidence:
  `docs/orchestration/DEPENDABOT_PR_1480_FRONTEND_CI_MYPY_HOTFIX_PACKET_2026-04-19.md:98-107`;
  `docs/review/PR_1480_FIXED_MAPPING.md:59-76`
