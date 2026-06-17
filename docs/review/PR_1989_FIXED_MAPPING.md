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
- Post-open role order executed:
  `qa-engineer-agent -> bug-hunter -> security-auditor`.
- Codex Security diff scan completed with no findings.
- `pulseplate-pr-review` completed with one advisory large-diff planning note;
  disposition below.
- CodeRabbit was still pending at the latest artifact update; no actionable
  CodeRabbit finding was available to map.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1989#pullrequestreview-4513245105 -> 8ee7b117f
Disposition: FIXED
Commit: 8ee7b117f
Evidence: `tests/test_python_supply_chain_controls.py` catches `InvalidRequirement`; `tests/guards/test_security_devtooling_regression_guards.py` checks stable advisory markers instead of full literal phrases.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1989#issuecomment-4727078656 -> 137362472
Disposition: FIXED
Commit: 137362472
Evidence: `tests/test_python_supply_chain_controls.py` uses parser-backed canonical package-name checks across default `.in` and `.txt` surfaces and adds a bypass regression for case, compatible-release specs, direct references, and non-requirement lines.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1989#discussion_r3427944464
Disposition: NOT-A-BUG
Evidence: `find artifacts/orchestration/experiments -maxdepth 5 -type f` shows the Experiment Runner packet at `artifacts/orchestration/experiments/artifacts/orchestration/experiments/torch-cve-2025-3000-vector-policy-oracle-packet.json`; the suggested single-prefix path does not exist in the emitted local artifact tree.
Reason: The duplicated-looking prefix is the actual path emitted by the Experiment Runner CLI for this lane, so changing the mapping to the suggested path would make the provenance reference less accurate.

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

## PulsePlate Review Disposition

- Tool: `pulseplate-pr-review`
- Finding: advisory `large-diff-risk`
- Disposition: NOT-A-BUG
- Evidence: Diff is intentionally docs/guards-heavy for a security evidence
  lane; scoped local gates include `make validate-changed` and focused
  supply-chain/security-devtooling tests. No product runtime, OpenAPI, legacy,
  frontend, iOS, or broad lock-regeneration files are touched.
- Reason: The advisory is review-planning evidence, not a code defect or
  merge-blocking finding.

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
- PASS: `pulseplate-pr-review` dry-run completed; advisory large-diff risk
  dispositioned as `NOT-A-BUG` above.
- PASS: Codex Security diff scan completed with no findings; report:
  `/tmp/codex-security-scans/resolve-torch-cve-2025-3000-vector-profile/d72d2a53b529_20260617T115720Z/report.md`.

## Machine-Heavy Deferral

- Operator-approved deferral: full local `make verify` was not run for this
  dependency/security lane.
- Required narrow local gates above were run.
- Current-head CI is the heavy verification signal before merge.

## Merge Readiness

- Not merge-ready at latest artifact update because current-head CI and
  CodeRabbit were still pending.
- Superseded CI run `27686954746` contains cancelled `coverage-pr` and
  `diff-coverage` rows after a newer CI run started; those cancelled rows are
  stale and are not current-head failures.
- Required before merge: CodeRabbit/actionable bot disposition, current-head CI,
  strict merge-readiness with auth, wait-window, local `main` sync, and
  lane-local cleanup.
