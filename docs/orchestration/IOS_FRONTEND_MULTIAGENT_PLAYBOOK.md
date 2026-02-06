# iOS + Frontend Multi‑Agent Playbook (Welcome Gate → Backend Realization)

**Last updated:** 6 February 2026
**Owner:** @katsiaryna_kavaleuskaya
**Scope:** iOS (`ios/**`) + Web (`frontend/**`) tasks that must ship as **thin clients** against backend contracts.

This playbook is intentionally practical: it describes **what artifacts must exist** so progress is visible and tasks are solved “by the whole team”.

---

## 0) Canonical anchors (do not duplicate rules)

- Global invariants + quality gates: `AGENTS.md`
- iOS invariants (thin client + CI): `ios/AGENTS.md`
- Web invariants (thin HTTP adapter + OpenAPI types): `frontend/AGENTS.md`
- Orchestration workflow (single SoT): `docs/orchestration/workflow.md`
- Canonical backlog (single SoT): `docs/roadmap/BACKLOG_LEDGER.md`

---

## 1) Team roles (who owns what)

- **Coordinator (agent-coordinator / PM-brain):**
  - writes Task Analysis + assigns tracks
  - owns “scope discipline” and ledger hygiene
  - enforces sync points and DoD
- **Architecture specialist:**
  - validates placement, invariants, thin-client constraints
  - flags forbidden patterns early (before implementation)
- **Creative designer:**
  - visual direction + assets checklist
  - a11y / HIG consistency review (spacing, readability, motion restraint)
- **Marketing strategist:**
  - copy deck (RU/EN/ES keys + variants)
  - value prop + CTA strategy (App Store-safe, no dark patterns)
- **Implementation (iOS/frontend dev):**
  - builds the slice using canonical HTTP/client seams
  - adds tests and keeps guard tests green
- **QA (human + automated):**
  - deterministic demo script + regression checklist
  - verifies localization + accessibility + key flows

---

## 2) “One task” lifecycle (mandatory)

Follow `docs/orchestration/workflow.md`, but for iOS/frontend tasks add these **hard deliverables**.

### 2.1 Pre-flight (must exist before coding)

- **Ledger item** in `docs/roadmap/BACKLOG_LEDGER.md` (or confirm it already exists)
  - Owner, Priority, Target PR, Reason, Links, DoD
- **Contract pointer**
  - Backend endpoint path(s) and response model(s)
  - If OpenAPI needs regeneration: note “requires `make openapi`” (backend work)
- **Design packet**
  - Figma link (or “temporary wireframe in doc” if no Figma yet)
  - Asset list (icons/illustrations), no text baked into images
- **Copy packet**
  - Key list (e.g. `onboarding.welcome.*`) and translations RU/EN/ES
  - 1–2 copy variants for A/B (optional; can be deferred)
- **Acceptance criteria**
  - “What the user sees” (screens, states, and the exact happy-path)
  - Error/empty/loading states included

### 2.2 Implementation track (thin slice)

- **iOS:** SwiftUI UI + storage + navigation wired at the single gate point
- **Web:** use `frontend/src/api/client.ts` only; types from `frontend/src/api/schema.ts`
- **Both:** no business logic duplication, no tier inference on clients

### 2.3 Verification track (before calling it “done”)

- **iOS local:** `make ios-test` (recommended before push)
- **Web local:** run thin-client guard test + build
  - `npm test -- --run src/api/__tests__/thin-client-guards.test.ts`
  - `npm run build`
- **Backend involved?** then `make verify` (root gate)

---

## Visibility Loop (Single Source of Truth)

Daily visibility requirements:
- 6–10 screenshots (RU/EN, light/dark if relevant)
- 20–30s screen recording of the flow
- Short daily changelog (3–7 bullets)

This section is the canonical reference. Other documents must link here and must not duplicate the rules.

### Daily artifacts (required while a task is in progress)

- **Screenshots (6–10):**
  - Light/Dark
  - RU + EN (ES spot-check if touched)
  - at least 1 screenshot with larger Dynamic Type (iOS)
- **20–30s screen recording:** happy path end-to-end
- **Short changelog:** 3–7 bullets (what changed in the app today)

### Where to put artifacts

- Prefer: PR description + PR comments (keeps review context)
- Optional: `docs/roadmap/` notes only if it changes long-term plans

---

## 4) Welcome Gate (PR-653) — standard operating packet

Anchor audit: `docs/audit/PR_653_P0_WELCOME_ONBOARDING_4SCREENS_AUDIT.md`

Supporting packets:

- Design direction: `docs/design/WELCOME_GATE_VISUAL_DIRECTION.md`
- Visual philosophy: `docs/design/WELCOME_GATE_VISUAL_PHILOSOPHY.md` (canvas is maintained externally in Figma / PR thread)
- Copy deck (RU/EN/ES variants): `docs/marketing/WELCOME_GATE_COPY_DECK.md`
- Paywall positioning (ethical): `docs/marketing/WELCOME_GATE_PAYWALL_POSITIONING.md`
- iOS-only experiment plan: `docs/marketing/WELCOME_GATE_EXPERIMENT_PLAN.md#variant-mapping-single-reference`
- GTM outline: `docs/marketing/WELCOME_GATE_GTM_OUTLINE.md`

### Required keys (namespace)

- `onboarding.welcome.screen{1..4}.{title,body}`
- `onboarding.welcome.cta.{continue,back,start}`
- `onboarding.welcome.stepA11y` (format string)

### Persistence (versioned)

- `has_seen_welcome_v1` only (future: `v2`, never mutate semantics in-place)

---

## 5) Scaling beyond Welcome Gate (backend realization)

Use `docs/roadmap/IOS_BACKEND_REALIZATION_ROADMAP.md` as the “what ships next”.

**Rule:** every “backend feature” must become an **app-visible** slice with:

- contract pointer
- iOS screen(s)
- loading/error/empty states
- i18n + a11y
- tests + guard tests green
- daily screenshots/video evidence

---

## 6) Stop conditions (fail fast)

Stop execution immediately if any of these is true:

- No ledger item exists for a deferred / postponed decision.
- iOS/web client introduces domain logic (BMI math/thresholds, tier inference).
- New networking path appears (direct `URLSession` or direct `fetch()`).
- CI/guard tests fail and are not addressed.
