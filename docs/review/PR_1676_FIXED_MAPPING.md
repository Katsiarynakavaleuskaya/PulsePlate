<!-- markdownlint-disable MD013 MD034 -->
# PR 1676 Fixed In Commit Mapping

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1676>
- Branch: `codex/fix-indexerror-in-validate_source_artifact`
- Title: `fix(evidence): reject current-dir source artifacts`
- Runtime/test fix commit: `45840c3292e50f012dde8f44d944a29b07e4d476`
- Coordinator packet: `39a28b0fcb9f`

## Summary

PR #1676 keeps the Evidence Graph Runtime event validator fail-closed for
current-directory-like `source_artifact` values. The runtime change rejects
empty `PurePosixPath.parts` before any `parts[0]` access, and the tests cover
`.`, `./`, and `./.` as unsafe values that must raise `ValueError`.

## Scope

- `core/evidence/events.py`
- `tests/core/evidence/test_events.py`
- `docs/review/PR_1676_FIXED_MAPPING.md`

## Role Order

- [x] Declared role order preserved: `agent-coordinator -> backend-engineer -> architecture-specialist -> security-auditor -> qa-engineer-agent -> bug-hunter`
- [x] Post-open coordinator packet: `39a28b0fcb9f`
- [x] Mandatory post-open review lane included: `qa-engineer-agent -> bug-hunter`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

GraphQL review-thread check returned no review threads for PR #1676.

Review/bot status observed for PR head `45840c3292e50f012dde8f44d944a29b07e4d476`:

- CodeRabbit status check passed; CodeRabbit posted a walkthrough and a PR description checklist warning, with no code review thread requiring a code change.
- Sourcery posted a reviewer guide and a COMMENTED review saying the changes look good, with no actionable review thread.
- Cubic posted a COMMENTED review saying "No issues found" across the two changed files.
- Codecov reported all modified and coverable lines covered by tests.

Any future actionable human or bot thread must remain unresolved until one of
these dispositions is recorded:

- `FIXED` with a post-comment commit SHA and evidence.
- `NOT-A-BUG` with evidence.
- `DEFERRED` with a backlog link and PR-body follow-up note.

## Fixed in Commit Mapping

- No actionable review comments

## Premortem Summary

Frame: It is 48 hours after PR #1676 merged. The evidence-event validator
closeout failed or widened unexpectedly. Why?

- The validator could still raise `IndexError` if `parts[0]` was accessed before
  proving `parts` is non-empty. Mitigation: `core/evidence/events.py` checks
  `not parts` before the forbidden-root access.
- Current-directory values could be normalized into ambiguous source lineage.
  Mitigation: `.`, `./`, and `./.` are covered by the unsafe-source-artifact
  parametrization in `tests/core/evidence/test_events.py` and must raise
  `ValueError`.
- The bugfix could accidentally expand Evidence Graph Runtime semantics.
  Mitigation: the diff is limited to validator fail-closed behavior, regression
  tests, and this review-governance artifact.
- Mapping could substitute for the actual fix. Mitigation: the runtime/test fix
  already exists in commit `45840c3292e50f012dde8f44d944a29b07e4d476`; this
  artifact only satisfies the canonical Phase 2 review-governance contract.

## Bug-Hunter Pass

- Current-directory rejection: covered by unsafe inputs `.`, `./`, and `./.`.
- No `IndexError`: `parts` is checked for emptiness before `parts[0]`.
- Valid repo-relative artifacts: existing event tests continue to exercise
  repo-relative source artifacts such as `artifacts/rag_eval/...` and
  `evals/ragas/report.json`.
- Scope drift: no frontend, iOS, OpenAPI, router, billing, auth, deploy, design,
  token, dependency, RAG runtime, or semantic-cache surface is intentionally
  changed.

## Validation

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: post-open `task_bootstrap.py` -> packet `39a28b0fcb9f`

Additional bounded checks are recorded in the PR body and must be current-head
verified before any merge-readiness claim.

## Merge Readiness

- [ ] Current-head PR CI complete
- [ ] CodeRabbit no actionable comments
- [ ] Sourcery no actionable comments
- [ ] Cubic no actionable comments
- [ ] `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 1676` passes
- [ ] `python3 scripts/orchestration/check_merge_ready.py --require-auth --pr-number 1676 --repo Katsiarynakavaleuskaya/PulsePlate` passes
- [ ] Mandatory review cycle / wait-window elapsed

This artifact does not claim merge readiness. Before any merge-ready claim,
current-head CI, required checks, review-bot pass/no-actionables, unresolved
thread disposition, and the mandatory wait-window still apply.

## Deferred / Follow-Ups

None.
