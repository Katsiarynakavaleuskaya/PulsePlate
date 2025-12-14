# Weekly Plan Reader – Smoke Test Checklist

**Purpose**: 5-minute validation before merging Weekly Plan Reader changes to `main`.

**When to use**: Before any PR merge that affects Weekly Plan Reader code (Models, ViewModels, Services, UI).

**Required**: Without Apple Developer Program, simulator testing is our primary quality gate.

---

## ✅ Pre-Merge Checklist

### 1. Build & Launch (30 seconds)

- [ ] **Clean build succeeds** (`Cmd+Shift+K` → `Cmd+B`)
- [ ] **No compiler warnings** in Weekly Plan Reader files
- [ ] **App launches without crashes** in iPhone 16 simulator (iOS 17+)

### 2. UI States (2 minutes)

Test all 4 states using mock service or previews:

#### Loading State

- [ ] Skeleton view displays correctly
- [ ] No layout glitches during animation

#### Loaded State

- [ ] All 7 days render with correct data
- [ ] Day navigation works (swipe left/right)
- [ ] Meal sections expand/collapse smoothly
- [ ] Daily summary shows correct macros
- [ ] Weekly coverage displays (if available)
- [ ] Shopping list renders (if available)

#### Empty State

- [ ] "No plan available" message displays
- [ ] Retry button visible and tappable

#### Error State

- [ ] Error message displays clearly
- [ ] Retry button works (triggers reload)

### 3. Adapter Resilience (1 minute)

Verify contract drift protection:

- [ ] **Missing totals**: Change mock to omit `daily_totals` → falls back to `totals`
- [ ] **Missing shopping list**: Remove `shopping_list` key → no crash, nil handling
- [ ] **Invalid coverage**: Set coverage to `1000%` → clamped to 0-300 range
- [ ] **Empty meals**: Zero kcal + no items → section skipped

### 4. Accessibility (1 minute)

- [ ] **VoiceOver**: Enable (Cmd+F5), navigate through meal sections
  - Labels read correctly ("Breakfast, 3 items, 420 kcal")
  - Values announced properly
  - No "unlabeled" elements
- [ ] **Dynamic Type**: Settings → Accessibility → Larger Text → Max size
  - Text doesn't truncate
  - ViewThatFits switches layout (HStack → VStack when horizontal space insufficient)
- [ ] **Dark Mode**: Toggle (Cmd+Shift+A) → no contrast issues

### 5. Multi-Device (30 seconds)

Quick layout validation:

- [ ] **iPhone 16** (6.1"): Default test device
- [ ] **iPad Pro 13"**: Glass cards scale properly, no excessive whitespace
- [ ] **iPhone SE** (4.7"): Compact layout works, no clipping

### 6. Memory & Performance (30 seconds)

- [ ] **No memory leaks**: Navigate in/out 5 times → Xcode memory graph stable
- [ ] **Task cancellation**: Trigger load → immediately retry → no parallel requests
- [ ] **Animations smooth**: 60fps on swipe navigation (no janky frames)

---

## 🛑 Blockers (Do NOT Merge If)

- **Crash on any state** (loading/loaded/empty/error)
- **Adapter fails on malformed JSON** (test edge cases: null values, missing keys, wrong types, deeply nested structures)
- **VoiceOver reads gibberish** ("Button, Button, Button" instead of meal names)
- **Dark mode text invisible** (white text on white background)
- **Memory leak detected** (instrument shows growing allocations)

---

## 📝 Optional (Nice to Have)

- [ ] **Previews update**: All `#Preview` macros compile and display correctly
- [ ] **Feature flag respected**: `FeatureFlags.weeklyPlanReaderEnabled = false` → hides feature
- [ ] **Localization ready**: No hardcoded "Monday" strings (use `.formatted()` for dates)
- [ ] **Currency formatting**: Uses `FormatStyle.currency` (not "$87.50" hardcoded)

---

## 🎯 Success Criteria

**Minimum bar for merge**:

- ✅ All 6 checklist sections completed
- ✅ Zero blockers
- ✅ PR description includes:
  - Screenshot/video of loaded state
  - Confirmation of adapter resilience tests
  - Device matrix tested (iPhone/iPad)

**Gold standard** (ship to production):

- ✅ All optional items checked
- ✅ Backend API deployed and stable
- ✅ VIP/Paywall gates implemented
- ✅ Analytics hooks integrated
- ✅ Release notes written

---

## 🚀 Next Steps After Merge

1. **Tag release candidate**: `git tag v0.1.0-rc1`
2. **Monitor main branch**: CI must pass (linting, tests)
3. **Prepare for TestFlight**: When Apple Developer Program active
4. **Update feature flag**: Enable in release build when ready

---

## 📚 Related Documentation

- [FeatureFlags.swift](../ios/PulsePlate/Utilities/FeatureFlags.swift) – Toggle feature on/off
- [WeeklyPlanPreviewData.swift](../ios/PulsePlate/Models/WeeklyPlan/WeeklyPlanPreviewData.swift) – Mock data for testing
- [WeeklyPlanAdapter.swift](../ios/PulsePlate/Models/WeeklyPlan/WeeklyPlanAdapter.swift) – Contract drift protection
- [GlassCard.swift](../ios/PulsePlate/Views/Components/GlassCard.swift) – iOS 17-26 glass effects

---

**Last Updated**: 2025-12-14
**Owner**: iOS Team
**Review Frequency**: Before every Weekly Plan Reader PR
