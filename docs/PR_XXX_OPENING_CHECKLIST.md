# PR-XXX Opening Checklist

**Date:** 2026-01-22
**Status:** ✅ Ready to open

---

## Pre-PR Checks

- [x] All tests passing (10 tests)
- [x] No BMI math in transport layer (grep verified)
- [x] DTOs aligned with backend schema (`app/schemas/bmi.py`)
- [x] Contract freeze documented
- [x] Technical debt tracked in BACKLOG_LEDGER.md
- [x] Legacy shims documented and isolated
- [x] Documentation updated (AGENTS.md, BACKLOG_LEDGER.md)
- [x] PR description ready (`docs/PR_XXX_DESCRIPTION_FINAL.md`)

---

## PR Opening Steps

### 1. Create PR Branch

```bash
# If not already on feature branch
git checkout -b feat/ios-thin-http-adapter

# Commit all changes (or use atomic commits from PR_XXX_COMMIT_STRUCTURE.md)
git add .
git commit -m "feat(ios): implement thin HTTP adapter for BMI service

Transport layer:
- HTTPClient: error mapping (422 vs 400/500)
- APIClient: request builder (URL, headers, JSON encoding)
- BMIService: thin wrapper (canonical path, DTO passthrough)
- DTOs aligned to backend schema (app/schemas/bmi.py)

Tests:
- 10 tests passing (HTTPClient, APIClient, BMIService)
- Contract boundary verified (422/400/500, snake_case, canonical path)
- Anti-flake: tearDown() resets StubURLProtocol.handler

Compatibility shims (temporary):
- LegacyBMIServicing/DefaultBMIService for existing UI
- UI migration tracked in BACKLOG_LEDGER.md (P1 item)

Documentation:
- AGENTS.md: thin client policy + no dual-path networking rule
- BACKLOG_LEDGER.md: UI migration tracking
- Technical debt report: docs/audit/PR_XXX_TECHNICAL_DEBT_REPORT.md

See: docs/audit/PR_XXX_THIN_CLIENT_HTTP_ADAPTER_AUDIT_TEMPLATE.md"

# Push branch
git push -u origin feat/ios-thin-http-adapter
```

### 2. Create PR on GitHub

**Title:**
```
feat(ios): thin HTTP adapter for BMI (transport layer)
```

**Description:**
- Copy entire content from `docs/PR_XXX_DESCRIPTION_FINAL.md`
- Ensure all links are correct (relative paths work in GitHub)

**Labels:**
- `enhancement`
- `ios`
- `networking`
- `backend-integration`

**Reviewers:**
- CodeRabbit (if configured)
- Human reviewer (if needed)

**Assignees:**
- @katsiaryna_kavaleuskaya

---

## Post-PR Actions

### 1. Monitor CI

- [ ] Wait for CI to pass
- [ ] Check test results (10 tests should pass)
- [ ] Verify no linter errors

### 2. Address Review Comments

**Common CodeRabbit comments (prepared responses):**

**Q: "Why is there code duplication (DefaultBMIService vs BMIService)?"**

**A:** This is temporary technical debt to unblock compilation without breaking existing UI code. Legacy shims are isolated (lines 48-159 in BMIService.swift) and will be removed in follow-up PR. See:
- `docs/audit/PR_XXX_TECHNICAL_DEBT_REPORT.md` (detailed analysis)
- `docs/roadmap/BACKLOG_LEDGER.md` (P1 item: "Migrate BMICalculatorViewModel + Screen to BMICalculate*DTO")

**Q: "Why are there two error types (BMIServiceError vs APIError)?"**

**A:** `BMIServiceError` is legacy error type for backward compatibility with existing UI code. It will be removed when UI migrates to new DTOs. New code should use `APIError` from `Networking/APIError.swift`. See technical debt report for details.

**Q: "Why does BMICalculatorViewModel still use legacy types?"**

**A:** UI migration is deferred to separate PR to keep this PR focused on transport layer only. ViewModel migration is tracked in BACKLOG_LEDGER.md (P1 item). This PR adds new transport layer without breaking existing UI.

**Q: "Shouldn't ShoppingListService/WeeklyPlanService also use APIClient?"**

**A:** Yes, that's tracked in BACKLOG_LEDGER.md (P1 item: "Unify ShoppingListService / WeeklyPlanService under thin HTTP adapter"). This PR establishes the pattern; other services will migrate in follow-up PRs. See AGENTS.md "No dual-path networking" rule.

### 3. After Merge

- [ ] Update BACKLOG_LEDGER.md: mark PR-XXX as merged
- [ ] Create follow-up PR for UI migration (P1)
- [ ] Create follow-up PR for Web thin adapter (P0)

---

## Quick Self-Review (2 minutes)

**Run these commands before opening PR:**

```bash
# 1. Verify no BMI math in transport layer
grep -r "18\.5\|24\.9\|25\|30" ios/PulsePlate/Networking/ ios/PulsePlate/Services/BMIService.swift | grep -v "test\|TODO\|comment\|legacy" || echo "✅ OK"

# 2. Verify tests pass
cd ios && xcodebuild -project PulsePlate.xcodeproj -scheme PulsePlate \
  -destination 'platform=iOS Simulator,name=iPhone 16' \
  -only-testing:PulsePlateTests/HTTPClientTests \
  -only-testing:PulsePlateTests/APIClientTests \
  -only-testing:PulsePlateTests/BMIServiceThinAdapterTests test 2>&1 | grep -E "(passed|failed)" | tail -5

# 3. Verify documentation exists
ls -la docs/PR_XXX_*.md docs/audit/PR_XXX_*.md || echo "⚠️ Missing docs"
```

---

## Success Criteria

**PR is ready to merge when:**

- ✅ CI green (all tests passing)
- ✅ Code review approved (no blocking comments)
- ✅ Documentation complete (DoD checklist, review checklist, technical debt report)
- ✅ Follow-ups tracked (BACKLOG_LEDGER.md updated)

---

**Last updated:** 2026-01-22
**Status:** ✅ Ready to open
