# PR #1375 — Fixed in Commit Mapping (SoT)

## Discussion Thread Pass

- [x] Discussion-thread pass initialized for PR-open state (no actionable review threads yet; rerun after new review activity)
- [x] Fixed in commit mapping initialized

Bot and human review threads must be dispositioned below when actionable comments appear; resolve conversations on GitHub only after mapping per `AGENTS.md`.

## Fixed in Commit Mapping

No actionable human or bot review threads at PR open.

Add new review comments below using canonical dispositions:
- `FIXED` with commit SHA + evidence
- `NOT-A-BUG` with reason + evidence
- `DEFERRED` with backlog link

## Merge Readiness

- [ ] Current-head CI green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates

### Scope Notes

- Primary hotfix commit: `d4eb976e7` — restore legacy-schema-safe `food_store` compatibility for missing `foods.nutrition_confidence`
- Merge-gate unblock commits:
  - `cb533ed72` — remove redundant casts blocking repo `make verify`
  - `b0a4bc2a9` — preserve literal narrowing for push-hook mypy on changed files
- Sanctioned scope expansion was limited to:
  - `core/judgment.py`
  - `core/judgment_eval.py`
  - `core/creative_research.py`

### Local Verification

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `pre-commit run --all-files`
- `make verify`
- mandatory final `bug-hunter` pass completed with no blocking findings

## Deferred / Follow-ups

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-food-store-legacy-schema-cache-follow-through`
