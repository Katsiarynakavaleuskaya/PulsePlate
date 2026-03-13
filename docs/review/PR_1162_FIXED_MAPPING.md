# PR 1162 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: f8b3b4c64c145a365ef3a396c3a71f5cc17edfe3
Evidence: `tools/codex_skills/pulseplate-workflow/SKILL.md:48` now uses `${GITHUB_REPOSITORY:-<OWNER/REPO>}` instead of a hardcoded owner/repo pair, and `tools/codex_skills/pulseplate-workflow/SKILL.md:52` through `tools/codex_skills/pulseplate-workflow/SKILL.md:70` convert the merge-lane guidance into references to canonical runbook/contract sections instead of re-describing the policy inline.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1162#pullrequestreview-3947407420 -> f8b3b4c64c145a365ef3a396c3a71f5cc17edfe3

Disposition: FIXED
Commit: 4e2da5ad7d6921b6c2133817c0d70dbd7e80303b
Evidence: `AGENTS.md:1364` now uses the non-history-rewriting `new branch from origin/main + cherry-pick child commits` recovery flow, `RUNBOOK_AGENT.md:328` through `RUNBOOK_AGENT.md:334` align the stacked PR replacement runbook with that same policy, `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:223` removes the rebase wording from the contract matrix, and `docs/orchestration/workflow.md:347` no longer requires after-merge cleanup inside the pre-merge DoD checklist.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1162#pullrequestreview-3947420895 -> 4e2da5ad7d6921b6c2133817c0d70dbd7e80303b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1162#discussion_r2934174993 -> 4e2da5ad7d6921b6c2133817c0d70dbd7e80303b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1162#discussion_r2934182421 -> 4e2da5ad7d6921b6c2133817c0d70dbd7e80303b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1162#discussion_r2934182422 -> 4e2da5ad7d6921b6c2133817c0d70dbd7e80303b

Disposition: FIXED
Commit: 1d65d46f3a8045c74558769c3186ef0c728a19a0
Evidence: `RUNBOOK_AGENT.md:3` now reflects `2026-03-13 (PR #1162)` for accurate header provenance, `RUNBOOK_AGENT.md:294` through `RUNBOOK_AGENT.md:302` add explicit implementation provenance for live-triage behavior, `RUNBOOK_AGENT.md:334` through `RUNBOOK_AGENT.md:336` cite the non-history-rewriting replacement-flow implementation, and `tools/codex_skills/pulseplate-workflow/SKILL.md:55` through `tools/codex_skills/pulseplate-workflow/SKILL.md:65` plus `tools/codex_skills/pulseplate-workflow/SKILL.md:86` through `tools/codex_skills/pulseplate-workflow/SKILL.md:90` now record implementation provenance for the merge-readiness and post-merge cleanup rules.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1162#pullrequestreview-3947467854 -> 1d65d46f3a8045c74558769c3186ef0c728a19a0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1162#discussion_r2934220669 -> 1d65d46f3a8045c74558769c3186ef0c728a19a0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1162#discussion_r2934220677 -> 1d65d46f3a8045c74558769c3186ef0c728a19a0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1162#discussion_r2934220679 -> 1d65d46f3a8045c74558769c3186ef0c728a19a0

## Merge Readiness
- [x] Local gates passed on current head
- [ ] All required checks green
- [ ] All actionable review threads resolved with dispositions
- [ ] CodeRabbit PASS / no-actionables
- [x] Sourcery PASS / no-actionables
- [ ] Cubic PASS / no-actionables
- [ ] Wait-window after latest bot/review activity observed
