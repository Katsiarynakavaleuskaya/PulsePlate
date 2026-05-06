<!-- markdownlint-disable MD013 -->
# Design Scorecard Checks

**Status:** Design Intelligence PR-4 contract
**Purpose:** Define deterministic scorecard checks over PulsePlate screen evidence pack metadata.

## Summary

Design scorecards are review evidence only. They do not become PulsePlate source of truth, product truth, design truth, Figma truth, Storybook truth, App Store truth, or implementation authority.

The repo source of truth remains code, docs, tests, `/tokens`, generated token mirrors, UI vocabulary, backend/OpenAPI contracts, and runtime implementation.

## Hard Rule

Scorecards do not judge subjective visual taste. They do not score whether a screen is beautiful, premium, luxurious, modern, market-ready, visually ready, or persuasive.

Scorecards only summarize deterministic metadata quality from PR-3 screen evidence manifests:

- source-of-truth compliance
- artifact hygiene
- component vocabulary integrity
- token evidence
- accessibility evidence presence
- responsive evidence presence
- copy safety
- navigation evidence presence
- overflow evidence presence
- motion evidence presence
- platform metadata

## CLI

```bash
python3 scripts/design/design_scorecard.py score <screen-evidence.json>
python3 scripts/design/design_scorecard.py score-dir <dir>
python3 scripts/design/design_scorecard.py validate-score <scorecard.json>
python3 scripts/design/design_scorecard.py summarize <scorecard.json>
```

`score` validates the input screen evidence manifest with `scripts/design/screen_evidence_pack.py` before scoring. Invalid evidence fails closed and does not emit a scorecard.

`score-dir` scores all JSON evidence manifests in deterministic path order.

`validate-score` checks generated scorecard shape, deterministic ids, dimensions, score bounds, sorted lists, and forbidden subjective score fields.

`summarize` emits compact deterministic JSON for one valid scorecard.

## Output Contract

Generated scorecards include:

- `scorecard_id`
- `source_evidence_id`
- `platform`
- `surface_id`
- `route_or_screen`
- `status`
- `total_score`
- `max_score`
- `normalized_score`
- `dimensions`
- `blocking_failures`
- `warnings`
- `recommendation`
- `source_of_truth_note`
- `generated_by`

No timestamps, random ids, screenshots, browser traces, image analysis results, Figma data, Canva data, Storybook build output, or implementation instructions are included.

## Thresholds

- Invalid evidence manifest: command exits non-zero before scorecard output.
- Blocking failures: `status=fail`.
- `normalized_score >= 0.85` with no blocking failures: `status=pass`.
- `normalized_score >= 0.60` with no blocking failures: `status=warn`.
- Below `0.60`: `status=fail`.

Recommendations:

- `usable_for_pr5_pr6_brief` means metadata evidence quality is sufficient for a future brief.
- `needs_evidence` means more evidence metadata is required before future implementation work.
- `rejected` means the evidence or scorecard cannot inform future implementation.

## Blocking Failures

The scorecard layer relies on PR-3 validation for fail-closed checks such as:

- source-of-truth violations
- unknown component ids
- unsafe artifact paths
- committed binary artifact references
- copy-safety violations
- invalid enum values or required fields

The scorecard also treats `status=rejected` evidence as a blocking failure.

## Deferred

PR-4 does not implement visual/pixel scoring, browser capture, Storybook parity, web implementation, iOS parity, App Store screenshot validation, Figma writes, Canva writes, GEPA, or external crawler work.

PR-5 and PR-6 may consume accepted scorecards as review evidence, but scorecards remain non-canonical and cannot override repo truth.
