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
- [x] Post-open `qa-engineer-agent` pass completed.
- [ ] Post-open `bug-hunter -> security-auditor` pass pending.
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

Disposition: FIXED
Commit: b2f5345618dcf6e29d65fad8ce6da1b911e88302
Evidence: `docs/review/PR_1984_FIXED_MAPPING.md` uses exact Phase2 checklist labels, parser-safe single-line disposition fields, `Packet: ...`, and `Artifact: ...`; `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 1984 --body "$(gh pr view 1984 --json body --jq .body)" --commit-range origin/main..HEAD --experiment-runner-evidence-mode required` passed locally after the correction.
Reason: Fixed the QA-identified Phase2 canonical mapping and PR-body parser failures.

Disposition: FIXED
Commit: 254e9752265152032d4604f53f2524cba1935f83
Evidence: `docs/security/CRYPTOGRAPHY_46_0_7_PRIVATE_INDEX_ADVISORY.md`, `docs/security/CVE-2026-26007-cryptography.md`, `docs/security/CVE-2026-40347-python-multipart.md`, and `docs/security/SFTY-20260615-python-runtime-floors.md` now include `file:line` anchors; `tests/test_dependency_security_guard.py` uses `CURRENT_SAFETY_RUNTIME_FLOORS` and `test_dependency_security_schema_tracks_current_safety_runtime_floors`; `docs/security/SFTY-20260615-python-runtime-floors.md` marks `run_safety_audit.py` as `SAFETY_API_KEY` auth-gated; Docs Phase1 and dependency guard focused tests passed locally.
Reason: Fixed the QA Docs Phase1 blocker and the Sourcery comments about hard-coded dated floor-test naming and misleading local Safety validation.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1984#pullrequestreview-4504293768 -> 254e9752265152032d4604f53f2524cba1935f83

Disposition: FIXED
Commit: 8e300e3daa6b5a2e0f9bbd1f64ed2fc220478a6c
Evidence: `docs/review/PR_1984_FIXED_MAPPING.md` now uses unchecked `- [ ]` Merge Readiness checklist items, and `docs/security/CRYPTOGRAPHY_46_0_7_PRIVATE_INDEX_ADVISORY.md` varies the Prohibited Shortcuts sentence structure while preserving the same restriction.
Reason: Fixed the CodeRabbit merge-readiness checklist finding and low-value readability nit.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1984#discussion_r3419061121 -> 8e300e3daa6b5a2e0f9bbd1f64ed2fc220478a6c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1984#pullrequestreview-4504377032 -> 8e300e3daa6b5a2e0f9bbd1f64ed2fc220478a6c

Disposition: FIXED
Commit: 32bbff22ed9488b391d2f2480d876fcb9860dcf8
Evidence: `docs/security/SFTY-20260615-python-runtime-floors.md` and this artifact now separate target-wheel rotation from the active exact fallback manifest TTL renewal under `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-private-pypi-proxy-mirror-parity`.
Reason: Fixed the security-auditor blocker that fallback-scope evidence could imply only `cryptography` and `python-multipart` metadata changed.

## Role Review Finding Disposition

- `qa-engineer-agent`: FIXED for Docs Phase1, Phase2 parser, and Sourcery mapping blockers. Evidence: `python3 scripts/ci/check_docs_phase1_gates.py --files ...` PASS, `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 1984 --body "$(gh pr view 1984 --json body --jq .body)" --commit-range origin/main..HEAD --experiment-runner-evidence-mode required` PASS, and Sourcery review `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1984#pullrequestreview-4504293768` mapped to commit `254e9752265152032d4604f53f2524cba1935f83`.
- `qa-engineer-agent`: NOT-A-BUG for dependency/lock drift and machine-heavy validation budget. Evidence: QA pass confirmed dependency/lock drift is controlled and local focused gates are appropriate, while current-head CI `CI / security` remains required before merge readiness.
- `bug-hunter`: FIXED for the CodeRabbit merge-readiness checklist blocker. Evidence: `docs/review/PR_1984_FIXED_MAPPING.md` now uses unchecked Merge Readiness checkboxes and maps both CodeRabbit URLs to commit `8e300e3daa6b5a2e0f9bbd1f64ed2fc220478a6c`.
- `bug-hunter`: NOT-A-BUG for dependency/lock drift and docs/parser stability. Evidence: bug-hunter confirmed the dependency hotfix diff is controlled, Docs Phase1 passed, and Phase2 passed after QA follow-up.
- `security-auditor`: FIXED for fallback manifest scope evidence. Evidence: commit `32bbff22ed9488b391d2f2480d876fcb9860dcf8` clarifies that target wheels were rotated while the still-active exact fallback manifest TTL was renewed under the existing private-index mirror-lag ledger item.
- `security-auditor`: NOT-A-BUG for dependency floors/pins and secrets baseline. Evidence: security-auditor confirmed the floors/pins are controlled and `.secrets.baseline` changed only hashed fingerprints and timestamp, with no plaintext `secret_value` fields.

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
- Emergency fallback target wheels were rotated to exact
  `cryptography 48.0.1` and `python-multipart 0.0.31` artifacts.
- The still-active exact fallback manifest TTL was renewed to `2026-06-30`
  under `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-private-pypi-proxy-mirror-parity`;
  this preserves the existing enumerated private-index mirror-lag bridge and
  does not add a broad public-index bypass.
- No `starlette` fallback was added because local dependency sync resolved it
  without a proxy miss.

## Local Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/ci/check_docs_phase1_gates.py --files docs/security/CRYPTOGRAPHY_46_0_7_PRIVATE_INDEX_ADVISORY.md docs/security/CVE-2026-26007-cryptography.md docs/security/CVE-2026-40347-python-multipart.md docs/security/DEPENDENCY_SECURITY_GUARD_WORKFLOW.md docs/security/GHSA-mj87-hwqh-73pj-python-multipart.md docs/security/SFTY-20260615-python-runtime-floors.md docs/review/PR_MAIN_SAFETY_DEPENDENCY_HOTFIX_PREMORTEM.md docs/review/PR_1984_FIXED_MAPPING.md docs/roadmap/BACKLOG_LEDGER.md`
- PASS: `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 1984 --body "$(gh pr view 1984 --json body --jq .body)" --commit-range origin/main..HEAD --experiment-runner-evidence-mode required`
- PASS:
  `.venv/bin/python -m pytest -q tests/test_dependency_security_guard.py tests/guards/test_security_devtooling_regression_guards.py tests/test_python_supply_chain_controls.py`
- PASS: `.venv/bin/python -m pytest -q tests/test_dependency_security_guard.py`
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

- [ ] Numbered fixed-mapping artifact committed and PR body mirror updated.
- [ ] Post-open role-agent review sequence completed.
- [ ] Codex Security diff scan / finding discovery completed.
- [ ] CodeRabbit/Sourcery/Cubic actionable comments fixed or dispositioned.
- [ ] `pulseplate-pr-review` completed.
- [ ] Current-head CI parity on latest pushed commit, especially repaired
  `CI / security` Safety job.
- [ ] Strict merge-readiness check with `--require-auth`.
- [ ] No unresolved actionable review or bot comments.
- [ ] Mandatory wait-window after latest bot/review activity.
