# Dependabot Alerts 118-119 pip Remediation Task Packet

## Summary

- **Date:** 25 April 2026
- **Stable starting branch:** `main`
- **Bundled alerts:** `#118`, `#119`
- **Package:** `pip`
- **Advisory:** `GHSA-58qw-9mgm-455v` / `CVE-2026-3219`
- **Vulnerable range:** `<=26.0.1`
- **First patched version:** none reported by GitHub on 2026-04-25
- **Worktree:** `worktrees/pip-unsafe-pin-remediation`
- **Branch:** `fix/pip-unsafe-pin-alerts-118-119`
- **Planned PR title:** `fix(deps): remove vulnerable pip unsafe pins`
- **Lane mode:** single coordinator-owned dependency-security remediation PR

This packet governs the narrow remediation lane for the two open Dependabot
alerts on unsafe `pip` lock entries. The lane is intentionally limited to
dependency lock cleanup, schema/guard synchronization, security evidence, and
merge governance.

## Coordinator Start

The lane was started with the canonical pre-edit gates:

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
python3 scripts/orchestration/task_bootstrap.py \
  --goal "Remediate Dependabot alerts 118 and 119 for pip GHSA-58qw-9mgm-455v without unrelated dependency churn" \
  --task-class "Security" \
  --pr-phase pre_open \
  --requested-agent agent-coordinator \
  --requested-agent security-auditor \
  --requested-agent backend-engineer \
  --requested-agent qa-engineer-agent \
  --requested-agent bug-hunter
```

Coordinator packet id: `1584d02b68fe`.

## Current-Head Truth

- GitHub Dependabot reports:
  - `#118` - `pip` in `requirements-dev.txt`
  - `#119` - `pip` in `requirements-lock.txt`
- Both alerts map to:
  - `GHSA-58qw-9mgm-455v`
  - `CVE-2026-3219`
  - vulnerable range `<=26.0.1`
  - first patched version `null`
- Pre-remediation repo evidence:
  - `requirements-dev.txt` pinned `pip==26.0`
  - `requirements-lock.txt` pinned `pip==26.0.1`
  - `tests/fixtures/dependency_security_schema.json` did not block vulnerable
    `pip` versions

## Mandatory Role Order

1. `agent-coordinator`
2. `security-auditor`
3. `backend-engineer`
4. `qa-engineer-agent`
5. `bug-hunter`

Rules:

- This role order is mandatory for the lane.
- `dev-operator` may be used only as an execution/evidence helper and does not
  replace the reviewer order.
- The mandatory post-open review pass remains `qa-engineer-agent -> bug-hunter`.
- No unrelated runtime, OpenAPI, frontend, iOS, Cloudflare, Sentry, Docker, or
  product behavior work may piggyback on this PR.

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
- PR lifecycle helpers:
  - `pulseplate-pr-review`
  - `create-pr`
  - `commit-work`
  - `ci-fix`
  - `coding-guidelines-verify`

## Scope Lock

### In scope

- Remove vulnerable unsafe `pip==26.0` from `requirements-dev.txt`
- Remove vulnerable unsafe `pip==26.0.1` from `requirements-lock.txt`
- Add `pip<=26.0.1` to the dependency security blocked-version schema
- Add dedicated security evidence for `GHSA-58qw-9mgm-455v`
- Open a draft PR, create the canonical review artifact, run the required
  post-open review pass, and complete merge-readiness governance

### Out of scope

- New runtime dependency pins or broad lock regeneration
- Frontend or npm dependency work
- OpenAPI regeneration or generated client types
- iOS, Cloudflare, Sentry, Docker, deployment, or product behavior changes
- Dismissing Dependabot alerts instead of fixing committed repo truth

## Expected Touched Surfaces

- `requirements-dev.txt`
- `requirements-lock.txt`
- `tests/fixtures/dependency_security_schema.json`
- `docs/security/GHSA-58qw-9mgm-455v-pip.md`
- `docs/orchestration/DEPENDABOT_ALERTS_118_119_PIP_REMEDIATION_TASK_PACKET_2026-04-25.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `docs/review/PR_<N>_FIXED_MAPPING.md`

## Acceptance Criteria

- Committed repo truth no longer pins vulnerable `pip` in `requirements-dev.txt`
  or `requirements-lock.txt`
- Dependency security schema blocks `pip<=26.0.1`
- Dedicated security note includes evidence and validation commands
- Alerts `#118-#119` are remediated by the PR
- Post-open review completes in mandatory order `qa-engineer-agent -> bug-hunter`
- Canonical fixed-mapping artifact and PR body mirror are synchronized before
  merge readiness

## Validation

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
.venv/bin/python -m pytest -q tests/test_dependency_security_guard.py
pre-commit run --all-files
make verify
```

## Merge / Return Rule

- Do not call the lane merge-ready until local gates are green, the post-open
  `qa-engineer-agent -> bug-hunter` pass is complete, current-head required
  checks are green, and the canonical review artifact and PR body mirror are
  synchronized.
- After merge, sync `main` with `git fetch --prune origin` and
  `git merge --ff-only origin/main`, verify `0 0`, then remove only this lane's
  branch/worktree/gitignored artifacts.
