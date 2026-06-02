# Dependabot Recurring Security Drift Audit

## Summary

**Date:** 10 April 2026

This audit explains why security issues appear to "keep falling" in the repo
even after narrow remediation PRs land. The dominant problem is not only
vulnerable packages. It is repeated **desynchronization** between:

- committed repo manifests and lockfiles,
- GitHub dependency graph / SBOM state,
- Dependabot alert lifecycle,
- repo-managed dependency submission coverage.

## Observed Facts

### Shared `axios` alert state: alerts `#105` + `#106`

- GitHub Dependabot alert `#105` (`axios`, `GHSA-3p68-rc4w-qgx5`,
  `CVE-2025-62718`) remained `open`.
- GitHub Dependabot alert `#106` (`axios`, `GHSA-fvcv-3m26-pcqx`,
  `CVE-2026-40175`) remained `open`.
- GitHub still points both alerts to root `package-lock.json`.
- Clean `main` repo evidence still shows a live root npm carrier:
  - `package.json:49` — root dependency still declares
    `@goplus/agentguard ^1.0.12`
  - `package-lock.json:627` — root lockfile still contains
    `node_modules/@goplus/agentguard 1.0.12`
  - `package-lock.json:634` — `@goplus/agentguard` still declares
    `axios ^1.6.7`
  - `package-lock.json:784` — root lockfile still contains
    `node_modules/axios 1.13.6`
- Runtime bridge evidence also still points to the external package:
  - `tools/agentguard/scan_text.mjs:6` — imports `SkillScanner` from
    `@goplus/agentguard`
  - `tools/agentguard/scan_text.mjs:39` — instantiates `SkillScanner`
- Guard tests currently prove that the AgentGuard dependency chain still exists,
  not that it was removed:
  - `tests/test_root_npm_dependency_guards.py:97`
- GitHub repo SBOM still reported:
  - `@goplus/agentguard 1.0.12`
  - `axios 1.13.6`

Current conclusion: on clean `origin/main`, GitHub's alert/SBOM view is still
aligned with repo manifests and the root lockfile. The earlier stale-alert /
graph-drift framing is therefore not yet proven for this alert family.

### Frontend `vitest` alert state: alert `#153`

- GitHub Dependabot alert `#153` (`vitest`, `GHSA-5xrq-8626-4rwp`,
  `CVE-2026-47429`) remained `open` on 2026-06-02.
- GitHub points the alert to `frontend/package-lock.json`.
- The affected range is `<4.1.0`; the first patched version is `4.1.0`.
- Clean `main` repo evidence already shows the frontend Vitest dependency stack
  pinned at `4.1.8`:
  - `frontend/package.json` declares `vitest`, `@vitest/coverage-v8`, and
    `@vitest/expect` at `4.1.8`
  - `frontend/package-lock.json` resolves the direct Vitest package to `4.1.8`
- GitHub repo SBOM still reported:
  - `vitest 3.2.4`

Current conclusion: unlike the `axios` alert family above, alert `#153` is
confirmed dependency-graph drift. Repo lock truth is patched above the vulnerable
range, but GitHub's graph has not yet ingested the frontend npm lockfile state.
Docker and Trivy evidence do not directly close this Dependabot dependency-graph
alert.

### Config asymmetry before repo-owned npm refresh

- `.github/dependabot.yml` currently covers only the `pip` ecosystem.
- A repo-managed dependency submission workflow exists only for Python:
  `.github/workflows/python-dependency-submission.yml`.
- No parallel npm-specific repo-managed dependency submission lane was present
  at audit open time.

### Current reconciliation lane change

- The repo now adds `.github/workflows/npm-dependency-submission.yml` as the
  minimum root npm dependency submission lane and extends it with a separate
  frontend npm dependency submission job for `/frontend`.
- The workflow is intentionally narrow:
  - root npm manifests in the root job only
  - frontend npm manifests in the frontend job only, via a temporary graph root
    that preserves `frontend/package-lock.json` as the submitted manifest path
  - dependency submission only
  - the root job excludes `frontend`, `node_modules`, `worktrees`, `.venv`
  - the frontend job prepares a temporary graph root with only the frontend npm
    manifests and excludes local/dev artifacts such as `node_modules`,
    `worktrees`, `.venv`
- This lane is meant to refresh GitHub graph truth for the root and frontend npm
  surfaces without reopening speculative dependency churn.

### Historical pattern

- The repo already tracks a broader stale-alert family in
  `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-reconcile-open-dependabot-alerts`.
- Prior narrow security PRs correctly fixed immediate vulnerable paths, but
  alert closure sometimes lagged because GitHub graph state did not refresh in
  sync with repo truth.

## Root Cause Classes

### 1. Current clean-`main` truth still carries the live root npm path

Before calling the alert family "stale", the repo must first verify current
`main`. On clean `origin/main`, the root manifest, root lockfile, and runtime
bridge still carry the `@goplus/agentguard -> axios` path. That means the
current blocker is not purely SBOM lag.

### 2. Historical stale-alert framing was opened before current-head truth was re-verified

The repo already had a broader stale-alert family open, but this specific
`axios` bundle inherited that framing too early. The clean-main recheck shows
that the `#105` / `#106` hypothesis must be corrected back to "live path still
present until proven otherwise".

### 3. Historically missing npm-specific repo-managed dependency submission lane

Python dependency submission was explicit and repo-managed while npm lacked an
equivalent lane when this audit was opened. That asymmetry still matters as a
process gap because the repo needs an explicit post-remediation graph-refresh
loop once the actual runtime fix lands.

### 3a. Frontend graph submission gap after Vitest remediation

Alert `#153` proves a more specific gap: root npm dependency submission alone is
not enough for nested npm workspaces when the vulnerable package lives under
`/frontend`. The workflow must submit frontend npm lockfile state explicitly,
with a frontend-scoped correlator and a repo-relative manifest source location,
so GitHub can update the graph entry attached to `frontend/package-lock.json`.

### 4. Partial Dependabot ecosystem coverage

Dependabot configuration currently expresses only `pip` updates. Even when npm
alerts are visible in GitHub, the repo does not yet own a symmetrical
Dependabot/update/submission strategy across all active package ecosystems.

### 5. Narrow PRs without synchronized graph-refresh proof

Narrow remediation is still the correct default for security work. The missing
piece is an explicit post-merge proof loop for dependency-graph convergence.
Without that loop, the repo accumulates “fixed in code, still open in GitHub”
security debt.

## Plugin Surface Inventory

These surfaces were checked only as inventory context and were not found to be
direct causes of the remaining `axios` alert family (`#105` + `#106`).

### GitHub

- Primary recurring-drift source.
- Relevant surfaces:
  - Dependabot alert lifecycle
  - dependency graph / SBOM
  - dependency submission workflows
  - current-head CI truth

### Hugging Face

- Python dependency inventory shows `huggingface-hub==1.5.0`.
- No direct link to the current `axios` alert family was found during this
  audit.

### Cloudflare

- Only workflow/config/CDN references were found.
- No direct vulnerable package path linked to the current `axios` alert family
  was found.

### Sentry

- No direct dependency path tied to the current `axios` alert family was found
  in the current repo surfaces inspected for this audit.

## Recommended Prevention Follow-Ups

1. Keep the root and frontend npm dependency submission lanes narrow and
   repo-owned so GitHub graph refresh is explicit rather than ambient after the
   runtime dependency fix lands.
2. Require a clean-`main` manifest/lockfile recheck before classifying an alert
   as dependency-graph drift.
3. Extend the stale-alert reconciliation ledger with alert-family-specific child
   items whenever GitHub graph state actually diverges from repo truth.
4. After every narrow dependency remediation PR, require a post-merge
   dependency-graph recheck:
   - alert state,
   - SBOM/package view,
   - current-head workflow completion.
5. For alert `#153`, confirm `NPM Dependency Submission` succeeds on `main` and
   the frontend graph no longer reports `vitest@3.2.4` before treating the
   Dependabot alert as graph-converged.
6. Keep security PRs narrow, but do not use a recurring-drift audit as a
   substitute for fixing a still-live runtime dependency path.

## Decision Log

- Default remediation mode remains **narrow PR + separate audit**.
- The repo should not treat every repeated alert as a signal to perform broad
  package churn.
- The first question is always whether GitHub is wrong about current repo truth.
- For alerts `#105` + `#106`, the clean-main answer in this PR is:
  "current repo truth still carries the live path; add the repo-owned npm
  submission lane now, then open the minimum remediation follow-up."
- For alert `#153`, the clean-main answer is different: frontend lock truth is
  already patched to `vitest@4.1.8`, while GitHub dependency graph / SBOM still
  reports `vitest@3.2.4`; add frontend npm dependency submission and verify graph
  convergence after the workflow runs on `main`.
