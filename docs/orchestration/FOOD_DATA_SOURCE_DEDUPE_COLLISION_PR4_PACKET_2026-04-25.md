# Food Data Source Dedupe/Collision Policy PR4 Packet

**Effective date:** 2026-04-25 (`America/New_York`)
**Status:** Active PR4 collision-policy lane
**Mode:** coordinator-owned deterministic preflight governance lane

## Goal

Define and enforce the dedupe/mapping collision boundary before any snapshot promotion,
PostgreSQL staging, or runtime cutover in the food-data line.

## Relationship to prior PRs

- PR1 (`#1513`) defined source-update preflight criteria.
- PR2 (`#1517`) implemented strict file-only manifest validation and diff scaffolding.
- PR3 provides deterministic source catalog and replacement decisioning.
- PR4 adds explicit collision contracts and preflight deltas.

## Role Order

1. `agent-coordinator`
2. `data-scientist-agent`
3. `backend-engineer`
4. `security-auditor`
5. `qa-engineer-agent`
6. `bug-hunter`
7. `dev-operator`

Mandatory post-open review lane remains: `qa-engineer-agent -> bug-hunter`.

## In Scope

- Extend manifest validation to include a deterministic `collision_policy` block with
  `dedupe_fields`, `mapping_fields`, and `collision_resolution`.
- Validate that dedupe/mapping fields are valid schema members.
- Enforce collision resolution value is one of:
  `reject`, `quarantine`, `skip`.
- Extend dry-run diff report with collision deltas:
  - dedupe-field delta
  - mapping-field delta
  - collision-resolution delta
- Add fixture coverage for:
  - valid current manifest
  - valid legacy static MenuStat manifest
  - invalid `source_classification`
  - schema/PK drift fixture
  - collision policy drift fixture

## Out of Scope

- No source downloads.
- No staging/ingest writes.
- No runtime source switch.
- No DigitalOcean PostgreSQL credential handling.

## Validation Plan

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- Targeted pytest: `tests/test_food_source_preflight.py`
- CLI smoke: `python3 scripts/food_source_preflight.py --current-manifest ... --incoming-manifest ... --dry-run --json`
- `pre-commit run --all-files` before push

`make verify` is intentionally not part of the local PR4 loop per machine-heavy
exception; GitHub current-head CI is the heavy merge signal for this lane.

## Acceptance Criteria

- `collision_policy` is required and strictly validated.
- collision/mapping fields must exist in manifest `schema.fields`.
- dry-run report includes deterministic collision deltas.
- collision-resolution always compares and is part of the deterministic output contract.
- `runtime_cutover` remains `false` in dry-run by design.
- No file/network/db side effects in preflight CLI path.
