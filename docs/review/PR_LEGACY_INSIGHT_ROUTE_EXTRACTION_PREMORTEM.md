Title: Legacy Insight Route Extraction Premortem
Mode: `pr-premortem`
Skill: `pulseplate-premortem-risk-review`
Branch: `codex/extract-legacy-insight-routes-with-creative-pilot`
Packet: `artifacts/orchestration/task_packets/573a3fcd7a6c.json`
Base: `bc19c7af87c8246101a0b1be1954747fec1c6355`
Head reviewed: `0287a536af4c8bfb73d9340acb8d074981ce0800`

## Summary

Plan: extract direct legacy insight route ownership for `POST /insight` and
`POST /api/v1/insight` from `legacy_app.py` into
`app/routers/legacy_insight.py`, while preserving VIP, quota, rate-limit, input
guard, transparency, error hygiene, OpenAPI hiding, and the existing
`insight_application_service` orchestration path.

Frame: it is six months from now and this route extraction failed because it
silently changed an AI security boundary, misrepresented Creative-Code pilot
authority, or left stale ownership evidence that future work trusted.

## Findings

| ID | Failure mode | Disposition | Evidence |
| --- | --- | --- | --- |
| PM-INSIGHT-001 | Extracted routes accidentally weaken VIP/rate-limit/OpenAPI-hidden metadata. | FIXED | `app/routers/legacy_insight.py`; `app/main.py` route-family registration; `tests/test_legacy_insight_registration_bootstrap.py`; `tests/test_legacy_insight_router.py`; focused pytest passed. |
| PM-INSIGHT-002 | Unsafe input, transparency failure, or quota exhaustion reaches the provider path. | FIXED | `tests/test_legacy_insight_router.py` covers unsafe-input-before-quota, transparency-before-quota, quota 429, and provider-not-reached on quota exhaustion; focused pytest passed. |
| PM-INSIGHT-003 | Creative-Code `no mutation` is misread as either no proposal at all or permission to apply an untrusted patch. | FIXED | `docs/orchestration/GOVERNED_CREATIVE_CODE_EXECUTION_CONTRACT.md` records artifact-only evidence rules; local proposal packet `artifacts/orchestration/experiments/creative_context/insight_extraction_proposal/` validates with `mutate_code=false`, `generate_patch=false`, `push=false`, and `open_pr=false`. |
| PM-INSIGHT-004 | Stale route ownership docs keep pointing future agents back to `legacy_app.py`. | FIXED | `docs/contracts/API_CANONICAL_MAP.md` and `docs/contracts/PRODUCT_TIER_MAP.md` point direct insight route ownership to `app/routers/legacy_insight.py` and bootstrap registration in `app/main.py`. |
| PM-INSIGHT-005 | Local oracle or Creative-Code evidence is stale and cited against the wrong head SHA. | FIXED | Current-head oracle result `artifacts/orchestration/experiments/results/exp-9494fb7a8ab6-current-head-0287a536a.json` is accepted; refreshed `oracle_attachment.json` records head `0287a536af4c8bfb73d9340acb8d074981ce0800` and fingerprint `sha256:6c6b167f3220bc0dc5903354b204a2450b329e635b3a8650614a479a2c67ab97`. |
| PM-INSIGHT-006 | Direct insight decorators or dynamic route registration regrow in `legacy_app.py`. | FIXED | `scripts/ci/check_legacy_growth_guard.py`; `tests/test_legacy_growth_guard.py` block direct decorators, `add_api_route`, aliased app wrappers, `include_router`, and dynamic `app.routers.legacy_insight` imports. |

## Synthesis

Most likely failure: stale governance evidence or docs drift would cause a
future agent to route direct insight work back through `legacy_app.py`.

Most dangerous failure: route extraction could bypass VIP/quota/input guard
ordering and allow provider execution for unsafe or over-quota requests.

Hidden assumption: proposal-only Creative-Code evidence is useful only if the
artifact makes its lack of mutation authority explicit and the PR body does not
treat it as accepted patch-run proof.

## Revised Plan

- Keep production implementation manual and reviewed; do not widen Creative-Code
  mutable candidate surfaces in this route-ownership PR.
- Cite Creative-Code as `not-generated` / proposal-only evidence unless a valid
  accepted `patch_runs/<run-id>/result.json` exists.
- Keep route ownership in `app/routers/legacy_insight.py` and route-family
  bootstrap in `app/main.py`; keep orchestration in the existing service/core
  seams.
- Preserve direct legacy callable patch seams through module attribute access so
  existing tests can still verify behavior without import-time rebinding drift.

## Pre-Open Checklist

- [x] Coordinator, backend, architecture, and security role passes completed.
- [x] Current-head focused tests passed for insight routes, bootstrap, growth
  guard, VIP guard, and error hygiene.
- [x] Current-head Experiment Runner oracle-only evidence refreshed.
- [x] Proposal-only Creative-Code packet refreshed and validated.
- [x] Premortem findings closed as FIXED with evidence above.
- [ ] `make validate-changed` and `pre-commit run --all-files` must pass before
  push / PR open.

## Decision

`proceed with changes`.

All premortem findings identified before PR open are closed by code, tests,
docs, or refreshed local evidence. This is not a merge-readiness claim; PR
readiness still depends on local narrow gates, current-head CI, post-open review
passes, fixed mapping, and strict merge-readiness governance.
