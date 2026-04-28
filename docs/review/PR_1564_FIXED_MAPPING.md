# PR #1564 Fixed Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1564>
Branch: `codex/docker-ci-ledger-closeout`
Date: 2026-04-28

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Artifact status: PR-open governance artifact exists for the Docker/CI ledger
closeout lane. No actionable review threads were present when this artifact was
created.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 8a61b46d4
Evidence: `docs/roadmap/BACKLOG_LEDGER.md` now keeps Docker/CI ledger `Status` values terse (`Landed` / `Blocked`) and moves explanatory closeout text into `Reason`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1564#pullrequestreview-4192132647 -> 8a61b46d4

Disposition: FIXED
Commit: 8a61b46d4
Evidence: `docs/roadmap/BACKLOG_LEDGER.md` removes the closed entitlement ledger item from the active SBOM/VEX `Blocked by` list and keeps release-truth closure as the active blocker.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1564#discussion_r3156967592 -> 8a61b46d4

Disposition: FIXED
Commit: 8a61b46d4
Evidence: this CodeRabbit review summary contained the active stale-blocker thread mapped above; commit hooks also re-ran `fix end of files` and passed for the final-newline nitpick.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1564#pullrequestreview-4192147292 -> 8a61b46d4

## Initial Evidence

- `python3 scripts/orchestration/check_preflight.py` (PASS)
- `python3 scripts/orchestration/check_agent_consistency.py` (PASS)
- `pre-commit run --all-files` (PASS)
- `pytest -q tests/test_repo_policy_guards.py` (PASS, 13 passed)
- `python3 scripts/ci/check_docs_phase1_gates.py --files docs/roadmap/BACKLOG_LEDGER.md docs/deploy/DOCKER.md` (PASS)
- `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python make validate-changed` (PASS; no Python files changed)
- `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python make validate-min` (PASS)
- commit hooks during `git commit` (PASS)
- pre-push hooks during `git push` (PASS)

## Machine-Heavy Local Gate Deferral

Full local `make verify` was not run for this docs/governance narrow-gate PR.
Merge readiness must rely on the PR-scoped local gates above plus current-head
GitHub CI parity before any readiness claim.

## Deferred / Follow-ups

- SBOM/VEX signed security artifacts remain blocked until P0 release-truth
  closure and a dedicated packet approves rollout.
- Dagger remains P2 deferred/evaluation-only; this PR does not enable a new CI
  control plane.

## Merge Readiness

- [ ] CI green on current head
- [ ] No unresolved actionable review threads
- [ ] CodeRabbit/Sourcery/Cubic statuses reviewed and mapped
- [ ] Fixed-mapping artifact and PR body mirror aligned
- [ ] `check_merge_ready.py --require-auth` PASS
