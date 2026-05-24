# Food Data PR20: Regional Catalog Source-Specific Terms Closeout

## Summary

PR20 is a file-only governance closeout lane downstream of merged PR19 `#1793`.
It validates the PR19 source-specific terms handoff, preserves the exact
regional catalog candidate set and order, records PR19 as merged, and carries
all unresolved legal/contract blockers into the next lane.

This packet does not approve network calls, API calls, scraping, downloads,
account access, paid provider use, seller or partner API access, database
writes, cache authority, redistribution, product display, runtime source
authority, source authority, nutrition authority, DigitalOcean PostgreSQL load,
OpenAPI changes, connector writes, or runtime behavior.

## Coordinator Start

Bootstrap packet:

- `artifacts/orchestration/task_packets/d4813d774a22.json`

Dispatch note: `qoder_dispatch_bridge.py --packet` emitted an incomplete role
sequence for this lane. PR20 therefore uses explicit manual role dispatch in
the coordinator-required order below. The bridge gap is not allowed to skip
requested or advisory agents.

Role order:

```text
agent-coordinator -> architecture-specialist -> security-auditor -> data-scientist-agent -> backend-engineer -> qa-engineer-agent -> bug-hunter -> dev-operator
```

Pre-open role-agent findings:

- `agent-coordinator`: BLOCKED until the full requested role sequence is
  actually run; fixed by captured manual dispatch before implementation.
- `architecture-specialist`: PASS; preserve file-only closeout, PR19 blocker
  status, exact candidate order, and typed pure validator/CLI boundaries.
- `security-auditor`: PASS; reject unsafe flags and unsafe approval prose.
- `data-scientist-agent`: PASS; use PR19 schema key
  `candidate_source_specific_terms` and preserve low/unverified evidence.
- `backend-engineer`: PASS; keep `core/` pure and CLI thin.
- `qa-engineer-agent`: PASS; require focused PR20 tests, CLI smoke, targeted
  mypy, adjacent regressions, pre-commit, and `make validate-changed`.
- `bug-hunter`: PASS; guard wrong matrix key, set-based candidate checks,
  unsafe prose, loose JSON typing, and CLI side effects.
- `dev-operator`: PASS; isolate branch/worktree and keep artifacts local.

## Scope

In scope:

- `core/food_sources/regional_catalog_source_specific_terms_closeout.py`
- `scripts/food_source_regional_catalog_source_specific_terms_closeout.py`
- `tests/test_food_source_regional_catalog_source_specific_terms_closeout.py`
- `docs/architecture/FOOD_DATA_REGIONAL_CATALOG_SOURCE_SPECIFIC_TERMS_CLOSEOUT_PR20_2026-05-24.json`
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

## Closeout Contract

PR20 validates:

- PR19 artifact path:
  `docs/architecture/FOOD_DATA_REGIONAL_CATALOG_SOURCE_SPECIFIC_TERMS_REVIEW_PR19_2026-05-21.json`
- PR19 merged PR: `#1793`
- PR19 merge marker: `PR #1793 merged before PR20 scope lock`
- PR19 handoff:
  `next_recommended_lane == regional_catalog_source_specific_terms_closeout`
- PR19 final gate:
  `regional_catalog_source_specific_terms_review_only_no_provider_use`
- inherited candidate order:
  `data_europa_national_portals`, `kroger`, `walmart`,
  `pepesto_grocery`, `pricesapi`, `yandex_eda`, `wildberries`, `ozon`,
  `apify_scraping_providers`

Every candidate remains `review_only_no_provider_use` with
`next_required_review == dedicated_legal_contract_review_required` and
`evidence_confidence == low_unverified`.

## Premortem Findings

Frame: six months after merge, PR20 failed because a closeout packet was treated
as source/provider approval or because required governance reviews were listed
but not actually run.

- PM-PR20-001: Closeout wording could become de facto source/provider approval.
  - Disposition: FIXED in validator/tests.
  - Evidence: unsafe flags and unsafe prose are rejected across top-level and
    candidate fields.
- PM-PR20-002: PR19 legal/contract blockers could be softened.
  - Disposition: FIXED in validator/tests.
  - Evidence: candidate rows must preserve every unverified, blocked, and
    review-only status from PR19.
- PM-PR20-003: Role-agent execution could be skipped because the dispatch bridge
  under-dispatched advisory roles.
  - Disposition: FIXED in packet/process.
  - Evidence: this packet records the full manually captured role sequence.
- PM-PR20-004: Typecheck gaps could surface only in CodeRabbit/CI.
  - Disposition: FIXED in validation plan.
  - Evidence: targeted mypy is a required pre-open gate.

## Validation

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
VENV_PYTHON="${VENV_PYTHON:-.venv/bin/python}"
"${VENV_PYTHON}" -m pytest -q tests/test_food_source_regional_catalog_source_specific_terms_closeout.py
"${VENV_PYTHON}" -m scripts.food_source_regional_catalog_source_specific_terms_closeout --json
"${VENV_PYTHON}" -m mypy --no-incremental --cache-dir=/dev/null core/food_sources/regional_catalog_source_specific_terms_closeout.py scripts/food_source_regional_catalog_source_specific_terms_closeout.py tests/test_food_source_regional_catalog_source_specific_terms_closeout.py
"${VENV_PYTHON}" -m pytest -q tests/test_food_source_regional_catalog_source_specific_terms.py tests/test_food_source_regional_catalog_provider_terms.py tests/test_food_source_regional_catalog_identity.py tests/test_food_source_preference_mapping_closeout.py tests/test_food_source_gap_audit.py tests/test_food_source_catalog.py tests/test_food_source_onboarding.py
"${VENV_PYTHON}" -m pytest -q tests/test_repo_policy_guards.py
pre-commit run --all-files
make validate-changed VENV_PYTHON="${VENV_PYTHON}"
```

Full local `make verify` is intentionally not the default for this
governance-only lane per operator instruction. Readiness depends on the focused
gates above, PR current-head CI parity, strict review-thread disposition, bot
review disposition, and merge-readiness checks.

## Post-Open Governance

After the non-draft PR exists, PR20 must add
`docs/review/PR_<N>_FIXED_MAPPING.md` and mirror the same governance sections
in the PR body before any readiness claim. Required post-open steps:

```bash
python3 scripts/orchestration/task_bootstrap.py --goal "Food Data PR20 regional catalog source-specific terms closeout" --task-class Orchestration --pr-phase post_open_review --requested-agent agent-coordinator --requested-agent architecture-specialist --requested-agent security-auditor --requested-agent data-scientist-agent --requested-agent backend-engineer --requested-agent qa-engineer-agent --requested-agent bug-hunter --requested-agent dev-operator --path docs/orchestration/FOOD_DATA_SOURCE_UPDATE_PREFLIGHT_CURRENT.md --path docs/roadmap/BACKLOG_LEDGER.md --path docs/architecture --path core/food_sources --path scripts --path tests
GH_TOKEN="$(gh auth token)" python3 scripts/orchestration/check_review_threads_disposition.py --pr-number <N> --require-auth
GITHUB_TOKEN="$(gh auth token)" python3 scripts/ci/check_pr_merge_readiness.py --pr-number <N> --repo Katsiarynakavaleuskaya/PulsePlate
gh pr checks <N> --repo Katsiarynakavaleuskaya/PulsePlate
```

The post-open role lane repeats every coordinator-declared role, including
advisory agents. The mandatory post-open `qa-engineer-agent -> bug-hunter`
sequence remains required, followed by CodeRabbit review, Codex Security
diff-scoped scan, security-auditor pass, and current-head check inspection.
Every human, bot, premortem, role-agent, and security finding must be `FIXED`,
`NOT-A-BUG`, or `DEFERRED` with evidence in the mapping artifact and PR body
mirror before merge readiness.
