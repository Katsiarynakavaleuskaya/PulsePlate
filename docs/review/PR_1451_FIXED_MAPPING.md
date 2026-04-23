# PR #1451 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:79-82`.

Current GitHub review surface for PR `#1451` was re-checked on `23 April 2026`:

- `reviewThreads`: original three actionable inline threads plus one CodeRabbit
  follow-up thread after the first merge-ready push
- actionable Sourcery review identified by Sourcery:
  `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1451#pullrequestreview-4131518820`
- actionable inline comments on current head:
  `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1451#discussion_r3102747673`,
  `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1451#discussion_r3102747787`,
  `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1451#discussion_r3102790380`
- actionable Cubic review identified by cubic:
  `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1451#pullrequestreview-4131575203`
- informational / non-actionable bot comments:
  `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1451#issuecomment-4270679765`,
  `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1451#pullrequestreview-4131519004`,
  `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1451#issuecomment-4270680915`,
  `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1451#issuecomment-4270724458`
- CodeRabbit follow-up on the merge-ready push:
  `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1451#discussion_r3133000980`

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1451#discussion_r3102747673 -> 213c85449fbae42b412a475d0743369bb931c571
Disposition: FIXED
Commit: 213c85449fbae42b412a475d0743369bb931c571
Evidence: `tests/test_dependency_security_guard.py:179-187` keeps blocked-package detection on `_packages_present_in_file(...)`, while `tests/test_dependency_security_guard.py:311-322` proves both unpinned and pinned blocked-package coverage. Local proof: `python3 -m pytest -q tests/test_dependency_security_guard.py`, `pre-commit run --all-files`, and `make verify` all passed after this commit.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1451#discussion_r3102747787 -> 213c85449fbae42b412a475d0743369bb931c571
Disposition: FIXED
Commit: 213c85449fbae42b412a475d0743369bb931c571
Evidence: `tests/test_dependency_security_guard.py:102-125` now skips dash-prefixed pip directives before parsing, and `tests/test_dependency_security_guard.py:346-352` locks the `-i` / `-f` regression with a dedicated temp-requirements test. Local proof: `python3 -m pytest -q tests/test_dependency_security_guard.py`, `pre-commit run --all-files`, and `make verify` all passed after this commit.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1451#discussion_r3102790380 -> 213c85449fbae42b412a475d0743369bb931c571
Disposition: FIXED
Commit: 213c85449fbae42b412a475d0743369bb931c571
Evidence: `tests/test_dependency_security_guard.py:136-186` now canonicalizes package-name comparisons with `_normalized_package_name(...)`, and `tests/test_dependency_security_guard.py:325-332` proves `_`, `.`, and `-` aliases collapse to the same blocked package identity. Local proof: `python3 -m pytest -q tests/test_dependency_security_guard.py`, `pre-commit run --all-files`, and `make verify` all passed after this commit.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1451#pullrequestreview-4131518820
Disposition: NOT-A-BUG
Evidence: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1451#discussion_r3102747673`
Reason: the aggregate Sourcery review shell only wraps the same pinned-vs-unpinned testing request already dispositioned as `FIXED` in the inline thread above; it does not add a separate defect once that inline comment is mapped with proof.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1451#pullrequestreview-4131575203
Disposition: NOT-A-BUG
Evidence: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1451#discussion_r3102790380`
Reason: the aggregate Cubic review shell repeats the same normalization defect already identified by cubic in the inline thread above; no separate unresolved obligation remains once that inline comment is mapped with proof.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1451#discussion_r3133000980 -> cb665b37ab5c49b6a613c6540076a0765c9ac5fb
Disposition: FIXED
Commit: cb665b37ab5c49b6a613c6540076a0765c9ac5fb
Evidence: `tests/test_dependency_security_guard.py:200-203` and `tests/test_dependency_security_guard.py:372-375` now read canonicalized package-name keys with `_normalized_package_name(pkg)`, matching the way `_effective_min_versions_per_package(...)` stores keys. Regression coverage in `tests/test_dependency_security_guard.py:335-343` and `tests/test_dependency_security_guard.py:386-395` proves alias-equivalent schema lookups for both minimum-version and blocked-version guard paths. Local proof before mapping: `python3 -m pytest -q tests/test_dependency_security_guard.py`.

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Current-head CI is green for PR branch head
  Evidence: `AGENTS.md:42-49`;
  `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:95-112`.
- [ ] Required checks complete (no pending jobs)
  Evidence: `AGENTS.md:46-49`;
  `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:155-163`.
- [ ] All review threads resolved on GitHub after disposition updates
  Evidence: actionable current-head threads are dispositioned above but still
  require explicit GitHub resolution after the updated branch head is pushed.
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: current actionable review shells and inline comments are mapped in
  `## Fixed in Commit Mapping`; final merge gate still requires a fresh
  current-head re-check after push.
- [ ] Pre-commit green on latest pushed head
  Evidence: local `pre-commit run --all-files` on the latest PR head.
- [ ] `make verify` green on latest pushed head
  Evidence: `AGENTS.md:1-16`;
  `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:175-180`.

## Deferred / Follow-ups

- Add entries here only after a `DEFERRED` disposition is chosen above; each
  follow-up must reuse the same ledger anchor recorded in `Fixed in Commit
  Mapping`.
