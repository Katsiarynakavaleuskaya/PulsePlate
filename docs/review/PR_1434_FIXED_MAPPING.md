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
Commit: 16e7def15
Evidence: `app/schemas/intervention.py:13`; `app/schemas/intervention.py:41`; `app/services/intervention_trigger_engine.py:30`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1434#discussion_r3094956544 -> 16e7def15

Disposition: FIXED
Commit: b8ac9122e
Evidence: `docs/security/GHSA-mj87-hwqh-73pj-python-multipart.md:25`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1434#discussion_r3094979105 -> b8ac9122e

Disposition: NOT-A-BUG
Evidence: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1434#discussion_r3094956544`
Reason: the Sourcery review summary does not add a distinct actionable beyond the inline localization-key comment already dispositioned separately above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1434#pullrequestreview-4122860200

Disposition: FIXED
Commit: 16e7def15
Evidence: `app/services/intervention_trigger_engine.py:10`; `app/services/intervention_trigger_engine.py:22`; `app/services/intervention_trigger_engine.py:36`; `app/services/intervention_trigger_engine.py:50`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1434#discussion_r3094994770 -> 16e7def15

Disposition: FIXED
Commit: b8ac9122e
Evidence: `docs/security/GHSA-mj87-hwqh-73pj-python-multipart.md:25`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1434#discussion_r3094994781 -> b8ac9122e

Disposition: NOT-A-BUG
Evidence: `frontend/src/api/openapi.json:2832`; `frontend/src/api/openapi.json:2852`; `frontend/src/api/openapi.json:2872`
Reason: `recommended_surface`, `trigger_reason`, and `why_now` are enum-constrained in the generated OpenAPI schema, so empty-string values are already rejected without adding separate `minLength` markers.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1434#discussion_r3094994784

Disposition: FIXED
Commit: 16e7def15
Evidence: `tests/fixtures/dependency_security_schema.json:14`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1434#discussion_r3094994796 -> 16e7def15

Disposition: FIXED
Commit: 16e7def15
Evidence: `tests/test_pro_premium_contract_parity.py:78`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1434#discussion_r3094994831 -> 16e7def15

Disposition: NOT-A-BUG
Evidence: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1434#discussion_r3094994770`; `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1434#discussion_r3094994781`; `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1434#discussion_r3094994784`; `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1434#discussion_r3094994796`; `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1434#discussion_r3094994831`
Reason: the CodeRabbit review summary adds no separate actionable beyond the inline comments already dispositioned above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1434#pullrequestreview-4122911691

Disposition: FIXED
Commit: b8ac9122e
Evidence: `app/routers/premium_week.py:27`; `app/routers/premium_week.py:318`; `tests/test_pro_premium_contract_parity.py:122`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1434#discussion_r3096531941 -> b8ac9122e

Disposition: FIXED
Commit: b8ac9122e
Evidence: `docs/security/GHSA-mj87-hwqh-73pj-python-multipart.md:25`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1434#discussion_r3096531949 -> b8ac9122e

Disposition: NOT-A-BUG
Evidence: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1434#discussion_r3096531941`; `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1434#discussion_r3096531949`
Reason: the Cubic review summary contains no additional actionable beyond the two inline comments mapped immediately above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1434#pullrequestreview-4124598249

## Merge Readiness

- [ ] Current-head CI is green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] `make verify` green
Notes: Local validation on branch head `b8ac9122e` is intentionally scoped to this PR surface only: `python3 scripts/orchestration/check_preflight.py`, `python3 scripts/orchestration/check_agent_consistency.py`, `make typecheck`, and `.venv/bin/python -m pytest -q tests/test_intervention_trigger_engine.py tests/test_bmi_calculate_endpoint.py tests/test_pro_premium_contract_parity.py tests/test_install_locked_python_requirements.py`. Full `make verify` was not run in this loop.
<!-- markdownlint-enable MD034 -->
