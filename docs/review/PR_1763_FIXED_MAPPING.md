<!-- markdownlint-disable MD013 MD034 -->
# PR 1763 Fixed In Commit Mapping

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1763>
- Branch: `codex/main-transformers-emergency-manifest-581`
- Title: `fix(ci): align transformers emergency wheel manifest`
- Implementing commit: `12cd7d788d6b355992956eb245a61bee906760ff`
- Scope: `scripts/ci/emergency_python_wheels.json` (privileged CI/supply-chain fallback manifest), `.secrets.baseline` (generated detect-secrets refresh for the new wheel digest), and `docs/roadmap/BACKLOG_LEDGER.md` (active fallback truth). No runtime application source changes.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Initial current-head governance pass found no actionable human review threads. Internal role-agent findings were fixed before this artifact: the generated detect-secrets baseline was refreshed for the new wheel digest, and stale active fallback ledger references were updated from `transformers 5.8.0` to `transformers 5.8.1`. External CodeRabbit, Sourcery, and Cubic reviews remain merge-blocking until their current-head statuses are terminal and reviewed.

## Fixed in Commit Mapping

- No actionable review comments

## Local Validation Evidence

- Pre-flight: `python3 scripts/orchestration/check_preflight.py` - PASS.
- Task bootstrap: `python3 scripts/orchestration/task_bootstrap.py ... --pr-phase pre_open` - packet `9912cfb3bff9`.
- Post-open governance bootstrap: `python3 scripts/orchestration/task_bootstrap.py ... --pr-phase post_open_review` - packet `7e9fbaea6156`.
- Agent consistency: `.venv/bin/python scripts/orchestration/check_agent_consistency.py` - PASS.
- Focused regression: `.venv/bin/python -m pytest -q tests/test_install_locked_python_requirements.py::test_repo_transformers_emergency_fallback_matches_rag_vector_surfaces` - PASS.
- Changed-file validation: `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed` - PASS (`No Python files changed on the current branch`).
- Pre-commit: `PRE_COMMIT_HOME=/tmp/pulseplate-precommit-main-transformers-581 pre-commit run --all-files` - PASS.
- Commit hooks: `git commit -m "fix(ci): align transformers emergency wheel manifest"` - PASS.
- Pre-push hooks: `git push -u origin codex/main-transformers-emergency-manifest-581` - PASS, including backend pre-push, full Bandit, and docker build test.

### Machine-heavy / operator-approved narrow gate

- Full local `make verify` is deferred per the operator-approved machine-safe policy and root `AGENTS.md` machine-heavy PR exception. This PR uses focused local gates plus current-head GitHub CI as the heavy matrix/full coverage signal.

## Security Notes

- Supply-chain: the emergency wheel remains an exact PyPI-hosted HTTPS artifact with pinned filename and sha256 digest.
- The new `transformers 5.8.1` digest is `5340fb95962162cdfdae5cc91d7f8fedd92ed75216c1154c5e1f590fcf56dd0e`.
- `.secrets.baseline` changed only because detect-secrets fingerprints the new hex digest; it is not a credential leak.
- No installer fallback behavior, public-index policy, auth, quota, runtime, or application code was changed.

## Risks / Rollback

- Risk: if the repo intentionally rolls RAG vector requirements back to `transformers 5.8.0`, this manifest entry would need to roll back with them.
- Rollback: revert implementing commit `12cd7d788d6b355992956eb245a61bee906760ff` and regenerate `.secrets.baseline` for the prior manifest digest.

## Merge Readiness

- [x] Pre-flight + agent consistency: PASS.
- [x] Canonical artifact: this file (`docs/review/PR_1763_FIXED_MAPPING.md`).
- [x] PR body mirror: will be updated from this artifact before pushing this commit.
- [ ] Current-head CI: pending rerun after this artifact lands.
- [ ] Bot summaries reviewed (CodeRabbit / Sourcery / Cubic): pending terminal statuses.
- [ ] Strict merge readiness: pending `check_review_threads_disposition.py --require-auth` and `check_merge_ready.py --require-auth`.

## Deferred / Follow-ups

- None.
