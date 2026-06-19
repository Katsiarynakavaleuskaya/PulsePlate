# PR 1996 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1996

Branch: `test/security-auth-tier-bola-contract-pack`

## Summary

This PR adds a narrow tests/docs API auth, tier, and BOLA contract pack. It does
not change runtime auth, OpenAPI, database, endpoint implementation, client, or
billing behavior.

## Scope

- Add `tests/security/_api_authz_contracts.py` as the test-only contract
  registry for sensitive API route auth/tier/ownership/OpenAPI exposure.
- Add contract tests for live-route registration, OpenAPI exposure,
  dependency-guard drift, object ownership policy, and foreign-object status
  evidence.
- Add focused BOLA/idempotency regressions for nutrition meal-log, nutrition
  day-close, and RAG feedback owner derivation.
- Refactor the existing PRO/VIP route dependency guard to reuse shared
  dependency-flattening helpers.
- Update security docs, tests registration guidance, and the auth-principal
  follow-up ledger.

## Out Of Scope

Runtime auth implementation changes, endpoint behavior changes, OpenAPI/client
changes, DB migrations, frontend/iOS changes, and hiding any discovered
authorization bypass inside this contract-pack PR.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/829553ac142b.json`
- Post-open packet: `artifacts/orchestration/task_packets/31612eecd993.json`
- Pre-open role order executed:
  `agent-coordinator -> security-auditor -> backend-engineer -> qa-engineer-agent -> bug-hunter -> architecture-specialist`
- Post-open role order executed:
  `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor`
- Starter: direct repo startup with `check_preflight.py --mode execute` and
  `task_bootstrap.py`; packet creation was treated as provenance only, not role
  execution.

## Local Validation

- PASS: `python3 scripts/orchestration/check_preflight.py --mode execute --primary security-auditor --reviewer agent-coordinator --path tests/security --path tests/test_pro_vip_route_dependency_guard.py --path docs/security --path tests/AGENTS.md --path docs/roadmap/BACKLOG_LEDGER.md`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `. .venv/bin/activate && python -m pytest -q tests/security/test_api_auth_tier_contract_pack.py tests/security/test_api_bola_contract_pack.py tests/test_pro_vip_route_dependency_guard.py`
- PASS: broader auth/tier/BOLA regression bundle covering paid-route guards,
  session cookie auth, Bayes adherence, nutrition log, feedback, payment
  reconciliation, subscription activation, OpenAPI namespace, partner routes,
  legacy exports, BMI PRO API, and business router tests.
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS: `make typecheck`
- PASS: `make test-fast`
- PASS: `make diff-cov`

## Known Gate State

- `make verify` is NOT passing locally because `make lint` fails on inherited
  `origin/main` `legacy_app.py` import-order/unused-import violations that are
  unchanged by this branch. Representative raw failures:
  `legacy_app.py:100:1: E402 module level import not at top of file` and
  `legacy_app.py:101:1: F401 'core.log_retention.DataClass' imported but unused`.
- Current-head GitHub CI remains the authoritative heavy signal before merge.
- This PR must not be called green, ready, or mergeable while current-head CI,
  bot review, strict merge-readiness, and the mandatory wait-window are pending.

## Experiment Runner Evidence

- Artifact:
  `artifacts/orchestration/experiments/results/exp-332646e053dc.json`
- Status: infrastructure-blocked/rejected in isolated temp checkout because
  `fastapi` was unavailable there; this is not treated as a local oracle PASS.
- Local repo oracle commands listed above passed in the real repo environment.
- Attribution: commit `ab190e860` includes
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` because
  the oracle attempt materially shaped admission and commit decisions.

## Post-Open Review Evidence

- `qa-engineer-agent`: FIXED valid governance findings in this mapping/docs
  update. The findings were missing security-doc `file:line` anchors and missing
  canonical `docs/review/PR_1996_FIXED_MAPPING.md` artifact.
- `bug-hunter`: FIXED false-green contract-test findings in `048d7235e`.
  Evidence: `tests/security/test_api_auth_tier_contract_pack.py:105`,
  `tests/security/test_api_auth_tier_contract_pack.py:119`, and
  `tests/test_pro_vip_route_dependency_guard.py:95`.
- `security-auditor`: FIXED stale-local-head/governance finding by pushing the
  post-review fix series; FIXED the remaining module/qualname-safe dependency
  assertion in `2dcc8c759`. Evidence:
  `tests/test_pro_vip_route_dependency_guard.py:114`.
- Codex Security diff scan / finding discovery: PASS / no reportable findings.
  Report directory:
  `/tmp/codex-security-scans/BMI-App_2025_clean/dfffec476_20260619T121118Z`.
  The scan reviewed 12/12 diff-scoped files and used an explicit
  `git diff --name-only` worklist fallback because the plugin default generator
  excludes tests/docs paths.
- `pulseplate-pr-review`: NOT-A-BUG for the advisory large-diff note.
  Evidence: `/tmp/pulseplate_pr1996_review_context.json`,
  `python3 scripts/orchestration/pr_review_report.py --context /tmp/pulseplate_pr1996_review_context.json --format markdown`,
  focused security pytest, `make validate-changed`, `pre-commit run --all-files`,
  and pre-push hooks passed. Reason: the diff is large because the route
  registry is explicit, but scope remains tests/docs-only with no runtime files
  changed.
- CodeRabbit: FIXED three actionable review findings. Evidence:
  `tests/security/test_api_auth_tier_contract_pack.py:21`,
  `tests/security/test_api_auth_tier_contract_pack.py:29`,
  `tests/security/test_api_bola_contract_pack.py:29`, and
  `tests/security/test_api_bola_contract_pack.py:152`.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

GitHub review threads have not been resolved without disposition evidence. This
pass records the current post-open state and must be repeated after any new bot
or human review activity.

## Fixed in Commit Mapping

Disposition: FIXED

Commit: 048d7235e

Evidence: `tests/security/test_api_auth_tier_contract_pack.py:21` and
`tests/security/test_api_auth_tier_contract_pack.py:29` replace the narrow
hard-coded object-id heuristic with generic path-parameter detection and
foreign-object `_id` classification. Focused pytest and `make validate-changed`
passed after the fix.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1996#discussion_r3442325743 -> 048d7235e

Disposition: FIXED

Commit: 8fbe52ade

Evidence: `tests/security/test_api_bola_contract_pack.py:29` registers explicit
PRO credentials with `ALLOW_ANONYMOUS_API_KEYS=false`, preserving the real PRO
tier path in the BOLA idempotency tests. Evidence:
`tests/security/test_api_bola_contract_pack.py:152` asserts JSON content type
before parsing the feedback response. Focused pytest, `make validate-changed`,
and `pre-commit run --all-files` passed after the fix.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1996#discussion_r3442325753 -> 8fbe52ade
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1996#discussion_r3442325757 -> 8fbe52ade
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1996#pullrequestreview-4532649016 -> 8fbe52ade

## Deferred / Follow-Ups

- First-class principal/user-auth mapping remains tracked in
  `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-first-class-auth-principal-mapping`.
- `pulseplate-pr-review` large-diff advisory does not require a backlog item
  because this PR already documents the narrow tests/docs scope and passed the
  targeted local gates.

## Merge Readiness

Status: NOT READY while fresh current-head CI for `8fbe52ade`, bot review,
strict merge-readiness, and the mandatory wait-window remain pending.

Required before merge:

- Fresh current-head PR CI parity after head `8fbe52ade`.
- No unresolved actionable human or bot review comments.
- Strict merge-readiness with auth passes.
- Mandatory wait-window after latest review/bot activity.
