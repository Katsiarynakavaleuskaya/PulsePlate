# Food Data PR18: Regional Catalog Provider Terms Matrix

## Summary

PR18 is a file-only governance lane downstream of merged PR17 `#1771`.
It records the PR17 regional catalog candidate set as a provider terms matrix,
proves the PR17 handoff to `regional_catalog_provider_terms_matrix`, and keeps
every candidate evidence-only until a later source-specific terms packet
verifies exact terms, account access, retrieval contract, license, cache,
redistribution, attribution, display, and authority boundaries.

This packet does not approve API calls, scraping, downloads, paid provider use,
seller or partner API access, database writes, cache authority, redistribution,
product display, runtime source authority, nutrition authority, DigitalOcean
PostgreSQL load, OpenAPI changes, or runtime behavior.

## Coordinator Start

Bootstrap packet: `artifacts/orchestration/task_packets/ddad07b7789b.json`

Role order declared by coordinator:

```text
agent-coordinator -> architecture-specialist -> cursor-specialist-agent -> security-auditor -> data-scientist-agent -> backend-engineer -> qa-engineer-agent -> bug-hunter -> dev-operator
```

Mandatory post-open role lane:

```text
qa-engineer-agent -> bug-hunter
```

Required review helpers:

- `pulseplate-premortem-risk-review`: completed before scope lock; findings
  below are closed by validator/tests/artifact posture.
- `pulseplate-ledger`: update the canonical food-data backlog item and current
  packet pointer.
- `pulseplate-graphmap`: run deterministic builder; commit generated graph only
  when the builder produces a deterministic diff.
- Experiment Runner: run after a real diff exists in oracle-only governance
  reviewer mode. Record the result artifact in PR body/fixed mapping; add the
  official co-author trailer only if the result materially changes commit
  content or engineering decisions.
- CodeRabbit and Codex Security: post-open only, after the non-draft PR exists.

## Scope

In scope:

- `docs/architecture/FOOD_DATA_REGIONAL_CATALOG_PROVIDER_TERMS_MATRIX_PR18_2026-05-21.json`
- typed validator and deterministic report builder under `core/food_sources/`
- CLI wrapper under `scripts/`
- focused pytest coverage for valid artifact load, malformed artifact rejection,
  CLI success/failure, JSON smoke, unsafe flag/prose rejection, exact PR17
  handoff, exact candidate set, and evidence-only provider posture
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

- `data_europa_national_portals`: public open-data portal umbrella, review-only
  until exact dataset terms and license are verified.
- `kroger` and `walmart`: commercial grocery API candidates, review-only.
- `pepesto_grocery`: commercial EU grocery API candidate, review-only.
- `pricesapi`: commercial price aggregator candidate, review-only.
- `yandex_eda`: partner menu API candidate, review-only.
- `wildberries` and `ozon`: seller marketplace API candidates, review-only.
- `apify_scraping_providers`: scraping-provider candidate, blocked for this
  lane and deferred to dedicated legal / anti-scraping governance.

Attached reports, spreadsheets, document analysis, and charts are evidence
inputs only. They do not become source authority, ingestion permission,
licensing truth, provider approval, or runtime truth.

## Premortem Findings

Frame: six months after merge, PR18 failed because a provider terms matrix was
treated as permission to use commercial, seller, partner, portal, or scraping
sources.

- Finding 1: terms matrix wording could be read as provider approval.
  - Disposition: FIXED in validator/tests.
  - Evidence: `allowed_role` must be `review_only_no_provider_use`; unsafe
    provider/source approval prose is rejected.
- Finding 2: candidate set could drift from PR17.
  - Disposition: FIXED in validator/tests.
  - Evidence: PR18 validates PR17 report success, PR17 next lane, exact candidate
    IDs, and PR17 candidate row fields.
- Finding 3: API/scraper/seller/partner/premium routes could bypass dedicated
  terms governance.
  - Disposition: FIXED in validator/tests.
  - Evidence: unsafe flags for API calls, scraping, downloads, paid use, seller
    or partner access, cache, redistribution, runtime, product display, nutrition
    authority, and DB writes must remain false.
- Finding 4: Experiment Runner evidence could become ambiguous attribution.
  - Disposition: FIXED by process.
  - Evidence: the PR records whether Experiment Runner materially shaped
    decisions; co-author trailer is added only when that is true.
- Finding 5: GraphMap could become noisy hand-edited drift.
  - Disposition: FIXED by process.
  - Evidence: GraphMap is updated only through `tools/graphmap/build_graph.py`
    and checked for deterministic output.

## Validation

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
VENV_PYTHON="${VENV_PYTHON:-.venv/bin/python}"
"${VENV_PYTHON}" -m pytest -q tests/test_food_source_regional_catalog_provider_terms.py
"${VENV_PYTHON}" -m pytest -q tests/test_food_source_regional_catalog_identity.py tests/test_food_source_preference_mapping_closeout.py tests/test_food_source_gap_audit.py tests/test_food_source_catalog.py tests/test_food_source_onboarding.py
"${VENV_PYTHON}" -m pytest -q tests/test_repo_policy_guards.py
"${VENV_PYTHON}" -m scripts.food_source_regional_catalog_provider_terms --json
python tools/graphmap/build_graph.py --out docs/graph/graph.json
python tools/graphmap/build_graph.py --out /tmp/pulseplate_pr18_graph_tmp.json
shasum -a 256 docs/graph/graph.json /tmp/pulseplate_pr18_graph_tmp.json
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

After the non-draft PR exists, PR18 must add
`docs/review/PR_<N>_FIXED_MAPPING.md` and mirror the same governance sections in
the PR body before any readiness claim. Required post-open steps:

```bash
python3 scripts/orchestration/task_bootstrap.py --goal "Food Data PR18 regional catalog provider terms matrix" --task-class Orchestration --pr-phase post_open_review --requested-agent agent-coordinator --requested-agent architecture-specialist --requested-agent security-auditor --requested-agent data-scientist-agent --requested-agent backend-engineer --requested-agent qa-engineer-agent --requested-agent bug-hunter --requested-agent dev-operator --path docs/orchestration/FOOD_DATA_SOURCE_UPDATE_PREFLIGHT_CURRENT.md --path docs/roadmap/BACKLOG_LEDGER.md --path docs/architecture --path core/food_sources --path scripts --path tests
GH_TOKEN="$(gh auth token)" python3 scripts/orchestration/check_review_threads_disposition.py --pr-number <N> --require-auth
GITHUB_TOKEN="$(gh auth token)" python3 scripts/ci/check_pr_merge_readiness.py --pr-number <N> --repo Katsiarynakavaleuskaya/PulsePlate
gh pr checks <N> --repo Katsiarynakavaleuskaya/PulsePlate
```

The post-open role lane remains `qa-engineer-agent -> bug-hunter`, followed by
CodeRabbit review, Codex Security diff-scoped scan, security-auditor pass, and
current-head check inspection. Every human, bot, premortem, role-agent,
Experiment Runner, and security finding must be `FIXED`, `NOT-A-BUG`, or
`DEFERRED` with evidence in the mapping artifact and PR body mirror before
merge readiness.
