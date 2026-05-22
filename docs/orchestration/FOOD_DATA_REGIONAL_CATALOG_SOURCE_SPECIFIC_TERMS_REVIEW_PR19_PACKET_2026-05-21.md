# Food Data PR19: Regional Catalog Source-Specific Terms Review

## Summary

PR19 is a file-only governance lane downstream of merged PR18 `#1783`.
It validates the PR18 regional catalog provider terms report, preserves the
exact PR18 candidate set and order, and records source-specific terms review
requirements for each candidate without approving any provider use.

This packet does not approve network calls, API calls, scraping, downloads,
account access, paid provider use, seller or partner API access, database
writes, cache authority, redistribution, product display, runtime source
authority, nutrition authority, DigitalOcean PostgreSQL load, OpenAPI changes,
or runtime behavior.

## Coordinator Start

Bootstrap packets:

- Root pre-worktree coordinator packet:
  `artifacts/orchestration/task_packets/cd933449cccf.json`
- PR19 worktree bootstrap packet:
  `artifacts/orchestration/task_packets/cd933449cccf.json`

Role order for this implementation lane:

```text
agent-coordinator -> architecture-specialist -> cursor-specialist-agent -> security-auditor -> data-scientist-agent -> backend-engineer -> qa-engineer-agent -> bug-hunter -> dev-operator
```

Required review helper:

- `pulseplate-premortem-risk-review`: applied as a risk checklist; findings are
  closed by validator/test/artifact posture.

## Scope

In scope:

- `core/food_sources/regional_catalog_source_specific_terms.py`
- `scripts/food_source_regional_catalog_source_specific_terms.py`
- `tests/test_food_source_regional_catalog_source_specific_terms.py`
- `docs/architecture/FOOD_DATA_REGIONAL_CATALOG_SOURCE_SPECIFIC_TERMS_REVIEW_PR19_2026-05-21.json`
- `docs/orchestration/FOOD_DATA_REGIONAL_CATALOG_SOURCE_SPECIFIC_TERMS_REVIEW_PR19_PACKET_2026-05-21.md`
- `docs/orchestration/FOOD_DATA_SOURCE_UPDATE_PREFLIGHT_CURRENT.md`
- `docs/roadmap/BACKLOG_LEDGER.md`

Out of scope:

- Provider/API/seller/partner account use
- Scraping, downloads, automated collection, or connector writes
- Source ingest, cache, redistribution, product display, nutrition authority, or
  runtime source authority
- DB writes, DigitalOcean PostgreSQL staging/load, OpenAPI/client changes, or
  runtime behavior

## Candidate Terms Review Rows

Each `candidate_source_specific_terms` row records:

- inherited PR18 identity fields and `pr18_allowed_role`
- inherited PR18 `provider_route_classification`
- `public_terms_reference` and `public_terms_reference_role`
- terms-document identity, account access, retrieval contract, license, cache,
  redistribution, display, attribution, product authority, and nutrition
  authority statuses
- `evidence_confidence`, `uncertainty_notes`, `blocking_reasons`,
  `allowed_role`, and `next_required_review`

Every candidate stays `review_only_no_provider_use`. Public references are
evidence pointers only and are not terms truth, source authority, provider
approval, runtime authority, product display permission, cache authority,
redistribution permission, or nutrition authority.

## Premortem Findings

Frame: six months after merge, PR19 failed because source-specific terms rows
were treated as approval to use providers.

- PM-PR19-001: source-specific terms review could be read as approval for
  provider/API/source use.
  - Disposition: FIXED in validator/tests.
  - Evidence: every candidate must remain `review_only_no_provider_use`; unsafe
    source/provider approval prose and booleans are rejected.
- PM-PR19-002: public evidence verification could cross into scraping,
  downloads, API calls, account access, or data collection.
  - Disposition: FIXED in artifact/validator/tests.
  - Evidence: `network_allowed`, `api_calls_allowed`,
    `source_download_allowed`, `scraping_allowed`, `account_access_allowed`,
    `provider_use_allowed`, and related flags must be `false`; public
    references use
    `candidate_public_reference_only_not_terms_or_source_authority`.
- PM-PR19-003: PR18 handoff could drift silently.
  - Disposition: FIXED in validator/tests.
  - Evidence: PR19 validates PR18 report success, PR18 next lane, exact
    candidate IDs/order, PR18 unsafe flags, and each PR18 candidate
    `next_required_review == source_specific_terms_packet_required`.
- PM-PR19-004: account/API/provider/source authority could leak through prose.
  - Disposition: FIXED in validator/tests.
  - Evidence: unsafe flags and approval prose for network/API/scraping/download,
    account access, paid, seller, partner, provider, DB, cache, redistribution,
    runtime, product, nutrition, and source authority are rejected.
- PM-PR19-005: full local `make verify` deferral could be under-documented and
  lead to an invalid readiness claim.
  - Disposition: FIXED in this packet and required PR body/fixed mapping.
  - Evidence: validation section documents focused gates, `make validate-changed`,
    `pre-commit run --all-files`, current-head CI parity, strict review-thread
    disposition, and merge-readiness checks before readiness.

## Validation

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
python3 scripts/orchestration/task_bootstrap.py --goal "Food Data PR19 regional catalog source-specific terms review" --task-class Orchestration --pr-phase pre_open --requested-agent agent-coordinator --requested-agent architecture-specialist --requested-agent security-auditor --requested-agent data-scientist-agent --requested-agent backend-engineer --requested-agent qa-engineer-agent --requested-agent bug-hunter --requested-agent dev-operator --path docs/orchestration/FOOD_DATA_SOURCE_UPDATE_PREFLIGHT_CURRENT.md --path docs/roadmap/BACKLOG_LEDGER.md --path docs/architecture --path core/food_sources --path scripts --path tests
VENV_PYTHON="${VENV_PYTHON:-.venv/bin/python}"
"${VENV_PYTHON}" -m pytest -q tests/test_food_source_regional_catalog_source_specific_terms.py
"${VENV_PYTHON}" -m pytest -q tests/test_food_source_regional_catalog_provider_terms.py tests/test_food_source_regional_catalog_identity.py tests/test_food_source_preference_mapping_closeout.py tests/test_food_source_gap_audit.py tests/test_food_source_catalog.py tests/test_food_source_onboarding.py
"${VENV_PYTHON}" -m pytest -q tests/test_repo_policy_guards.py
"${VENV_PYTHON}" -m scripts.food_source_regional_catalog_source_specific_terms --json
pre-commit run --all-files
make validate-changed VENV_PYTHON="${VENV_PYTHON}"
```

Full local `make verify` is deferred by operator instruction for this
governance-only lane. Readiness depends on the focused gates above, PR
current-head CI parity, strict review-thread disposition, and merge-readiness
checks.
