# Sprint Roadmap: Q1 2026

## Strategy

**Approach:** Clean layer by layer, bringing clients (web/iOS) to already-ready backend features.

**Principle:** Backend is "thick" (features ready), clients are "thin" (need to catch up).

---

## Sprint A: Security & Infra Hygiene

**Goal:** Ensure security updates are properly applied and add guard checks.

### PR-492: Verify urllib3 2.6.3 in Docker Image

**Problem:** Need to verify that Docker image actually uses urllib3 2.6.3 after PR-487 merge.

**Tasks:**
- [ ] Verify urllib3 version in Docker image after PR-487 merge
- [ ] Add Dockerfile check/test to ensure dependencies match requirements-lock.txt
- [ ] (Optional) Add CI guard check for dependency version consistency

**Acceptance Criteria:**
- Docker image contains urllib3 2.6.3
- CI verifies dependency versions match lock file
- No security vulnerabilities in image scan

**Related:**
- Follow-up to PR-487 (Dependabot urllib3 update)

---

## Sprint B: BMI Contract Polish + Docs

**Goal:** Document BMI visualization contract and add contract tests.

### Tasks

#### 1. Documentation

- [ ] **docs/bmi/visualization.md**:
  - What is BMI visualization
  - JSON spec examples for different groups:
    - Adult (general)
    - Athlete
    - Elderly
    - Child/Teen (visualization: null)
  - Group-specific range differences
  - Fallback behavior

- [ ] **docs/api/bmi.md**:
  - `/api/v1/bmi/calculate` endpoint documentation
  - Request/response examples
  - Visualization field explanation

#### 2. Contract Tests

- [ ] **tests/test_bmi_contract.py**:
  - JSON schema validation for `BMICalculateResponse`
  - Visualization spec structure validation
  - Group-specific range validation (adult vs athlete vs elderly)
  - `visualization: null` cases validation

- [ ] **Sanity checks:**
  - Visualization optional (endpoint returns 200 even if visualization fails)
  - Fallback behavior (visualization: null on builder failure)
  - All groups return valid response structure

**Acceptance Criteria:**
- Documentation covers all visualization scenarios
- Contract tests verify API response structure
- Examples work for all groups
- Sanity checks pass

**Related:**
- PR-490B (BMI visualization group-aware)
- PR-491 (test reorganization)

---

## Sprint C: i18n + iOS Bootstrap Audit

**Goal:** Establish i18n foundation and bootstrap iOS client.

### Tasks

#### 1. i18n Foundation

- [ ] **Single source of truth for i18n keys:**
  - Audit existing i18n keys (RU/EN/ES)
  - Create/update `core/i18n/keys.py` or similar
  - Document i18n key structure

- [ ] **i18n switcher:**
  - Language detection/selection logic
  - Fallback chain (requested → default → en)
  - API language parameter handling

- [ ] **Contract/snapshot tests:**
  - All i18n keys exist for all languages
  - No missing translations
  - Key structure consistency

#### 2. iOS Bootstrap Audit

- [ ] **Current state assessment:**
  - What exists in iOS client?
  - What's missing?
  - Dependencies and setup

- [ ] **Base screen setup:**
  - Basic navigation structure
  - Screen templates
  - Common UI components

- [ ] **API client:**
  - HTTP client setup
  - Request/response models (DTOs)
  - Error handling
  - Authentication (API key handling)

- [ ] **Models/DTOs:**
  - BMI models (BMICalculateRequest, BMICalculateResponse)
  - Error models
  - Common models

- [ ] **Error localization:**
  - Error message mapping
  - i18n for error messages
  - User-friendly error display

**Acceptance Criteria:**
- i18n keys centralized and documented
- Language switching works
- iOS client has basic structure
- API client can make requests
- Models match backend schemas
- Errors are localized

**Related:**
- Backend API contracts (PR-490B)
- i18n infrastructure

---

## Sprint D: PRO/VIP UI Integration

**Goal:** Connect existing PRO/VIP endpoints to iOS/web clients.

### Tasks

#### 1. Audit Existing PRO/VIP Endpoints

- [ ] List all PRO/VIP endpoints in backend
- [ ] Document which features are PRO vs VIP
- [ ] Identify what's ready for client integration

#### 2. iOS Integration

- [ ] **PRO features:**
  - Identify PRO endpoints to integrate
  - Create UI screens for PRO features
  - Add PRO subscription check/flow
  - Connect to backend endpoints

- [ ] **VIP features:**
  - Identify VIP endpoints to integrate
  - Create UI screens for VIP features
  - Add VIP subscription check/flow
  - Connect to backend endpoints

#### 3. Web Integration

- [ ] **PRO features:**
  - Update web UI for PRO features
  - Add subscription checks
  - Connect to backend endpoints

- [ ] **VIP features:**
  - Update web UI for VIP features
  - Add subscription checks
  - Connect to backend endpoints

**Principle:** Don't expand backend — it's already "thick". Clients are "thin" and need to catch up.

**Acceptance Criteria:**
- PRO features accessible in iOS/web
- VIP features accessible in iOS/web
- Subscription checks work
- Backend endpoints properly connected
- No backend changes (only client integration)

**Related:**
- Existing PRO/VIP backend endpoints
- Subscription system

---

## Dependencies & Order

### Critical Path

1. **Sprint A** → Must complete before other sprints (security foundation)
2. **Sprint B** → Can start after PR-491 merge (documentation)
3. **Sprint C** → Can start in parallel with Sprint B (i18n + iOS)
4. **Sprint D** → Depends on Sprint C completion (iOS bootstrap needed)

### Parallel Work

- Sprint B (docs) and Sprint C (i18n) can run in parallel
- Sprint C (iOS bootstrap) can start while Sprint B (docs) is in progress

---

## Success Metrics

### Sprint A
- ✅ Security vulnerabilities resolved
- ✅ CI guards prevent dependency drift

### Sprint B
- ✅ Documentation complete and accurate
- ✅ Contract tests prevent API breakage
- ✅ Examples work for all scenarios

### Sprint C
- ✅ i18n centralized and testable
- ✅ iOS client can make API calls
- ✅ Basic iOS structure in place

### Sprint D
- ✅ PRO features accessible in clients
- ✅ VIP features accessible in clients
- ✅ Subscription flow works

---

## Notes

### Backend Status

- ✅ BMI visualization group-aware (PR-490B)
- ✅ Test organization clean (PR-491)
- ✅ Security updates (PR-487 merged)
- ✅ Architecture solid and maintainable

### Client Status

- ⏳ iOS: Needs bootstrap
- ⏳ Web: Needs PRO/VIP integration
- ⏳ i18n: Needs centralization

### Strategy

**Don't expand backend** — it's already feature-rich. Focus on:
- Client integration
- Documentation
- Testing
- i18n foundation

---

## Next Actions

1. **Immediate:**
   - ✅ PR-491 merged (test reorganization)
   - ✅ PR-487 merged (urllib3 update)
   - **Start Sprint A (PR-492)** — Verify urllib3 in Docker image

2. **This Week:**
   - Complete Sprint A (PR-492)
   - Start Sprint B (docs) and Sprint C (i18n) in parallel

3. **Next Week:**
   - Complete Sprint B and Sprint C
   - Start Sprint D (PRO/VIP integration)

---

## Related Documents

- `docs/pr/HANDOFF_PR_490_491.md` — Current context
- `docs/pr/RELEASE_NOTES_PR_490_491.md` — Recent changes
- `docs/pr/PR_487_REVIEW_CHECKLIST.md` — Security update
