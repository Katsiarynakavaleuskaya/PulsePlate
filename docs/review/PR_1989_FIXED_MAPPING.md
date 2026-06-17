# PR 1989 Fixed Mapping

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/341a9a60ff26.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Branch: `codex/resolve-torch-cve-2025-3000-vector-profile`
- Bootstrap packet: `artifacts/orchestration/task_packets/341a9a60ff26.json`
- Pre-open role order executed:
  `agent-coordinator -> security-auditor -> backend-engineer -> qa-engineer-agent -> bug-hunter -> architecture-specialist`
- Packet creation was treated as provenance only, not role execution.

## Scope

- In scope: optional RAG/vector PyTorch `CVE-2025-3000` policy evidence,
  scoped Safety waiver refresh, dependency-security floor alignment, and focused
  supply-chain guards.
- Out of scope: runtime behavior, app/core/legacy route changes, OpenAPI,
  FoodDB, auth/BOLA, frontend/iOS/macOS, torch bump, broad lock regeneration,
  and private emergency-wheel fallback changes.

## Implementation Mapping

- Initial implementation: `ab866229b`
  - `safety-policy.yaml`: refreshed `SFTY-20250331-30014` waiver evidence and
    expiry to `2026-07-17`.
  - `docs/security/PYTORCH_JIT_CVE_2025_3000_ADVISORY.md`: refreshed current
    advisory state, no-patched-version evidence, and default-surface no-torch
    notes.
  - `docs/roadmap/BACKLOG_LEDGER.md`: refreshed the optional-vector backlog
    item with 2026-06-17 source evidence and ci-lite graph-lag note.
  - `constraints.txt`: aligned `pyarrow>=20.0.0` with canonical inputs and
    corrected the flake8/ruff comment.
  - `.github/workflows/security.yml`: aligned Security workflow Safety install
    floor to `safety>=3.8.1`.
  - `tests/test_python_supply_chain_controls.py` and
    `tests/guards/test_security_devtooling_regression_guards.py`: added guards
    for dependency floor alignment, optional-vector profile boundaries, and
    waiver/advisory/backlog coherence.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- No review threads existed at PR open.
- Post-open review passes are still required before merge readiness:
  `qa-engineer-agent -> bug-hunter -> security-auditor`, then Codex Security
  diff scan when available, CodeRabbit/actionable bot review disposition, and
  `pulseplate-pr-review`.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1989#pullrequestreview-4513245105 -> 8ee7b117f
Disposition: FIXED
Commit: 8ee7b117f
Evidence: `tests/test_python_supply_chain_controls.py` catches `InvalidRequirement`; `tests/guards/test_security_devtooling_regression_guards.py` checks stable advisory markers instead of full literal phrases.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1989#issuecomment-4727078656 -> 137362472
Disposition: FIXED
Commit: 137362472
Evidence: `tests/test_python_supply_chain_controls.py` uses parser-backed canonical package-name checks across default `.in` and `.txt` surfaces and adds a bypass regression for case, compatible-release specs, direct references, and non-requirement lines.

## Premortem

- Local artifact:
  `artifacts/orchestration/premortem/torch-cve-2025-3000-vector-policy-premortem.md`
- Decision: `proceed with changes`.
- Closure: findings were addressed by keeping the PR in waiver/evidence mode,
  adding optional-profile drift guards, and aligning waiver/advisory/backlog
  dates.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/artifacts/orchestration/experiments/torch-cve-2025-3000-vector-policy-oracle-packet.json`
- Artifact: `artifacts/orchestration/experiments/results/torch-cve-2025-3000-vector-policy-oracle-result.json`
- Mode: `oracle_only_governance_reviewer`
- Status: `accepted`; `mutated_paths=[]`; oracle commands passed.
- Contribution: `oracle_review`; implementation commit `ab866229b` includes:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.

## Tests

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS:
  `.venv/bin/python -m pytest -q tests/test_python_supply_chain_controls.py tests/test_install_locked_python_requirements.py tests/test_run_safety_audit.py tests/guards/test_security_devtooling_regression_guards.py`
- BLOCKED LOCALLY: `python3 scripts/ci/run_safety_audit.py` stopped before scan
  because `SAFETY_API_KEY` is not exported in the local shell; CI must run it
  with the repository secret.
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS during push: pre-push hooks including backend pytest, pip-audit, and
  full-repo Bandit pre-push.

## Machine-Heavy Deferral

- Operator-approved deferral: full local `make verify` was not run for this
  dependency/security lane.
- Required narrow local gates above were run.
- Current-head CI is the heavy verification signal before merge.

## Merge Readiness

- Not merge-ready at artifact creation time.
- Required before merge: post-open role passes, Codex Security diff scan when
  available, CodeRabbit/actionable bot disposition, `pulseplate-pr-review`,
  current-head CI, strict merge-readiness with auth, wait-window, local `main`
  sync, and lane-local cleanup.
