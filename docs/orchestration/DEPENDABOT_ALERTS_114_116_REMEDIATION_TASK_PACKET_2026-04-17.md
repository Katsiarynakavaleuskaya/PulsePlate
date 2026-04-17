# Dependabot Alerts 114-116 Remediation Task Packet

## Summary

- **Date:** 17 April 2026
- **Stable starting branch:** `main`
- **Bundled alerts:** `#114`, `#115`, `#116`
- **Package:** `Mako`
- **Advisory:** `GHSA-v92g-xgxw-vvmm`
- **Patched floor:** `Mako >= 1.3.11`
- **Worktree:** `worktrees/mako-security-floor`
- **Branch:** `fix/mako-security-floor`
- **Planned PR title:** `fix(deps): raise Mako security floor for alerts 114-116`
- **Lane mode:** single coordinator-owned dependency-security remediation PR

This packet governs the narrow remediation lane for the three currently open
Dependabot alerts on `Mako` across the repo's Python requirement and lock
surfaces. The lane is intentionally limited to dependency floors, lock
regeneration, schema/guard synchronization, security evidence, and merge
governance. It must complete before the Wave 6 `security-floor` docs/governance
lane tracked in `docs/roadmap/BACKLOG_LEDGER.md:1657-1678` and reconciled by
merged `PR #1433` (`docs(roadmap): reconcile Wave 6 PR-S0 lane and security floor`,
<https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1433>) returns to
normal sequencing.

## Current-Head Truth

- GitHub Dependabot currently reports:
  - `#114` — `Mako` in `requirements-ci-lite.txt`
  - `#115` — `Mako` in `requirements-lock.txt`
  - `#116` — `Mako` in `requirements.txt`
- All three alerts map to the same advisory:
  - `GHSA-v92g-xgxw-vvmm`
  - vulnerable range `<= 1.3.10`
  - first patched version `1.3.11`
- Current repo evidence before remediation:
  - `requirements.in:37` — `alembic>=1.17.2,<2.0.0` currently resolves to `Mako==1.3.10`
  - `requirements-ci-lite.in:34` — `alembic>=1.17.2,<2.0.0` currently resolves to `Mako==1.3.10`
  - `requirements.txt:103` — runtime lock pins `mako==1.3.10`
  - `requirements-lock.txt:213` — full lock pins `mako==1.3.10`
  - `requirements-ci-lite.txt:152` — CI-lite lock pins `mako==1.3.10`
  - `constraints.txt:50` — no explicit `Mako` security floor exists yet
  - `tests/fixtures/dependency_security_schema.json:2` — no `Mako` minimum safe
    version exists yet
- Execution rule:
  - all implementation happens only in the clean dedicated worktree above to
    satisfy the repo worktree-isolation rule in `AGENTS.md:227-232`; the root
    tree stays out of scope for this remediation lane.

## Mandatory Role Order

1. `agent-coordinator`
2. `security-auditor`
3. `backend-engineer`
4. `architecture-specialist` only if source-floor strategy conflicts with the
   repo's dependency/lock policy
5. `qa-engineer-agent`
6. `bug-hunter`

Rules:

- This role order is mandatory for the lane.
- `dev-operator` may be used only as the execution/evidence helper and does not
  replace the reviewer order.
- The mandatory post-open review pass remains `qa-engineer-agent -> bug-hunter`.
- No unrelated runtime, OpenAPI, frontend, iOS, or security-epic/docs work may
  piggyback on this PR.

## Skill Routing

- `agent-coordinator`
  - `pulseplate-workflow`
  - `docs-sync`
  - `pulseplate-gates`
- `security-auditor`
  - `security-best-practices`
  - `security-threat-model`
  - `pulseplate-guards`
- `backend-engineer`
  - `pulseplate-gates`
  - `docs-sync`
- `qa-engineer-agent`
  - `bug-triage`
  - `pulseplate-gates`
  - `code-review-expert`
- `bug-hunter`
  - `bug-triage`
  - `pulseplate-gates`
  - `pulseplate-guards`

## Scope Lock

### In scope

- Raise the `Mako` security floor to `1.3.11` across the repo's governed Python
  dependency source surfaces
- Regenerate the affected pinned Python lock surfaces so the committed repo
  truth closes alerts `#114-#116`
- Update the dependency security schema so `Mako 1.3.11` becomes an enforced
  minimum safe version
- Add a dedicated security evidence note for `GHSA-v92g-xgxw-vvmm`
- Open a draft PR, create the canonical review artifact, run the required
  post-open review pass, and complete merge-readiness governance

### Out of scope

- Frontend or npm dependency work
- OpenAPI regeneration or generated client types
- Backend or frontend behavior changes unrelated to the dependency remediation
- Wave 6 security-floor docs reconciliation already landed in merged `PR #1433`
  (`docs(roadmap): reconcile Wave 6 PR-S0 lane and security floor`,
  <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1433>; seam SoT:
  `docs/roadmap/BACKLOG_LEDGER.md:1657-1678`)

## Expected Touched Surfaces

- governed Python dependency source and constraint surfaces
- pinned runtime / full lock / CI-lite lock surfaces
- `scripts/ci/emergency_python_wheels.json`
- `tests/fixtures/dependency_security_schema.json`
- `docs/security/GHSA-v92g-xgxw-vvmm-mako.md`
- `docs/security/MAKO_1_3_11_PRIVATE_INDEX_ADVISORY.md`
- `docs/review/PR_<N>_FIXED_MAPPING.md`

## Acceptance Criteria

- Committed repo truth shows `Mako >= 1.3.11` on governed source surfaces and
  `mako==1.3.11` on the remediated pinned lock surfaces
- Dependency security schema enforces `Mako 1.3.11`
- A dedicated security note exists with `file:line` evidence and validation
  commands
- Alerts `#114-#116` are remediated by the PR
- Post-open review completes in mandatory order `qa-engineer-agent -> bug-hunter`
- Only after this PR merges do we resume the security-epic/docs lane

## Evidence Requirements

- Live alert queries:
  - `gh api repos/Katsiarynakavaleuskaya/PulsePlate/dependabot/alerts/114`
  - `gh api repos/Katsiarynakavaleuskaya/PulsePlate/dependabot/alerts/115`
  - `gh api repos/Katsiarynakavaleuskaya/PulsePlate/dependabot/alerts/116`
- Repo evidence:
  - `requirements.in`
  - `requirements-ci-lite.in`
  - `requirements-dev.in`
  - `constraints.txt`
  - `requirements.txt`
  - `requirements-dev.txt`
  - `requirements-lock.txt`
  - `requirements-ci-lite.txt`
  - `scripts/ci/emergency_python_wheels.json`
  - `tests/fixtures/dependency_security_schema.json`
- Security note:
  - `docs/security/GHSA-v92g-xgxw-vvmm-mako.md`
  - `docs/security/MAKO_1_3_11_PRIVATE_INDEX_ADVISORY.md`

## Validation

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
.venv/bin/python -m pytest -q tests/test_dependency_security_guard.py
pre-commit run --all-files
make verify
```

## Merge / Return Rule

- Do not call the lane merge-ready until:
  - local gates are green,
  - the post-open `qa-engineer-agent -> bug-hunter` review pass is complete,
  - current-head required checks are green,
  - the canonical review artifact and PR body mirror are synchronized.
- Do not resume the paused security-epic/docs lane until this remediation PR is
  merged and local refs are re-synced from `main`; the governing seam remains
  `docs/roadmap/BACKLOG_LEDGER.md:1657-1678` and merged `PR #1433`
  (<https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1433>).
- After merge:
  - `git fetch --prune origin`
  - remove the merged local branch/worktree
  - `git worktree prune`
  - only then return to the next active Wave 6 docs/governance item recorded in
    `docs/roadmap/BACKLOG_LEDGER.md:1657-1678`.
