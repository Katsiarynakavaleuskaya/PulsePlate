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

## 0.1 Design canon (cross‑platform) — what is SoT vs what is UI-only

This section defines the **design canon** for Web+iOS work. It is intentionally simple: it exists to prevent
“every screen invents its own styles” drift and to make delegation to specialists predictable.

### Source of truth (SoT)

- **Contracts**: OpenAPI + backend schemas are the only SoT for data/fields (`AGENTS.md:L418-L424`, `AGENTS.md:L682-L706`).
  - Web consumes `frontend/src/api/schema.ts` (generated; do not edit by hand) (`frontend/src/api/schema.ts:L1-L6`, `frontend/AGENTS.md:L17-L18`).
  - iOS consumes aligned DTOs (example: `ios/PulsePlate/Models/NutritionData.swift:L7-L28`; SoT pipeline note: `ios/AGENTS.md:L91-L94`).
- **Thin-client policy**: no business logic duplication on clients (`AGENTS.md:L426-L457`, `ios/AGENTS.md:L34-L55`, `frontend/AGENTS.md:L23-L33`).
- **Design tokens (Web)**: `frontend/src/styles/tokens.ts` (`frontend/src/styles/tokens.ts:L1-L120`).

### UI-only (allowed) mapping

- **View models**: small mapping layers for *display* are allowed (formatting, grouping, i18n lookup), but must not
  re-compute domain values (BMI thresholds, tier inference, risk logic).

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

## 1.1 Specialist agent roster (recommended for fast, consistent UI shipping)

These “agents” can be humans, AI subagents, or checklists. What matters is the **explicit I/O contract**.

- **Design Token Sync (design-token-sync)**
  - Input: token canon (starting point: `frontend/src/styles/tokens.ts`)
  - Output: a single “token delta” note (what changed + why) + updated token mirrors (platform-specific), or a backlog entry if deferred
- **Component Library Audit (component-library-audit)**
  - Input: changed UI files
  - Output: violations list (`file:line`) for hardcoded colors/spacing/typography outside tokens + suggested replacements
- **Accessibility Enforcer (accessibility-enforcer)**
  - Input: changed UI components/screens
  - Output: a11y checklist result (must include: labels, focus, contrast, touch targets, Dynamic Type)
- **FitChef Asset Manager (fitchef-asset-manager)**
  - Input: UI state + message intent (“success”, “error”, “empty”, “onboarding”)
  - Output: asset checklist + requested assets (SVG/Lottie) + usage constraints (no text baked into images)
- **Conversion Safety (conversion-safety)**
  - Input: paywall/onboarding/result screen spec
  - Output: conversion checklist + App Store safe copy guidance (no medical claims, no dark patterns)

Optional (future features):

- **CV Contract Agent (cv-contract-agent)**: schemas for photo → items → confidence → uncertainty, plus deterministic degrade states
- **Sensor Invariant Guard (sensor-invariant-guard)**: physically plausible bounds + calibration UX rules (no “magic sizing”)

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

### 2.1.1 Design system packet (required for any new UI component)

This is how we keep Web+iOS visually consistent without blocking velocity.

- **Token usage**
  - No hardcoded colors/spacing/typography in new components unless explicitly justified
  - Any new “style decision” must be either:
    - mapped to an existing token, or
    - proposed as a new token (and recorded in the ledger if deferred)
- **Accessibility defaults**
  - iOS: VoiceOver labels + Dynamic Type sizing + 44×44pt tap targets
  - Web: semantic elements + keyboard focus states + 48×48px touch targets

### 2.2 Implementation track (thin slice)

- **iOS:** SwiftUI UI + storage + navigation wired at the single gate point
- **Web:** use `frontend/src/api/client.ts` only; types from `frontend/src/api/schema.ts` (`frontend/AGENTS.md:L29-L32`, `frontend/AGENTS.md:L59-L63`)
- **Both:** no business logic duplication, no tier inference on clients (`AGENTS.md:L426-L457`)

### 2.3 Verification track (before calling it “done”)

- **iOS local:** `make ios-test` (recommended before push)
- **Web local:** run thin-client guard test + build
  - `npm test -- --run src/api/__tests__/thin-client-guards.test.ts`
  - `npm run build`
- **Backend involved?** then `make verify` (root gate)

---

## 3) “Visibility loop” (so progress is undeniable)

### 3.1 Accessibility checklist (ship-blocking for new UI)

Minimum bar (must be explicitly checked in PR description):

- **iOS**
  - VoiceOver: all interactive elements have meaningful labels; decorative images hidden
  - Dynamic Type: no fixed font sizes; layout remains usable at larger sizes
  - Touch targets: ≥44×44pt
  - Contrast: text/background meets WCAG AA intent (verify for Navy/Blue/Green/Red usage)
- **Web**
  - Semantic HTML (no clickable divs for primary actions)
  - Keyboard: focus visible; modals trap focus; Escape closes where applicable
  - Touch targets: ≥48×48px
  - Contrast: WCAG AA (4.5:1 for body text)

### 3.2 Conversion / App Store checklist (for onboarding & paywalls)

- Value-first (no medical claims): “wellness tracking”, not diagnosis/treatment
- Clear CTA above the fold; safe dismissal path exists
- Tier differentiation is explicit (FREE vs PRO vs VIP) without trickery
- Copy is localized (RU/EN/ES keys), no text baked into images/screenshots

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
- iOS-only experiment plan: `docs/marketing/WELCOME_GATE_EXPERIMENT_PLAN.md`
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

---

## 7) Adding a new specialist agent (how to scale the team safely)

When a new agent is proposed (e.g., algorithmic-art for brand textures, CV agent, security auditor), record:

- **Role name** + **scope boundary** (what it MUST NOT do)
- **Inputs** it consumes (files, contracts, metrics)
- **Outputs** it produces (docs, checklists, asset lists, guard tests)
- **Quality gates** it must not violate (thin-client, OpenAPI determinism, docs-only PR rules)
- **Backlog entry** if implementation work is deferred
