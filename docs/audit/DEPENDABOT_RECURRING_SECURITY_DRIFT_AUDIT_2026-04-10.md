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

### Shared `axios` drift: alerts `#105` + `#106`

- GitHub Dependabot alert `#105` (`axios`, `GHSA-3p68-rc4w-qgx5`,
  `CVE-2025-62718`) remained `open`.
- GitHub Dependabot alert `#106` (`axios`, `GHSA-fvcv-3m26-pcqx`,
  `CVE-2026-40175`) remained `open`.
- GitHub still points both alerts to root `package-lock.json`.
- Local root graph evidence does not show `axios` in `package-lock.json`.
- Local root graph evidence does not show `@goplus/agentguard` in
  `package-lock.json`.
- Guard tests already enforce the removed runtime path.
- GitHub repo SBOM still reported:
  - `@goplus/agentguard 1.0.12`
  - `axios 1.13.6`

### Config asymmetry before repo-owned npm refresh

- `.github/dependabot.yml` currently covers only the `pip` ecosystem.
- A repo-managed dependency submission workflow exists only for Python:
  `.github/workflows/python-dependency-submission.yml`.
- No parallel npm-specific repo-managed dependency submission lane was present
  at audit open time.

### Current reconciliation lane change

- The repo now adds `.github/workflows/npm-dependency-submission.yml` as the
  minimum root npm dependency submission lane.
- The workflow is intentionally narrow:
  - root npm manifests only
  - dependency submission only
  - excludes `frontend`, `node_modules`, `worktrees`, `.venv`
- This lane is meant to refresh GitHub graph truth for the root npm surface
  without reopening speculative dependency churn.

### Historical pattern

- The repo already tracks a broader stale-alert family in
  `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-reconcile-open-dependabot-alerts`.
- Prior narrow security PRs correctly fixed immediate vulnerable paths, but
  alert closure sometimes lagged because GitHub graph state did not refresh in
  sync with repo truth.

## Root Cause Classes

### 1. GitHub dependency graph / SBOM lag

The strongest current signal is the mismatch between committed lockfiles and the
live GitHub SBOM. This means a successfully merged remediation PR is not always
enough to make GitHub immediately agree with repo truth.

### 2. Historically missing npm-specific repo-managed dependency submission lane

Python dependency submission was explicit and repo-managed while npm lacked an
equivalent lane when this audit was opened. That asymmetry left GitHub graph
refresh for Node surfaces dependent on ambient GitHub parsing rather than an
explicit repo-owned submission contract.

### 3. Partial Dependabot ecosystem coverage

Dependabot configuration currently expresses only `pip` updates. Even when npm
alerts are visible in GitHub, the repo does not yet own a symmetrical
Dependabot/update/submission strategy across all active package ecosystems.

### 4. Narrow PRs without synchronized graph-refresh proof

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

1. Keep the root npm dependency submission lane narrow and repo-owned so GitHub
   graph refresh is explicit rather than ambient.
2. Extend the stale-alert reconciliation ledger with alert-family-specific child
   items whenever GitHub graph state diverges from repo truth.
3. After every narrow dependency remediation PR, require a post-merge
   dependency-graph recheck:
   - alert state,
   - SBOM/package view,
   - current-head workflow completion.
4. Keep security PRs narrow, but attach a recurring-drift audit whenever the
   repo is already patched and GitHub still reports the old graph.

## Decision Log

- Default remediation mode remains **narrow PR + separate audit**.
- The repo should not treat every repeated alert as a signal to perform broad
  package churn.
- The first question is always whether GitHub is wrong about current repo truth.
- For alerts `#105` + `#106`, the current narrow lane answer is "refresh graph
  truth first, then re-evaluate."
