---
name: pulseplate-agent-learning-loop
description: Produce redacted, deterministic, repo-governed learning-loop proposals with metrics for repeated PulsePlate failure and successful-iteration patterns.
---

# PulsePlate Agent Learning Loop

## When to use

- A PR exposes a repeated role-agent, review, premortem, workflow, architecture,
  or successful-iteration pattern.
- The operator asks to turn review learning into repo-governed guidance.

## Procedure

1. Keep learning-loop artifacts proposal-only until a reviewed repo diff
   promotes them into a scoped instruction surface.
2. Use the offline helper and tests:

   ```bash
   python3 -m pytest tests/test_agent_learning_loop.py -q
   ```

3. Redaction is mandatory. Do not store tokens, secrets, raw provider payloads,
   hidden reasoning, or local absolute evidence paths as learning-loop truth.
4. Learning records must use `agent_learning_record.v1`, set `pattern_kind`,
   and include bounded `learning_metrics`. Metrics are proposal-only process
   signals; do not write runtime telemetry, semantic cache, graph truth, or
   product runtime truth.

## SoT links

- `docs/orchestration/AGENT_LEARNING_LOOP.md`
- `docs/orchestration/contracts/agent_learning_record.v1.json`
- `scripts/orchestration/agent_lesson_extractor.py`
- `scripts/orchestration/agent_lesson_promoter.py`
