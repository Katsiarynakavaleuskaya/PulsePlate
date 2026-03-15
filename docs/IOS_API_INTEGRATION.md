# iOS API Integration (Canonical)

**Last Updated**: 7 February 2026
**Status**: Canonical (repo source of truth)
**Scope**: iOS thin-client networking only (transport + contracts + tests)
**Non-goals**: IAP/receipt, analytics, domain logic, “roll your own URLSession client”, new singleton transport layers

---

## Current SoT (repo paths)

Use the existing networking implementation. Do **not** create a parallel transport layer.

- **Transport**
  - `ios/PulsePlate/Networking/APIClient.swift` (protocol: `APIClientProtocol:4`)
  - `ios/PulsePlate/Networking/HTTPClient.swift`
  - `ios/PulsePlate/Networking/APIError.swift`
- **Base URL**
  - `ios/PulsePlate/Services/AppConfig.swift` → `AppConfig.baseURL()` (Info.plist → env → fallback)
- **PRO key provider**
  - `ios/PulsePlate/Services/ProKeyProvider.swift:3` (enum; Keychain-only runtime source)
  - `ios/PulsePlate/Services/KeychainStore.swift:8` (Keychain wrapper)
- **Profile query params (PRO endpoints)**
  - `ios/PulsePlate/Services/ProfileProvider.swift:42-49` (protocol `ProfileProviding`)
  - `ios/PulsePlate/Services/ProfileProvider.swift:52-115` (default impl reads AppStorage/UserDefaults)

---

## Rules (thin-client)

- **No domain logic on iOS**: BMI/risk/category logic lives on the backend only.
- **One HTTP seam**: do not use `URLSession` directly outside `ios/PulsePlate/Networking/*`.
- **Contracts first**: request/response DTOs must mirror backend contracts (snake_case on wire; `convertToSnakeCase` is configured in `APIClient` encoder).
- **Errors**: use `APIError` from `ios/PulsePlate/Networking/APIError.swift` (transport vs validation vs api errors are distinct).

### Deprecated / legacy endpoints (do not treat as SoT)

- **Forbidden as iOS source-of-truth:** `GET /api/nutrition/{date}` (legacy alias; deprecated).
- **Canonical (PRO):** `GET /api/v1/pro/nutrition/daily` (requires `X-API-Key` + profile query params).

Rationale: legacy aliases may have contract/guard drift; iOS must integrate against canonical endpoints only.

Policy anchors:

- `ios/AGENTS.md` (iOS Thin Client Policy + CI enforcement)
- Root `AGENTS.md` (Thin Client Policy + no dual-path networking)

---

## How to add a new endpoint (recipe)

### Step 1) Add DTOs (transport-only)

- Add request/response DTOs under an appropriate folder (keep them **transport-only**; no computed semantics).
- Ensure wire keys match backend schema (snake_case).

### Step 2) Add a thin service wrapper (preferred) or call APIClient directly

Prefer a small, explicit service that:

- builds headers (e.g. `X-API-Key` if required),
- calls `apiClient.post(...)` / `apiClient.postRaw(...)` / `apiClient.get(...)`,
- returns DTOs unchanged.

Example patterns in repo:

- BMI (FREE): `ios/PulsePlate/Services/BMIService.swift:19-39` (calls `POST /api/v1/bmi/calculate`)
- PRO daily nutrition (Plate): `ios/PulsePlate/Services/ProDailyNutritionService.swift:80-115` (calls `GET /api/v1/pro/nutrition/daily` with profile query params + `X-API-Key`)
- Weekly plan: `ios/PulsePlate/Services/WeeklyPlanService.swift` (calls `postRaw` with optional API key)

### Step 3) Tests (deterministic, no real network)

- Prefer URLProtocol stubs via `HTTPClientProtocol` injection.
- Repo examples:
  - `ios/PulsePlateTests/Networking/HTTPClientTests.swift`
  - `ios/PulsePlateTests/Networking/APIClientTests.swift`
  - `ios/PulsePlateTests/Services/ProDailyNutritionServiceTests.swift:6-65` (deterministic URL + header assertion)

Hard rule: avoid tests that call real endpoints; they are flaky and violate determinism.

---

## Key handling (CURRENT)

Document the current repo truth explicitly.

- **PRO key**: `ios/PulsePlate/Services/ProKeyProvider.swift`
  - **Runtime source**: Keychain only (`ios/PulsePlate/Services/KeychainStore.swift`).
  - **Dev/test seam**: inject explicit `apiKeyProvider` closures in previews/tests; do not use hidden runtime env fallback.
  - **Hard rule**: no hardcoded keys / placeholder fallbacks in sources.
  - **Missing-key behavior**: must return `nil` (explicit + testable), not a silent fallback.
  - **Tests**: `ios/PulsePlateTests/Services/ProKeyProviderTests.swift`

If you need new key types (e.g., VIP), add providers deliberately and track secure storage work in the ledger.

---

## Future (tracked in BACKLOG_LEDGER)

Keep future work out of the canonical networking guide; track it as discrete backlog items:

- Onboarding/UX around existing Keychain-backed PRO flows
- Additional Keychain-backed providers for future secret types (for example VIP)
- Receipt validation / IAP orchestration
- Deep-link allowlist and onboarding gates

---

## Payments Transport (P0 baseline policy)

Contract source:
- `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:1`
- `docs/contracts/IOS_STOREKIT_PRODUCTS_CONTRACT.md:1` (canonical StoreKit product IDs and setup baseline)

Thin-client rules for payments:
1. iOS must use existing `APIClient`/`HTTPClient` seam only (evidence: `ios/PulsePlate/Networking/APIClient.swift:57`, `ios/PulsePlate/Networking/HTTPClient.swift:22`).
2. Receipt/business decision logic stays server-side; the additive Apple verify seam is `/api/v1/billing/apple/verify-receipt`, while RU/BY payment transport remains on `/api/v1/pro/payments/ru-by/*` until the runtime migration lands (evidence: `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:27`, `docs/contracts/API_CANONICAL_MAP.md:20`, `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-payments-ruby-ios`).
3. Client may send transport payload and render server state, but must not infer activation logic locally (evidence: `ios/PulsePlate/Networking/APIClient.swift:84`, `ios/PulsePlate/Networking/HTTPClient.swift:13`).
4. Key material/storage remains in Keychain-backed providers; no `UserDefaults` fallback for secrets (evidence: `ios/PulsePlate/Services/ProKeyProvider.swift:20`, `ios/PulsePlate/Services/KeychainStore.swift:8`).
5. The iOS app must never call Apple `verifyReceipt` directly; server-side verification is production-first with a single sandbox fallback on `21007` and requires backend-held `APPLE_SHARED_SECRET`.

Current / planned transport surfaces:
- `POST /api/v1/billing/apple/verify-receipt` (implemented additive billing seam for verify-only receipt validation)
- `POST /api/v1/pro/payments/ru-by/manual-intent` (current runtime transport during the transition window)
- `POST /api/v1/pro/payments/ru-by/reconcile` (current runtime transport during the transition window)
- `GET /api/v1/pro/payments/ru-by/reconcile/{intent_id}` (current runtime transport during the transition window)

Testing expectations (runtime PRs):
- Deterministic service tests with URLProtocol stubs.
- Contract tests for success/error envelopes and idempotent retries.
