# PR 1742 Fixed Mapping

## PR

- PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742
- Branch: `feat/ai-runtime-semantic-cache-backend-selection-contract`
- Title: `feat(ai-runtime): add semantic-cache backend selection contract`
- Scope: SC-G5 offline semantic-cache backend selection contract/evaluation matrix only.

## Summary

SC-G5 adds a deterministic, offline, label-only backend selection contract and matrix for future semantic-cache backend evaluation. Redis and GPTCache remain inert candidate labels only. The global semantic-cache gate remains closed.

## Scope

- Pure stdlib-only `core/ai/semantic_cache_backend_selection.py`.
- Machine-checkable SC-G5 contract doc and schema.
- CI checker and docs Phase 1 gate updates.
- Focused tests and import/call guard coverage.
- Narrow roadmap/backlog updates.

## Out Of Scope

- Runtime serving.
- `/insight` route wiring.
- Redis/GPTCache clients, imports, connection strings, probes, or activation.
- Embeddings, vector search, provider calls, DB, FastAPI/OpenAPI, migrations, frontend, or iOS.
- Raw prompt/query/response/answer persistence.

## Premortem Fixes Before PR Open

| Finding | Disposition | Commit | Evidence |
| --- | --- | --- | --- |
| Forged candidate decisions could bypass safety ranking. | FIXED | `8a974394e` | Selector recomputes candidate decisions; regression coverage in `tests/core/ai/test_semantic_cache_backend_selection.py`. |
| Machine-state checker could pass after required fields were renamed/removed. | FIXED | `8a974394e` | SC-G5 checker validates exact required keys and unexpected keys. |
| Guard missed annotated `Path` aliases. | FIXED | `8a974394e` | `AnnAssign` aliases are tracked; regression coverage added. |
| Matrix constructor accepted forged final decision / candidate decisions. | FIXED | `8a974394e` | Matrix recomputes decisions and rejects mismatches. |
| Guard missed direct/alias `Path.open(...).write(...)`. | FIXED | `a09788814` | Guard detects direct/alias Path open writes; regression coverage added. |
| Matrix constructor accepted forged `matrix_id`. | FIXED | `a09788814` | Matrix validates canonical deterministic matrix ID. |
| Guard missed context-manager `Path.open(...).write(...)`. | FIXED | `3772bba5d` | Guard tracks context manager file handles from Path.open. |
| Context-manager test was too broad and could false-green. | FIXED | `f2f3dabf4` | Dedicated test now asserts `Path.open.write` specifically. |

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Initial state after PR open: no human/bot review threads have been dispositioned yet. Review thread mapping must be added only after real fixes or explicit NOT-A-BUG/DEFERRED evidence.

## Fixed in Commit Mapping

- No actionable review comments

## Bot Review Tracking

| Source | Status | Disposition |
| --- | --- | --- |
| CodeRabbit | Pending post-open review | Not merge-ready until no actionables or dispositions. |
| Sourcery | Pending post-open review | Not merge-ready until no actionables or dispositions. |
| Cubic | Pending post-open review | Not merge-ready until no actionables or dispositions. |
| Codex Security | Pending post-open review | Threat-model, security-scan, and validation required. |

## Local Evidence Before PR Open

- `python scripts/orchestration/check_preflight.py` passed.
- `python scripts/orchestration/check_agent_consistency.py` passed.
- `python scripts/ci/check_semantic_cache_gate.py` passed.
- `python scripts/ci/check_docs_phase1_gates.py --files ...` passed.
- Focused semantic-cache pytest bundle passed.
- Narrow mypy passed.
- `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed` passed.
- `PATH=.venv/bin:$PATH pre-commit run --all-files` passed.
- Diff-cover for SC-G5 changed code passed at 99%.
- Pre-push hooks passed during branch push.

## Merge Readiness

Not merge-ready at PR open. Required before merge:

- Current-head CI clean.
- Strict merge wrapper with auth passes.
- No unresolved review threads.
- CodeRabbit, Sourcery, Cubic have no actionables or explicit dispositions.
- Codex Security review clean or dispositioned.
- Mandatory wait-window observed.
