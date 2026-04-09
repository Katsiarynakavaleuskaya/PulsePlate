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

## Merge Readiness

- [ ] All required checks pass (GitHub CI on current PR head after each push)
- [ ] No unresolved review threads
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [x] Pre-commit green
- [x] `make verify` green locally

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
