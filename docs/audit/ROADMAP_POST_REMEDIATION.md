# Roadmap: Post-Remediation PRs (PR-A through PR-D)

**Date:** 2026-01-16
**Status:** Canonical Roadmap
**Purpose:** Structured plan for post-remediation work after PR #535

---

## 🎯 Overview

This roadmap defines four sequential PRs to be executed after P0 remediation (PR #535) is merged:

- **PR-A:** Post-remediation cleanup (dead code, orphan tests, mocks)
- **PR-B:** Product contract / soft paywall audit (documentation only)
- **PR-C:** Legal / compliance pack (wellness positioning)
- **PR-D:** Frontend audit (only after backend is stable)

**Hard Rule:** PR-D is **forbidden** until remediation + PR-A cleanup are complete.

---

## PR-A: Post-Remediation Cleanup (P1)

**Goal:** Remove dead code, clean up legacy remnants, update tests/mocks, remove "tests for missing places", update coverage hints, align mocks/patches with engine.

### Audit Questions (What to Look For)

#### 1. Dead Code / Orphan Modules

**Questions:**
- Which files/modules are no longer imported after remediation?
- Are there "registration lists" of modules/routers that are no longer used?
- Are there helper functions that were replaced by canonical paths?

**Search commands:**
```bash
# Find unused imports
ruff check --select F401 .

# Find modules that are never imported
grep -r "from.*import" . | grep -v "test" | sort | uniq

# Check for deleted module references
grep -r "bmi_extras_pro\|bmi_extras_simple" . --exclude-dir=.git
```

#### 2. Legacy Remnants

**Questions:**
- Is there any import/delegation back to legacy layers (especially around BMI/interpretation/extras)?
- Are there "compat" endpoints that execute business logic instead of thin proxy?
- Are there legacy constants that are no longer referenced?

**Search commands:**
```bash
# Find legacy imports
grep -r "from bmi_core\|import bmi_core" . --exclude-dir=.git

# Find compat endpoints
grep -r "compat\|legacy\|deprecated" app/routers/ --include="*.py"
```

#### 3. Tests for "Missing Places"

**Questions:**
- Which tests check structure instead of behavior (e.g., "file must exist/not exist", "module must be stub")?
- Are there tests that became "false shields" (because they fixate on old architecture)?
- Are there tests that import deleted modules (`bmi_extras_pro`, `bmi_extras_simple`)?

**Search commands:**
```bash
# Find tests that check for deleted modules
grep -r "bmi_extras_pro\|bmi_extras_simple" tests/

# Find tests that check file existence
grep -r "Path.*exists\|os.path.exists\|file.*exist" tests/ --include="*.py"
```

#### 4. Coverage Hints / Exception Lists

**Questions:**
- Where are "coverage hints" located and why are they still needed?
- Can exceptions be removed/narrowed without breaking stability?
- Are there coverage exclusion lists that are outdated?

**Search commands:**
```bash
# Find coverage configuration
grep -r "coverage\|\.coveragerc\|coverage\.ini" . --include="*.{py,ini,toml,yaml,yml}"

# Find coverage excludes
grep -r "omit\|exclude" .coveragerc pyproject.toml setup.cfg 2>/dev/null
```

#### 5. Mocks/Patches Under Engine

**Questions:**
- Which tests patch legacy functions/endpoints instead of `core/* engine`?
- Can we migrate to dependency overrides (and remove `sys.modules`/reload tricks) to stabilize the suite?
- Are there xfailed tests that can be fixed by using engine mocks?

**Search commands:**
```bash
# Find sys.modules mutations
grep -r "sys\.modules\[" tests/ --include="*.py"

# Find xfailed tests
grep -r "@pytest.mark.xfail" tests/ --include="*.py"

# Find importlib.reload
grep -r "importlib.reload\|reload(" tests/ --include="*.py"
```

### DoD (Definition of Done) for PR-A

- [ ] `pytest` green, xfail count reduced or eliminated
- [ ] No "structural tests" without explicit value
- [ ] Dead code removed (not "covered by test")
- [ ] `AGENTS.md` updated: what's forbidden/what was removed/what's the new mock pattern
- [ ] `make verify` → PASS
- [ ] `make cov-check` → PASS (≥97%)
- [ ] `make diff-cov` → PASS (≥97%)

---

## PR-B: Product Contract / Soft Paywall Audit (P1)

**Goal:** Document Free→Pro hook (soft paywall) **without UI** and without interfering with remediation.

### Audit Questions (What to Document)

#### 1. Free→Pro Hook Point

**Questions:**
- Where exactly does the "PRO offer point" occur in Free flow?
- What is the **minimal** contract entity needed by backend (e.g., `pro_hook: { title, body, cta, deeplink }`), so frontend is thin?
- What triggers the hook (BMI calculation result? threshold? feature limit?)?

**Search commands:**
```bash
# Find PRO tier checks
grep -r "require_pro_tier\|PRO\|pro_tier" app/routers/ --include="*.py"

# Find Free tier endpoints
grep -r "FREE\|free_tier" app/routers/ --include="*.py"
```

#### 2. i18n Keys and Structure

**Questions:**
- RU/EN/ES texts: what i18n keys, where do they live, how do we test determinism?
- Are there hardcoded strings that should be i18n keys?
- Is there a canonical i18n structure for PRO hooks?

**Search commands:**
```bash
# Find i18n usage
grep -r "i18n\|Language\|t(" core/ app/ --include="*.py"

# Find hardcoded PRO-related strings
grep -r "PRO\|premium\|upgrade" app/routers/ --include="*.py" | grep -v "import\|#"
```

#### 3. Wellness, Not Medical Guarantee

**Questions:**
- What formulations, tone, prohibition on diagnosis/treatment?
- Where are disclaimers currently located?
- Are there any medical language that needs to be removed?

**Search commands:**
```bash
# Find disclaimers
grep -r "disclaimer\|medical\|diagnosis\|treatment" . --include="*.py" -i

# Check core/disclaimers.py
cat core/disclaimers.py
```

#### 4. What NOT to Do in PR-B

**Explicitly forbidden:**
- ❌ No UI changes
- ❌ No payment integration
- ❌ No interpretation logic changes ("how in PRO")
- ❌ No new features

**Allowed:**
- ✅ i18n key definitions
- ✅ API contract documentation
- ✅ Text content (wellness positioning)

---

## PR-C: Legal / Compliance Pack (P1)

**Goal:** Disclaimer + Terms + Privacy (RU/EN/ES), markets CIS + EU/US — at text and tone level.

### Audit Questions

#### 1. Single Source of Truth

**Questions:**
- Where will be the "single source of truth" for texts (docs/ + export to app)?
- Should texts live in `core/disclaimers.py` or separate legal module?
- How do we export texts to API responses?

**Search commands:**
```bash
# Check existing disclaimers structure
cat core/disclaimers.py

# Find legal-related modules
find . -name "*legal*" -o -name "*disclaimer*" -o -name "*terms*" -o -name "*privacy*"
```

#### 2. Visibility Points

**Questions:**
- In which product places should texts be visible (API response? separate endpoint? static pages later)?
- Should there be a `/legal/disclaimer` endpoint?
- Should disclaimers be in every API response or opt-in?

#### 3. Forbidden Formulations

**Questions:**
- What formulations are strictly forbidden (medicine/diagnosis/treatment/disease prediction)?
- Are there any current texts that violate wellness positioning?
- What tone is required (informational, not medical advice)?

#### 4. Privacy Data Collection

**Questions:**
- What data do we actually collect/not collect now (logging, analytics, IP, identifiers)?
- What data is stored vs. ephemeral?
- Are there any PII/PHI in logs?

**Search commands:**
```bash
# Find logging statements
grep -r "logging\|logger" app/ core/ --include="*.py" | grep -i "log\|print"

# Find analytics
grep -r "analytics\|tracking\|telemetry" . --include="*.py" -i
```

#### 5. US/EU Tone and Structure

**Questions:**
- What tone is required for US market (informational, not medical advice)?
- What tone is required for EU market (GDPR compliance)?
- Are there region-specific disclaimers needed?

---

## PR-D: Frontend Audit (P2 - Only After Backend Stable)

**Hard Rule:** PR-D is **forbidden** until:
- ✅ Remediation PR merged
- ✅ PR-A cleanup merged
- ✅ Backend guards green
- ✅ `make verify` passes

### Audit Questions

#### iOS (SwiftUI Thin Client)

**Questions:**
1. Which endpoints does iOS actually call (path/method/DTO)?
2. Is there **any BMI logic** on client (formulas/categories/thresholds)? → Should be 0.
3. Where do models live: generated from OpenAPI or manual DTOs? (Manual forbidden if type exists in OpenAPI)
4. How is error localization RU/EN/ES structured: do keys match API?
5. Mocks/stubs: do they match OpenAPI (without "fantasies")?

**Search commands:**
```bash
# Find BMI logic in iOS
grep -r "bmi\|BMI" ios/ --include="*.swift" | grep -v "//\|import\|struct\|class"

# Find API calls
grep -r "URLRequest\|URLSession\|api" ios/ --include="*.swift" | head -20

# Find manual DTOs
find ios/ -name "*Model*.swift" -o -name "*DTO*.swift"
```

#### Web (React/Vite Thin Client)

**Questions:**
1. Does `schema.ts` generation from OpenAPI pass gate `make openapi && git diff ...`?
2. Are there legacy paths `/premium/*` in runtime calls (should be hidden or shim only)?
3. Are there manual types in `frontend/src/api/*` (duplicate schema) — remove.
4. MSW handlers / mocks: updated to canonical paths?
5. UI error states: match contract (422/401/403) without "invented" fields?

**Search commands:**
```bash
# Find legacy premium paths
grep -r "/premium/" frontend/src/ --include="*.{ts,tsx}"

# Find manual types
grep -r "interface.*Response\|type.*Request" frontend/src/api/ --include="*.ts" | grep -v "schema.ts"

# Find MSW handlers
find frontend/ -name "*msw*" -o -name "*mock*" | head -10
```

#### Alignment / PR-525 (Return)

**Questions:**
1. What is the divergence point: path/method/model/labels?
2. Which endpoints are "needed by frontend" but hidden from schema (`include_in_schema=False`)?
3. Are there deprecated aliases that accidentally got into OpenAPI?
4. Are there "silent feature flags" that change contract without docs reflection?
5. Post-check: after fixes — did we update PR template / checklist links?

**Search commands:**
```bash
# Find include_in_schema=False
grep -r "include_in_schema.*False" app/routers/ --include="*.py"

# Find deprecated endpoints
grep -r "deprecated.*True" app/routers/ --include="*.py"
```

---

## 🔒 Current Blockers in Main

### A) Trivy Code Scanning: glibc CVE-2026-0861 (CRITICAL)

**Status:** Unfixed upstream in Debian (bookworm)

**Strategy:**
1. Create separate PR-SEC (quick, minimal):
   - Document fact "unfixed upstream in distro"
   - Add **temporary** suppression/ignore in Trivy **with expiry** (strict date + CVE link + condition to remove when fixed version appears)
2. Parallel:
   - Update base image to latest digest + security updates at build time
   - Monitor when Debian/Upstream release patch
3. If policy "no CRITICAL merges": switch to base image/distro where glibc is already fixed, or temporarily use musl-base (Alpine) if compatibility OK

**Security Notes:**
- Exploitability depends on ability to "feed" too large alignment to memalign-family. In typical Python/FastAPI this is usually not direct user-input, but it's still a system library → triage/acceptance must be documented.

### B) CD-Test #252: `ghcr.io` denied

**Status:** Authentication/permissions issue

**Fix checklist:**
1. Workflow job must have: `permissions: packages: read` (and usually `contents: read`)
2. Before `docker pull`, do login: `docker/login-action` with `registry: ghcr.io`, `username: ${{ github.repository_owner }}`, `password: ${{ secrets.GHCR_READ_TOKEN }}`
3. In package settings (GHCR) → **"Actions access"**: repository needs permission to access package
4. If workflow runs from fork PR: GITHUB_TOKEN/permissions may be restricted (and no secrets). Then options:
   - Don't pull private image in PR context
   - Or make image public
   - Or `pull_request_target` (carefully, security risk)

**Note:** Fix already applied in PR #536, but token must be added to GitHub Secrets (staging environment).

---

## 📋 AGENTS.md Updates Required

1. **Policy on "unfixed distro CVE":** How to act (ignore with expiry + separate security PR + monitor fixed version)
2. **Policy on GHCR in CI:** Required job permissions + mandatory docker login before pull
3. **Explicit rule:** Frontend audit PR-D forbidden until remediation+PR-A (already canon, but better keep as "gate")

---

**Last updated:** 2026-01-16
**Status:** Canonical Roadmap
