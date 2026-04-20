# Dependabot Alert 105 Reconciliation Task Packet

> Historical packet retained for provenance. Bundled successor:
> `docs/orchestration/DEPENDABOT_ALERTS_105_106_RECONCILIATION_TASK_PACKET_2026-04-11.md`.

## Summary

- **Date:** 10 April 2026
- **Alert:** `#105`
- **Package:** `axios`
- **Advisory:** `GHSA-3p68-rc4w-qgx5`
- **CVE:** `CVE-2025-62718`
- **Patched floor:** `1.15.0`
- **Scope mode:** narrow security lane + separate recurring-drift audit

This packet governs the replacement security lane for GitHub Dependabot alert
`#105` after merged PR `#1384` (`fd21501e08ea078db3db595e1b625a5470941926`)
removed the external root runtime path `@goplus/agentguard -> axios`, but the
live GitHub alert and repo SBOM still reported the stale vulnerable graph on
`10 April 2026`.

Historical note: the stale-alert hypothesis recorded here does not match the
clean-`main` evidence re-verified on `11 April 2026` for PR `#1394`. Keep this
file for provenance only; use the bundled successor packet as the corrected SoT.

## Current-Head Truth

- Local repo state:
  - `package.json` still declares `@goplus/agentguard ^1.0.12`
  - `package-lock.json` still contains
    `node_modules/@goplus/agentguard 1.0.12`
  - `package-lock.json` still contains `node_modules/axios 1.13.6`
- Guard evidence:
  - `tests/test_root_npm_dependency_guards.py:97`
  - `tests/test_remaining_modules.py`
- Live GitHub state on `10 April 2026`:
  - Dependabot alert `#105` remained `open`
  - Repo SBOM still reported `@goplus/agentguard 1.0.12`
  - Repo SBOM still reported `axios 1.13.6`
- Merge commit current-head CI for `fd21501e08ea078db3db595e1b625a5470941926`
  was still stabilizing when this packet was opened, so follow-up branch work
  must use current-head `main` truth only after the remaining canonical jobs
  finish.

## Role Order

1. `agent-coordinator`
2. `security-auditor`
3. `backend-engineer`
4. `architecture-specialist` only if dependency-graph refresh mechanics require
   workflow or graph-policy changes
5. `qa-engineer-agent`
6. `bug-hunter`

Mandatory post-open review lane remains `qa-engineer-agent -> bug-hunter`.

## Scope Lock

### In scope

- Reconcile alert `#105` against live `main`
- Capture evidence that the repo runtime graph is already remediated or apply
  the minimum additional scanner-refresh mechanic required to close the stale
  GitHub dependency state
- Update the canonical remediation note for `CVE-2025-62718`
- Open a replacement PR only after current-head `main` health is confirmed
- Record recurring-drift findings in a separate audit artifact and backlog lane

### Out of scope

- Broad dependency refreshes
- Unrelated npm, pip, frontend, iOS, or infra dependency remediation waves
- Runtime interface or bridge contract changes
- Hugging Face / Cloudflare / Sentry product changes without a direct alert path

## Evidence Requirements

- Live alert query:
  - `gh api repos/Katsiarynakavaleuskaya/PulsePlate/dependabot/alerts/105`
- Live SBOM query:
  - `gh api repos/Katsiarynakavaleuskaya/PulsePlate/dependency-graph/sbom`
- Local manifest / lockfile evidence:
  - `package.json`
  - `package-lock.json`
- Guard evidence:
  - `tests/test_root_npm_dependency_guards.py`
  - `tests/test_remaining_modules.py`
- Canonical remediation note:
  - `docs/security/CVE-2025-62718-axios.md`
- Separate recurring-drift audit:
  - `docs/audit/DEPENDABOT_RECURRING_SECURITY_DRIFT_AUDIT_2026-04-10.md`

## PR Lane Decision

- If current-head `main` finishes green and the alert auto-closes after GitHub
  graph refresh, do not open a synthetic remediation PR. Open a narrow
  reconciliation/evidence PR only if documentation or audit artifacts still
  need to land.
- If current-head `main` still shows the live `@goplus/agentguard -> axios`
  path, do not reuse this stale-alert assumption. Open a replacement PR on top
  of `origin/main` with the minimum runtime remediation needed to remove or
  replace that path, then use graph refresh as the proof loop.
- Do not reuse the already-merged PR `#1384` lane for new review activity.
