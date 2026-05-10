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

- No actionable review comments (baseline)

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

- [ ] Pre-flight + agent consistency: PASS at branch tip
- [x] Canonical artifact: this file
- [ ] PR body mirrors Discussion Thread Pass / Fixed in Commit Mapping / Merge Readiness (mirror after artifact lands)
- [ ] Required current-head CI jobs green (`CI` canonical lane + governance checks)
- [ ] Post-open reviewers: security-auditor → qa-engineer-agent → bug-hunter (mandatory ordering per root `AGENTS.md`)

## Deferred / Follow-ups

- **PR #1720** (mypy 2.0.0): separate lane; widen coordinator stack (`backend-engineer`, `architecture-specialist`) and budget for `make typecheck` fallout after this hotfix merges.
