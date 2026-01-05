# feat: Add PRO tier router and standardize endpoints for iOS

## 🎯 Overview

This PR standardizes API structure for iOS mobile app integration by creating a new `/api/v1/pro/*` router and deprecating the old `/api/v1/premium/*` endpoints.

## 📋 Changes

### New Features

- ✅ Created new PRO tier router (`app/routers/pro.py`)
- ✅ Added `POST /api/v1/pro/meal/weekly` endpoint for weekly meal planning
- ✅ Implemented comprehensive API tier validation via `require_pro_tier` middleware

### Deprecations

- ⚠️ Marked `/api/v1/premium/plan/week-flexible` as deprecated (backward compatible)
- ⚠️ Added deprecation warnings and migration guide in documentation

### Documentation

- ✅ Updated `ENDPOINT_AUDIT_MOBILE_FOCUS.md` with new structure
- ✅ Added `CURRENT_WORK_STATUS.md` for project tracking
- ✅ Updated OpenAPI tags (added "pro", marked "premium" as deprecated)

### Testing

- ✅ Created comprehensive test suite (`tests/test_pro_router.py`)
- ✅ 11 tests covering API key validation, request validation, backward compatibility
- ✅ All tests passing

### Developer Experience

- ✅ Optimized `.cursor-settings.json` for better editor performance
- ✅ Added Qoder setup and hang fix scripts

## 🏗️ API Structure

### Before

```
/api/v1/premium/plan/week-flexible  (inconsistent naming)
```

### After

```
/api/v1/pro/meal/weekly  ✅ NEW (standardized for iOS)
/api/v1/premium/plan/week-flexible  ⚠️ DEPRECATED (still works)
```

## 🔐 API Key Tiers

- **FREE**: No API key required (`/api/v1/bmi/*`, `/api/v1/foods/*`, etc.)
- **PRO**: PRO tier API key required (`/api/v1/pro/*`) ✅ NEW
- **VIP**: VIP tier API key required (`/api/v1/vip/*`) - VIP keys also grant PRO access

## 📱 iOS Integration

This PR prepares the API for iOS mobile app integration:

- Clean, consistent endpoint structure
- Proper tier-based access control
- Backward compatibility maintained during migration period

## 🧪 Testing

```bash
pytest tests/test_pro_router.py -v
# 11 passed in 0.58s
```

All tests cover:

- API key validation (PRO/VIP tiers)
- Request validation
- Response structure
- Backward compatibility with deprecated endpoints

## 📚 Related

- `ENDPOINT_AUDIT_MOBILE_FOCUS.md` - Full endpoint audit and migration plan
- `CURRENT_WORK_STATUS.md` - Project status tracking
- Issue #286 - Bayesian module integration (ongoing)

## ✅ Checklist

- [x] New PRO router created
- [x] Endpoint implemented and tested
- [x] Deprecation warnings added
- [x] Documentation updated
- [x] Tests written and passing
- [x] Pre-commit checks passed
- [x] Conflicts with main resolved

## 🔄 Migration Path

For iOS developers:

1. Update API client to use `/api/v1/pro/meal/weekly`
2. Request/response format remains the same
3. API key validation remains the same (PRO tier required)
4. Old endpoint will be removed in v2.0
