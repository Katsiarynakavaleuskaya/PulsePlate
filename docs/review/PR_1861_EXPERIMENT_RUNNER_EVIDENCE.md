# PR #1861 - Experiment Runner Evidence Summary

## Purpose

Committed summary for the local Experiment Runner oracle result used by PR
#1861. Raw Experiment Runner JSON artifacts remain under gitignored
`artifacts/` by repo policy, so this document records the verifiable fields used
for PR governance without tracking local runtime artifacts.

## Local Artifact

- Path: `artifacts/orchestration/experiments/results/nightly-xdist-security-outcomes-oracle-result.json`
- SHA-256: `a23164e7f6972c1cba5156ad2ed1ff92e57292cf1942d11fa8981c5540450f2b`
- Status: `accepted`
- Runner mode: `oracle_only_governance_reviewer`
- Contribution kind: `oracle_review`
- Mutated paths: `[]`
- Co-author required: `true`
- Co-author reason: Experiment Runner oracle-only evidence shaped the nightly
  xdist stabilization PR validation and commit decision.

## Oracle Commands

- `python -m pytest --collect-only -q tests/test_experiment_slack_kpp_renderer.py::test_security_sensitive_headers` - PASS, return code 0, collected 2 cases.
- `python -m pytest -q -n 4 --dist=loadscope tests/test_experiment_slack_kpp_renderer.py::test_security_sensitive_headers tests/test_experiment_slack_kpp_renderer.py::test_security_sensitive_outcomes_frozen` - PASS, return code 0, 3 tests passed.

## Attribution

Every branch commit for this PR carries:

`Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

The final merge message must preserve that exact trailer.
