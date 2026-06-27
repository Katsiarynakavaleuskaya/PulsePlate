---
name: pulseplate-review-pattern-oracles
description: Use offline PulsePlate review-pattern oracles for recurring PR governance, validator parity, fail-closed, and fixed-mapping hygiene checks.
---

# PulsePlate Review Pattern Oracles

## When to use

- A PulsePlate orchestration or review-governance task mentions recurring review
  patterns, oracle checks, fixed mapping, validator parity, or fail-closed edges.
- A role agent needs deterministic reviewer-planning evidence before PR open.

## Procedure

1. Preserve repo governance first: `AGENTS.md`, scoped `AGENTS.md`,
   `RUNBOOK_AGENT.md`, preflight, task bootstrap, and the active packet win.
2. Use the offline helper only for advisory planning:

   ```bash
   python3 -m pytest tests/test_review_pattern_oracles.py -q
   ```

3. Treat oracle output as proposal-only. It must not post comments, resolve
   threads, update fixed mapping, or claim merge readiness.

## SoT links

- `docs/orchestration/REVIEW_PATTERN_ORACLES.md`
- `docs/orchestration/contracts/review_pattern_oracles.v1.json`
- `scripts/orchestration/review_pattern_oracles.py`
