# PR Audit — Analytics Indexes + Guards (Vendor-agnostic)

**Date:** 11 February 2026
**Scope:** docs + tests (no runtime changes)
**Status:** Opinion + Evidence (commands are reproducible; outputs are examples)

---

## Summary

This PR adds a minimal, vendor-agnostic analytics surface under `docs/analytics/*` and enforces its existence and
minimum structure via deterministic guard tests.

The goal is to prevent two recurring failure modes:

1. **Metric drift**: metric semantics exist only in dashboards or in memory, and change silently.
2. **Experiment drift**: experiments run without a registry, owners, or explicit “ship/reject” decision trails.

This PR explicitly avoids introducing new agent roles. Instead, it expands the scope of the existing
`data-scientist-agent` to serve as the single drafting hub for analytics/metrics/experimentation artifacts.

---

## Scope / Non-goals

### In scope

- Vendor-agnostic analytics docs (templates + minimal SoT)
- Deterministic guard tests that prevent accidental deletion/drift of those docs
- Updating the existing `data-scientist-agent` instructions to reference these artifacts

### Out of scope

- Any runtime telemetry collection
- Any vendor/tool decisions (Amplitude/Mixpanel/Grafana/etc.)
- Any “analytics database” or pipelines
- Creating new agents (analytics/BI/data-quality/etc.)

---

## Evidence (repo truth)

### 1) Analytics docs are present

Command:

```bash
ls docs/analytics
```

Expected files:

- `README.md`
- `ANALYTICS_INDEX.md`
- `METRICS_CATALOG.md`
- `DATA_CATALOG.md`
- `EXPERIMENT_REGISTRY.md`

### 2) Data scientist agent references analytics artifacts (no new agent added)

Command:

```bash
rg -n \"docs/analytics/\" .cursor/agents/data-scientist-agent.md
```

Interpretation:

- Analytics/metrics/experiments are handled by the existing `data-scientist-agent` role.

### 3) Guards are deterministic and do not write snapshots

Command:

```bash
pytest -q tests/test_analytics_docs_guards.py
```

Interpretation:

- Tests fail with actionable messages if canonical docs are missing or stripped of required sections.
- Tests do not perform time-based checks and do not write any snapshot files.

---

## DoD (what “done” means)

- [ ] `docs/analytics/*` exists and is vendor-agnostic (templates usable immediately)
- [ ] `data-scientist-agent` explicitly references `docs/analytics/*` as its context (no new agent added)
- [ ] Guard tests enforce existence + minimum structure deterministically
- [ ] Quality gates pass (`make verify`)
