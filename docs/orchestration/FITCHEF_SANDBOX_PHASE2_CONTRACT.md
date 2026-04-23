# FitChef Sandbox Phase 2 Contract

## Status

This document defines the deferred Phase 2 scope for the FitChef sandbox
runtime. These capabilities are planned, not live.

Canonical backlog anchor:

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-pr1013-fitchef-phase2-scope`

Until a dedicated implementation PR lands, FitChef sandbox scope remains
limited to the approved Phase 1 surface:

- coaching insight
- meal-plan generation
- shopping-list follow-up

Phase 2 must not be described in product/runtime docs as already available.

## Phase 2 Capability Set

Phase 2 may promote only these three bounded additions:

1. export orchestration
2. realtime progress streaming
3. broader bounded multi-tool autonomy

Anything outside this list requires a separate backlog item and contract review.

## Contract 1: Export Orchestration

### Scope

FitChef may orchestrate CSV/PDF export follow-ups only through backend routes.

### Required gates before execution

- export route remains backend-only and thin-client
- rate limit is enforced before expensive generation
- tier gate is enforced before file generation
- audit trail records the export-capable action
- OpenAPI documents the export contract and 429 behavior

### Non-goals

- direct filesystem browsing from client prompts
- arbitrary file generation outside canonical export surfaces
- bypass of export auth/tier checks

## Contract 2: Realtime Progress

### Scope

Phase 2 may expose bounded progress updates for long-running FitChef tasks.

### Required gates before execution

- transport remains on canonical backend realtime surface only
- event allowlist is explicit and versioned
- auth remains fail-closed before subscription is accepted
- quota/policy gates execute before realtime task start
- progress messages never leak hidden tool output or secrets

### Non-goals

- unrestricted fan-out
- client-owned orchestration state
- unbounded chat streaming without backend policy checkpoints

## Contract 3: Bounded Multi-Tool Autonomy

### Scope

Phase 2 may expand FitChef from a single-task orchestration wrapper to a
bounded multi-tool planner with explicit action budgets.

### Required gates before execution

- policy allowlist resolves before any tool call
- per-task tool budgets are explicit and deterministic
- monthly quota and execution mode are checked before provider/tool calls
- audit trail captures each privileged tool step
- refusal path is defined when the requested chain exceeds policy

### Non-goals

- arbitrary shell autonomy
- recursive self-expansion of tools
- client-side tool execution

## Security Review Baseline

Phase 2 promotion requires a dedicated security review in the same PR. That
review must confirm the following invariant for every new capability:

- policy gate first
- quota/rate-limit gate before expensive execution
- audit evidence for privileged actions
- fail-closed behavior when auth, policy, or quota checks fail

No Phase 2 runtime capability should ship before this review is written and
linked from the PR.

## Promotion Checklist

Phase 2 is ready for implementation only when a dedicated PR includes all of
the following:

- route/runtime contract for the added capability
- tests for policy/quota/audit ordering
- updated product/runtime docs pointing to the same Phase 2 contract
- explicit statement that unsupported capabilities remain deferred
