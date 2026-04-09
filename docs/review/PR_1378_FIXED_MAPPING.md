<!-- markdownlint-disable MD034 -->
# PR 1378 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1378#issuecomment-4209830092
  Disposition: NOT-A-BUG
  Evidence: Informational CodeRabbit draft-skip status comment only; no code or doc action requested.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1378#issuecomment-4209832933
  Disposition: NOT-A-BUG
  Evidence: Informational Sourcery reviewer-guide comment only; no actionable finding or requested change.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1378#discussion_r3056080059
  Disposition: FIXED
  Commit: `08b4a6050`
  Evidence: `docs/roadmap/BACKLOG_LEDGER.md` now adds anchor `ledger-p1-reconcile-open-dependabot-alerts` and splits child reconciliation lanes for alerts `#100`, `#99-#95`, `#94`, and `#93-#92`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1378#discussion_r3056080077
  Disposition: NOT-A-BUG
  Evidence: `docs/security/CRYPTOGRAPHY_46_0_7_PRIVATE_INDEX_ADVISORY.md:1` keeps the patched `46.0.7` floor and documents the mirror-lag blocker; `docs/review/PR_1378_FIXED_MAPPING.md:20` keeps merge-readiness unchecked until current-head CI is green.

## Merge Readiness

- [ ] All required checks pass (GitHub CI on current PR head after each push)
- [ ] No unresolved review threads
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
- [ ] `make verify` green locally

### Scope Notes

- Keep this PR limited to dependency and security remediation for npm overrides and the `cryptography 46.0.7` patched floor plus its exact-wheel fallback.
- Keep the backlog note for open Dependabot alert reconciliation on `main`.
- Do not mix any `rag` / `insight` lane changes into this PR.

### Local Verification

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `pytest -q tests/test_dependency_security_guard.py`
- `pre-commit run --all-files`
- `make verify`
- `git push -u origin repair/hono-security`

Notes: Mirror `## Discussion Thread Pass`, `## Fixed in Commit Mapping`, and `## Merge Readiness` in the PR body as review activity appears.

<!-- markdownlint-enable MD034 -->
