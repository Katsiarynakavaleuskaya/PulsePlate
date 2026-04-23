# PulsePlate RAG Release Gates Threshold Reporting Task Packet

**Date:** 2026-04-22 (`America/New_York`)
**Mode:** coordinator-first, worktree-isolated, canonical-release-gates follow-up
**Worktree:** `worktrees/rag-release-gates-threshold-reporting`
**Branch:** `feat/rag-release-gates-threshold-reporting`
**Ledger:** [`ledger-p1-rag-release-gates-lane`](../roadmap/BACKLOG_LEDGER.md#ledger-p1-rag-release-gates-lane)

## Decision Question

How should PulsePlate improve canonical threshold/result reporting for the
release-gates lane and optionally surface companion RAGAS metrics without
creating a second evaluation rail or widening into runtime/GraphRAG work?

## Summary

This lane is a narrow follow-up on the canonical release-gates runner.
It adds richer threshold reporting and an optional informational companion
artifact adapter for precomputed RAGAS JSON. Canonical gate ownership stays
inside `scripts/evals/run_rag_release_gates.py`.

## Success Criteria

1. The canonical runner emits deterministic `threshold_results`.
2. `gate_report.md` and `GITHUB_STEP_SUMMARY` show threshold rows clearly.
3. A precomputed companion RAGAS JSON artifact can be ingested for
   informational reporting only.
4. Companion metrics do not change `gate_checks`, `release_decision`, or
   `--require-pass`.
5. PR smoke remains advisory/reporting-only.
6. Weekly/manual execution remains the only canonical strict GitHub lane.

## Role Order (mandatory)

Execute in this order for the lane:

1. `agent-coordinator`
2. `architecture-specialist`
3. `data-scientist-agent`
4. `ai-innovation-specialist`
5. `backend-engineer`

Post-open mandatory review lane:

1. `qa-engineer-agent`
2. `bug-hunter`

Conditional reviewer:

- `security-auditor` only if scope drifts into privileged surfaces beyond the
  approved eval/docs/workflow seam

## Skill / Plugin Routing

Required skills:

- `pulseplate-workflow`
- `pulseplate-gates`
- `docs-sync`

Recommended skills:

- `agents-md`
- `code-review-expert`
- `bug-triage`

Required plugin surfaces:

- `GitHub` for live PR/check/review truth
- `CodeRabbit` for post-open review truth

Explicitly out of scope for this lane:

- `Computer Use`
- `Linear`
- `Hugging Face`
- `Life Science Research`
- `Netlify`
- `Cloudflare`
- `Sentry`
- `build-ios-apps`
- `build-macos-apps`
- `build-web-apps`
- `Expo`

## Scope

### In scope

- `scripts/evals/run_rag_release_gates.py`
- `tests/test_rag_release_gates_runner.py`
- `docs/evals/PULSEPLATE_RAG_RELEASE_GATES.md`
- `docs/evals/RAGAS_SETUP.md`
- this packet
- `.github/workflows/rag-release-gates.yml` only if required to surface improved
  reporting without changing PR-smoke strictness

### Out of scope

- `app/**`
- `core/**`
- `llm.py`
- `evals/ragas/**`
- runtime requirements / CI install surface for `ragas`
- public DTO/OpenAPI/runtime schema changes
- GraphRAG runtime behavior
- graph-specific thresholds or artifact schema

## Architecture Decision

### Canonical ownership

- `scripts/evals/run_rag_release_gates.py` remains the only canonical owner of:
  - `thresholds`
  - `threshold_results`
  - `gate_checks`
  - `release_decision`
  - `--require-pass`

### Companion bridge

- Optional input: precomputed companion JSON artifact
- Source family: `artifacts/rag_eval/<experiment_id>/...`
- Reporting role: informational only
- Companion metrics must never affect:
  - `threshold_results`
  - `gate_checks`
  - `release_decision`
  - weekly/manual strict semantics

## Risks

- accidental second eval rail through companion metrics influencing gate logic
- accidental CI widening by installing or invoking `ragas`
- doc drift between threshold values in code and canonical docs
- accidental forward-binding of future selective GraphRAG evaluation semantics

## Mitigations

- fail closed on malformed companion JSON
- keep companion metrics report-only
- keep PR smoke advisory
- keep weekly/manual strict lane unchanged
- update docs to state that GraphRAG stays deferred to a separate docs/ADR lane

## Validation

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
pytest -q tests/test_rag_release_gates_runner.py
pre-commit run --all-files
make verify
```

Manual local composition smoke:

```bash
python -m evals.ragas.run_ragas_eval \
  --dataset evals/ragas/testset.jsonl \
  --output-json artifacts/rag_eval/ragas_bootstrap_manual/metrics_summary.json

python3 scripts/evals/run_rag_release_gates.py \
  --input-path data/evals/pulseplate_rag_eval_sample.jsonl \
  --retriever-mode local_tfidf \
  --generator-mode extractive_stub \
  --companion-metrics-json artifacts/rag_eval/ragas_bootstrap_manual/metrics_summary.json
```

## DoD

- canonical runner emits deterministic threshold rows
- canonical docs describe threshold reporting and companion artifact bridge
- companion JSON ingestion is fail-closed and informational only
- no runtime/request-path/GraphRAG widening is introduced
- post-open `qa-engineer-agent -> bug-hunter` lane is executed after PR open
