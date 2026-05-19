# Food Data PR16: Preference Recipe Mapping Contract Review Closeout

## Summary

PR16 is a file-only governance closeout lane downstream of merged PR15 `#1747`.
It updates the food-data source-update preflight source of truth after the PR15
preference-to-recipe mapping contract and records the next bounded food-data
lane as `regional_catalog_identity_license_review`.

This packet does not approve API calls, scraping, downloads, paid provider use,
recipe ingest, restaurant ingest, database writes, cache authority, product
display, runtime source authority, DigitalOcean PostgreSQL load, OpenAPI
changes, or runtime behavior.

## Coordinator Start

Bootstrap packet: `artifacts/orchestration/task_packets/810d06e7f204.json`

Operator note: root `main` was checked out in another worktree during startup,
so this PR16 lane starts from an isolated worktree based on `origin/main`
without taking ownership of the existing `main` worktree.

Dispatch note: `qoder_dispatch_bridge.py` could not consume bootstrap packet
`810d06e7f204` because the current packet schema did not expose bridge-readable
role slugs. This PR therefore uses explicit manual role dispatch in the
coordinator-declared order below. The bridge incompatibility is not allowed to
skip the role-agent sequence and does not grant runtime/provider authority.

Role order unless coordinator updates this packet:

```text
agent-coordinator -> security-auditor -> data-scientist-agent -> backend-engineer -> qa-engineer-agent -> bug-hunter -> dev-operator
```

Mandatory post-open role lane:

```text
qa-engineer-agent -> bug-hunter
```

## Scope

In scope:

- `docs/architecture/FOOD_DATA_PREFERENCE_RECIPE_MAPPING_CLOSEOUT_PR16_2026-05-19.json`
- typed validator and deterministic report builder under `core/food_sources/`
- CLI wrapper under `scripts/`
- focused pytest coverage for valid artifact load, malformed artifact rejection,
  CLI success/failure, unsafe flag rejection, no-network/no-ingest/no-runtime
  authority invariants, PR15 handoff checks, and PR11 regional catalog handoff
  checks
- `docs/orchestration/FOOD_DATA_SOURCE_UPDATE_PREFLIGHT_CURRENT.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- fixed-mapping artifact and PR body mirror after PR number exists

Out of scope:

- API calls, scraping, downloads, or paid provider access
- recipe text ingest, restaurant menu ingest, or provider integration
- database writes, cache authority, redistribution, or product display
- runtime source authority, PostgreSQL cutover, OpenAPI changes, or API behavior

## Premortem Findings

Frame: six months after merge, PR16 failed because a closeout packet was treated
as permission to use paid providers or external research artifacts as nutrition
authority.

- Finding 1: PR16 could accidentally promote the attached report/spreadsheet/docx
  or charts into source authority.
  - Disposition: FIXED in planned validator/tests.
  - Evidence: `external_research_evidence_role` must stay
    `review_context_only_not_source_authority`.
- Finding 2: budget-first policy could be misread as permission to scrape or buy
  provider data immediately.
  - Disposition: FIXED in planned validator/tests.
  - Evidence: paid provider, scraper, snapshot, and runtime cutover follow-ups
    remain deferred.
- Finding 3: PR16 could choose a next lane that bypasses PR11 unresolved regional
  catalog governance.
  - Disposition: FIXED in planned validator/tests.
  - Evidence: validator cross-checks PR11 `regional_local_products.next_action`.

## Validation

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
VENV_PYTHON="${VENV_PYTHON:-.venv/bin/python}"
"${VENV_PYTHON}" -m pytest -q tests/test_food_source_preference_mapping_closeout.py
"${VENV_PYTHON}" -m pytest -q tests/test_food_source_preference_recipe_mapping.py tests/test_food_source_gap_audit.py tests/test_food_source_catalog.py tests/test_food_source_onboarding.py
"${VENV_PYTHON}" -m pytest -q tests/test_repo_policy_guards.py
"${VENV_PYTHON}" -m scripts.food_source_preference_mapping_closeout --json
pre-commit run --all-files
make validate-changed VENV_PYTHON="${VENV_PYTHON}"
```

Full local `make verify` is intentionally not the default for this governance-only
lane per operator instruction; merge readiness still requires PR current-head CI
parity and strict review-governance checks.

Worktree note: if the isolated worktree does not contain its own `.venv`, either
create one with the repo's normal environment setup or point `VENV_PYTHON` at an
existing repo-compatible virtualenv before running the validation bundle.

## Post-Open Governance

After the non-draft PR exists, PR16 must add
`docs/review/PR_<N>_FIXED_MAPPING.md` and mirror the same governance sections in
the PR body before any readiness claim. Required post-open steps:

```bash
python3 scripts/orchestration/task_bootstrap.py --goal "Food Data PR16 preference recipe mapping contract review closeout" --task-class Orchestration --pr-phase post_open_review --requested-agent agent-coordinator --requested-agent security-auditor --requested-agent data-scientist-agent --requested-agent backend-engineer --requested-agent qa-engineer-agent --requested-agent bug-hunter --requested-agent dev-operator --path docs/orchestration/FOOD_DATA_SOURCE_UPDATE_PREFLIGHT_CURRENT.md --path docs/roadmap/BACKLOG_LEDGER.md --path docs/architecture --path core/food_sources --path scripts --path tests
GH_TOKEN="$(gh auth token)" python3 scripts/orchestration/check_review_threads_disposition.py --pr-number <N> --require-auth
GITHUB_TOKEN="$(gh auth token)" python3 scripts/ci/check_pr_merge_readiness.py --pr-number <N> --repo Katsiarynakavaleuskaya/PulsePlate
gh pr checks <N> --repo Katsiarynakavaleuskaya/PulsePlate
```

The post-open role lane remains `qa-engineer-agent -> bug-hunter`, followed by
CodeRabbit review, Codex Security diff-scoped scan, security-auditor pass, and
current-head check inspection. Every human, bot, premortem, role-agent, and
security finding must be `FIXED`, `NOT-A-BUG`, or `DEFERRED` with evidence in
the mapping artifact and PR body mirror before merge readiness.
