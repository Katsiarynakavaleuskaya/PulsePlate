# Figma Rebuild Runtime Vocabulary Decision

## Purpose

This document freezes the repo-side semantic decision for current Figma rebuild
families. Figma remains a governed secondary lane. Repo vocabulary and runtime
contracts remain the source of truth.

## Hard Rule

- A Figma rebuild family is not a canonical primitive unless it has exact repo
  vocabulary support or an explicit reviewed promotion.
- Adjacent semantics do not equal canonical mapping.
- Off-canon-risk module families must not be promoted further in Figma until
  repo-side vocabulary/governance catches up.

## Decision Table

| Family | Status | Proposed mapping | Reason | Action |
| --- | --- | --- | --- | --- |
| `PP/Shared/InsightCallout/Runtime` | `specialized_existing_candidate` | `alert` | Adjacent to alert semantics, not an exact repo primitive | keep as Figma helper only |
| `PP/Shared/ResultPanel/Runtime` | `specialized_existing_candidate` | `card` | Result surface is card-adjacent, not a canonical card family | keep as Figma helper only |
| `PP/Shared/ProfileSummary/Runtime` | `specialized_existing_candidate` | `card` | Summary shell is card-adjacent, but repo vocabulary does not define this family | keep as Figma helper only |
| `PP/Shared/CoverageBadgeRow/Runtime` | `specialized_existing_candidate` | `badge` | Badge row is adjacent to badge usage, but row semantics are not canonical | keep as Figma helper only |
| `PP/Shared/StatTile/Runtime` | `specialized_existing_candidate` | `stats-card` | Metric tile is adjacent to stats-card, not an exact canonical match | keep as Figma helper only |
| `PP/Shared/SectionHeader/Runtime` | `governed_gap_missing` | `none` | Internal section helper with no exact vocabulary entry | governed gap, no primitive promotion |
| `PP/Shared/EmptyState/Runtime` | `maps_to_existing_vocabulary` | `empty-state` | Exact match to canonical empty-state vocabulary | safe mapping |
| `PP/Shared/MetaRow/Runtime` | `governed_gap_missing` | `none` | Internal metadata row helper with no canonical vocabulary support | governed gap, no primitive promotion |
| `PP/Shared/StatTileGroup/Runtime` | `specialized_existing_candidate` | `stats-card` | Metric grouping is adjacent to stats-card, but group semantics are not canonical | keep as Figma helper only |
| `PP/Shared/DetailGroup/Runtime` | `governed_gap_missing` | `none` | Detail grouping helper has no exact repo vocabulary entry | governed gap, no primitive promotion |
| `PP/Shared/SupportRow/Runtime` | `governed_gap_missing` | `none` | Support row remains an internal helper, not a governed primitive | governed gap, no primitive promotion |
| `PP/Shared/SectionBlock/Runtime` | `governed_gap_missing` | `none` | Section block is a layout helper with no safe canonical mapping | governed gap, no primitive promotion |
| `PP/Shared/SummaryPanel/Runtime` | `off_canon_risk_stop_promotion` | `none` | Behaves like a new semantic summary family; stop promotion until repo mapping exists | stop promotion |
| `PP/Shared/ActionCluster/Runtime` | `off_canon_risk_stop_promotion` | `none` | Behaves like a grouped action family beyond current vocabulary; stop promotion | stop promotion |
| `PP/Shared/OptionGroup/Runtime` | `off_canon_risk_stop_promotion` | `none` | Acts like a new choice family in Figma; stop promotion until repo decision exists | stop promotion |
| `PP/Shared/ReviewBlock/Runtime` | `off_canon_risk_stop_promotion` | `none` | Acts like a new review surface family; stop promotion until vocabulary catches up | stop promotion |

## Immediate Governance Decision

- Exact-safe mapping today: EmptyState only.
- Specialized-but-not-canonical families remain Figma helper families.
- Governed-gap families must not be treated as primitives.
- Module families are frozen from further promotion.

## Next Approved Move

The next approved move is not another Figma extraction layer.
The next approved move is a repo-side primitive decision for any family that
needs promotion beyond helper status.

## Specialized family follow-through

- This follow-through reviews specialized families only.
- It does not reopen governed-gap or stop-promotion module families.
- Canonical primitive status still requires a separate explicit promotion decision.
