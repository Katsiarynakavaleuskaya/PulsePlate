# Wave 6 A1b PRO Quota Reconciliation Task Packet

**Date:** 17 April 2026
**Scope:** docs/backlog/governance only
**Mode:** historical packet retained for closeout evidence

## Historical Closeout Status

This packet is historical. PR #1461 merged on 2026-04-19T11:34:45Z with merge
commit `cd01d9c6db89813202f85b8b9f4c8378e72380ea` from branch
`codex/wave6-a1b-pro-quota-reconciliation`, and PR #1466 merged on
2026-04-19T11:34:46Z with merge commit
`fa0979e734b88575e01e3eca9ddd4d57ade86c05` from branch
`codex/pr1461-mapping-fix`. Current A1b reconciliation uses a
ready-for-review closeout, not this older active-lane packet.

Runtime truth remains PR #1379, merged on 2026-04-10T12:08:46Z with merge
commit `1ddf8c6778ca1f13c2bfce2e052db5409e8d06ba` from branch
`feat/insight-fallback-chain`.

## Purpose

The original purpose was to freeze PR-A1b as a docs/backlog governance
reconciliation for already-landed PRO/VIP quota truth on live `main`.

This closeout keeps the useful boundaries:

- reconcile the roadmap/backlog wording with already-landed PRO/VIP quota truth;
- keep A1b docs-only and governance-only;
- preserve the canonical A1b -> A5 runtime sequence;
- prevent semantic-cache or plugin/control-plane work from widening this lane;
- preserve the role-agent order that reviewed the historical lane.

## Hard Boundaries

- No runtime/product code changes
- No OpenAPI or public contract mutation
- No semantic cache implementation or semantic-cache gate change
- No Redis / GPTCache rollout
- No provider/auth/billing behavior changes
- No plugin/control-plane implementation work for GitHub / Cloudflare / Figma /
  Hugging Face / Linear / Computer Use / Remotion / Life Science Research
- No widening into A2-A5
- No review artifact creation before the current PR number exists

## Canonical Scope

### In scope

- `docs/roadmap/BACKLOG_LEDGER.md`
- `docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md`
- this packet as historical evidence
- `docs/review/PR_<N>_FIXED_MAPPING.md` only after current PR open
- optional cross-link-only touch to
  `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
- a closeout guard and regression tests

### Out of scope

- `core/rag/*`
- `llm.py`
- `app/services/*`
- `legacy_app.py`
- quota runtime logic
- provider fallback logic
- auth/entitlement/billing runtime surfaces
- Rail B1 workforce/wiki implementation
- Rail B2 plugin/control-plane implementation

## Required Closeout Content

### `docs/roadmap/BACKLOG_LEDGER.md`

- mark `ledger-p1-pro-monthly-quota-ledger-reconciliation` closed;
- record PR #1461 and PR #1466 merge truth;
- anchor runtime truth to merged PR #1379 using merge SHA and file:line runtime
  evidence;
- keep the item as docs/governance closeout only;
- if real residual debt is found, create a narrow follow-up item instead of
  widening A1b;
- do not close or mutate:
  - `ledger-p1-rag-hardening-followthrough`
  - `ledger-p1-ai-bounded-context-packet`
  - `ledger-p1-ai-bounded-context-extraction`
  - `ledger-p1-llm-reliability-security-gates`
- do not create or reopen any semantic-cache item.

### `docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md`

- present PR-A1b as closed by PR #1461 / PR #1466;
- strengthen evidence wording so A1b follows already-landed PR #1379 runtime
  truth;
- preserve sequence A1b -> A2 -> A3 -> A4 -> A5;
- keep semantic cache deferred and outside A1b.

### `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`

- optional backlink only if needed for evidence symmetry;
- hard-gate machine markers must remain unchanged.

## Required Role-Agent Order

1. `agent-coordinator`
2. `security-auditor`
3. `bug-hunter`
4. `architecture-specialist`
5. `qa-engineer-agent`
6. `backend-engineer` - conditional, only for explicit non-user-ingest widening
7. `dev-operator` - required execution helper for local validation/evidence

Rules:

- this order remains the lane source of truth even if a routing helper suggests a
  different primary;
- no assigned role agent may be skipped without an explicit packet update;
- `dev-operator` cannot be omitted because this packet relies on command-level
  validation evidence;
- `backend-engineer` remains out of roster unless the lane is explicitly widened
  beyond docs/governance into a non-user-ingest runtime ticket;
- the canonical post-open `qa-engineer-agent -> bug-hunter` pass remains
  mandatory.

## Current PR Lifecycle Contract

### PR title

`docs(ai-runtime): reconcile A1b PRO quota closeout`

### Required PR body sections

- `Scope`
- `Files`
- `DoD`
- `Deferred / Follow-ups`
- `Discussion Thread Pass`
- `Fixed in Commit Mapping`
- `Merge Readiness`

### Post-open actions

1. create `docs/review/PR_<N>_FIXED_MAPPING.md`
2. run the mandatory `post_open_review` lane
3. iterate on current-head checks and actionable review comments
4. refresh the PR body mirror whenever the canonical review artifact changes

## Validation

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `python scripts/ci/check_ai_pro_quota_a1b_closeout.py`
- `python scripts/ci/check_semantic_cache_gate.py`
- focused pytest for the closeout guard and related governance tests
- `make validate-changed`
- `PATH=.venv/bin:$PATH pre-commit run --all-files`

Full `make verify` is intentionally not part of this machine-heavy closeout lane
unless the operator separately requests it. The current PR body and fixed mapping
must document that deferral and list the bounded local gates that did run.

## Next Lane After Merge

After merge and safe cleanup, the next canonical slice is:

- `PR-A2` - RAG hardening follow-through

It is explicitly not semantic cache.
