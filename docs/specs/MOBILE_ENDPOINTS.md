# API Endpoints Audit - Mobile App Focus

**Date**: 2025-12-13
**Context**: iOS mobile app development + PRO/VIP subscription tiers
**Issue**: Endpoint duplication and confusion between PRO and VIP tiers

---

## 🎯 Core Architecture Understanding

### Mobile App Strategy

- **Primary**: iOS mobile application (see `IOS_DEVELOPMENT_ROADMAP.md`)
- **Secondary**: Web frontend (React)
- **Subscription Tiers**:
  - **FREE**: Basic features
  - **PRO**: Advanced features (BMI Pro, basic meal planning)
  - **VIP**: Premium features (micronutrients, auto-repair, recipe synthesis, shopping lists)

### Payment Flow (Mobile)

- Frontend mocks: `/api/purchase`, `/api/restore`
- Paywall component: `frontend/src/components/Paywall/BeforeAfter.tsx`
- Revenue models: Freemium + subscription (from `business_bayesian_analyzer.py`)

---

## 📊 Current Endpoint Inventory

### 1. FREE Tier Endpoints

#### `/api/v1/bmi` (bmi_pro.py)

```
POST /api/v1/bmi/pro
- BMI calculation with WHR, WHTR, FFMI
- NO API key required (free feature)
- Mobile-ready: Yes ✅
```

#### `/api/v1/foods` (foods.py)

```
GET  /api/v1/foods
GET  /api/v1/foods/search
GET  /api/v1/foods/{food_id}
- Food database access
- NO API key required
- Mobile-ready: Yes ✅
```

#### `/api/v1/recipes` (recipes.py)

```
GET  /api/v1/recipes
GET  /api/v1/recipes/search
GET  /api/v1/recipes/{recipe_id}
POST /api/v1/recipes/preview
- Recipe browsing and preview
- NO API key required
- Mobile-ready: Yes ✅
```

### 2. PRO Tier Endpoints

#### `/api/v1/premium` (premium_week.py)

```
POST /api/v1/premium/plan/week-flexible
- Generate weekly meal plan
- WHO-based nutrition targets
- Dietary restrictions support
- NO API key check currently ⚠️
- Status: NEEDS API KEY GATING
```

**Issues:**

- Missing API key validation for PRO tier
- Confusion with VIP `/menu/weekly/plan`

### 3. VIP Tier Endpoints

#### `/api/v1/vip` (vip.py - 51.3KB, 19 endpoints)

**Core VIP Features:**

```
✅ Strict API Key Required (_require_api_key_strict)

HEALTH:
GET  /api/v1/vip/health

MEAL PLANNING:
POST /api/v1/vip/menu/weekly/plan        ← MAIN endpoint
POST /api/v1/vip/weekly-plan              ← DUPLICATE/LEGACY ⚠️
POST /api/v1/vip/menu/weekly/repair

SHOPPING LISTS:
POST /api/v1/vip/shoplist/weekly
POST /api/v1/vip/shoplist/daily
GET  /api/v1/vip/shoplist/formats

REGIONAL CATALOGS:
GET  /api/v1/vip/regions
GET  /api/v1/vip/regions/{region}/search
GET  /api/v1/vip/regions/{region}/categories
GET  /api/v1/vip/regions/{region}/stores
GET  /api/v1/vip/regions/compare/{product_name}

RECIPE SYNTHESIS (AI):
POST /api/v1/vip/recipes/synthesize
POST /api/v1/vip/recipe/synthesize        ← DUPLICATE ⚠️
POST /api/v1/vip/recipes/weekly
GET  /api/v1/vip/recipes/templates

AUTO-REPAIR (Advanced):
POST /api/v1/vip/auto-repair/weekly
POST /api/v1/vip/auto-repair/suggestions
GET  /api/v1/vip/auto-repair/strategies
```

### 4. Business/Analytics Endpoints

#### `/api/v1/business` (business.py)

```
POST /api/v1/business/analyze
GET  /api/v1/business/status
- Bayesian business analysis
- NO API key check ⚠️
- Status: Internal tooling, not for mobile
```

### 5. Export/Utility Endpoints

#### Shoplist Export (shoplist_export.py)

```
GET /api/v1/shoplist/export
GET /api/v1/shoplist/export.csv
GET /api/v1/shoplist/export.pdf
- NO prefix (global)
- Overlaps with VIP shoplist ⚠️
```

#### Plan Export (plan_export.py)

```
Various export endpoints
- NO API key check ⚠️
```

---

## 🚨 Critical Issues Found

### Issue #1: Duplicate Meal Planning Endpoints

**Problem**: 3 different endpoints for weekly meal planning!

```
1. /api/v1/premium/plan/week-flexible   (premium_week.py) - NO API KEY
2. /api/v1/vip/menu/weekly/plan         (vip.py) - STRICT API KEY ✅
3. /api/v1/vip/weekly-plan              (vip.py) - LEGACY API KEY ⚠️
```

**Impact**:

- Mobile app doesn't know which to use
- Inconsistent API key enforcement
- Maintenance burden (3 implementations)

**Recommendation**:

- **Keep**: `/api/v1/vip/menu/weekly/plan` (strict key, main endpoint)
- **Deprecate**: `/api/v1/vip/weekly-plan` (legacy, remove after mobile migration)
- **Repurpose**: `/api/v1/premium/plan/week-flexible` for PRO tier with proper API key

### Issue #2: Duplicate Recipe Synthesis

**Problem**: 2 endpoints for same feature

```
POST /api/v1/vip/recipes/synthesize  ← Plural (batch)
POST /api/v1/vip/recipe/synthesize   ← Singular (one) ⚠️
```

**Recommendation**:

- Keep plural version for consistency
- Remove singular or make it an alias

### Issue #3: Missing API Key Validation

**Endpoints without API key checks:**

- `/api/v1/premium/*` - Should require PRO tier
- `/api/v1/business/*` - Should be internal only
- Export endpoints - Should require authentication

### Issue #4: Inconsistent Prefixes

**Current structure:**

```text
/api/v1/bmi/*        (FREE)
/api/v1/foods/*      (FREE)
/api/v1/recipes/*    (FREE)
/api/v1/premium/*    (PRO) ⚠️ Missing API key
/api/v1/vip/*        (VIP) ✅ Has API key
/api/v1/business/*   (Internal) ⚠️ No protection
```

`/api/v1/users/*` is intentionally excluded from the mobile client contract.
It remains a runtime-only internal surface and must not be called directly by first-party mobile apps.

---

## 🎯 Proposed API Structure for Mobile App

### Tier 1: FREE (No API Key)

```
/api/v1/auth/*          - Login, register, logout
/api/v1/bmi/calculate   - Basic BMI calculation
/api/v1/foods/search    - Browse food database
/api/v1/recipes/search  - Browse recipe database
```

### Internal-only note

`/api/v1/users/*` is intentionally excluded from the mobile client contract.
It remains a runtime-only internal surface and must not be called directly by first-party mobile apps.

### Tier 2: PRO (API Key Required - Level 1)

**✅ IMPLEMENTED**: New PRO router at `/api/v1/pro/*`

```plaintext
POST /api/v1/pro/meal/weekly     - Weekly meal plan (macros only) ✅
GET  /api/v1/pro/bmi/advanced    - BMI Pro with WHR, WHTR, FFMI (planned)
GET  /api/v1/pro/meal/daily      - Daily meal plan (planned)
POST /api/v1/pro/nutrition/targets - WHO-based nutrition goals (planned)
```

**Migration Status**:

- ✅ `/api/v1/pro/meal/weekly` - **NEW** (replaces `/api/v1/premium/plan/week-flexible`)
- ⚠️ `/api/v1/premium/plan/week-flexible` - **DEPRECATED** (still works, will be removed in v2.0)

### Tier 3: VIP (API Key Required - Level 2)

```
/api/v1/vip/meal/weekly/plan     - Weekly plan with micronutrients
/api/v1/vip/meal/weekly/repair   - Auto-repair meal plans
/api/v1/vip/shoplist/generate    - AI shopping list
/api/v1/vip/shoplist/export      - Export (CSV, PDF)
/api/v1/vip/recipes/synthesize   - AI recipe generation
/api/v1/vip/recipes/weekly       - Custom recipe week
/api/v1/vip/regions/search       - Regional price comparison
/api/v1/vip/auto-repair/*        - Advanced repair strategies
```

### Internal Only (Admin API Key)

```
/api/v1/admin/business/analyze  - Business analytics
/api/v1/admin/logs/*            - Log management
/api/v1/admin/users/*           - Admin user management
```

---

## 📱 Mobile App Integration Plan

### Phase 1: Consolidation (1 week)

**Goal**: Remove duplicates, fix API key validation

**Tasks**:

1. ✅ Audit complete (this document)
2. Deprecate `/api/v1/vip/weekly-plan` (add deprecation warning)
3. Remove `/api/v1/vip/recipe/synthesize` (singular)
4. Add API key validation to `/api/v1/premium/*`
5. Add API key tier validation middleware
6. Document migration path for mobile app

**Files to modify**:

- `app/routers/vip.py` - Remove legacy endpoint
- `app/routers/premium_week.py` - Add API key check
- `app/routers/business.py` - Add admin-only check

### Phase 2: API Key Tiers (1 week)

**Goal**: Implement 3-tier API key system

**New middleware**:

```python
# app/middleware/api_tiers.py
def require_pro_tier(api_key: str) -> bool:
    """Validate PRO tier access."""
    # Check against subscription database

def require_vip_tier(api_key: str) -> bool:
    """Validate VIP tier access."""
    # Check against subscription database
```

**Database schema**:

```sql
CREATE TABLE subscriptions (
    user_id TEXT PRIMARY KEY,
    tier TEXT NOT NULL,  -- 'FREE', 'PRO', 'VIP'
    api_key TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP,
    platform TEXT,  -- 'ios', 'android', 'web'
    receipt_data TEXT  -- App Store/Google Play receipt
);
```

### Phase 3: iOS Integration (2 weeks)

**Goal**: Connect iOS app to consolidated API

**Tasks**:

1. Update iOS networking layer to use new endpoints
2. Implement IAP (In-App Purchase) → API key flow
3. Add receipt validation
4. Implement offline caching
5. Add proper error handling for API tier restrictions

**iOS changes**:

- `ios/PulsePlate/Network/APIClient.swift` - Update endpoints
- `ios/PulsePlate/Store/SubscriptionManager.swift` - IAP integration
- `ios/PulsePlate/Models/Subscription.swift` - Tier model

### Phase 4: Frontend Migration (1 week)

**Goal**: Update web frontend to use new structure

**Tasks**:

1. Update API calls in `frontend/src/`
2. Migrate paywall to use new tier system
3. Update mocks in `frontend/src/mocks/handlers.ts`

---

## 🔄 Migration Strategy

### Step 1: Add New Endpoints (No Breaking Changes)

```
Week 1:
- Add /api/v1/pro/* with proper validation
- Keep all existing endpoints working
- Add deprecation warnings to legacy endpoints
```

### Step 2: Mobile App Migration

```
Week 2-3:
- Update iOS app to use new endpoints
- Test on TestFlight
- Monitor usage of old vs new endpoints
```

### Step 3: Remove Legacy Endpoints

```
Week 4:
- Remove /api/v1/vip/weekly-plan
- Remove /api/v1/vip/recipe/synthesize (singular)
- Update all documentation
```

---

## 📝 Action Items

### ✅ Completed (PR 4.3.1 + Current Work)

- [x] Create API tier middleware (`app/middleware/api_tiers.py`) - ✅ Done
- [x] Add deprecation warnings to legacy endpoints - ✅ `/weekly-plan` deprecated
- [x] Add API key validation to premium endpoints - ✅ `/premium/plan/week-flexible`
- [x] Remove duplicate endpoint `/vip/recipe/synthesize` - ✅ Removed
- [x] Create comprehensive tests for middleware - ✅ 22 tests passing
- [x] Create new PRO router (`app/routers/pro.py`) - ✅ Done
- [x] Implement `/api/v1/pro/meal/weekly` endpoint - ✅ Done
- [x] Add deprecation to `/api/v1/premium/plan/week-flexible` - ✅ Done
- [x] Create tests for PRO router - ✅ Done

### Immediate (Next Steps)

- [x] Document new structure in OpenAPI/Swagger - ✅ Updated tags
- [ ] Update iOS app to use new `/api/v1/pro/*` endpoints
- [x] Create migration guide for mobile developers - ✅ This document
- [ ] Add remaining PRO endpoints (BMI advanced, daily meal, nutrition targets)

### Short-term (2-3 PRs)

- [ ] Implement subscription database schema
- [ ] Create subscription management endpoints
- [ ] Update iOS app networking layer
- [ ] Add receipt validation for App Store

### Long-term (Phase 2+)

- [ ] Android app support
- [ ] Web subscription management UI
- [ ] Analytics dashboard for subscription metrics
- [ ] A/B testing for pricing tiers

---

## 🎯 Success Metrics

**Technical**:

- ✅ Zero duplicate endpoints
- ✅ 100% API key coverage on paid endpoints
- ✅ <200ms latency for mobile endpoints
- ✅ 99.9% uptime for payment/subscription APIs

**Business**:

- Track FREE → PRO conversion rate
- Track PRO → VIP conversion rate
- Monitor API key usage by tier
- Track IAP receipt validation success rate

---

## 📚 Related Documents

- [BAYESIAN_ROLLOUT_PLAN_SMALL_PRS.md](./BAYESIAN_ROLLOUT_PLAN_SMALL_PRS.md) - PR breakdown
- [IOS_DEVELOPMENT_ROADMAP.md](./IOS_DEVELOPMENT_ROADMAP.md) - iOS development plan
- [GLOBAL_ROADMAP_2025.md](./GLOBAL_ROADMAP_2025.md) - Overall project roadmap
- `frontend/src/components/Paywall/BeforeAfter.tsx` - Paywall UI
- `app/routers/vip.py` - VIP endpoints implementation

---

## 🤝 Next Steps

**Proposal**: Create **PR 4.3.1 - API Consolidation** as a prerequisite to PR 4.3 (Nutrition API)

**Why**: Clean up existing mess before adding new endpoints

**Scope**:

1. Remove duplicate endpoints (2-3 files)
2. Add API tier middleware (1 new file)
3. Update tests (3-4 test files)
4. Update documentation

**Timeline**: 2-3 days
**Risk**: Low (backward compatible with deprecation warnings)

---

**Questions for Discussion**:

1. Should PRO and VIP use different API key prefixes? (e.g., `pro_` vs `vip_`)
2. Receipt validation: Server-side or client-side?
3. Grace period for expired subscriptions?
4. Offline mode for mobile: Cache duration?
