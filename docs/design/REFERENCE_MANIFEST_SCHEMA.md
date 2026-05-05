<!-- markdownlint-disable MD013 -->
# Reference Manifest Schema

**Status:** PR-0 design intelligence contract
**Purpose:** Define the external UI/UX reference intake schema for future PulsePlate design briefs.

## Summary

External references are read-only benchmark inputs. They do not become PulsePlate source of truth, product truth, token truth, runtime UI, Figma truth, Storybook truth, or App Store truth.

Every future reference record must normalize external observations into PulsePlate vocabulary before it can influence a design brief.

## Hard Rule

No external screenshot, asset, brand, direct layout copy, proprietary component implementation, visual identity, or unverified copy becomes repo truth.

References may contribute only derived, normalized metadata and an explicit `adopt`, `adapt`, or `reject` decision.

## Status Values

`status` must be one of:

- `read_only`: source is registered for inspection only.
- `normalized`: source has normalized metadata and no direct-copy elements.
- `rejected`: source is blocked by fit, safety, license, copy, accessibility, legal, or implementation risk.
- `candidate_for_brief`: source may inform a future brief after scorecard approval and repo promotion.

## Scorecard Decision Mapping

`adopt_adapt_reject_decision` and `status` must stay aligned:

| Scorecard decision | Allowed `status` values | Rule |
| --- | --- | --- |
| not scored / incomplete evidence | `read_only` | No brief influence until evidence is complete |
| `reject` | `rejected` | Blocked references cannot be `candidate_for_brief` |
| `adapt` | `normalized`, `candidate_for_brief` | `candidate_for_brief` requires resolved license/copy risk, forbidden-copy elements, normalization notes, and mapped PulsePlate components |
| `adopt` | `normalized`, `candidate_for_brief` | `candidate_for_brief` requires existing PulsePlate token/component fit and no unresolved hard-risk axis |

`status=candidate_for_brief` is never allowed with `adopt_adapt_reject_decision=reject`, incomplete evidence, or unresolved license/copy risk.

## Required Fields

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `reference_id` | string | yes | Stable repo-local id, for example `refero-dashboard-density-001` |
| `source_name` | string | yes | Human source label |
| `source_url` | string | yes | Public or internal source URL, with access notes if needed |
| `license_status` | string | yes | `permissive`, `restricted`, `unknown`, `internal_only`, or `not_applicable` |
| `attribution_required` | boolean | yes | Whether attribution is required for any derived discussion |
| `product_category` | string | yes | Product category such as wellness, SaaS, ecommerce, coaching, analytics |
| `platform` | array | yes | `web`, `ios`, `android`, `desktop`, `cross_platform`, or `unknown` |
| `surface_type` | array | yes | Surface family such as landing, dashboard, onboarding, paywall, settings |
| `visual_archetype` | string | yes | Normalized visual pattern, not vendor wording |
| `palette_archetype` | string | yes | Derived palette family, not copied hex set |
| `typography_archetype` | string | yes | Derived type hierarchy pattern |
| `spacing_density` | string | yes | `compact`, `balanced`, `comfortable`, `editorial`, or `unknown` |
| `radius_profile` | string | yes | `sharp`, `subtle`, `medium`, `soft`, `pill`, `mixed`, or `unknown` |
| `component_patterns` | array | yes | Normalized component patterns observed |
| `layout_patterns` | array | yes | Normalized layout patterns observed |
| `motion_notes` | string | yes | Motion pattern and reduced-motion risk notes |
| `accessibility_notes` | string | yes | Contrast, focus, keyboard, touch target, readability notes |
| `wellness_safety_notes` | string | yes | Wellness-only tone and claim-safety notes |
| `monetization_notes` | string | yes | Conversion/paywall/pricing signal notes without copying claims |
| `legal_copy_risks` | array | yes | Unsupported claims, testimonial risk, ranking risk, brand/copyright concerns |
| `adopt_adapt_reject_decision` | string | yes | `adopt`, `adapt`, or `reject` |
| `normalization_notes` | string | yes | How external terms were mapped into PulsePlate vocabulary |
| `mapped_pulseplate_components` | array | yes | Canonical component ids/names from `UI_COMPONENT_VOCABULARY` |
| `forbidden_copy_elements` | array | yes | Assets/layouts/copy/brand elements that must not be copied |
| `icon-silhouette-check` | string | yes | Verification status required before finalizing Results/Evidence artifacts; use `required`, `passed`, `not_applicable`, or `blocked` |
| `design-guard` | string | yes | Export-gate status required before design exports or icon-core lock updates; use `required`, `passed`, `not_applicable`, or `blocked` |
| `status` | string | yes | `read_only`, `normalized`, `rejected`, or `candidate_for_brief` |

## Example Shape

```json
{
  "reference_id": "refero-dashboard-density-001",
  "source_name": "Refero Styles",
  "source_url": "https://example.invalid/reference",
  "license_status": "unknown",
  "attribution_required": false,
  "product_category": "wellness",
  "platform": ["web", "ios"],
  "surface_type": ["dashboard", "onboarding"],
  "visual_archetype": "calm-premium-dashboard",
  "palette_archetype": "dark-navy-with-controlled-accent",
  "typography_archetype": "clear-hierarchy-with-compact-labels",
  "spacing_density": "balanced",
  "radius_profile": "medium",
  "component_patterns": ["card", "badge", "segmented-control"],
  "layout_patterns": ["stacked-dashboard", "summary-plus-detail"],
  "motion_notes": "Subtle transitions only; reduced-motion fallback required.",
  "accessibility_notes": "Check contrast, focus states, touch targets, and non-color state signals.",
  "wellness_safety_notes": "Avoid diagnostic, treatment, or crisis-support claims.",
  "monetization_notes": "May inform value framing; pricing truth remains repo/backend/store-owned.",
  "legal_copy_risks": ["unsupported testimonial copy", "brand-specific wording"],
  "adopt_adapt_reject_decision": "adapt",
  "normalization_notes": "External 'pill filter' maps to PulsePlate segmented-control.",
  "mapped_pulseplate_components": ["card", "badge", "segmented-control"],
  "forbidden_copy_elements": ["screenshot", "brand name", "exact layout", "testimonial copy"],
  "icon-silhouette-check": "required",
  "design-guard": "required",
  "status": "normalized"
}
```

## Validation Rules

- `source_url` must never be used as implementation authority.
- `license_status=unknown` cannot pair with `status=candidate_for_brief`; keep the reference `read_only` or `normalized` until license/copy risk is resolved.
- `status=candidate_for_brief` requires scorecard decision `adopt` or `adapt`; it is forbidden when the decision is `reject`.
- `adopt` is allowed only for abstract patterns already compatible with PulsePlate tokens/components.
- `adapt` is the default for useful references with any legal, brand, copy, layout, or platform risk.
- When a reference requires copying protected assets, brand identity, exact layout, proprietary components, unsupported medical claims, or unverified monetization copy, `reject` is mandatory.
- Every `component_patterns` entry must map to PulsePlate vocabulary before implementation.
- Every future implementation brief must cite the manifest record and scorecard decision.
- `icon-silhouette-check` must be `passed` or `not_applicable` before any Results/Evidence finalization.
- `design-guard` must be `passed` or `not_applicable` before any design export or icon-core lock update.

## Source Policy Encoding

- Refero Styles: read-only benchmark corpus; no copying.
- `nexu-io/open-design`: read-only open design corpus / ingestion reference; derived metadata only.
- VibeUI: inspiration / market-scan only; no direct dependency.
- Stitch / DESIGN.md examples: contract-shape inspiration only; PulsePlate DESIGN.md must be generated or drift-checked from repo truth.
- GEPA / Nous-style evolution: future prompt/rubric optimization only; no production UI, token, or runtime mutation.
