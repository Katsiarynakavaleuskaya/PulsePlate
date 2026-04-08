# PulsePlate — RAG / LLM / Karpathy Epic Pipeline

## One-line decision

Do **not** implement "Karpathy" as a replacement for PulsePlate product RAG.
Implement it as a **separate advisory compiled-memory workforce rail**, while the **product AI rail** stays aligned with Wave 6 AI follow-through.

---

## Canonical split

| Rail | Umbrella / anchor | Scope | In scope | Out of scope |
| --- | --- | --- | --- | --- |
| Rail A | `P1: Wave 6 AI runtime umbrella` | Canonical product AI runtime | fallback chain, quota/provider safety, RAG hardening, bounded-context extraction, reliability/security gates | advisory wiki memory, operator-only compiled notes, non-canonical workforce tooling |
| Rail B | `P2: Karpathy-style advisory wiki umbrella` | Advisory workforce compiled memory | local operator memory, advisory wiki/compiler/query-lint/reference-corpus controls | product RAG replacement, DB/runtime/API source of truth, public response-contract logic |

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

### Rail B — Karpathy-style workforce compiled memory (advisory only)
Purpose:
- local operator memory
- advisory wiki pages
- query/lint/promote tooling for workforce track
- repository navigation and accumulated decision memory

Truth model:
- wiki/support-plane = non-canonical advisory memory only
- never replace raw repo truth, DB truth, legal truth, or public API truth

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

### Governance rule for the prep PR

The governance/docs prep PR for this epic must:
- start with `agent-coordinator`;
- treat the coordinator-declared role-agent order as mandatory for the lane;
- use `docs/orchestration/GOVERNANCE_COORDINATOR_FIRST_RAG_KARPATHY_TASK_PACKET_2026-04-08.md`
  as the canonical packet for the prep lane;
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

## PR-A0 — docs/backlog umbrella
#### Title
`docs(roadmap): add Wave 6 AI runtime umbrella for RAG/LLM execution`

#### Goal
Create one explicit umbrella item so Codex does not re-derive sequencing from scattered ledger entries.

#### In scope
- add AI umbrella backlog entry
- add missing child items:
  - `rag-hardening-followthrough`
  - `ai-bounded-context-packet`
- link existing items:
  - insight fallback chain
  - PRO monthly quota parity
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

## PR-A1b — PRO monthly quota parity
#### Title
`feat(ai-runtime): enforce PRO monthly quota before provider calls`

#### Backlog target
existing PRO monthly quota item

#### Goal
Close the remaining quota gap before deeper LLM/RAG rollout.

#### In scope
- PRO quota enforcement for CBT insight and future PRO LLM surfaces
- 429 tests
- fail-closed startup / config checks if needed

#### Reason for placement
Recursive / philosophy rollout increases call amplification. Quota parity must exist before deeper rollout.

---

## PR-A2 — RAG hardening follow-through
#### Title
`feat(rag): harden retrieval path and recompute confidence deterministically`

#### Backlog target
new `ledger-p1-rag-hardening-followthrough`

#### Goal
Turn the scattered RAG technical debt into one bounded runtime hardening lane.

#### In scope
- vector query hardening
- confidence recomputation
- retrieval-source weighting cleanup
- SQL assembly hardening / refactor where needed
- deterministic response reasons

#### Out of scope
- workforce wiki
- broad UX changes
- giant multimodal expansion

#### DoD
- confidence is recomputed deterministically from retrieval/verification evidence
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

#### DoD
- explicit evaluation package exists
- gates are deterministic
- runtime docs point to one gate source

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

#### Backlog target
`ledger-p1-recursive-methods`

#### Goal
Promote recursive methods as a bounded runtime improvement, not as an uncontrolled cost explosion.

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

#### Source basis
Speech-act classification, language-game detection, early stopping, adaptive depth.

#### Goal
Reduce recursive latency before broadening rollout.

#### In scope
- speech act classifier
- language game depth mapping
- verification-based early stopping
- pragmatic early stopping

---

## PR-A9 — scientific reliability packet
#### Title
`docs(ai): publish scientific reliability evidence packet for the AI lane`

#### Backlog target
`ledger-p1-scientific-reliability-pipeline`

#### Goal
Turn the AI moat into evidence-backed positioning without overclaiming.

#### In scope
- benchmarks
- claim boundaries
- reproducible evidence packet
- internal/public article mapping

---

## RAIL B — Karpathy-style workforce compiled-memory epic

### Rule
This rail is **not product RAG**.
It is a **workforce/operator memory rail**.

## PR-B0 — launcher/bootstrap hardening
#### Title
`fix(local-workforce): harden launcher/bootstrap seam before advisory wiki expansion`

#### Goal
Ensure session start reliably runs preflight + bootstrap before relying on compiled memory.

---

## PR-B1 — advisory wiki compiler v1
#### Title
`feat(orchestration): advisory wiki compiler over local support plane`

#### Current anchor
existing local workforce PR-D entry

#### Goal
Implement raw/wiki/index/log style advisory memory.

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

#### Optional follow-on
- orphan detection
- stale link detection
- contradiction lint
- title/heading weighting
- manifest/history improvements

#### Still out of scope
- embeddings
- vector DB
- product RAG replacement

---

## PR-B4 — optional reference-corpus policy
#### Title
`docs(orchestration): define bounded reference-corpus policy for advisory wiki`

#### Goal
Allow DeepWiki or other reference corpora only as read-only secondary understanding aids.

#### Rule
- DeepWiki/reference corpora = helper for understanding
- repo = source of truth

---

## What is missing in the backlog right now

Add these missing items explicitly:

1. `P1: Wave 6 AI runtime umbrella for RAG/LLM execution`
2. `P1: RAG hardening follow-through`
3. `P1: AI bounded-context packet`
4. `P2: Karpathy-style advisory wiki umbrella`
5. `P2: Advisory wiki query/lint enrichment`

Without these five entries, the line is still scattered and Codex will keep reconstructing sequencing from fragments.

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

Build the PulsePlate RAG/LLM/Karpathy line as two separate but coordinated rails:

1. **Product AI runtime rail (canonical)**
   - PR-A0 docs/backlog umbrella
   - PR-A1 insight fallback chain
   - PR-A1b PRO monthly quota parity
   - PR-A2 RAG hardening follow-through
   - PR-A3 AI bounded-context packet
   - PR-A4 AI bounded-context extraction
   - PR-A5 LLM reliability/security gates
   - PR-A6 philosophical rollout W1
   - PR-A7 recursive methods W1
   - PR-A8 speed optimization for recursive stack
   - PR-A9 scientific reliability packet

2. **Karpathy workforce rail (advisory only)**
   - PR-B0 launcher/bootstrap hardening
   - PR-B1 advisory wiki compiler v1
   - PR-B2 advisory wiki semantics hardening
   - PR-B3 optional query/lint enrichment
   - PR-B4 optional reference-corpus policy

Never treat advisory wiki as product truth. Never replace repo/contracts/DB truth. Never let this rail overtake still-open emergency release blockers.

For the governance/docs prep PR:
- keep `docs/review/PR_1372_FIXED_MAPPING.md` as a separate active review artifact;
- merge the governance packet/runbook line first;
- start the next PR only if synced local `main` is current-head green and stable.
