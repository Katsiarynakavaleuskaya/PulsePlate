# PR 1924 Fixed in Commit Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1924>

## Summary

This PR restores read compatibility for legacy local Experiment operator ledger
events that used SHA-256 idempotency keys, while keeping newly written records on
the current PBKDF2 idempotency, content hash, and idempotency-key-check path.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/084ae57479a4.json`
- Original packet: `artifacts/orchestration/task_packets/71b19978fa8d.json`
- Branch: `codex/fix-ledger-record-compatibility-issue`
- Head commit at bootstrap: `ec6c62ccf6e03ac1edcdedfa2cfbd71882339fb0`
- Current local head after main refresh: `516ff66a2501c70cb53bd23d919d73a9cca9a430`
- Pushed governance refresh head reviewed: `a599cb7fa94526ba48385608f9c69fc9d79b2ebb`
- Current `origin/main` merge-base: `38571b1621f4d061367c63d04a0c5fb04e808cda`
- Main refresh commits on this branch:
  `47f0762091a0b896f38a74ba8516b1122be52607`,
  `516ff66a2501c70cb53bd23d919d73a9cca9a430`
- Role dispatch command executed: `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/084ae57479a4.json --pretty`
- Role order declared: `agent-coordinator -> backend-engineer -> qa-engineer-agent -> bug-hunter -> security-auditor -> architecture-specialist -> cursor-specialist-agent`

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

- `agent-coordinator`: PASS for final current-main scope lock, role order, and
  narrow-gate plan on packet `084ae57479a4`; merge-readiness remains blocked
  until the local head is pushed and current-head CI/review governance is fresh.
- `backend-engineer`: PASS; legacy SHA-256 material is pinned separately from
  current PBKDF2 material, the legacy read helper uses the pinned tuple, and
  current record validation still fails closed on filename/key, content hash,
  and idempotency-key-check mismatch.
- `qa-engineer-agent`: PASS for coverage sufficiency; deterministic tests cover
  legacy SHA-256 load, current-material drift, current record tamper rejection,
  and persisted-key loading.
- `bug-hunter`: PASS; no edge-case regressions found in exact-key validation,
  filename/key mismatch handling, legacy exact-shape detection, or current
  PBKDF2 record validation.
- `security-auditor`: PASS; no reportable security findings in the scoped
  three-file diff. Legacy records are accepted only by exact legacy shape and
  current records still fail closed on filename/key, content hash, and
  idempotency-key-check validation.
- `architecture-specialist`: PASS; diff remains limited to the planned
  local-operator-ledger compatibility files and does not move product runtime,
  OpenAPI/client contracts, semantic-cache rails, advisory wiki, support-plane,
  or knowledge-promotion authority.
- `cursor-specialist-agent`: PASS; packet 084ae57479a4, dispatch manifest role 7,
  role-order wording, pending/current-head gates, PR body Phase2 structural
  compatibility, and no absolute local paths in the artifact were verified
  read-only.

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

- PASS: `python3 scripts/orchestration/check_preflight.py --mode analyze --path scripts/orchestration/experiment_operator_ledger.py --path tests/test_experiment_operator_ledger.py --path docs/review/PR_1924_FIXED_MAPPING.md`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/orchestration/task_bootstrap.py --goal "Final current-main PR 1924 legacy operator ledger idempotency compatibility closeout and merge-readiness refresh" --task-class orchestration --path scripts/orchestration/experiment_operator_ledger.py --path tests/test_experiment_operator_ledger.py --path docs/review/PR_1924_FIXED_MAPPING.md --requested-agent agent-coordinator --requested-agent backend-engineer --requested-agent qa-engineer-agent --requested-agent bug-hunter --requested-agent security-auditor --requested-agent architecture-specialist --requested-agent cursor-specialist-agent --pr-phase merge_ready --native-bridge-transport codex-native-subagents`
- PASS: `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/084ae57479a4.json --pretty`
- PASS: `python3 -m py_compile scripts/orchestration/experiment_operator_ledger.py tests/test_experiment_operator_ledger.py`
- PASS: repo-approved shared virtualenv Python ran
  `python -m pytest -q -p no:cacheprovider tests/test_experiment_operator_ledger.py`
- PASS: `make validate-changed` with `VENV_PYTHON` pointing at the
  repo-approved shared virtualenv Python
- PASS: `git diff --check origin/main...HEAD`
- PASS: `git diff --check`
- PASS: `pre-commit run --all-files` with `GIT_TERMINAL_PROMPT=0` and
  `VENV_PYTHON` pointing at the repo-approved shared virtualenv Python.
- NOT RUN: full `make verify` is intentionally deferred under the operator
  approved machine-heavy exception for this narrow orchestration lane. This
  artifact and the PR body use focused local gates plus current-head CI as the
  heavy signal.
- PASS: Codex Security diff scan / finding discovery for pushed head
  `a599cb7fa94526ba48385608f9c69fc9d79b2ebb`; the plugin report validated and
  rendered with no reportable findings. The scan bundle is local-only and not
  committed.
- PASS: `pulseplate-pr-review` dry-run for pushed head
  `a599cb7fa94526ba48385608f9c69fc9d79b2ebb`; no deterministic findings.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1924#pullrequestreview-4458575633 -> 6de8e93da
Disposition: FIXED
Commit: 6de8e93da
Evidence: scripts/orchestration/experiment_operator_ledger.py:229; scripts/orchestration/experiment_operator_ledger.py:451; tests/test_experiment_operator_ledger.py:60; tests/test_experiment_operator_ledger.py:1056
Reason: Sourcery review-level feedback is fixed by pinning legacy SHA-256 idempotency material separately from the current PBKDF2 material and covering the drift case with a deterministic regression test.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1924#discussion_r3380629400 -> 6de8e93da
Disposition: FIXED
Commit: 6de8e93da
Evidence: scripts/orchestration/experiment_operator_ledger.py:229; scripts/orchestration/experiment_operator_ledger.py:451; tests/test_experiment_operator_ledger.py:60; tests/test_experiment_operator_ledger.py:1056
Reason: `_legacy_sha256_idempotency_key(...)` now uses `LEGACY_SHA256_IDEMPOTENCY_MATERIAL_FIELDS` through a legacy-only material helper, so future changes to `IDEMPOTENCY_MATERIAL_FIELDS` do not make existing SHA-256 ledger events unreadable.

## Bot Review Summary

- Sourcery: FIXED in commit `6de8e93da`; the review-level and inline discussion
  actionables are mapped above.
- Cubic: prior pushed head reported no issues across the two changed files.
  Current-head bot freshness remains pending after the next push.
- CodeRabbit: prior pushed head was rate-limited and did not produce actionable
  review findings for this PR. Current-head bot freshness remains pending after
  the next push.
- Codecov: prior pushed head patch coverage comment reported all modified
  coverable lines covered. Current-head CI/coverage remains required after the
  next push.

## Deferred / Follow-ups

None.

## Merge Readiness

Not merge-ready yet. Pending after this artifact refresh:

- Push this artifact-only refresh and rerun current-head CI for the pushed head.
- Current-head CI rerun with `PR Body Phase2 gates` and `Merge readiness gate`
  passing for the pushed head.
- Sourcery review thread remains resolved only if strict disposition checks pass
  against the pushed current head.
- CodeRabbit, Sourcery, Cubic, and Codecov must have no actionable items on the
  pushed current head.
- Strict merge-readiness wrapper with auth must pass with no unresolved review
  threads, no actionable bot comments, current-head checks acceptable under the
  machine-heavy exception, and the required wait window elapsed.
