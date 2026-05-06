# PR #1681 Fixed Mapping

## Summary

PR-E5 adds a pure deterministic advisory wiki evidence bridge.

## Goal

Link existing advisory wiki artifact metadata to advisory Evidence Graph assets
and advisory admission inputs while preserving that advisory wiki memory is not
product/runtime truth.

## Business reason

This PR improves operator navigation, lineage, and future reviewability without
turning wiki pages into canonical product truth. Repo/backend/OpenAPI/DB/runtime
contracts remain authoritative.

## Scope

- `core/evidence/wiki_bridge.py`
- Advisory `EvidenceAssetRef` mapping
- Advisory E4 `AdmissionInput` adapter
- Metadata/path safety validation
- Deterministic IDs and serialization
- Import guards
- Contract docs, scoped agent guidance, and roadmap/backlog updates

## Out of scope

- Wiki compiler rewrite
- `wiki_artifact_to_eval_event(...)`
- Product RAG behavior
- Runtime API, FastAPI routes, OpenAPI, DB migrations, providers
- Redis, GPTCache, semantic cache
- GraphRAG
- Eval runners
- Frontend, iOS, design files
- Advisory wiki as runtime source of truth

## Files touched

- `core/evidence/wiki_bridge.py`
- `core/evidence/__init__.py`
- `core/evidence/AGENTS.md`
- `tests/core/evidence/test_wiki_bridge.py`
- `docs/orchestration/contracts/EVIDENCE_ADVISORY_WIKI_BRIDGE.md`
- `docs/roadmap/EVIDENCE_GRAPH_RUNTIME_EPIC.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `docs/review/PR_1681_FIXED_MAPPING.md`

## Tests

Passed locally:

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
.venv/bin/python -m pytest -q tests/core/evidence/test_wiki_bridge.py tests/core/evidence/test_admission.py tests/core/evidence/test_promotion_ledger.py tests/core/evidence/test_replay.py tests/core/evidence/test_events.py tests/core/evidence/test_assets.py tests/core/evidence/test_fingerprints.py
.venv/bin/python -m pytest -q tests/test_wiki_ingest.py tests/test_wiki_promote.py tests/test_wiki_compiler_keys.py tests/test_local_support_plane.py
.venv/bin/python -m mypy --no-incremental --cache-dir=/dev/null core/evidence tests/core/evidence/test_wiki_bridge.py
make validate-changed
pre-commit run --all-files
```

Also passed during pre-push:

- changed-file mypy
- pip-audit
- backend pre-push tests
- full-repo Bandit
- Docker build test

Full `make verify` was intentionally not run under the operator-approved
machine-heavy exception.

## Security notes

- Metadata rejects prompt, response, query, user-health, secret, runtime,
  canonical, source-of-truth, and unsafe path-like payloads.
- Paths reject traversal, absolute paths, home paths, Windows drive paths, and
  current-directory values `.`, `./`, and `./.`.
- Import guards block wiki compiler CLIs, local support-plane mutation tooling,
  runtime app code, providers, DB/session, cache, GraphRAG, and eval runners.
- Wiki artifacts map only to advisory rail evidence assets.

## Premortem

- Compiler recreation risk: fixed by metadata-only bridge and import guards.
- Runtime authority risk: fixed by enforced `advisory_only=True`, advisory-only
  asset mapping, and docs.
- Local support-plane import risk: fixed by AST import guard.
- Runtime rail mapping risk: fixed by hardcoded advisory rail.
- E1/E4 bypass risk: fixed by using `create_evidence_asset_ref` and
  `AdmissionInput`.
- Semantic cache scope drift: fixed by explicit docs/backlog deferral.
- Raw payload/secret risk: fixed by metadata safety checks and tests.
- Byte-like raw payload risk: fixed by rejecting `bytes`, `bytearray`, and
  `memoryview` before generic sequence handling. Evidence:
  `core/evidence/wiki_bridge.py`; regression tests in
  `tests/core/evidence/test_wiki_bridge.py`.
- Path traversal/current-directory risk: fixed by path safety checks and tests.
- Mutation risk: fixed by defensive-copy tests.
- Checklist-only risk: code/tests/docs were changed before this mapping artifact.

## Rollback / risks

Rollback is to revert this PR. There are no runtime callers, migrations,
providers, routes, or persistent writers.

Residual risk: downstream agents could misread advisory admission as product
serving. `core/evidence/AGENTS.md` and the contract doc constrain the bridge to
advisory review/query/promotion workflows only.

## DoD

- `core/evidence/wiki_bridge.py` exists and is pure/deterministic.
- Existing advisory wiki compiler is not duplicated.
- Wiki artifacts can be represented as advisory evidence assets.
- Runtime rail mapping is blocked.
- Metadata and path safety are fail-closed.
- No core/evidence import of `scripts/orchestration` or local support-plane
  mutation tooling.
- Tests cover mapping, authority boundaries, metadata/path safety,
  deterministic IDs, mutation safety, stable serialization, and import guards.
- Docs state advisory wiki remains non-canonical workforce memory.
- Semantic cache remains blocked pending a dedicated gate.

## Commit breakdown

- `e2b067db4` - `feat(evidence): add advisory wiki bridge`
- `f7b04d1e5` - `fix(evidence): reject byte-like wiki metadata`

## Pre-push checklist

- [x] Coordinator bootstrap packet created: `bc1f48dd1ba3`
- [x] Preflight passed
- [x] Agent consistency passed
- [x] Focused evidence tests passed
- [x] Wiki compiler/support-plane regression tests passed
- [x] Narrow mypy passed
- [x] `make validate-changed` passed
- [x] `pre-commit run --all-files` passed
- [x] Pre-push hooks passed
- [x] Full `make verify` intentionally deferred under machine-heavy exception

## Post-merge checklist

- Sync local `main` with `git fetch --prune origin` and
  `git merge --ff-only origin/main`.
- Prune `codex/evidence-advisory-wiki-bridge` after merge.
- Confirm root checkout remains clean and unrelated local design work is
  untouched.
- Let operator select the next Evidence Graph follow-up; semantic cache remains
  blocked unless a dedicated gate opens.

## AGENTS.md updates

Added E5 guidance to `core/evidence/AGENTS.md`: advisory wiki bridge is pure
deterministic mapping only; no compiler, local support-plane, runtime, wiki
mutation, semantic cache, GraphRAG, or runtime rail authority.

## Deferred / Follow-ups

- Add wiki-specific advisory event types only if a later event-schema PR opens
  that scope.
- Operator-selected Evidence Graph follow-up after E5.
- Semantic cache remains blocked pending a separate dedicated gate with lineage,
  admission, replay, observability, false-hit guardrails, and rollout contract.

## Discussion Thread Pass

Initial PR opening. No review threads yet.

## Fixed in Commit Mapping

No review threads existed at PR opening.

Implementation:

- PR branch implementation -> `e2b067db4`

## Merge Readiness

Not merge-ready at mapping creation.

Required before merge:

- current-head PR CI clean;
- PR body gates clean;
- CodeRabbit/Sourcery/Cubic no-actionables confirmed;
- mandatory post-open `qa-engineer-agent -> bug-hunter` pass complete;
- strict merge-readiness wrapper passes;
- review wait-window observed.
