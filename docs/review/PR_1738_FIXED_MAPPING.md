<!-- markdownlint-disable MD013 MD034 -->
# PR 1738 Fixed In Commit Mapping

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738>
- Branch: `codex/main-docker-proxy-security-unblock`
- Title: `fix(docker): unblock pip bootstrap through governed fallback`
- Implementing commits:
  - `d1a242507dde7ecf8f05c51582f469e929c2efce` - update the generated detect-secrets baseline for the new pinned emergency wheel digest.
  - `75d780cc3ef2b2a9300b2c9f126298b5a527b176` - route Docker pip bootstrap through the governed installer emergency fallback path.

## Discussion Thread Pass

- [ ] Discussion-thread pass completed after latest bot/human review activity.
- [ ] Fixed in commit mapping completed after latest bot/human review activity.

Per root `AGENTS.md` review governance, each actionable bot/human comment receives a disposition (`FIXED` / `NOT-A-BUG` / `DEFERRED`) with proof before thread resolution.

### Fixed in Commit Mapping

No review threads have been dispositioned yet. This draft PR must update this section after post-open review and before any merge-readiness claim.

## Merge Readiness

- [x] Pre-flight + agent consistency: PASS locally on hotfix branch.
- [x] Canonical artifact: this file.
- [ ] PR body Phase2 mirror synchronized after this artifact commit is pushed.
- [ ] Required current-head CI jobs green.
- [ ] Docker Build and Push reaches image security scan and uploads current-head evidence.
- [ ] Hidden Trivy/image findings triaged or split to a follow-up PR.
- [ ] Post-open reviewers completed (`qa-engineer-agent` -> `bug-hunter`) and actionables dispositioned.
- [ ] Mandatory wait-window after latest bot/review activity observed.

## Local Validation Evidence

- Startup gate: `python3 scripts/orchestration/check_preflight.py --path Dockerfile --path .github/workflows/build.yml --path .github/workflows/cd.yml --path .github/workflows/security.yml --path scripts/ci/install_locked_python_requirements.py --path scripts/ci/emergency_python_wheels.json --path tests/test_install_locked_python_requirements.py --path docs/roadmap/BACKLOG_LEDGER.md` - PASS.
- Agent consistency: `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- Focused tests: `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_install_locked_python_requirements.py tests/test_repo_policy_guards.py` - PASS.
- Branch-diff backend tests: `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python BRANCH_DIFF_MODE=1 bash scripts/run-backend-tests-pre-commit.sh` - PASS.
- Pre-commit: `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python pre-commit run --all-files` - PASS.
- Full local gate: `make verify` - PASS after using an ignored local `.venv` symlink to the repo venv; symlink and coverage artifacts were removed after the run.
- Pre-push hooks: PASS, including mypy, pip-audit, backend pre-push tests, full-repo Bandit, and docker build test.
