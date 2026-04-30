# PR #1573 Fixed Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1573>
Branch: `fix/ci-feature-fast-feedback`
Date: 2026-04-29

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Artifact status: PR-open governance artifact for the CI feature/fix
fast-feedback prerequisite lane. One actionable CodeRabbit review thread was
fixed after the comment timestamp and is mapped below.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1573#discussion_r3164706825 -> a9f38fd9ed5fd43da09bd7fd60601d589b8e7d41
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1573#pullrequestreview-4201341325 -> a9f38fd9ed5fd43da09bd7fd60601d589b8e7d41
Disposition: FIXED
Commit: a9f38fd9ed5fd43da09bd7fd60601d589b8e7d41
Evidence: `.github/workflows/ci.yml:956` marks missing fast-feedback timing seed as `timing_unavailable` with `elapsed_seconds=-1` instead of falling back to `date +%s`; `tests/test_ci_workflow_pr_size_governance_contract.py:188` asserts the explicit missing-seed warning and forbids the legacy fallback.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1573#discussion_r3164765312 -> a50f5928b43a173766328bc012a0a698603ee708
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1573#pullrequestreview-4201409535 -> a50f5928b43a173766328bc012a0a698603ee708
Disposition: FIXED
Commit: a50f5928b43a173766328bc012a0a698603ee708
Evidence: `docs/review/PR_1573_FIXED_MAPPING.md:111-116` keeps merge-readiness checkboxes unchecked until the final merge cycle, matching CodeRabbit's governance request.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1573#discussion_r3164782569 -> 45731a11c82d6d170cdbb7f4b7b5f39d8615a16c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1573#pullrequestreview-4201427404 -> 45731a11c82d6d170cdbb7f4b7b5f39d8615a16c
Disposition: FIXED
Commit: 45731a11c82d6d170cdbb7f4b7b5f39d8615a16c
Evidence: `docs/review/PR_1573_FIXED_MAPPING.md:111-116` points at the actual merge-readiness checklist block after CodeRabbit flagged the stale line anchor.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1573#discussion_r3166079874 -> d8ccf2327f8bed2475a1f27d744d0a7b33ea01f1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1573#pullrequestreview-4202936731 -> d8ccf2327f8bed2475a1f27d744d0a7b33ea01f1
Disposition: FIXED
Commit: d8ccf2327f8bed2475a1f27d744d0a7b33ea01f1
Evidence: `tests/test_payment_source_contract_api.py:32` narrows the canonical app import guard to `ImportError`; targeted payment tests, focused PR gate, `pre-commit run --all-files`, `make validate-changed`, and `make validate-min` passed.

## Regression Stabilization Evidence

- `f7f07c25d5f90821d099add4b679e43bea3c5b8a` keeps the PR aligned with
  the already-merged payment auth override isolation fix by clearing app-level
  `get_api_key` overrides from the canonical FastAPI app used by billing
  resolver code.
- `pytest -q tests/test_payment_source_contract_api.py::test_pop_app_get_api_key_overrides_removes_stale_reload_key tests/test_payment_source_contract_api.py::test_pop_app_get_api_key_overrides_scans_canonical_app tests/test_payment_source_contract_api.py::test_manual_intent_rejects_env_configured_pro_key_without_app_validator_override -vv`
  (PASS)
- CI-order prefix through `tests/test_payment_source_contract_api.py` using
  `scripts/ci/run_main_test_shards.py --python-version 3.13 --shard-count 2`
  (PASS: 5683 passed, 8 skipped)
- Rebased-head focused gate:
  `pytest -q tests/test_payment_source_contract_api.py tests/test_repo_policy_guards.py tests/test_ci_workflow_pr_size_governance_contract.py tests/test_ci_risk_profile.py tests/test_python_supply_chain_controls.py::test_ci_workflow_uses_single_direct_proxy_python_install_path_per_job`
  (PASS)

## Initial Evidence

- `python3 scripts/orchestration/check_preflight.py` (PASS)
- `python3 scripts/orchestration/check_agent_consistency.py` (PASS)
- `pytest -q tests/test_ci_workflow_pr_size_governance_contract.py tests/test_ci_risk_profile.py tests/test_python_supply_chain_controls.py::test_ci_workflow_uses_single_direct_proxy_python_install_path_per_job` (PASS)
- `pytest -q tests/test_repo_policy_guards.py tests/test_ci_workflow_pr_size_governance_contract.py tests/test_ci_risk_profile.py tests/test_python_supply_chain_controls.py::test_ci_workflow_uses_single_direct_proxy_python_install_path_per_job` (PASS)
- `pre-commit run --all-files` (PASS)
- `make validate-changed VENV_PYTHON=<venv-python>` (PASS)
- `make validate-min VENV_PYTHON=<venv-python>` (PASS)
- pre-push hooks during `git push` (PASS)

## Representative Feedback-Budget Evidence

Representative push run `25138247476` on `fix/ci-feature-fast-feedback`
captured before this governance evidence refresh:

- [x] `test-feature (3.13)` settled on implementation head `15f78c0ad9bbe43792a4a11bd5c64017f6a54b8a` (PASS, 9m59s)
- [x] `feature-feedback-budget-3.13` artifact present
- [x] elapsed/target evidence reviewed before deciding whether to open `ledger-p1-ci-install-profile-split-after-disk-unblock`

Budget artifact evidence:

```json
{
  "status": "within_budget",
  "elapsed_seconds": 587,
  "target_minutes": 45,
  "python_version": "3.13",
  "contract_risk_groups": "billing_entitlement,insight_ai,openapi_contract,food_catalog,route_contract_safety,merge_governance",
  "run_backend_blocking": "true"
}
```

## Machine-Heavy Local Gate Deferral

Full local `make verify` was not run for this coordinator-owned CI/tooling PR.
The PR uses narrow local gates plus current-head GitHub CI as the
machine-heavy signal. Merge readiness still requires current-head required CI
parity and strict merge-readiness wrappers.

## Deferred / Follow-ups

- [`ledger-p1-ci-install-profile-split-after-disk-unblock`](../roadmap/BACKLOG_LEDGER.md#ledger-p1-ci-install-profile-split-after-disk-unblock)
  remains gated until this prerequisite lands and representative feature/fix
  push evidence is reviewed.
- [`ledger-p2-ci-contract-risk-helper-extraction`](../roadmap/BACKLOG_LEDGER.md#ledger-p2-ci-contract-risk-helper-extraction)
  remains deferred; no helper extraction is included in this PR.
- [SBOM/VEX signed security artifacts](../roadmap/BACKLOG_LEDGER.md#ledger-p1-sbom-vex-signed-security-artifacts)
  remains blocked until release-truth closure.
- [Dagger pilot after Docker baseline](../roadmap/BACKLOG_LEDGER.md#ledger-p2-dagger-pilot-after-docker-baseline)
  remains P2 deferred/evaluation-only.

## Merge Readiness

- [ ] CI green on current head after review-fix push
- [ ] CodeRabbit actionable mapped as FIXED; Sourcery/Cubic statuses reviewed as no actionable repo change
- [ ] Fixed-mapping artifact and PR body are mirror-aligned for the known actionable
- [ ] `check_review_threads_disposition.py --require-auth` PASS
- [ ] `check_pr_merge_readiness.py` PASS
- [ ] `check_merge_ready.py --require-auth` PASS

## Additional Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1573#discussion_r3166113804 -> 0e59a7b12721b584a575e21fb2a2ef573df7e5c1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1573#pullrequestreview-4202982395 -> 0e59a7b12721b584a575e21fb2a2ef573df7e5c1
Disposition: FIXED
Commit: 0e59a7b12721b584a575e21fb2a2ef573df7e5c1
Evidence: `docs/review/PR_1573_FIXED_MAPPING.md:99-107` links each deferred follow-up to its canonical `BACKLOG_LEDGER.md` anchor.
