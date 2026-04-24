# Wave 6 A9 Scientific Reliability Packet

**Date:** 23 April 2026
**Scope:** bounded Wave 6 docs-only evidence publication for the existing
product-AI lane
**Mode:** planning packet

## Snapshot immutability

The `2026-04-23` date in this packet name and in the local replay artifact path
is intentional. It marks an immutable evidence snapshot for the `PR-A9` slice,
not a rolling document name. Future evidence refreshes must create a new dated
packet or an explicit superseding follow-up instead of silently rewriting this
snapshot.

The canonical exact replay table, guardrail result, and reproducibility command
block live in
`docs/audit/PR_A9_SCIENTIFIC_RELIABILITY_EVIDENCE_PACKET_2026-04-23.md`.
This planning packet may summarize those results, but it must not become a
second source of truth for replay metrics or commands.

## Purpose

Freeze one narrow Wave 6 follow-up slice after merged `PR-A8` that turns the
current AI reliability lane into a reproducible, wellness-safe evidence packet
without widening runtime scope.

This packet exists to:

- keep `PR-A9` docs-only and evidence-first;
- publish one canonical replay-backed reliability packet for the AI lane;
- separate publishable claims from deferred hypotheses and forbidden claims;
- map internal evidence to future public article themes without implying live
  runtime or medical proof;
- keep runtime, verification admission, and semantic-cache scope unchanged.

## Current-head truth

- The roadmap already defines `PR-A9` as
  `docs(ai): publish scientific reliability evidence packet for the AI lane`
  with backlog target `ledger-p1-scientific-reliability-pipeline`
  (`docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md:493-506`).
- The only canonical evaluation proof surface for this lane is the governed
  offline replay contract plus its deterministic test surface
  (`docs/orchestration/contracts/LOGIC_PHILOSOPHY_REPLAY_EVAL_CONTRACT.md:1-77`,
  `tests/test_logic_philosophy_replay_eval.py:153-241`).
- The evaluator enforces immutable replay inputs, zero-network execution, and
  an output path under
  `artifacts/orchestration/experiments/results/`
  (`scripts/orchestration/logic_philosophy_replay_contract.py:91-231`,
  `scripts/orchestration/logic_philosophy_replay_eval.py:147-240`).
- A fresh local replay artifact for this lane was generated at
  `artifacts/orchestration/experiments/results/logic-philosophy/a9-2026-04-23.json`
  with `winner_arm=A3_combined`, `promotion_ready=true`, and
  `guardrails.known_good_false_positive_rate=0.0`.
- Shipped runtime seams may be cited as implementation anchors only, not as
  benchmark proof:
  `core/ai/insight_runtime.py:68-80`,
  `core/insight/philosophical_runtime.py:192-216`,
  `core/verification/contracts.py:16-38`,
  `core/rag/orchestration.py:30-73`.
- The verification registry still marks recursive execution as
  `recursive_path_not_canonical` for validated-evidence authorship, so A9 must
  not market recursive execution as the canonical validated-evidence write path
  (`core/verification/registry.py:256-286`).

## Hard boundaries

- No `core/*`, `app/*`, `legacy_app.py`, `app/routers/*`, OpenAPI, or public
  response-shape changes
- No new benchmark harnesses or runtime experiments
- No semantic cache, Redis/GPTCache, GraphRAG, or ContextManifest work
- No verification-contract, `VerificationBundle`, or knowledge-admission
  changes
- No public trust-field claims or route-authority claims
- No production, latency, cost, clinical-efficacy, diagnostic, or health-outcome
  claims
- No recursive-path claim as canonical validated-evidence authorship

## Canonical source-of-truth anchors

### Proof surfaces

- `docs/orchestration/contracts/LOGIC_PHILOSOPHY_REPLAY_EVAL_CONTRACT.md`
- `tests/test_logic_philosophy_replay_eval.py`
- `scripts/orchestration/logic_philosophy_replay_eval.py`
- `scripts/orchestration/logic_philosophy_replay_contract.py`
- `tests/fixtures/orchestration/logic_philosophy_replay/replay_cases.json`
- `tests/fixtures/orchestration/logic_philosophy_replay/replay_negative_controls.json`
- local reproducibility path:
  `artifacts/orchestration/experiments/results/logic-philosophy/a9-2026-04-23.json`

### Runtime anchors only

- `core/ai/insight_runtime.py`
- `core/insight/philosophical_runtime.py`
- `core/verification/contracts.py`
- `core/verification/registry.py`
- `core/rag/orchestration.py`

### Background-only context

- `docs/analysis/SCIENTIFIC_INNOVATION_ANALYSIS.md`
- `docs/insights/RECURSIVE_METHODS_LLM_RAG.md`
- `docs/insights/PHILOSOPHICAL_LOGIC_LLM_RELIABILITY.md`

These background docs may explain motivation, but they are not benchmark proof.

## Required role-agent order for this lane

1. `agent-coordinator`
2. `data-scientist-agent`
3. `architecture-specialist`
4. `backend-engineer`
5. `security-auditor`
6. `qa-engineer-agent`
7. `bug-hunter`

Rules:

- every assigned role agent must be used in this order;
- no assigned role agent may be skipped without an explicit packet update;
- the canonical post-open `qa-engineer-agent -> bug-hunter` pass remains
  mandatory.

## Scope

### In scope

- one A9 task-analysis doc
- one A9 planning packet
- one canonical audit evidence packet with exact replay metrics and claim
  boundaries
- backlog reconciliation for `ledger-p1-scientific-reliability-pipeline`
- optional roadmap note linking the active A9 packet
- internal/public article mapping that stays inside bounded evidence claims

### Out of scope

- any runtime, service, RAG, or verification implementation changes
- OpenAPI or public response changes
- new replay harnesses, new fixtures, or new scoring logic
- public article publication itself
- semantic-cache or recursive-learning follow-up work

## Replay evidence summary

Canonical source:
`docs/audit/PR_A9_SCIENTIFIC_RELIABILITY_EVIDENCE_PACKET_2026-04-23.md`.

Replay contract bounds, copied here only as a scope summary:

- mode: `offline_replay_ablation`
- replay corpus: `n=3` cases
- known-good controls: `n=3`
- `network_budget=0`

Current reproduced guardrail summary:

- `winner_arm=A3_combined`
- `promotion_ready=true`
- `guardrails.known_good_false_positive_rate=0.0`

Use the audit packet for exact per-arm rates and the command block that
regenerates the local replay artifact.

## Publishable claims

- On a governed offline replay corpus (`n=3` cases, `n=3` known-good controls),
  the combined logic + philosophy arm outperformed the partial arms on the
  tracked answer-quality metrics.
- The replay lane is deterministic, zero-network, and reproducible from repo
  fixtures and scripts.
- The combined arm matched the current curated oracle set without triggering
  known-good false positives in this replay.
- The current AI lane includes bounded internal verification and admission
  controls, but those controls remain internal-only implementation seams.

## Hypotheses and deferred claims

- broader scientific validation beyond the governed replay corpus
- production/runtime efficacy
- latency, throughput, or cost improvements
- public proof for recursive execution as canonical validated-evidence
  authorship
- any external benchmark or competitor comparison

## Forbidden claims

- `validated in production`
- `runtime-proven`
- `clinically proven`
- `medical safety`
- `diagnostic quality`
- `health outcomes improved`
- `VerificationBundle is user-visible`
- `recursive verification is the canonical validated-evidence write path`

## Wellness-safe / non-medical claim rules

- Frame the lane as `general wellness information`, not diagnosis or treatment.
- Always disclose `offline_replay_ablation`, curated fixtures, and zero-network
  execution.
- Every published rate must include corpus counts.
- Treat runtime seams as implementation anchors only, never as standalone
  benchmark proof.

## Internal/public article mapping

| Internal evidence section | Public-safe narrative theme |
| --- | --- |
| Replay contract and corpus bounds | `Evidence-backed offline replay methods` |
| Per-arm quality table | `How bounded reasoning patterns are evaluated` |
| Wellness-safe boundaries | `Why claims stay non-medical and scoped` |
| Internal verification/admission anchors | `Internal trust controls exist without exposing public trust fields` |
| Deferred claims section | `What is intentionally not claimed yet` |

This PR does not publish the external article itself; it only freezes the
mapping from internal evidence to future public-safe themes.

## Validation

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `. .venv/bin/activate && pytest -q tests/test_logic_philosophy_replay_eval.py`
- replay CLI command from the canonical audit packet
- `pre-commit run --all-files`
- `make verify` before any merge-ready claim

## Scope-drift stop conditions

- any edit outside docs/backlog/audit/orchestration surfaces
- any use of analysis/insight prose as benchmark proof
- any new runtime, OpenAPI, DTO, verification, or route-metadata changes
- any wording that collapses offline replay evidence into live runtime or
  medical proof
- any published metric without corpus counts or reproducibility commands
