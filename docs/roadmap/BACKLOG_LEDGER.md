# Backlog Ledger (Canonical)

**Purpose:** single source of truth for postponed / follow-up work.
If it is not recorded here — it does not exist.

## Rules (non-negotiable)
1) Any postponed work MUST be recorded here immediately.
2) Each item MUST include:
   - Owner
   - Priority (P0/P1/P2)
   - Target PR (number or placeholder)
   - Reason for deferral
   - Links to relevant audit/docs
   - DoD (acceptance criteria)
3) Every PR description MUST include a "Deferred / Follow-ups" section with links to items here.
4) Closing an item requires:
   - PR merged OR explicit "won't do" decision recorded (with reason).

---

## P0 — Next (Must happen)
- [ ] PR-560 Web Thin Client (BMI)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-560
  - Reason: separated scope; iOS PR-559 must merge first
  - Links:
    - docs/audit/IOS_WEB_THIN_CLIENT_AUDIT.md
  - DoD:
    - Web calls POST `/api/v1/bmi/calculate` only
    - No BMI math / thresholds / inference in web client
    - Contract-driven UI only
    - Add web anti-duplication guard (equivalent to iOS guard concept)
    - CI green

---

## P1 — Improvements (Optional / polish)

- [ ] Fix or restore AnimationTests.swift (iOS)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD (separate from PR-559)
  - Reason: pre-existing compilation failures (missing types: PulsingView, ShimmerEffect, SlideInTransition, FadeTransition, AnimatedProgressRing, NutritionSegment; internal access issues). Excluded from PulsePlateTests target to unblock PR-559 CI.
  - Links:
    - ios/PulsePlate/Tests/AnimationTests.swift
    - ios/PulsePlate.xcodeproj/project.pbxproj (line 52: removed from membershipExceptions)
  - DoD:
    - AnimationTests.swift compiles without errors
    - All referenced types/modifiers are accessible (public/internal as needed)
    - Tests restored to PulsePlateTests target
    - CI green with AnimationTests included

- [ ] Wire soft paywall CTA to real paywall router (iOS)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD
  - Reason: paywall navigation infrastructure not yet available; hook is rendered but CTA is no-op
  - Links:
    - ios/PulsePlate/Screens/BMICalculatorScreen.swift (line ~73)
  - DoD:
    - Paywall router/navigation handler implemented
    - SoftPaywallHookView CTA wired to navigation
    - No TODO comments in production code
- [ ] Optional: CI script guard for iOS (repo-wide scan)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD
  - Reason: current Swift Testing guard is sufficient; script is hardening
  - Links:
    - docs/audit/PR_559_ANTI_DUPLICATION_GUARDS.md
  - DoD:
    - GH Actions step scans iOS app Swift sources for forbidden patterns
    - Excludes fixtures/mocks
    - Documented in ios/AGENTS.md

- [ ] Optional: tighten guard false-positives (comment stripping / pattern tuning)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD
  - Reason: avoid guard flakiness if comments include examples
  - Links:
    - ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift
  - DoD:
    - Guard remains strict but avoids comment-only hits
    - CI remains deterministic

---

## P2 — Future (Low priority / research)
- (None currently)

---

**Last updated:** 2026-01-19
**Maintainer:** @katsiaryna_kavaleuskaya
