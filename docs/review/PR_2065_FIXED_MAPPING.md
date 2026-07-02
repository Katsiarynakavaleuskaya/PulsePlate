# PR #2065 Fixed in Commit Mapping

## Scope

PR #2065 documents and hardens the existing authenticated principal mapping
contract with docs/tests only.

Material implementation commit:

- `ab417ff6b` - adds `docs/security/AUTHENTICATED_PRINCIPAL_MAPPING.md`,
  `docs/review/PR_AUTH_PRINCIPAL_MAPPING_PREMORTEM.md`, and
  `tests/security/test_authenticated_principal_mapping.py`.

## Discussion Thread Pass

No GitHub review discussion threads existed when this artifact was created.
Future actionable human, bot, role-agent, premortem, Experiment Runner, or
Codex Security findings must be added here with disposition evidence before
merge-readiness claims.

## Premortem Findings

- R1 false full-BOLA closure interpretation - FIXED by scope wording and
  no-overclaim tests in `tests/security/test_authenticated_principal_mapping.py`.
- R2 runtime alerting overclaim - FIXED by future-only alert wording and
  no-overclaim tests.
- R3 manual billing / paid entitlement confusion - FIXED by issuer-scoped
  billing contract tests.
- R4 legacy alias weaker-than-canonical risk - FIXED for the representative
  alias/canonical paid-route pair.
- R5 accidental new auth model interpretation - FIXED by derived-subject
  boundary wording and docs tests.

## Experiment Runner Evidence

- Packet:
  `artifacts/orchestration/experiments/auth-principal-mapping-contract-experiment-packet-macos.json`
- Result:
  `artifacts/orchestration/experiments/results/auth-principal-mapping-contract-oracle-macos.json`
- Mode: `oracle_only_governance_reviewer`
- Status: accepted
- Source diff paths:
  - `docs/review/PR_AUTH_PRINCIPAL_MAPPING_PREMORTEM.md`
  - `docs/security/AUTHENTICATED_PRINCIPAL_MAPPING.md`
  - `tests/security/test_authenticated_principal_mapping.py`
- Oracle commands:
  - focused 39-test authenticated-principal/auth-tier/BOLA/manual-billing bundle
  - docs phase-1 gate for the new security/review docs
- Shared tree untouched: true
- Co-author required: true

## Local Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")" && "$VENV_PYTHON" -m pytest -q tests/security/test_authenticated_principal_mapping.py tests/security/test_api_auth_tier_contract_pack.py tests/security/test_api_bola_contract_pack.py tests/guards/test_manual_billing_auth_contract_guard.py tests/test_paid_route_guards.py`
  -> 39 passed
- PASS: `python3 scripts/ci/check_docs_phase1_gates.py --files docs/security/AUTHENTICATED_PRINCIPAL_MAPPING.md docs/review/PR_AUTH_PRINCIPAL_MAPPING_PREMORTEM.md`
- PASS: `python3 scripts/ci/check_python_dependency_surfaces.py`
- PASS: `python3 verify_requirements.py`
- PASS:
  `python3 scripts/ci/install_locked_python_requirements.py --preflight-only`
  with canonical `PULSEPLATE_PYTHON_INDEX_URL`
- PASS: `git diff --check`
- PASS: `make validate-changed` -> selected
  `tests/security/test_authenticated_principal_mapping.py`, 9 passed
- PASS: `pre-commit run --all-files`
- PASS: push hooks, including pip-audit, backend pre-push tests, and full-repo
  Bandit
- PASS: `python3 scripts/orchestration/check_experiment_runner_identity.py --json`

## Merge Readiness

Not claimed. Current-head CI, post-open role passes, one Codex Security pass on
the material diff, bot review disposition, and strict merge-readiness governance
remain required before any merge-readiness claim.
