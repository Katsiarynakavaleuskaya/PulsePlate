# Logic + Philosophy Replay Eval Contract

## Summary

This contract defines the first applied `LLM/RAG reliability` experiment lane for PulsePlate as a strictly offline replay + ablation workflow. It evaluates whether deterministic `logic` and `philosophy` layers improve answer quality before any runtime rollout.

The lane is grounded in the existing experimentation umbrella and runtime foundations:

- `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`
- `core/insight/philosophical_runtime.py`
- `core/insight/analytical/__init__.py`

## Scope

- Mode: `offline_replay_ablation`
- Budget: `network_budget = 0`
- Mutable runtime surfaces are out of scope for this PR; this lane evaluates immutable replay fixtures only.
- Promotion target remains evidence-only until the replay summary passes and a later human-reviewed PR chooses to consume it.

## Canonical Arms

- `A0_control`: baseline answer without the added logic/philosophy stack
- `A1_logic`: logic-only answer
- `A2_philosophy`: philosophy-only answer
- `A3_combined`: combined logic + philosophy answer

All replay fixtures must provide outputs for all four arms. Partial arm sets are invalid.

## Immutable Oracle Inputs

- Replay corpus: `tests/fixtures/orchestration/logic_philosophy_replay/replay_cases.json`
- Known-good negative controls: `tests/fixtures/orchestration/logic_philosophy_replay/replay_negative_controls.json`
- Evaluator: `scripts/orchestration/logic_philosophy_replay_eval.py`
- Contract validation helpers: `scripts/orchestration/logic_philosophy_replay_contract.py`

The replay corpus is immutable during evaluation. The evaluator may score it, but it must not mutate it.

## Primary Metrics

- `correctness_pass_rate`
- `unsupported_claim_rate`
- `contradiction_rate`
- `first_pass_readiness_proxy`

Definitions live in `docs/analytics/METRICS_CATALOG.md`.

## Guardrails

- `known_good_false_positive_rate` must stay at `0.0` for the provided negative controls
- `usefulness_floor_rate` is reported for every arm and must not silently collapse when correctness improves
- Any non-zero network budget invalidates the lane for wave 1
- The evaluator must remain deterministic and offline-only

## CLI Contract

Run from repo root:

```bash
python3 scripts/orchestration/logic_philosophy_replay_eval.py \
  --cases tests/fixtures/orchestration/logic_philosophy_replay/replay_cases.json \
  --negative-controls tests/fixtures/orchestration/logic_philosophy_replay/replay_negative_controls.json
```

Optional artifact output must stay under:

```text
artifacts/orchestration/experiments/results/
```

## Promotion Rule

The replay summary is promotion-ready only when all are true:

- `A3_combined` ranks highest by readiness/correctness
- `A3_combined` improves over `A0_control` on readiness and correctness
- `A3_combined` does not regress unsupported-claim rate or contradiction rate vs `A0_control`
- `known_good_false_positive_rate == 0.0`

Passing this contract authorizes only a later human-reviewed `pr_packet` promotion step. It does not authorize runtime rollout, autonomous merge, or live provider experimentation.
