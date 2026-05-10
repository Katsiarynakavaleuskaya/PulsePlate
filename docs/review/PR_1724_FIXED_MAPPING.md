<!-- markdownlint-disable MD013 MD034 -->
# PR 1724 Fixed In Commit Mapping

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1724>
- Branch: `hotfix/remove-pip-pin-requirements-dev`
- Title: `fix(security): remove pip pin from requirements-dev lock (guard / GHSA-58qw)`
- Implementing commit (remove pip lock line + GHSA anchors): `321be80d958519a72f9995ca7c7dc9548e34b914`
- Scope: `requirements-dev.txt`, `docs/security/GHSA-58qw-9mgm-455v-pip.md` — restores `test_repo_managed_lock_surfaces_do_not_pin_pip` on main; no application runtime surface.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Dependency-security hotfix: treat new bot threads via disposition below once CI/review emits them.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1724#pullrequestreview-4259625562
Disposition: NOT-A-BUG
Evidence: `scripts/ci/check_docs_phase1_gates.py:96` enforces explicit `` `file:line` `` anchors for `docs/security/*.md`; Sourcery suggestion to drop line-specific anchors would fail CI. Review body matches boilerplate **Prompt for AI Agents**; no code change for this hotfix scope.

## Local Validation Evidence

- Pre-flight: `python3 scripts/orchestration/check_preflight.py --path requirements-dev.txt --path docs/security/GHSA-58qw-9mgm-455v-pip.md` — PASS.
- Agent consistency: `python3 scripts/orchestration/check_agent_consistency.py` — PASS.
- `pytest tests/test_dependency_security_guard.py::test_repo_managed_lock_surfaces_do_not_pin_pip` — PASS.
- `python3 scripts/ci/check_docs_phase1_gates.py --files docs/security/GHSA-58qw-9mgm-455v-pip.md` — PASS (`file:line` anchors present).
- `make validate-min` — PASS.
- `pre-commit run --all-files` — PASS before commit; pre-push hooks — PASS.

### Bootstrap / coordinator lane

- `task_bootstrap` (Security, `pre_open`): packet `artifacts/orchestration/task_packets/manual_hotfix_pip_lock_pre_open.json` — primary `security-auditor`; local-only artifact per repo policy.

### Machine-heavy / operator-approved narrow gate

- Full `make verify` deferred for this scoped hotfix; narrow gates above + canonical current-head CI are the merge signal.

## Security Notes

- Removes `pip==...` from repo-managed dev lock (`requirements-dev.txt`) per `GHSA-58qw-9mgm-455v` remediation lane (no fictitious “safe” pip pin).
- Evidence: `requirements-dev.txt:250`, `requirements-lock.txt:212`, `tests/test_dependency_security_guard.py` (pip pin prohibition).

## Risks / Rollback

- Risk: negligible for runtime; CI/dev envs resolve `pip` via base image / ephemeral tooling — matches existing policy doc.
- Rollback: revert `321be80d958519a72f9995ca7c7dc9548e34b914`.

## Merge Readiness

- [x] Pre-flight + agent consistency: PASS (local gates in evidence section)
- [x] Canonical artifact: this file
- [ ] PR body Phase2 mirror synchronized (checked boxes + `### Fixed in Commit Mapping` → canonical artifact pointer)
- [ ] Required current-head CI jobs green (`CI` canonical lane + governance checks)
- [ ] Post-open reviewers: security-auditor → qa-engineer-agent → bug-hunter completed per root `AGENTS.md`

## Deferred / Follow-ups

- **PR #1720** (mypy 2.0.0): separate lane; widen coordinator stack (`backend-engineer`, `architecture-specialist`) and budget for `make typecheck` fallout after this hotfix merges.
