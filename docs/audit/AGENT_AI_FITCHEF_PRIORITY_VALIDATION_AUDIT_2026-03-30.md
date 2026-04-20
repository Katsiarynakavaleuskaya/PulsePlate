# Agent / AI / FitChef Priority Validation Audit (2026-03-30)

## Scope

- Docs-only validation audit.
- No runtime, schema, frontend, iOS, or workflow behavior changes.
- Purpose: convert the open-priority map into a canonical `ready now / blocked /
  defer` evidence pack without editing the attached plan file.

## Validation Method

The audit classifies work by three tests:

1. **Ready now**: backlog entry already has a bounded DoD, clear owner, and
   enough links to support a focused PR.
2. **Blocked**: valid priority, but depends on earlier routing, reliability, or
   canon stabilization.
3. **Defer**: useful later-wave work that should not precede foundation slices.

## Evidence

### A. Bootstrap and routing are still the top orchestration gap

- `docs/roadmap/BACKLOG_LEDGER.md:137` marks `P0: Requested-agent bootstrap override and advisory specialist contract` as open.
- `docs/roadmap/BACKLOG_LEDGER.md:143` explains that explicit specialist intent is currently under-expressed for `agent-coordinator`, `backend-engineer`, `bug-hunter`, `ml-engineer-agent`, and `data-scientist-agent`.
- `docs/roadmap/BACKLOG_LEDGER.md:150` through `docs/roadmap/BACKLOG_LEDGER.md:153` define a bounded DoD: preserve `requested_agents`, explain advisory vs routable handling, and add deterministic tests.
- `docs/orchestration/AUTOMATION_READINESS_MATRIX.md:83` states that coordinator-first handling is policy-required, not guaranteed at raw-session start.
- `docs/orchestration/AUTOMATION_READINESS_MATRIX.md:84` shows bootstrap packet generation is already deterministic once invoked, so this gap is implementation-hardening, not greenfield architecture.

### B. Deterministic routing is the next orchestration layer

- `docs/roadmap/BACKLOG_LEDGER.md:2086` opens `P1: Skill-router parity with policy docs and requested-agent bundles`.
- `docs/roadmap/BACKLOG_LEDGER.md:2092` states the concrete drift: coordinator packets can promise skills the runtime selector never emits.
- `docs/roadmap/BACKLOG_LEDGER.md:2122` opens `P1: Coordinator automation PR2 - bootstrap engine hardening`.
- `docs/roadmap/BACKLOG_LEDGER.md:2138` through `docs/roadmap/BACKLOG_LEDGER.md:2141` define bounded PR2 packet fields and deterministic tests.
- `docs/roadmap/BACKLOG_LEDGER.md:2163` opens `P1: Coordinator automation PR3 - skill routing and intent classifier`.
- `docs/roadmap/BACKLOG_LEDGER.md:2169` through `docs/roadmap/BACKLOG_LEDGER.md:2182` define explicit task classes plus `required`, `recommended`, `conditional`, and `blocked` skill semantics.
- `docs/orchestration/AUTOMATION_READINESS_MATRIX.md:158` through `docs/orchestration/AUTOMATION_READINESS_MATRIX.md:172` already describe PR3 as the canonical deterministic routing slice, which confirms this is `ready now`.

### C. AI reliability still needs one canonical gate loop

- `docs/roadmap/BACKLOG_LEDGER.md:1095` opens `P1: LLM reliability and security CI gates for retrieval, faithfulness, prompt-injection, and privacy`.
- `docs/roadmap/BACKLOG_LEDGER.md:1102` says AI quality and safety can drift silently between releases without this bundle.
- `docs/roadmap/BACKLOG_LEDGER.md:1110` through `docs/roadmap/BACKLOG_LEDGER.md:1113` define concrete CI/release-gate outcomes.
- `docs/roadmap/BACKLOG_LEDGER.md:1326` opens `AI multi-agent contracts (RAG/UQ/CV + safety) - runtime follow-up`.
- `docs/roadmap/BACKLOG_LEDGER.md:1333` through `docs/roadmap/BACKLOG_LEDGER.md:1342` require bounded recursion, citations, uncertainty fields, quota enforcement, and deterministic tests.
- `docs/roadmap/BACKLOG_LEDGER.md:1346` opens `P1: Extract AI runtime into a dedicated bounded context`.
- `docs/roadmap/BACKLOG_LEDGER.md:1352` through `docs/roadmap/BACKLOG_LEDGER.md:1364` show this is a consolidation/hardening slice with a stable target seam in `core/ai/*`.
- `docs/roadmap/BACKLOG_LEDGER.md:2441` opens `P1: AI reliability experimentation sublane for logic + philosophy offline replay`.
- `docs/roadmap/BACKLOG_LEDGER.md:2461` through `docs/roadmap/BACKLOG_LEDGER.md:2465` define a bounded offline-only experiment packet with no live runtime mutation or provider/network spend.
- `docs/roadmap/BACKLOG_LEDGER.md:1269` opens `P1: PRO monthly quota for LLM endpoints`.
- `docs/roadmap/BACKLOG_LEDGER.md:1274` says current AGENTS policy already requires quota before provider calls, but only VIP has implementation.
- `docs/roadmap/BACKLOG_LEDGER.md:1213` opens `P1: vector_rag SQL assembly refactor`.
- `docs/roadmap/BACKLOG_LEDGER.md:1218` through `docs/roadmap/BACKLOG_LEDGER.md:1227` show a bounded hardening task with no product-surface expansion.

### D. FitChef should expand through bounded eval-first lanes

- `docs/roadmap/BACKLOG_LEDGER.md:1878` opens `P1: FitChef umbrella initiative foundation`.
- `docs/roadmap/BACKLOG_LEDGER.md:1883` states the current canon already exists under `/api/v1/insight/fitchef*`, and future work must stay split into governed PR families.
- `docs/roadmap/BACKLOG_LEDGER.md:1914` through `docs/roadmap/BACKLOG_LEDGER.md:1919` lock the umbrella invariants: no duplicate truth, no FREE open-ended runtime, structured DTO rendering, routed actions only, and docs-only foundation lanes.
- `docs/roadmap/BACKLOG_LEDGER.md:7831` opens `P1: FitChef-first judgment offline eval contract and replay pack`.
- `docs/roadmap/BACKLOG_LEDGER.md:7838` says FitChef needs deterministic offline judgment eval before any bounded runtime adoption.
- `docs/roadmap/BACKLOG_LEDGER.md:7855` through `docs/roadmap/BACKLOG_LEDGER.md:7861` define a bounded, provider-free, network-free replay contract with local gates.
- `docs/orchestration/contracts/JUDGMENT_EVAL_CONTRACT.md:1` is already the canonical contract surface for that eval seam.
- `docs/audit/PR_1211_FITCHEF_JUDGMENT_OFFLINE_EVAL_AUDIT.md:4` confirms the existing FitChef judgment lane is additive, internal-first, and does not change public runtime behavior.
- `docs/roadmap/BACKLOG_LEDGER.md:1923` opens `P1: Distortion Simulator structured coaching lane`.
- `docs/roadmap/BACKLOG_LEDGER.md:1928` explicitly prefers a bounded PRO coaching tool over broad open-ended chat.
- `docs/roadmap/BACKLOG_LEDGER.md:1943` opens `P1: Identity Loop Mapper reflective coaching lane`.
- `docs/roadmap/BACKLOG_LEDGER.md:1948` defines it as a bounded VIP reflection tool, not generic chat widening.
- `docs/roadmap/BACKLOG_LEDGER.md:1861` opens `FitChef assets: establish a reusable SVG/Lottie pipeline + usage guide`.
- `docs/roadmap/BACKLOG_LEDGER.md:1866` through `docs/roadmap/BACKLOG_LEDGER.md:1874` show the asset lane is valid, but it is still a brand consistency slice rather than the first operational priority.

### E. User-visible rollout is important, but it depends on prior layers

- `docs/roadmap/BACKLOG_LEDGER.md:1689` opens `P1: Frontend parity for new AI-agent and LLM reliability features`.
- `docs/roadmap/BACKLOG_LEDGER.md:1694` states quality work is invisible to users unless confidence, verification, and fallback states reach web and iOS.
- `docs/roadmap/BACKLOG_LEDGER.md:1705` through `docs/roadmap/BACKLOG_LEDGER.md:1708` define bounded UI contracts and tests.
- `docs/roadmap/BACKLOG_LEDGER.md:4787` opens `P1: FitChef website brand rollout`.
- `docs/roadmap/BACKLOG_LEDGER.md:4794` through `docs/roadmap/BACKLOG_LEDGER.md:4808` make it explicit that brand rollout should not mix with mascot canon promotion and depends on that canon landing first.
- `docs/roadmap/BACKLOG_LEDGER.md:4811` opens `P1: FitChef Figma production sync`.
- `docs/roadmap/BACKLOG_LEDGER.md:4818` through `docs/roadmap/BACKLOG_LEDGER.md:4824` show it is a later promotion step after repo mascot canon and consumers stabilize.

### F. Unified integration remains a later wave

- `docs/roadmap/BACKLOG_LEDGER.md:2816` opens `P2: Unified Framework implementation (UnifiedAICoach: Philosophy + Math + CBT integration)`.
- `docs/roadmap/BACKLOG_LEDGER.md:2821` through `docs/roadmap/BACKLOG_LEDGER.md:2825` list multiple upstream dependencies, including philosophical logic, recursive methods, frontend parity, and payment baselines.
- `docs/roadmap/BACKLOG_LEDGER.md:2826` through `docs/roadmap/BACKLOG_LEDGER.md:2848` describe an integration wave rather than a first foundation slice, so this is correctly classified as `defer`.

## Classification Result

### Ready Now

- Requested-agent bootstrap override
- Skill-router parity
- Coordinator automation PR2
- Coordinator automation PR3
- Privileged workflow security-review routing
- LLM reliability and security CI gates
- AI multi-agent contracts runtime follow-up
- AI bounded-context extraction
- AI reliability offline replay sublane
- PRO monthly quota for LLM endpoints
- vector_rag SQL assembly refactor
- FitChef judgment offline eval closeout
- Distortion Simulator
- Identity Loop Mapper
- Frontend AI reliability parity

### Blocked

- Agent knowledge library template packs
- FitChef website brand rollout
- FitChef Figma production sync
- FitChef asset pipeline as a rollout-first choice

### Defer

- Centralize bootstrap sync-policy constants
- UnifiedAICoach
- FitChef phase-2 and localization expansion

## Decision

The evidence supports this execution order:

1. bootstrap truth
2. deterministic routing
3. AI reliability gates and offline eval
4. bounded FitChef coaching expansion
5. frontend reliability parity
6. brand rollout and unified integration later

This means the plan should be implemented as a dependency-ordered execution map,
not as an attempt to land all open backlog themes directly.

## Security Notes

This audit does not widen any AI runtime, does not relax any quota or safety
contract, and does not move FitChef toward open-ended coaching. It preserves the
current repo policy that reliability and bounded evaluation should precede wider
agent rollout.
