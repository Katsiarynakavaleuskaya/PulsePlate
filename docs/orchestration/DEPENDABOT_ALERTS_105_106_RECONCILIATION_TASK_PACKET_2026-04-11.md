# Dependabot Axios Alerts 105 + 106 Reconciliation Task Packet

## Summary

- **Date:** 11 April 2026
- **Stable `main` SHA:** `8374c977a56408599cdbcde97a0f1ff5dec01922`
- **Bundled alerts:** `#105` + `#106`
- **Package family:** `axios`
- **Advisories:** `GHSA-3p68-rc4w-qgx5`, `GHSA-fvcv-3m26-pcqx`
- **CVEs:** `CVE-2025-62718`, `CVE-2026-40175`
- **Patched floor:** `axios >= 1.15.0`
- **Lane mode:** coordinator-owned preparatory lane; no speculative npm upgrade
  churn in this PR

This packet governs the bundled reconciliation lane for open Dependabot alerts
`#105` and `#106` after `main` stabilized on
`8374c977a56408599cdbcde97a0f1ff5dec01922`. Clean-main evidence gathered for
this PR shows that the root repo still carries the live
`@goplus/agentguard -> axios` path, so this lane cannot honestly claim a stale
GitHub-only alert state yet. Steps 1-3 in this PR are therefore limited to
coordinator/ledger formalization, a repo-managed root npm dependency-submission
workflow, and documentation/audit corrections that reset the lane to verified
current-main truth before the follow-up remediation PR.

## Current-Head Truth

- `origin/main` is stable on `8374c977a56408599cdbcde97a0f1ff5dec01922`.
- GitHub still reports both alerts as `open`:
  - `#105` (`GHSA-3p68-rc4w-qgx5`, `CVE-2025-62718`)
  - `#106` (`GHSA-fvcv-3m26-pcqx`, `CVE-2026-40175`)
- Both alerts currently point to root `package-lock.json` in the GitHub npm
  dependency graph.
- Local root repo truth on stable `main`:
  - `package.json` still declares `@goplus/agentguard ^1.0.12`
    (`package.json:49`)
  - `package-lock.json` still contains
    `node_modules/@goplus/agentguard 1.0.12` (`package-lock.json:627`)
  - `package-lock.json` still records `axios ^1.6.7` under that dependency
    path (`package-lock.json:634`)
  - `package-lock.json` still contains `node_modules/axios 1.13.6`
    (`package-lock.json:784`)
  - `tools/agentguard/scan_text.mjs` still imports and instantiates
    `SkillScanner` from `@goplus/agentguard`
- `tests/test_root_npm_dependency_guards.py:97` confirms the AgentGuard-rooted
  dependency chain still exists in the root lock invariants.
- GitHub repo SBOM still reports `axios 1.13.6`, which matches current repo
  truth instead of proving graph drift by itself.

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
- Update security notes and recurring drift audit so they reflect verified
  clean-main repo truth instead of the earlier premature stale-alert framing

### Out of scope

- Root npm version bumps or lockfile churn beyond the dedicated follow-up
  remediation lane
- Frontend npm graph remediation
- Broad Dependabot config refactors across unrelated ecosystems
- Runtime API, bridge, or product behavior changes

## Acceptance Criteria for Steps 1-3

- Bundled packet exists and records the mandatory coordinator-owned role order
- Ledger carries explicit child items for both `#105` and `#106` under one
  bundled reconciliation lane
- `.github/workflows/npm-dependency-submission.yml` exists and stays scoped to
  root npm manifests only
- Security/audit docs describe verified clean-main truth and do not claim stale
  alert closure that current repo evidence cannot support
- The follow-up remediation lane is explicitly separated from this preparatory
  workflow/docs PR

## Evidence Requirements

- Live alert queries:
  - `gh api repos/Katsiarynakavaleuskaya/PulsePlate/dependabot/alerts/105`
  - `gh api repos/Katsiarynakavaleuskaya/PulsePlate/dependabot/alerts/106`
- Live SBOM query:
  - `gh api repos/Katsiarynakavaleuskaya/PulsePlate/dependency-graph/sbom`
- Local manifest / lockfile evidence:
  - `package.json:49`
  - `package-lock.json:627`
  - `package-lock.json:634`
  - `package-lock.json:784`
- Guard evidence:
  - `tests/test_root_npm_dependency_guards.py:97`
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

- This PR does not claim that the alerts are already stale on clean `main`.
- After this preparatory lane merges, open the minimum follow-up remediation
  lane that removes, replaces, or otherwise hardens the live
  `@goplus/agentguard -> axios` path on current `main`.
- Once the real runtime fix lands, use the new root npm dependency submission
  lane as the graph-refresh proof loop for alert closure.
