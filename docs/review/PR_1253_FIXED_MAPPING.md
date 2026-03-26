# PR 1253 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: 5b0bf7a9
Evidence: docs/review/PR_1250_FIXED_MAPPING.md:8
Reason: Carryover evidence from the conflicted replacement-source PR remains valid for the clean-topology rebuild and preserves the already-fixed review item on the active lane.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1250#discussion_r2997499001 -> 5b0bf7a9

Disposition: FIXED
Commit: 777c4465
Evidence: docs/review/PR_1250_FIXED_MAPPING.md:9
Reason: The replacement PR keeps the original carryover fixes for the paired review comments that were already addressed before the clean-topology rebuild.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1250#discussion_r2997517780 -> 777c4465
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1250#discussion_r2997517784 -> 777c4465

Disposition: FIXED
Commit: b86ef645
Evidence: scripts/ci/ci_risk_profile.py:50, tests/test_ci_risk_profile.py:76
Reason: The PR3 risk-profile follow-up fixes expanded workflow-privileged and merge-governance coverage so the replacement branch routes `.github/scripts`, PR-template changes, and governance tests deterministically.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1253#discussion_r2997748282 -> b86ef645
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1253#discussion_r2997758754 -> b86ef645
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1253#discussion_r2997774639 -> b86ef645
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1253#discussion_r2997774646 -> b86ef645
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1253#pullrequestreview-4017431658 -> b86ef645
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1253#pullrequestreview-4017459025 -> b86ef645

Disposition: FIXED
Commit: 0998259a
Evidence: scripts/ci/check_pr_size_governance.py:21, tests/test_check_pr_size_governance.py:44
Reason: The PR-size governance parser now handles the CodeRabbit follow-up cases deterministically, including nested headings, HTML comments, placeholder bullets, and governed missing-value failures.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1253#discussion_r2997781420 -> 0998259a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1253#discussion_r2997781428 -> 0998259a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1253#discussion_r2997781431 -> 0998259a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1253#discussion_r2997781439 -> 0998259a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1253#discussion_r2997781440 -> 0998259a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1253#discussion_r2997781444 -> 0998259a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1253#discussion_r2997781448 -> 0998259a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1253#discussion_r2997781452 -> 0998259a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1253#pullrequestreview-4017466061 -> 0998259a

## Carryover Notes
- Historical closed replacement-source PR `#1248` remains referenced only as supporting evidence in `docs/review/PR_1248_FIXED_MAPPING.md`.
- The conflicted replacement-source artifact remains preserved in `docs/review/PR_1250_FIXED_MAPPING.md`.

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
- [ ] `make verify` green
- [ ] Canonical `pull_request` validation restored on replacement PR `#1253`.
Notes: pre-commit passed, `make verify` passed, and canonical `pull_request` validation is restored on PR `#1253`; the checklist stays unchecked until the final merge cycle.
