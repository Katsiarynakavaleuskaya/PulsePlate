# FitChef Sandbox Integration Plan

## Goal

Define the first production-minded local shape of the FitChef backend-agent that
runs inside the execution sandbox and serves iOS, web, and Android clients from
one shared runtime.

## Core Decision

FitChef is a **backend agent runtime**, not a client-embedded agent.

- iOS, web, and Android remain thin clients
- the sandbox hosts the privileged execution boundary
- RAG, policy, audit, and tool execution live server-side
- the same backend contract is reused by every client

This keeps behavior aligned across platforms and avoids duplicating safety or
LLM logic in mobile/web code.

## Phase 1 Runtime Shape

### Entry Surface

Start with the existing CBT-style agent surface:

- `app/routers/cbt_insight.py`
- `app/security/agent_control_plane.py`
- `app/security/agent_input_guard.py`
- `core/rag/orchestration.py`
- `core/insight/llm_provider_loader.py`

This already gives FitChef a narrow and safe first runtime:

- feature flag
- execution mode
- signed audit
- monthly quota
- RAG retrieval
- bounded LLM call

### First FitChef Capability Set

FitChef v1 should orchestrate only three capabilities:

1. coaching insight
2. meal-plan generation
3. shopping-list follow-up

Initial tool/domain bindings:

- coaching insight: `app/routers/cbt_insight.py`
- weekly planning: `app/routers/pro.py`, `app/services/weekly_plan/pipeline.py`
- shopping list: `app/routers/shopping_list_pro.py`

Do not start with exports, realtime fan-out, or broad multi-tool autonomy.
These follow-ups stay deferred until dedicated backlog items are merged:

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-pr1013-fitchef-phase2-scope`
- `docs/orchestration/FITCHEF_SANDBOX_PHASE2_CONTRACT.md`

## Runtime Contract

FitChef sandbox calls should use one shared orchestration envelope:

```json
{
  "agent_id": "fitchef-agent",
  "mode": "auto-safe",
  "task_type": "coach_insight | weekly_plan | shopping_followup",
  "input": {
    "user_text": "...",
    "profile_id": "...",
    "tier": "pro"
  },
  "tool_budget": {
    "max_steps": 3,
    "max_llm_calls": 1,
    "max_retrieval_calls": 1
  }
}
```

Response baseline:

```json
{
  "agent_id": "fitchef-agent",
  "mode": "auto-safe",
  "task_type": "coach_insight",
  "result": {
    "message": "...",
    "sources": [],
    "confidence": 0.0,
    "uncertainty": "low | medium | high",
    "warnings": []
  },
  "quota_state": {
    "allowed": true,
    "tier": "pro"
  }
}
```

## Client Integration Rule

Clients must consume FitChef through backend APIs only.

### Web

Primary integration targets:

- `frontend/src/api/schema.ts`
- `frontend/src/api/openapi.json`
- future dedicated consumer for `/api/v1/pro/cbt/insight`

### iOS

Primary integration targets:

- `ios/PulsePlate/Services/WeeklyPlanService.swift`
- future dedicated CBT/FitChef service using the same backend contract

### Android

Android is not yet present in this repo, but should follow the same thin-client
contract: transport + rendering only, no local sandbox execution.

## Local Sandbox Binding

The sandbox should execute only bounded orchestration tasks, not arbitrary app
logic.

First local binding:

- route request enters `cbt_insight`
- control plane resolves mode and policy
- sandbox may execute bounded helper commands only when needed
- RAG and provider layers stay inside backend runtime

Allowed local helper usage examples:

- deterministic offline evaluation commands
- bounded retrieval preparation
- safe formatting or validation helpers

Forbidden in v1:

- arbitrary shell autonomy
- unbounded recursive planning
- direct client-triggered filesystem exploration
- bypass of policy gate or quota gate

## Rollout Order

1. Keep `cbt_insight` as the first FitChef runtime surface.
2. Add a dedicated `fitchef-agent` orchestration wrapper above existing domain modules.
3. Bind weekly-plan generation as a second task type.
4. Bind shopping-list follow-up as a third task type.
5. Only after that, expose streaming/realtime progress and richer tool chains.

Those additions are still planned only and must follow the dedicated Phase 2
contract:

- `docs/orchestration/FITCHEF_SANDBOX_PHASE2_CONTRACT.md`

## Success Criteria

Phase 1 is complete when:

- one backend FitChef runtime serves all clients
- sandbox remains fail-closed
- execution mode and policy gate are always enforced first
- quota is consumed before provider call
- audit trail exists for every privileged run
- no client embeds duplicate agent logic

## Non-Goals

- on-device full agent execution on iOS or Android
- separate agent implementations per platform
- large local multi-model orchestration on a 16 GB laptop
- strong container/VM isolation in this phase
- exports, realtime fan-out, or broader tool autonomy before the Phase 2
  backlog item is scheduled
- any document describing Phase 2 capabilities as already live
