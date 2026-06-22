# PR #1995 Fixed in Commit Mapping

## Scope

PR #1995 hardens web-session cookie Secure handling by centralizing raw explicit
developer-env detection in `settings.py` and keeping `pp_web_session` Secure by
default for unset, unknown, and conflicting runtime labels.

Out of scope: PR #2006, colleague-owned branch state, unrelated planning-target
tests, and full local `make verify`.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Review comments inspected for PR #1995.
- [x] Actionable Sourcery feedback mapped after the code fix commit existed.
- [x] Actionable Codex inline P2 feedback mapped after the code fix commit existed.
- [ ] Review threads resolved in GitHub after this artifact and PR body mirror are pushed.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 3fb1c6993
Evidence: `settings.py` owns `is_raw_explicit_developer_env()` via `_DEVELOPER_LIKE_ENVS`, `app/security/web_session.py` no longer defines `_DEVELOPER_COOKIE_ENVS`, and `tests/test_production_runtime_invariants.py` guards against duplicate cookie developer-env allowlists.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1995#pullrequestreview-4532066588 -> 3fb1c6993

Disposition: FIXED
Commit: 3fb1c6993
Evidence: cookie policy keeps production-like labels Secure first, disables `Secure` only when every explicit raw runtime label is developer-like, and tests cover unset, unknown, local/review-style conflict, production/local conflict, exchange-header, and clear-cookie behavior.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1995#discussion_r3441832916 -> 3fb1c6993

## Premortem Risk Review

Mode: `pr-premortem` / `post_open_review`

Frame: It is 48 hours from now. This hotfix made cookie security worse. We are
looking backward to understand why.

Findings:
- Duplicate developer-env vocabulary drifts again and cookie policy silently
  diverges from runtime settings. Disposition: FIXED by centralizing raw explicit
  detection in `settings.py` and guarding against `_DEVELOPER_COOKIE_ENVS`.
- A leftover raw `APP_ENV=local` with non-dev `ENVIRONMENT` disables `Secure` in
  review/QA deployments. Disposition: FIXED by requiring all explicit raw labels
  to be developer-like and adding conflict tests.
- Tests pass falsely because repo-wide `ENVIRONMENT=test` masks the raw-env
  cases. Disposition: FIXED by clearing the opposite env var in targeted cookie
  tests and adding route/header coverage.

Decision: proceed with changes.

## Experiment Runner Evidence

- Accepted artifact:
  `artifacts/orchestration/experiments/results/pr1995_cookie_security_oracle_result_v2.json`
- Artifact: `artifacts/orchestration/experiments/results/pr1995_cookie_security_oracle_result_v2.json`
- Runner mode: `oracle_only_governance_reviewer`
- Result: accepted; 3/3 oracle commands passed; `source_diff_applied=true`;
  `mutated_paths=[]`.
- Oracle commands:
  - `python3 -m pytest -q tests/test_production_runtime_invariants.py tests/test_web_session_security.py tests/test_pro_session_cookie_auth.py tests/test_api_tiers.py`
  - `python3 -m mypy settings.py app/security/web_session.py`
  - `git diff --check`
- Contribution: `oracle_review`
- Co-author trailer required and used on commit `3fb1c6993`:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`
- Non-authoritative rejected attempt:
  `artifacts/orchestration/experiments/results/pr1995_cookie_security_oracle_result.json`
  rejected because `make validate-changed` cannot discover the shared venv from
  Experiment Runner's temporary checkout. Local `make validate-changed` passed
  separately and is recorded below.

## Local Validation

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/orchestration/task_bootstrap.py ...` with packet
  `artifacts/orchestration/task_packets/ab4687ea7227.json`
- PASS: role dispatch order completed:
  `agent-coordinator -> backend-engineer -> qa-engineer-agent -> bug-hunter -> security-auditor`
- PASS:
  `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_production_runtime_invariants.py tests/test_web_session_security.py tests/test_pro_session_cookie_auth.py tests/test_api_tiers.py`
- PASS:
  `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m mypy settings.py app/security/web_session.py`
- PASS:
  `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python make validate-changed`
- PASS:
  `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python /Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pre_commit run --all-files`
- PASS: `git diff --check`

Full local `make verify` not run by operator instruction for this narrow lane.

## Merge Readiness

Not merge-ready yet.

Remaining before merge:
- Push current commits to PR #1995.
- Update PR body mirror with this fixed mapping.
- Run current-head CI review after push.
- Run Codex Security diff scan / finding discovery and `pulseplate-pr-review`.
- Resolve review threads only after GitHub-visible disposition evidence exists.
- Run strict merge-readiness wrapper with auth and current-head CI evidence.
