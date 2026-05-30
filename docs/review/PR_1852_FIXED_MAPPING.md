# PR 1852 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: ec72bdf7c
Evidence: `scripts/orchestration/mvp_evidence_snapshot.py` — added `policy_version` validation in `_read_latest_snapshot_line`, added `retention_days <= 0` guard in `cleanup_expired_snapshots`, wrapped `stat()` and `open()` in `try/except OSError` in `read_latest_snapshot_line`; `scripts/orchestration/experiment_slack_socket_bridge.py` — narrowed `except Exception` to `(ValueError, OSError, TypeError)` in `render_mvp_evidence_summary`; `docs/review/PREMORTEM_SLACK_MVP_EVIDENCE_LEDGER.md` — fixed typo `atomously` → `atomically`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1852#pullrequestreview-4395156071 -> ec72bdf7c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1852#discussion_r3328567935 -> ec72bdf7c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1852#discussion_r3328567937 -> ec72bdf7c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1852#discussion_r3328567939 -> ec72bdf7c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1852#pullrequestreview-4395159172 -> ec72bdf7c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1852#discussion_r3328571594 -> ec72bdf7c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1852#discussion_r3328571596 -> ec72bdf7c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1852#discussion_r3328571598 -> ec72bdf7c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1852#pullrequestreview-4395162487 -> ec72bdf7c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1852#discussion_r3328574636 -> ec72bdf7c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1852#discussion_r3328574637 -> ec72bdf7c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1852#pullrequestreview-4395177150 -> ec72bdf7c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1852#discussion_r3328591979 -> ec72bdf7c

Disposition: FIXED
Commit: TBD
Evidence: `scripts/orchestration/mvp_evidence_snapshot.py` — temp file cleanup now matches `.tmp.{pid}` pattern via `".tmp" in entry.suffixes` instead of `entry.suffix == ".tmp"`; `tests/test_mvp_evidence_snapshot.py` — added `test_cleanup_removes_stale_temp_files_with_pid_suffix` and updated `test_render_mvp_evidence_summary_fallback_on_read_exception` to prove exception path was exercised with `nonlocal called` flag

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1852#discussion_r3328593729 -> TBD

Disposition: NOT-A-BUG
Reason: `routePath` and `authState` are frontend-controlled enum-like strings from the MVP observability contract. The snapshot is aggregate-only (event name counts) and values are preserved as opaque identifiers for operator diagnostics. Server-side enum enforcement would add coupling to frontend routing internals without security benefit for this aggregate-only, sanitized surface.
Evidence: `scripts/orchestration/mvp_evidence_snapshot.py:ALLOWED_PAYLOAD_KEYS` defines the allowlist; payload values are never used for authorization or sensitive decisions; snapshot schema is explicitly aggregate-only with no PII.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1852#discussion_r3328574635

## Agent Findings Summary

| Finding | Role | Disposition | Evidence |
|---------|------|-------------|----------|
| Bare `Exception` in bridge snapshot read | sourcery-ai | FIXED | Commit `ec72bdf7c` |
| Missing `retention_days` validation | sourcery-ai | FIXED | Commit `ec72bdf7c` |
| Typo `atomously` → `atomically` | sourcery-ai | FIXED | Commit `ec72bdf7c` |
| Typo `atomously` → `atomically` | coderabbitai | FIXED | Commit `ec72bdf7c` |
| Filesystem race in `read_latest_snapshot_line` | coderabbitai | FIXED | Commit `ec72bdf7c` |
| Unknown `policy_version` not rejected | coderabbitai | FIXED | Commit `ec72bdf7c` |
| Test can't prove exception path exercised | coderabbitai | FIXED | Commit `TBD` |
| Broad `except Exception` masks guard failures | cubic-dev-ai | FIXED | Commit `ec72bdf7c` |
| `p.stat().st_mtime` OSError outside try block | cubic-dev-ai | FIXED | Commit `ec72bdf7c` |
| Stale temp cleanup won't match `.tmp.{pid}` | cubic-dev-ai | FIXED | Commit `TBD` |
| `routePath`/`authState` arbitrary strings | cubic-dev-ai | NOT-A-BUG | Aggregate-only, frontend-controlled contract |

## Merge Readiness

- [x] Pre-open agents: agent-coordinator, cursor-specialist-agent, security-auditor, architecture-specialist
- [x] Post-open agents: qa-engineer-agent, bug-hunter
- [x] `make validate-changed` passed
- [x] `make test-fast` passed
- [x] `pre-commit run --all-files` passed
- [x] `python3 scripts/orchestration/check_preflight.py` passed
- [x] `python3 scripts/orchestration/check_agent_consistency.py` passed
- [x] PR review dry-run report generated (`/tmp/pulseplate_pr_review_context.json`)

### Experiment Runner evidence

- Co-authored-by trailer included in commits where runner materially contributed.
- No runner-mutated paths in this PR (operator-authored snapshot/bridge/test/docs changes only).

---
