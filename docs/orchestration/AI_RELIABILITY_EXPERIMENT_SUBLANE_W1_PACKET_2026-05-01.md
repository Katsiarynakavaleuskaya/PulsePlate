# AI Reliability Experiment Sublane W1 Packet

## Summary
This packet defines the first applied `LLM/RAG reliability` experiment sublane for PulsePlate as a strictly offline replay + ablation workflow. It evaluates whether deterministic `logic` and `philosophy` layers improve answer quality before any runtime rollout.

## Backlog Anchor
P1: AI reliability experimentation sublane for logic + philosophy offline replay
Target PR: codex/ai-reliability-experiment-sublane-w1

## Non-goals
- Do not change public runtime behavior
- Do not modify app/routers/*
- Do not modify OpenAPI schema
- Do not add DB migrations
- Do not add Redis/GPTCache/semantic cache
- Do not add live LLM provider calls in CI
- Do not use Nemotron as mandatory runtime dependency
- Do not change billing, entitlement, frontend, or iOS code
- Do not reduce coverage thresholds
- Do not add skip/xfail to tests
- Do not modify existing guards without necessity

## Experiment Arms
- **A0_control**: Baseline answer without added logic/philosophy stack
- **A1_logic**: Logic-only answer
- **A2_philosophy**: Philosophy-only answer
- **A3_combined**: Combined logic + philosophy answer

All replay fixtures must provide outputs for all four arms. Partial arm sets are invalid.

## Dataset Policy
- Immutable fixtures only (no live data)
- No live provider calls
- No network access (network_budget = 0)
- No user data
- No PHI/PII
- Corpus stored in tests/fixtures/orchestration/logic_philosophy_replay/

## Primary Metrics
- **correctness_pass_rate**: Percentage of cases where all required facts are present
- **unsupported_claim_rate**: Ratio of claims not supported by oracle to total claims
- **contradiction_rate**: Percentage of cases with logical contradictions
- **first_pass_readiness_proxy**: Composite metric requiring correctness, usefulness, zero contradictions, and zero unsupported claims

## Promotion Rule
Result packet can only become implementation PR (`pr_packet`) after passing the offline replay artifact checks. Specifically:
- A3_combined must rank highest by readiness/correctness
- A3_combined must improve over A0_control on readiness and correctness
- A3_combined must not regress unsupported-claim rate or contradiction rate vs A0_control
- known_good_false_positive_rate must equal 0.0
- A3_combined must not regress usefulness_floor_rate vs A0_control

## Failure Rule
If any metric cannot be computed deterministically, mark BLOCKED rather than inventing a score.

## Security/Privacy Notes
- No PHI/PII in fixtures
- No external network calls permitted
- All data is synthetic and localized to test fixtures
- Evaluation runs in an air-gapped deterministic environment

## Validation Commands
```bash
# From repo root:
python3 scripts/orchestration/logic_philosophy_replay_eval.py \
  --cases tests/fixtures/orchestration/logic_philosophy_replay/replay_cases.json \
  --negative-controls tests/fixtures/orchestration/logic_philosophy_replay/replay_negative_controls.json
```

## Deferred / Follow-up
- Runtime rollout of logic/philosophy layers (requires separate PR)
- Integration with live RAG/LLM provider (requires separate PR)
- Online ablation testing (requires separate PR with provider budget)
- Semantic cache promotion (requires separate gate opening)
