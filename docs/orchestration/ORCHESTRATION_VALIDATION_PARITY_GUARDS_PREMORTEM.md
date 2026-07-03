# Orchestration Validation Parity Guards Premortem

Frame: it is 6 months from now and this guardrail PR failed because future
review-governance PRs trusted stale or partial validation evidence.

## Summary

Plan: add shared negative validation fixtures, privileged review-surface routing
guards, stricter fixed-mapping validation, and a non-runtime route-family
migration proof contract.

Decision: proceed with changes already included in this diff.

## Most likely failure

Privileged routing drifts again because one consumer keeps a local matcher while
another uses the canonical sync-policy helper.

Closure: `scripts/orchestration/skill_router.py` consumes
`privileged_review_surface_matches(...)` from
`scripts/orchestration/bootstrap_sync_policy.py`; the same fixture matrix is
used by `tests/test_bootstrap_sync_policy.py`, `tests/test_skill_router.py`, and
`tests/test_task_bootstrap.py`.

## Most dangerous failure

Review mapping accepts a plausible-looking proof with the wrong disposition
shape, letting a thread appear handled without a commit, evidence, or backlog
reference that matches the disposition.

Closure: `scripts/orchestration/review_mapping_artifact.py` now validates
FIXED, NOT-A-BUG, and DEFERRED proof blocks separately; regression coverage is
in `tests/test_review_mapping_artifact.py`.

## Hidden assumption

Schema constraints and Python validators will stay aligned simply because both
exist in the repo.

Closure: `tests/fixtures/orchestration/validation_negative_cases.json` feeds
`tests/test_validation_parity.py`, which checks the same negative classes
against schema fragments and Python validators without adding dependencies.

## Pre-merge Checklist

- Focused pytest for validation parity, bootstrap sync policy, skill router,
  task bootstrap, review mapping artifact, and route-family proof passes.
- `python3 scripts/orchestration/check_preflight.py` passes, with only local
  private-index/analyze-mode warnings if present.
- `python3 scripts/orchestration/check_agent_consistency.py` passes.
- `make validate-changed` result is recorded, including any branch-diff selector
  limitation before commit.
- `pre-commit run --all-files` passes after formatter changes are committed.
- No product runtime, OpenAPI, provider, frontend, iOS/macOS, workflow dispatch,
  semantic-cache, or route-registration files are touched.
