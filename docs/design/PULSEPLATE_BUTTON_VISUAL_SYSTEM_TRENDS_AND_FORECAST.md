<!-- markdownlint-disable MD013 MD034 -->
# PulsePlate Button Visual System + 5-Year Trend Intelligence (H+P+Pr)

**Date:** February 18, 2026
**Scope:** Home + Plate + Progress (`H+P+Pr`) for Web + iOS, including linked downstream CTA flows (setup/paywall/retry/edit)
**Language mode:** EN primary, RU notes for critical constraints

## 1) Purpose + SoT Links

This document is the visual-system companion to the CTA behavior matrix.

Primary SoT links:

- `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`
- `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md`
- `docs/design/LUXURY_UI_REVIEW_CHECKLIST.md`
- `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md`
- `docs/sora/PULSEPLATE_SORA_BUTTON_VARIANTS_HPP.md`
- `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md`
- `docs/figma/PULSEPLATE_FIGMA_AI_GOVERNANCE_INDEX.md`

RU (critical): если возникает конфликт по поведению кнопки, первичен `PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`.

## 2) External Source Registry (Primary Sources, Dated)

Verification date for registry below: **February 18, 2026**.

| Priority | Source | Date signal | Evidence focus for this doc |
| --- | --- | --- | --- |
| P0 | Apple WWDC25 Design session 281: https://developer.apple.com/videos/play/wwdc2025/281/ | WWDC25 session page | Glanceable interaction model, clear action verbs, low-friction confirmations for interactive UI snippets with buttons |
| P0 | Apple Design portal: https://developer.apple.com/design/ | Apple design page shows “Liquid Glass”, “new design”, and “Icon Composer” entries (live page snapshot) | Current Apple direction toward expressive surfaces with clarity-first behavior |
| P0 | Apple App Icons docs index: https://developer.apple.com/design/human-interface-guidelines/app-icons | HIG app icon docs index (live) | App icon/emblem governance source for iOS-facing branding |
| P0 | Google Play icon spec: https://developer.android.com/distribute/google-play/resources/icon-design-specifications | Page “Last updated 2026-01-07 UTC” | Store icon rendering constraints: 30% corner radius, shadow handling, keyline adaptation |
| P0 | Google Material 3 Expressive launch: https://blog.google/products/android/material-3-expressive-android-wearos-launch/ | Published May 13, 2025 | Expressive motion/personalization trend with usability framing |
| P0 | AOSP Material You design: https://source.android.com/docs/core/display/material | “Starting in Android 12” + Dynamic color guidance | Multi-year personalization trend and dynamic color ecosystem baseline |
| P0 | WCAG 2.2 Recommendation: https://www.w3.org/TR/WCAG22/ | W3C Recommendation | Accessibility baseline authority |
| P0 | W3C WCAG 2.2 announcement: https://www.w3.org/news/2023/web-content-accessibility-guidelines-wcag-2-2-is-a-w3c-recommendation/ | Published October 5, 2023 | Concrete publication date for accessibility milestone |
| P0 | web.dev touch targets: https://web.dev/articles/accessible-tap-targets | web.dev guidance | Practical mobile target sizing (48x48 CSS px recommendation) |

## 3) 5-Year Visual Evolution (2021-2026)

Facts and inferences are intentionally separated.

| Year | Factual signals | Inference for PulsePlate CTA/Button design |
| --- | --- | --- |
| 2021 | Material You (AOSP) emphasizes personalization + dynamic color (Android 12 baseline) | Users became more comfortable with adaptive yet consistent color systems; CTA systems should be token-led, not hard-coded |
| 2022 | Continued platform-level expansion of dynamic themes and personalization components across Android ecosystem | Personalization is expected, but trust requires consistent semantic roles (primary/success/error) |
| 2023 | WCAG 2.2 became W3C Recommendation on October 5, 2023 | Accessibility moved from “nice-to-have” to “expected quality floor” for target size, clarity, and robust state distinction |
| 2024 | Transitional year in this source set between WCAG 2.2 baseline (2023) and explicit expressive platform pushes (2025) | Keep CTA hierarchy strict and accessible-first while preparing for moderate visual expressiveness |
| 2025 | Apple design portal highlights “new design”, “Liquid Glass”, and “Icon Composer”; Google launches Material 3 Expressive (May 13, 2025) | Expressive visuals are accepted only when paired with clear, predictable interaction and strong readability |
| 2026 | Google Play icon spec explicitly sets dynamic corner radius to 30% and keeps shadow handling dynamic (updated Jan 7, 2026) | Brand emblems/icons must be resilient to platform masking and small-size rendering; avoid edge-dependent icon detail |

## 4) Forecast (2026-2028, Inference)

This block is forecast, not platform policy.

### 4.1 Expected direction

- Expressive surface language will continue, but interaction clarity will be an even stronger differentiator.
- Users will expect stronger small-size icon semantics and less ambiguity in CTA intent.
- State communication (loading/error/recovery/locked) will be expected as first-class design, not fallback.
- Comfort-first UX will outperform high-drama “growth hacks” in wellness contexts.

### 4.2 Risk controls to keep forecast usable

- Preserve anti-copycat constraints in all visual/prompt outputs.
- Preserve anti-neon and anti-generic-AI constraints.
- Preserve wellness-not-medical framing.
- Preserve token parity between Web and iOS.

## 5) Audience Expectation Model

Primary audience lock: **mainstream wellness adults (22-45)**.

Expected emotional outcomes for CTA design:

- Confidence: primary actions feel dependable and obvious.
- Progress clarity: supportive secondary actions are clearly discoverable.
- Low anxiety recovery: error/loading states guide users without blame/fear.

RU (critical): в ошибках и блокировках избегаем стыда/давления; тон спокойный и поддерживающий.

## 6) Button Visual System Definition

### 6.1 Variant families (fixed)

| Variant | Name | Use band | Visual signature | Constraints |
| --- | --- | --- | --- | --- |
| V1 | Calm Solid | Default recommended for primary actions | Solid semantic fill, high label contrast, subtle shadow edge | Must stay token-driven and pass WCAG AA |
| V2 | Soft Glass | Premium/emphasis contexts only | Layered surface with restrained translucency and depth cues | Never reduce legibility or blur CTA label |
| V3 | Precision Outline | Secondary/utility actions | Clean outline + subtle fill-on-interaction | Keep low-importance hierarchy, avoid faux-primary weight |

### 6.2 Mandatory state set

Every CTA component in this scope must define:

- `default`
- `hover/pressed`
- `focus-visible`
- `disabled/locked`
- `loading`
- `error`

### 6.3 Icon/emblem rules

- Small-size readability validated at 24/32 px.
- Uniform stroke/radius grammar across one screen context.
- No ambiguous medical symbols in wellness-only contexts.
- Keep icon silhouette recognizable after platform masking/cropping.

### 6.4 Accessibility minima

- Web tap/click target minimum for this project: **48x48 CSS px**.
- iOS tap target minimum for this project: **44x44 pt**.
- WCAG AA contrast baseline is mandatory.

## 7) Placement Map (Zone IDs)

### 7.1 Web zones

| Zone ID | Screen area | Notes |
| --- | --- | --- |
| `W_HOME_QA_GRID` | Home quick actions grid | 2-column card rhythm, primary intent above fold |
| `W_PLATE_GATE_ACTIONS` | Plate premium gate action strip | Locked-state hierarchy: informative secondary + unlock primary |
| `W_PROGRESS_HEADER_UTIL` | Progress header utility zone | Utility actions on right side, never compete with chart focus |
| `W_PAYWALL_MODAL_FOOTER` | Paywall modal footer | Primary purchase CTA + safe cancel secondary |
| `W_SETUP_FORM_FOOTER` | Setup form footer | Single dominant submit action |
| `W_SETUP_RESULT_ACTIONS` | Setup result recovery strip | Retry + edit actions with calm recovery semantics |

### 7.2 iOS zones

| Zone ID | Screen area | Notes |
| --- | --- | --- |
| `I_HOME_QUICK_ACTIONS` | Home quick-action stack | Touch-first row cards, high scanability |
| `I_HOME_PRO_TOOLS` | Home pro-tools block | Flag-aware affordance states and progressive disclosure |
| `I_PLATE_BOTTOMBAR_PRIMARY` | Plate bottom action bar | Primary nutritional actions, thumb-reachable |
| `I_PLATE_ISSUE_RECOVERY` | Plate issue block | Dynamic recovery CTA based on issue classifier |
| `I_PROGRESS_EMPTY_RECOVERY` | Progress empty-state action block | Refresh action with clear loading feedback |
| `I_PROGRESS_ISSUE_RECOVERY` | Progress issue action block | Retry/profile/pro-setup fallback actions |

### 7.3 Linked downstream zones

- `W_PAYWALL_MODAL_FOOTER`
- `W_SETUP_FORM_FOOTER`
- `W_SETUP_RESULT_ACTIONS`

## 8) Per-Button Visual Table (All H+P+Pr CTA IDs)

State set for all rows: `default, hover/pressed, focus-visible, disabled/locked, loading, error`.

| Platform | Screen | Button/CTA ID | Placement Zone | UX Intent | Variant A (V1) | Variant B (V2) | Variant C (V3) | Recommended Variant | State Set | Icon Rule | Sora Prompt IDs | Design Review Reference/TBD | Implement Note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Web | Home | `web.home.open_setup` | `W_HOME_QA_GRID` | Start setup flow fast | Solid primary CTA with calm trust contrast | Soft-glass elevated tile CTA | Precision outline quick-action CTA | V1 | All mandatory states | Setup/support icon, no medical glyph | `SORA_BTN_web_home_open_setup_V1_default_V1` + same contract for V2/V3 and all states | TBD | Keep as primary Home CTA, test parity across desktop/mobile |
| Web | Home | `web.home.open_plate` | `W_HOME_QA_GRID` | Navigate to Plate (auth-aware) | Solid secondary-primary bridge CTA | Soft-glass gated CTA with subtle lock affordance | Precision outline navigation CTA | V3 | All mandatory states | Plate icon must stay readable at 24 px | `SORA_BTN_web_home_open_plate_V3_default_V1` + full state contract | TBD | Add clearer locked/redirect visual affordance |
| Web | Home | `web.home.open_progress` | `W_HOME_QA_GRID` | Navigate to Progress (auth-aware) | Solid progress action CTA | Soft-glass progress card CTA | Precision outline progress nav CTA | V3 | All mandatory states | Progress/chart icon, minimalist stroke | `SORA_BTN_web_home_open_progress_V3_default_V1` + full state contract | TBD | Align guard hint style with `open_plate` |
| Web | Home | `web.home.open_pro` | `W_HOME_QA_GRID` | Enter Pro/Premium context | Solid premium CTA with controlled emphasis | Soft-glass premium highlight CTA | Precision outline premium teaser CTA | V2 | All mandatory states | Pro gem/star abstraction without copycat motifs | `SORA_BTN_web_home_open_pro_V2_default_V1` + full state contract | TBD | Keep “coming soon” tone without fake urgency |
| Web | Plate | `web.plate.open_setup` | `W_PLATE_GATE_ACTIONS` | Open setup from plate context | Solid primary recovery CTA | Soft-glass premium-context CTA | Precision outline fallback CTA | V1 | All mandatory states | Setup icon + calm orientation cue | `SORA_BTN_web_plate_open_setup_V1_default_V1` + full state contract | TBD | Improve non-premium explanatory state |
| Web | Plate | `web.plate.open_progress` | `W_PLATE_GATE_ACTIONS` | Move from plate to progress | Solid action CTA | Soft-glass transition CTA | Precision outline context-switch CTA | V3 | All mandatory states | Progress icon with consistent stroke grammar | `SORA_BTN_web_plate_open_progress_V3_default_V1` + full state contract | TBD | Add premium/non-premium state visual parity |
| Web | Plate | `web.plate.premium_gate_cta` | `W_PLATE_GATE_ACTIONS` | Open premium modal | Solid unlock CTA | Soft-glass premium unlock CTA | Precision outline unlock CTA | V2 | All mandatory states | Unlock icon must avoid aggressive urgency styling | `SORA_BTN_web_plate_premium_gate_cta_V2_default_V1` + full state contract | TBD | Purchase flow still callback-only, keep states explicit |
| Web | Progress | `web.progress.export_pdf` | `W_PROGRESS_HEADER_UTIL` | Export report file | Solid utility-primary CTA | Soft-glass utility CTA | Precision outline utility CTA | V3 | All mandatory states | Export/download icon with 24 px clarity | `SORA_BTN_web_progress_export_pdf_V3_default_V1` + full state contract | TBD | Add deterministic error-state visual branch |
| iOS | Home | `ios.home.bmi_calculator` | `I_HOME_QUICK_ACTIONS` | Start BMI flow | Solid row CTA with high tap confidence | Soft-glass row CTA | Precision outline row CTA | V1 | All mandatory states | BMI icon must avoid clinical cross symbols | `SORA_BTN_ios_home_bmi_calculator_V1_default_V1` + full state contract | TBD | Keep fast discoverability in top rows |
| iOS | Home | `ios.home.profile_setup` | `I_HOME_QUICK_ACTIONS` | Open profile setup | Solid profile CTA | Soft-glass profile CTA | Precision outline profile CTA | V1 | All mandatory states | Profile icon with simple human silhouette | `SORA_BTN_ios_home_profile_setup_V1_default_V1` + full state contract | TBD | Needs nav outcome tests |
| iOS | Home | `ios.home.open_plate` | `I_HOME_QUICK_ACTIONS` | Open Plate screen | Solid plate CTA | Soft-glass plate CTA | Precision outline plate CTA | V1 | All mandatory states | Plate icon must stay consistent with Web family | `SORA_BTN_ios_home_open_plate_V1_default_V1` + full state contract | TBD | Keep parity with web plate affordance |
| iOS | Home | `ios.home.weekly_plan_reader` | `I_HOME_PRO_TOOLS` | Open weekly plan reader (flagged) | Solid flagged CTA with lock-aware tone | Soft-glass premium tool CTA | Precision outline flagged CTA | V3 | All mandatory states | Planner icon with low-detail clarity | `SORA_BTN_ios_home_weekly_plan_reader_V3_default_V1` + full state contract | TBD | Feature-flagged; keep blocked state explicit |
| iOS | Home | `ios.home.shopping_list_generator` | `I_HOME_PRO_TOOLS` | Open shopping list generator (flagged) | Solid flagged CTA | Soft-glass premium tool CTA | Precision outline flagged CTA | V3 | All mandatory states | Cart/list icon, no clutter | `SORA_BTN_ios_home_shopping_list_generator_V3_default_V1` + full state contract | TBD | Backend path partially pending; keep expectation clear |
| iOS | Plate | `ios.plate.add_meal` | `I_PLATE_BOTTOMBAR_PRIMARY` | Primary meal add action | Solid primary thumb-zone CTA | Soft-glass primary CTA | Precision outline secondary fallback | V1 | All mandatory states | Add icon must remain readable at compact sizes | `SORA_BTN_ios_plate_add_meal_V1_default_V1` + full state contract | TBD | Runtime destination placeholder (partial) |
| iOS | Plate | `ios.plate.view_details` | `I_PLATE_BOTTOMBAR_PRIMARY` | Open detail drilldown | Solid secondary-primary CTA | Soft-glass detail CTA | Precision outline details CTA | V3 | All mandatory states | Details icon must avoid data-clutter look | `SORA_BTN_ios_plate_view_details_V3_default_V1` + full state contract | TBD | Runtime destination placeholder (partial) |
| iOS | Plate | `ios.plate.issue_action_dynamic` | `I_PLATE_ISSUE_RECOVERY` | Dynamic issue recovery action | Solid recovery CTA | Soft-glass recovery CTA | Precision outline recovery CTA | V1 | All mandatory states | Dynamic icon set: retry/profile/pro with shared stroke grammar | `SORA_BTN_ios_plate_issue_action_dynamic_V1_default_V1` + full state contract | TBD | Add branch-level visual QA per issue type |
| iOS | Progress | `ios.progress.refresh` | `I_PROGRESS_EMPTY_RECOVERY` | Refresh data in empty state | Solid recovery CTA | Soft-glass recovery CTA | Precision outline utility refresh CTA | V1 | All mandatory states | Refresh icon with motion-safe loading pair | `SORA_BTN_ios_progress_refresh_V1_default_V1` + full state contract | TBD | Add no-data->loading->success visual test parity |
| iOS | Progress | `ios.progress.issue_action_dynamic` | `I_PROGRESS_ISSUE_RECOVERY` | Dynamic issue recovery action | Solid recovery CTA | Soft-glass recovery CTA | Precision outline recovery CTA | V1 | All mandatory states | Dynamic issue icons aligned with Plate issue family | `SORA_BTN_ios_progress_issue_action_dynamic_V1_default_V1` + full state contract | TBD | Branch mapping visual checks needed |
| Web (linked flow) | Paywall Modal | `web.paywall.modal.cta` | `W_PAYWALL_MODAL_FOOTER` | Confirm premium purchase path | Solid purchase CTA with trust tone | Soft-glass premium purchase CTA | Precision outline purchase CTA | V2 | All mandatory states | Purchase icon optional; never use fear cues | `SORA_BTN_web_paywall_modal_cta_V2_default_V1` + full state contract | TBD | Runtime purchase hook still partial |
| Web (linked flow) | Paywall Modal | `web.paywall.modal.cancel` | `W_PAYWALL_MODAL_FOOTER` | Safe modal dismiss action | Solid cancel CTA | Soft-glass cancel CTA | Precision outline cancel CTA | V3 | All mandatory states | Cancel/close icon should be neutral and clear | `SORA_BTN_web_paywall_modal_cancel_V3_default_V1` + full state contract | TBD | Keep cancel always visible and calm |
| Web (linked flow) | Nutrition Setup Form | `web.setup.submit_calculate` | `W_SETUP_FORM_FOOTER` | Submit setup and calculate plate | Solid dominant submit CTA | Soft-glass dominant submit CTA | Precision outline submit CTA | V1 | All mandatory states | Calculate icon optional, text-first clarity | `SORA_BTN_web_setup_submit_calculate_V1_default_V1` + full state contract | TBD | Preserve single clear primary action |
| Web (linked flow) | Nutrition Setup Result | `web.setup.result.retry` | `W_SETUP_RESULT_ACTIONS` | Retry failed calculation | Solid recovery CTA | Soft-glass recovery CTA | Precision outline retry CTA | V1 | All mandatory states | Retry icon must convey recovery, not failure panic | `SORA_BTN_web_setup_result_retry_V1_default_V1` + full state contract | TBD | Extend error-branch visual QA |
| Web (linked flow) | Nutrition Setup Result | `web.setup.result.edit` | `W_SETUP_RESULT_ACTIONS` | Return to edit input data | Solid edit CTA | Soft-glass edit CTA | Precision outline edit CTA | V3 | All mandatory states | Edit/pencil icon simple and readable | `SORA_BTN_web_setup_result_edit_V3_default_V1` + full state contract | TBD | Unify visual behavior for both edit entry points |

## 9) Execution Queue (Visual System Rollout)

| Priority | Item | Why | Owner lane | Target PR |
| --- | --- | --- | --- | --- |
| P0 | Resolve partial runtime couplings for `ios.plate.add_meal`, `ios.plate.view_details`, `web.paywall.modal.cta` | Visual states must map to real outcomes | FE + iOS + Coordinator | Next runtime parity PR |
| P0 | Add deterministic CTA-state QA for dynamic issue actions (Plate/Progress iOS) | Dynamic labels need state-consistent visuals | iOS + QA | Same PR wave as runtime couplings |
| P1 | Roll out V1/V2/V3 harmonization across all 23 CTA IDs in Figma component sets | Prevent drift between screens/platforms | Creative + Sora + Figma coordinator | Figma component sync PR |
| P1 | Materialize row-level Sora prompt outputs from prompt IDs in this document | Ensure deterministic prompt handoff | Sora prompt engineer | Prompt ops PR |
| P2 | Backfill all `Design Review Reference` cells after component freeze | Complete tool-neutral design-to-code traceability | Design + FE + iOS | Design traceability PR |
| P2 | Capture screenshot parity snapshots per CTA state family | Improve review reproducibility | QA + Coordinator | Visual QA hardening PR |

## 10) Security + Safety Notes

- Never include secrets, internal URLs, credentials, or private system data in prompt payloads.
- Keep language wellness-safe and non-diagnostic.
- Keep anti-copycat and anti-drift constraints active for every visual variant.

## 11) Marketing & GTM Notes

- This table is a CTA-level creative registry for ASO screenshot planning and social creatives.
- Recommended variant per CTA reduces brand drift across product and campaign materials.
- Recovery-state design quality directly supports trust and retention in wellness journeys.

## 12) Decision Log

- 2026-02-18: Locked variant set to `V1 Calm Solid`, `V2 Soft Glass`, `V3 Precision Outline`.
- 2026-02-18: Locked mandatory state set for all CTA IDs.
- 2026-02-18: Locked target audience model to mainstream wellness adults (22-45).
- 2026-02-18: Locked forecast horizon to 2026-2028 and marked as inference.
<!-- markdownlint-enable MD013 -->
