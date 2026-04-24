# PR A9 Scientific Reliability Evidence Packet

**Date:** 2026-04-23
**Status:** Verified docs-only evidence packet
**Scope:** Wave 6 AI reliability publication evidence only

## Snapshot Immutability

The `2026-04-23` date in this file name and in the replay output path is part
of the evidence identity for `PR-A9`. Treat this document as an immutable
snapshot for that dated slice. Future refreshes must create a new dated packet
or an explicit superseding follow-up; they should not silently roll this file
forward.

This audit packet is the canonical source for the exact replay metrics,
guardrail result, and reproducibility commands for `PR-A9`. Planning and
roadmap documents may link here, but they should not duplicate the full replay
table or command block.

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
  `docs/orchestration/contracts/LOGIC_PHILOSOPHY_REPLAY_EVAL_CONTRACT.md:5`
  defines the lane as offline replay + ablation before runtime rollout, and
  `docs/orchestration/contracts/LOGIC_PHILOSOPHY_REPLAY_EVAL_CONTRACT.md:15`
  locks `offline_replay_ablation`.
- deterministic test:
  `tests/test_logic_philosophy_replay_eval.py:153` asserts that the provided
  offline corpus ranks `A3_combined` highest, and
  `tests/test_logic_philosophy_replay_eval.py:225` guards artifact output
  placement.
- evaluator:
  `scripts/orchestration/logic_philosophy_replay_eval.py:147` evaluates all
  replay arms, and
  `scripts/orchestration/logic_philosophy_replay_eval.py:202` computes the
  known-good false-positive guardrail.
- corpus validation:
  `scripts/orchestration/logic_philosophy_replay_contract.py:91` validates
  replay cases and
  `scripts/orchestration/logic_philosophy_replay_contract.py:171` validates
  negative controls.
- immutable fixtures:
  `tests/fixtures/orchestration/logic_philosophy_replay/replay_cases.json:3`
  and
  `tests/fixtures/orchestration/logic_philosophy_replay/replay_negative_controls.json:3`
  both declare `offline_replay_ablation`.
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
/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_logic_philosophy_replay_eval.py
/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python scripts/orchestration/logic_philosophy_replay_eval.py \
  --cases tests/fixtures/orchestration/logic_philosophy_replay/replay_cases.json \
  --negative-controls tests/fixtures/orchestration/logic_philosophy_replay/replay_negative_controls.json \
  --output logic-philosophy/a9-2026-04-23.json
```

Local generated output path:

- `artifacts/orchestration/experiments/results/logic-philosophy/a9-2026-04-23.json`

Verified command evidence:

- Command:
  `python3 scripts/orchestration/check_preflight.py`
  Output:
  `PASS: All required SoT files present`;
  `PASS: worktrees/ not tracked`;
  `PASS: working tree clean`.
  Exit code: `0`.
- Command:
  `python3 scripts/orchestration/check_agent_consistency.py`
  Output:
  `OK: agent docs and files are consistent.`
  Exit code: `0`.
- Command:
  `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_logic_philosophy_replay_eval.py`
  Output:
  `...............                                                          [100%]`
  Exit code: `0`.
- Command:
  `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python scripts/orchestration/logic_philosophy_replay_eval.py --cases tests/fixtures/orchestration/logic_philosophy_replay/replay_cases.json --negative-controls tests/fixtures/orchestration/logic_philosophy_replay/replay_negative_controls.json --output logic-philosophy/a9-2026-04-23.json`
  Output:
  `"winner_arm": "A3_combined"`;
  `"promotion_ready": true`;
  `"known_good_false_positive_rate": 0.0`.
  Exit code: `0`.

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
