# Agent instructions (scope: core/evidence/ and subdirectories)

## Evidence Graph Runtime sequencing

Evidence Graph Runtime changes must preserve this separation:

- Eval runners generate artifacts.
- Evidence events normalize artifact metadata into deterministic event records.
- Promotion ledger and replay consume normalized events in later PRs.
- Semantic cache is a separate runtime optimization and must not be introduced
  through evidence-event PRs.
- GraphRAG / knowledge graph expansion is out of scope unless a later packet
  explicitly opens that rail.
- Karpathy/advisory wiki is workforce memory only and must not become
  product-runtime or eval-event source of truth.

For E2/E3-style work, keep `core/evidence/` pure and deterministic. Do not
import FastAPI, providers, DB/session state, Redis/cache modules, eval runners,
or advisory wiki modules from this package.

E3 promotion ledger/replay changes may add append-only promotion contracts and
dry-run replay summaries only. They must not write files, call runtime stores,
create promotion side effects, or duplicate `core/knowledge/promotion.py`.

## E4 active metadata admission

E4 admission logic must stay pure and deterministic.

Allowed:

- policy/input/decision dataclasses
- deterministic `allow_execute`, `allow_promote`, and `allow_serve` decisions
- explicit `now` / timestamp input
- `reason_codes`, `blocking_reasons`, and `warnings`
- metadata validation

Forbidden:

- runtime writes
- DB/session access
- provider calls
- FastAPI/router imports
- eval runner imports
- semantic cache, Redis, or GPTCache imports
- GraphRAG runtime imports
- advisory wiki/local support-plane imports
- product knowledge-promotion rewrites

Admission decisions are gates, not side effects. They may block future
promotion/serve actions, but this package must not perform those actions.

## E5 advisory wiki bridge

E5 bridge logic must stay pure deterministic mapping only.

Allowed:

- advisory wiki artifact reference dataclasses
- advisory `EvidenceAssetRef` mapping
- advisory admission metadata adapters
- deterministic IDs, fingerprints, idempotency keys, and serialization
- metadata/path safety validation

Forbidden:

- wiki compiler rewrites
- local support-plane mutation imports
- `scripts/orchestration` imports
- wiki ingest/promote/query/lint CLI imports
- runtime writes or product serving behavior
- runtime rail mapping for wiki artifacts
- semantic cache, Redis, GPTCache, or GraphRAG imports
- advisory wiki as product/runtime/eval source of truth

Advisory wiki artifacts are workforce memory. They may be linked to advisory
evidence assets for lineage and review, but they must not become canonical
repo/runtime/DB/OpenAPI/test truth.
