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

Also passed after diff-coverage remediation:

```bash
rm -f .coverage coverage.xml && .venv/bin/python -m coverage run -m pytest -q tests/core/evidence/test_wiki_bridge.py && .venv/bin/python -m coverage xml -o coverage.xml && .venv/bin/diff-cover coverage.xml --compare-branch origin/main --fail-under 97 --exclude 'tests/**' --exclude '*.md' --exclude '*.yml' --exclude '*.yaml' --exclude '*.toml' --exclude '*.txt'
```

Result: `core/evidence/wiki_bridge.py` diff coverage 97.2%.

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
- Runtime upstream leakage risk: fixed by validating wiki artifact upstream IDs
  against advisory rail policy before asset/admission mapping. Evidence:
  `core/evidence/wiki_bridge.py`; regression test in
  `tests/core/evidence/test_wiki_bridge.py`.
- E1/E4 bypass risk: fixed by using `create_evidence_asset_ref` and
  `AdmissionInput`.
- Semantic cache scope drift: fixed by explicit docs/backlog deferral.
- Raw payload/secret risk: fixed by metadata safety checks and tests.
- Byte-like raw payload risk: fixed by rejecting `bytes`, `bytearray`, and
  `memoryview` before generic sequence handling. Evidence:
  `core/evidence/wiki_bridge.py`; regression tests in
  `tests/core/evidence/test_wiki_bridge.py`.
- Non-canonical public constructor risk: fixed by recomputing advisory wiki
  artifact identity inside `AdvisoryWikiArtifactRef.__init__` and rejecting
  mismatched caller-provided `artifact_id` or `idempotency_key`. Evidence:
  `core/evidence/wiki_bridge.py`; regression tests in
  `tests/core/evidence/test_wiki_bridge.py`.
- Admission target identity risk: fixed by making the admission adapter target
  the advisory `EvidenceAssetRef` identity instead of the source wiki artifact
  identity. Evidence: `core/evidence/wiki_bridge.py`; regression tests in
  `tests/core/evidence/test_wiki_bridge.py`.
- Diff-coverage regression risk: fixed by adding branch coverage for policy,
  constructor, helper type/path, metadata recursion, and artifact mapping guard
  branches in `tests/core/evidence/test_wiki_bridge.py`.
- Numeric authority-claim risk: fixed by treating truthy numeric authority
  metadata as a forbidden authority claim. Evidence:
  `core/evidence/wiki_bridge.py`; regression test in
  `tests/core/evidence/test_wiki_bridge.py`.
- Path traversal/current-directory risk: fixed by path safety checks and tests.
- URI and drive-relative path risk: fixed by rejecting URI schemes and
  drive-qualified first path segments. Evidence: `core/evidence/wiki_bridge.py`;
  regression tests in `tests/core/evidence/test_wiki_bridge.py`.
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
- `c5cd925a9` - `fix(evidence): harden wiki bridge safety checks`
- `85154507f` - `fix(evidence): enforce wiki artifact identity`
- `2c09b8a32` - `fix(evidence): target wiki admission assets`
- `b7efbfa2d` - `docs(agents): update instructions`
- `ccb5c0630` - `docs(review): map PR 1681 review threads`
- `7bc213ff4` - `test(evidence): cover wiki bridge guards`
- `cd0b8b4a1` - `docs(review): record PR 1681 coverage fix`
- `abc3c9563` - `docs(review): map CodeRabbit aggregate review`
- `1967ab477` - `fix(evidence): remove unused wiki bridge import`

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

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

- QA lane found byte-like metadata bypass; fixed in code/tests.
- Bug-hunter lane found URI/drive-relative paths, runtime upstream, and numeric
  authority-claim bypasses; fixed in code/tests.
- Codex review found that admission inputs targeted source wiki artifact
  identity instead of advisory EvidenceAssetRef identity; fixed in code/tests.
- CodeRabbit review requested canonical constructor identity enforcement; fixed
  in code/tests.
- CodeRabbit review requested a scoped AGENTS commit titled
  `docs(agents): update instructions`; fixed with that commit title.
- CodeRabbit review noted advisory serve scope is metadata-only; disposition is
  NOT-A-BUG because E5 is a pure advisory bridge and must not widen E4 serve
  policy or product runtime behavior.
- CodeRabbit review flagged mapping checkbox governance; fixed by a
  post-comment docs/governance repair before final merge-readiness.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 2c09b8a32
Evidence: `wiki_artifact_to_admission_input(...)` targets advisory `EvidenceAssetRef` identity; `tests/core/evidence/test_wiki_bridge.py` covers target ID, fingerprint, idempotency key, and upstream identity.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1681#discussion_r3195195608 -> 2c09b8a32

Disposition: FIXED
Commit: b7efbfa2d
Evidence: `core/evidence/AGENTS.md` E5 reviewer guidance was clarified in the commit titled `docs(agents): update instructions`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1681#discussion_r3195235932 -> b7efbfa2d

Disposition: FIXED
Commit: 85154507f
Evidence: `AdvisoryWikiArtifactRef.__init__` recomputes canonical identity and rejects mismatched caller-provided `artifact_id` / `idempotency_key`; `tests/core/evidence/test_wiki_bridge.py` covers both mismatches.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1681#discussion_r3195235937 -> 85154507f

Disposition: FIXED
Commit: c5cd925a9
Evidence: `core/evidence/wiki_bridge.py` rejects neutral-key runtime/canonical authority claims, URI paths, drive-relative paths, runtime evidence upstreams, and truthy numeric authority claims; `tests/core/evidence/test_wiki_bridge.py` covers the regressions.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1681#discussion_r3195235955 -> c5cd925a9

Disposition: FIXED
Commit: 11dc14dc6
Evidence: `docs/review/PR_1681_FIXED_MAPPING.md` restored the required checkboxes and normalized the artifact before thread resolution.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1681#discussion_r3195235962 -> 11dc14dc6

Disposition: NOT-A-BUG
Evidence: E5 remains a pure advisory bridge; the adapter metadata preserves `serve_scope=advisory_review_only`, the admission input now targets advisory EvidenceAssetRef identity, and product runtime serve enforcement remains outside this PR by scope.
Reason: Adding a top-level E4 serve-scope policy would widen E4 admission contracts and product-serving semantics, which is explicitly out of scope for PR-E5.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1681#discussion_r3195235953

Disposition: NOT-A-BUG
Evidence: Aggregate CodeRabbit review actionables are represented by the individual inline discussion URLs mapped above.
Reason: The review-level URL has no separate actionable beyond those inline comments; it is included for merge-readiness governance completeness.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1681#pullrequestreview-4235839249

Disposition: FIXED
Commit: 1967ab477
Evidence: `core/evidence/wiki_bridge.py` removed the unused `Any` import reported in the aggregate CodeRabbit review; focused wiki bridge tests and narrow mypy passed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1681#pullrequestreview-4236389688 -> 1967ab477

## Merge Readiness

Not merge-ready at mapping creation.

Required before merge:

- current-head PR CI clean;
- PR body gates clean;
- CodeRabbit/Sourcery/Cubic no-actionables confirmed;
- mandatory post-open `qa-engineer-agent -> bug-hunter` pass complete;
- strict merge-readiness wrapper passes;
- review wait-window observed.
