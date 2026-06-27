# PR 2023 Fixed Mapping

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/11fd4a5c871e.json`
- Branch: `codex/propose-fix-for-dependency-security-bypass`
- Base: `main`
- Worktree: isolated PR #2023 dependency-surface worktree
- Role order executed pre-open:
  `agent-coordinator -> qa-engineer-agent -> security-auditor -> architecture-specialist`
- Packet creation was treated as provenance only, not role execution.

## Scope Boundary

- In scope: Python dependency surface contract, offline surface validator,
  `verify_requirements.py` compatibility wrapper, installer security-floor
  regression coverage, and canonical docs for profile owners, install
  authority, security coverage, and noncanonical aggregate files.
- Out of scope: package version changes, Python lockfile regeneration, Ruff
  bump, duplicate Pillow cleanup, Faraday/Fastlane remediation, Trivy
  suppression changes, PR #2025, and PR #2026.

## Discussion Thread Pass

- [x] Discussion-thread pass completed for currently visible inline Sourcery
  comments.
- [x] Fixed in commit mapping completed for the two actionable Sourcery
  comments.
- [x] Premortem findings dispositioned.
- [x] Experiment Runner oracle-only governance evidence recorded.
- [x] Local focused gates, `make validate-changed`, and
  `pre-commit run --all-files` passed before the implementation commit.
- [ ] Post-push current-head CI inspection is still required.
- [ ] Post-open `qa-engineer-agent -> bug-hunter -> security-auditor`, Codex
  Security diff scan / finding discovery, and `pulseplate-pr-review` remain
  required before any readiness claim.
- [ ] CodeRabbit, Sourcery, and Cubic current-head actionables must be
  rechecked after push.
- [ ] Strict merge-readiness wrapper with auth and the mandatory wait-window
  remain required before merge.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: b6802627bcdf87c38d7bf9086aa8a7101d27a4f3
Evidence:
`tests/test_install_locked_python_requirements.py` now asserts the returned
effective constraints file content for duplicate exact-pin removal and
security-floor preservation, and focused pytest plus `make validate-changed`
passed with those assertions.
Reason: Sourcery requested assertions for the effective constraints file
contents in the two new regression tests; the implementation commit adds those
content checks and preserves the intended installer security-floor behavior.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2023#discussion_r3476956759 -> b6802627bcdf87c38d7bf9086aa8a7101d27a4f3
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2023#discussion_r3476956764 -> b6802627bcdf87c38d7bf9086aa8a7101d27a4f3

Disposition: FIXED
Commit: b6802627bcdf87c38d7bf9086aa8a7101d27a4f3
Evidence:
`scripts/ci/check_python_dependency_surfaces.py`,
`verify_requirements.py`, `tests/test_python_dependency_surfaces.py`,
`tests/test_verify_requirements.py`,
`docs/contracts/PYTHON_DEPENDENCY_SURFACES.md`, `REQUIREMENTS.md`,
`docs/DEPENDENCY_MANAGEMENT.md`, and
`docs/roadmap/BACKLOG_LEDGER.md`.
Reason: Adds the PR-1 Python dependency surface contract and validator while
leaving dependency versions and lockfiles unchanged.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2023 -> b6802627bcdf87c38d7bf9086aa8a7101d27a4f3

## Premortem Closure

- Artifact: `docs/review/PR_2023_PREMORTEM.md`
- Decision: proceed with changes.
- Finding PM-2023-001 changed-file validation gap:
  - Disposition: FIXED
  - Evidence:
    `scripts/ci/check_python_dependency_surfaces.py`,
    `tests/test_python_dependency_surfaces.py`, focused pytest, and
    `make validate-changed`.
- Finding PM-2023-002 PR-2 churn collapse:
  - Disposition: FIXED
  - Evidence: no `requirements*.in`, `requirements*.txt`,
    `constraints.txt`, `ios/Gemfile.lock`, Trivy, or Faraday files are
    changed in this PR.
- Finding PM-2023-003 stale `verify_requirements.py` authority:
  - Disposition: FIXED
  - Evidence: `verify_requirements.py` delegates to
    `scripts/ci/check_python_dependency_surfaces.py`, and
    `tests/test_verify_requirements.py` covers the wrapper.
- Finding PM-2023-004 repo-root script execution:
  - Disposition: FIXED
  - Evidence: direct
    `python scripts/ci/check_python_dependency_surfaces.py` passed.

## Experiment Runner Evidence

- Packet:
  `artifacts/orchestration/experiments/pr2023-dependency-surface-contract-oracle-v2.json`
- Result:
  `artifacts/orchestration/experiments/results/pr2023-dependency-surface-contract-oracle-result-v2.json`
- Status: accepted.
- Runner mode: `oracle_only_governance_reviewer`.
- Shared tree untouched: `true`.
- Failure class: `null`.
- Contribution kind: `oracle_review`.
- Co-author required: `true`.
- Commit trailer included in implementation commit
  `b6802627bcdf87c38d7bf9086aa8a7101d27a4f3`:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.
- Oracle commands:
  - `python scripts/ci/check_python_dependency_surfaces.py`
  - `python -m pytest -q tests/test_python_dependency_surfaces.py tests/test_verify_requirements.py tests/test_install_locked_python_requirements.py -k 'dependency_surface or verify_requirements or effective_constraints_file_for_requirement'`

## Local Validation Evidence

- PASS:
  `python3 scripts/orchestration/check_preflight.py --mode analyze --path .`
- PASS:
  `python scripts/ci/check_python_dependency_surfaces.py`
- PASS:
  `python verify_requirements.py`
- PASS:
  `python -m py_compile scripts/ci/check_python_dependency_surfaces.py verify_requirements.py tests/test_python_dependency_surfaces.py tests/test_verify_requirements.py`
- PASS:
  `python -m pytest -q tests/test_python_dependency_surfaces.py tests/test_verify_requirements.py tests/test_install_locked_python_requirements.py -k 'dependency_surface or verify_requirements or effective_constraints_file_for_requirement or run_dependency_floor_preflight or main_preflight_only'`
- PASS:
  `python -m pytest -q tests/test_python_supply_chain_controls.py -k 'dependency_docs_describe_eval_and_data_profiles_as_local_manual or eval_and_data_dependency_profiles_are_compiled_and_pinned or eval_and_data_profiles_do_not_join_shared_install_routing or security_scan_workflow_audits_runtime_and_optional_manifests'`
- PASS:
  `python -m pytest -q tests/test_install_locked_python_requirements.py -k 'install_from_proxy_preserves_floor_constraint_for_exact_pin or main_runs_download_install_and_static_guard_without_pip_self_upgrade or main_runs_direct_proxy_install_and_static_guard or effective_constraints_file_for_requirement'`
- PASS:
  `VENV_PYTHON=<repo>/.venv/bin/python make validate-changed`
- PASS:
  `python -m black --check scripts/ci/check_python_dependency_surfaces.py verify_requirements.py tests/test_python_dependency_surfaces.py tests/test_verify_requirements.py tests/test_install_locked_python_requirements.py`
- PASS:
  `python -m flake8 scripts/ci/check_python_dependency_surfaces.py verify_requirements.py tests/test_python_dependency_surfaces.py tests/test_verify_requirements.py tests/test_install_locked_python_requirements.py`
- PASS:
  `git diff --check`
- PASS:
  `pre-commit run --all-files`

## Machine-Heavy Verification Deferral

Full local `make verify` was not run. The operator explicitly requested the
machine-heavy exception for this dependency lane, so this PR used focused local
dependency tests, `make validate-changed`, and `pre-commit run --all-files`.
Merge readiness still requires current-head CI parity, review-thread
dispositions, post-open role passes, Codex Security diff scan / finding
discovery, `pulseplate-pr-review`, strict merge-readiness checks with auth, and
the mandatory wait-window.

## Dependency Delta Proof

- No package versions are changed.
- No Python lockfiles or requirement manifests are regenerated.
- No `constraints.txt` changes are included.
- No Faraday, Fastlane, Trivy, or iOS lockfile changes are included.
- `requirements-all.txt` and `requirements-lock.txt` remain documented as
  noncanonical aggregate install surfaces.

## Merge Readiness

- [ ] Current-head CI inspected and passing for the pushed head SHA.
- [ ] CodeRabbit PASS / no actionables confirmed for current head.
- [ ] Sourcery PASS / no actionables confirmed for current head.
- [ ] Cubic PASS / no actionables confirmed for current head.
- [ ] All review threads resolved only after disposition evidence is present.
- [ ] Strict merge-readiness wrapper with auth passes.
- [ ] Mandatory wait-window satisfied.
