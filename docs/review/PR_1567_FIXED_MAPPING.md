# PR #1567 Fixed Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1567>
Branch: `codex/compose-v2-command-surface`
Date: 2026-04-29

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Artifact status: PR-open governance artifact exists for the Compose v2 command
surface migration lane. No actionable review threads were present when this
artifact was created.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: ba1a4f633
Evidence: `scripts/design/verify_design.py` defines `STATUS_ICONS` once at module scope and reuses it inside the report loop.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1567#discussion_r3157411828 -> ba1a4f633

Disposition: FIXED
Commit: ba1a4f633
Evidence: `docs/review/PR_1567_FIXED_MAPPING.md` rephrases the merge-readiness checklist item to `Fixed-mapping artifact and PR body are mirror-aligned`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1567#discussion_r3157411832 -> ba1a4f633

Disposition: NOT-A-BUG
Evidence: `pre-commit run --all-files` and commit hooks passed with the Bandit-compatible dict construction, and the Compose v2 checks intentionally keep production helper scripts standalone for operator copy/paste surfaces in this PR scope.
Reason: The review-level readability/centralization notes are valid advisory feedback, but this lane is scoped to retiring the command-surface seam without introducing a new shared shell helper contract.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1567#pullrequestreview-4192679623

## Initial Evidence

- `python3 scripts/orchestration/check_preflight.py` (PASS)
- `python3 scripts/orchestration/check_agent_consistency.py` (PASS)
- `pre-commit run --all-files` (PASS)
- `pytest -q tests/test_repo_policy_guards.py::test_active_command_surfaces_use_docker_compose_v2` (PASS)
- `pytest -q tests/test_deploy_contract_scripts.py -q` (PASS, 32 passed)
- `pytest -q tests/test_repo_policy_guards.py tests/test_deploy_contract_scripts.py` (PASS, 46 passed)
- `python3 scripts/ci/check_docs_phase1_gates.py --files docs/roadmap/BACKLOG_LEDGER.md docs/architecture/ADR_COMPOSE_V2_COMMAND_SURFACE_SEAM_2026-03-09.md docs/runbooks/ENGINEER_QUICKPATH.md scripts/QUICK_DIAGNOSTIC.md` (PASS)
- `make validate-changed VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python` (PASS)
- `make validate-min VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python` (PASS)
- commit hooks during `git commit` (PASS)
- pre-push hooks during `git push` (PASS)

## Machine-Heavy Local Gate Deferral

Full local `make verify` was not run for this coordinator-owned Docker/CI
command-surface governance PR. The operator approved using narrow local gates
plus current-head GitHub CI as the machine-heavy signal. Merge readiness still
requires current-head required CI parity and strict merge-readiness wrappers.

## Start Gate Note

The branch was started after root/worktree preflight and agent consistency
passed. `origin/main` was locally synced, and the operator explicitly approved
starting while she monitored near-green `main` CI herself.

## Deferred / Follow-ups

- SBOM/VEX signed security artifacts remain blocked until P0 release-truth
  closure and a dedicated packet approves rollout.
- Dagger remains P2 deferred/evaluation-only; this PR does not enable a new CI
  control plane.
- Compose file names such as `docker-compose.production.yaml` remain unchanged.

## Merge Readiness

- [ ] CI green on current head
- [ ] No unresolved actionable review threads
- [ ] CodeRabbit/Sourcery/Cubic statuses reviewed and mapped
- [ ] Fixed-mapping artifact and PR body are mirror-aligned
- [ ] `check_review_threads_disposition.py --require-auth` PASS
- [ ] `check_pr_merge_readiness.py` PASS
- [ ] `check_merge_ready.py --require-auth` PASS
