# Mobile API Migration Guide

**Last Updated**: 2025-12-13
**Target Audience**: iOS/Android Mobile Developers
**Context**: Migration to tiered API structure (FREE/PRO/VIP)

---

## 🎯 Overview

PulsePlate API has been consolidated into a clean, tiered structure optimized for mobile app integration with subscription-based access levels.

### What Changed

**Before** (Legacy):

- Multiple duplicate endpoints (`/vip/weekly-plan`, `/premium/plan/week-flexible`)
- Inconsistent API key validation
- Confusion between PRO and VIP features

**After** (New Structure):

- Single canonical endpoint per feature
- Consistent 3-tier access control (FREE/PRO/VIP)
- Mobile-optimized error responses
- Proper deprecation warnings for legacy endpoints

---

## 📊 API Tier Structure

### Tier 1: FREE (No API Key Required)

**Target Users**: All users, no subscription

**Endpoints**:

```
GET  /api/v1/bmi/pro              - Advanced BMI calculation
GET  /api/v1/foods                - Browse food database
GET  /api/v1/foods/search         - Search foods
GET  /api/v1/foods/{food_id}      - Get food details
GET  /api/v1/recipes              - Browse recipes
GET  /api/v1/recipes/search       - Search recipes
GET  /api/v1/recipes/{recipe_id}  - Get recipe details
POST /api/v1/recipes/preview      - Preview recipe nutrition
POST /api/v1/users                - Create user
GET  /api/v1/users/{user_id}      - Get user profile
```

**Mobile Integration**:

```swift
// No API key needed for FREE tier
let request = URLRequest(url: URL(string: "https://api.pulseplate.com/api/v1/foods/search?q=chicken")!)
```

---

### Tier 2: PRO (API Key Required - Level 1)

**Target Users**: PRO subscribers ($4.99/month)

**Features**:

- Weekly meal planning (macros only)
- WHO-based nutrition targets
- Basic dietary restrictions
- Cost estimation

**Canonical Endpoint**:

```
POST /api/v1/pro/meal/weekly
```

Deprecated alias (hidden from public OpenAPI, do not use as source of truth):

```
POST /api/v1/premium/plan/week-flexible
```

**Authentication**:

```
Header: X-API-Key: <PRO_API_KEY>
```

**Request Payload**:

```json
{
  "sex": "female",
  "age": 30,
  "height_cm": 165,
  "weight_kg": 60,
  "activity": "moderate",
  "goal": "maintain",
  "diet_flags": ["vegetarian"],
  "lang": "en"
}
```

**Response**:

```json
{
  "daily_menus": [
    {
      "day": "monday",
      "meals": [
        {
          "meal_type": "breakfast",
          "name": "Oatmeal with Berries",
          "kcal": 350,
          "protein_g": 12,
          "fat_g": 8,
          "carbs_g": 55
        }
      ]
    }
  ],
  "weekly_coverage": {
    "protein_g": 95.2,
    "fat_g": 88.7,
    "carbs_g": 92.1
  },
  "shopping_list": {
    "oats": 500,
    "berries": 300
  },
  "total_cost": 45.50,
  "adherence_score": 0.92
}
```

**Mobile Integration (Swift)**:

```swift
func generateWeeklyPlan(
    apiClient: APIClientProtocol,
    apiKeyProvider: () -> String?,
    targets: JSONValue = .emptyObject()
) async throws -> WeeklyPlanDTO {
    guard let apiKey = apiKeyProvider(), !apiKey.isEmpty else {
        throw APIError.invalidAPIKey
    }

    let service = DefaultWeeklyPlanService(apiClient: apiClient)
    let requestBody = try targets.encodeSorted()

    return try await service.fetchWeeklyPlan(
        request: WeeklyPlanRequest(
            endpointPath: "/api/v1/pro/meal/weekly",
            body: requestBody,
            apiKey: apiKey
        )
    )
}
```

Use the existing `APIClient` / `HTTPClient` seam for iOS transport. Direct
`URLSession` snippets are legacy examples only and are forbidden for new app
runtime code.

---

### Tier 3: VIP (API Key Required - Level 2)

**Target Users**: VIP subscribers ($9.99/month)

**Features** (All PRO features +):

- Micronutrient tracking (vitamins, minerals)
- AI recipe synthesis
- Auto-repair meal plans
- Regional price comparison
- Shopping list export (CSV/PDF)

**Key Endpoints**:

```
POST /api/v1/vip/menu/weekly/plan       - Weekly plan with micronutrients
POST /api/v1/vip/menu/weekly/repair     - Auto-repair nutrition gaps
POST /api/v1/vip/recipes/synthesize     - AI recipe generation
POST /api/v1/vip/shoplist/weekly        - Generate shopping list
GET  /api/v1/vip/regions/{region}/search - Regional price comparison
POST /api/v1/vip/auto-repair/weekly     - Advanced auto-repair
```

**Authentication**:

```
Header: X-API-Key: <VIP_API_KEY>
```

**Example: Recipe Synthesis**

Request:

```json
POST /api/v1/vip/recipes/synthesize
X-API-Key: <VIP_API_KEY>

{
  "ingredients": [
    {"name": "chicken breast", "amount": 200, "unit": "g"},
    {"name": "rice", "amount": 150, "unit": "g"},
    {"name": "broccoli", "amount": 100, "unit": "g"}
  ],
  "cuisine_preference": "asian",
  "difficulty_preference": "easy",
  "servings": 2
}
```

Response:

```json
{
  "recipe": {
    "name": "Asian Chicken Stir-Fry",
    "instructions": [
      "Cut chicken into bite-sized pieces",
      "Cook rice according to package",
      "Stir-fry chicken with broccoli"
    ],
    "nutrition": {
      "kcal": 520,
      "protein_g": 42,
      "fat_g": 8,
      "carbs_g": 65,
      "vitamins": {
        "vitamin_c_mg": 85,
        "vitamin_a_mcg": 420
      }
    },
    "cook_time_min": 25,
    "difficulty": "easy"
  }
}
```

---

## 🔑 API Key Management

### Development/Testing

**Base URL Detection (Non-secret)**:

```swift
struct APIConfig {
    static var baseURL: String {
        #if DEBUG
        return "http://localhost:8000"
        #else
        return "https://api.pulseplate.com"
        #endif
    }
}
```

**Runtime Secret Source**:

- iOS runtime secrets come from Keychain only.
- Tests and previews should inject explicit `apiKeyProvider` values instead of using hidden config or environment fallbacks.

### Production

**API Key Format**:

- PRO keys: Validated against subscription database
- VIP keys: Validated against subscription database

**Key Storage** (iOS):

```swift
import Security

class APIKeyManager {
    static let shared = APIKeyManager()

    func storeAPIKey(_ key: String, for tier: SubscriptionTier) {
        // Safe conversion: Data(key.utf8) is non-failable
        let keyData = Data(key.utf8)

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: "pulseplate_api_key_\(tier.rawValue)",
            kSecValueData as String: keyData,
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        ]

        SecItemDelete(query as CFDictionary)
        SecItemAdd(query as CFDictionary, nil)
    }

    func retrieveAPIKey(for tier: SubscriptionTier) -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: "pulseplate_api_key_\(tier.rawValue)",
            kSecReturnData as String: true
        ]

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        guard status == errSecSuccess,
              let data = result as? Data,
              let key = String(data: data, encoding: .utf8) else {
            return nil
        }

        return key
    }
}
```

---

## ⚠️ Deprecated Endpoints

### Legacy Endpoints (Still Available, But Deprecated)

```
⚠️  POST /api/v1/vip/weekly-plan
    → Use: POST /api/v1/vip/menu/weekly/plan
    → Deprecation Date: 2025-01-15

⚠️  POST /api/v1/vip/recipe/synthesize (singular)
    → Use: POST /api/v1/vip/recipes/synthesize (plural)
    → Removed in version 1.1.0
```

**Deprecation Headers**:

```
Warning: 299 - "Endpoint /vip/weekly-plan is deprecated. Use /vip/menu/weekly/plan"
Sunset: Sat, 15 Jan 2025 00:00:00 GMT
```

**Migration Timeline**:

- **Now - Jan 15, 2025**: Both endpoints work
- **Jan 15, 2025+**: Legacy endpoints return 410 Gone

---

## 🚨 Error Handling

### HTTP Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Process response |
| 400 | Bad Request | Check request payload |
| 401 | Unauthorized | Tier insufficient (e.g., PRO key on VIP endpoint) |
| 403 | Forbidden | Invalid/missing API key |
| 404 | Not Found | Endpoint doesn't exist |
| 410 | Gone | Deprecated endpoint removed |
| 429 | Too Many Requests | Rate limit exceeded, retry after delay |
| 500 | Server Error | Retry with exponential backoff |
| 503 | Service Unavailable | Server maintenance, retry later |

### Error Response Format

```json
{
  "detail": "Invalid API Key",
  "error_code": "AUTH_INVALID_KEY",
  "tier_required": "PRO",
  "tier_current": "FREE"
}
```

### Swift Error Handling

```swift
enum APIError: Error {
    case invalidAPIKey
    case insufficientTier(required: String, current: String)
    case rateLimitExceeded(retryAfter: TimeInterval)
    case serverError(Int)
    case invalidResponse
}

extension APIClient {
    func handleAPIError(response: HTTPURLResponse, data: Data) throws {
        let decoder = JSONDecoder()
        if let errorResponse = try? decoder.decode(APIErrorResponse.self, from: data) {
            switch response.statusCode {
            case 401:
                throw APIError.insufficientTier(
                    required: errorResponse.tierRequired ?? "UNKNOWN",
                    current: errorResponse.tierCurrent ?? "UNKNOWN"
                )
            case 403:
                throw APIError.invalidAPIKey
            case 429:
                let retryAfter = Double(response.value(forHTTPHeaderField: "Retry-After") ?? "60") ?? 60
                throw APIError.rateLimitExceeded(retryAfter: retryAfter)
            default:
                throw APIError.serverError(response.statusCode)
            }
        }
        throw APIError.serverError(response.statusCode)
    }
}
```

---

## 📱 iOS In-App Purchase (IAP) Integration

### Purchase Flow

```
1. User initiates purchase (PRO or VIP)
   ↓
2. StoreKit processes payment
   ↓
3. App receives transaction receipt
   ↓
4. Send receipt to backend for validation
   ↓
5. Backend validates with App Store
   ↓
6. Backend returns API key for tier
   ↓
7. App stores API key securely
   ↓
8. App uses API key for premium endpoints
```

### Backend Endpoint (Future)

```
POST /api/v1/subscriptions/validate
Content-Type: application/json

{
  "receipt_data": "<base64_encoded_receipt>",
  "platform": "ios",
  "bundle_id": "com.pulseplate.app"
}

Response:
{
  "api_key": "live_pro_abc123...",
  "tier": "PRO",
  "expires_at": "2025-02-13T00:00:00Z",
  "auto_renewing": true
}
```

---

## ✅ Migration Checklist

### For Existing Mobile Apps

- [ ] Update base URL if changed
- [ ] Replace deprecated endpoints with canonical ones
- [ ] Add `X-API-Key` header to PRO/VIP requests
- [ ] Implement proper error handling (401 vs 403)
- [ ] Add tier detection logic
- [ ] Store API keys securely (Keychain on iOS with `kSecAttrAccessibleWhenUnlockedThisDeviceOnly`)
- [ ] Use explicit injected test doubles for development and previews; do not rely on `Config.plist`, env, or DEBUG secret fallbacks
- [ ] Implement IAP → API key flow
- [ ] Add retry logic for 429/503 errors
- [ ] Update Swagger/OpenAPI client if using code generation
- [ ] **Implement offline resilience**:
  - [ ] Add response caching (URLCache, NSCache, or custom persistence)
  - [ ] Implement stale-while-revalidate or cache-first strategies
  - [ ] Design offline UI states (loading, cached, no-connectivity)
  - [ ] Add automated tests for offline scenarios
  - [ ] Test manual offline mode (airplane mode, network disconnection)
  - [ ] Ensure graceful sync when connectivity returns

### For New Mobile Apps

- [ ] Review tier structure and choose appropriate endpoints
- [ ] Use explicit injected API key providers for development flows; keep runtime secrets in Keychain only
- [ ] Implement subscription manager
- [ ] Add proper analytics for tier usage
- [ ] **Implement offline resilience**:
  - [ ] Design cache strategy (TTL, eviction policies, size limits)
  - [ ] Implement local persistence for critical data
  - [ ] Test offline mode thoroughly (cache behavior, UI states)
  - [ ] Validate stale-while-revalidate patterns
  - [ ] Add offline-first sync logic for write operations
  - [ ] Test graceful degradation and recovery
- [ ] Implement graceful degradation (PRO → FREE fallback)

---

## 🔗 Related Documentation

- **API Reference**: Swagger UI at `/docs` (when running locally)
- **iOS Integration**: `IOS_API_INTEGRATION.md`
- **Endpoint Audit**: `ENDPOINT_AUDIT_MOBILE_FOCUS.md`
- **Backend Architecture**: `BAYESIAN_ROLLOUT_PLAN_SMALL_PRS.md`

---

## 📞 Support

**Issues**: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/issues>
**Discussions**: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/discussions>

---

**Questions?**

1. **How do I get production API keys?**
   → Production keys are issued after IAP receipt validation via `/api/v1/subscriptions/validate` (coming soon)

2. **Can I use test keys in production?**
   → No, test keys only work in development/test environments

3. **What happens if my subscription expires?**
   → API returns 401 Unauthorized. App should prompt user to renew subscription

4. **How do I test PRO/VIP features without paying?**
   → Pass test/dev keys through explicit injected `apiKeyProvider` seams in previews, UI tests, or dedicated debug harnesses; iOS runtime no longer reads hidden env/config fallbacks for premium API secrets

5. **What's the rate limit?**
   → FREE: 100 req/hour, PRO: 1000 req/hour, VIP: 5000 req/hour (subject to change)
