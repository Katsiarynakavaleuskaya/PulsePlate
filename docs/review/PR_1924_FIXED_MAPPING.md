# PR 1924 Fixed in Commit Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1924>

## Summary

This PR restores read compatibility for legacy local Experiment operator ledger
events that used SHA-256 idempotency keys, while keeping newly written records on
the current PBKDF2 idempotency, content hash, and idempotency-key-check path.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/71b19978fa8d.json`
- Branch: `codex/fix-ledger-record-compatibility-issue`
- Head commit at bootstrap: `ec6c62ccf6e03ac1edcdedfa2cfbd71882339fb0`
- Role dispatch command executed: `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/71b19978fa8d.json --pretty`
- Role order executed: `agent-coordinator -> backend-engineer -> qa-engineer-agent -> bug-hunter -> security-auditor -> architecture-specialist -> cursor-specialist-agent`

## Scope

IN:

- `scripts/orchestration/experiment_operator_ledger.py`
- `tests/test_experiment_operator_ledger.py`
- `docs/review/PR_1924_FIXED_MAPPING.md`

OUT:

- Product runtime behavior
- OpenAPI or client contracts
- Semantic-cache admission or runtime cache behavior
- Advisory wiki, support-plane, or knowledge-promotion authority

## Agent Execution Log

- `agent-coordinator`: PASS for scope lock and role-order confirmation; blocked
  merge-readiness until the mapping artifact and GitHub-backed Sourcery
  disposition were added.
- `backend-engineer`: PASS after confirming the Sourcery finding and recommending
  a pinned legacy SHA-256 material tuple separate from current PBKDF2 material.
- `qa-engineer-agent`: PASS; deterministic regression coverage is sufficient for
  the legacy SHA-256 load path and current-material drift scenario.
- `bug-hunter`: PASS; no edge-case regressions found in exact-key validation,
  filename/key mismatch handling, or current PBKDF2 record validation.
- `security-auditor`: PASS; no subprocess, network, secret-decoding,
  path-exposure, or authority-widening behavior found.
- `architecture-specialist`: PASS; diff stays limited to local operator-ledger
  compatibility and does not move product truth or widen semantic-cache rails.
- `cursor-specialist-agent`: FAIL at first pass until this canonical mapping
  artifact and the PR-body mirror exist; the governance artifact and PR-body
  refresh address that workflow blocker.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/exp-058679fc78b5.json`
- Mode: `oracle_only_governance_reviewer`
- Status: `accepted`
- Shared tree untouched: `true`
- Mutated paths: `[]`
- Oracle commands: `python3 scripts/orchestration/check_preflight.py`; `python3 -m py_compile scripts/orchestration/experiment_operator_ledger.py tests/test_experiment_operator_ledger.py`; `git diff --check origin/main...HEAD`
- Co-author trailer required for this governance commit: `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`
- Rejected non-evidence attempt: `artifacts/orchestration/experiments/results/exp-eeddea7b8dfc.json` was rejected because the runner isolated checkout had no repo/shared `.venv` for `make validate-changed`; direct local `make validate-changed` evidence is recorded below instead.

## Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/orchestration/task_bootstrap.py --goal "Complete PR 1924 legacy operator ledger idempotency compatibility and review governance" --task-class orchestration --path scripts/orchestration/experiment_operator_ledger.py --path tests/test_experiment_operator_ledger.py --path docs/review/PR_1924_FIXED_MAPPING.md --requested-agent agent-coordinator --requested-agent backend-engineer --requested-agent qa-engineer-agent --requested-agent bug-hunter --requested-agent security-auditor --requested-agent architecture-specialist --pr-phase post_open_review --native-bridge-transport codex-native-subagents`
- PASS: `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/71b19978fa8d.json --pretty`
- PASS: `python3 -m py_compile scripts/orchestration/experiment_operator_ledger.py tests/test_experiment_operator_ledger.py`
- PASS: `.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_experiment_operator_ledger.py -k 'legacy_sha256 or idempotency_key_check or persisted_key_without_rederiving'`
- PASS: `.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_experiment_operator_ledger.py`
- PASS: `make validate-changed`
- PASS: commit hook run for `6de8e93da` with `VENV_PYTHON` pointing at the repo/shared virtualenv.
- PASS: `pre-commit run --all-files` with `VENV_PYTHON` pointing at the repo/shared virtualenv.
- FAIL / unrelated repo-wide blocker: `make verify` passed `verify-env` and `flake8`, then failed in `make typecheck` with 13 existing mypy errors in `core/ai/semantic_cache_offline_admission_runner.py` and `core/ai/semantic_cache_shadow_admission_harness.py`; neither file is in `git diff --name-only origin/main...HEAD` for PR 1924, so this lane cannot honestly claim full local hard-gate merge readiness.
- PASS: Codex Security diff scan / finding discovery wrote `/tmp/codex-security-scans/PulsePlate-pr-1924/fcd06a096bb2_20260611T114746Z/report.md`; no reportable security findings.
- ADVISORY: `pulseplate-pr-review` dry-run completed; initial run inspected the then-current remote PR head and produced one advisory large-diff planning note for stale remote context, so it must be repeated after pushing current head before merge-readiness can be claimed.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1924#pullrequestreview-4458575633 -> 6de8e93da
Disposition: FIXED
Commit: 6de8e93da
Evidence: scripts/orchestration/experiment_operator_ledger.py:231; scripts/orchestration/experiment_operator_ledger.py:434; tests/test_experiment_operator_ledger.py:60; tests/test_experiment_operator_ledger.py:1036
Reason: Sourcery review-level feedback is fixed by pinning legacy SHA-256 idempotency material separately from the current PBKDF2 material and covering the drift case with a deterministic regression test.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1924#discussion_r3380629400 -> 6de8e93da
Disposition: FIXED
Commit: 6de8e93da
Evidence: scripts/orchestration/experiment_operator_ledger.py:231; scripts/orchestration/experiment_operator_ledger.py:434; tests/test_experiment_operator_ledger.py:60; tests/test_experiment_operator_ledger.py:1036
Reason: `_legacy_sha256_idempotency_key(...)` now uses `LEGACY_SHA256_IDEMPOTENCY_MATERIAL_FIELDS` through a legacy-only material helper, so future changes to `IDEMPOTENCY_MATERIAL_FIELDS` do not make existing SHA-256 ledger events unreadable.

## Bot Review Summary

- Sourcery: FIXED in commit `6de8e93da`; the review-level and inline discussion
  actionables are mapped above.
- Cubic: NOT-A-BUG / no actionable findings visible for current reviewed head;
  Cubic reported no issues across the two changed files.
- CodeRabbit: NOT-A-BUG for current state; CodeRabbit was rate-limited and did
  not produce actionable review findings for this PR. A later CodeRabbit review
  remains acceptable but is not claimed here.
- Codecov: NOT-A-BUG; patch coverage comment reports all modified coverable
  lines covered for the previous head, and current-head CI remains required
  after this artifact commit.

## Deferred / Follow-ups

None.

## Merge Readiness

Not merge-ready yet. Pending after this artifact commit:

- Push local commits and rerun current-head CI for the pushed head.
- Current-head CI rerun with `PR Body Phase2 gates` and `Merge readiness gate`
  passing for the pushed head.
- Sourcery review thread resolution after this artifact and PR-body mirror are
  pushed.
- Repeat `pulseplate-pr-review` against the pushed current head.
- Full `make verify` remains blocked locally by unrelated repo-wide mypy errors
  outside the PR 1924 diff; do not claim merge-ready until this is resolved or
  explicitly dispositioned under repo policy.
- Strict merge-readiness wrapper with auth, no unresolved review threads, no
  actionable bot comments, and the required wait window.
