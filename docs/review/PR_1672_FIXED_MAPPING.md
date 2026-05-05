# PR #1672 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1672
Branch: `codex/eval-event-schema`
Title: `feat(evidence): add unified eval event schema`

## Summary

PR #1672 adds the PR-E2 unified eval event schema for Evidence Graph Runtime.
It normalizes current eval/RAG/RAGAS artifact families into immutable,
deterministic event contracts without changing product runtime behavior.

## Scope

- `core/evidence/events.py`
- `core/evidence/__init__.py`
- `core/evidence/AGENTS.md`
- `docs/orchestration/contracts/EVIDENCE_EVENT_SCHEMA.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `tests/core/evidence/test_events.py`
- `docs/review/PR_1672_FIXED_MAPPING.md`

## Role Order

- [x] Declared role order preserved: `agent-coordinator -> rag-systems-agent -> architecture-specialist -> data-scientist-agent -> security-auditor -> qa-engineer-agent -> bug-hunter -> cursor-specialist-agent`
- [x] Pre-open coordinator packet: `e3e17d4a6ba2`
- [x] Post-open coordinator packet: `92032fa9f0e0`
- [x] Mandatory post-open review lane included: `qa-engineer-agent -> bug-hunter`

## Discussion Thread Pass

- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed

No human, CodeRabbit, Sourcery, or Cubic review threads had been triaged at the
time this initial mapping artifact was created. Keep these checkboxes open
until post-open review comments are inspected and dispositioned.

## Fixed in Commit Mapping

No actionable review threads are mapped yet. Add each resolved actionable thread
with disposition-specific proof after the comment exists and after the fixing
commit, if any, lands.

## Premortem Summary

Frame: It is 48 hours after PR-E2 merged. Evidence Graph work became harder to
trust or review. Why?

- E2 became a second eval runner: mitigated by schema-only code, no eval-runner
  imports, and a forbidden-import test.
- E2 mixed product runtime and advisory rails: mitigated by explicit rail enum,
  cross-rail asset-ref rejection, and scoped `core/evidence/AGENTS.md`.
- E2 stored raw prompt/user-health/secret payloads: mitigated by fail-closed
  metadata key/string checks and tests.
- E2 created nondeterministic event IDs: mitigated by canonical event identity
  payload and stable serialization tests with fixed timestamps.
- E2 duplicated #1666/#1667 fixes: mitigated by treating sidecar symlink
  hardening and eval-validity validation as baseline.
- E2 invented semantic cache/GraphRAG/wiki scope: mitigated by contract docs,
  scoped AGENTS rules, and forbidden import tests.
- E2 could not represent existing gate artifacts: mitigated by event types for
  RAG gate run/report/metric/decision, RAGAS report, validity sidecars, and item
  metadata/statistics.
- E2 bypassed E1 primitives: mitigated by using `EvidenceAssetRef`,
  `fingerprint_payload`, `validate_fingerprint`, policy version validation, and
  upstream-id normalization.

## Validation

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: pre-open `task_bootstrap.py` -> packet `e3e17d4a6ba2`
- PASS: post-open `task_bootstrap.py` -> packet `92032fa9f0e0`
- PASS: `.venv/bin/python -m pytest -q tests/core/evidence/test_events.py tests/core/evidence/test_assets.py tests/core/evidence/test_fingerprints.py` -> `52 passed`
- PASS: `make validate-changed` after commit -> selected `tests/core/evidence/test_events.py`, `26 passed`
- PASS: `pre-commit run --all-files`
- PASS: targeted pre-push mypy hook after the `FrozenJsonValue` alias fix
- PASS: `git push -u origin codex/eval-event-schema` pre-push hooks, including changed-file mypy, pip-audit, backend tests, full-repo Bandit, and Docker build test

LOCAL GAP: full local `make verify` was intentionally not run under the
operator-approved machine-heavy exception. Current-head GitHub CI parity and
the strict merge-readiness wrapper are required before any merge-readiness
claim.

## Merge Readiness

- [ ] Current-head PR CI green
- [ ] CodeRabbit no actionable comments
- [ ] Sourcery no actionable comments
- [ ] Cubic no actionable comments
- [ ] `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 1672` passes
- [ ] `python3 scripts/orchestration/check_merge_ready.py --require-auth --pr-number 1672 --repo Katsiarynakavaleuskaya/PulsePlate` passes
- [ ] Mandatory review cycle / wait-window elapsed

## Deferred / Follow-ups

- PR-E3: promotion ledger + replay consuming normalized eval events.
- Concrete adapter PRs may normalize runner outputs into the event schema after
  PR-E2 lands.
- Semantic cache remains blocked until its dedicated gate opens with lineage,
  admission, replay, reliability, and security contracts.
