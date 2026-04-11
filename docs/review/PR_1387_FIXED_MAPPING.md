# PR 1387 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: NOT-A-BUG
Evidence: `scripts/orchestration/review_mapping_artifact.py:31` and `scripts/orchestration/review_mapping_artifact.py:106` require the exact lowercase checkbox text `- [x] Fixed in commit mapping completed`, while `scripts/orchestration/check_review_threads_disposition.py:107` and `scripts/orchestration/check_review_threads_disposition.py:347` explicitly accept FIXED commit proofs in the 7–40 hex SHA range. Changing the artifact to Sourcery's preferred capitalization would break the canonical phase2 gate, and expanding `e3a883693` to 40 chars is optional hardening rather than a repo-policy defect.
Reason: Both bot nitpicks conflict with or exceed the enforced repository contract, so the artifact stays on the canonical lowercase checkbox text and on an accepted 9-character commit SHA shorthand.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1387#discussion_r3067642298
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1387#pullrequestreview-4093446469
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1387#pullrequestreview-4093460979

Disposition: FIXED
Commit: e3a883693
Evidence: `app/security/goplus_agentguard_bridge.py:33`, `app/security/goplus_agentguard_bridge.py:73`, `tests/test_agent_input_guard.py:377`, `tests/test_agent_input_guard.py:398`, `docs/review/PR_1387_FIXED_MAPPING.md:12`, `docs/review/PR_1387_FIXED_MAPPING.md:35`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1387#discussion_r3067644214 -> e3a883693
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1387#discussion_r3067644215 -> e3a883693
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1387#discussion_r3067644216 -> e3a883693
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1387#discussion_r3067644217 -> e3a883693
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1387#discussion_r3067646807 -> e3a883693
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1387#discussion_r3067646808 -> e3a883693
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1387#pullrequestreview-4093448349 -> e3a883693
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1387#pullrequestreview-4093450789 -> e3a883693

Disposition: FIXED
Commit: 0644dc260
Evidence: `docs/review/PR_1387_FIXED_MAPPING.md:34`, `docs/review/PR_1387_FIXED_MAPPING.md:35`, `app/AGENTS.md:298`, `tests/AGENTS.md:525`, and `git log --oneline origin/main..HEAD` includes `372193eb1 docs(agents): update instructions`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1387#discussion_r3067658197 -> 0644dc260
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1387#pullrequestreview-4093462354 -> 0644dc260
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1387#pullrequestreview-4093464046 -> 0644dc260

## Merge Readiness

- [x] All required checks pass (current head)
- [x] No unresolved review threads (re-check before merge)
- [x] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [x] Required docs commit present: `docs(agents): update instructions`
- [x] Pre-commit green on latest push
- [x] `make verify` green where required for merge
- [x] Mandatory post-open **qa-engineer-agent** pass completed
- [x] Mandatory post-open **bug-hunter** pass completed (latest-head artifact/body/runtime diff re-review found no blocking findings beyond the already-mapped bridge/test comments)
- [x] **backend-engineer** scoped review completed (`Mencius`)
- [x] **security-auditor** scoped review completed (`Boole`)

## Notes

Current-head strict wrappers are green on this lane: `make verify`, review-thread
disposition, and merge-readiness all pass on the latest branch head. Narrative
lock for this PR: the slowdown was not "the last 2-3 PRs broke Python tests" —
an older py313 sequential-only CI contract amplified a pre-existing expensive
Node subprocess hot path in `app/security/goplus_agentguard_bridge.py`. `#1384`
made the local Node scanner the active runtime/test seam on `main`; `#1387`
remains the root-fix lane because it removes that live bridge cost from the
default test runtime. `tests/conftest.py` already sets `TESTING=true` during
pytest bootstrap, so current evidence does not justify a separate CI env patch.
Latest PR-side `CI` rerun `24288236911` is green, and `main` is stabilized after
merge `#1392` with green `CI` run `24286369504`. `gh pr checks 1387` may still
show historical failed push run `24281080918`, but that failure is superseded
history rather than current-head PR truth.
