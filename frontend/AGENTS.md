# Agent instructions (scope: frontend/ and subdirectories)

## Scope and layout
- This AGENTS.md applies to: `frontend/` and below.
- Key directories: `frontend/src/`, `frontend/src/api/`, `frontend/public/`.

## Commands (run from `frontend/`)
- Runtime requirement: Node `24.x` (repo-canonical range: `>=24.0.0 <25.0.0`; CI pin lives in repo-root `.nvmrc`)
- Install: `npm install`
- Dev: `npm run dev`
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

## Source-patched Caddy builder

The Caddy v3 backport has one maintained patch and one real consumer test under
`frontend/patches/`, governed by
`docs/security/CVE-2026-116587-caddy-go-jose.md`. Apply it only to the verified
official v3.0.5 copy with standard git apply; preserve the module cache and sumdb.
The recipe admits exactly its version-qualified local replacement, binds the
whole source before/after tests/build, and rejects all other replacements.
Run the complete patched-module tests and actual smallstep compatibility tests
before Caddy compilation in a qualified admitted environment. Keep source,
patch, tree, graph and binary identities synchronized after formatting.
The byte-pinned upstream patch includes significant unified-diff context spaces;
exclude only its exact path from trailing-whitespace normalization and retain
its full digest and application checks.
Cached build output is not fresh test execution. Historical xnet060 remains
Go1.26.9/four-get/zero-Replace and does not qualify this patched recipe.
Source tests do not authorize exception removal or establish scanner PASS;
retain full scanner inventory and the owner's exact native evidence and remaining
full-image proof. The existing `caddy-contract` job selects `ubuntu-24.04`.
That runner pin is preventive configuration, not observed qualification of this
source-patched producer. A runner or image-store change requires actual native
requalification; another recipe's runner evidence cannot qualify this one.
The source-qualified producer/consumer requires the exact closed regular-member
inventory owned by `scripts/ci/check_docker_runtime_dependency_surface.py` at
`/usr/share/pulseplate-caddy-build`, including the original sixteen v3 proof members
and the explicitly bound standard-library extension. Replaced-v3 native Sum/Version
omissions must remain truthful. Its six candidate/official/secret full+HC scans
share a frozen scanner/DB epoch, and complete native finding/fingerprint relations
plus owned cleanup must pass before candidate artifact release. No D policy
filter or calendar renewal substitutes for this proof. Preserve all lower findings
and v3 UNKNOWN. The owning job's 220-minute cap and shared phase reserves are
planning ceilings, not observed fit; each 330-second scan includes 300 seconds of work and
bounded termination/capture. Keep historical attempts and failures as history,
without using them as a new-attempt prohibition or successful hosted proof.
Authenticated API reads keep the canonical no-redirect opener inside the existing
process owner: authentication and response collection share 20 seconds, with
10 seconds reserved for owned cleanup in the same 30-second call slot. Bind the
fixed helper source and actual namespace-package resolution; reject source shadows
and project bytecode without inventing package initializer inputs.


## Contracts & Types policy (OpenAPI)

**Canonical source:** See root `AGENTS.md` section "OpenAPI generation (determinism requirement)" for full policy.

### Frontend-specific rules

- **Types:** Import types from `src/api/schema.ts` (generated by `openapi-typescript`).
- **Mapping layers:** Small UI-only mapping layers (view models) are allowed, explicitly named and localized.
- **Forbidden:**
  - Manual API request/response types that duplicate backend schemas.
  - Editing `src/api/schema.ts` by hand.

## Token loader qualification

The existing token generator reads the eleven explicit sources through
`style-dictionary.config.mjs` without the retired Style Dictionary dependency.
Keep decoded duplicate-key rejection, supported typography objects, own-property
alias traversal, explicit platform union and validation/rendering before writes.
Changing this loader requires native `tokens:build` / `tokens:check` and the
independent Python parity oracle under the qualified Node version, with exact
CSS/TS/Swift byte comparison against the unchanged authoring inputs and old
qualified outputs. Do not repair loader drift by rewriting generated mirrors.
The existing `--check` builds before checking drift; it is not read-only.

## Checked Redocly install and use

The canonical frontend `ci` paths explicitly run
`node scripts/check-redocly-compat.mjs apply` after npm succeeds. This finite
Redocly1.34.15 adaptation has no lifecycle hook. For a direct manual frontend
`npm ci`, run that apply command explicitly; `generate-types` independently
runs verify before the CLI. Cached Make installs also verify the complete
installed payload before use. A checker failure is terminal: do not reinstall,
retry npm, bypass verify or rewrite lock integrity to derived source hashes.
Root, audit and lock-only operations do not apply the adaptation. Preserve the
fixed687 original/derived members and measured modes, exact parent dependency
resolution and existing brace-expansion floors. Use canonical `make openapi`
for combined schema/type generation as required by root instructions.
