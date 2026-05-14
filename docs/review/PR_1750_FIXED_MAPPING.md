<!-- markdownlint-disable MD013 MD034 -->
# PR #1750 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1750
Branch: `codex/main-pr15-preference-notes-ci-hotfix`
Title: `fix(food-data): restore PR15 CI coverage`
Implementing commits:
- `e7a6bbd13ef1f6865dcc85fd57caec9d466dada7` - restore PR15 CI coverage and close xdist/notes-guard risk.
- `147f6c9918e5a713f7499968937866f15d920544` - fix contrastive negation after bot review.
- `77f0583a35e3c871e2348d8b70a5a39420168b7c` - harden review-mapping evidence.
- `ee0b63e28ccfd14f9585a08821e260fd0b957bae` - preserve controlled PR11 handoff errors and deduplicate CLI timeouts.
- `07728343bc053d858608a5c4eb77f289fc90ba18` - cover additional contrastive note boundaries.
- `c51a52165e48575f601d20af9ae060783b4eb690` - correct bot mapping SHAs and add contrastive-boundary evidence.
- `c5088d47ae5cd4de7fa30776dabded924e6b22f1` - cover `whereas` contrastive note boundary.
- `62f8b3041026fc8e5729a1776d34d03ff3d6ff06` - cover `while` and `despite` contrastive note boundaries.
- `5a5b36b76974f94fc4cc7e9b206d98442a4d70c5` - cover conditional and exception note boundaries.

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
Commit: 77f0583a35e3c871e2348d8b70a5a39420168b7c
Evidence:
- This artifact uses `$VENV_PYTHON` instead of local absolute interpreter paths
  in validation evidence.
- This artifact points contrastive-negation mappings at the valid current-branch
  commit `147f6c9918e5a713f7499968937866f15d920544`.

### Bot review: preserve controlled PR11 handoff errors

Disposition: FIXED
Commit: ee0b63e28ccfd14f9585a08821e260fd0b957bae
Evidence:
- `core/food_sources/preference_recipe_mapping.py` now routes required PR11
  domain/source-gap lookups through `_require_existing_entry(...)`, which
  raises `PreferenceRecipeMappingError` via `_mapping_error(...)` instead of a
  raw `KeyError`.
- `tests/test_food_source_preference_recipe_mapping.py` covers the controlled
  missing-entry helper path.
- CLI subprocess tests use `_CLI_TIMEOUT_SECONDS` instead of duplicated
  timeout literals.

### Bot review: include common contrastive note boundaries

Disposition: FIXED
Commit: c5088d47ae5cd4de7fa30776dabded924e6b22f1
Evidence:
- `core/food_sources/preference_recipe_mapping.py` treats `although`,
  `though`, `even though`, and `whereas` as contrastive boundaries when
  evaluating whether a prior negation still protects a later approval phrase.
- `tests/test_food_source_preference_recipe_mapping.py` rejects
  `although`/`though`/`even though`/`whereas` source-use approval after an
  earlier negated allow-list phrase.

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
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1750#pullrequestreview-4285583509 -> 147f6c9918e5a713f7499968937866f15d920544
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1750#discussion_r3237633346 -> 147f6c9918e5a713f7499968937866f15d920544
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1750#pullrequestreview-4285586614 -> 147f6c9918e5a713f7499968937866f15d920544
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1750#discussion_r3237635615 -> 147f6c9918e5a713f7499968937866f15d920544
Disposition: FIXED
Commit: 77f0583a35e3c871e2348d8b70a5a39420168b7c
Evidence: `docs/review/PR_1750_FIXED_MAPPING.md` uses portable `$VENV_PYTHON`, removes stale no-actionable wording, and maps valid current-branch SHAs.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1750#pullrequestreview-4285614100 -> 77f0583a35e3c871e2348d8b70a5a39420168b7c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1750#discussion_r3237656706 -> 77f0583a35e3c871e2348d8b70a5a39420168b7c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1750#pullrequestreview-4285617716 -> 77f0583a35e3c871e2348d8b70a5a39420168b7c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1750#discussion_r3237659595 -> 77f0583a35e3c871e2348d8b70a5a39420168b7c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1750#discussion_r3237659599 -> 77f0583a35e3c871e2348d8b70a5a39420168b7c
Disposition: FIXED
Commit: ee0b63e28ccfd14f9585a08821e260fd0b957bae
Evidence: `core/food_sources/preference_recipe_mapping.py` preserves controlled PR11 handoff errors; `tests/test_food_source_preference_recipe_mapping.py` covers the helper path and centralizes CLI timeout configuration.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1750#pullrequestreview-4285580137 -> ee0b63e28ccfd14f9585a08821e260fd0b957bae
Disposition: FIXED
Commit: c5088d47ae5cd4de7fa30776dabded924e6b22f1
Evidence: `core/food_sources/preference_recipe_mapping.py` extends contrastive note boundaries; `tests/test_food_source_preference_recipe_mapping.py` covers `although`, `though`, `even though`, and `whereas` source-use approvals after a negated allow-list phrase.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1750#discussion_r3237747300 -> c5088d47ae5cd4de7fa30776dabded924e6b22f1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1750#discussion_r3237907082 -> c5088d47ae5cd4de7fa30776dabded924e6b22f1
Disposition: FIXED
Commit: 62f8b3041026fc8e5729a1776d34d03ff3d6ff06
Evidence: `core/food_sources/preference_recipe_mapping.py` extends contrastive note boundaries; `tests/test_food_source_preference_recipe_mapping.py` covers `while` and `despite` source-use approvals after a negated allow-list phrase.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1750#discussion_r3239533528 -> 62f8b3041026fc8e5729a1776d34d03ff3d6ff06
Disposition: FIXED
Commit: 5a5b36b76974f94fc4cc7e9b206d98442a4d70c5
Evidence: `core/food_sources/preference_recipe_mapping.py` extends note clause boundaries; `tests/test_food_source_preference_recipe_mapping.py` covers `unless`, `even if`, `except`, and `notwithstanding` source-use approvals after a negated allow-list phrase.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1750#discussion_r3239620011 -> 5a5b36b76974f94fc4cc7e9b206d98442a4d70c5
Disposition: FIXED
Commit: c51a52165e48575f601d20af9ae060783b4eb690
Evidence: `docs/review/PR_1750_FIXED_MAPPING.md` now uses the reachable full SHA `77f0583a35e3c871e2348d8b70a5a39420168b7c` and records current-branch mapping evidence after the stale bot review cycle.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1750#discussion_r3237747291 -> c51a52165e48575f601d20af9ae060783b4eb690
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1750#discussion_r3237747295 -> c51a52165e48575f601d20af9ae060783b4eb690
Disposition: NOT-A-BUG
Evidence: current head `7e79821135e61c38312b61403b063151fe66f908` contains `ee0b63e28ccfd14f9585a08821e260fd0b957bae`; `git merge-base --is-ancestor ee0b63e28ccfd14f9585a08821e260fd0b957bae HEAD` -> exit 0.
Reason: The bot reviewed stale submitted head `2cf640be2136a49e4d4b9f266e9951ebbdd5cafa`; the current PR head contains the mapped PR11 handoff fix commit.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1750#discussion_r3237830683
Disposition: NOT-A-BUG
Evidence: current branch head contains the listed proof commits; `git merge-base --is-ancestor e7a6bbd13ef1f6865dcc85fd57caec9d466dada7 HEAD`, `git merge-base --is-ancestor 147f6c9918e5a713f7499968937866f15d920544 HEAD`, and `git merge-base --is-ancestor ee0b63e28ccfd14f9585a08821e260fd0b957bae HEAD` all exit 0 locally.
Reason: The bot reviewed a virtual squashed head; the canonical PR branch history contains the mapped proof commits and the merge-readiness gate passes on current head.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1750#discussion_r3237907086
Disposition: NOT-A-BUG
Evidence: current branch head contains the listed proof commits and the latest mapping follow-up commit; `git merge-base --is-ancestor e7a6bbd13ef1f6865dcc85fd57caec9d466dada7 HEAD`, `git merge-base --is-ancestor 62f8b3041026fc8e5729a1776d34d03ff3d6ff06 HEAD`, and `git merge-base --is-ancestor 5a5b36b76974f94fc4cc7e9b206d98442a4d70c5 HEAD` all exit 0 locally.
Reason: The bot reviewed a virtual squashed head; the canonical PR branch history contains the mapped proof commits and current-head CI merge-readiness gates pass on the branch history.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1750#discussion_r3239620006
Disposition: NOT-A-BUG
Evidence: current branch head contains the listed proof commits; `git merge-base --is-ancestor e7a6bbd13ef1f6865dcc85fd57caec9d466dada7 HEAD`, `git merge-base --is-ancestor 147f6c9918e5a713f7499968937866f15d920544 HEAD`, `git merge-base --is-ancestor 77f0583a35e3c871e2348d8b70a5a39420168b7c HEAD`, `git merge-base --is-ancestor ee0b63e28ccfd14f9585a08821e260fd0b957bae HEAD`, `git merge-base --is-ancestor c5088d47ae5cd4de7fa30776dabded924e6b22f1 HEAD`, `git merge-base --is-ancestor 62f8b3041026fc8e5729a1776d34d03ff3d6ff06 HEAD`, and `git merge-base --is-ancestor 5a5b36b76974f94fc4cc7e9b206d98442a4d70c5 HEAD` all exit 0 locally.
Reason: The bot reviewed non-branch virtual commit `be55ffec16ca99581f7c7d653f152fdae516c745`, which is not a local branch commit object. The canonical PR branch history and current-head checks use branch head `dadbdaa7321fe588efc32d3f5e407259878714de`, where the mapped proof commits are reachable.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1750#discussion_r3239715557

## Local Validation Evidence

- `python3 scripts/orchestration/check_preflight.py` -> PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` -> PASS.
- `$VENV_PYTHON -m pytest -q tests/test_food_source_preference_recipe_mapping.py`
  -> PASS.
- `$VENV_PYTHON -m pytest -q tests/test_food_source_preference_recipe_mapping.py::test_preference_recipe_mapping_rejects_contrastive_approval_after_negation`
  -> PASS.
- `$VENV_PYTHON -m pytest -q -n 4 --dist=loadscope tests/test_food_source_preference_recipe_mapping.py`
  -> PASS.
- Focused coverage for `core/food_sources/preference_recipe_mapping.py` ->
  99.84%, no missed statements.
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
