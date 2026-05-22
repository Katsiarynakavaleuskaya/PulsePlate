# PulsePlate — RAG / LLM / Karpathy Epic Pipeline

## One-line decision

Do **not** implement "Karpathy" as a replacement for PulsePlate product RAG.
Implement it as a **separate advisory compiled-memory workforce rail**, while the **product AI rail** stays aligned with Wave 6 AI follow-through.

---

## Canonical split

| Rail | Umbrella / anchor | Scope | In scope | Out of scope |
| --- | --- | --- | --- | --- |
| Rail A | `P1: Wave 6 AI runtime umbrella` | Canonical product AI runtime | fallback chain, quota/provider safety, RAG hardening, bounded-context extraction, reliability/security gates | advisory wiki memory, operator-only compiled notes, non-canonical workforce tooling |
| Rail B1 | `P2: Karpathy-style advisory wiki umbrella` | Advisory workforce compiled memory | local operator memory, advisory wiki/compiler/query-lint/reference-corpus controls | product RAG replacement, DB/runtime/API source of truth, public response-contract logic, semantic cache |
| Rail B2 | `P2: Plugin/control-plane families umbrella` | Advisory plugin/control-plane families | GitHub governance/CI review truth, Cloudflare preview/deploy control-plane, Figma design execution/review evidence, Hugging Face research/model-eval tooling | product runtime truth, public response-contract logic, semantic cache, bounded-context ownership |

For the continuous bootstrap lane `PR-S0 -> PR-A5`, `docs/orchestration/WAVE6_AI_RUNTIME_AND_ADVISORY_SERIES_PACKET_2026-04-13.md` is the canonical series SoT. This roadmap epic defers to that packet whenever sequencing, rail-boundary, or semantic-cache-gating wording diverges. The first bounded post-A5 runtime follow-up is `PR-K1`, governed by `docs/orchestration/WAVE6_K1_KNOWLEDGE_PROMOTION_PACKET_2026-04-19.md`.

### Temporary `security-floor` seam (canonical wording)

This epic inherits the Wave 6 packet rule for one narrow dependency-only
`security-floor` unblock when a known advisory blocks a docs/governance lane.
The seam is limited to governed dependency manifests, lock regeneration,
schema/guard sync, and CVE evidence; it must not widen into runtime/API/product
scope.

Evidence:

- `docs/orchestration/DEPENDABOT_ALERTS_110_113_REMEDIATION_TASK_PACKET_2026-04-16.md:64-70`
- `docs/security/CVE-2026-40347-python-multipart.md:17-25`
- `docs/security/GHSA-39q2-94rc-95cp-dompurify.md:17-24`

Governance:

- Canonical packet wording:
  `docs/orchestration/WAVE6_AI_RUNTIME_AND_ADVISORY_SERIES_PACKET_2026-04-13.md:30-59`
- ADR: `docs/architecture/ADR_WAVE6_SECURITY_FLOOR_UNBLOCK_SEAM_2026-04-17.md`
- Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-security-floor-unblock-seam`

### Rail A — Product AI runtime (canonical)
Purpose:
- insight fallback reliability
- quota / provider safety
- RAG hardening
- bounded-context extraction
- reliability/security CI gates
- later: philosophy + recursive methods as bounded runtime upgrades

Truth model:
- repo artifacts / contracts / DB / runtime = canonical source of truth
- public response contracts stay controlled by backend schemas and tests

### Rail B1 — Karpathy-style workforce compiled memory (advisory only)
Purpose:
- local operator memory
- advisory wiki pages
- query/lint/promote tooling for workforce track
- repository navigation and accumulated decision memory

Truth model:
- wiki/support-plane = non-canonical advisory memory only
- never replace raw repo truth, DB truth, legal truth, or public API truth
- never authorize semantic cache, public response-contract logic, or
  product-runtime behavior

Canonical umbrella packet:
- `docs/orchestration/KARPATHY_ADVISORY_WIKI_UMBRELLA_S0_PACKET_2026-04-24.md`

### Rail B2 — plugin/control-plane families (advisory only)
Purpose:
- GitHub governance / CI / review truth
- Cloudflare edge preview / Access control-plane
- Figma design execution / review evidence
- Hugging Face research / model-eval / external model tooling

Truth model:
- plugin/control-plane artifacts remain advisory or operational only
- never become product AI runtime truth implicitly
- must not overtake runtime sequencing on Rail A

Canonical umbrella packet:
- `docs/orchestration/PLUGIN_CONTROL_PLANE_FAMILIES_UMBRELLA_S0_PACKET_2026-04-24.md`

---

## What is already present and should NOT be reopened

1. RAG contract / response baseline already exists (`sources[]`, confidence, feedback storage, RLS, CBT RAG route).
2. Philosophy validator core already exists.
3. Philosophy validation pipeline already exists.
4. Recursive RAG W1 groundwork already exists.
5. First governed experimentation reliability loop already exists.
6. Local workforce advisory wiki line already exists as its own separate track and should remain separate from product RAG.

---

## Execution rule

This epic is a **separate planning / implementation line** from the emergency fix train.
It should **not overtake** still-open release-truth blockers.

Use it as:
- architecture/packet preparation now
- implementation rail after the emergency fixes are stabilized
- strict one-PR-at-a-time runtime sequence through `A5`
- treat `K1` as the first bounded post-A5 follow-up, not as semantic-cache rollout

### Governance rule for the prep PR

The governance/docs prep PR for this epic must:
- start with `agent-coordinator`;
- treat the coordinator-declared role-agent order as mandatory for the lane;
- use `docs/orchestration/GOVERNANCE_COORDINATOR_FIRST_RAG_KARPATHY_TASK_PACKET_2026-04-08.md`
  as the canonical packet for the prep lane;
- use `docs/orchestration/WAVE6_AI_RUNTIME_AND_ADVISORY_SERIES_PACKET_2026-04-13.md`
  as the canonical packet for the continuous `PR-S0 -> PR-A5` bootstrap lane;
- keep the active advisory-wiki review artifact in `docs/review/PR_1372_FIXED_MAPPING.md`
  separate from the governance PR;
- avoid opening the next PR in the train until local `main` is synced and current-head
  `main` is green/stable after merge fallout.

### Required role order for the governance/docs prep PR

1. `agent-coordinator`
2. `cursor-specialist-agent`
3. `architecture-specialist`
4. `security-auditor`
5. `qa-engineer-agent`
6. `bug-hunter`

Rules:
- every role agent assigned by coordinator must be used in the declared order
- no assigned role agent may be skipped without an explicit coordinator update
- no ad-hoc internal role stack may replace the declared order
- the canonical post-open `qa-engineer-agent -> bug-hunter` pass remains mandatory

---

## RAIL A — Product AI runtime epic

### Runtime series boundary

The continuous series implemented from this packet stops at:

- `PR-S0`
- `PR-A1b`
- `PR-A2`
- `PR-A3`
- `PR-A4`
- `PR-A5`

`A6-A9` remain valid future lanes, but they are not part of the current closure cycle.

## PR-S0 — docs/backlog umbrella
#### Title
`docs(roadmap): add Wave 6 AI runtime umbrella for RAG/LLM execution`

#### Goal
Create one explicit umbrella item so Codex does not re-derive sequencing from scattered ledger entries.

If a dependency advisory blocks this docs/governance lane, use the canonical
`security-floor` seam above instead of widening PR-S0 into runtime or product
scope.

#### In scope
- add AI umbrella backlog entry
- add missing child items:
  - `rag-hardening-followthrough`
  - `ai-bounded-context-packet`
- link existing items:
  - insight fallback chain
  - PRO monthly quota ledger reconciliation
  - ai bounded context extraction
  - llm reliability security gates
  - philosophical logic
  - recursive methods
  - scientific reliability pipeline

#### DoD
- one umbrella entry exists
- Wave 6 order is explicit
- product rail and Karpathy workforce rail are explicitly separated

---

## PR-A1 — insight fallback chain
#### Title
`feat(ai-runtime): implement insight fallback chain and readiness visibility`

#### Backlog target
`ledger-p0-insight-fallback-chain`

#### Goal
Make provider fallback deterministic and expose fallback / echo mode in readiness without leaking secrets.

#### In scope
- provider fallback order
- failover policy
- `/ready` fallback/echo visibility
- backward-compatible response behavior

#### Out of scope
- recursive methods
- new public AI surfaces
- UI redesign

#### DoD
- deterministic provider order
- readiness surface shows fallback state
- tests cover provider-down / fallback-on / echo-mode cases

---

## PR-A1b — PRO monthly quota ledger reconciliation
#### Title
`docs(roadmap): reconcile landed PRO quota truth before deeper runtime rollout`

#### Backlog target
`ledger-p1-pro-monthly-quota-ledger-reconciliation`

#### Goal
Reconcile the execution spine with live `main`, where tier-aware PRO/VIP quota
machinery is already materially landed (evidence:
`app/security/llm_monthly_quota.py:25-41`;
`app/security/llm_monthly_quota.py:52-77`;
`app/security/llm_monthly_quota.py:123-158`;
`app/bootstrap/startup_guards.py:44-56`;
`app/routers/cbt_insight.py:129-150`;
`app/services/fitchef_runtime.py:711-835`;
`tests/test_cbt_insight_api.py:921-952`;
merged `PR #1379` / `1ddf8c6778ca1f13c2bfce2e052db5409e8d06ba`
as recorded in `docs/roadmap/BACKLOG_LEDGER.md:296-300`).

#### In scope
- docs/backlog correction after merged `A1`
- live-runtime evidence links for landed PRO quota machinery
- explicit handoff from historical `A1` runtime implementation to the new docs-only `A1b` reconciliation lane
- isolate any true residual quota debt into a separate narrow follow-up if discovered

#### Reason for placement
Recursive / philosophy rollout still depends on quota parity, but `main` already implements the core parity seam. `A1b` therefore exists as a docs/governance reconciliation slice over already-merged quota truth, not as a fresh runtime-from-scratch quota implementation PR.

#### Lane governance note
This slice owns a dedicated lane packet
`docs/orchestration/WAVE6_A1B_PRO_QUOTA_RECONCILIATION_TASK_PACKET_2026-04-17.md:131-179`
and must maintain its own canonical `docs/review/PR_<N>_FIXED_MAPPING.md`
artifact-first review loop.
Because merged `PR #1440` and `PR #1441` already changed
`docs/roadmap/BACKLOG_LEDGER.md` on `main`, `A1b` must late-rebase onto fresh
`origin/main` before merge-readiness and stop instead of force-resolving if the
same ledger anchors remain in conflict with trunk
(`docs/orchestration/WAVE6_A1B_PRO_QUOTA_RECONCILIATION_TASK_PACKET_2026-04-17.md:138-148`).

#### Deferred optimization note
Any semantic-cache work remains governed by
`docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md:27-33`
and remains blocked until the `A1b -> A5` runtime sequence is closed
(`docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md:135-142`).

---

## PR-A2 — RAG hardening follow-through
#### Title
`feat(rag): harden degraded retrieval paths and keep contracts additive`

#### Backlog target
new `ledger-p1-rag-hardening-followthrough`

#### Goal
Turn the residual RAG technical debt into one bounded runtime hardening lane without reopening already-landed work.

#### In scope
- vector query hardening
- degraded retrieval / fail-safe behavior
- retrieval-source weighting cleanup
- malformed vector / embedding row handling
- deterministic response reasons

#### Out of scope
- workforce wiki
- broad UX changes
- giant multimodal expansion
- semantic cache
- Redis / GPTCache rollout

#### DoD
- degraded retrieval collapses fail-safe without corrupting the prompt contract
- vector path is safer and more maintainable
- no response-contract regressions

---

## PR-A3 — AI bounded-context packet
#### Title
`docs(architecture): define AI bounded-context packet and ownership map`

#### Backlog target
new `ledger-p1-ai-bounded-context-packet`

#### Goal
Lock architecture before extraction.

#### In scope
- define ownership boundaries for:
  - `core/ai/*`
  - `core/rag/*`
  - `core/insight/*`
  - provider seams
  - safety / eval / telemetry ownership
- list what remains transitional

#### DoD
- packet exists as canonical architecture SoT for extraction PR
- routers/adapters vs AI core ownership is explicit

---

## PR-A4 — bounded-context extraction
#### Title
`feat(ai-runtime): extract remaining AI runtime into dedicated bounded context`

#### Backlog target
`ledger-p1-ai-bounded-context-extraction`

#### Goal
Physically move remaining runtime ownership into the canonical AI seam.

#### In scope
- provider/runtime ownership moves into `core/ai/*`
- routers stay thin
- transitional ownership removed

#### Out of scope
- new model features
- product copy changes

#### DoD
- AI core ownership is consolidated
- adapters stay thin
- file:line evidence exists

---

## PR-A5 — LLM reliability/security gates
#### Title
`feat(ai-quality): add retrieval, faithfulness, injection, and privacy gates`

#### Backlog target
`ledger-p1-llm-reliability-security-gates`

#### Goal
Make AI quality drift detectable before merge/release.

#### In scope
- retrieval regression checks
- faithfulness / unsupported-claim checks
- prompt-injection adversarial tests
- privacy-sensitive evaluation
- philosophy_validator in release/CI path where appropriate
- canonical gate source: `docs/orchestration/contracts/AI_RUNTIME_GATE_CONTRACT.md`
- canonical launcher: `scripts/orchestration/ai_runtime_gate_bundle.py`

#### DoD
- explicit evaluation package exists
- gates are deterministic
- runtime docs point to one gate source

---

## PR-K1 — knowledge promotion from validated RAG evidence
#### Title
`feat(knowledge): add knowledge contracts and promotion from validated RAG evidence`

#### Status
Landed via PR `#1483` on `2026-04-20`; this closeout reconciles ledger,
roadmap, and review-governance state without reopening runtime scope.

#### Backlog target
`ledger-p1-knowledge-promotion-from-validated-rag`

#### Goal
Record the landed bounded internal knowledge seam after `A5` so later runtime
work can rely on PR `#1483` without treating retrieval artifacts, raw model
output, request-local recursive caches, or this closeout PR as semantic-cache
authority.

#### In scope
- landed PR `#1483` evidence for `core/knowledge/*` contracts, policy,
  promotion, and store protocol
- landed runtime knowledge policy via `prepare_insight_runtime(...)`
- landed internal-only promotion candidate seams and deterministic tests
- docs/backlog/review reconciliation for the K1 closeout state
- role-agent and Engineering Lessons updates for source-of-truth, mapping,
  and gate-closed wording failures found during the closeout review

#### Out of scope
- semantic cache implementation
- Redis/GPTCache/backend approval or serving selection
- DB migrations or persistent knowledge storage rollout
- route / OpenAPI / public response shape changes
- promotion from `DEEP_REASONING` or from raw provider output
- philosophy semantic-cache admission work owned by the separate philosophy epic

#### DoD
- PR `#1483` is the runtime evidence for promotion derived only from validated
  RAG evidence that survives orchestration
- degraded paths fail closed, route layer remains thin, and public contracts are unchanged
- ledger and roadmap no longer present K1 as open implementation work
- role-agent and engineering lesson updates prevent repeated RAG/cache
  closeout drift without changing runtime behavior
- semantic cache stays gate-closed, deferred, and out of scope

---

## PR-V1 — verification registry and verify-before-write admission
#### Title
`feat(ai-quality): add verification registry and verify-before-write admission invariant`

#### Status
Landed via PR #1491 on 2026-04-22 with merge commit
`ce024e7cdca3ec94bbffb095e050010a8198e792`. This closeout reconciles stale
ledger/roadmap/review governance truth and keeps PR-V1 as already-implemented
repo evidence, not as an active implementation lane. No `core/verification/*` reimplementation is in scope.

#### Backlog target
`ledger-p1-verification-registry-admission`

#### Goal
Record that the landed K1 knowledge seam is now strengthened by one first-class
verification registry/bundle, so future knowledge-promotion, cache, or action
lanes point at the merged verification truth instead of treating PR-V1 as
missing work.

#### In scope
- landed `core/verification/*` internal contracts, policy, and registry assembly
  evidence
- landed reuse of existing recursive verification diagnostics and philosophical
  runtime verification/falsification signals
- landed internal-only verification bundle threading through
  RAG/runtime/application seams
- verify-before-write admission for knowledge promotion only
- ledger, roadmap, role-agent, engineering-lesson, and review-mapping
  reconciliation so stale active-lane wording does not trigger duplicate
  implementation

#### Out of scope
- semantic cache implementation or gate opening
- cache/action runtime enablement
- DB persistence for verification artifacts
- route / OpenAPI / public response shape changes
- GraphRAG, Redis/GPTCache, or ContextManifest work

#### DoD
- write admission requires a passed canonical verification bundle
- recursive and philosophical verification signals converge into one registry
- route/app layers stay thin and do not author verification truth
- degraded response paths remain safe and do not break user-visible answers
- PR-V1 stays a closeout/reconciliation truth source, not a semantic-cache
  rollout or backend-selection approval

---

## PR-A6 — philosophical rollout W1
#### Title
`feat(ai-quality): rollout philosophical validation phases on bounded surfaces`

#### Backlog target
`ledger-p1-philosophical-logic`

#### Goal
Promote the philosophy line from isolated groundwork into a bounded runtime lane.

#### Recommended order inside the PR series
1. Aristotelian logic
2. Analytical philosophy
3. Post-analytical philosophy
4. Linguistic philosophy
5. unified validator/prompt builder

#### Constraint
Must remain behind bounded runtime surfaces and existing safety/eval gates.

---

## PR-A7 — recursive methods W1
#### Title
`feat(ai-runtime): rollout recursive RAG and bounded recursive verification`

#### Status
Landed via PR #1499 on 2026-04-23 with merge commit
`1e7166e55c54448c0d6475338e1b9984efd0caf1` from branch
`codex/ai-recursive-methods-w1`. This closeout reconciles stale
backlog/roadmap/review truth and does not duplicate runtime implementation.
The parent recursive-methods P1 item remains open until the full recursive
framework DoD is separately proven.

#### Backlog target
`ledger-p1-recursive-methods`

#### Goal
Promote recursive methods as a bounded runtime improvement, not as an uncontrolled cost explosion.

#### Landed W1 scope
- bounded recursive RAG and bounded recursive verification on existing product-AI insight seams
- recursive budgets, deterministic depth control, degraded/fail-safe behavior, and thin app/service handoff
- existing `VerificationBundle` truth preserved through the recursive/RAG path
- review-governed closeout evidence through PR #1499 and `docs/review/PR_1499_FIXED_MAPPING.md`

#### Out of scope
- semantic cache implementation or gate opening
- Redis/GPTCache rollout or backend approval
- GraphRAG, ContextManifest, embeddings, or vector database rollout
- DB persistence, public route, OpenAPI, DTO, or response-shape changes
- provider-side tree-of-thought / chain-of-thought expansion
- recursive learning or user-feedback adaptation

#### Recommended order
1. recursive retrieval
2. recursive reasoning
3. recursive refinement
4. recursive verification
5. recursive learning
6. unified assistant integration

#### Constraint
Use budgets, caching, early stopping, and deterministic depth control.

---

## PR-A8 — speed optimization for recursive stack
#### Title
`feat(ai-runtime): add philosophical speed optimization to recursive stack`

#### Current status
Landed via PR [#1506](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1506) on
`2026-04-23T20:41:25Z` with merge commit
`19fdbd3098a6aef780a71e94e94980cb3d0f61ee` from branch
`codex/ai-recursive-speed-optimization-w1`; hardened by PR
[#1578](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1578) on
`2026-04-29T20:32:42Z` with merge commit
`37995a6e8d4e9451b85e7e6284e9bd0cd5afff45` from branch
`codex/wave6-a8-recursive-speed-optimization`.

This closeout reconciles stale roadmap/backlog/review truth and does not
duplicate runtime implementation.

#### Landed and hardened scope
- deterministic recursive optimization hints from existing route truth
- bounded aggressive and pragmatic early-stop diagnostics
- thin app/service handoff without public contract changes

#### Benchmark boundary
Runtime evidence is limited to landed symbols, tests, and review artifacts.
This closeout does not claim fresh benchmark results. Any latency or quality
number remains a hypothesis target that requires benchmark validation.

#### Out of scope
Semantic cache remains closed. Redis/GPTCache, GraphRAG, ContextManifest, DB
persistence, public routes, OpenAPI, DTOs, recursive learning, provider
chain-of-thought, provider tree-of-thought, and default activation remain out
of scope.

---

## PR-A9 — scientific reliability packet
#### Title
`docs(ai): publish scientific reliability evidence packet for the AI lane`

#### Backlog target
`ledger-p1-scientific-reliability-pipeline`

#### Canonical packet
`docs/orchestration/WAVE6_A9_SCIENTIFIC_RELIABILITY_PACKET_2026-04-23.md`

#### Goal
Turn the AI moat into evidence-backed positioning without overclaiming.

#### Current status
Merged as PR `#1512` on 24 April 2026
(`2c9d9f4f6bbee139b855944568d5a2d25cd0bc15`). Treat this lane as
historical/closed; do not reopen `PR-A9` as the active publish lane. Future
scientific-reliability refreshes require a new dated packet or separate
superseding follow-up.

#### In scope
- governed offline replay evidence
- claim boundaries
- reproducible evidence packet
- internal/public article mapping

---

## RAIL B1 — Karpathy-style workforce compiled-memory epic

### Rule
This rail is **not product RAG**.
It is a **workforce/operator memory rail**.
It is non-canonical advisory memory only and must not authorize semantic cache,
runtime truth, DB/API truth, public response-contract logic, embeddings, vector
DB, Redis/GPTCache, GraphRAG, or ContextManifest work.

## PR-S0-B1 — advisory wiki umbrella
#### Title
`docs(roadmap): define Karpathy advisory wiki umbrella`

#### Canonical packet
`docs/orchestration/KARPATHY_ADVISORY_WIKI_UMBRELLA_S0_PACKET_2026-04-24.md`

#### Goal
Lock the Karpathy-style advisory wiki rail as a separate workforce-memory
umbrella without reopening product RAG, runtime implementation, semantic cache,
or plugin/control-plane ownership.

#### In scope
- Rail B1 umbrella canonicalization
- advisory wiki/support-plane source-of-truth boundaries
- links to launcher/bootstrap, compiler, query/lint enrichment, and
  reference-corpus policy children
- explicit separation from Rail A product runtime and Rail B2 plugin/control-plane

#### Out of scope
- product RAG replacement
- route, OpenAPI, schema, DTO, DB, runtime, or public response changes
- semantic cache, Redis/GPTCache, embeddings, vector DB, GraphRAG, or
  ContextManifest work
- GitHub, Cloudflare, Figma, Hugging Face, or other plugin/control-plane
  implementation

## PR-B0 — launcher/bootstrap hardening
#### Title
`fix(local-workforce): harden launcher/bootstrap seam before advisory wiki expansion`

#### Goal
Ensure session start reliably runs preflight + bootstrap before relying on compiled memory.

#### Packet
`docs/orchestration/KARPATHY_PR_B0_LAUNCHER_BOOTSTRAP_HARDENING_PACKET_2026-04-29.md`

#### Boundary
Repo-side bridge hardening only: no host auto-start claim, no advisory wiki compiler, and no
product runtime or semantic-cache scope. Evidence:
`docs/orchestration/KARPATHY_PR_B0_LAUNCHER_BOOTSTRAP_HARDENING_PACKET_2026-04-29.md:9-14`
and `docs/orchestration/KARPATHY_PR_B0_LAUNCHER_BOOTSTRAP_HARDENING_PACKET_2026-04-29.md:35-39`.

---

## PR-B1 — advisory wiki compiler v1
#### Title
`feat(orchestration): advisory wiki compiler over local support plane`

#### Current anchor
Closed local workforce PR-D entry:
`docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-local-workforce-pr-d-advisory-wiki-compiler`

#### Goal
Implement raw/wiki/index/log-style advisory memory.

#### Current status
Materially landed via PR #1371 on 2026-04-07
(`72b665763db36291b132ee148d347d7d6d8d273e`) with PR #1372 hardening on
2026-04-08 (`0c997be2352603c1bd5820d6d98f1c6b25793204`). Do not reopen or
reimplement compiler v1 as a new baseline lane.

#### Closeout packet
`docs/orchestration/KARPATHY_PR_B1_ADVISORY_WIKI_COMPILER_CLOSEOUT_PACKET_2026-04-29.md`

#### In scope
- ingest
- query
- lint
- promote
- local support-plane metadata

#### Out of scope
- embeddings
- vector DB
- user-facing truth
- public RAG replacement

---

## PR-B2 — advisory wiki semantics hardening
#### Title
`fix(orchestration): harden advisory wiki semantics and promote rollback safety`

#### Current status
Materially landed via `PR #1372`; do not reopen as baseline work.
Treat `PR #1372` as historical workforce-rail context only, not as scope carryover
into the governance/docs umbrella PR.

#### Goal
Non-destructive promote semantics + deterministic slug hardening.

---

## PR-B3 — query/lint enrichment
#### Title
`feat(orchestration): enrich advisory wiki query and lint without changing SoT`

#### Current status
Historical / merged Rail B1 implementation slice.

PR-B3 merged as PR #1596 on 2026-04-30 with merge commit
`438d135f7ae0a07cb28549488284a40e08183c92`. The canonical packet remains
`docs/orchestration/KARPATHY_PR_B3_ADVISORY_WIKI_QUERY_LINT_ENRICHMENT_PACKET_2026-04-30.md`;
review-governance evidence remains in `docs/review/PR_1596_FIXED_MAPPING.md`.
Closeout reconciliation packet:
`docs/orchestration/KARPATHY_PR_B3_ADVISORY_WIKI_QUERY_LINT_CLOSEOUT_PACKET_2026-04-30.md`.

#### First-cut scope
- opt-in query context for local substring search
- deterministic index/page consistency lint
- deterministic stale local `pages/<slug>.md` link lint

#### Deferred follow-on
- contradiction lint
- title/heading weighting or ranking
- manifest/history improvements
- bounded reference-corpus policy

#### Still out of scope
- embeddings
- vector DB
- product RAG replacement
- semantic cache

---

## PR-B4 — bounded reference-corpus policy
#### Title
`docs(orchestration): define bounded reference-corpus policy for advisory wiki`

#### Current status
Historical / merged Rail B1 docs-governance slice.

PR-B4 merged as PR #1607 on 2026-04-30 with merge commit
`07e11f4147bd75d20f8994175a9545782e02b04a`. The canonical packet remains
`docs/orchestration/KARPATHY_PR_B4_BOUNDED_REFERENCE_CORPUS_POLICY_PACKET_2026-04-30.md`;
review-governance evidence remains in `docs/review/PR_1607_FIXED_MAPPING.md`.
No PR-B4 implementation scope remains open.

#### Canonical packet
`docs/orchestration/KARPATHY_PR_B4_BOUNDED_REFERENCE_CORPUS_POLICY_PACKET_2026-04-30.md`

#### Goal
Allow DeepWiki or other reference corpora only as bounded, read-only secondary
understanding aids.

#### Policy contract
- DeepWiki/reference corpora are helper inputs for operator and role-agent
  understanding only.
- Repo-tracked artifacts remain the only canonical source of truth for product
  behavior, runtime contracts, orchestration policy, ledger state, and merge
  governance.
- Any conflict between a reference corpus and repo artifacts resolves to repo
  truth.
- Reference corpora cannot authorize product behavior, public response shape,
  API/DTO/OpenAPI contracts, DB/runtime truth, legal/compliance claims, medical
  or production marketing claims, or knowledge promotion.

#### Out of scope
- embeddings or vector DB/search
- product RAG replacement or runtime memory
- semantic cache, GraphRAG, Redis/GPTCache, or ContextManifest
- external corpus import, sync, scraping, or background refresh
- contradiction lint, ranking/index weighting, manifest/history, or corpus
  admission tooling

---

## RAIL B2 — plugin/control-plane families umbrella

### Rule
This rail is **not product runtime truth**.
It is an advisory/control-plane family map that keeps operator tooling and external
platform integrations from leaking into runtime ownership.

### PR-S0-B2 — plugin/control-plane families umbrella
#### Title
`docs(roadmap): define plugin control-plane families umbrella`

#### Canonical packet
`docs/orchestration/PLUGIN_CONTROL_PLANE_FAMILIES_UMBRELLA_S0_PACKET_2026-04-24.md`

#### Goal
Lock Rail B2 as a separate advisory/control-plane umbrella for GitHub,
Cloudflare, Figma, and Hugging Face without reopening product runtime truth,
semantic cache, bounded-context ownership, public response logic, or plugin
implementation.

#### In scope
- Rail B2 umbrella canonicalization
- advisory/control-plane family placement
- explicit separation from Rail A product runtime and Rail B1 advisory wiki
- explicit prohibition on semantic-cache, product RAG, public response, and
  bounded-context authorization

#### Out of scope
- GitHub, Cloudflare, Figma, Hugging Face, or other plugin implementation
- route, OpenAPI, schema, DTO, DB, runtime, authz, billing, or public response
  changes
- semantic cache, Redis/GPTCache, embeddings, vector DB, GraphRAG, or
  ContextManifest work
- Cloudflare deploy/Access mutation, Figma asset promotion, Hugging Face model
  jobs, or side-effectful tool/action execution

### Family placement

Canonical family placement, truth model, and conflict-resolution rules are
defined in:

- `docs/orchestration/PLUGIN_CONTROL_PLANE_FAMILIES_UMBRELLA_S0_PACKET_2026-04-24.md`

### Rule set

- no plugin family may become runtime truth implicitly
- no plugin family may be used as a shortcut for semantic cache rollout
- no plugin family may overtake the `A1b -> A5` runtime sequence

---

## Current backlog normalization gaps

Normalize these items explicitly:

1. `P1: Wave 6 AI runtime umbrella for RAG/LLM execution`
2. `P1: RAG hardening follow-through`
3. `P1: AI bounded-context packet`
4. `P2: Karpathy-style advisory wiki umbrella`
5. `P2: Plugin/control-plane families umbrella`

The first four items already exist and must stay authoritative. The fifth item is the
new normalization anchor that keeps plugin/control-plane families out of runtime truth.

---

## Global constraints for Codex

### Must do
- keep repo / contracts / DB as canonical truth
- keep product AI rail separate from advisory workforce wiki rail
- keep PRs narrow and single-purpose
- add deterministic tests for each lane
- preserve public contract compatibility where stated

### Must not do
- do not replace product RAG with wiki
- do not introduce a second source of truth
- do not open embeddings/vector DB early in workforce rail
- do not widen bounded-context PRs with new product features
- do not overtake still-open emergency/release blockers

---

## Paste-ready short instruction for Codex

Build the PulsePlate RAG/LLM/Karpathy line as three separate but coordinated rails:

1. **Product AI runtime rail (canonical)**
   - PR-S0 docs/backlog umbrella
   - PR-A1 insight fallback chain already landed on `main`; keep it as historical context, not as a current closure step
   - PR-A1b docs reconciliation for already-landed PRO quota truth
     (evidence: `docs/roadmap/BACKLOG_LEDGER.md:299-305`;
     `docs/review/PR_1379_FIXED_MAPPING.md:12-30`)
   - PR-A2 RAG hardening follow-through
   - PR-A3 AI bounded-context packet
   - PR-A4 AI bounded-context extraction
   - PR-A5 LLM reliability/security gates
   - PR-V1 verification registry and verify-before-write admission
   - PR-A6 philosophical rollout W1
   - PR-A7 recursive methods W1
   - Historical PR-A8 speed-optimization record: landed via PR #1506 and hardened by PR #1578; no active implementation lane remains in this closeout.
   - PR-A9 scientific reliability packet

2. **Karpathy workforce rail (advisory only)**
   - PR-S0-B1 Karpathy advisory wiki umbrella
   - PR-B0 launcher/bootstrap hardening
   - PR-B1 advisory wiki compiler v1
   - PR-B2 advisory wiki semantics hardening

   Semantic cache is a later optimization gate on the product AI runtime rail only.
   See `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`.
   Any dependency-blocked docs lane must use the canonical `security-floor`
   seam only (ADR:
   `docs/architecture/ADR_WAVE6_SECURITY_FLOOR_UNBLOCK_SEAM_2026-04-17.md`;
   Backlog:
   `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-security-floor-unblock-seam`).
   - PR-B3 optional query/lint enrichment
   - PR-B4 optional reference-corpus policy

3. **Plugin/control-plane rail (advisory only)**
   - PR-S0-B2 plugin/control-plane families umbrella
   - GitHub governance / CI / review truth
   - Cloudflare edge / preview / Access control-plane
   - Figma design execution / review evidence
   - Hugging Face research / model-eval / external model tooling

Never treat advisory wiki as product truth. Do not replace repo/contracts/DB truth. This rail must not overtake still-open emergency release blockers.

For the governance/docs prep PR:
- keep `docs/review/PR_1372_FIXED_MAPPING.md` as a separate active review artifact;
- merge the governance packet/runbook line first;
- start the next PR only if synced local `main` is current-head green and stable.
