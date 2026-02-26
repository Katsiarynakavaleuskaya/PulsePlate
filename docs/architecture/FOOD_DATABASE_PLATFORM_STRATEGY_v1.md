# Food Database Platform Strategy v1

**Status:** Architecture plan (P0 foundation)
**Date:** 2026-02-24
**Owner:** @katsiaryna_kavaleuskaya
**Scope:** docs-only strategy source of truth for the Food Data Platform program

---

## 1. Goal

Build a professional, self-updating, multi-source food database with minimal live external API dependency.

Primary outcomes:

- snapshot-first ingestion (copy once, serve locally)
- verified canonical nutrition records across sources
- expansion from products to restaurant menus
- controlled user submissions with moderation
- stable API compatibility for existing clients

---

## 2. Current State (As-Is)

Implemented foundation already exists:

- source integration: USDA + Open Food Facts (`core/food_apis/unified_db.py:152`, `core/food_apis/update_manager.py:134`, `core/food_apis/scheduler.py:28`, `core/food_sources/usda.py:20`, `core/food_sources/off.py:19`)
- merge layer: `core/food_merge.py:50`
- build/export flow: `scripts/build_food_db.py:62`
- existing API surface: `/api/v1/foods`, `/api/v1/foods/search`, `/api/v1/foods/{food_id}` (`app/routers/foods.py:29`, `app/routers/foods.py:53`, `app/routers/foods.py:66`)

Validation criteria for this as-is claim:
- keep the referenced symbols active at the anchored paths or update anchors in this doc in the same PR
- keep food foundation tests passing for `tests/test_food_apis*.py` and `tests/test_food_merge*.py` when these surfaces change

Known gap:

- no fully governed snapshot lifecycle and source-tier rollout model
- no canonical confidence/provenance policy as an explicit SoT
- limited restaurant/menu coverage
- no controlled submission pipeline for unknown products

---

## 3. Architecture Principles (Target)

1. Snapshot-first: local snapshots are primary runtime source.
2. Multi-source with provenance: every canonical record keeps source evidence.
3. Non-breaking API evolution: keep current endpoints stable.
4. Deterministic ingestion: manifests/checksums and predictable update windows.
5. Cost and reliability first: live fallback API calls only for unknown misses.

---

## 4. Source Tiers and Update Cadence

| Tier | Source | Role | Update policy |
|------|--------|------|---------------|
| Tier 1 | USDA | scientific baseline | full snapshot quarterly |
| Tier 1 | Open Food Facts | barcode + branded coverage | weekly delta sync + periodic full refresh |
| Tier 2 | MenuStat | restaurant menu baseline | annual snapshot |
| Tier 2 | Nutritionix | chain/menu enrichment | monthly scoped snapshot + constrained fallback API |
| Tier 3 | regional catalogs (EU/RF/EAEU where legal) | local-market coverage | source-dependent periodic import |
| Tier 4 | live fallback APIs | miss resolution only | called only when local miss occurs |

Policy rule:

- local search/lookup first
- external API only on miss and only after local cache check
- successful external result is normalized and cached into canonical store

---

## 5. Canonical Data Contracts

### 5.1 Snapshot contract

Required metadata per snapshot:

- source name
- snapshot date/version
- checksum (`sha256`)
- record count
- file size
- manifest entry with immutable path

### 5.2 Canonical entity contract

Canonical food record must support:

- normalized nutrients per 100g
- source identifiers (`usda_fdc_id`, `off_barcode`, etc.)
- confidence score
- source count / provenance mapping
- update timestamps and verification date

### 5.3 Provenance contract

Every canonical record update must preserve:

- source origin
- source record ID
- snapshot date
- raw payload reference for audit/debug

---

## 6. API Compatibility and Planned Additions

### 6.1 Preserve (non-breaking)

- `GET /api/v1/foods`
- `GET /api/v1/foods/search`
- `GET /api/v1/foods/{food_id}`

### 6.2 Additions (non-breaking)

- `GET /api/v1/foods/barcode/{barcode}`
- `GET /api/v1/restaurants/search`
- `GET /api/v1/restaurants/{chain_id}/menu`

Compatibility guarantee:

- no request/response shape break for existing clients
- additive rollout for new endpoints

---

## 7. Execution Program (Wave Model)

## W1 (P0): Snapshot manager + OFF delta + canonical merge contract

Deliverables:

- immutable raw snapshot layout
- manifest/checksum policy
- deterministic delta ingestion behavior
- canonical merge contract without API break

## W2 (P1): Search modernization + API compatibility

Deliverables:

- local-first search engine modernization (MeiliSearch or TypeSense)
- compatibility-preserving transition for existing `/foods` routes
- explicit query/filter contract for new behaviors

## W3 (P1): Restaurant menus + controlled submissions

Deliverables:

- MenuStat ingestion baseline
- restaurant menu schema and endpoints
- moderated user submissions (`pending/approved/rejected`) with audit trail

Operational bootstrap (local-first, deterministic):

- run `python -m scripts.import_restaurant_menu --input data/restaurant_menu_sample.csv --snapshot-date 2026-02-25 --db-path data/food.sqlite`
- this command performs MenuStat-style CSV normalization and writes to `restaurant_chains`, `restaurant_menu_items`, and `source_catalog` via `app/services/restaurant_store.py`
- use sample CSV for deterministic local bootstrap; production snapshots should keep immutable raw files under `data/raw/menustat/*` and run checksum validation before import

## W4 (P2): Optional semantic retrieval

Deliverables:

- pgvector + multilingual embeddings behind feature flag
- cost/performance benchmark and rollback-safe rollout
- execution split:
  - W4-A: feature flag + non-breaking API/contract path (default off)
    (evidence: `docs/roadmap/BACKLOG_LEDGER.md:126`)
  - W4-B: embeddings pipeline + pgvector indexing + benchmark report
    (evidence: `docs/roadmap/BACKLOG_LEDGER.md:138`)
    (benchmark evidence: `docs/audit/PR_914_FOOD_DB_W4_SEMANTIC_BENCHMARK.md`)
    (artifact: `docs/audit/artifacts/food_w4_semantic_benchmark.json`)
    (rollback tests: `tests/test_food_store_service.py:348`, `tests/test_foods_router_additional.py:303`)
  - temporary split exit criteria:
    - W4-B implementation PR is merged with benchmark artifact and rollback notes
    - semantic path remains feature-flagged until W4-B benchmark gate is accepted
    - ledger entry is updated from `In Progress` to `✅ Merged` with concrete PR references

---

## 8. Test and Acceptance Gates

Program gates:

1. Merge-readiness gate: zero unresolved threads + zero unmapped actionable bot comments.
2. Docs-only gate for strategy PR: only markdown/doc files changed.
3. W1 tests: snapshot manifest integrity, checksum fail-closed, deterministic delta behavior.
4. W2 tests: existing `/foods` contract remains valid; new search/barcode filters covered.
5. W3 tests: moderation state transitions and provenance persistence.
6. Runtime PR hard gate: `pre-commit run --all-files` and `make verify`.

---

## 9. Security Notes

- Verify checksum for each external snapshot before import.
- Keep source credentials in environment variables only.
- Never auto-promote user-submitted records into canonical tables.
- Keep search services internal/private behind API boundary.
- Validate malformed payload paths before canonical ingestion.

---

## 10. Marketing and GTM

Positioning after W2/W3:

- verified multi-source food + restaurant menu database
- local-first speed and lower manual entry burden
- stronger SEO surface from canonical product/menu entities

Differentiator:

- verified source provenance + practical coverage + predictable latency

---

## 11. Alignment Notes

This strategy is aligned with:

- `docs/design/RESTAURANT_INTEGRATION_SPEC.md` (partner-facing menu contract direction)
- `docs/roadmap/BACKLOG_LEDGER.md` (execution backlog and PR tracking)

This document is a planning SoT and does not change runtime behavior.
