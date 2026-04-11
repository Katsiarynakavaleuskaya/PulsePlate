# Dependabot Axios Alerts 105 + 106 Reconciliation Task Packet

## Summary

- **Date:** 11 April 2026
- **Stable `main` SHA:** `8374c977a56408599cdbcde97a0f1ff5dec01922`
- **Bundled alerts:** `#105` + `#106`
- **Package family:** `axios`
- **Advisories:** `GHSA-3p68-rc4w-qgx5`, `GHSA-fvcv-3m26-pcqx`
- **CVEs:** `CVE-2025-62718`, `CVE-2026-40175`
- **Patched floor:** `axios >= 1.15.0`
- **Lane mode:** coordinator-owned reconciliation only; no speculative npm
  upgrade churn

This packet governs the bundled reconciliation lane for open Dependabot alerts
`#105` and `#106` after `main` stabilized on
`8374c977a56408599cdbcde97a0f1ff5dec01922`. The current repo truth no longer
proves a live root runtime `axios` carrier, so steps 1-3 for this lane are
limited to coordinator/ledger formalization, a repo-managed root npm
dependency-submission refresh mechanic, and documentation/audit updates that
frame the problem as dependency-graph divergence until GitHub graph state
converges.

## Current-Head Truth

- `origin/main` is stable on `8374c977a56408599cdbcde97a0f1ff5dec01922`.
- GitHub still reports both alerts as `open`:
  - `#105` (`GHSA-3p68-rc4w-qgx5`, `CVE-2025-62718`)
  - `#106` (`GHSA-fvcv-3m26-pcqx`, `CVE-2026-40175`)
- Both alerts currently point to root `package-lock.json` in the GitHub npm
  dependency graph.
- Local root repo truth on stable `main`:
  - `package-lock.json` does not contain `axios`
  - `package-lock.json` does not contain `@goplus/agentguard`
  - `npm ls axios` does not show a live root runtime path
- GitHub repo SBOM still reports `axios 1.13.6`.

## Mandatory Role Order

1. `agent-coordinator`
2. `security-auditor`
3. `backend-engineer`
4. `architecture-specialist` only if graph-refresh mechanics require workflow
   or policy changes
5. `qa-engineer-agent`
6. `bug-hunter`

Rules:

- This order is mandatory for the lane.
- No ad-hoc parallel role override may replace it.
- Any extra custom context is advisory only and must not mutate the mandatory
  role order.
- Mandatory post-open review lane remains `qa-engineer-agent -> bug-hunter`.

## Scope Lock

### In scope

- Formalize one bundled coordinator packet for alerts `#105` + `#106`
- Update backlog tracking so both alerts are carried in one reconciliation lane
- Add `.github/workflows/npm-dependency-submission.yml` as the repo-owned graph
  refresh mechanic for the root npm surface
- Update security notes and recurring drift audit so they describe graph drift,
  not a currently proven live runtime `axios` carrier

### Out of scope

- Root npm version bumps or lockfile churn without fresh proof of a live path
- Frontend npm graph remediation
- Broad Dependabot config refactors across unrelated ecosystems
- Runtime API, bridge, or product behavior changes

## Acceptance Criteria for Steps 1-3

- Bundled packet exists and records the mandatory coordinator-owned role order
- Ledger carries explicit child items for both `#105` and `#106` under one
  bundled reconciliation lane
- `.github/workflows/npm-dependency-submission.yml` exists and stays scoped to
  root npm manifests only
- Security/audit docs describe the current state as dependency-graph
  divergence/reconciliation
- No root npm dependency or lockfile contents change in this lane unless fresh
  evidence proves a live runtime path still exists

## Evidence Requirements

- Live alert queries:
  - `gh api repos/Katsiarynakavaleuskaya/PulsePlate/dependabot/alerts/105`
  - `gh api repos/Katsiarynakavaleuskaya/PulsePlate/dependabot/alerts/106`
- Live SBOM query:
  - `gh api repos/Katsiarynakavaleuskaya/PulsePlate/dependency-graph/sbom`
- Local manifest / lockfile evidence:
  - `package.json`
  - `package-lock.json`
- Guard evidence:
  - `tests/test_root_npm_dependency_guards.py`
  - `tests/test_remaining_modules.py`
- Reconciliation artifacts:
  - `.github/workflows/npm-dependency-submission.yml`
  - `docs/security/CVE-2025-62718-axios.md`
  - `docs/security/CVE-2026-40175-axios.md`
  - `docs/audit/DEPENDABOT_RECURRING_SECURITY_DRIFT_AUDIT_2026-04-10.md`

## Validation

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
pre-commit run --all-files
pytest -q tests/test_root_npm_dependency_guards.py
pytest -q tests/test_remaining_modules.py
gh api repos/Katsiarynakavaleuskaya/PulsePlate/dependabot/alerts/105
gh api repos/Katsiarynakavaleuskaya/PulsePlate/dependabot/alerts/106
gh api repos/Katsiarynakavaleuskaya/PulsePlate/dependency-graph/sbom
```

## Decision Rule

- If the root npm dependency submission lane refreshes GitHub graph state and
  both alerts close, stop here; do not open a speculative dependency-bump PR.
- If alerts remain open after the refresh on stable `main`, the next lane is a
  follow-up reconciliation/investigation step, not automatic npm churn.
