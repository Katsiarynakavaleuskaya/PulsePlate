# PR #2091 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2091
Branch: `codex/extract-legacy-insight-routes-with-creative-pilot`

## Summary

Extract direct legacy insight route ownership for `POST /insight` and
`POST /api/v1/insight` from `legacy_app.py` into
`app/routers/legacy_insight.py`. Preserve VIP guard behavior, rate-limit
metadata, monthly quota ordering, input guard behavior, transparency notice,
provider/error hygiene, and hidden OpenAPI behavior.

## Scope

- Add hidden compatibility route ownership in `app/routers/legacy_insight.py`.
- Register the family from `app/main.py` through
  `ensure_route_family_registered(...)`.
- Remove direct insight decorators from `legacy_app.py`.
- Tighten legacy growth guard tests against direct decorator and dynamic route
  reintroduction.
- Record proposal-only Creative-Code pilot evidence and route ownership docs.

## Out Of Scope

New LLM providers, RAG behavior, semantic-cache serving, prompt template changes,
new wellness claims, frontend/iOS/macOS, generated OpenAPI/client drift, and any
autonomous Creative-Code GitHub write or patch promotion.

## Implementation Commits

- `5c6d65a99` - freeze legacy insight route behavior and creative pilot gates.
- `0f047cf6e` - extract legacy insight route ownership.
- `a9c18cd9e` - block insight handlers in the legacy seam.
- `2ad600441` - record Creative-Code pilot artifact rules.
- `730e8d138` - update insight route ownership and AGENTS rules.
- `f805bc042` - centralize insight route lookup helpers.
- `1a8ace115` - harden route lookup diagnostics.
- `9eadedd5c` - prove quota exhaustion blocks provider execution.
- `0287a536a` - update insight tier evidence.
- `395230ea2` - add insight extraction premortem.
- `6cd05b751` - harden legacy insight error-envelope assertions.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/573a3fcd7a6c.json`
- Dispatch manifest:
  `artifacts/orchestration/task_packets/573a3fcd7a6c.dispatch.json`
- Required pre-open role order:
  `agent-coordinator -> backend-engineer -> architecture-specialist -> security-auditor`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] `agent-coordinator` completed pre-open.
- [x] `backend-engineer` completed pre-open.
- [x] `architecture-specialist` completed pre-open.
- [x] `security-auditor` completed pre-open.
- [x] `qa-engineer-agent` completed post-open.
- [x] `bug-hunter` completed post-open.
- [x] `security-auditor` completed post-open.
- [ ] Current-head CI complete before readiness language.
- [x] Codex Security diff scan / finding discovery complete before readiness language.
- [x] `pulseplate-pr-review` complete before readiness language.
- [ ] Strict merge-readiness checks run after final review/check cycle.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 6cd05b751
Evidence: `tests/test_legacy_insight_router.py`, `tests/test_legacy_insight_registration_bootstrap.py`; focused validation `. .venv/bin/activate && pytest -q tests/test_legacy_insight_router.py tests/test_legacy_insight_registration_bootstrap.py -p no:warnings` passed (`30` passed), and `python3 scripts/ci/check_legacy_growth_guard.py` passed.
Reason: CodeRabbit found JSON error-envelope tests called `resp.json()` without first asserting the JSON response contract; the fix adds `Content-Type: application/json` assertions before the affected JSON parsing calls and keeps route source lookup normalized through existing helpers. The parent CodeRabbit review URL is mapped to the same fix commit because the merge-readiness gate treats the review summary (`Actionable comments posted: 1`) as a separate actionable item from the inline discussion thread.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2091#discussion_r3540069383 -> 6cd05b751
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2091#pullrequestreview-4649444162 -> 6cd05b751

Disposition: FIXED
Commit: 89164cd1c
Evidence: `docs/orchestration/GOVERNED_CREATIVE_CODE_EXECUTION_CONTRACT.md`
Reason: Cubic found the Creative-Code evidence sentence overbroad: it could be
read as invalidating valid non-`patch_runs` artifact families. The contract now
limits the `patch_runs/<run-id>/` requirement to candidate-patch promotion
evidence and explicitly preserves private-pilot, spec-bridge, learning-rollup,
applied-candidate, patch-admission, and inventory artifacts as non-promotion
local evidence.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2091#discussion_r3550613909 -> 89164cd1c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2091#pullrequestreview-4661873449 -> 89164cd1c

## Implementation Evidence

Disposition: FIXED
Commit: `0f047cf6e`
Evidence: `app/routers/legacy_insight.py`, `app/main.py`, `legacy_app.py`,
`tests/test_legacy_insight_registration_bootstrap.py`,
`tests/test_legacy_insight_router.py`
Reason: Direct legacy insight route ownership moved out of `legacy_app.py` into
the router/bootstrap pattern while preserving VIP, rate-limit, quota, input
guard, transparency, error hygiene, and OpenAPI-hidden behavior.

Disposition: FIXED
Commit: `a9c18cd9e`
Evidence: `scripts/ci/check_legacy_growth_guard.py`,
`tests/test_legacy_growth_guard.py`
Reason: Direct insight route decorators and dynamic route registration are now
blocked from regrowing in `legacy_app.py`.

Disposition: FIXED
Commit: `9eadedd5c`
Evidence: `tests/test_legacy_insight_router.py`
Reason: Backend role pass found the quota-exhaustion test should explicitly
prove provider execution is not reached after monthly quota failure. The test now
fails if `_execute_insight_request` runs after quota exhaustion.

Disposition: FIXED
Commit: `0287a536a`
Evidence: `docs/contracts/PRODUCT_TIER_MAP.md`,
`docs/contracts/API_CANONICAL_MAP.md`
Reason: Architecture role pass found stale direct insight route ownership
evidence pointing at `legacy_app.py`; the docs now point to
`app/routers/legacy_insight.py` and `app/main.py` route-family bootstrap.

Disposition: FIXED
Commit: `395230ea2`
Evidence: `docs/review/PR_LEGACY_INSIGHT_ROUTE_EXTRACTION_PREMORTEM.md`
Reason: Pre-open premortem records actual-diff risk findings and closes them
with code, tests, docs, or refreshed local evidence.

Disposition: FIXED
Commit: `6cd05b751`
Evidence: `tests/test_legacy_insight_router.py`,
`tests/test_legacy_insight_registration_bootstrap.py`
Reason: Post-open CodeRabbit review and role-agent passes found missing JSON
content-type assertions on error-envelope tests plus a normalized route lookup
test-hardening gap. The PR fixed both without changing runtime route code.

## Role-Agent Evidence

### agent-coordinator

Disposition: NOT-A-BUG
Evidence: Coordinator pass found scope coherent and no route-behavior blocker.
It required the existing role order, premortem, final oracle refresh, and
pre-push gates before PR open.

### backend-engineer

Disposition: FIXED
Commit: `9eadedd5c`
Evidence: `tests/test_legacy_insight_router.py`
Reason: Backend pass found one non-blocking test hardening gap for quota/provider
ordering. The PR fixed it before opening.

### architecture-specialist

Disposition: FIXED
Commit: `0287a536a`
Evidence: `docs/contracts/PRODUCT_TIER_MAP.md`
Reason: Architecture pass found one stale ownership evidence pointer in
`PRODUCT_TIER_MAP.md`. The PR fixed it before opening.

### security-auditor

Disposition: FIXED
Evidence:
`artifacts/orchestration/experiments/results/exp-9494fb7a8ab6-current-head-395230ea2.json`,
`artifacts/orchestration/experiments/creative_context/insight_extraction_proposal/oracle_attachment.json`
Reason: Security pass found no code blocker but warned that earlier local oracle
evidence was stale. The oracle and proposal-only attachment were refreshed for
head `395230ea2ef81e1647c3f7e8640981586bc74565`.

## Post-Open Role-Agent Evidence

### agent-coordinator

Disposition: NOT-A-BUG
Evidence: Packet `artifacts/orchestration/task_packets/9c0ed0a730cf.json`
and dispatch manifest generated by
`python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/9c0ed0a730cf.json --pretty`.
Reason: Coordinator confirmed scope stays limited to legacy insight route
extraction plus governance closeout, and CodeRabbit must be fixed or
dispositioned before mapping/readiness.

### qa-engineer-agent

Disposition: FIXED
Commit: `6cd05b751`
Evidence: `tests/test_legacy_insight_router.py`,
`tests/test_legacy_insight_registration_bootstrap.py`
Reason: QA confirmed the CodeRabbit content-type finding was valid and the
mapping artifact was stale until the post-comment fix commit existed.

### bug-hunter

Disposition: FIXED
Commit: `6cd05b751`
Evidence: `tests/test_legacy_insight_router.py`,
`tests/test_legacy_insight_registration_bootstrap.py`
Reason: Bug-hunter confirmed no duplicate direct insight routes and no
quota/provider ordering regression, then identified the same test hardening and
source-route normalization fixes.

### security-auditor

Disposition: NOT-A-BUG
Evidence: `app/routers/legacy_insight.py`, `app/main.py`,
`tests/test_legacy_insight_router.py`
Reason: Security-auditor found no runtime security blocker in the extracted
route. VIP dependency, rate-limit metadata, hidden OpenAPI, input guard,
transparency check, monthly quota-before-provider, and error hygiene remain
represented in code and tests.

## Codex Security Diff Scan / Finding Discovery

Disposition: NOT-A-BUG
Evidence:
`https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2091#issuecomment-4911811764`,
`app/routers/legacy_insight.py`, `app/main.py`,
`tests/test_legacy_insight_router.py`,
`tests/test_legacy_insight_registration_bootstrap.py`
Reason: Codex Security cloud connector reported usage limits and could not run
an automated diff scan. Finding discovery was completed via readonly
security-review of the material branch diff: no medium-or-higher security
findings. VIP guard, rate-limit metadata, feature gate, AI input guard,
transparency notice, quota-before-provider ordering, OpenAPI-hidden status, and
legacy growth anti-regrowth controls remain intact. The Codex quota comment is
infrastructure-only and is not an actionable merge-gate item under
`check_pr_merge_readiness.py` actionable markers.

## pulseplate-pr-review

Disposition: FIXED
Commit: 6cd05b751
Evidence: `docs/review/PR_2091_FIXED_MAPPING.md`,
`tests/test_legacy_insight_router.py:176,206,257`,
CI merge-readiness UNMAPPED for
`https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2091#pullrequestreview-4649444162`
Reason: `pulseplate-pr-review` found no new runtime defects in the insight
route extraction. The remaining governance blocker was the unmapped parent
CodeRabbit review URL; it is now mapped to the same Content-Type fix commit as
the resolved discussion thread. Creative-Code remains proposal-only/oracle-only.

## Premortem Evidence

- Artifact: `docs/review/PR_LEGACY_INSIGHT_ROUTE_EXTRACTION_PREMORTEM.md`
- Result: `proceed with changes`
- Closure: all premortem findings are closed by code, tests, docs, or refreshed
  local evidence before PR open.

## Creative-Code Pilot Evidence

Local gitignored evidence, not committed:
`artifacts/orchestration/experiments/creative_context/insight_extraction_proposal/`

- patch run id: none
- status: `not-generated` / proposal-only
- candidate patch used: no
- promotion authority: no
- validated local artifact types:
  `creative_hypothesis_packet`,
  `creative_hypothesis_coordinator_dispatch`,
  `experiment_runner_pr_oracle_attachment`
- current-head oracle result:
  `artifacts/orchestration/experiments/results/exp-9494fb7a8ab6-current-head-395230ea2.json`
- current-head oracle fingerprint:
  `sha256:1ec9024e11151b462a46c1e0edbb81eda86c3cd2d50f8c71913c88bfa7c6b74e`

Interpretation: Creative-Code supplied proposal/routing evidence only. It did
not generate or apply a patch, did not create or write branches, did not push or
open the PR, did not resolve review threads, did not call providers, and did not
claim merge readiness.

## Experiment Runner Evidence

Artifact: `artifacts/orchestration/experiments/results/exp-9494fb7a8ab6-current-head-395230ea2.json`

Interpretation: Experiment Runner evidence is local, gitignored, and
oracle-only for current head `395230ea2ef81e1647c3f7e8640981586bc74565`. It
does not authorize patch promotion, GitHub writes, review-thread resolution,
merge-readiness claims, or cleanup of the creative pilot artifact tree.

## Validation Evidence

- `python3 scripts/orchestration/check_preflight.py --path ...` - PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- `python3 scripts/ci/check_legacy_growth_guard.py` - PASS.
- `. .venv/bin/activate && pytest -q tests/test_legacy_insight_router.py tests/test_legacy_insight_registration_bootstrap.py tests/test_legacy_growth_guard.py tests/test_insight_vip_guard_api.py tests/test_insight_error_hygiene.py -p no:warnings` - PASS (`54` passed).
- `. .venv/bin/activate && mypy app/routers/legacy_insight.py app/main.py legacy_app.py` - PASS.
- `. .venv/bin/activate && pytest -q tests/test_legacy_insight_router.py tests/test_legacy_insight_registration_bootstrap.py -p no:warnings` - PASS (`30` passed) after post-open CodeRabbit fix commit `6cd05b751`.
- `python3 -m scripts.orchestration.experiment_runner_pr_creative_context validate --artifact-type creative_hypothesis_packet --path artifacts/orchestration/experiments/creative_context/insight_extraction_proposal/hypothesis_packet.json` - PASS.
- `python3 -m scripts.orchestration.experiment_runner_pr_creative_context validate --artifact-type creative_hypothesis_coordinator_dispatch --path artifacts/orchestration/experiments/creative_context/insight_extraction_proposal/coordinator_dispatch.json` - PASS.
- `python3 -m scripts.orchestration.experiment_runner_pr_creative_context validate --artifact-type experiment_runner_pr_oracle_attachment --path artifacts/orchestration/experiments/creative_context/insight_extraction_proposal/oracle_attachment.json` - PASS.
- `make validate-changed` - PASS.
- `pre-commit run --all-files` - PASS.
- Pre-push hook - PASS, including `pip-audit`, backend tests, full-repo Bandit,
  and Docker build test.
- `git diff --check` - PASS.

## Local Verification Exception

Local `make verify` was not run. This follows the repository hard gate for this
checkout; full/heavy verification remains GitHub current-head CI.

## Merge Readiness

- [x] Pre-open role order completed.
- [x] Current local narrow bundle completed for PR-open head `395230ea2`.
- [x] Pre-open premortem completed with findings closed.
- [x] Current-head Experiment Runner oracle-only evidence refreshed.
- [x] Post-open `qa-engineer-agent -> bug-hunter -> security-auditor` role pass complete.
- [x] CodeRabbit content-type actionable fixed in commit `6cd05b751`.
- [x] CodeRabbit parent review URL mapped to `6cd05b751`.
- [x] Codex Security diff scan / finding discovery complete for the material diff
  (Codex cloud quota unavailable; readonly security-review found no medium+ issues).
- [x] `pulseplate-pr-review` complete.
- [ ] Current-head CI complete for latest PR head.
- [x] CodeRabbit, Sourcery, and Cubic actionables checked and dispositioned.
- [ ] Strict merge-readiness wrapper passes with auth.
