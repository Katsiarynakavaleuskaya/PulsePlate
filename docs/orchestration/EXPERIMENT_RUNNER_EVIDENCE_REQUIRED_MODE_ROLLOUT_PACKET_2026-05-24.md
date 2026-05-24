# Experiment Runner Evidence Required-Mode Rollout Packet

Date: 2026-05-24

## Status

Required-mode mechanics are implemented, but the repo default remains advisory.
This packet closes the ledger drift after PR #1800 and reserves the default flip
for a separate rollout PR.

## Current Mechanics

- `scripts/ci/check_pr_body_phase2_gates.py` supports advisory and required
  Experiment Runner evidence modes.
- `scripts/orchestration/check_merge_ready.py` forwards the selected mode into
  Phase2 validation.
- Required mode fails closed on missing or malformed Experiment Runner evidence.
- Advisory mode remains the rollback-safe default.

## Activation Preconditions

- Current-head CI and review-governance checks remain stable with advisory mode.
- Non-trivial lane classification is explicit in PR body or mapping artifacts.
- `Not applicable:` remains narrow and must include a reason.
- Experiment Runner artifact load/write failures are treated as infra blockers,
  not valid `Not applicable` reasons.
- The activation PR proves rollback to advisory mode through CLI/env coverage.

## Rollback

Set the evidence mode back to advisory through the Phase2 CLI or merge wrapper
environment:

```bash
PULSEPLATE_EXPERIMENT_RUNNER_EVIDENCE_MODE=advisory
```

Rollback does not weaken malformed-path validation, identity checks, review
thread disposition, fixed mapping, or current-head CI requirements.

## Out Of Scope

- Slack notification identity and operator messaging behavior.
- Runner mutation access to `scripts/ci/**` or other governance validators.
- Any change to Git attribution, review-thread authority, merge authority, or
  autonomous runner promotion.
