# PR-585 — Backlog Sweep Audit

**Date:** 2026-01-25
**Target branch:** `main`
**Source branch:** `docs/pr-585-backlog-sweep`
**CI:** ✅ green (docs-only)
**Author:** @katsiaryna_kavaleuskaya

## Purpose

Systematic inventory of all technical debt, skips, TODOs, policy exceptions, and thin-client violations across the repository. **No fixes in this PR** — inventory only.

---

## Sweep Categories & Findings

### A1. Tests / Skipping

| File:Line | Marker | Reason | Priority | Target PR |
|-----------|--------|--------|----------|-----------|
| `tests/test_level_es.py:13` | `pytestmark = pytest.mark.skip` | Unknown (investigate) | P2 | TBD |
| `tests/test_bmi_visualization.py:523` | `@pytest.mark.xfail` | Test isolation issue in full suite | P1 | TBD |
| `tests/test_app_coverage_unit_combined.py:81` | `@pytest.mark.skip` | interpret_group removed with bmi_core.py | P2 | TBD |
| `tests/test_app_coverage_unit_combined.py:86` | `@pytest.mark.skip` | estimate_level removed with bmi_core.py | P2 | TBD |
| `tests/test_app_branching_and_errors.py:185` | `@pytest.mark.xfail` | Module reload/patching not supported | P1 | TBD |
| `tests/test_repo_policy_guards.py:85` | `@pytest.mark.skip` | TODO: sys.modules cleanup in follow-up PR | P1 | TBD |
| `tests/test_app_plate_helpers.py:145` | `pytest.xfail` | Unknown (investigate) | P2 | TBD |
| `tests/test_update_manager_fixed.py:129` | `@pytest.mark.skip` | Update manager path attribute issues | P2 | TBD |
| `tests/test_food_apis_coverage_errors.py:303,331,351,396,416,437` | `@pytest.mark.skip` (6x) | Mock doesn't prevent exception / method signature issues | P2 | TBD |

**iOS Tests:**

| Location | Marker | Reason | Priority | Target PR |
|----------|--------|--------|----------|-----------|
| `ios/PulsePlate.xcodeproj/project.pbxproj:43-52` | `membershipExceptions` | AnimationTests.swift excluded (missing types) | P1 | PR-564+ |
| `.github/workflows/ci.yml:633` | `-skip-testing:PulsePlateUITests` | UI tests unstable | P1 | TBD |

---

### A2. Tech Debt Markers (TODO/FIXME/HACK)

**Backend (P1/P2 — mixed priorities):**

| File:Line | Content | Priority | Target PR |
|-----------|---------|----------|-----------|
| `core/business_bayesian_analyzer.py:145` | TODO: Replace with actual metrics from telemetry | P2 | TBD |
| `core/business_bayesian_analyzer.py:1067` | TODO: Integrate actual telemetry/metrics | P2 | TBD |
| `legacy_app.py:1985` | TODO: Read version from pyproject.toml | P2 | TBD |
| `app/middleware/api_tiers.py:146` | TODO: Implement database lookup for production | P1 | TBD |
| `app/middleware/api_tiers.py:284` | TODO: Implement database lookup | P1 | TBD |
| `app/routers/premium_week.py:97,127` | TODO: Add i18n support | P2 | TBD |
| `app/routers/pro.py:152,182,529,537` | TODO: i18n, dedup, meal logging integration | P2 | TBD |
| `app/schemas/bayes_adherence.py:29` | TODO(SEC-001): Add per-API-key rate limiting | P1 | TBD |

**iOS (already tracked in BACKLOG_LEDGER):**

| File:Line | Content | Status |
|-----------|---------|--------|
| `ios/PulsePlate/ViewModels/BMICalculatorViewModel.swift:6,9,14,19` | TODO: Migrate to DTO/APIError | ✅ Tracked |
| `ios/PulsePlate/Services/BMIService.swift:52,58,90` | TODO: Remove legacy shims | ✅ Tracked |
| `ios/PulsePlateTests/Mocks/MockBMIService.swift:5` | TODO: Update to use DTO | ✅ Tracked |

---

### A3. CI / Policy Exceptions

**Security Suppressions (with expiry):**

| File | CVE/Item | Expiry | Status |
|------|----------|--------|--------|
| `trivy/ignore-policy.rego` | CVE-2026-0915, CVE-2025-15281 | 2026-03-01 | ✅ Tracked |
| `.trivyignore` | ~25 CVEs (documented) | Various / None | ⚠️ Review needed |

**CI Exceptions:**

| File:Line | Exception | Reason | Priority |
|-----------|-----------|--------|----------|
| `.github/workflows/ci.yml:126` | `SKIP: no-commit-to-branch` | Pre-commit skip for branch protection | ✅ Intentional |
| `.github/workflows/pr-tests.yml:7` | `branches-ignore` | Skip for certain branches | ✅ Intentional |
| `.github/workflows/pr-coverage.yml:122-140` | `--exclude` patterns | Coverage excludes | ✅ Intentional |

---

### A4. Deprecated API Surface / Legacy

**Deprecated Endpoints:**

| Router | Path | Status | Migration Path |
|--------|------|--------|----------------|
| `app/routers/bmi_pro.py:158` | `/api/v1/pro/bmi` (POST, legacy calc) | DEPRECATED | `/api/v1/pro/bmi/calculate` |
| `app/routers/bmi_pro_legacy_alias.py:29` | `/api/v1/bmi/pro` | DEPRECATED | `/api/v1/pro/bmi` |
| `app/routers/premium_week.py:179` | `/api/v1/premium/plan/week-flexible` | DEPRECATED | `/api/v1/pro/meal/weekly` |
| `app/routers/vip.py:706` | `/api/v1/vip/menu/weekly` (legacy) | DEPRECATED | Canonical VIP endpoint |

**Legacy Modules:**

| Module | Purpose | Status |
|--------|---------|--------|
| `legacy_app.py` | Thin compatibility proxy | ✅ Policy-compliant |
| `bmi_core.py` | Legacy BMI oracle | ⚠️ Being phased out |

---

### A5. Thin-Client Violations

**iOS:**

| File:Line | Issue | Priority | Target PR |
|-----------|-------|----------|-----------|
| `ios/PulsePlate/Models/NutritionData.swift:60` | `URLSession.shared.data` (not APIClient) | P1 | PR-563+ |
| `ios/PulsePlate/Views/DebugToolsScreen.swift:97` | `URLSession.shared.data` | P2 | Debug tools, acceptable |
| `ios/PulsePlate/Services/ShoppingListService.swift` | Uses URLSession directly | P1 | ✅ Tracked |
| `ios/PulsePlate/Services/WeeklyPlanService.swift` | Uses URLSession directly | P1 | ✅ Tracked |

**Frontend (Web):**

| File:Line | Issue | Status |
|-----------|-------|--------|
| `frontend/src/api/openapi.json` | Contains threshold examples (18.5, 25.0) | ✅ OK — contract documentation |
| `frontend/src/api/schema.ts` | Contains threshold examples | ✅ OK — generated from OpenAPI |
| `frontend/src/api/bmi.ts:23` | `calculateBMI` function | ✅ OK — thin HTTP wrapper |

---

## Summary

| Category | Count | P0 | P1 | P2 |
|----------|-------|----|----|----|
| Test skips/xfails | 15 | 0 | 5 | 10 |
| Tech debt TODOs | 12 | 0 | 4 | 8 |
| Security suppressions | 27 | 0 | 2 (expiry) | 25 |
| Deprecated endpoints | 4 | 0 | 0 | 4 |
| Thin-client violations | 4 | 0 | 3 | 1 |

---

## Next Steps

1. ✅ Add all findings to `docs/roadmap/BACKLOG_LEDGER.md`
2. Continue with PR-563 (iOS Thin HTTP Adapter) — P0
3. Continue with PR-564 (Web Thin HTTP Adapter) — P0
4. Address P1 items in subsequent PRs

---

## Verification Commands

```bash
# Test skips/xfails
rg -n "@pytest\.mark\.(skip|xfail)" tests/

# TODO/FIXME
rg -n "\b(TODO|FIXME)\b" app core --type py | head -50

# Deprecated endpoints
rg -n "deprecated=True" app/routers/

# iOS thin-client violations
rg -n "URLSession\.shared\.data" ios/

# Security suppressions with expiry
rg -n "Suppression expires" trivy .trivyignore
```

---

**Last updated:** 2026-01-25
**Maintainer:** @katsiaryna_kavaleuskaya
