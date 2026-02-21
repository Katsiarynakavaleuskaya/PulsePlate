# CI Throughput and Flake Budget Policy

**Date:** 2026-02-21
**Status:** Active policy (Wave 2)
**Exit Criteria:** This policy becomes permanent when: (1) median CI time reaches target (<=6 min), (2) flake budget tracking is automated in CI
**Purpose:** Reduce CI critical-path latency and manage test flakiness systematically

---

## CI Critical-Path Baseline

### Current Baseline (2026-02-21)

| Metric | Value | Target | Owner |
|--------|-------|--------|-------|
| **Median PR CI Time** | ~8 min | <=6 min | @katsiaryna_kavaleuskaya |
| **P95 PR CI Time** | ~15 min | <=10 min | @katsiaryna_kavaleuskaya |
| **Critical Path Jobs** | lint, test-pr, coverage-pr | Parallel where possible | DevEx |

### Critical Path Definition

The **critical path** is the sequence of jobs that determines total CI wall-clock time:

```text
PR opened
   |
   +-- lint (parallel)
   +-- test-pr (parallel, depends on lint for some checks)
   |      |
   |      +-- coverage-pr (sequential after test-pr)
   |
   +-- openapi-sync (parallel)
```

### Optimization Targets

1. **Parallelization:** Run independent jobs concurrently
2. **Caching:** Leverage pip/npm/SPM caches for dependency installation
3. **Test Sharding:** Split large test suites across workers (-n auto)
4. **Conditional Jobs:** Skip iOS/frontend tests when only backend changes

---

## Flake Budget Policy

### Definition

A **flaky test** is a test that fails non-deterministically (passes on retry without code changes).

### Budget Rules

| Category | Weekly Budget | Action on Exceed |
|----------|---------------|------------------|
| **Known Flaky (documented)** | 3 incidents/week | Immediate fix PR or skip with ledger entry |
| **Unknown Flaky (new)** | 0 tolerated | Root-cause analysis required within 24h |
| **Infrastructure Flake** | 2 incidents/week | Infra team triage |

### Flake Classification

| Class | Description | Retry Policy | Tracking |
|-------|-------------|--------------|----------|
| **Test Logic** | Non-deterministic test code (timing, ordering) | No retry | Fix required |
| **Environment** | Runner resource limits, network, disk | 1 retry allowed | Track frequency |
| **Third-Party** | External service timeouts, rate limits | 1 retry allowed | Mock if persistent |
| **Infrastructure** | CI runner issues, cache corruption | 2 retries allowed | Escalate to GitHub |

### Retry Policy

**Hard Rule:** Retries are only allowed for documented flaky test classes with evidence.

**Forbidden:**

- Blanket continue-on-error: true on test jobs
- Unconditional retries without flake classification
- Masking failures with || true

---

## Flake Burn-Down Process

### Weekly Review (Every Monday)

1. **Collect:** Gather flaky test incidents from past week
2. **Classify:** Assign each to a flake class
3. **Prioritize:** Rank by frequency and blast radius
4. **Assign:** Owner commits to fix/skip with deadline
5. **Track:** Update BACKLOG_LEDGER.md with flake entries

---

## Monitoring and Alerts

### CI Health Dashboard (Planned)

| Metric | Source | Alert Threshold |
|--------|--------|-----------------|
| Median CI Time | GitHub Actions API | >8 min |
| Flaky Test Rate | Test result parsing | >5% |
| Cache Hit Rate | Actions cache stats | <80% |
| Queue Wait Time | Runner availability | >2 min |

---

## Ownership Map

| Area | Owner | Responsibility |
|------|-------|----------------|
| **CI Workflow** | @katsiaryna_kavaleuskaya | Workflow optimization, job parallelization |
| **Test Determinism** | @katsiaryna_kavaleuskaya | Flake prevention, xdist stability |
| **Cache Strategy** | @katsiaryna_kavaleuskaya | Dependency caching, build artifacts |
| **Flake Triage** | @katsiaryna_kavaleuskaya | Weekly review, burn-down tracking |

---

## KPIs (Wave 2 Target)

- **Median CI Time:** Reduced from baseline (~8 min) to <=6 min
- **Flaky Failure Rate:** Trending down over 8 weeks
- **Known Flakes Documented:** 100% (no silent retries)

---

## References

- AGENTS.md: Hard Gates (Non-negotiable)
- Test Policy: tests/AGENTS.md
- Wave 2 Execution Pack: docs/roadmap/WAVE_2_3_EXECUTION_PACK.md

---

**Last updated:** 2026-02-21
