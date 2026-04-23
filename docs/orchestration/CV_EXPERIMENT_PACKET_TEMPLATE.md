# CV Experiment Packet Template

<!-- markdownlint-disable MD013 -->

Use this template for governed offline CV experiment charters and result packets.

Canonical base protocol:
`docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`

Canonical CV overlay:
`docs/orchestration/CV_EXPERIMENTATION_PROTOCOL.md`

---

## Experiment Header

- **Experiment ID:** `EXP-TBD`
- **Stage:** `charter` | `candidate_run` | `result`
- **Owner:** `@owner`
- **Primary agent:** `agent-coordinator`
- **Reviewer:** `architecture-specialist`
- **Related PR / backlog:** `PR-TBD` / `docs/roadmap/BACKLOG_LEDGER.md`

## Decision Question

One sentence describing the offline CV evaluation question.

## Candidate Mutable Surface

- Allowed paths:
  - `docs/prompts/cv/program.md`
  - `docs/orchestration/contracts/CV_PHOTO_FOOD_EVAL_CONTRACT.md`
- Forbidden paths for this cycle:
  - policy docs
  - runtime ingestion code
  - public API contracts

## Immutable Oracle List

- Oracle 1:
  - command: `...`
  - expected signal: `...`
- Oracle 2:
  - command: `...`
  - expected signal: `...`

## CV Context

- `dataset`:
  - `id`:
  - `version`:
  - `source`:
  - `license`:
  - `split_strategy`:
  - `label_provenance`:
- `sensor_conditions`:
- `uncertainty_band_policy`:
  - bands: `high`, `medium`, `low`, `unknown`
  - mode: `qualitative_only`
- `degrade_state_matrix`:
  - `high`: `show_ranked_candidates`
  - `medium`: `confirm_top_candidate`
  - `low`: `manual_entry_required`
  - `unknown`: `reject_unusable_image`
- `privacy_packet`:
  - raw image retention:
  - logging policy:
  - consent policy:
  - deletion policy:

## Metrics

- Primary metric:
- Baseline:
- Acceptance threshold:
- Secondary metrics:

## Negative Controls

- non-food image
- empty / invalid image
- ambiguous multi-item image
- low-light / blur / occlusion
- out-of-distribution image

## Result Summary

- Outcome: `promote` | `discard` | `defer`
- Failure class:
- Notes:

## Promotion Target

Choose exactly one:

- PR packet / implementation PR
- audit artifact
- guard/test proposal
- backlog entry
- memory capsule

## Deferred Follow-up Block

- Backlog item:
- Owner:
- Priority:
- Reason for deferral:
- Relevant links:
- Target PR:
- DoD:
