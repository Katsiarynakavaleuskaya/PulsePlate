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
