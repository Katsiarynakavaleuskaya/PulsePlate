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

Post-open bot and agent review threads were triaged after concrete fixes or explicit dispositions. Mapping was updated after fix commits existed.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 083c1eeca
Evidence: Mapping artifact checkboxes and matrix signature checks were added; local gates passed before the commit was pushed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233091753 -> 083c1eeca
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233099804 -> 083c1eeca

Disposition: FIXED
Commit: 7c745043b
Evidence: Sourcery, CodeRabbit, and Cubic findings were fixed in code/docs/tests; focused tests, mypy, semantic-cache checker, docs gate, validate-changed, and pre-commit passed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233057757 -> 7c745043b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233057761 -> 7c745043b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233091809 -> 7c745043b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233099837 -> 7c745043b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233143300 -> 7c745043b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233143327 -> 7c745043b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233143335 -> 7c745043b

Disposition: FIXED
Commit: 710920a07
Evidence: Follow-up Codex review findings were fixed in code/tests; focused tests, mypy, semantic-cache checker, docs gate, bounded regression bundle, validate-changed, and pre-commit passed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233099817 -> 710920a07
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233099830 -> 710920a07
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233099844 -> 710920a07
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233249559 -> 710920a07
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233249564 -> 710920a07
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233249572 -> 710920a07
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233249582 -> 710920a07
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233249588 -> 710920a07
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233249590 -> 710920a07
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233249591 -> 710920a07
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233249593 -> 710920a07

Disposition: NOT-A-BUG
Evidence: `tests/core/ai/test_semantic_cache_backend_selection.py` includes `test_no_core_ai_export_side_door`, which asserts SC-G5 remains unexported from `core/ai/__init__.py`.
Reason: The test import path intentionally exercises the repo import contract; SC-G5 still has no eager export or runtime serving side door.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233249567

## Post-Open Agent Review Fixes

| Source | Disposition | Commit | Evidence |
| --- | --- | --- | --- |
| QA final pass: overbroad `sk-` token matching rejected benign `risk-audit`; uppercase `FILE://` metadata bypassed path blocking. | FIXED | `45155f837` | Boundary-aware token regex and case-insensitive path regex; regression tests in `tests/core/ai/test_semantic_cache_backend_selection.py`. |
| Bug-hunter final pass: caller-relaxed criteria could allow safety breaches; generic CI/human proof IDs could satisfy proof gates; import guard missed subprocess and dynamic Path.open write modes. | FIXED | `45155f837` | Criteria now enforce zero-tolerance safety gates and structured proof IDs; import guard blocks process launchers and unknown write modes with focused tests. |
| Security final pass: proof IDs accepted blocked payload/truth-source terms and emitted them in stable mappings. | FIXED | `45155f837` | Evidence/proof ID validation blocks raw-payload, HealthKit, account, billing, legal, compliance, advisory/wiki, and workforce-memory terms before serialization. |
| Codex Security final scan after substantive fix. | CLEAN | `45155f837` | `/tmp/codex-security-scans/ai-runtime-semantic-cache-backend-selection-contract/45155f837_20260513T110057Z/report.md` reports no surviving findings. |

## Bot Review Tracking

| Source | Status | Disposition |
| --- | --- | --- |
| CodeRabbit | Pending current-head re-review after fix push | Prior actionables mapped above; not merge-ready until bot reports no remaining actionables or explicit dispositions. |
| Sourcery | Pending current-head re-review after fix push | Prior actionables mapped above; not merge-ready until bot reports no remaining actionables or explicit dispositions. |
| Cubic | Pending current-head re-review after fix push | Prior actionables mapped above; not merge-ready until bot reports no remaining actionables or explicit dispositions. |
| Codex Security | Clean after final substantive fix | Final scan for commit `45155f837` reports no surviving findings. |
| Codecov | Pending current-head CI parity | Historical patch coverage comment is not merge-readiness proof; canonical diff coverage remains current-head CI plus local focused diff-cover evidence. |

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
