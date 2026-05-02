# App Store Release Notes Template and Claim Policy

> Canonical governance for `release_notes.txt` across all Fastlane locales.
> This document defines what release notes may and may not claim, provides
> modular templates for EN/RU/ES, and cross-references the reviewer submission
> matrix and screenshot asset gate.

**Last updated:** 2026-05-02
**PR train:** `epic/appstore-release-readiness-full-feature` (PR-6)
**Owner:** @katsiaryna_kavaleuskaya

---

## Table of Contents

1. [Purpose](#1-purpose)
2. [Source of Truth References](#2-source-of-truth-references)
3. [Scope](#3-scope)
4. [Release Notes Classification System](#4-release-notes-classification-system)
5. [Claim Gate Rules](#5-claim-gate-rules)
6. [Forbidden Claims in Release Notes](#6-forbidden-claims-in-release-notes)
7. [Current Release Notes Audit](#7-current-release-notes-audit)
8. [EN Template](#8-en-template-en-us)
9. [RU Template](#9-ru-template-ru-ru)
10. [ES Template](#10-es-template-es-es)
11. [Release Note Block Library](#11-release-note-block-library)
12. [Reviewer Notes Dependency Matrix](#12-reviewer-notes-dependency-matrix)
13. [Final Submission Rule](#13-final-submission-rule)
14. [Non-Goals](#14-non-goals)
15. [Decision Log](#15-decision-log)
16. [Validation Checklist](#16-validation-checklist)

---

## 1. Purpose

Release notes (`ios/fastlane/metadata/<locale>/release_notes.txt`) are a public
App Store claim surface. They are visible to every App Store visitor and are
subject to the same governance as description, subtitle, and promotional text.

This document ensures that:

- Release notes never claim features that are not release-enabled
- Release notes never contain forbidden medical, pricing, or outcome claims
- Release notes are claim-equivalent across all supported locales (EN/RU/ES)
- Every claim in release notes has a corresponding reviewer-note entry
- Template blocks are reusable and auditable

---

## 2. Source of Truth References

| Document | What it governs |
| --- | --- |
| `docs/release/APPSTORE_FASTLANE_METADATA_AUDIT.md` | Metadata forbidden claims, description alignment, risk table |
| `docs/release/APPSTORE_REVIEWER_SUBMISSION_MATRIX.md` | Reviewer note requirements by feature surface |
| `docs/release/APPSTORE_SCREENSHOT_ASSET_GATE.md` | Screenshot scenario classification and gate rules |
| `docs/release/APPSTORE_FEATURE_ASSET_MATRIX.md` | Feature-level submission status |
| `docs/release/APPSTORE_RELEASE_READINESS_EPIC.md` | Epic SoT for PR train (PR-0 through PR-10) |
| `docs/contracts/IOS_STOREKIT_PRODUCTS_CONTRACT.md` | StoreKit pricing truth; copy fallback rules |
| `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md` | Payment activation contract |
| `docs/legal/Privacy.md` | Privacy policy (data categories, disclosures) |
| `docs/runbooks/IOS_APPSTORE_ASSETS_ROLLOUT.md` | Protected upload procedure and rollout steps |
| `ios/fastlane/metadata/review_information/notes.txt` | Current reviewer notes |

---

## 3. Scope

### In scope

- `ios/fastlane/metadata/en-US/release_notes.txt`
- `ios/fastlane/metadata/ru-RU/release_notes.txt`
- `ios/fastlane/metadata/es-ES/release_notes.txt`
- Governance rules for what may appear in release notes
- Template blocks and claim classification

### Out of scope

- Actual text remediation of release notes files (deferred to PR-8+)
- Description, subtitle, promotional text (governed by PR-5 metadata audit)
- Screenshot captions and keywords
- Protected upload execution (operator-only; governed by rollout runbook)

---

## 4. Release Notes Classification System

Every claim in release notes must be classified before submission.

| Classification | Meaning | Submission allowed? |
| --- | --- | --- |
| `SAFE_TO_MENTION` | Feature is implemented, release-enabled, privacy-disclosed, and reviewer-note-covered | Yes |
| `MENTION_WITH_REVIEWER_NOTE` | Feature exists and is release-enabled but requires specific reviewer note support (HealthKit, AI, StoreKit) | Yes, only if reviewer note exists |
| `INTERNAL_ONLY` | Feature exists in repo but is feature-flagged off or not release-enabled for this version | No |
| `BLOCKED_FROM_RELEASE_NOTES` | Feature is `IMPLEMENTATION_REQUIRED` per asset matrix, or claim would be forbidden | No |

### Classification derivation rules

1. If the feature is `IMPLEMENTATION_REQUIRED` in `APPSTORE_FEATURE_ASSET_MATRIX.md`
   then the release note claim is `BLOCKED_FROM_RELEASE_NOTES`.
2. If the feature is `SUBMIT_READY` and requires no special reviewer note
   then the release note claim is `SAFE_TO_MENTION`.
3. If the feature is `SUBMIT_READY` but touches HealthKit, AI, or StoreKit
   then the release note claim is `MENTION_WITH_REVIEWER_NOTE`.
4. If the feature is behind a feature flag that is off in the release build
   then the release note claim is `INTERNAL_ONLY`.

---

## 5. Claim Gate Rules

These rules apply to every line in `release_notes.txt` for every locale.

### Gate 1: Feature must be release-enabled

A release note must not mention a feature unless that feature is confirmed
`SUBMIT_READY` in the feature asset matrix or has a documented exception.

### Gate 2: Privacy must cover the data flow

If the release note mentions a feature that processes user data (HealthKit,
AI analysis, nutrition tracking), the corresponding data flow must be
disclosed in `ios/PulsePlate/PrivacyInfo.xcprivacy` and
`ios/fastlane/app_privacy_details.json`.

### Gate 3: Reviewer notes must explain applicable flows

If the release note mentions HealthKit, AI, or subscription features,
the reviewer notes must contain a corresponding explanation per the
reviewer submission matrix.

### Gate 4: No hardcoded pricing

Release notes must not contain specific prices, trial durations, or discount
percentages. Per `IOS_STOREKIT_PRODUCTS_CONTRACT.md`, pricing truth comes from
StoreKit runtime or App Store Connect only.

### Gate 5: No medical or outcome claims

Release notes must not contain any forbidden claims (see section 6).

### Gate 6: Claim equivalence across locales

All three locales (EN/RU/ES) must make the same claims. It is forbidden to
mention a feature in one locale but omit it in another (or vice versa).
Wording may differ for natural language quality, but the claim set must match.

### Gate 7: No feature-flagged content depicted as live

If a feature is behind a flag that is off in the release build, the release
note must not mention it as available.

---

## 6. Forbidden Claims in Release Notes

<!-- pulseplate-allow:blocker-example — This section lists forbidden claim patterns as policy examples. -->

The following claims are forbidden in any `release_notes.txt` file. This list
is aligned with `APPSTORE_FASTLANE_METADATA_AUDIT.md` section "Forbidden Claims
in App Store Metadata".

| # | Category | Forbidden pattern | Example of violation |
| --- | --- | --- | --- |
| 1 | Diagnosis | Claiming the app diagnoses health conditions | "Diagnose nutritional deficiencies" |
| 2 | Treatment | Claiming the app treats any medical condition | "Treats obesity with personalized plans" |
| 3 | Therapy | Claiming the app provides therapy or CBT treatment | "CBT therapy sessions included" |
| 4 | Cure | Claiming the app cures any condition | "Cure your metabolic issues" |
| 5 | Guaranteed weight loss | Asserting definite weight-loss outcomes | "Lose 5 kg in 2 weeks" |
| 6 | Guaranteed health outcome | Asserting definite health improvements | "Guaranteed to lower your BMI" |
| 7 | Doctor/medical-device framing | Positioning the app as medical advice or device | "Your pocket nutritionist doctor" |
| 8 | Hardcoded pricing | Stating specific prices or trial durations | "Only $4.99/month with 7-day free trial" |
| 9 | Live AI without disclosure | Claiming AI features without disclosing third-party processing | "AI-powered meal suggestions" (without reviewer note) |
| 10 | Unreleased features | Mentioning features not yet release-enabled | "New weekly meal planner" (if `IMPLEMENTATION_REQUIRED`) |

### Wellness-safe alternatives

Instead of forbidden patterns, use wellness-only language:

- "Track your wellness journey" (not "diagnose your health")
- "Explore nutrition insights" (not "treat nutritional deficiencies")
- "Understand your body composition" (not "cure metabolic issues")
- "See current pricing in the app" (not "$4.99/month")

---

## 7. Current Release Notes Audit

### Current content (as of PR-5 / PR #1620)

**en-US:**

```text
This release refreshes PulsePlate onboarding copy, wellness guidance, and App Store presentation.
```

**ru-RU:**

```text
В этом выпуске обновлены локализация, wellness-подсказки и представление PulsePlate в App Store.
```

**es-ES:**

```text
Esta versión actualiza la experiencia de PulsePlate, la localización y la presentación en App Store.
```

### Audit result

| Check | Result | Notes |
| --- | --- | --- |
| Forbidden claims | PASS | No medical, pricing, or outcome claims |
| Feature claim accuracy | PASS | Generic text, no specific feature claims |
| Claim equivalence (EN/RU/ES) | PASS | All three locales make the same generic claim |
| Pricing claims | PASS | No pricing mentioned |
| AI disclosure | N/A | No AI features mentioned |
| HealthKit disclosure | N/A | No HealthKit mentioned |

**Classification:** All three locales are `SAFE_TO_MENTION` (generic, no feature claims,
no forbidden wording).

**Risk:** P2 (generic text is safe but does not inform users about actual release content).

**Required action:** Update release notes text before final App Store submission
to reflect actual release content using approved template blocks. This text
remediation is deferred to PR-8+ in the release readiness train.

---

## 8. EN Template (en-US)

Use the following template for `ios/fastlane/metadata/en-US/release_notes.txt`.
Select only blocks whose features are classified `SAFE_TO_MENTION` or
`MENTION_WITH_REVIEWER_NOTE` (with reviewer note confirmed).

```text
PulsePlate <version> — What's New

[BLOCK:core_bmi]
- Improved BMI calculation and body composition insights

[BLOCK:wellness_guidance]
- Updated wellness guidance and onboarding experience

[BLOCK:localization]
- Refreshed localization for Russian, English, and Spanish

[BLOCK:healthkit_read]
- Optional Health data integration for personalized tracking (read-only)

[BLOCK:nutrition_pro]
- Enhanced nutrition analysis for PRO subscribers

[BLOCK:storekit_subscription]
- Subscription management improvements (see the app for current pricing)

[BLOCK:ai_insight]
- Wellness insights powered by AI (third-party processing disclosed in Privacy Policy)

[BLOCK:general_polish]
- Bug fixes and performance improvements
```

**Instructions:**

1. Remove `[BLOCK:...]` labels before submission (they are template markers only).
2. Remove any block whose feature is not `SAFE_TO_MENTION` or confirmed
   `MENTION_WITH_REVIEWER_NOTE`.
3. Replace `<version>` with the actual version number.
4. App Store Connect enforces a 4000-character limit for release notes.

---

## 9. RU Template (ru-RU)

Use the following template for `ios/fastlane/metadata/ru-RU/release_notes.txt`.
Claim set must match EN exactly. Wording is adapted for natural Russian.

```text
PulsePlate <version> — Что нового

[BLOCK:core_bmi]
- Улучшенный расчёт ИМТ и анализ состава тела

[BLOCK:wellness_guidance]
- Обновлённые рекомендации по здоровому образу жизни и приветственный экран

[BLOCK:localization]
- Обновлённая локализация для русского, английского и испанского языков

[BLOCK:healthkit_read]
- Интеграция с Apple Health для отслеживания показателей (только чтение, по желанию)

[BLOCK:nutrition_pro]
- Расширенный анализ питания для подписчиков PRO

[BLOCK:storekit_subscription]
- Улучшения управления подпиской (актуальные цены — в приложении)

[BLOCK:ai_insight]
- Рекомендации на основе ИИ (обработка третьей стороной раскрыта в Политике конфиденциальности)

[BLOCK:general_polish]
- Исправления ошибок и улучшения производительности
```

**Instructions:** Same as EN template. Remove unused blocks. Replace `<version>`.

---

## 10. ES Template (es-ES)

Use the following template for `ios/fastlane/metadata/es-ES/release_notes.txt`.
Claim set must match EN exactly. Wording is adapted for natural Spanish.

```text
PulsePlate <version> — Novedades

[BLOCK:core_bmi]
- Cálculo de IMC mejorado y análisis de composición corporal

[BLOCK:wellness_guidance]
- Orientación de bienestar actualizada y experiencia de bienvenida renovada

[BLOCK:localization]
- Localización actualizada para ruso, inglés y español

[BLOCK:healthkit_read]
- Integración opcional con Apple Health para seguimiento personalizado (solo lectura)

[BLOCK:nutrition_pro]
- Análisis nutricional avanzado para suscriptores PRO

[BLOCK:storekit_subscription]
- Mejoras en la gestión de suscripciones (consulta los precios actuales en la app)

[BLOCK:ai_insight]
- Información de bienestar con inteligencia artificial (procesamiento por terceros descrito en la Política de Privacidad)

[BLOCK:general_polish]
- Correcciones de errores y mejoras de rendimiento
```

**Instructions:** Same as EN template. Remove unused blocks. Replace `<version>`.

---

## 11. Release Note Block Library

Each block has conditions that must be satisfied before it can be included in
release notes.

### BLOCK:core_bmi

| Field | Value |
| --- | --- |
| Feature | BMI calculation and body composition |
| Classification | `SAFE_TO_MENTION` |
| Allowed when | Core BMI endpoint is release-enabled and smoke-tested |
| Forbidden when | BMI calculation is broken or returns undefined |
| Reviewer note dependency | None |
| Privacy dependency | None (no HealthKit required for basic BMI) |
| Asset matrix reference | `core_value` scenario (`SUBMIT_READY` after PR-8) |

### BLOCK:wellness_guidance

| Field | Value |
| --- | --- |
| Feature | Onboarding copy and wellness guidance |
| Classification | `SAFE_TO_MENTION` |
| Allowed when | Onboarding screens are implemented and localized |
| Forbidden when | Onboarding is not implemented or contains medical claims |
| Reviewer note dependency | None |
| Privacy dependency | None |
| Asset matrix reference | N/A (no dedicated scenario) |

### BLOCK:localization

| Field | Value |
| --- | --- |
| Feature | Localization for RU/EN/ES |
| Classification | `SAFE_TO_MENTION` |
| Allowed when | All three locales are present and pass metadata audit |
| Forbidden when | Any locale is missing or contains forbidden claims |
| Reviewer note dependency | None |
| Privacy dependency | None |
| Asset matrix reference | N/A |

### BLOCK:healthkit_read

| Field | Value |
| --- | --- |
| Feature | HealthKit integration (read-only) |
| Classification | `MENTION_WITH_REVIEWER_NOTE` |
| Allowed when | HealthKit read-only access is implemented, Swift 6 clean, and reviewer notes confirm read-only + optional + revocable |
| Forbidden when | HealthKit is not release-enabled or reviewer notes do not cover it |
| Reviewer note dependency | Reviewer notes lines 3-6 (HealthKit read-only, optional, revocable) |
| Privacy dependency | `PrivacyInfo.xcprivacy` must cover Health data; `app_privacy_details.json` must declare Health data flows |
| Asset matrix reference | `health_progress` scenario (`IMPLEMENTATION_REQUIRED`) |
| Special note | Block is allowed even though `health_progress` screenshot is `IMPLEMENTATION_REQUIRED` because HealthKit read access itself may be release-enabled independently of the progress UI screenshot. Release-enablement is tracked independently from screenshot readiness; the SoT for feature release status is `APPSTORE_FEATURE_ASSET_MATRIX.md` and the SoT for screenshot submission status is `APPSTORE_SCREENSHOT_ASSET_GATE.md`. |

### BLOCK:nutrition_pro

| Field | Value |
| --- | --- |
| Feature | Enhanced nutrition analysis for PRO tier |
| Classification | `MENTION_WITH_REVIEWER_NOTE` |
| Allowed when | PRO nutrition endpoints are release-enabled and StoreKit subscription flow is functional |
| Forbidden when | PRO tier is not accessible or subscription flow is broken |
| Reviewer note dependency | Reviewer notes must explain StoreKit subscription path |
| Privacy dependency | None beyond base privacy policy |
| Asset matrix reference | `nutrition_analysis` scenario (`IMPLEMENTATION_REQUIRED`) |
| Special note | Block text must not mention specific pricing; use "for PRO subscribers" only. Note: release-enablement of the PRO nutrition endpoint is tracked independently from the `nutrition_analysis` screenshot scenario; a release-enabled endpoint does not imply a submission-ready screenshot. The SoT for feature release status is `APPSTORE_FEATURE_ASSET_MATRIX.md`. |

### BLOCK:storekit_subscription

| Field | Value |
| --- | --- |
| Feature | Subscription management and StoreKit integration |
| Classification | `MENTION_WITH_REVIEWER_NOTE` |
| Allowed when | StoreKit subscription flow is implemented and backend activation works |
| Forbidden when | StoreKit returns zero products or subscription activation is broken |
| Reviewer note dependency | Reviewer notes must explain StoreKit flow and reference ASC pricing |
| Privacy dependency | None |
| Asset matrix reference | N/A (subscription is infrastructure, not a screenshot scenario) |
| Special note | Must always include "see the app for current pricing" or equivalent; never hardcode prices |

### BLOCK:ai_insight

| Field | Value |
| --- | --- |
| Feature | AI-powered wellness insights |
| Classification | `MENTION_WITH_REVIEWER_NOTE` |
| Allowed when | AI insight endpoint is release-enabled, user consent gate exists, third-party processing is disclosed in privacy policy, and reviewer notes explain AI disclosure |
| Forbidden when | AI features are feature-flagged off, consent gate is missing, or reviewer notes do not cover AI |
| Reviewer note dependency | Reviewer notes must disclose third-party LLM processing, data sent to provider, and user consent requirement |
| Privacy dependency | Privacy policy must disclose external AI providers |
| Asset matrix reference | `ai_assistant` scenario (`IMPLEMENTATION_REQUIRED`) |
| Special note | Must always include "(third-party processing disclosed in Privacy Policy)" or equivalent |

### BLOCK:general_polish

| Field | Value |
| --- | --- |
| Feature | Bug fixes and performance improvements |
| Classification | `SAFE_TO_MENTION` |
| Allowed when | Always (generic block) |
| Forbidden when | Never (this block makes no specific feature claim) |
| Reviewer note dependency | None |
| Privacy dependency | None |
| Asset matrix reference | N/A |

---

## 12. Reviewer Notes Dependency Matrix

This matrix maps release note claim types to specific reviewer note
requirements. Cross-references `APPSTORE_REVIEWER_SUBMISSION_MATRIX.md`.

> **Drift reminder:** The "Currently covered?" column references specific line
> numbers from `ios/fastlane/metadata/review_information/notes.txt`. These
> references must be updated whenever reviewer notes are modified. When
> reviewing this section, verify line references against the current content
> of `notes.txt`.

| Release note claim type | Reviewer note requirement | Submission matrix category | Currently covered? |
| --- | --- | --- | --- |
| BMI calculation | None required | Wellness-Only Positioning | Yes (line 9: wellness disclaimer) |
| Wellness guidance | None required | Wellness-Only Positioning | Yes (line 9) |
| Localization | None required | N/A | N/A |
| HealthKit read access | Read-only, optional, revocable | HealthKit Read-Only Status | Yes (lines 3-6) |
| PRO subscription features | StoreKit flow explanation | Billing/Subscription Path | Partially (line 11 references ASC) |
| Subscription management | StoreKit flow + ASC pricing reference | Billing/Subscription Path | Partially (line 11) |
| AI wellness insights | Third-party LLM disclosure, data sent, consent | AI Feature Disclosure | No (3 open items in matrix) |
| Feature-flagged-off features | List of disabled features | What Is Intentionally Not Enabled | No (1 open item in matrix) |

### Gaps requiring resolution before release

1. **AI Feature Disclosure** (3 items open): Third-party LLM disclosure,
   data-sent-to-provider notice, user consent confirmation. Blocks
   `BLOCK:ai_insight`.
2. **Billing/Subscription Path** (1 item partially open): Full StoreKit flow
   explanation needed. Partially blocks `BLOCK:storekit_subscription` and
   `BLOCK:nutrition_pro`.
3. **What Is Intentionally Not Enabled** (1 item open): Feature-flagged
   features must be listed. Blocks any `INTERNAL_ONLY` feature from being
   accidentally mentioned.

---

## 13. Final Submission Rule

Before submitting release notes to App Store Connect:

1. Every line must pass all 7 claim gate rules (section 5).
2. Every feature-specific block must satisfy its block library conditions (section 11).
3. All reviewer note dependencies must be confirmed satisfied (section 12).
4. All three locales must contain the same claim set (gate 6).
5. `[BLOCK:...]` markers must be removed from final text.
6. Version number must be filled in.
7. Total text must be under 4000 characters per locale.

**Fail-closed rule:** If any gate check fails for a block, that block must be
removed from all three locales. A submission with one locale mentioning a
feature and another omitting it is forbidden.

---

## 14. Non-Goals

This document does NOT:

- Modify actual `release_notes.txt` files (deferred to PR-8+)
- Govern `description.txt`, `subtitle.txt`, or `promotional_text.txt`
  (governed by PR-5 metadata audit)
- Define screenshot captions or keywords
- Execute protected uploads to App Store Connect
- Define StoreKit product configuration (governed by
  `IOS_STOREKIT_PRODUCTS_CONTRACT.md`)
- Change any runtime, backend, or iOS code

---

## 15. Decision Log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-05-02 | Release notes are a public claim surface requiring same governance as description | Release notes are visible to all App Store visitors; ungoverned claims risk App Store Review rejection |
| 2026-05-02 | Current generic release notes are classified `SAFE_TO_MENTION` (P2 risk) | Generic text is safe but does not inform users; update deferred to PR-8+ |
| 2026-05-02 | Template uses modular block system with per-block conditions | Enables selective inclusion based on release readiness; prevents accidental claim of unreleased features |
| 2026-05-02 | Claim equivalence across EN/RU/ES is mandatory (gate 6) | Inconsistent claims across locales is a reviewer red flag and a policy violation |
| 2026-05-02 | AI block requires explicit third-party processing disclosure | Per reviewer submission matrix and App Store Review Guidelines section 5.1.1(iii) |
| 2026-05-02 | StoreKit block must never hardcode pricing | Per `IOS_STOREKIT_PRODUCTS_CONTRACT.md` copy fallback rules |

---

## 16. Validation Checklist

Run before any release notes text update PR:

- [ ] Every feature-specific line is backed by a `SAFE_TO_MENTION` or confirmed `MENTION_WITH_REVIEWER_NOTE` block
- [ ] No forbidden claims present (run wellness language guard: `pytest -q tests/guards/test_wellness_language_blockers_guard.py`)
- [ ] No hardcoded pricing, trial durations, or discount percentages
- [ ] All three locales (EN/RU/ES) contain the same claim set
- [ ] Reviewer notes cover every `MENTION_WITH_REVIEWER_NOTE` block included
- [ ] `PrivacyInfo.xcprivacy` and `app_privacy_details.json` cover data flows for included blocks
- [ ] `[BLOCK:...]` markers are removed from final text
- [ ] Version number is filled in
- [ ] Total text is under 4000 characters per locale
- [ ] `pre-commit run --all-files` passes after text update
