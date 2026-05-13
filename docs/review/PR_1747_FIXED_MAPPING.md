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
Commit: 44f42ee9f
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
Commit: 44f42ee9f
Evidence:
- `core/food_sources/preference_recipe_mapping.py` requires PR11
  `preference_menu_planning.next_action == preference_recipe_mapping_contract`.
- `core/food_sources/preference_recipe_mapping.py` requires PR14
  `next_recommended_lane == preference_recipe_mapping_contract`.
- `tests/test_food_source_preference_recipe_mapping.py` covers PR11 and PR14
  drift failures.

### PR15 treated as ingest/runtime prep

Disposition: FIXED
Commit: 44f42ee9f
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
- `$VENV_PYTHON -m pytest tests/test_food_source_preference_recipe_mapping.py -q`
  -> PASS after the latest review-fix cycle
- Adjacent food-source governance regression pytest for PR11, PR12, PR13,
  PR14, catalog, and onboarding -> PASS
- `$VENV_PYTHON -m pytest -q tests/test_repo_policy_guards.py`
  -> 14 passed
- Targeted mypy for the new module, CLI, and tests -> PASS
- CLI JSON smoke for PR15 artifact -> `success: true`
- `pre-commit run --all-files` -> PASS
- `make validate-changed VENV_PYTHON=$VENV_PYTHON`
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
Commit: f49a4255d
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
Commit: c33da5764
Evidence:
- `docs/orchestration/FOOD_DATA_PREFERENCE_RECIPE_MAPPING_PR15_PACKET_2026-05-13.md`
  now names `docs/review/PR_1747_FIXED_MAPPING.md` explicitly.

### CodeRabbit Finding: Fixed Mapping Section Ambiguous With CLI Findings

Disposition: FIXED
Commit: dcda77a8f
Evidence:
- `docs/review/PR_1747_FIXED_MAPPING.md` now explicitly distinguishes
  GitHub review-thread URL mappings from local CodeRabbit CLI dispositions.
- `scripts/orchestration/review_mapping_artifact.py` validation still passes
  with the repo-required `- No actionable review comments` marker.

### Codex Security Diff-Scoped Scan

Disposition: NOT-A-BUG
Evidence:
- Report:
  `/tmp/codex-security-scans/food-data-preference-recipe-mapping-contract-pr15/08bd8000a_20260513T133038Z/report.md`
- Result: 0 reportable findings.
- Scope: PR #1747 diff at head `08bd8000a`.
Reason: The diff adds a local file-only validator/CLI and governance artifacts;
no runtime route, OpenAPI behavior, DB migration, cache writer, provider
integration, network fetcher, or secret-bearing path was added.

### QA/Bug-Hunter Advisory: Large Diff Review Risk

Disposition: NOT-A-BUG
Evidence:
- `gh pr diff 1747 --repo Katsiarynakavaleuskaya/PulsePlate --name-only`
  returns only the expected 8 PR15 files.
- `git diff --shortstat origin/main...HEAD` reports 8 files changed, with the
  volume concentrated in the new typed validator, deterministic tests, and
  governance artifacts.
- Focused PR15 pytest covers 133 deterministic cases, including malformed
  artifacts, unsafe flags, CLI success/failure, no-network/no-ingest/no-runtime
  authority invariants, and PR11/PR14 handoff drift.
Reason: The advisory large-diff warning is acknowledged, but splitting would
separate the governance artifact, validator, CLI, and tests that prove the same
contract. No unrelated runtime or provider surface is present in the live PR
diff.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 3c83a498b
Evidence: `docs/roadmap/BACKLOG_LEDGER.md` splits the PR15 status into a readable active-lane line plus merged-PR summary line.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#pullrequestreview-4281710415

Disposition: FIXED
Commit: 0df4b0788
Evidence: `core/food_sources/preference_recipe_mapping.py` derives approval/allowed note variants from `BLOCKED_METHODS`, and `tests/test_food_source_preference_recipe_mapping.py` rejects approval/allowed forms for every blocked method plus common natural-language variants.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#discussion_r3234315912
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#discussion_r3234605982
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#pullrequestreview-4281710541
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#pullrequestreview-4282056114

Disposition: FIXED
Commit: f7899072d
Evidence: `docs/review/PR_1747_FIXED_MAPPING.md` uses portable `$VENV_PYTHON` forms for validation evidence and maps FIXED proofs to commits present in current PR head history.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#discussion_r3234407783
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#pullrequestreview-4281820759
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#pullrequestreview-4281925247
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#pullrequestreview-4282020905

Disposition: FIXED
Commit: 30a3a41fa
Evidence: `docs/review/PR_1747_FIXED_MAPPING.md` distinguishes local CodeRabbit CLI dispositions from GitHub review-thread mappings; this section now records concrete bot review/comment URLs instead of the no-actionable marker.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#discussion_r3234420143
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#pullrequestreview-4281837137

Disposition: FIXED
Commit: 0df4b0788
Evidence: `core/food_sources/preference_recipe_mapping.py` validates PR14 `evidence_policy` and `final_gate_decision` in addition to `next_recommended_lane`; `tests/test_food_source_preference_recipe_mapping.py` rejects PR14 no-ingest handoff drift.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#discussion_r3234854631

Disposition: FIXED
Commit: 0df4b0788
Evidence: `core/food_sources/preference_recipe_mapping.py` validates PR11 preference coverage, gap, and authority decisions before accepting the handoff; `tests/test_food_source_preference_recipe_mapping.py` rejects PR11 authority-decision drift.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#discussion_r3234854638

Disposition: FIXED
Commit: 0df4b0788
Evidence: `core/food_sources/preference_recipe_mapping.py` derives forbidden note approvals from every `BLOCKED_METHODS` token; `tests/test_food_source_preference_recipe_mapping.py` rejects `approved`, `is approved`, `allowed`, and `is allowed` forms for every blocked method.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#discussion_r3234854624

Disposition: FIXED
Commit: aea4017cd
Evidence: `core/food_sources/preference_recipe_mapping.py` rejects present-tense `approve`/`approves` note approvals while allowing explicit negated present-tense notes; `tests/test_food_source_preference_recipe_mapping.py` covers both forms.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#discussion_r3235087844

Disposition: FIXED
Commit: aea4017cd
Evidence: `core/food_sources/preference_recipe_mapping.py` rechecks PR14 review-row statuses, cache/display decisions, rollback requirement, and allowed role for direct `RecipeDishCorpusGovernance` handoffs; `tests/test_food_source_preference_recipe_mapping.py` rejects approved/drifted PR14 review rows.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#discussion_r3235087859

Disposition: FIXED
Commit: f7899072d
Evidence: `docs/review/PR_1747_FIXED_MAPPING.md` remaps the affected FIXED proof entries to current-head ancestor commits and records this mapping fix in the artifact itself.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#discussion_r3234854627

Disposition: NOT-A-BUG
Evidence: Live PR head before this follow-up was `b44172feadd8ba19bb0c319fa5f75d66d7191a2c`; local ancestry check `git merge-base --is-ancestor 0df4b0788 b44172feadd8ba19bb0c319fa5f75d66d7191a2c` passed, and `gh pr view 1747 --json headRefOid` reported that same live head.
Reason: The review comment cited `4b2759e080a321f8fce1dc34c0be91c26dc168b7`, which was not the live PR head when the disposition was recorded.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#discussion_r3235087851

Disposition: FIXED
Commit: 2a09022b6
Evidence: `core/food_sources/preference_recipe_mapping.py` now scans every occurrence of each forbidden note phrase instead of only the first match; `tests/test_food_source_preference_recipe_mapping.py` rejects a later positive `api approved` statement after an earlier negated `does not approve API calls` phrase.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#pullrequestreview-4282838820
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#discussion_r3235269759

Disposition: FIXED
Commit: 2a09022b6
Evidence: `core/food_sources/preference_recipe_mapping.py` rejects short `api approved`, `approved api`, `allowed api`, `api allowed`, `approved ingest`, `allowed ingest`, `approved cache`, and `allowed cache` note aliases; `tests/test_food_source_preference_recipe_mapping.py` covers these aliases.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#discussion_r3235281731
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#discussion_r3235281746

Disposition: NOT-A-BUG
Evidence: Local ancestry checks passed for the mapped proof commits against current local head `2a09022b6`: `git merge-base --is-ancestor 0df4b0788 HEAD`, `git merge-base --is-ancestor f7899072d HEAD`, and `git merge-base --is-ancestor aea4017cd HEAD`.
Reason: The fixed-mapping proof commits are present in the PR branch history; no mapping rewrite is required for this comment beyond recording the fresh evidence.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#discussion_r3235281738

Disposition: FIXED
Commit: 2a09022b6
Evidence: `core/food_sources/preference_recipe_mapping.py` now revalidates PR11 `next_recommended_lane` and `final_gate_decision` when direct callers pass a `SourceGapAudit` object; `tests/test_food_source_preference_recipe_mapping.py` rejects PR11 top-level handoff drift.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#discussion_r3235281743

Disposition: FIXED
Commit: 2a09022b6
Evidence: `core/food_sources/preference_recipe_mapping.py` now revalidates PR14 top-level `source`, `source_classification`, and `source_family` when direct callers pass a `RecipeDishCorpusGovernance` object; `tests/test_food_source_preference_recipe_mapping.py` rejects PR14 top-level identity drift.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#discussion_r3235281749

Disposition: FIXED
Commit: 2a09022b6
Evidence: `core/food_sources/preference_recipe_mapping.py` now rechecks PR11 Edamam/Spoonacular source-gap decisions, source family, allowed role, and unsafe approval flags; `tests/test_food_source_preference_recipe_mapping.py` rejects direct-object drift in those source-gap rows.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#discussion_r3235281755

Disposition: FIXED
Commit: 98b9872aa
Evidence: `core/food_sources/preference_recipe_mapping.py` now rechecks PR14 review-row `source_classification` and `source_family`; `tests/test_food_source_preference_recipe_mapping.py` rejects direct PR14 review identity drift.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#discussion_r3235508600

Disposition: NOT-A-BUG
Evidence: Live PR head before this follow-up was `101cc29c631e2c4d1de4f1ebb92e2ef5b3868534`, and strict disposition guard passed against the live PR after resolving 18 review threads. The reviewed squash-like SHA `5e0e74bc8638865a7b644883179118c750297d87` is not the live GitHub PR branch head.
Reason: The canonical mapping proof is evaluated against the live PR branch history, where the mapped commits were present before this follow-up; no remap to the review-internal squash SHA is required.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#discussion_r3235508608

Disposition: FIXED
Commit: 98b9872aa
Evidence: `core/food_sources/preference_recipe_mapping.py` now applies the PR15 safe-note scanner to PR14 review-row notes during direct handoff validation; `tests/test_food_source_preference_recipe_mapping.py` rejects PR14 review notes such as `api calls are allowed`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#discussion_r3235508615

Disposition: FIXED
Commit: 98b9872aa
Evidence: `core/food_sources/preference_recipe_mapping.py` now applies the PR15 safe-note scanner to PR11 Edamam/Spoonacular source-gap notes during direct handoff validation; `tests/test_food_source_preference_recipe_mapping.py` rejects PR11 source-gap notes such as `source use approved`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#discussion_r3235508620

Disposition: FIXED
Commit: 98b9872aa
Evidence: `core/food_sources/preference_recipe_mapping.py` rejects duplicate PR11 `source_gap_decisions` before building the lookup; `tests/test_food_source_preference_recipe_mapping.py` covers duplicate Edamam rows with unsafe drift.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#discussion_r3235508626

Disposition: NOT-A-BUG
Evidence: Sourcery review body reports rate limiting only; it contains no actionable code or governance finding for this PR.
Reason: External service quota notice does not require a code change.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#pullrequestreview-4281679198

Disposition: NOT-A-BUG
Evidence: Cubic review body says `No issues found` across the original 7 files.
Reason: No actionable finding to fix.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#pullrequestreview-4281713734

Disposition: FIXED
Commit: 72bff386f
Evidence: `core/food_sources/preference_recipe_mapping.py` now requires the direct PR11 `coverage_domains` order to match the canonical PR11 artifact order before building the lookup; `tests/test_food_source_preference_recipe_mapping.py` rejects duplicate and extra PR11 coverage-domain rows with unsafe drift.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#discussion_r3235680186
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#discussion_r3235680221

Disposition: FIXED
Commit: 72bff386f
Evidence: `core/food_sources/preference_recipe_mapping.py` now applies the PR15 safe-note scanner to PR11 top-level notes and the `preference_menu_planning` coverage-domain notes during direct handoff validation; `tests/test_food_source_preference_recipe_mapping.py` rejects approving PR11 top-level and preference-domain notes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#discussion_r3235680192
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#discussion_r3235680216

Disposition: FIXED
Commit: 72bff386f
Evidence: `core/food_sources/preference_recipe_mapping.py` now requires the direct PR11 `source_gap_decisions` order to match the canonical PR11 artifact order after duplicate detection; `tests/test_food_source_preference_recipe_mapping.py` rejects extra PR11 source-gap rows with unsafe drift.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#discussion_r3235680203

Disposition: FIXED
Commit: 72bff386f
Evidence: `core/food_sources/preference_recipe_mapping.py` now applies the PR15 safe-note scanner to PR14 top-level notes during direct handoff validation; `tests/test_food_source_preference_recipe_mapping.py` rejects approving PR14 top-level notes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1747#discussion_r3235680210

## Merge Readiness

Current-head merge readiness is pending the final post-fix push/check cycle. Already completed locally before this mapping update: post-open task bootstrap, mandatory QA/bug-hunter pass, CodeRabbit review pass, Codex Security diff-scoped pass, current-head checks inspection, and review-thread disposition loop.
