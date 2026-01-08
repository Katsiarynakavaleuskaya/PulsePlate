# Recommendations Summary: Q1 2026 Roadmap

## 🎯 Final Recommendation

**Execute in order:** Sprint B → Sprint C.1 (parallel with B) → Sprint C.2 → Sprint D

**Skip:** PR-492 (Docker verification) — security alert resolved, verification redundant.

---

## 📊 Decision Matrix

| Sprint | Priority | Risk | Value | Time | Dependencies |
|--------|----------|------|-------|------|--------------|
| **B: BMI Contract Docs** | 🔴 HIGH | 🟢 LOW | 🔴 HIGH | 2-3h | None |
| **C.1: i18n Audit** | 🟡 MED-HIGH | 🟢 LOW | 🟡 MED-HIGH | 2-3h | None (can parallel with B) |
| **C.2: iOS BMI** | 🔴 HIGH | 🟢 LOW | 🔴 HIGH | 3-4h | B, C.1 |
| **D: PRO/VIP UI** | 🟡 MEDIUM | 🟢 LOW | 🔴 HIGH | 6-8h | C.2 |

**Total Time:** 13-18 hours (sequential) or 11-16 hours (B+C.1 parallel)

---

## 🔍 Detailed Evidence

### 1. PR-492: Skip Docker Verification

**Evidence:**
```bash
# Security alert #495 disappeared after PR-487 merge
# requirements-dev.txt contains urllib3==2.6.3
# No active security alerts
```

**Conclusion:** Verification PR not needed — environment already updated.

---

### 2. Sprint B: BMI Contract Documentation — **DO THIS FIRST**

**Why High Priority:**
- iOS/Web developers need documented contract to implement visualization
- Contract tests prevent regressions
- Examples speed up development

**Evidence from Codebase:**

**✅ What Exists:**
```python
# app/schemas/bmi.py
class BMICalculateResponse(BaseModel):
    visualization: BMIScaleV1Spec | None = None  # ✅ Field exists

# app/services/bmi_visualization.py
def build_bmi_scale_v1(result: BMICalculateResult) -> BMIScaleV1Spec | None:
    # ✅ Builder exists, group-aware
```

**❌ What's Missing:**
- No `docs/bmi/visualization.md` — contract undocumented
- No JSON examples for different groups (adult/athlete/elderly/child)
- No contract tests validating response structure

**Action Items:**
1. Create `docs/bmi/visualization.md` with:
   - What `visualization` field means
   - JSON examples for each group
   - `visualization: null` explanation
   - Fallback behavior

2. Create `tests/test_bmi_contract.py` with:
   - JSON schema validation
   - Response structure validation
   - Group-specific range validation

**Code Example (What to Document):**
```json
// Adult general group
{
  "visualization": {
    "kind": "bmi_scale_v1",
    "bmi": 23.4,
    "min": 0.0,
    "max": 60.0,
    "ranges": [
      {"key": "bmi.underweight", "from": 0, "to": 18.5},
      {"key": "bmi.normal", "from": 18.5, "to": 25.0},
      {"key": "bmi.overweight", "from": 25.0, "to": 30.0},
      {"key": "bmi.obesity", "from": 30.0, "to": 60.0}
    ],
    "marker": {"value": 23.4}
  }
}

// Athlete group (normal extends to 27.0)
{
  "visualization": {
    "ranges": [
      {"key": "bmi.underweight", "from": 0, "to": 18.5},
      {"key": "bmi.normal", "from": 18.5, "to": 27.0},  // ← Different!
      {"key": "bmi.overweight", "from": 27.0, "to": 30.0},
      {"key": "bmi.obesity", "from": 30.0, "to": 60.0}
    ]
  }
}

// Child/teen group (no visualization)
{
  "visualization": null  // ← category=None groups
}
```

---

### 3. Sprint C.1: i18n Audit — **DO IN PARALLEL WITH B**

**Why Medium-High Priority:**
- Prevent missing translations
- Centralize key management
- Enable client development

**Evidence from Codebase:**

**✅ What Exists:**
```swift
// iOS localization files exist
ios/PulsePlate/en.lproj/Localizable.strings  // ✅
ios/PulsePlate/ru.lproj/Localizable.strings  // ✅
ios/PulsePlate/es.lproj/Localizable.strings  // ✅

// Backend i18n exists
core/i18n.py  // ✅ Has BMI category keys
```

**❌ What's Missing:**
```swift
// iOS Localizable.strings - NO BMI visualization keys
// Missing:
"bmi.underweight" = "Underweight";
"bmi.normal" = "Normal";
"bmi.overweight" = "Overweight";
"bmi.obesity" = "Obesity";

// Backend - no centralized key registry
// Missing: core/i18n/keys.py or similar
```

**Action Items:**
1. Create `core/i18n/keys.py` with all i18n keys as constants
2. Add BMI keys to iOS `Localizable.strings` (RU/EN/ES)
3. Add contract tests: all keys exist in all languages

**Code Example (What to Add):**
```swift
// ios/PulsePlate/en.lproj/Localizable.strings
"bmi.underweight" = "Underweight";
"bmi.normal" = "Normal";
"bmi.overweight" = "Overweight";
"bmi.obesity" = "Obesity";

// ios/PulsePlate/ru.lproj/Localizable.strings
"bmi.underweight" = "Недостаточная масса";
"bmi.normal" = "Норма";
"bmi.overweight" = "Избыточная масса";
"bmi.obesity" = "Ожирение";
```

---

### 4. Sprint C.2: iOS BMI Bootstrap — **DO AFTER B + C.1**

**Why High Priority:**
- iOS structure exists, just need BMI-specific files
- Patterns established (ShoppingList, WeeklyPlan)
- Foundation for PRO/VIP integration

**Evidence from Codebase:**

**✅ What Exists (Patterns to Replicate):**
```swift
// Service pattern exists
ios/PulsePlate/Services/ShoppingListService.swift
public func fetchShoppingList(request: ShoppingListRequest) async throws -> ShoppingListDTO

// Model pattern exists
ios/PulsePlate/Models/NutritionData.swift
struct NutritionData: Codable { ... }

// Screen pattern exists
ios/PulsePlate/Screens/ShoppingListReaderScreen.swift
```

**❌ What's Missing for BMI:**
```swift
// Missing files:
ios/PulsePlate/Models/BMICalculateRequest.swift  // ❌
ios/PulsePlate/Models/BMICalculateResponse.swift  // ❌
ios/PulsePlate/Models/BMIScaleV1Spec.swift  // ❌
ios/PulsePlate/Services/BMIService.swift  // ❌
ios/PulsePlate/Screens/BMICalculateScreen.swift  // ❌
```

**Action Items:**
1. Create BMI models (matching backend schemas)
2. Create `BMIService.swift` (API client)
3. Create `BMICalculateScreen.swift` (basic UI)
4. Create BMI visualization component (SwiftUI)

**Code Example (What to Create):**
```swift
// ios/PulsePlate/Models/BMICalculateRequest.swift
struct BMICalculateRequest: Codable {
    let weightKg: Double
    let heightCm: Double
    let age: Int
    let gender: String
    let lang: String
}

// ios/PulsePlate/Models/BMICalculateResponse.swift
struct BMICalculateResponse: Codable {
    let bmi: Double
    let category: String?
    let group: String
    let visualization: BMIScaleV1Spec?
    // ... other fields
}

// ios/PulsePlate/Services/BMIService.swift
class BMIService {
    func calculateBMI(request: BMICalculateRequest) async throws -> BMICalculateResponse {
        // Follow ShoppingListService pattern
    }
}
```

---

### 5. Sprint D: PRO/VIP UI Integration — **DO AFTER C.2**

**Why Medium Priority:**
- Backend endpoints ready
- iOS foundation needed first
- Incremental approach

**Evidence from Codebase:**

**✅ What Exists (Backend):**
```python
# PRO endpoints
app/routers/pro.py  # ✅ /api/v1/pro/meal/weekly, /api/v1/pro/nutrition/targets
app/routers/bmi_pro.py  # ✅ /api/v1/bmi/pro
app/routers/nutrition_log.py  # ✅ /api/v1/nutrition-log/meal-log

# VIP endpoints
app/routers/vip.py  # ✅ Multiple VIP endpoints
app/routers/vip_shoplist.py  # ✅ /api/v1/vip/shoplist/*
```

**✅ What Exists (iOS):**
```swift
// PRO/VIP infrastructure exists
ios/PulsePlate/Services/ProKeyProvider.swift  // ✅
ios/PulsePlate/Models/StoreKitManager.swift  // ✅
```

**❌ What's Missing:**
- No PRO/VIP UI screens (except shopping list/weekly plan)
- No BMI Pro screen
- No nutrition log screen
- No VIP-specific UI

**Action Items:**
1. Audit existing PRO/VIP endpoints
2. Create PRO/VIP UI screens
3. Integrate subscription checks
4. Connect to backend endpoints

---

## 🚀 Execution Plan

### Week 1: Foundation (Sprint B + C.1)

**Day 1-2: Sprint B (2-3h)**
- Create `docs/bmi/visualization.md`
- Create `tests/test_bmi_contract.py`
- Add JSON examples

**Day 1-2: Sprint C.1 (2-3h) — Parallel**
- Create `core/i18n/keys.py`
- Add BMI keys to iOS `Localizable.strings`
- Add contract tests

### Week 2: iOS Bootstrap (Sprint C.2)

**Day 3-4: Sprint C.2 (3-4h)**
- Create BMI models
- Create `BMIService.swift`
- Create `BMICalculateScreen.swift`
- Create visualization component

### Week 3: PRO/VIP Integration (Sprint D)

**Day 5-7: Sprint D (6-8h)**
- Audit PRO/VIP endpoints
- Create PRO/VIP UI screens
- Integrate subscription flows
- Connect to backend

---

## ✅ Success Criteria

### Sprint B
- [ ] `docs/bmi/visualization.md` exists with examples
- [ ] `tests/test_bmi_contract.py` passes
- [ ] JSON examples for all groups documented

### Sprint C.1
- [ ] `core/i18n/keys.py` exists
- [ ] BMI keys in iOS `Localizable.strings` (RU/EN/ES)
- [ ] Contract tests pass

### Sprint C.2
- [ ] BMI models exist (matching backend)
- [ ] `BMIService.swift` works
- [ ] `BMICalculateScreen.swift` renders
- [ ] Visualization component works

### Sprint D
- [ ] PRO/VIP UI screens exist
- [ ] Subscription checks integrated
- [ ] Backend endpoints connected

---

## 📝 Notes

- **PR-492:** Skip — security alert resolved
- **Sprint B:** Do first — enables client development
- **Sprint C.1:** Can parallel with B — independent work
- **Sprint C.2:** Do after B+C.1 — needs documented contract
- **Sprint D:** Do last — needs iOS foundation

**Total Time:** 13-18 hours (sequential) or 11-16 hours (B+C.1 parallel)
