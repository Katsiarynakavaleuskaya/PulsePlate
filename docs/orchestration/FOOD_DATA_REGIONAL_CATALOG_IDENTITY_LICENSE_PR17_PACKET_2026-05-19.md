# Food Data PR17: Regional Catalog Identity License Review

## Summary

PR17 is a file-only governance lane downstream of merged PR16 `#1768`.
It records regional catalog identity and license candidates as review context
only, proves the PR16 handoff to `regional_catalog_identity_license_review`, and
keeps regional/local catalog source use blocked until exact provider identity,
license, retrieval contract, locale/language, units, schema, attribution, cache,
freshness, and redistribution evidence is reviewed in later dedicated lanes.

This packet does not approve API calls, scraping, downloads, paid provider use,
seller or partner API access, database writes, cache authority, redistribution,
product display, runtime source authority, nutrition authority, DigitalOcean
PostgreSQL load, OpenAPI changes, or runtime behavior.

## Coordinator Start

Bootstrap packet: `artifacts/orchestration/task_packets/10fc764884e7.json`

Dispatch note: `qoder_dispatch_bridge.py` could not consume bootstrap packet
`10fc764884e7` because the packet schema did not expose bridge-readable role
slugs. This PR therefore uses explicit manual role dispatch in the
coordinator-declared order below. The bridge incompatibility is not allowed to
skip the role-agent sequence and does not grant runtime/provider authority.

Role order unless coordinator updates this packet:

```text
agent-coordinator -> cursor-specialist-agent -> architecture-specialist -> security-auditor -> data-scientist-agent -> backend-engineer -> qa-engineer-agent -> bug-hunter -> dev-operator
```

Mandatory post-open role lane:

```text
qa-engineer-agent -> bug-hunter
```

## Scope

In scope:

- `docs/architecture/FOOD_DATA_REGIONAL_CATALOG_IDENTITY_LICENSE_PR17_2026-05-19.json`
- typed validator and deterministic report builder under `core/food_sources/`
- CLI wrapper under `scripts/`
- focused pytest coverage for valid artifact load, malformed artifact rejection,
  CLI success/failure, unsafe flag rejection, no-network/no-ingest/no-runtime
  authority invariants, PR16 handoff checks, PR11 regional catalog handoff
  checks, and PR3/PR5 unresolved regional catalog policy checks
- `docs/orchestration/FOOD_DATA_SOURCE_UPDATE_PREFLIGHT_CURRENT.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- fixed-mapping artifact and PR body mirror after PR number exists

Out of scope:

- API calls, scraping, downloads, paid provider access, seller API access, or
  partner API access
- provider integration, source onboarding, data ingest, restaurant ingest, or
  regional catalog loading
- database writes, cache authority, redistribution, product display, nutrition
  authority, or runtime source authority
- PostgreSQL cutover, OpenAPI changes, API behavior, or client behavior
- dependency-security fixes owned by separate dependency PRs

## Candidate Decisions

- `data_europa_national_portals`: open-data portal review candidate only; exact
  dataset identity and license remain unverified.
- `kroger` and `walmart`: regional price/availability candidates only; not
  nutrition authority.
- `pepesto_grocery`: commercial EU catalog candidate only.
- `pricesapi`: global price aggregator candidate only.
- `yandex_eda`: partner menu candidate only.
- `wildberries` and `ozon`: seller terms candidates only.
- `apify_scraping_providers`: blocked for PR17 and deferred to a later legal /
  anti-scraping packet.

Attached reports, spreadsheets, document analysis, and charts are evidence
inputs only. They do not become source authority, ingestion permission,
licensing truth, provider approval, or runtime truth.

## Premortem Findings

Frame: six months after merge, PR17 failed because a regional catalog review
artifact was treated as permission to use commercial, seller, partner, portal,
or scraping sources.

- Finding 1: evidence-only attached research could be promoted into source or
  nutrition authority.
  - Disposition: FIXED in validator/tests.
  - Evidence: `external_research_evidence_role` must stay
    `review_context_only_not_source_authority`; all authority flags remain
    false.
- Finding 2: broad portals such as `data.europa.eu` could be treated as exact
  dataset/license identity.
  - Disposition: FIXED in validator/tests.
  - Evidence: candidate rows require `provider_identity_status` and
    `license_status` to remain unverified.
- Finding 3: seller, partner, paid, or scraper providers could bypass a
  source-specific legal/terms packet.
  - Disposition: FIXED in validator/tests.
  - Evidence: seller API, partner API, paid use, scraping, download, cache,
    redistribution, provider integration, product display, and nutrition
    authority flags must remain false.
- Finding 4: PR17 could drift from PR11 and PR16 handoffs.
  - Disposition: FIXED in validator/tests.
  - Evidence: the report builder validates PR16
    `next_substantive_lane == regional_catalog_identity_license_review` and
    PR11 `regional_local_products` / `regional_catalogs` unresolved posture.

## Validation

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
VENV_PYTHON="${VENV_PYTHON:-.venv/bin/python}"
"${VENV_PYTHON}" -m pytest -q tests/test_food_source_regional_catalog_identity.py
"${VENV_PYTHON}" -m pytest -q tests/test_food_source_preference_mapping_closeout.py tests/test_food_source_gap_audit.py tests/test_food_source_catalog.py tests/test_food_source_onboarding.py
"${VENV_PYTHON}" -m pytest -q tests/test_repo_policy_guards.py
"${VENV_PYTHON}" -m scripts.food_source_regional_catalog_identity --json
pre-commit run --all-files
make validate-changed VENV_PYTHON="${VENV_PYTHON}"
```

Full local `make verify` is intentionally not the default for this
governance-only lane per operator instruction; merge readiness still requires
PR current-head CI parity and strict review-governance checks.

Worktree note: if the isolated worktree does not contain its own `.venv`, point
`VENV_PYTHON` at an existing repo-compatible virtualenv before running the
validation bundle.

## Post-Open Governance

After the non-draft PR exists, PR17 must add
`docs/review/PR_<N>_FIXED_MAPPING.md` and mirror the same governance sections in
the PR body before any readiness claim. Required post-open steps:

```bash
python3 scripts/orchestration/task_bootstrap.py --goal "Food Data PR17 regional catalog identity license review" --task-class Orchestration --pr-phase post_open_review --requested-agent agent-coordinator --requested-agent security-auditor --requested-agent data-scientist-agent --requested-agent backend-engineer --requested-agent qa-engineer-agent --requested-agent bug-hunter --requested-agent dev-operator --path docs/orchestration/FOOD_DATA_SOURCE_UPDATE_PREFLIGHT_CURRENT.md --path docs/roadmap/BACKLOG_LEDGER.md --path docs/architecture --path core/food_sources --path scripts --path tests
GH_TOKEN="$(gh auth token)" python3 scripts/orchestration/check_review_threads_disposition.py --pr-number <N> --require-auth
GITHUB_TOKEN="$(gh auth token)" python3 scripts/ci/check_pr_merge_readiness.py --pr-number <N> --repo Katsiarynakavaleuskaya/PulsePlate
gh pr checks <N> --repo Katsiarynakavaleuskaya/PulsePlate
```

The post-open role lane remains `qa-engineer-agent -> bug-hunter`, followed by
CodeRabbit review, Codex Security diff-scoped scan, security-auditor pass, and
current-head check inspection. Every human, bot, premortem, role-agent, and
security finding must be `FIXED`, `NOT-A-BUG`, or `DEFERRED` with evidence in
the mapping artifact and PR body mirror before merge readiness.
