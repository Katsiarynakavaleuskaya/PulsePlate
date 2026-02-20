<!-- markdownlint-disable MD013 -->
# PulsePlate Sora Button Variants Pack (H+P+Pr)

**Date:** February 18, 2026
**Scope:** Home + Plate + Progress CTA visuals (Web + iOS) + linked downstream CTA flows
**Related visual SoT:** `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md`

## 1) Purpose

This pack defines deterministic prompt contracts for CTA/button/icon generation.

Use with:

- `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`
- `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md`
- `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md`
- `docs/design/LUXURY_UI_REVIEW_CHECKLIST.md`
- `docs/figma/PULSEPLATE_FIGMA_AI_GOVERNANCE_INDEX.md`

## 2) Prompt ID Contract

Canonical format:

`SORA_BTN_<platform>_<screen>_<cta_id>_<variant>_<state>_V1`

Normalization rules:

- `platform`: `web` or `ios`
- `screen`: `home`, `plate`, `progress`, `paywall`, `setup`
- `cta_id`: short snake case ID (`open_setup`, `premium_gate_cta`, `issue_action_dynamic`, etc.)
- `variant`: `V1` / `V2` / `V3`
- `state`: `default`, `pressed`, `focus`, `disabled`, `loading`, `error`
- contract version suffix: `_V1`

Example:

`SORA_BTN_web_home_open_setup_V1_default_V1`

## 3) Mandatory Guard Clause Block (attach to every prompt)

Use this exact guard clause block for every generated prompt body:

```text
PulsePlate guard clauses:
- palette locked (#0F172A #339FFF #20C997, #FF5D5D accent-only)
- wellness not medical
- no diagnostic/cure framing
- no copycat brand imitation
- no neon/acid drift
- small-size readability priority (24/32 px icon context)
- no manipulative fear/shame tone
```

## 4) Output Contract

Every prompt request and output record must include:

- `prompt_id`
- `Button/CTA ID`
- `platform`
- `screen`
- `variant`
- `state`
- `asset_intent` (`button`, `icon`, `button+icon`)
- `expected_style_signature`
- `negative_prompt_fallback`

## 5) Prompt Templates by Family

### 5.1 Primary CTA Template

```text
Template ID: SORA_TEMPLATE_CTA_PRIMARY_V1
Target: <platform>/<screen>/<cta_id>
Goal: Produce a primary CTA asset with calm, trust-first hierarchy.
Variant: <V1|V2|V3>
State: <default|pressed|focus|disabled|loading|error>
Style: luxury-clean wellness UI, flat forms, soft depth, clear label legibility.
Guards: [insert mandatory guard clause block]
Output: one CTA render concept with state-appropriate affordance and accessible contrast.
Negative fallback: remove decorative clutter, increase label contrast, simplify silhouette.
```

### 5.2 Secondary CTA Template

```text
Template ID: SORA_TEMPLATE_CTA_SECONDARY_V1
Target: <platform>/<screen>/<cta_id>
Goal: Supportive CTA with lower visual weight than primary while preserving clarity.
Variant: <V1|V2|V3>
State: <default|pressed|focus|disabled|loading|error>
Style: same family as primary, controlled emphasis and spacing.
Guards: [insert mandatory guard clause block]
Output: balanced secondary CTA state with non-ambiguous action tone.
Negative fallback: reduce noise and prevent faux-primary styling.
```

### 5.3 Utility CTA Template

```text
Template ID: SORA_TEMPLATE_CTA_UTILITY_V1
Target: <platform>/<screen>/<cta_id>
Goal: Utility action (export, cancel, edit) with precise low-cognitive-load styling.
Variant: <V1|V2|V3>
State: <default|pressed|focus|disabled|loading|error>
Style: precision outline or restrained solid style, text-first legibility.
Guards: [insert mandatory guard clause block]
Output: utility CTA style with strong scanability in dense layouts.
Negative fallback: remove dramatic styling and preserve neutral utility tone.
```

### 5.4 Disabled/Locked Template

```text
Template ID: SORA_TEMPLATE_CTA_DISABLED_LOCKED_V1
Target: <platform>/<screen>/<cta_id>
Goal: Non-interactive or gated state with respectful, clear affordance.
Variant: <V1|V2|V3>
State: disabled
Style: muted but readable, no hidden controls, optional lock cue.
Guards: [insert mandatory guard clause block]
Output: disabled/locked CTA state preserving readability and dignity.
Negative fallback: avoid low-contrast gray collapse and avoid error-red misuse.
```

### 5.5 Loading Template

```text
Template ID: SORA_TEMPLATE_CTA_LOADING_V1
Target: <platform>/<screen>/<cta_id>
Goal: In-progress CTA state with calm motion and no anxiety cues.
Variant: <V1|V2|V3>
State: loading
Style: subtle motion-safe indicator, legible label.
Guards: [insert mandatory guard clause block]
Output: loading CTA state (spinner/progress hint) with reduced-motion compatibility.
Negative fallback: remove flashing/jitter and simplify moving elements.
```

### 5.6 Error-Recovery Template

```text
Template ID: SORA_TEMPLATE_CTA_ERROR_RECOVERY_V1
Target: <platform>/<screen>/<cta_id>
Goal: Recovery CTA pair/state (retry/edit/help) with calm guidance.
Variant: <V1|V2|V3>
State: error
Style: clear hierarchy for primary recovery + optional secondary fallback.
Guards: [insert mandatory guard clause block]
Output: error CTA state with confident recovery affordance and readable context.
Negative fallback: remove blame/fear language and reduce visual aggression.
```

### 5.7 Icon/Emblem Template

```text
Template ID: SORA_TEMPLATE_ICON_EMBLEM_V1
Target: <platform>/<screen>/<cta_id>
Goal: Navigation/support icon for CTA context.
Variant family: aligned with CTA variant selected for the row.
State: default (with derivatives for disabled/loading/error where needed)
Style: clean geometry, consistent stroke/radius grammar, high 24/32 px readability.
Guards: [insert mandatory guard clause block]
Output: icon concept with clear silhouette and token-compatible accent usage.
Negative fallback: remove tiny details and any clinical symbol semantics.
```

## 6) CTA Prompt ID Index (All 23 Rows)

| Button/CTA ID | Recommended Variant | Prompt ID Base |
| --- | --- | --- |
| `web.home.open_setup` | `V1` | `SORA_BTN_web_home_open_setup_<variant>_<state>_V1` |
| `web.home.open_plate` | `V3` | `SORA_BTN_web_home_open_plate_<variant>_<state>_V1` |
| `web.home.open_progress` | `V3` | `SORA_BTN_web_home_open_progress_<variant>_<state>_V1` |
| `web.home.open_pro` | `V2` | `SORA_BTN_web_home_open_pro_<variant>_<state>_V1` |
| `web.plate.open_setup` | `V1` | `SORA_BTN_web_plate_open_setup_<variant>_<state>_V1` |
| `web.plate.open_progress` | `V3` | `SORA_BTN_web_plate_open_progress_<variant>_<state>_V1` |
| `web.plate.premium_gate_cta` | `V2` | `SORA_BTN_web_plate_premium_gate_cta_<variant>_<state>_V1` |
| `web.progress.export_pdf` | `V3` | `SORA_BTN_web_progress_export_pdf_<variant>_<state>_V1` |
| `ios.home.bmi_calculator` | `V1` | `SORA_BTN_ios_home_bmi_calculator_<variant>_<state>_V1` |
| `ios.home.profile_setup` | `V1` | `SORA_BTN_ios_home_profile_setup_<variant>_<state>_V1` |
| `ios.home.open_plate` | `V1` | `SORA_BTN_ios_home_open_plate_<variant>_<state>_V1` |
| `ios.home.weekly_plan_reader` | `V3` | `SORA_BTN_ios_home_weekly_plan_reader_<variant>_<state>_V1` |
| `ios.home.shopping_list_generator` | `V3` | `SORA_BTN_ios_home_shopping_list_generator_<variant>_<state>_V1` |
| `ios.plate.add_meal` | `V1` | `SORA_BTN_ios_plate_add_meal_<variant>_<state>_V1` |
| `ios.plate.view_details` | `V3` | `SORA_BTN_ios_plate_view_details_<variant>_<state>_V1` |
| `ios.plate.issue_action_dynamic` | `V1` | `SORA_BTN_ios_plate_issue_action_dynamic_<variant>_<state>_V1` |
| `ios.progress.refresh` | `V1` | `SORA_BTN_ios_progress_refresh_<variant>_<state>_V1` |
| `ios.progress.issue_action_dynamic` | `V1` | `SORA_BTN_ios_progress_issue_action_dynamic_<variant>_<state>_V1` |
| `web.paywall.modal.cta` | `V2` | `SORA_BTN_web_paywall_modal_cta_<variant>_<state>_V1` |
| `web.paywall.modal.cancel` | `V3` | `SORA_BTN_web_paywall_modal_cancel_<variant>_<state>_V1` |
| `web.setup.submit_calculate` | `V1` | `SORA_BTN_web_setup_submit_calculate_<variant>_<state>_V1` |
| `web.setup.result.retry` | `V1` | `SORA_BTN_web_setup_result_retry_<variant>_<state>_V1` |
| `web.setup.result.edit` | `V3` | `SORA_BTN_web_setup_result_edit_<variant>_<state>_V1` |

## 7) Execution Rules for Sora Prompt Engineer

- Use the recommended variant as default; produce V2/V3 alternates only when explicitly requested.
- Generate state-complete bundles (all six states) for each CTA ID.
- Keep prompt payload free of secrets, internal URLs, and private identifiers.
- Always attach guard clause block and output contract metadata.

## 8) QA Quick Pass

Before accepting generated assets:

- Check variant hierarchy (`V1` primary comfort, `V2` premium emphasis, `V3` secondary precision).
- Validate 24/32 px icon readability.
- Validate WCAG AA contrast baseline in mock usage.
- Validate wellness-safe wording and non-clinical semantics.
- Validate no copycat/neon/generic-AI drift.

## 9) Decision Log

- 2026-02-18: Prompt ID contract locked to `SORA_BTN_<platform>_<screen>_<cta_id>_<variant>_<state>_V1`.
- 2026-02-18: Mandatory guard clause block standardized for all CTA prompt families.
- 2026-02-18: Row-level prompt bases aligned with all 23 CTA IDs in H+P+Pr scope.
<!-- markdownlint-enable MD013 -->
