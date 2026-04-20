# PulsePlate RAG Release Gates Task Packet

**Date:** 2026-04-20 (`America/New_York`)
**Mode:** coordinator-first, worktree-isolated, internal-evaluation-first
**Worktree:** `worktrees/rag-release-gates`
**Branch:** `codex/rag-release-gates`
**Ledger:** [`ledger-p1-rag-release-gates-lane`](../roadmap/BACKLOG_LEDGER.md#ledger-p1-rag-release-gates-lane)

## Decision Question

How should PulsePlate integrate the delivered RAG / Insight evaluation notebook as a
canonical internal release-gates lane without prematurely turning it into a product-facing
 dashboard or introducing a second storage truth?

## Summary

The notebook is accepted as the analyst-facing source artifact, but the canonical CI path is a
deterministic companion runner. v1 output lives in gitignored artifacts, while any later
persistent history must target the existing PostgreSQL path instead of Cloudflare D1.

## Success Criteria

1. A clean worktree lane exists off synced `main`.
2. The repo contains the notebook, sample dataset, canonical docs, and deterministic runner.
3. The artifact contract is fixed under `artifacts/rag_eval/<experiment_id>/`.
4. PR/CI visibility uses build artifacts and markdown summaries instead of a new database.
5. The schema contract is stable enough to mirror later into PostgreSQL.
6. Cheap smoke is safe by default and does not require paid provider calls.

## Role Order (mandatory)

Execute in this order for the lane:

1. `agent-coordinator`
2. `architecture-specialist`
3. `ai-innovation-specialist`
4. `backend-engineer`
5. `qa-engineer-agent`
6. `bug-hunter`

Reviewer:

- `security-auditor`

Helper:

- `dev-operator`

## Scope

### In scope

- `notebooks/pulseplate_rag_release_gates.ipynb`
- `data/evals/pulseplate_rag_eval_sample.jsonl`
- `docs/evals/PULSEPLATE_RAG_RELEASE_GATES.md`
- `scripts/evals/run_rag_release_gates.py`
- tests for the runner and trace/gate contract
- CI smoke / manual-weekly workflow integration
- ledger anchor and this task packet

### Out of scope

- product-facing dashboard or admin UI
- Cloudflare D1 persistence
- Figma work
- Linear automation
- a committed 500-query weekly dataset

## Architecture Decision

### v1 source of truth

- artifact pack under `artifacts/rag_eval/<experiment_id>/`
- output files:
  - `traces.jsonl`
  - `metrics_summary.json`
  - `gate_report.md`
  - `latest_executed.ipynb`
  - optional `traces.parquet`

### v2 persistence target

- canonical persistent target: PostgreSQL
- optional access/delivery layer: Cloudflare Worker + Hyperdrive
- explicit non-goal: Cloudflare D1

## Risks

- notebook and runner drift if one becomes the only maintained surface
- silent fallback could hide strict-mode environment breakage
- trace payload sprawl if artifacts are treated like committed evidence
- future dashboard work could incorrectly normalize Cloudflare as storage truth

## Mitigations

- doc declares the notebook as analyst surface and the runner as canonical CI emitter
- strict-mode fallbacks are recorded in runtime warnings and artifact summaries
- `artifacts/rag_eval/` is gitignored
- v2 persistence is documented now as PostgreSQL-only

## Validation

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
python3 scripts/evals/run_rag_release_gates.py \
  --input-path data/evals/pulseplate_rag_eval_sample.jsonl \
  --retriever-mode local_tfidf \
  --generator-mode extractive_stub
pytest -q tests/test_rag_release_gates_runner.py
```

## DoD

- notebook, sample fixture, runner, and docs are committed
- canonical artifact pack is documented and emitted by the runner
- CI has a cheap smoke path and a manual/weekly path
- no product UI or Cloudflare D1 storage is introduced
- packet and ledger point to the same scope and contract
