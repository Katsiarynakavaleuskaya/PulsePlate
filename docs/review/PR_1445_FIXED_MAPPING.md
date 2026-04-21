# PR #1445 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:79-82`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact is rebuilt from live review truth for the clean-room `origin/main`
restart of PR #1445. The canonical current code-fix commit is `b97d4c15e`,
which preserves the `/metrics` auth lane on top of current `main`, restores the
late-bootstrap route contract without `legacy_app` request-path imports, and
drops the stale dependency/docs carryover drift from the old branch head.
Follow-up test-harness commit `dea9de69a` keeps legacy pytest `/metrics` probes
on the real auth path by auto-injecting the deterministic test API key instead
of relying on a global bypass.
Follow-up security-hardening commit `be2c68076` removes the weak developer-mode
fallback in `validate_app_api_key(...)` so `/metrics` fails closed when
`API_KEY` is unset outside the explicit pytest-scoped bypass path.

## Fixed in Commit Mapping

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1445_FIXED_MAPPING.md`; `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1445#discussion_r3102736762`
Reason: This Sourcery review body is a generated summary shell around the single actionable inline metrics-bypass finding dispositioned immediately below.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1445#pullrequestreview-4131505785

Disposition: FIXED
Commit: b97d4c15e
Evidence: `app/bootstrap/metrics.py:50-72`; `app/AGENTS.md:110-119`; `tests/test_metrics.py:21-39`; `tests/test_metrics.py:764-807`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1445#discussion_r3102736762 -> b97d4c15e

Disposition: FIXED
Commit: b97d4c15e
Evidence: `app/bootstrap/metrics.py:50-72`; `app/routers/api_key.py:46-75`; `tests/test_metrics.py:269-329`; `tests/test_metrics.py:753-833` <!-- pragma: allowlist secret -->
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1445#discussion_r3102740429 -> b97d4c15e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1445#discussion_r3102774098 -> b97d4c15e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1445#discussion_r3102779019 -> b97d4c15e

Disposition: NOT-A-BUG
Evidence: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1445#discussion_r3102740429`; `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1445#discussion_r3102774098`; `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1445#discussion_r3102779019`
Reason: These bot review submissions are aggregate wrappers for the DI/auth-runtime findings dispositioned above and add no separate unresolved obligation on the rebuilt branch.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1445#pullrequestreview-4131553263
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1445#pullrequestreview-4131559979

Disposition: FIXED
Commit: b97d4c15e
Evidence: `app/bootstrap/metrics.py:58-71`; `app/AGENTS.md:117-119`; `tests/test_metrics.py:775-807`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1445#discussion_r3107439328 -> b97d4c15e

Disposition: NOT-A-BUG
Evidence: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1445#discussion_r3107439328`
Reason: This review shell only summarizes the pytest-scoped bypass hardening thread dispositioned immediately above.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1445#pullrequestreview-4136489304

Disposition: FIXED
Commit: dea9de69a
Evidence: `git diff --name-only origin/main...dea9de69a` now limits the rebuilt PR delta to `.secrets.baseline`, `app/AGENTS.md`, `app/bootstrap/metrics.py`, `app/routers/api_key.py`, `conftest.py`, `tests/_client.py`, `tests/conftest.py`, `tests/test_app_main_import.py`, `tests/test_metrics.py`, and this canonical mapping artifact, removing the prior stale mapping/audit/dependency carryover from scope.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1445#discussion_r3107442735 -> dea9de69a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1445#pullrequestreview-4136502221 -> dea9de69a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1445#discussion_r3111979921 -> dea9de69a

Disposition: NOT-A-BUG
Evidence: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1445#discussion_r3107442735`; `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1445#discussion_r3111979921`
Reason: These bot review bodies are summary wrappers for the stale-artifact and stale-audit-anchor issues dispositioned immediately above.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1445#pullrequestreview-4136491644
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1445#pullrequestreview-4141527107

Disposition: FIXED
Commit: be2c68076
Evidence: `app/routers/api_key.py:51-66`; `tests/test_business_router.py:247-322`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1445#discussion_r3120330101 -> be2c68076

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Current-head CI is green for PR branch head
  Evidence: current-head GitHub checks after push.
- [ ] Required checks complete (no pending jobs)
  Evidence: current-head GitHub checks after push.
- [ ] All review threads resolved on GitHub after disposition updates
  Evidence: `gh api graphql` review-thread snapshot before merge.
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: this artifact plus current PR timeline after push.
- [ ] Pre-commit green on latest pushed head
  Evidence: local `pre-commit run --all-files` on rebuilt branch head.
- [ ] `make verify` green on latest pushed head
  Evidence: local `make verify` on rebuilt branch head.

## Deferred / Follow-ups

- post-push mandatory `qa-engineer-agent -> bug-hunter` review cycle still required before any merge-ready claim
- stale PR body metadata and current-head SHA references must be rewritten to match the rebuilt branch before merge readiness is re-checked
