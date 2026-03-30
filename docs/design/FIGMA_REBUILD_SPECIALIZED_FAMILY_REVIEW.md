# Figma Rebuild Specialized Family Review

## Purpose

This review applies only to `specialized_existing_candidate` families and does
not promote new primitives.

## Decision Table

| Family | Current adjacent mapping | Decision | Reason | Immediate action |
| --- | --- | --- | --- | --- |
| `PP/Shared/InsightCallout/Runtime` | `alert` | `merge_into_existing_canonical_concept` | Existing prompt/doc language can safely normalize this helper to the canonical `alert` concept without creating a new primitive | use `alert` wording in docs and prompts; keep helper out of canonical vocabulary |
| `PP/Shared/ResultPanel/Runtime` | `card` | `keep_helper_only` | Result-specific shell remains only card-adjacent and is not stable enough to absorb into canonical card semantics | keep helper-only naming out of vocabulary and primitive docs |
| `PP/Shared/ProfileSummary/Runtime` | `card` | `keep_helper_only` | Summary shell is card-adjacent, but current repo vocabulary does not justify a distinct summary primitive or safe absorption into `card` | keep helper-only naming out of vocabulary and primitive docs |
| `PP/Shared/CoverageBadgeRow/Runtime` | `badge` | `keep_helper_only` | Badge-row composition is layout/helper behavior, not a safe canonical badge primitive | keep helper-only naming out of vocabulary and primitive docs |
| `PP/Shared/StatTile/Runtime` | `stats-card` | `merge_into_existing_canonical_concept` | Metric tile semantics can be described safely with the existing canonical `stats-card` concept in docs and prompts | use `stats-card` wording in docs and prompts; keep helper out of canonical vocabulary |
| `PP/Shared/StatTileGroup/Runtime` | `stats-card` | `future_rfc_needed` | Grouped metric treatment appears repeatedly valuable, but current vocabulary does not safely cover group-level semantics | track as RFC candidate; no primitive promotion now |

## Recommendation Summary

- Stay helper-only now: `ResultPanel`, `ProfileSummary`, and
  `CoverageBadgeRow`.
- Use existing canonical concepts in docs/prompts where safe:
  `InsightCallout` -> `alert`, `StatTile` -> `stats-card`.
- Future RFC needed before any primitive promotion: `StatTileGroup`.
