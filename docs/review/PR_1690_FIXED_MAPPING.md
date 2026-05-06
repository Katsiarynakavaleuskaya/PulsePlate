# PR #1690 Fixed Mapping

## Summary

Canonical Codecov token-exposure fix. PR #1691 is a duplicate and must not be
merged after #1690 lands.

## Machine-Heavy Deferral

Full `make verify` intentionally not run per operator-approved batch
instruction. This PR uses bounded checks and `make validate-changed`.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

- GitHub review-thread GraphQL inspection found no review threads for PR #1690.
- CodeRabbit completed review with no actionable findings.
- Sourcery and cubic produced summary/reviewer-guide comments only; no actionable
  Codecov fix request was present.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1690 -> e1f351b2adfef854529c8dc62c1e1aaeb4a3b40b
Disposition: FIXED
Commit: e1f351b2adfef854529c8dc62c1e1aaeb4a3b40b
Evidence: Internal premortem findings are fixed by `tests/test_python_supply_chain_controls.py::test_frontend_build_keeps_codecov_token_out_of_branch_controlled_build`; `.github/workflows/frontend-ci.yml` keeps `CODECOV_TOKEN` out of `Build frontend`; `frontend/vite.config.ts` omits `uploadToken` and `process.env.CODECOV_TOKEN`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1690#pullrequestreview-4238084481
Disposition: NOT-A-BUG
Evidence: Sourcery generated a reviewer guide and did not leave an actionable Codecov fix request for PR #1690.
Reason: Reviewer-guide comments are advisory context, not code defects.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1691
Disposition: NOT-A-BUG
Evidence: PR #1691 has the same title, changed files, and head SHA `38938e599795f9983a2768ac43cde317132cc849`; it will be closed after #1690 merges with an explicit duplicate comment.
Reason: Duplicate PR closure is batch hygiene, not a defect in PR #1690.

## Merge Readiness

Strict readiness must be run before merge:

```bash
GH_TOKEN=$(gh auth token) GITHUB_TOKEN=$(gh auth token) \
python3 scripts/orchestration/check_merge_ready.py \
  --pr-number 1690 \
  --repo Katsiarynakavaleuskaya/PulsePlate \
  --require-auth
```
