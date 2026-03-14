# Logic + Philosophy Replay Eval Contract

## Summary

This contract defines the first applied `LLM/RAG reliability` experiment lane for PulsePlate as a strictly offline replay + ablation workflow. It evaluates whether deterministic `logic` and `philosophy` layers improve answer quality before any runtime rollout.

The lane is grounded in the existing experimentation umbrella and runtime foundations:

- `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md:24`
- `core/insight/philosophical_runtime.py:170`
- `core/insight/analytical/__init__.py:89`

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

- Replay corpus: `tests/fixtures/orchestration/logic_philosophy_replay/replay_cases.json:1`
- Known-good negative controls: `tests/fixtures/orchestration/logic_philosophy_replay/replay_negative_controls.json:1`
- Evaluator: `scripts/orchestration/logic_philosophy_replay_eval.py:50-59` and `scripts/orchestration/logic_philosophy_replay_eval.py:144-192`
- Contract validation helpers: `scripts/orchestration/logic_philosophy_replay_contract.py:44-88` and `scripts/orchestration/logic_philosophy_replay_contract.py:90-231`

The replay corpus is immutable during evaluation. The evaluator may score it, but it must not mutate it (`scripts/orchestration/logic_philosophy_replay_contract.py:90-231`, `scripts/orchestration/logic_philosophy_replay_eval.py:151-192`).

## Primary Metrics

- `correctness_pass_rate`
- `unsupported_claim_rate`
- `contradiction_rate`
- `first_pass_readiness_proxy`

Definitions live in `docs/analytics/METRICS_CATALOG.md:266`, `docs/analytics/METRICS_CATALOG.md:293`, `docs/analytics/METRICS_CATALOG.md:320`, and `docs/analytics/METRICS_CATALOG.md:347`.

## Guardrails

- `known_good_false_positive_rate` must stay at `0.0` for the provided negative controls (`scripts/orchestration/logic_philosophy_replay_eval.py:167-190`)
- `usefulness_floor_rate` is reported for every arm and must not silently collapse when correctness improves (`scripts/orchestration/logic_philosophy_replay_eval.py:115-140`, `scripts/orchestration/logic_philosophy_replay_eval.py:200-207`)
- Any non-zero network budget invalidates the lane for wave 1 (`scripts/orchestration/logic_philosophy_replay_contract.py:82-88`)
- The evaluator must remain deterministic and offline-only (`scripts/orchestration/logic_philosophy_replay_contract.py:82-88`, `scripts/orchestration/logic_philosophy_replay_eval.py:144-229`)

## CLI Contract

Run from repo root:

```bash
python3 scripts/orchestration/logic_philosophy_replay_eval.py \
  --cases tests/fixtures/orchestration/logic_philosophy_replay/replay_cases.json \
  --negative-controls tests/fixtures/orchestration/logic_philosophy_replay/replay_negative_controls.json
```

Optional artifact output must stay under (`scripts/orchestration/logic_philosophy_replay_eval.py:230-240`):

```text
artifacts/orchestration/experiments/results/
```

## Promotion Rule

The replay summary is promotion-ready only when all are true:

- `A3_combined` ranks highest by readiness/correctness
- `A3_combined` improves over `A0_control` on readiness and correctness
- `A3_combined` does not regress unsupported-claim rate or contradiction rate vs `A0_control`
- `known_good_false_positive_rate == 0.0`
- `A3_combined` does not regress `usefulness_floor_rate` vs `A0_control` (`scripts/orchestration/logic_philosophy_replay_eval.py:200-207`)

Passing this contract authorizes only a later human-reviewed `pr_packet` promotion step. It does not authorize runtime rollout, autonomous merge, or live provider experimentation.
