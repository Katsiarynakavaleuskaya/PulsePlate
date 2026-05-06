<!-- markdownlint-disable MD013 -->
# Evidence Promotion Ledger And Replay Contract

## Purpose

PR-E3 adds the first Evidence Graph promotion/replay layer after the unified
eval event schema from PR-E2.

```text
normalized eval event
-> promotion ledger entry
-> deterministic dry-run replay
-> promotion diff report
```

This contract is internal and schema-first. It does not add product runtime
behavior, routes, OpenAPI, DB writes, eval runners, dashboards, semantic cache,
GraphRAG, or advisory-wiki authority.

## Ledger Entry Contract

`core/evidence/promotion_ledger.py` defines immutable promotion ledger entries
with these canonical fields:

- `ledger_entry_id`
- `promotion_id`
- `source_event_id`
- `source_event_type`
- `source_event_fingerprint`
- `decision`
- `idempotency_key`
- `policy_version`
- `producer`
- `produced_at`
- `upstream_ids`
- `supersedes`
- `validation_status`
- `reason_codes`
- `metadata`

Supported decisions are intentionally narrow:

- `promote`
- `reject`
- `defer`
- `supersede`

`ledger_entry_id` is deterministic and derived from canonical entry fields via
`fingerprint_payload`. It does not depend on wall-clock time; `produced_at` is
recorded for audit context only.

## Validation

The ledger fails closed on:

- unsupported decisions or validation statuses;
- blank source event IDs, source fingerprints, idempotency keys, policy
  versions, producer names, or producer versions;
- promotion/supersession of source events that are not `valid`;
- promotion/supersession entries whose ledger validation status is not `valid`;
- self-supersession and duplicate `supersedes` entries;
- duplicate/colliding reason codes after normalization;
- metadata that appears to contain raw prompts, raw responses, user-health
  payloads, secrets, or path-like artifact payloads;
- caller-owned mutable structures changing after validation.

Reject/defer decisions may record invalid, degraded, or deferred source events,
but they do not promote those events.

## Replay Contract

`core/evidence/replay.py` defines a dry-run-only replay helper. It accepts
existing ledger entries and candidate ledger entries, sorts them
deterministically, and returns a summary with a promotion diff.

Diff buckets are:

- `added`
- `duplicate`
- `superseded`
- `rejected`
- `deferred`
- `conflict`

Replay deduplicates by `idempotency_key`. The same key and same entry is a
duplicate. The same key with different deterministic identity is a conflict.
Candidate entries with conflicting `promotion_id` scope are reported as
non-promoting conflicts unless they are explicit supersession entries.

Replay does not mutate inputs, write files, call a database, call providers,
call eval runners, or import product runtime modules.

## Rail Boundaries

E3 consumes normalized eval events from `core/evidence/events.py`. It does not
make eval events product truth and does not mix product runtime, advisory wiki,
control-plane, or eval rails.

Forbidden imports include:

- FastAPI/routes and `legacy_app`;
- providers and `llm.py`;
- DB/session layers;
- Redis/cache/GPTCache or semantic cache;
- GraphRAG/knowledge graph runtime;
- eval runners and `scripts.evals`;
- advisory wiki or local support-plane modules.

`core/knowledge/promotion.py` remains a separate product knowledge-promotion
seam. E3 does not import or rewrite it.

## Premortem Notes

| Failure mode | Mitigation in E3 | Evidence |
| --- | --- | --- |
| Hidden writer/store | Replay is dry-run-only and returns values only | `tests/core/evidence/test_replay.py` |
| Duplicate knowledge-promotion layer | E3 lives under `core/evidence` and does not import `core/knowledge/promotion.py` | import guard tests |
| Invalid evidence promoted silently | Promote/supersede require valid source event and valid ledger status | ledger tests |
| Nondeterministic replay | Entries are sorted and IDs are content-derived | replay determinism tests |
| Weak idempotency | Duplicate keys dedupe; colliding keys conflict | replay tests |
| Raw prompt/health/secret leakage | Metadata validation fails closed | ledger metadata tests |
| Semantic cache or GraphRAG side door | Import guards block cache/GraphRAG/wiki/runtime modules | AST guard tests |

## E4 Handoff

PR-E4 can build active metadata admission on top of these deterministic ledger
and replay contracts. E4 should own admission decisions such as
`allow_execute`, `allow_promote`, and `allow_serve`; E3 only provides the
append-only ledger and dry-run replay substrate.
