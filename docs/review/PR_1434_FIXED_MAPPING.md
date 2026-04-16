<!-- markdownlint-disable MD034 -->
# PR #1434 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Latest actionable review comments are dispositioned below. If new comments arrive,
record them here before resolving threads on GitHub.

## Fixed in Commit Mapping

Disposition: NOT-A-BUG
Evidence: `legacy_app.py:4088`; `legacy_app.py:4161`
Reason: the WHO-targets fallback path already clamps `kcal_daily` before building the `next_best_action`, so the reported unclamped handoff is not present on the current branch head.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1434#discussion_r3094956539

Disposition: FIXED
Commit: b8ac9122e
Evidence: `app/routers/premium_week.py:27`; `app/routers/premium_week.py:318`; `tests/test_pro_premium_contract_parity.py:122`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1434#discussion_r3096531941 -> b8ac9122e

Disposition: FIXED
Commit: b8ac9122e
Evidence: `docs/security/GHSA-mj87-hwqh-73pj-python-multipart.md:25`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1434#discussion_r3096531949 -> b8ac9122e

## Merge Readiness

- [ ] Current-head CI is green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] `make verify` green
Notes: Local validation on branch head `b8ac9122e` is intentionally scoped to this PR surface only: `python3 scripts/orchestration/check_preflight.py`, `python3 scripts/orchestration/check_agent_consistency.py`, `make typecheck`, and `.venv/bin/python -m pytest -q tests/test_intervention_trigger_engine.py tests/test_bmi_calculate_endpoint.py tests/test_pro_premium_contract_parity.py tests/test_install_locked_python_requirements.py`. Full `make verify` was not run in this loop.
<!-- markdownlint-enable MD034 -->
