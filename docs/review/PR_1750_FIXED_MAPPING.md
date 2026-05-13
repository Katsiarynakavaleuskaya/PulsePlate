<!-- markdownlint-disable MD013 MD034 -->
# PR #1750 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1750
Branch: `codex/main-pr15-preference-notes-ci-hotfix`
Title: `fix(food-data): restore PR15 CI coverage`
Implementing commits:
- `e7a6bbd13ef1f6865dcc85fd57caec9d466dada7` - restore PR15 CI coverage and close xdist/notes-guard risk.
- `147f6c9918e5a713f7499968937866f15d920544` - fix contrastive negation after bot review.
- `77f0583a3c6142f134bc8061af70208893e39f8d` - harden review-mapping evidence.

## Scope

Main CI recovery for PR15 preference-to-recipe mapping governance. This PR
keeps the lane file-only and contract-only: no runtime, OpenAPI, DB, provider,
network, ingest, Cloudflare, or production infra behavior changes.

## Coordinator Evidence

- Preflight: `python3 scripts/orchestration/check_preflight.py` -> PASS.
- Agent consistency:
  `python3 scripts/orchestration/check_agent_consistency.py` -> PASS.
- Pre-open bootstrap packet:
  `artifacts/orchestration/task_packets/main_pr15_ci_hotfix_role_chain.json`
  with task packet id `b1d6315d09c6`.
- Post-open bootstrap packet:
  `artifacts/orchestration/task_packets/pr1750_post_open_review.json`
  with task packet id `499e233d32e2`.
- Role order executed:
  `agent-coordinator -> architecture-specialist -> security-auditor -> backend-engineer -> qa-engineer-agent -> bug-hunter`.

## Premortem / Role Review Findings

### Xdist false confidence on PR15 tests

Disposition: FIXED
Commit: e7a6bbd13ef1f6865dcc85fd57caec9d466dada7
Evidence:
- `$VENV_PYTHON -m pytest -q -n 4 --dist=loadscope tests/test_food_source_preference_recipe_mapping.py`
  -> PASS.
- Focused module coverage for `core/food_sources/preference_recipe_mapping.py`
  reached 99.83% with no missed statements.

### Diff-cover regression from uncovered PR15 validation branches

Disposition: FIXED
Commit: e7a6bbd13ef1f6865dcc85fd57caec9d466dada7
Evidence:
- `tests/test_food_source_preference_recipe_mapping.py` covers top-level schema
  drift, mapping row drift, PR14 review ordering, invalid JSON loading, and
  note-guard edge cases.
- `core/food_sources/preference_recipe_mapping.py` removed unreachable duplicate
  PR11 checks that were already enforced by exact expected-domain and
  source-gap order contracts.

### Notes guard false-green after contrastive negation

Disposition: FIXED
Commit: e7a6bbd13ef1f6865dcc85fd57caec9d466dada7
Evidence:
- `core/food_sources/preference_recipe_mapping.py` stops treating a leading
  negation as protective after contrastive wording such as `but`, `however`,
  or `yet`.
- `tests/test_food_source_preference_recipe_mapping.py` rejects
  `no api calls or downloads allowed but source use allowed`.

### Security review: no fail-open shortcuts

Disposition: FIXED
Commit: e7a6bbd13ef1f6865dcc85fd57caec9d466dada7
Evidence:
- No `nosec`, `type: ignore`, skip, xfail, public-source fallback, or
  coverage pragma was added.
- CLI subprocess tests now include timeouts.
- `pre-commit run --all-files` -> PASS.

### Bot review: preserve direct negation after contrastive clauses

Disposition: FIXED
Commit: 147f6c9918e5a713f7499968937866f15d920544
Evidence:
- `core/food_sources/preference_recipe_mapping.py` now evaluates negation
  against the suffix after the last contrastive connector instead of
  discarding direct negation.
- `tests/test_food_source_preference_recipe_mapping.py` covers safe
  `but no ... allowed` phrasing plus unsafe `but source use allowed`.

### Bot review: mapping artifact evidence portability

Disposition: FIXED
Commit: 77f0583a3c6142f134bc8061af70208893e39f8d
Evidence:
- This artifact uses `$VENV_PYTHON` instead of local absolute interpreter paths
  in validation evidence.
- This artifact points contrastive-negation mappings at the valid current-branch
  commit `147f6c9918e5a713f7499968937866f15d920544`.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Bot findings are mapped below. New bot or human findings must be added with
exact `FIXED`, `NOT-A-BUG`, or `DEFERRED` thread dispositions before merge
readiness is claimed.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 147f6c9918e5a713f7499968937866f15d920544
Evidence: `core/food_sources/preference_recipe_mapping.py` and `tests/test_food_source_preference_recipe_mapping.py` fix and cover contrastive negation.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1750#discussion_r3237633346 -> 147f6c9918e5a713f7499968937866f15d920544
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1750#discussion_r3237635615 -> 147f6c9918e5a713f7499968937866f15d920544
Disposition: FIXED
Commit: 77f0583a3c6142f134bc8061af70208893e39f8d
Evidence: `docs/review/PR_1750_FIXED_MAPPING.md` uses portable `$VENV_PYTHON`, removes stale no-actionable wording, and maps valid current-branch SHAs.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1750#discussion_r3237656706 -> 77f0583a3c6142f134bc8061af70208893e39f8d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1750#discussion_r3237659595 -> 77f0583a3c6142f134bc8061af70208893e39f8d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1750#discussion_r3237659599 -> 77f0583a3c6142f134bc8061af70208893e39f8d

## Local Validation Evidence

- `python3 scripts/orchestration/check_preflight.py` -> PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` -> PASS.
- `$VENV_PYTHON -m pytest -q tests/test_food_source_preference_recipe_mapping.py`
  -> PASS.
- `$VENV_PYTHON -m pytest -q -n 4 --dist=loadscope tests/test_food_source_preference_recipe_mapping.py`
  -> PASS.
- Focused coverage for `core/food_sources/preference_recipe_mapping.py` ->
  99.83%, no missed statements.
- `pre-commit run --all-files` -> PASS.
- `VENV_PYTHON=$VENV_PYTHON make validate-changed`
  -> PASS.
- Push hook -> PASS, including changed-file mypy, pip-audit, pre-push backend
  tests, full-repo Bandit, and Docker build test.

Plain `make validate-changed` in this isolated worktree failed before test
execution because the target selected system `python3`, which lacked
`fastapi`. The same target passed with explicit `VENV_PYTHON` pointing to the
repo root virtualenv.

## Security Notes

This PR does not introduce network, runtime, DB, provider, OpenAPI, ingest, or
production infra behavior. PR15 remains file-only governance validation.

## Risks / Rollback

Risk is limited to PR15 governance validation strictness. Rollback by reverting
this PR; no runtime data path is affected.
