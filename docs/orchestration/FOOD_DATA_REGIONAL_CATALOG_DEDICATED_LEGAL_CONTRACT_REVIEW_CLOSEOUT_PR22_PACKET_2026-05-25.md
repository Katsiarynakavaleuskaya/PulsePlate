# Food Data PR22 Dedicated Legal Contract Review Closeout Packet

## Purpose

Close the PR21 regional catalog dedicated legal/contract review lane as
governance-only documentation and validation. This packet does not approve any
regional catalog source, provider, API route, account access, paid plan,
scraping, download, ingest, cache authority, runtime authority, product display,
nutrition authority, source authority, redistribution, or connector write.

Canonical artifact:
[`FOOD_DATA_REGIONAL_CATALOG_DEDICATED_LEGAL_CONTRACT_REVIEW_CLOSEOUT_PR22_2026-05-25.json`](../architecture/FOOD_DATA_REGIONAL_CATALOG_DEDICATED_LEGAL_CONTRACT_REVIEW_CLOSEOUT_PR22_2026-05-25.json)

Canonical CLI:
`python -m scripts.food_source_regional_catalog_dedicated_legal_contract_review_closeout --json`

## Startup Evidence

- Main sync and health were checked before PR22 implementation work continued.
- Preflight passed: `python3 scripts/orchestration/check_preflight.py`.
- Agent consistency passed:
  `python3 scripts/orchestration/check_agent_consistency.py`.
- Coordinator bootstrap packet:
  `artifacts/orchestration/task_packets/6538794d0fae.json` (local-only,
  not committed).
- Dispatch manifest was generated with:
  `python3 scripts/orchestration/qoder_dispatch_bridge.py --packet artifacts/orchestration/task_packets/6538794d0fae.json --mode docs-only --pretty`.

Coordinator-declared role order:

1. `agent-coordinator`
2. `architecture-specialist`
3. `data-scientist-agent`
4. `backend-engineer`
5. `qa-engineer-agent`
6. `bug-hunter`
7. `security-auditor`
8. `dev-operator`
9. `cursor-specialist-agent`

All declared pre-open role agents were run. `dev-operator` and
`cursor-specialist-agent` correctly blocked on an already-existing PR22
worktree and untracked PR22 files. The operator explicitly approved using those
existing untracked files as the working data for this lane before staging,
committing, pushing, or opening the PR. This packet records that provenance
exception; it does not relax future coordinator-first sequencing.

Mandatory post-open lane:
`qa-engineer-agent -> bug-hunter -> security-auditor`, followed by current-head
checks and review-thread disposition guard.

## Scope

In scope:

- PR22 closeout artifact and packet.
- Typed file-only validator/report builder and thin CLI.
- Focused tests covering canonical success, malformed artifact rejection, PR21
  handoff drift, candidate order, unsafe flags/prose, CLI failure/success, and
  file-only import surface.
- Current food-data preflight pointer and backlog ledger update.

Out of scope:

- Runtime APIs, OpenAPI behavior, DB schema, DB writes, ingestion, scraping,
  downloads, API calls, provider/account/paid use, cache authority, product
  display, nutrition authority, source authority, redistribution approval,
  connector writes, and DigitalOcean/PostgreSQL load or cutover.

## Handoff Contract

PR22 validates:

- PR21 artifact path:
  `docs/architecture/FOOD_DATA_REGIONAL_CATALOG_DEDICATED_LEGAL_CONTRACT_REVIEW_PR21_2026-05-25.json`.
- PR21 merge marker: `PR #1829 merged before PR22 scope lock`.
- PR21 `next_recommended_lane`:
  `regional_catalog_dedicated_legal_contract_review_closeout`.
- PR21 final gate:
  `regional_catalog_dedicated_legal_contract_review_only_no_source_or_provider_use`.
- Exact candidate order:
  `data_europa_national_portals`, `kroger`, `walmart`, `pepesto_grocery`,
  `pricesapi`, `yandex_eda`, `wildberries`, `ozon`,
  `apify_scraping_providers`.
- Evidence-only posture and all false unsafe authority flags.

PR22 sets the next lane to the artifact-owned value:
`regional_catalog_legal_contract_packet_handoff`.

## Premortem Dispositions

- `PM-PR22-001`: stale PR21 handoff. Disposition: FIXED by exact PR21 lane,
  merge, final-gate, and candidate-order validation.
- `PM-PR22-002`: closeout approval drift. Disposition: FIXED by controlled
  closeout text and unsafe prose rejection.
- `PM-PR22-003`: missing-field false-green. Disposition: FIXED by required
  closeout fields and malformed-artifact tests.
- `PM-PR22-004`: Experiment Runner evidence drift. Disposition: FIXED by
  requiring oracle-only local-result status in artifact, PR body, and fixed
  mapping.
- `PM-PR22-005`: local artifact leakage. Disposition: FIXED by keeping
  `artifacts/orchestration/**` local-only and checking git status before push.
- `PM-PR22-006`: pre-gate worktree provenance drift. Disposition: FIXED by
  explicit operator approval to reuse existing untracked PR22 files before
  staging, plus this packet and PR-body/fixed-mapping evidence.

## Experiment Runner

Experiment Runner is mandatory for PR22 after a real diff exists and before PR
open. Use `oracle_only_governance_reviewer` mode. Result artifacts stay local
under `artifacts/orchestration/experiments/results/` and must not be committed.

Pre-open result:

- Packet: `artifacts/orchestration/experiments/exp-9cbf3a6cf3f3.json`
- Result:
  `artifacts/orchestration/experiments/results/exp-9cbf3a6cf3f3.json`
- Status: accepted
- Oracles: PR22 CLI JSON smoke, focused PR22 pytest, and focused PR22 mypy all
  returned 0.
- Contribution decision:
  `Not applicable: reviewed but did not change commit decisions`.

Attribution rule:

- Add `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` only if
  the artifact materially changes implementation, validation, admission, or
  commit decisions.
- Otherwise record:
  `Not applicable: reviewed but did not change commit decisions`.

## Local Gates

Run before opening the PR:

```bash
VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python
"${VENV_PYTHON}" -m pytest -q tests/test_food_source_regional_catalog_dedicated_legal_contract_review_closeout.py
"${VENV_PYTHON}" -m scripts.food_source_regional_catalog_dedicated_legal_contract_review_closeout --json
"${VENV_PYTHON}" -m mypy --no-incremental --cache-dir=/dev/null core/food_sources/regional_catalog_dedicated_legal_contract_review_closeout.py scripts/food_source_regional_catalog_dedicated_legal_contract_review_closeout.py tests/test_food_source_regional_catalog_dedicated_legal_contract_review_closeout.py
"${VENV_PYTHON}" -m pytest -q tests/test_food_source_regional_catalog_dedicated_legal_contract_review.py tests/test_food_source_regional_catalog_source_specific_terms_closeout.py tests/test_food_source_regional_catalog_source_specific_terms.py tests/test_food_source_regional_catalog_provider_terms.py tests/test_food_source_regional_catalog_identity.py tests/test_food_source_preference_mapping_closeout.py tests/test_food_source_gap_audit.py tests/test_food_source_catalog.py tests/test_food_source_onboarding.py
"${VENV_PYTHON}" -m pytest -q tests/test_repo_policy_guards.py
pre-commit run --all-files
make validate-changed VENV_PYTHON="${VENV_PYTHON}"
```

Full local `make verify` is intentionally deferred for this governance-only
machine-heavy lane unless the coordinator/operator explicitly requires it. The
PR body and fixed mapping must document the deferral and rely on focused local
gates plus GitHub current-head CI parity before any readiness claim.
