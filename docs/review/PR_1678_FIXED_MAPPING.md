# PR 1678 Fixed Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1678
Branch: `codex/evidence-active-metadata-admission`
Title: `feat(evidence): add active metadata admission gates`

## Summary

PR-E4 adds deterministic active metadata admission gates for Evidence Graph
Runtime. It introduces internal `allow_execute`, `allow_promote`, and
`allow_serve` decision contracts over E1/E2/E3 evidence metadata.

## Goal

Make evidence execution, promotion, and serving decisions deterministic,
replay-compatible, policy-visible, metadata-safe, and side-effect free.

## Business Reason

This PR closes the next Evidence Graph reliability gap by preventing future AI
release gates, semantic-cache gates, and metadata admission decisions from
relying on scattered ad hoc checks.

This PR does not add visible product features.

## Scope

- `core/evidence/admission.py` with admission policy/input/decision contracts.
- Deterministic `decide_admission`, `decide_allow_execute`,
  `decide_allow_promote`, and `decide_allow_serve` helpers.
- Fail-closed metadata validation for prompt/response/user-health/secret and
  path-like payloads.
- Focused tests for thresholds, staleness, metadata safety, mutation safety,
  stable serialization, and import boundaries.
- Contract, backlog, epic, and scoped agent-instruction documentation.

## Out Of Scope

- Semantic cache, Redis, GPTCache, or cache-hit logic.
- GraphRAG or knowledge graph runtime.
- Product RAG behavior or `core/knowledge/promotion.py` rewrites.
- Runtime routes, FastAPI, OpenAPI, DB migrations, providers, eval runners, or
  RAGAS runner behavior.
- Online eval, judge calibration, goldens, dashboards, frontend/iOS/design
  changes, billing/auth/compliance surfaces, or advisory wiki authority.

## Files Touched

- `core/evidence/admission.py`
- `core/evidence/__init__.py`
- `core/evidence/AGENTS.md`
- `tests/core/evidence/test_admission.py`
- `docs/orchestration/contracts/EVIDENCE_METADATA_ADMISSION.md`
- `docs/roadmap/EVIDENCE_GRAPH_RUNTIME_EPIC.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `docs/review/PR_1678_FIXED_MAPPING.md`

## Coordinator Bootstrap

- Pre-open packet: `a7b8aa010ed7`
- Post-open review packet: `fa1dd5432386`
- Declared pre-open role order:
  `agent-coordinator -> architecture-specialist -> rag-systems-agent -> data-scientist-agent -> security-auditor -> qa-engineer-agent -> bug-hunter -> cursor-specialist-agent`
- Mandatory post-open lane:
  `qa-engineer-agent -> bug-hunter`

## Tests

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `.venv/bin/python -m pytest -q tests/core/evidence/test_admission.py tests/core/evidence/test_promotion_ledger.py tests/core/evidence/test_replay.py tests/core/evidence/test_events.py tests/core/evidence/test_assets.py tests/core/evidence/test_fingerprints.py`
- PASS: `.venv/bin/python -m mypy --no-incremental --cache-dir=/dev/null core/evidence tests/core/evidence/test_admission.py`
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS: pre-push hook set: changed-files mypy, pip-audit, backend pre-push
  tests, full-repo Bandit, docker build test

Full local `make verify` was intentionally not run under the
operator-approved machine-heavy exception. Current-head GitHub CI parity and
strict merge-readiness remain required before merge.

## Security Notes

Admission metadata rejects raw prompt/response/user-health/secret fields,
obvious secret strings, bytes, non-JSON values, and path-like strings including
`.`, `./`, and `./.`.

AST import guards block runtime, provider, DB/session, Redis/cache/GPTCache,
semantic cache, GraphRAG, eval-runner, and advisory wiki/support-plane imports.

## Premortem

| Risk | Disposition | Evidence |
| --- | --- | --- |
| Runtime side effects | FIXED | `core/evidence/admission.py` is pure contracts/helpers; no writes, DB, network, routes, or providers. |
| Semantic cache or GraphRAG side door | FIXED | Import guard blocks cache/GraphRAG fragments; docs state semantic-cache prerequisites remain incomplete. |
| Product knowledge promotion duplication | FIXED | E4 does not import or rewrite `core/knowledge/promotion.py`; import guard blocks `knowledge` fragments. |
| Invalid/degraded evidence promotion | FIXED | Promote path requires valid status plus threshold and lineage checks. |
| Wall-clock nondeterminism | FIXED | Decision helpers require explicit `now`; tests cover stale and future timestamps. |
| Bad numeric metrics | FIXED | Metrics must be finite values in `[0, 1]`; tests cover NaN/inf/out-of-range. |
| Raw prompt/health/secret metadata | FIXED | Recursive metadata validation and tests reject unsafe keys and strings. |
| PR #1676-style current-directory path bug | FIXED | Admission metadata rejects `.`, `./`, `./.` with stable `ValueError`. |
| Rail/runtime/advisory mixing | FIXED | `core/evidence/AGENTS.md` and AST tests keep E4 inside pure evidence contracts. |
| Checklist-only fixes | FIXED | Premortem findings were converted into validators, tests, and docs before mapping. |
| Scope widening into eval platform | FIXED | PR excludes goldens, judge calibration, dashboards, online eval, and eval runners. |

## Rollback / Risks

Rollback is low risk: revert the internal contract/test/docs commits. No
runtime caller, API, DB, provider, cache, or eval runner is changed.

Residual risk: no production caller exercises admission yet. Later PRs must
wire E4 carefully without treating it as semantic-cache approval.

## DoD

- [x] `core/evidence/admission.py` exists.
- [x] Admission policy/input/decision contracts exist.
- [x] `allow_execute`, `allow_promote`, and `allow_serve` semantics are
  deterministic and test-covered.
- [x] Invalid/degraded/stale/low-coverage/high-fallback evidence blocks
  promotion.
- [x] Metadata safety is fail-closed.
- [x] No runtime/API/OpenAPI/DB/provider/eval-runner/cache/wiki changes.
- [x] No semantic cache or GraphRAG scope.
- [x] No product knowledge promotion rewrite.
- [x] Tests cover metrics, staleness, validation status, metadata safety,
  mutation safety, stable serialization, import boundaries, and PR
  #1676-style path regression.
- [x] Backlog/Evidence epic points to PR-E5 advisory wiki evidence bridge as
  the next Evidence Graph step after E4.

## Commit Breakdown

- `79dbda67a` - `feat(evidence): add active metadata admission gates`
- `1fff9eae9` - `docs(review): add PR 1678 fixed mapping`
- `e7b72d4d9` - `test(evidence): close admission review gaps`
- `3b0b4a497` - `fix(evidence): tighten admission decision validation`

## Pre-push Checklist

- [x] Coordinator preflight and agent consistency gates run.
- [x] Focused pytest bundle passed.
- [x] Narrow mypy passed.
- [x] `make validate-changed` passed after implementation commit.
- [x] `pre-commit run --all-files` passed.
- [x] Branch pushed successfully.

## Post-merge Checklist

- Sync local `main` with `git fetch --prune origin` and
  `git merge --ff-only origin/main`.
- Confirm `HEAD...origin/main = 0 0`.
- Prune merged branch/worktree only after merge.
- Keep semantic cache blocked until a separate dedicated gate opens.
- Start PR-E5 advisory wiki evidence bridge only from clean synced main and
  current repo truth.

## AGENTS.md Updates

Updated `core/evidence/AGENTS.md` with E4-specific guidance: admission
decisions are pure gates, require explicit timestamp input, and must not write,
import runtime/provider/DB/cache/wiki/eval-runner surfaces, or rewrite product
knowledge promotion.

## Deferred / Follow-ups

- PR-E5 advisory wiki evidence bridge remains next in the Evidence Graph train.
- Semantic cache remains deferred until its dedicated gate opens with
  observability, false-hit guardrails, rollout contract, and current-head CI
  governance.
- AI release gates, goldens, judge calibration, dashboards, and online eval
  remain later eval-roadmap work, not E4.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Post-open `qa-engineer-agent -> bug-hunter` sidecar review pass completed.
CodeRabbit/Sourcery/Cubic final no-actionables check remains required before
merge readiness.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1678#pullrequestreview-4235099053 -> e7b72d4d9
Disposition: FIXED
Commit: e7b72d4d9
Evidence: `tests/core/evidence/test_admission.py` mutates the returned `AdmissionInput.metadata` view and asserts subsequent reads are unchanged.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1678#pullrequestreview-4235145977 -> 3b0b4a497
Disposition: FIXED
Commit: 3b0b4a497
Evidence: Cubic identified decision timestamp and `allow_degraded` validation risks; `core/evidence/admission.py` now validates `allow_degraded` as a strict bool and sets `AdmissionDecision.produced_at` from explicit `now`, while `tests/core/evidence/test_admission.py` covers both paths.

## Sidecar Review Findings

- QA sidecar finding: `admission_input_from_eval_event()` dropped source
  event metadata and could bypass E4 metadata safety -> e7b72d4d9
  - Disposition: FIXED
  - Evidence: `core/evidence/admission.py` merges source metadata under
    `event_metadata`; `tests/core/evidence/test_admission.py` covers unsafe
    E2 event metadata rejected by the E4 adapter.
- QA sidecar finding: `execute` could allow degraded status without
  `allow_degraded` -> e7b72d4d9
  - Disposition: FIXED
  - Evidence: `core/evidence/admission.py` adds execute-specific degraded
    blocking; `tests/core/evidence/test_admission.py` covers degraded execute
    denial when only the status allowlist includes degraded.
- Bug-hunter sidecar finding: raw `query_text` / eval-row text aliases could
  pass E4 adapter metadata safety -> e7b72d4d9
  - Disposition: FIXED
  - Evidence: `core/evidence/admission.py` expands the metadata denylist for
    `query_text`, `question_text`, `answer_text`, and raw query aliases;
    `tests/core/evidence/test_admission.py` covers adapter rejection for those
    fields.

## Merge Readiness

Not merge-ready at mapping creation time.

Required before merge:

- current-head CI parity clean;
- diff coverage clean;
- CodeRabbit/Sourcery/Cubic no-actionables;
- all review threads resolved with disposition evidence;
- strict merge-readiness wrapper with auth;
- mandatory review wait-window after latest bot/review activity.
