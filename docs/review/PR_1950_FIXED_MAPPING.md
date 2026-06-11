# PR #1950 Fixed in Commit Mapping

## Summary

PR #1950 adds an internal backend-only Markov coaching orchestration adapter v1
for FitChef. It composes the existing user coaching state builder and Markov
transition planner into an internal shadow result plus prompt-safe Markov
context projection.

## Scope

- Internal frozen schemas for Markov orchestration trace/result status.
- Internal service-only adapter:
  `build_user_coaching_state(...) -> build_markov_coaching_transition_plan(...) -> to_prompt_safe_markov_context(...)`.
- Focused tests for composition, degradation, shadow gating, no recommendation,
  fail-closed planner errors, prompt-safe projection, and service-only guards.

## Out Of Scope

- Public routes, OpenAPI/client changes, iOS/web changes, runtime prompt
  injection, persistence, provider calls, RL/MDP learning, RAG/GraphRAG,
  semantic cache, hidden memory, and medical/therapy claims.

## Implementation Commits

- `8a4730e25fafa2301f04b346c3c45100e1957cb7` - implementation, tests,
  pre-open governance fixes, and Experiment Runner co-author trailer.
- `18c82466de44a902aa46c12aa64888bffe0738a3` - canonical PR #1950 mapping
  artifact.
- `01f2ad6ee949f9c5147730af33c134291230592a` - post-open QA fixes for
  result status invariants and Phase2 mapping artifact format.
- `ff9bf5f87071d5c3e4bddc30cd4f38db7516907b` - post-open bug-hunter fix for
  result status truth-table validation.
- `07e20c9c401a8abeee1145742b583ab20130d560` - non-force branch sync with
  current `origin/main` before final current-head gates.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/5c57ba922c89.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Branch: `codex/fitchef-markov-coaching-orchestration-adapter-v1`
- Base: `origin/main` at `b20f807a5c61cb166f909d9aacbe86b3044ee31e`

## Role-Agent Passes

Pre-open role order completed:

1. `agent-coordinator`
2. `architecture-specialist`
3. `security-auditor`
4. `qa-engineer-agent`
5. `bug-hunter`
6. `backend-engineer`

Post-open role order required before readiness:

1. `qa-engineer-agent`
2. `bug-hunter`
3. `security-auditor`
4. Codex Security diff scan / finding discovery
5. `pulseplate-pr-review`

## Premortem Risk Review

Decision: `proceed with changes`.

Findings:

- Disposition: FIXED
  Evidence: `app/schemas/user_coaching_state.py` validates
  prompt-safe-context-to-plan consistency; regression coverage is in
  `tests/test_coaching_markov_orchestration_adapter.py`.
  Reason: prompt-safe context and transition plan could otherwise diverge under
  tampered model copies.
- Disposition: FIXED
  Evidence: `app/services/coaching_markov_orchestration_adapter.py` computes
  planner degradation from the final trace reason set; regression coverage is in
  `tests/test_coaching_markov_orchestration_adapter.py`.
  Reason: fail-closed planner errors could otherwise emit `planner_unavailable`
  while `planner_degraded` remained false.
- Disposition: FIXED
  Evidence: service-only source guards and prompt-safe leakage tests in
  `tests/test_coaching_markov_orchestration_adapter.py` and
  `tests/test_user_coaching_state.py`.
  Reason: the adapter must not wire public/runtime/provider/RAG/cache/write
  surfaces or leak raw user data.

## Experiment Runner Evidence

- Packet:
  `artifacts/orchestration/experiments/markov-orchestration-adapter-v1-oracle-packet.json`
- Artifact:
  `artifacts/orchestration/experiments/results/markov-orchestration-adapter-v1-oracle-result.json`
- Mode: `oracle_only_governance_reviewer`
- Status: accepted
- Oracle results: 2/2 passed
- Shared tree: untouched
- Source diff: applied to isolated checkout
- Contribution: `oracle_review`
- Commit trailer:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- No actionable review comments

## Post-Open Review Disposition

- `qa-engineer-agent`: FIXED required, then fixed in
  `01f2ad6ee949f9c5147730af33c134291230592a`.
  Evidence:
  `app/schemas/user_coaching_state.py`,
  `app/services/coaching_markov_orchestration_adapter.py`,
  `tests/test_coaching_markov_orchestration_adapter.py`, and this artifact.
  Findings fixed: result status invariants, prompt-safe projection under
  `no_recommendation`, exact Phase2 mapping format, and PR body heading
  contract.
- CodeRabbit: NOT-A-BUG for this code diff at this stage. The bot comment is a
  rate-limit/usage notice and does not identify code actionables. Explicit
  no-actionables/pass remains a merge-readiness prerequisite if the bot reruns.
- Sourcery: NOT-A-BUG for this code diff at this stage. The bot review comment
  is a weekly rate-limit notice and does not identify code actionables. Explicit
  no-actionables/pass remains a merge-readiness prerequisite if the bot reruns.
- `bug-hunter`: FIXED in `ff9bf5f87071d5c3e4bddc30cd4f38db7516907b`. Evidence:
  `app/schemas/user_coaching_state.py` now rejects `ready` traces with degraded
  evidence and `no_recommendation` traces attached to recommending plans;
  regression coverage is in `tests/test_coaching_markov_orchestration_adapter.py`.
- `security-auditor`: PASS / no-actionables at
  `0bcba262564978cd365c57e7bca371af772cecae`. Evidence: read-only review
  covered leakage, prompt-safety, medical/therapy claims, route/OpenAPI/client/
  runtime/provider/RAG/semantic-cache/write coupling, status tampering, and
  governance gaps.
- Codex Security diff scan / finding discovery: PASS / no-actionables at
  `07e20c9c401a8abeee1145742b583ab20130d560`. Evidence:
  `/tmp/codex-security-scans/fitchef-markov-coaching-orchestration-adapter-v1/5b2b230a2115_20260611T190057Z/report.md`
  validated successfully and `report.html` rendered; work ledger completed 2/2
  deep-review rows for `app/schemas/user_coaching_state.py` and
  `app/services/coaching_markov_orchestration_adapter.py`; no raw candidates
  were emitted.
- `pulseplate-pr-review`: NOT-A-BUG for the advisory large-diff note. Evidence:
  refreshed post-sync report reviewed 5 files / 1146 additions, matching the
  operator-requested large backend-only PR scope; deterministic gates passed:
  focused pytest, touched-file mypy, `make validate-changed`,
  `pre-commit run --all-files`, and pre-push hooks. No code, security,
  architecture, wellness, or governance finding was emitted.

## Local Validation

- `python3 scripts/orchestration/check_preflight.py`: PASS
- `python3 scripts/orchestration/check_agent_consistency.py`: PASS
- `pytest -q tests/test_coaching_markov_orchestration_adapter.py tests/test_coaching_transition_planner.py tests/test_user_coaching_state.py tests/test_bayes_adherence_model.py tests/test_bayes_adherence_service.py tests/test_nutrition_log_idempotency.py`: PASS
- `mypy app/schemas/user_coaching_state.py app/services/coaching_state_builder.py app/services/coaching_transition_planner.py app/services/coaching_markov_orchestration_adapter.py tests/test_user_coaching_state.py tests/test_coaching_transition_planner.py tests/test_coaching_markov_orchestration_adapter.py --no-incremental --cache-dir=/dev/null`: PASS
- `flake8` on touched schema/service/tests: PASS
- `make validate-changed`: PASS
- `pre-commit run --all-files`: PASS
- Pre-push hooks: PASS, including changed-file mypy, pytest pre-push,
  full-repo bandit, and docker build test.
- After non-force `origin/main` sync at
  `07e20c9c401a8abeee1145742b583ab20130d560`:
  - focused pytest for adapter/planner/state/bayes/nutrition idempotency:
    PASS, 85 tests.
  - touched-file mypy: PASS, 7 source files.
  - `make validate-changed`: PASS, 38 tests.
  - `pre-commit run --all-files`: PASS.
  - pre-push hooks: PASS, including pip-audit, backend pre-push pytest,
    full-repo bandit, and docker build test.

## Merge Readiness

Not claimed. Current-head CI, strict merge-readiness, no unresolved threads, and
mandatory wait-window remain pending.
