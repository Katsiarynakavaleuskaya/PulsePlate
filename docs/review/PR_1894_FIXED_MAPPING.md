# PR #1894 Fixed in Commit Mapping

## Scope

This PR adds an internal FitChef Markov coaching transition planner v1 over
`UserCoachingStateV1`. The planner is service-only and deterministic: it ranks
allowed coaching scenarios from backend-derived sufficient state, then exposes a
prompt-safe projection. It does not add public routes, OpenAPI/client changes,
runtime prompt wiring, persistence, provider calls, semantic cache, RAG/GraphRAG,
RL/MDP learning, hidden memory, or medical/therapy claims.

## Lane Start Provenance

- Branch: `codex/fitchef-markov-transition-planner-v1`
- Base: `origin/main` at `86e40c9f9`
- Packet: `artifacts/orchestration/task_packets/61fbd8909a0a.json`
- Declared pre-open role order:
  `agent-coordinator -> architecture-specialist -> security-auditor -> qa-engineer-agent -> bug-hunter -> backend-engineer`
- Dispatch manifest:
  `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/61fbd8909a0a.json --mode runtime --pr-phase pre_open --implementation-owner backend-engineer --pretty`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- Review threads inspected after PR open.
- Bot reviews/actionables: CodeRabbit/Sourcery/Cubic inspected; actionable GitHub review threads are mapped below.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1894#discussion_r3367035663 -> 41010c3eba0f07092ec58ae00693398fbef27e16
Disposition: FIXED
Commit: 41010c3eba0f07092ec58ae00693398fbef27e16
Evidence: `MarkovCoachingTransitionPlanV1` and `PromptSafeMarkovTransitionContext` reset canonical `MARKOV_TRANSITION_SAFETY_LABELS`; `test_prompt_safe_markov_context_recovers_tampered_plan_derived_fields` covers tamper recovery.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1894#discussion_r3367035672 -> 41010c3eba0f07092ec58ae00693398fbef27e16
Disposition: FIXED
Commit: 41010c3eba0f07092ec58ae00693398fbef27e16
Evidence: `MarkovCoachingTransitionPlanV1` recomputes `recommended_scenario` from the first ranked scenario and `PromptSafeMarkovTransitionContext` mirrors the recomputed recommendation; `test_prompt_safe_markov_context_recovers_tampered_plan_derived_fields` covers injected recommendation override.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1894#discussion_r3367035674 -> 41010c3eba0f07092ec58ae00693398fbef27e16
Disposition: FIXED
Commit: 41010c3eba0f07092ec58ae00693398fbef27e16
Evidence: `_confidence` now applies a scenario-unavailable downgrade and `test_scenario_filtering_and_empty_available_scenarios_degrade` asserts the filtered plan has lower confidence than the full plan.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1894#discussion_r3367040476 -> 41010c3eba0f07092ec58ae00693398fbef27e16
Disposition: FIXED
Commit: 41010c3eba0f07092ec58ae00693398fbef27e16
Evidence: `MarkovCoachingTransitionPlanV1` validates consecutive ranks and normalized probability sums; `test_transition_plan_schema_rejects_impossible_rank_or_probability_shapes` covers invalid distributions.

## Implementation Evidence

- `64c250fbb` — adds the Markov transition schemas, deterministic planner
  service, prompt-safe projection, and focused planner tests.
- `f128e638d` — closes premortem safety-label drift by adding
  `non_diagnostic` to the Markov safety-label surface and tests.
- `41010c3eb` — hardens derived-field recomputation, probability/rank
  validation, canonical safety-label recovery, and scenario-unavailable
  confidence degradation.
- `621fe1c14` — closes post-open bug-hunter fallback invariant by rejecting
  ranked scenarios outside `available_scenarios` and adding regression coverage.
- `5315f1235` — closes post-open bug-hunter transition-state steering by moving
  fixed-policy scenario weights into schema validation and reusing them in the
  planner service.
- `004af7447` — closes post-open bug-hunter direct prompt-safe construction
  steering by reusing the same ranked-scenario validator in
  `PromptSafeMarkovTransitionContext`.
- `539dcfe26` — closes post-open bug-hunter self-consistent transition-state
  steering by requiring plan-level ranked scenarios to match the exact fixed
  policy for `transition_state + available_scenarios` and by validating
  transition-state reasons.
- `5a07e4c8b` — covers all fixed-policy validator branches after `539dcfe26`
  so diff-cover remains above the branch threshold without weakening guards.
- `7dd9a5b4f` — closes post-open bug-hunter fallback confidence inflation by
  requiring `scenario_unavailable` for fallback rankings and
  `no_recommendation_available` for empty allowlists.
- `6823411ad` — closes post-open backend-engineer inverse invariant by
  rejecting `no_recommendation_available` plans with non-empty
  `available_scenarios`.
- `1e8526dac` — closes post-open architecture prompt-safe policy asymmetry by
  validating direct `PromptSafeMarkovTransitionContext` probability vectors
  against fixed-policy ratios for the ranked subset.

## Post-open Role Findings

- Role: `bug-hunter`
  - Disposition: FIXED
  - Commit: `621fe1c1443e454daf9073482720bd2c7702fa5e`
  - Evidence: `MarkovCoachingTransitionPlanV1` rejects ranked scenarios outside
    `available_scenarios`; `test_transition_plan_schema_rejects_unavailable_ranked_scenarios`
    covers unavailable non-empty rankings, including empty allowlist plans.
- Role: `bug-hunter`
  - Disposition: FIXED
  - Commit: `5315f123555097669c8f7c97074532e6cfa35a02`
  - Evidence: `MarkovCoachingTransitionPlanV1` rejects ranked scenarios not
    valid for the current `transition_state`; `to_prompt_safe_markov_context`
    revalidation fails closed for tampered transition-state steering in
    `test_prompt_safe_markov_context_rejects_transition_state_steering`.
- Role: `bug-hunter`
  - Disposition: FIXED
  - Commit: `004af744709ce86f3bfc5d35350a33e17043a2f4`
  - Evidence: `PromptSafeMarkovTransitionContext` now reuses the same rank,
    probability, and transition-state scenario validator as
    `MarkovCoachingTransitionPlanV1`; `test_prompt_safe_markov_context_rejects_transition_state_steering`
    covers direct prompt-safe schema construction.
- Role: `bug-hunter`
  - Disposition: FIXED
  - Commit: `539dcfe26bfd61210d715cb0063966de52393447`
  - Evidence: `MarkovCoachingTransitionPlanV1` now requires exact
    fixed-policy ranked distributions and compatible transition-state reasons;
    `test_transition_plan_schema_rejects_non_policy_ranked_distribution` and
    `test_prompt_safe_markov_context_rejects_transition_state_steering` cover
    self-consistent plan steering before prompt-safe projection.
- Role: `bug-hunter`
  - Disposition: FIXED
  - Commit: `5a07e4c8be143cfb5774c03ae3a367e21445f79e`
  - Evidence: `test_transition_plan_schema_allows_empty_policy_when_primary_is_unavailable`,
    `test_markov_transition_schemas_reject_reason_mismatches`, and
    `test_transition_plan_schema_rejects_ranked_reason_mismatch` cover the
    fail-closed reason/policy branches added for bug-hunter findings.
- Role: `bug-hunter`
  - Disposition: FIXED
  - Commit: `7dd9a5b4f2b5883f606360ef385a43ed2ab0582d`
  - Evidence: `test_markov_schemas_require_scenario_unavailable_for_fallback_rankings`
    rejects direct plan/prompt-safe fallback rankings without
    `scenario_unavailable` and verifies fallback confidence is recomputed down;
    `test_transition_plan_schema_requires_no_recommendation_state_for_empty_allowlist`
    rejects empty-allowlist plans that do not use `no_recommendation_available`.
- Role: `bug-hunter`
  - Disposition: PASS
  - Evidence: Repeat pass after `7dd9a5b4f2b5883f606360ef385a43ed2ab0582d`
    found no correctness/regression findings and confirmed unavailable ranked
    scenarios, transition-state impossible scenarios, prompt-safe steering,
    fallback `scenario_unavailable`, confidence downgrade, and valid planner
    round-trip probes.
- Role: `security-auditor`
  - Disposition: PASS
  - Evidence: Local HEAD `4a6fa6e47` review found no file/line security,
    privacy, safety, or compliance findings; verified no route/OpenAPI/provider,
    DB/cache/RAG/runtime wiring, prompt-safe identifier/raw-event exclusion,
    fixed-policy/fallback validation, safety tests, and runtime-wiring guards.
- Role: `backend-engineer`
  - Disposition: FIXED
  - Commit: `6823411ade1884106665eb15948c6208c2b2f753`
  - Evidence: `test_transition_plan_schema_requires_no_recommendation_state_for_empty_allowlist`
    now rejects non-empty `available_scenarios` paired with
    `no_recommendation_available`; focused tests, mypy, flake8, and diff-cover
    passed after the fix.
- Role: `backend-engineer`
  - Disposition: PASS
  - Evidence: Repeat pass after `6823411ade1884106665eb15948c6208c2b2f753`
    found no backend file/line findings; verified inverse invariant,
    deterministic fixed-policy planner outputs, schema-only service imports,
    and no router/provider/DB/RAG/cache/persistence matches.
- Role: `architecture-specialist`
  - Disposition: FIXED
  - Commit: `1e8526dac6267f63343681663bd8e9a297939988`
  - Evidence: `PromptSafeMarkovTransitionContext` now validates direct
    prompt-safe ranked probability vectors against the fixed-policy ranked
    subset; `test_transition_plan_schema_rejects_non_policy_ranked_distribution`
    covers direct prompt-safe non-policy distributions.
- Role: `architecture-specialist`
  - Disposition: PASS
  - Evidence: Repeat pass after `1e8526dac6267f63343681663bd8e9a297939988`
    found no architecture file/line findings; verified prompt-safe fixed-policy
    validation, internal schema-only service boundary, no route/OpenAPI/client/
    runtime/provider/DB/RAG/cache/RL/learning changes, and no Markov references
    in `coaching_state_builder.py`.
- Codex Security diff scan
  - Disposition: PASS
  - Evidence: `/tmp/codex-security-scans/BMI-App_2025_clean/d94b67c55_mergebase_86e40c9f9_20260606T105235Z/report.md`
    and `.html`; 2/2 diff-scoped source rows completed in
    `artifacts/02_discovery/work_ledger.jsonl`, raw candidates empty, final
    report validated and rendered, no reportable findings.
- Skill: `pulseplate-pr-review`
  - Disposition: NOT-A-BUG
  - Evidence: Dry-run report emitted one advisory large-diff-risk note
    (`1644` changed lines) only. PR scope governance passed as a 5-file micro
    PR, the operator requested a larger cohesive epic-line PR instead of
    micro/docs-only slices, and local `make validate-changed`,
    `pre-commit run --all-files`, focused pytest/mypy/diff-cover, role passes,
    and Codex Security scan passed.
- `app/services/coaching_transition_planner.py` contains no router/runtime,
  provider, RAG/cache, DB/session, or persistence imports.
- `tests/test_coaching_transition_planner.py` covers default-prior handling,
  slip evidence, weekly reflection routing, scenario allowlist filtering,
  empty-scenario degradation, deterministic ranking, injection resistance,
  prompt-safe leakage exclusions, and builder integration.
- `tests/test_user_coaching_state.py` extends the service-only source guard to
  include `app/services/coaching_transition_planner.py`.

## Premortem Findings

- Safety-label vocabulary drift
  - Disposition: FIXED
  - Commit: `f128e638d`
  - Evidence: `PromptSafeMarkovTransitionContext` now carries
    `non_diagnostic`, and `tests/test_coaching_transition_planner.py` asserts
    that label while still blocking diagnosis, therapy, medical, and treatment
    wording.
- Slip-support promotion gap
  - Disposition: NOT-A-BUG
  - Evidence: This PR is explicitly service-only and does not claim runtime
    slip-support enablement. `tests/test_coaching_transition_planner.py` proves
    the builder integration degrades to `mascot_insight` with
    `scenario_unavailable` when `slip_support` is not in `available_scenarios`.
- Markov probability overclaim
  - Disposition: NOT-A-BUG
  - Evidence: The planner uses static fixed-policy weights, deterministic
    tie-breaks, no random sampling, and no learning/persistence surface.
- Dead foundation / follow-up risk
  - Disposition: NOT-A-BUG
  - Evidence: This is the approved internal foundation slice for the epic line;
    runtime integration remains out of scope and must use a separate gate.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/exp-455d960da55d.json`
- Artifact: `artifacts/orchestration/experiments/results/exp-455d960da55d.json`
- Status: `accepted`
- Runner mode: `oracle_only_governance_reviewer`
- Mutated paths: `[]`
- Shared tree untouched: `true`
- Co-author trailer: not required; the result did not shape a subsequent code,
  test, docs, mapping, review-disposition, or commit decision.
- Oracle 1:
  `python -m pytest -q tests/test_user_coaching_state.py tests/test_coaching_transition_planner.py`
  returned `0`.
- Oracle 2:
  `python -m mypy app/schemas/user_coaching_state.py app/services/coaching_transition_planner.py tests/test_coaching_transition_planner.py --no-incremental --cache-dir=/dev/null`
  returned `0`.

## Validation Evidence

- `python3 scripts/orchestration/check_preflight.py --path app/schemas/user_coaching_state.py --path app/services/coaching_state_builder.py --path app/services/coaching_transition_planner.py --path tests/test_coaching_transition_planner.py --path tests/test_user_coaching_state.py` — PASS
- `python3 scripts/orchestration/check_agent_consistency.py` — PASS
- `.venv/bin/python -m pytest -q tests/test_user_coaching_state.py tests/test_coaching_transition_planner.py tests/test_bayes_adherence_model.py tests/test_bayes_adherence_service.py tests/test_nutrition_log_idempotency.py` — 72 passed after `1e8526dac`
- `.venv/bin/python -m mypy app/schemas/user_coaching_state.py app/services/coaching_transition_planner.py tests/test_coaching_transition_planner.py --no-incremental --cache-dir=/dev/null` — PASS
- `.venv/bin/python -m diff_cover.diff_cover_tool coverage.xml --compare-branch=origin/main --include-untracked --fail-under=97 --format json:/tmp/markov-diff-cover.json` — PASS, 100%
- `make validate-changed VENV_PYTHON=.venv/bin/python` — PASS
- `VENV_PYTHON=.venv/bin/python pre-commit run --all-files` — PASS
- `VENV_PYTHON=.venv/bin/python git push -u origin codex/fitchef-markov-transition-planner-v1` — pre-push hooks PASS
- Codex Security diff scan — PASS, no findings; report:
  `/tmp/codex-security-scans/BMI-App_2025_clean/d94b67c55_mergebase_86e40c9f9_20260606T105235Z/report.md`
- `pulseplate-pr-review` — completed; advisory large-diff note dispositioned
  as NOT-A-BUG because this is an operator-requested cohesive 5-file epic-line
  PR with passing scope governance and targeted gates.

## Merge Readiness

Not claimed. Pending:

- External bot review disposition
- Current-head CI evidence
- Strict merge-readiness check with required auth
