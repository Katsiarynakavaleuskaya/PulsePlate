# Food Data PR21: Regional Catalog Dedicated Legal Contract Review

## Summary

PR21 is a file-only governance lane downstream of merged PR20 `#1815`. It records
dedicated legal/contract review requirements for the inherited regional catalog
candidate set while keeping every source and provider route blocked until a
later authority-specific PR explicitly approves it.

This packet does not approve network calls, API calls, scraping, downloads,
account access, paid provider use, seller or partner API access, database
writes, cache authority, redistribution, product display, runtime source
authority, source authority, nutrition authority, DigitalOcean PostgreSQL load,
OpenAPI changes, connector writes, or runtime behavior.

## Coordinator Start

Bootstrap packet:

- `artifacts/orchestration/task_packets/eb95bc5061f3.json`

Dispatch manifest:

- `python3 scripts/orchestration/qoder_dispatch_bridge.py --packet artifacts/orchestration/task_packets/eb95bc5061f3.json --mode docs-only --pretty`

Role order captured before implementation:

```text
agent-coordinator -> architecture-specialist -> data-scientist-agent -> backend-engineer -> qa-engineer-agent -> bug-hunter -> security-auditor -> dev-operator -> cursor-specialist-agent
```

Pre-open role-agent findings:

- `agent-coordinator`: PASS; keep PR21 governance/file-only, validate PR20
  handoff, run every declared role, premortem, Experiment Runner, focused gates,
  and full `make verify`.
- `architecture-specialist`: PASS; preserve exact PR20 candidate order and keep
  legal/contract review as review-only documentation, not source authority.
- `data-scientist-agent`: PASS; preserve low/unverified evidence confidence and
  do not upgrade provider terms into usable data authority.
- `backend-engineer`: PASS; keep a pure typed validator/report builder and a
  thin CLI; no runtime, API, DB, cache, provider, or OpenAPI changes.
- `qa-engineer-agent`: PASS; require canonical load/report, malformed artifact,
  CLI, unsafe prose, exact handoff, adjacent regressions, mypy, pre-commit,
  `make validate-changed`, and full `make verify`.
- `bug-hunter`: PASS; guard approval-sounding legal prose, candidate drift,
  inherited-field drift, evidence-overreach, and CLI failure paths.
- `security-auditor`: PASS; reject source/provider/API/account/download/cache/
  redistribution/product/nutrition/runtime authority flags and prose.
- `dev-operator`: PASS; open ready-for-review only after local gates, then rerun
  post-open bootstrap, role agents, bot/security reviews, current-head checks,
  disposition guard, wait-window, merge, sync, cleanup, and sanity.
- `cursor-specialist-agent`: PASS; no cursor rule changes required for this
  governance-only lane.

## Scope

In scope:

- `core/food_sources/regional_catalog_dedicated_legal_contract_review.py`
- `scripts/food_source_regional_catalog_dedicated_legal_contract_review.py`
- `tests/test_food_source_regional_catalog_dedicated_legal_contract_review.py`
- `docs/architecture/FOOD_DATA_REGIONAL_CATALOG_DEDICATED_LEGAL_CONTRACT_REVIEW_PR21_2026-05-25.json`
- this packet
- `docs/orchestration/FOOD_DATA_SOURCE_UPDATE_PREFLIGHT_CURRENT.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- post-open fixed mapping and PR body mirror after the PR number exists

Out of scope:

- Provider/API/seller/partner account use
- Scraping, downloads, automated collection, browser collection, or connector writes
- Source ingest, cache, redistribution, product display, nutrition authority, or
  runtime source authority
- DB writes, DigitalOcean PostgreSQL staging/load, OpenAPI/client changes, or
  runtime behavior
- Legal approval or legal advice

## Legal-Contract Review Contract

PR21 validates:

- PR20 artifact path:
  `docs/architecture/FOOD_DATA_REGIONAL_CATALOG_SOURCE_SPECIFIC_TERMS_CLOSEOUT_PR20_2026-05-24.json`
- PR20 merged PR: `#1815`
- PR20 merge marker: `PR #1815 merged before PR21 scope lock`
- PR20 handoff:
  `next_recommended_lane == regional_catalog_dedicated_legal_contract_review`
- PR20 final gate:
  `regional_catalog_source_specific_terms_closeout_only_no_provider_use`
- inherited candidate order:
  `data_europa_national_portals`, `kroger`, `walmart`,
  `pepesto_grocery`, `pricesapi`, `yandex_eda`, `wildberries`, `ozon`,
  `apify_scraping_providers`

Every candidate remains `review_only_no_provider_use` with
`next_required_review == dedicated_legal_contract_review_required` and
`evidence_confidence == low_unverified`. PR21 adds legal-contract review fields,
but every legal/contract/source/provider decision remains `not_approved`,
`blocked_unresolved`, `blocked_not_approved`, `blocked_not_authority`, or
`unverified`.

## Premortem Findings

Frame: six months after merge, PR21 failed because legal-review wording was
treated as source/provider approval, candidate order drifted, or role/review
evidence became checkbox-only.

- PM-PR21-001: Legal-review wording could sound like approval.
  - Disposition: FIXED in validator/tests.
  - Evidence: controlled decision vocabulary and unsafe prose rejection block
    approval terms across top-level and candidate fields.
- PM-PR21-002: PR20 handoff or candidate order could drift.
  - Disposition: FIXED in validator/tests.
  - Evidence: PR20 report, final gate, candidate order, and inherited blocked
    statuses are exact validation inputs.
- PM-PR21-003: Public references or attached documents could be treated as
  source authority.
  - Disposition: FIXED in artifact/validator/tests.
  - Evidence: evidence role fields stay `review_context_only_not_*_authority`.
- PM-PR21-004: Role-agent and Experiment Runner provenance could become
  checkbox-only.
  - Disposition: FIXED in packet/process.
  - Evidence: role-agent dispatch status and Experiment Runner policy are
    validator-controlled artifact fields.
- PM-PR21-005: Type or coverage gaps could surface only after PR open.
  - Disposition: FIXED in validation plan.
  - Evidence: targeted mypy, focused tests, adjacent regressions, pre-commit,
    `make validate-changed`, and full `make verify` are required gates.

## Experiment Runner

Experiment Runner is mandatory after a real diff exists and before PR open in
`oracle_only_governance_reviewer` mode. Its local result artifact must live under
`artifacts/orchestration/experiments/results/` and be recorded in the PR body and
post-open fixed mapping. The commit trailer
`Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` is used only if
the artifact materially changes implementation, validation, admission, or commit
decisions; otherwise the PR records `Not applicable: reviewed but did not change
commit decisions`.

## Validation

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
VENV_PYTHON="${VENV_PYTHON:-.venv/bin/python}"
"${VENV_PYTHON}" -m pytest -q tests/test_food_source_regional_catalog_dedicated_legal_contract_review.py
"${VENV_PYTHON}" -m scripts.food_source_regional_catalog_dedicated_legal_contract_review --json
"${VENV_PYTHON}" -m mypy --no-incremental --cache-dir=/dev/null core/food_sources/regional_catalog_dedicated_legal_contract_review.py scripts/food_source_regional_catalog_dedicated_legal_contract_review.py tests/test_food_source_regional_catalog_dedicated_legal_contract_review.py
"${VENV_PYTHON}" -m pytest -q tests/test_food_source_regional_catalog_source_specific_terms_closeout.py tests/test_food_source_regional_catalog_source_specific_terms.py tests/test_food_source_regional_catalog_provider_terms.py tests/test_food_source_regional_catalog_identity.py tests/test_food_source_preference_mapping_closeout.py tests/test_food_source_gap_audit.py tests/test_food_source_catalog.py tests/test_food_source_onboarding.py
"${VENV_PYTHON}" -m pytest -q tests/test_repo_policy_guards.py
pre-commit run --all-files
make validate-changed VENV_PYTHON="${VENV_PYTHON}"
make verify
```

## Post-Open Governance

After the non-draft PR exists, PR21 must add
`docs/review/PR_<N>_FIXED_MAPPING.md` and mirror the same governance sections
in the PR body before any readiness claim. Required post-open steps:

```bash
python3 scripts/orchestration/task_bootstrap.py --goal "Food Data PR21 regional catalog dedicated legal contract review" --task-class Orchestration --pr-phase post_open_review --requested-agent agent-coordinator --requested-agent architecture-specialist --requested-agent security-auditor --requested-agent data-scientist-agent --requested-agent backend-engineer --requested-agent qa-engineer-agent --requested-agent bug-hunter --requested-agent dev-operator --path docs/orchestration/FOOD_DATA_SOURCE_UPDATE_PREFLIGHT_CURRENT.md --path docs/roadmap/BACKLOG_LEDGER.md --path docs/architecture --path core/food_sources --path scripts --path tests
GH_TOKEN="$(gh auth token)" python3 scripts/orchestration/check_review_threads_disposition.py --pr-number <N> --require-auth
GITHUB_TOKEN="$(gh auth token)" python3 scripts/ci/check_pr_merge_readiness.py --pr-number <N> --repo Katsiarynakavaleuskaya/PulsePlate
gh pr checks <N> --repo Katsiarynakavaleuskaya/PulsePlate
```

The post-open role lane repeats every coordinator-declared role, including
advisory agents. The mandatory post-open `qa-engineer-agent -> bug-hunter`
sequence remains required, followed by CodeRabbit review, Codex Security
diff-scoped scan, security-auditor pass, and current-head check inspection.
Every human, bot, premortem, role-agent, Experiment Runner, and security finding
must be `FIXED`, `NOT-A-BUG`, or `DEFERRED` with evidence in the mapping artifact
and PR body mirror before merge readiness.
