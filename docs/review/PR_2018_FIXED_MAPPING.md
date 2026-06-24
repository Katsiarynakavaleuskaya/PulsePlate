# PR #2018 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2018
Title: `fix(deps): remove vulnerable Safety audit dependency`
Branch: `codex/deps-safety-nltk-alert-fix`

## Summary

This PR removes the active Safety dependency-audit lane after new Dependabot
alerts showed vulnerable transitive `nltk` re-entering the security tooling
graph. The replacement audit path is strict `pip-audit` from the pinned
`ci-lite` toolchain.

In scope:

- Delete the Safety runtime closure and policy surfaces:
  `requirements-security.txt`, `scripts/ci/run_safety_audit.py`,
  `.github/scripts/parse-safety-report.py`, `safety-policy.yaml`, and
  `safety-policy.toml`.
- Route CI, Security Scan, and nightly dependency audits through
  `scripts/ci_pip_audit.sh`.
- Pin `pip-audit` in `requirements-ci-lite.in/.txt`.
- Keep the existing optional-RAG `torch` / `CVE-2025-3000` no-fixed-version
  waiver scoped to `requirements-rag-vector*.txt` only.
- Update supply-chain tests, security/devtooling guards, risk routing,
  dependency docs, and advisory records.

Out of scope:

- Torch alerts `#160`, `#161`, `#162`: no patched version is available in the
  current advisory metadata; remain a separate advisory lane.
- Faraday alert `#224`: remains a dedicated Fastlane/Ruby lane.
- Platform-aware RAG CPU/macOS lock work: separate dependency/tooling lane.
- Hash-pinned Python lock generation: immediate follow-up supply-chain lane
  after this Safety/NLTK remediation. The current `pip-audit --no-deps`
  warnings are not vulnerability findings or gate failures, but they correctly
  point at the broader hash-pinning architecture gap for requirement locks.

## Implementation Commits

- `3275af6c630ce043d0395ab8104f298ec125e361` - `fix(deps): remove vulnerable Safety audit dependency`
- `6f1bef1c9f745e8611fa2635adbe00bf2235106f` - `fix(ci): address pip-audit review findings`
- `7ff04b686256c4792e8d146e7e4ec2028d4bed13` - `fix(ci): harden pip-audit workflow guards`

## Lane Start Provenance

- Worktree: `worktrees/deps-safety-nltk-alert-fix`
- Branch: `codex/deps-safety-nltk-alert-fix`
- Packet: `artifacts/orchestration/task_packets/fdfa5f023bcf.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Role dispatch manifest:
  `scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/fdfa5f023bcf.json --mode runtime --implementation-owner qa-engineer-agent --implementation-owner security-auditor --pretty`
- Dispatch order declared:
  `agent-coordinator -> qa-engineer-agent -> security-auditor -> bug-hunter`
- Transport note: native subagent transport for `agent-coordinator` did not
  return and was closed to avoid an unbounded hang. This PR is not merge-ready
  until post-open role/review passes and strict merge-readiness governance are
  complete.

## Local Validation

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/ci/install_locked_python_requirements.py --requirements-file requirements-ci-lite.txt --constraints-file constraints.txt --preflight-only`
- PASS: `pip-audit -r requirements-ci-lite.txt --no-deps --disable-pip -f json -o /tmp/deps-safety-nltk-ci-lite-pip-audit.json`
- PASS: `bash scripts/ci_pip_audit.sh`
  - `requirements.txt`: no known vulnerabilities
  - `requirements-docker-runtime.txt`: no known vulnerabilities
  - `requirements-data.txt`: no known vulnerabilities
  - `requirements-evals.txt`: no known vulnerabilities
  - `requirements-rag-vector.txt`: no known vulnerabilities, 1 ignored
    documented optional-RAG `CVE-2025-3000` torch finding with no fixed version
  - `requirements-rag-vector-cpu.txt`: no known vulnerabilities
- PASS: `.venv/bin/python -m pytest -q tests/test_python_supply_chain_controls.py tests/guards/test_security_devtooling_regression_guards.py tests/test_ci_risk_profile.py tests/test_ci_workflow_pr_size_governance_contract.py tests/test_dependency_security_guard.py`
- PASS after CodeRabbit fixes: `.venv/bin/python -m pytest -q tests/test_python_supply_chain_controls.py::test_pip_audit_helper_invokes_cpu_rag_vector_manifest tests/test_python_supply_chain_controls.py::test_pip_audit_helper_scans_all_manifests_before_returning_failure tests/test_ci_risk_profile.py::test_security_audit_helper_path_is_workflow_privileged tests/test_ci_risk_profile.py::test_security_audit_helper_change_routes_backend_and_security`
- PASS after CodeRabbit follow-up: `python3 scripts/ci/check_docs_phase1_gates.py --files docs/DEPENDENCY_MANAGEMENT.md docs/review/PR_2018_FIXED_MAPPING.md docs/roadmap/BACKLOG_LEDGER.md docs/security/CVE-2025-14009-nltk.md docs/security/PYTORCH_JIT_CVE_2025_3000_ADVISORY.md`
- PASS after CodeRabbit follow-up: `.venv/bin/python -m pytest -q tests/test_python_supply_chain_controls.py::test_security_scan_workflow_uses_ci_lite_direct_proxy_setup tests/test_python_supply_chain_controls.py::test_ci_security_job_runs_pip_audit_from_ci_lite_toolchain tests/test_python_supply_chain_controls.py::test_pip_audit_helper_scans_all_manifests_before_returning_failure tests/test_python_supply_chain_controls.py::test_pip_audit_helper_invokes_cpu_rag_vector_manifest`
- PASS after CodeRabbit fixes: `.venv/bin/python -m pytest -q tests/test_python_supply_chain_controls.py tests/guards/test_security_devtooling_regression_guards.py tests/test_ci_risk_profile.py tests/test_ci_workflow_pr_size_governance_contract.py tests/test_dependency_security_guard.py`
- PASS after CodeRabbit fixes: `PATH=.venv/bin:$PATH bash scripts/ci_pip_audit.sh`
- PASS: `VENV_PYTHON=.venv/bin/python make validate-changed`
  - Note: selected no Python/cross-surface tests, so the focused pytest above is
    the meaningful local test gate for this PR.
- PASS after CodeRabbit fixes: `VENV_PYTHON=.venv/bin/python make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS during commit `6f1bef1c9`: changed-file pre-commit hooks, including
  changed-file backend tests and Bandit.
- PASS during push: changed-file mypy, pip-audit, backend pre-push pytest,
  full-repo Bandit, and docker build test.
- PASS after rebase: `pulseplate-pr-review` dry-run report against
  `4e832857e40d79a3a0183ee044fd311d75f7bc07...3bd2d3386` confirmed the scoped
  28-file diff. Its large-diff note is expected because this no-legacy lane
  deletes the dead Safety wrapper/test/policy graph; split rationale is the
  Safety/NLTK alert remediation only, with Torch/Faraday/RAG platform work kept
  out of scope.

Full local `make verify` was not run under the operator-approved machine-heavy
dependency-lane exception. Current-head CI is the required heavy parity signal
before any merge-readiness claim.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Any later bot, human, CodeRabbit, Sourcery, Cubic, Codex Security, QA,
bug-hunter, security-auditor, or `pulseplate-pr-review` finding remains
blocking until fixed or formally dispositioned with evidence.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2018#discussion_r3470273502
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2018#discussion_r3470273520
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2018#discussion_r3470586006
Disposition: FIXED
Commit: see mapping entries below
Evidence: `scripts/ci_pip_audit.sh` now aggregates per-manifest `pip-audit` failures and exits nonzero only after every manifest has been scanned; `tests/test_python_supply_chain_controls.py` proves later manifests still run and write reports after an earlier manifest fails; `scripts/ci/ci_risk_profile.py` now classifies `scripts/ci_pip_audit.sh` as workflow-privileged, and `tests/test_ci_risk_profile.py` asserts that stronger governance routing. `tests/test_python_supply_chain_controls.py` now rejects any inline `pip install` invocation in the dependency-audit workflow steps, while `docs/security/CVE-2025-14009-nltk.md` broadens the Safety/NLTK validation search and both security advisories include file-line evidence anchors for Docs Phase1.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2018#discussion_r3470273502 -> 6f1bef1c9f745e8611fa2635adbe00bf2235106f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2018#discussion_r3470273520 -> 6f1bef1c9f745e8611fa2635adbe00bf2235106f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2018#discussion_r3470586006 -> 7ff04b686256c4792e8d146e7e4ec2028d4bed13

## Security Notes

- Active vulnerable `nltk` is removed by deleting the Safety audit dependency
  graph, not by suppressing the alert.
- `scripts/ci_pip_audit.sh` no longer skips outside CI, no longer ignores
  failures with `|| true`, and no longer invokes resolver installs for pinned
  lockfiles.
- `scripts/ci_pip_audit.sh` now audits every configured manifest before
  returning any nonzero dependency-audit status, preserving both artifact
  coverage and fail-closed behavior.
- The only retained waiver is `CVE-2025-3000`, scoped to optional RAG/vector
  manifests and tracked in
  `docs/security/PYTORCH_JIT_CVE_2025_3000_ADVISORY.md` plus
  `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-pytorch-jit-cve-2025-3000-vector-profile`.

## Merge Readiness

- Current-head CI: pending.
- CodeRabbit / Sourcery / Cubic actionables: pending.
- Review thread disposition: pending.
- Codex Security diff scan: pending.
- Strict merge wrapper: pending.

Do not call this PR green, ready, or mergeable until all items above pass on the
current head SHA.
