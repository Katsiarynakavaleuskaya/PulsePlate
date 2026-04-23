# PR A9 Scientific Reliability Evidence Packet

**Date:** 2026-04-23
**Status:** docs-only evidence packet
**Scope:** Wave 6 AI reliability publication evidence only

## Summary

Current `main` now carries enough governed replay/eval infrastructure to
publish a narrow scientific reliability packet for the AI lane. This packet
does not claim production proof, medical efficacy, or generalized scientific
superiority. It documents the current reproducible offline replay evidence,
the trust boundaries around that evidence, and the mapping from internal proof
to future public-safe narrative themes.

## Scope In

- offline replay contract and deterministic evaluator
- replay corpus bounds and guardrails
- current per-arm evidence snapshot
- claim boundaries and forbidden claims
- wellness-safe trust framing
- reproducibility commands and local artifact path

## Scope Out

- runtime or API implementation changes
- OpenAPI, DTO, or response-shape changes
- public publication of an external article
- new benchmark harnesses or new replay fixtures
- production, latency, cost, clinical, or competitor claims
- semantic cache, recursive-learning, or broader benchmark follow-up lanes

## Evidence Sources

- contract:
  `docs/orchestration/contracts/LOGIC_PHILOSOPHY_REPLAY_EVAL_CONTRACT.md`
- deterministic test:
  `tests/test_logic_philosophy_replay_eval.py`
- evaluator:
  `scripts/orchestration/logic_philosophy_replay_eval.py`
- corpus validation:
  `scripts/orchestration/logic_philosophy_replay_contract.py`
- immutable fixtures:
  `tests/fixtures/orchestration/logic_philosophy_replay/replay_cases.json`
  and
  `tests/fixtures/orchestration/logic_philosophy_replay/replay_negative_controls.json`
- local reproducibility output:
  `artifacts/orchestration/experiments/results/logic-philosophy/a9-2026-04-23.json`

## Replay Corpus Snapshot

- mode: `offline_replay_ablation`
- replay cases: `n=3`
- known-good controls: `n=3`
- `network_budget=0`
- output arm order:
  `A3_combined`, `A1_logic`, `A2_philosophy`, `A0_control`

## Current Evidence Table

| Arm | correctness_pass_rate | unsupported_claim_rate | contradiction_rate | first_pass_readiness_proxy | usefulness_floor_rate |
| --- | --- | --- | --- | --- | --- |
| `A3_combined` | `1.0` | `0.0` | `0.0` | `1.0` | `1.0` |
| `A1_logic` | `0.0` | `0.0` | `0.0` | `0.0` | `1.0` |
| `A2_philosophy` | `0.0` | `0.0` | `0.0` | `0.0` | `0.0` |
| `A0_control` | `0.0` | `1.0` | `0.3333` | `0.0` | `0.0` |

Guardrail result:

- `winner_arm=A3_combined`
- `promotion_ready=true`
- `guardrails.known_good_false_positive_rate=0.0`

Interpretation:

- `A3_combined` is the only arm that clears all tracked answer-quality metrics
  on this governed corpus.
- `A1_logic` suppresses unsupported claims but still misses required facts.
- `A2_philosophy` preserves non-medical framing but still misses required facts.
- `A0_control` fails correctness, readiness, and contradiction discipline on
  the same corpus.

## Publishable Claims

- On a governed deterministic offline replay corpus (`n=3` cases, `n=3`
  known-good controls), the combined logic + philosophy arm outperformed the
  partial arms on the tracked answer-quality metrics.
- The replay lane is reproducible from repo fixtures and scripts with
  `network_budget=0`.
- The combined arm did not trigger known-good false positives on this replay.
- Current product-AI work includes bounded internal verification and admission
  seams, but those remain internal-only implementation details.

## Hypotheses and Deferred Claims

- latency, throughput, or cost improvements
- production or live-runtime efficacy
- broad scientific validation beyond this replay corpus
- public proof for recursive execution as canonical validated-evidence
  authorship
- competitor comparison or industry-leading performance

## Forbidden Claims

- `validated in production`
- `runtime-proven`
- `clinically proven`
- `medical safety`
- `diagnostic quality`
- `health outcomes improved`
- `VerificationBundle is publicly exposed`
- `recursive verification is the canonical validated-evidence write path`

## Security / Trust Boundaries

- This evidence is offline replay only. It is not live traffic, production
  telemetry, or clinical evidence.
- Replay fixtures are curated immutable oracle inputs, not real-user outcome
  data.
- Wellness-safe framing remains mandatory: the AI lane provides general
  wellness information, not diagnosis or treatment advice.
- Verification truth remains internal-only; no public trust fields are implied
  by this packet.
- Runtime seams are cited as implementation anchors only, not as benchmark
  proof.

## Reproducibility

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
. .venv/bin/activate && pytest -q tests/test_logic_philosophy_replay_eval.py
. .venv/bin/activate && python3 scripts/orchestration/logic_philosophy_replay_eval.py \
  --cases tests/fixtures/orchestration/logic_philosophy_replay/replay_cases.json \
  --negative-controls tests/fixtures/orchestration/logic_philosophy_replay/replay_negative_controls.json \
  --output logic-philosophy/a9-2026-04-23.json
```

Local generated output path:

- `artifacts/orchestration/experiments/results/logic-philosophy/a9-2026-04-23.json`

## Internal / Public Narrative Mapping

| Internal proof | Public-safe framing |
| --- | --- |
| offline replay contract | `evidence-backed offline replay methods` |
| combined-vs-partial arm table | `bounded reasoning patterns are evaluated, not assumed` |
| non-medical caveats | `wellness-safe claim discipline` |
| internal verification/admission seams | `internal trust controls exist without public trust-field claims` |
| deferred claims | `what is intentionally not claimed yet` |

## Decision

`PR-A9` should stay narrow and docs-only. The current repo truth is sufficient
for a reproducible evidence packet, but not for production, latency, clinical,
or generalized scientific claims. Any future lane that needs those claims must
introduce its own governed benchmark contract and separate proof surface.
