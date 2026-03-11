# External Food Source Operating Policy

<!-- markdownlint-disable MD013 -->

This document defines the operating policy for external food and menu datasets
used by PulsePlate. It is an internal operating contract, not legal advice.

## 1. Purpose

Use one reviewed matrix for ingestion, local caching, redistribution,
attribution, and commercial-risk defaults so future source onboarding does not
treat technically reachable data as automatically safe to ship or reuse.

Repo-grounded evidence:

- `docs/architecture/FOOD_DATABASE_PLATFORM_STRATEGY_v1.md`, section
  `## 4. Source Tiers and Update Cadence`, already lists canonical source tiers,
  including USDA, Open Food Facts, MenuStat-style, and Nutritionix-style lanes.
- `docs/architecture/FOOD_DATABASE_PLATFORM_STRATEGY_v1.md`, section
  `### 5.1 Snapshot contract`, defines the repo's snapshot-oriented operating
  lane.
- `app/routers/pro_food_attribution.py`, route `GET /api/v1/pro/attribution`,
  anchors the current attribution runtime contract.
- `docs/legal/ODbL_COMPLIANCE.md`, section `## Policy`, defines the
  provider-specific ODbL policy for Open Food Facts.

## 2. Workflow definitions

### Snapshot workflow

Snapshot workflow means deterministic, non-request-time ingestion, build, or
refresh jobs that create or update local canonical datasets before runtime
serving.

Current repo examples:

- `scripts/build_food_db.py`
- `core/food_apis/update_manager.py`
- source-specific ingestion and normalization logic under `core/food_sources/`

### Runtime workflow

Runtime workflow means request-time serving, lookup, attribution, or fallback
behavior that executes while handling application/API traffic.

Current repo examples:

- `app/routers/pro_food_attribution.py`
- food-serving and source-license lookup paths under `app/services/food_store.py`

## 3. Default operating rules

- Hard rule: no new external food or menu source may enter runtime or snapshot
  workflows without a reviewed matrix entry in this policy or a stricter
  provider-specific document.
- Hard rule: redistribution is forbidden by default unless the reviewed matrix
  says otherwise.
- Hard rule: local caching is forbidden by default unless the reviewed matrix
  says otherwise.
- Attribution defaults to required when terms or source status are uncertain.
- Commercial usage defaults to medium-or-higher risk until reviewed.

## 4. Source matrix

| Source lane | Ingestion | Local cache | Redistribution | Attribution | Commercial risk note |
| --- | --- | --- | --- | --- | --- |
| USDA / FoodData Central-style public nutrition datasets | Allowed for reviewed normalization and snapshot workflows | Allowed for reviewed local snapshots | Not allowed by default without explicit source-term review in rollout PR | Recommended | Medium: public data source, but downstream product use still needs documented review |
| Open Food Facts (ODbL) | Allowed | Allowed | Allowed only when ODbL obligations and derivative-db obligations are preserved | Required | Medium: open-data friendly, but share-alike and attribution duties are binding |
| MenuStat-style public research datasets | Allowed only after file-level license review in onboarding PR | Allowed for reviewed local snapshots | Not allowed by default | Required | Medium: publication is public/research-oriented, but redistribution rights may be narrower than access suggests |
| Nutritionix-style commercial datasets | Not allowed by default without contract | Not allowed by default without contract | Not allowed by default | Contract-dependent | High: commercial provider terms usually govern cache, display, and redistribution rights |

## 5. Relationship to provider-specific docs

- `docs/legal/ODbL_COMPLIANCE.md` remains the canonical provider-specific policy
  for Open Food Facts.
- If a source has stricter obligations than this matrix, the provider-specific
  document wins.
- If a source is not listed here, it is treated as not approved for rollout.

## 6. Operating requirements for rollout PRs

Every future source-onboarding or expansion PR must state:

- source name and source class
- ingestion path
- cache decision
- redistribution decision
- attribution decision
- commercial-risk note
- whether a provider-specific policy doc is required

## 7. Prohibited assumptions

- "Publicly downloadable" does not mean "safe to redistribute"
- "Factual nutrition data" does not mean "contract-free to cache forever"
- "Available through an API" does not mean "safe for bulk ingestion or model
  training"

## 8. Deferred enforcement

Automation that validates source onboarding against this matrix is deferred and
must be tracked in `docs/roadmap/BACKLOG_LEDGER.md`.

## 9. Related docs

- `docs/legal/ODbL_COMPLIANCE.md`
- `docs/architecture/FOOD_DATABASE_PLATFORM_STRATEGY_v1.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
