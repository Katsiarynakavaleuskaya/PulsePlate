# PR #2065 Fixed in Commit Mapping

## Scope

PR #2065 documents and hardens the existing authenticated principal mapping
contract with docs/tests only.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/a0d678a19b80.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Branch: `codex/auth-principal-mapping-contract`

Material implementation commit:

- `ab417ff6b` - adds `docs/security/AUTHENTICATED_PRINCIPAL_MAPPING.md`,
  `docs/review/PR_AUTH_PRINCIPAL_MAPPING_PREMORTEM.md`, and
  `tests/security/test_authenticated_principal_mapping.py`.

## Discussion Thread Pass

- [x] Discussion-thread pass completed.
- [x] Fixed in commit mapping completed.
- [x] Post-open `qa-engineer-agent` pass completed.
- [x] Post-open `bug-hunter` pass completed.
- [x] Post-open `security-auditor` pass completed.
- [ ] Codex Security diff scan / finding discovery completed.
- [ ] `pulseplate-pr-review` completed.
- [ ] CodeRabbit actionable review comments checked and dispositioned.
- [ ] Sourcery actionable review comments checked and dispositioned.
- [ ] Cubic actionable review comments checked and dispositioned.
- [ ] Current-head CI complete before readiness language.
- [ ] Strict merge-readiness checks run after the final review/check cycle.

No GitHub review discussion threads existed when this artifact was created.
Future actionable human, bot, role-agent, premortem, Experiment Runner, or
Codex Security findings must be added here with disposition evidence before
merge-readiness claims.

## Fixed in Commit Mapping

- No actionable review comments

## Post-Open Role Findings

### QA Engineer Agent

- Finding: no-overclaim guard was too literal and could miss equivalent claims
  such as live runtime alerts, production emission of alert labels, or full BOLA
  closure wording.
  - Disposition: FIXED
  - Commit: `8c3d7bb38`
  - Evidence:
    `tests/security/test_authenticated_principal_mapping.py::test_docs_do_not_claim_runtime_alerting_or_full_bola_closure`
    now normalizes docs text and blocks expanded overclaim variants.
- Finding: local evidence used `.venv/bin/python` as though the isolated
  worktree owned a local venv.
  - Disposition: FIXED
  - Commit: `8c3d7bb38`
  - Evidence: this artifact records the focused bundle with the repo-resolved
    `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"`
    form.

### Bug Hunter

- Finding: canonical fixed-mapping artifact and PR body mirror were missing the
  Phase 2 mapping contract shape, including checked discussion/mapping
  checkboxes, parser-valid `## Fixed in Commit Mapping` content, and literal
  Experiment Runner `Artifact:` evidence.
  - Disposition: FIXED
  - Commit: `cfd7102b7`
  - Evidence:
    `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 2065` passes,
    and `python3 scripts/orchestration/check_review_threads_disposition.py --pr-number 2065`
    reports no resolved review threads to enforce.

### Security Auditor

Disposition: NOT-A-BUG
Source: post-open `security-auditor`
Evidence: The security-auditor pass on head `2eb40400a` found no false
principal-source mapping, billing entitlement confusion, credential-derived
subject overclaim, SEC-001 overclaim, live telemetry overclaim, or fail-open
test assumption in this docs/tests-only diff.

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
- Artifact:
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
