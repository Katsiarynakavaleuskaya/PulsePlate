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
- Startup packet: `artifacts/orchestration/task_packets/61fbd8909a0a.json`
- Declared pre-open role order:
  `agent-coordinator -> architecture-specialist -> security-auditor -> qa-engineer-agent -> bug-hunter -> backend-engineer`
- Dispatch manifest:
  `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/61fbd8909a0a.json --mode runtime --pr-phase pre_open --implementation-owner backend-engineer --pretty`

## Discussion Thread Pass

- [x] Discussion-thread pass completed for pre-open state.
- [x] Fixed in commit mapping initialized.
- Review threads inspected after PR open: none yet.
- Bot reviews/actionables: pending post-open review cycle.

## Fixed in Commit Mapping

No GitHub review threads exist yet for PR #1894. Future actionable review
threads must be added here with `FIXED`, `NOT-A-BUG`, or `DEFERRED` disposition
proof before any merge-readiness claim.

## Implementation Evidence

- `64c250fbb` — adds the Markov transition schemas, deterministic planner
  service, prompt-safe projection, and focused planner tests.
- `f128e638d` — closes premortem safety-label drift by adding
  `non_diagnostic` to the Markov safety-label surface and tests.
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
- Result: `artifacts/orchestration/experiments/results/exp-455d960da55d.json`
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
- `.venv/bin/python -m pytest -q tests/test_user_coaching_state.py tests/test_coaching_transition_planner.py tests/test_bayes_adherence_model.py tests/test_bayes_adherence_service.py tests/test_nutrition_log_idempotency.py` — 61 passed
- `.venv/bin/python -m mypy app/schemas/user_coaching_state.py app/services/coaching_transition_planner.py tests/test_coaching_transition_planner.py --no-incremental --cache-dir=/dev/null` — PASS
- `make validate-changed VENV_PYTHON=.venv/bin/python` — PASS
- `VENV_PYTHON=.venv/bin/python pre-commit run --all-files` — PASS
- `VENV_PYTHON=.venv/bin/python git push -u origin codex/fitchef-markov-transition-planner-v1` — pre-push hooks PASS

## Merge Readiness

Not claimed. Pending:

- Post-open `qa-engineer-agent -> bug-hunter -> security-auditor`
- Codex Security diff scan / finding discovery
- `pulseplate-pr-review`
- External bot review disposition
- Current-head CI evidence
- Strict merge-readiness check with required auth
