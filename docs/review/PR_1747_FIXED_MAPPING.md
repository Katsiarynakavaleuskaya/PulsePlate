# PR #1747 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747
Branch: `codex/food-data-preference-recipe-mapping-contract-pr15`
Head at open: `44f42ee9f`

## Scope

Food Data PR15 adds the preference-to-recipe mapping contract as a
governance/file-only lane. It does not authorize ingest, scraping, provider
API calls, recipe downloads, DB writes, cache authority, runtime source
authority, PostgreSQL cutover, OpenAPI/runtime behavior, or provider
integration.

## Coordinator Evidence

- Preflight: `python3 scripts/orchestration/check_preflight.py` -> PASS
- Agent consistency:
  `python3 scripts/orchestration/check_agent_consistency.py` -> PASS
- Pre-open bootstrap packet:
  `artifacts/orchestration/task_packets/21a58a9d82bc`
- Declared role order:
  `agent-coordinator -> security-auditor -> data-scientist-agent -> backend-engineer -> qa-engineer-agent -> bug-hunter -> dev-operator`
- Native subagent spawn note: local agent thread limit blocked new native
  subagent threads, so the pre-open role review was performed manually against
  the coordinator packet and repository instructions.

## Premortem Dispositions

### Recipe/preference/LLM text becomes nutrition authority

Disposition: FIXED
Commit: `44f42ee9f`
Evidence:
- `docs/architecture/FOOD_DATA_PREFERENCE_RECIPE_MAPPING_PR15_2026-05-13.json`
  keeps `recipe_text_authority_allowed`,
  `user_preference_text_authority_allowed`, `llm_output_authority_allowed`,
  and `nutrition_authority_allowed` false.
- `core/food_sources/preference_recipe_mapping.py` validates the authority
  flags fail-closed.
- `tests/test_food_source_preference_recipe_mapping.py` covers unsafe flag
  rejection and authority contradiction rejection.

### PR11/PR14 handoff drift

Disposition: FIXED
Commit: `44f42ee9f`
Evidence:
- `core/food_sources/preference_recipe_mapping.py` requires PR11
  `preference_menu_planning.next_action == preference_recipe_mapping_contract`.
- `core/food_sources/preference_recipe_mapping.py` requires PR14
  `next_recommended_lane == preference_recipe_mapping_contract`.
- `tests/test_food_source_preference_recipe_mapping.py` covers PR11 and PR14
  drift failures.

### PR15 treated as ingest/runtime prep

Disposition: FIXED
Commit: `44f42ee9f`
Evidence:
- `docs/orchestration/FOOD_DATA_PREFERENCE_RECIPE_MAPPING_PR15_PACKET_2026-05-13.md`
  declares the lane file-only and governance-only.
- `scripts/food_source_preference_recipe_mapping.py` only reads local files
  and returns deterministic validation output.
- `tests/test_food_source_preference_recipe_mapping.py` covers no-network,
  no-ingest, no-runtime-authority invariants.

## Local Validation Evidence

- `python3 scripts/orchestration/check_preflight.py` -> PASS
- `python3 scripts/orchestration/check_agent_consistency.py` -> PASS
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest tests/test_food_source_preference_recipe_mapping.py -q`
  -> 45 passed
- Adjacent food-source governance regression pytest for PR11, PR12, PR13,
  PR14, catalog, and onboarding -> PASS
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_repo_policy_guards.py`
  -> 14 passed
- Targeted mypy for the new module, CLI, and tests -> PASS
- CLI JSON smoke for PR15 artifact -> `success: true`
- `pre-commit run --all-files` -> PASS
- `make validate-changed VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python`
  -> PASS
- `git push` pre-push hooks -> PASS, including backend tests, full-repo
  bandit, and docker build test

Operator/coordinator note: full `make verify` was started and then stopped
after operator clarification that this file-only governance PR should use
changed/focused validation unless the coordinator explicitly requires a
runtime-wide full run. No merge-readiness claim relies on that interrupted
heavy run.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

No review threads were present at PR open. Post-open CodeRabbit, Codex
Security, QA, bug-hunter, bot, and human findings must be added here as one of
`FIXED`, `NOT-A-BUG`, or `DEFERRED` with evidence before merge readiness is
claimed.

The formal `## Fixed in Commit Mapping` section below uses the repo-required
`- No actionable review comments` marker because there are no GitHub
review-thread URLs to map. Local CodeRabbit CLI review issues are recorded in
this `## Discussion Thread Pass` section with dispositions and proof.

### CodeRabbit Finding: Missing Fixed Mapping Checkboxes

Disposition: FIXED
Commit: `f49a4255d`
Evidence:
- `docs/review/PR_1747_FIXED_MAPPING.md` now includes the required artifact
  markers `- [x] Discussion-thread pass completed` and
  `- [x] Fixed in commit mapping completed` under `## Discussion Thread Pass`.
- `scripts/orchestration/review_mapping_artifact.py` defines the exact required
  checkbox markers.

### CodeRabbit Finding: Target PR Branch Should Be `vscode-changes`

Disposition: NOT-A-BUG
Evidence:
- `gh pr view 1747 --repo Katsiarynakavaleuskaya/PulsePlate --json headRefName`
  returns `codex/food-data-preference-recipe-mapping-contract-pr15`.
- `docs/roadmap/BACKLOG_LEDGER.md` intentionally names
  `codex/food-data-preference-recipe-mapping-contract-pr15`, matching the live
  PR head branch.
Reason: CodeRabbit's suggested `vscode-changes` branch does not match the
actual PR #1747 source branch and would make the ledger inaccurate.

### CodeRabbit Finding: Packet Uses Ambiguous Fixed Mapping Wording

Disposition: FIXED
Commit: `c33da5764`
Evidence:
- `docs/orchestration/FOOD_DATA_PREFERENCE_RECIPE_MAPPING_PR15_PACKET_2026-05-13.md`
  now names `docs/review/PR_1747_FIXED_MAPPING.md` explicitly.

### CodeRabbit Finding: Fixed Mapping Section Ambiguous With CLI Findings

Disposition: FIXED
Commit: `30a3a41fa`
Evidence:
- `docs/review/PR_1747_FIXED_MAPPING.md` now explicitly distinguishes
  GitHub review-thread URL mappings from local CodeRabbit CLI dispositions.
- `scripts/orchestration/review_mapping_artifact.py` validation still passes
  with the repo-required `- No actionable review comments` marker.

## Fixed in Commit Mapping

- No actionable review comments

## Merge Readiness

Not claimed. Required before merge readiness:

- post-open task bootstrap
- mandatory `qa-engineer-agent -> bug-hunter` pass
- CodeRabbit review pass
- Codex Security diff-scoped pass
- current-head PR checks inspection
- review-thread and bot-comment dispositions
- final strict merge-readiness wrapper
