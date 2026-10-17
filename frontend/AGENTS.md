# Agent instructions (scope: frontend/ and subdirectories)

## Scope and layout
- This AGENTS.md applies to: `frontend/` and below.
- Key directories: `frontend/src/`, `frontend/src/api/`, `frontend/public/`.

## Commands (run from `frontend/`)
- Runtime requirement: Node `24.x` (repo-canonical range: `>=24.0.0 <25.0.0`; CI pin lives in repo-root `.nvmrc`)
- Install: `npm install`
- Dev: `npm run dev`
- Private remote development: inside the selected Linux devcontainer, from its repo root use
  `VITE_API_BASE=/api/v1 ./scripts/frontend_npm.sh --prefix frontend run dev -- --mode remote --host 0.0.0.0 --port 5173 --strictPort`.
  The opt-in development proxy targets only the backend on container loopback
  `127.0.0.1:8001`; build and preview do not enable it. Use this bind only inside
  the private devcontainer with no published Docker ports and loopback-only
  SSH forwarding through the inspected current container bridge address. LOCAL
  PulsePlate ports are backend `18001` and web `15173`, mapped to container
  `8001`/`5173`; preserve existing Surreal services on local `8000`/`8001`.
  Codex sends commands through explicit SSH to the selected container, binding
  current I/W material and persisted run/result; SSH/sync failure stops without
  silent heavy Mac fallback. Optional remote CLI is separate; no editor
  is required. Setup and acceptance live in
  [`docs/dev/REMOTE_DEVELOPMENT.md`](../docs/dev/REMOTE_DEVELOPMENT.md).
- Typecheck: `npm run typecheck`
- Production API/foundation lint: `npm run lint:foundation` (explicit existing config,
  authored top-level API/premium TypeScript and analytics, zero warnings). Generated
  `src/api/schema.ts` is excluded precisely; this command does not claim all frontend
  or API tests are lint-clean. Frontend CI runs native controls after installation;
  the Python workflow contracts remain runnable without Node.
- Authored UI lint: `npm run lint:ui` (explicit existing config, recursive
  `src/components/ui/**/*.{ts,tsx}`, including stories, tests and nested sources,
  zero warnings). Existing `.d.ts` exclusion and test-specific rule exceptions
  remain unchanged; this does not claim the entire frontend is lint-clean.
  The same Frontend CI native-control step independently enumerates nonempty
  regular UI membership, rejects ignored/omitted members and checks exact native
  lint/startup outcomes with owned fixture cleanup. Python `node24` workflow
  contracts bind reviewed wiring only; actual ESLint execution is separate evidence.
- Build: `npm run build`
- Preview: `npm run preview`
- Test: `npm run test`, `npm run test:ci`, `npm run test:precommit`, `npm run test:coverage`
- Full dependency guard (repo root): `tests/test_frontend_dependency_guards.py`
  requires canonical Node/npm for registry-spec and native virtual-graph checks.
  Python-only range/contract subsets supplement the full native guard. Derive
  guest prerequisites from the actual selected calls and their native tools,
  rather than the `.py` filename.
- Generate API types: `npm run generate-types`
- OpenAPI sync parity: when `make openapi` or frontend type generation touches
  `frontend/`, run those steps under Node `24.x` to match CI and lockfile engines.

## Conventions
- Production build performs TypeScript checking before Vite bundling.
- API base is `/api/v1`; keep client paths aligned with backend routers.
- OpenAPI types are generated from `src/api/openapi.json` into `src/api/schema.ts`.
- Keep UI changes in sync with backend schema updates.
- For coordinated iOS+frontend work (designer/marketing/dev), follow:
  `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md`.
- Visual quality workflow, review gates, and button-level references are canonical in root
  `AGENTS.md`; this scoped file should only reference that SoT (no duplicated checklist text).

## Thin HTTP Adapter Policy (Hard Rule)

**Invariant:** See root `AGENTS.md` → "Thin HTTP Adapter Policy (Hard Rule)" for full policy.

### Web-specific enforcement

- ❌ Direct `fetch()` calls outside `src/api/client.ts`
- ✅ Use `api()` / `fetchBlob()` from `src/api/client.ts`
- ✅ OpenAPI-generated types from `src/api/schema.ts`
- ✅ Guards: `src/api/__tests__/thin-client-guards.test.ts` must stay green
- ✅ Web premium truth must come only from canonical backend/store state; legacy mock
  purchase/restore flows must stay out of shared release-path handlers and runtime-facing tests

### Canonical local checks

```bash
# Run guard tests (thin-client policy enforcement)
npm test -- --run src/api/__tests__/thin-client-guards.test.ts

# Run all frontend tests
npm test

# Build (catches TS errors)
npm run build
```

**Links:**
- Root policy: `AGENTS.md` (Thin HTTP Adapter Policy)
- Audit: `docs/audit/PR_586_WEB_THIN_HTTP_ADAPTER_AUDIT.md`

## FitChef web client policy

- Web FitChef surfaces must stay thin adapters over backend contracts; no client-side nutrition math, entitlement inference, or action synthesis.
- Current live FitChef mascot routes remain `/api/v1/insight/fitchef*`; any future `/api/v1/pro/fitchef/*` or `/api/v1/vip/fitchef/*` usage must follow additive contract rollout.
- UI must render structured DTO fields or frozen response envelopes; do not parse free-form prose to derive routing, badges, or gated states.
- FREE-tier web surfaces may show bounded/static FitChef guidance, but must not expose open-ended coach runtime.

---

## Realtime WebSocket adapter policy

- Raw `WebSocket(...)` construction is allowed only in `src/api/wsClient.ts`.
- `src/api/__tests__/thin-client-guards.test.ts` must enforce this restriction and stay green.
- Incoming realtime payloads MUST be minimally validated at runtime in adapter layer
  before forwarding to UI callbacks (at least protocol `version` and event `type`).
- WebSocket state and message callbacks in adapter code should use explicit function type
  signatures to keep TypeScript guardrails clear in review and CI.

---

## Contracts & Types policy (OpenAPI)

**Canonical source:** See root `AGENTS.md` section "OpenAPI generation (determinism requirement)" for full policy.

### Frontend-specific rules

- **Types:** Import types from `src/api/schema.ts` (generated by `openapi-typescript`).
- **Mapping layers:** Small UI-only mapping layers (view models) are allowed, explicitly named and localized.
- **Forbidden:**
  - Manual API request/response types that duplicate backend schemas.
  - Editing `src/api/schema.ts` by hand.
