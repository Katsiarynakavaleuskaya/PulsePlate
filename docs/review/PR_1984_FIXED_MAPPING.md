# PR 1984 Fixed in Commit Mapping

## Lane Start Provenance

Packet: `artifacts/orchestration/task_packets/e783c0240b3a.json`
- Branch: `codex/fix-main-safety-security-deps-after-pr1982`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Base: `origin/main` at PR #1982 merge commit `e2b8fbae5`.
- Role order executed pre-open:
  `agent-coordinator -> security-auditor -> backend-engineer -> qa-engineer-agent -> bug-hunter -> architecture-specialist -> cursor-specialist-agent -> web-research-agent`

## Scope Boundary

- In scope: Python dependency security floors, regenerated Python lock
  surfaces, dependency-security guard schema/tests, security evidence docs,
  exact emergency wheel fallback metadata, and stale private-index backlog
  tracking.
- Out of scope: legacy route work, BMI/plan behavior, planning engines, FoodDB,
  premium, exports, insight, frontend, iOS/macOS, and broad dependency refresh.

## Premortem Closure

- Artifact: `docs/review/PR_MAIN_SAFETY_DEPENDENCY_HOTFIX_PREMORTEM.md`
- Decision: proceed with the dependency-security hotfix.
- Closure: premortem risks are addressed by narrow lock regeneration,
  no-`pip==...` negative controls, focused runtime smoke tests, exact fallback
  metadata updates, and `.secrets.baseline` review after hook regeneration.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/main-safety-deps-hotfix-oracle-full-packet.json`
Artifact: `artifacts/orchestration/experiments/results/exp-03780de8d42f.json`
- Result: `artifacts/orchestration/experiments/results/exp-03780de8d42f.json`
- Status: accepted.
- Runner mode: `oracle_only_governance_reviewer`.
- Oracles executed: 2.
- Source diff applied to temp checkout: `true`.
- Source diff paths: 23.
- Failure class: `null`.
- Contribution kind: `oracle_review`.
- Co-author required: `true`.
- Commit trailer included in implementation commit
  `93575bfe58d1953aa8a1ceacb2021913c280c822`:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Initial PR open: no review threads existed at artifact creation.
- [ ] Post-open `qa-engineer-agent -> bug-hunter -> security-auditor` pass
  pending.
- [ ] Codex Security diff scan / finding discovery pending.
- [ ] CodeRabbit review pending when authenticated.
- [ ] `pulseplate-pr-review` pending.
- [ ] Current actionable bot/review comments must be fixed or dispositioned
  before merge readiness.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 93575bfe58d1953aa8a1ceacb2021913c280c822
Evidence: `requirements.in`, `requirements-ci-lite.in`, `requirements-dev.in`, `requirements-docker-runtime.in`, `constraints.txt`, all regenerated lock surfaces, `tests/fixtures/dependency_security_schema.json`, `tests/test_dependency_security_guard.py`, `docs/security/SFTY-20260615-python-runtime-floors.md`, and `scripts/ci/emergency_python_wheels.json`.
Reason: Restores current `main` CI security by raising Safety-blocked Python runtime dependency floors, regenerating the affected lock surfaces, guarding against reintroduction of vulnerable floors, and refreshing exact emergency fallback metadata for private-index lag.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1984 -> 93575bfe58d1953aa8a1ceacb2021913c280c822

## Dependency Delta Proof

- `cryptography` source floor:
  `cryptography>=48.0.1,<49.0.0`.
- `python-multipart` source floor:
  `python-multipart>=0.0.31,<1.0.0`.
- `starlette` source floor:
  `starlette>=1.3.1,<2.0.0`.
- Lock pins across affected lock surfaces:
  `cryptography==48.0.1`, `python-multipart==0.0.31`, and
  `starlette==1.3.1`.
- Negative control: no repo-managed retained `pip==...` lock pin in
  `requirements-dev.txt` or `requirements-lock.txt`.
- Emergency fallback metadata updated only for exact `cryptography 48.0.1`
  and `python-multipart 0.0.31` wheels; no `starlette` fallback added because
  local dependency sync resolved it without a proxy miss.

## Local Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS:
  `.venv/bin/python -m pytest -q tests/test_dependency_security_guard.py tests/guards/test_security_devtooling_regression_guards.py tests/test_python_supply_chain_controls.py`
- PASS: focused emergency-wheel/install guard subset.
- PASS: focused Starlette/FastAPI runtime smoke subset covering health,
  WebSocket security, realtime WebSocket security, pro-session cookie auth, and
  web-session security helpers.
- AUTH-BLOCKED locally:
  `python3 scripts/ci/run_safety_audit.py` exited before scanning because
  `SAFETY_API_KEY` is not exported:
  `ERROR: SAFETY_API_KEY is required for Safety scan in cicd/production stage.`
  Current-head CI `CI / security` is the required Safety proof for this PR.
- PASS:
  `make validate-changed VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python`
- PASS: `pre-commit run --all-files`
- PASS during commit/push hooks: backend changed-file pytest, pre-push backend
  pytest, `pip-audit`, full-repo Bandit, and docker build test.

## Machine-Heavy Verification Deferral

Full local `make verify` was not run. This PR uses the operator-approved
machine-heavy exception for a narrow `main` stabilization lane. Merge readiness
requires the focused local gates above, pre-commit/pre-push evidence,
current-head CI parity, review-thread disposition, strict merge-readiness
checks with auth, and the wait-window.

## Merge Readiness

Not ready at latest artifact update. Required before merge:

- Numbered fixed-mapping artifact committed and PR body mirror updated.
- Post-open role-agent review sequence completed.
- Codex Security diff scan / finding discovery completed.
- CodeRabbit/Sourcery/Cubic actionable comments fixed or dispositioned.
- `pulseplate-pr-review` completed.
- Current-head CI parity on latest pushed commit, especially repaired
  `CI / security` Safety job.
- Strict merge-readiness check with `--require-auth`.
- No unresolved actionable review or bot comments.
- Mandatory wait-window after latest bot/review activity.
