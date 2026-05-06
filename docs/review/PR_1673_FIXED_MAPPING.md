# PR 1673 Fixed Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1673
Branch: `codex/evidence-promotion-ledger-replay`
Title: `feat(evidence): add promotion ledger and replay scaffold`

## Scope

PR-E3 adds deterministic Evidence Graph promotion ledger contracts and a pure
dry-run replay scaffold over PR-E2 eval events.

Out of scope: runtime routes, OpenAPI, DB migrations, providers, eval runners,
semantic cache, GraphRAG, advisory wiki authority, dashboards, online eval,
judge calibration, goldens, billing/auth/compliance changes.

## Coordinator Bootstrap

- Pre-open packet: `b95c4f512a1a`
- Post-open review packet: `edd7a12bccc3`
- Declared pre-open role order:
  `agent-coordinator -> architecture-specialist -> rag-systems-agent -> data-scientist-agent -> security-auditor -> qa-engineer-agent -> bug-hunter -> cursor-specialist-agent`
- Mandatory post-open lane:
  `qa-engineer-agent -> bug-hunter`

## Local Validation

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `.venv/bin/python -m pytest -q tests/core/evidence/test_promotion_ledger.py tests/core/evidence/test_replay.py tests/core/evidence/test_events.py tests/core/evidence/test_assets.py tests/core/evidence/test_fingerprints.py`
- PASS: `.venv/bin/python -m mypy --no-incremental --cache-dir=/dev/null core/evidence tests/core/evidence/test_promotion_ledger.py tests/core/evidence/test_replay.py`
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS: pre-push hook set: changed-files mypy, pip-audit, backend pre-push tests, full-repo bandit, docker build test

Full local `make verify` was intentionally not run under the
operator-approved machine-heavy exception. Current-head GitHub CI parity and
strict merge-readiness remain required before merge.

## Premortem Actions

| Risk | Disposition | Evidence |
| --- | --- | --- |
| Hidden writer/store | FIXED | `core/evidence/replay.py` returns dry-run summaries only; replay tests assert mutation-free behavior. |
| Duplicate `core/knowledge/promotion.py` | FIXED | E3 lives under `core/evidence`; import guards block runtime/knowledge-adjacent side doors. |
| Invalid/degraded evidence promoted | FIXED | Promote/supersede require valid source event and valid ledger status. |
| Nondeterministic replay | FIXED | Replay sorts entries deterministically and tests stable output regardless of input order. |
| Weak idempotency | FIXED | Replay dedupes identical idempotency keys and reports collisions as conflict. |
| Raw prompt/health/secret metadata | FIXED | Ledger metadata safety rejects prompt/response/user-health/secret/path-like payloads. |
| Semantic cache/GraphRAG side door | FIXED | AST import guards block cache, semantic-cache, GraphRAG, wiki/support-plane, runtime, DB, provider, and eval-runner imports. |

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- No actionable review comments

## Sidecar Review Findings

- Coordinator sidecar finding: validate source event id before upstream normalization -> `d57a5b5af`
  - Evidence: `core/evidence/promotion_ledger.py` validates `source_event.event_id` and `source_event.fingerprint` before lineage normalization.
- Coordinator sidecar finding: factory did not accept `ledger_entry_id` passthrough used by deterministic-id tests -> `d57a5b5af`
  - Evidence: `create_promotion_ledger_entry(...)` accepts optional `ledger_entry_id` and passes it to `PromotionLedgerEntry`.
- Bug-hunter sidecar finding: existing ledger conflicts are silently overwritten -> ab3bd46f8
  - Disposition: FIXED
  - Evidence: `core/evidence/replay.py` builds existing replay indexes with fail-closed duplicate idempotency and active-scope checks; `tests/core/evidence/test_replay.py` covers both corrupt baseline cases.
- Bug-hunter sidecar finding: supersede can apply without an active target -> ab3bd46f8
  - Disposition: FIXED
  - Evidence: `core/evidence/replay.py` reports candidate orphan supersession as `conflict` and rejects orphan existing supersession; `tests/core/evidence/test_replay.py` covers both paths.
- Bug-hunter sidecar finding: promotion creation does not enforce eval rail boundary -> ab3bd46f8
  - Disposition: FIXED
  - Evidence: `core/evidence/promotion_ledger.py` rejects non-`eval` source events; `tests/core/evidence/test_promotion_ledger.py` covers runtime rail rejection.
- Bug-hunter sidecar finding: metadata leakage guard misses raw payload values -> ab3bd46f8
  - Disposition: FIXED
  - Evidence: `core/evidence/promotion_ledger.py` scans value strings for raw prompt/response/user-health payload markers and rejects bytes/bytearray; `tests/core/evidence/test_promotion_ledger.py` covers these cases.
- QA sidecar finding: replay drops accepted reject/defer ledger entries -> ab3bd46f8
  - Disposition: FIXED
  - Evidence: `core/evidence/replay.py` appends accepted reject/defer entries to `applied_entry_ids`; `tests/core/evidence/test_replay.py` asserts preservation.
- QA sidecar finding: existing supersession state is order-derived, not ledger-derived -> ab3bd46f8
  - Disposition: FIXED
  - Evidence: `core/evidence/replay.py` sorts promote before supersede and resolves current active entries through supersession semantics; `tests/core/evidence/test_replay.py` covers an existing promote -> supersede -> candidate supersede chain.
- QA sidecar finding: bytes-like metadata is silently normalized as JSON arrays -> ab3bd46f8
  - Disposition: FIXED
  - Evidence: `core/evidence/promotion_ledger.py` rejects bytes/bytearray before generic sequence handling; `tests/core/evidence/test_promotion_ledger.py` covers bytes metadata rejection.
- QA sidecar finding: fixed mapping artifact is not in canonical Phase2 format -> ab3bd46f8
  - Disposition: FIXED
  - Evidence: this artifact now includes `## Discussion Thread Pass` and canonical no-thread mapping language.

## Merge Readiness

Not merge-ready at mapping creation time.

Required before merge:

- current-head CI parity clean;
- CodeRabbit/Sourcery/Cubic no-actionables;
- all review threads resolved with disposition evidence;
- strict merge-readiness wrapper with auth;
- mandatory review wait-window after latest bot/review activity.
