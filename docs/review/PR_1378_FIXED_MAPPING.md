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
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1378#pullrequestreview-4080339795
  Disposition: NOT-A-BUG
  Evidence: General Sourcery future-hardening suggestions only; current PR remains intentionally scoped to the active blocker documented in `docs/security/CRYPTOGRAPHY_46_0_7_PRIVATE_INDEX_ADVISORY.md:5` and the narrow-scope guard in `docs/review/PR_1378_FIXED_MAPPING.md:34`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1378#pullrequestreview-4080362047
  Disposition: NOT-A-BUG
  Evidence: Review-container URL only; its actionable items are already dispositioned at `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1378#discussion_r3056080059` and `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1378#discussion_r3056080077`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1378#pullrequestreview-4081271826
  Disposition: FIXED
  Commit: `d7bd8daba`
  Evidence: `Dockerfile:248` now copies `scripts/ci/emergency_python_wheels.json`, and `Dockerfile:264` plus `Dockerfile:275` pass `--emergency-wheel-manifest` in both development-stage install branches.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1378#discussion_r3056871964
  Disposition: FIXED
  Commit: `d7bd8daba`
  Evidence: `docs/security/CRYPTOGRAPHY_46_0_7_PRIVATE_INDEX_ADVISORY.md:17`, `docs/security/CRYPTOGRAPHY_46_0_7_PRIVATE_INDEX_ADVISORY.md:34`, and `docs/security/CRYPTOGRAPHY_46_0_7_PRIVATE_INDEX_ADVISORY.md:56` add concrete `file:line` anchors.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1378#pullrequestreview-4081276804
  Disposition: FIXED
  Commit: `d7bd8daba`
  Evidence: The issue identified by cubic is closed by strict date-format enforcement at `scripts/ci/install_locked_python_requirements.py:236` and the regression test at `tests/test_install_locked_python_requirements.py:322`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1378#discussion_r3056876895
  Disposition: FIXED
  Commit: `d7bd8daba`
  Evidence: `scripts/ci/install_locked_python_requirements.py:238` now rejects non-canonical date forms before parsing, and `tests/test_install_locked_python_requirements.py:345` asserts the failure mode.

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
