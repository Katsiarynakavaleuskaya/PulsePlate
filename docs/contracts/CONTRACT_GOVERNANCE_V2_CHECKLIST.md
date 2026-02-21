# Contract Governance v2 Checklist

**Date:** 2026-02-21
**Status:** Active policy (Wave 2)
**Purpose:** Prevent contract drift and breaking changes across backend/web/iOS surfaces

---

## OpenAPI Diff Classification

Every PR that touches `app/routers/*`, `app/schemas/*`, or `app.main.app` routes must classify its OpenAPI impact:

| Label | Description | Review Gate |
|-------|-------------|-------------|
| **`breaking`** | Removes/renames endpoints, changes required fields, narrows enum values, changes response status codes | **Requires explicit owner approval + migration plan** |
| **`risky`** | Adds optional fields, widens enum values, adds new endpoints, changes default values | **Requires PR description acknowledgment + client impact note** |
| **`safe`** | Docs-only, internal refactors, no schema changes, test-only changes | **Standard review** |

### Breaking Change Examples

- Removing or renaming an endpoint path
- Removing or renaming a response field
- Changing a field from optional to required
- Narrowing enum values (removing a previously valid value)
- Changing response status codes for existing flows
- Changing authentication requirements (401/403 guard changes)

### Risky Change Examples

- Adding new optional fields to request/response schemas
- Adding new enum values
- Adding new endpoints (safe for backend, but may require client awareness)
- Changing default values for optional fields
- Adding rate limits or quotas to existing endpoints

### Safe Change Examples

- Documentation updates
- Internal implementation changes (no public contract impact)
- Test additions/modifications
- Performance optimizations (no behavior change)
- Refactoring without contract changes

---

## Contract Change Checklist (PR Gate)

Before merging any PR that modifies OpenAPI-visible contracts:

### 1. Schema Classification
- [ ] PR description includes `contract: breaking|risky|safe` label
- [ ] Classification matches actual diff impact (reviewer verifies)

### 2. OpenAPI Artifact Sync
- [ ] `make openapi` regenerated if backend schemas changed
- [ ] `make openapi-check` passes (artifacts committed)
- [ ] Determinism test green: `tests/test_openapi_determinism.py`

### 3. Client Impact Assessment
- [ ] **Web:** Frontend imports from `frontend/src/api/schema.ts` compile
- [ ] **iOS:** Manual review of affected DTO alignment (until OpenAPI codegen is enabled)
- [ ] **External:** Breaking changes documented with migration guidance

### 4. Breaking Change Protocol (if `breaking`)
- [ ] Migration path documented in PR description
- [ ] Deprecated alias created for removed/renamed endpoints (if applicable)
- [ ] Client migration tracked in `BACKLOG_LEDGER.md`
- [ ] Owner approval obtained

### 5. Rollback Plan
- [ ] Breaking changes are revertible without data migration
- [ ] Rollback procedure documented (or "revert PR" sufficient)

---

## Contract Review Checkpoint

Every non-draft PR triggers the following contract review flow:

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐
│ PR Created  │ --> │ OpenAPI Sync CI │ --> │ Schema Diff Gate │
└─────────────┘     └─────────────────┘     └──────────────────┘
                                                    │
                    ┌───────────────────────────────┴─────────────────┐
                    │                                                 │
                    v                                                 v
          ┌─────────────────┐                              ┌──────────────────┐
          │ No Schema Diff  │                              │ Schema Changed   │
          │ (auto-pass)     │                              │ (requires label) │
          └─────────────────┘                              └──────────────────┘
                                                                    │
                    ┌───────────────────────────────────────────────┴─────┐
                    │                         │                           │
                    v                         v                           v
          ┌─────────────────┐    ┌──────────────────┐      ┌──────────────────┐
          │ safe            │    │ risky            │      │ breaking         │
          │ Standard review │    │ + Impact note    │      │ + Owner approval │
          └─────────────────┘    └──────────────────┘      │ + Migration plan │
                                                           └──────────────────┘
```

---

## Backend/Web/iOS Contract Matrix

| Surface | Contract Source | Sync Mechanism | Breaking Change Impact |
|---------|-----------------|----------------|------------------------|
| **Backend** | `app/schemas/*.py` + `app/routers/*.py` | OpenAPI generation | API consumers break |
| **Web** | `frontend/src/api/schema.ts` (generated) | `make openapi` | TypeScript compile errors |
| **iOS** | Manual DTO alignment | Code review | Runtime decode failures |

### Cross-Surface Contract Rules

1. **Backend → Web:** Automatic sync via OpenAPI generation (`make openapi`)
2. **Backend → iOS:** Manual sync; breaking changes must include iOS DTO update PR (or ledger item)
3. **Web → Backend:** Frontend must not assume schema; always use generated types
4. **iOS → Backend:** Mobile must handle unknown fields gracefully (future-proofing)

---

## Evidence and Verification

### CI Gates

- `openapi-sync` job: Ensures `frontend/src/api/openapi.json` matches backend
- `test_openapi_determinism.py`: Ensures schema generation is reproducible
- PR Body Phase2 gates: Enforces contract label presence for schema-touching PRs

### Manual Verification Commands

```bash
# Regenerate OpenAPI artifacts
make openapi

# Verify artifacts are committed
make openapi-check

# Check OpenAPI diff (requires jq)
git diff origin/main -- frontend/src/api/openapi.json | head -100

# Run determinism test
pytest tests/test_openapi_determinism.py -v
```

---

## References

- OpenAPI Stability Policy: `docs/policy/openapi_stability.md`
- ADR-002 OpenAPI Schema-Only Mode: `docs/architecture/ADR-002-openapi-schema-only-mode.md`
- Product Tier Map: `docs/contracts/PRODUCT_TIER_MAP.md`
- AGENTS.md: "OpenAPI generation (determinism requirement)"

---

## KPIs (Wave 2 Target)

- **Contract-related rollback incidents:** 0
- **OpenAPI drift incidents detected pre-merge:** 100%

---

**Last updated:** 2026-02-21
# Contract Governance v2 Checklist

**Date:** 2026-02-21
**Status:** Active policy (Wave 2)
**Purpose:** Prevent contract drift and breaking changes across backend/web/iOS surfaces

---

## OpenAPI Diff Classification

Every PR that touches `app/routers/*`, `app/schemas/*`, or `app.main.app` routes must classify its OpenAPI impact:

| Label | Description | Review Gate |
|-------|-------------|-------------|
| **`breaking`** | Removes/renames endpoints, changes required fields, narrows enum values, changes response status codes | **Requires explicit owner approval + migration plan** |
| **`risky`** | Adds optional fields, widens enum values, adds new endpoints, changes default values | **Requires PR description acknowledgment + client impact note** |
| **`safe`** | Docs-only, internal refactors, no schema changes, test-only changes | **Standard review** |

### Breaking Change Examples

- Removing or renaming an endpoint path
- Removing or renaming a response field
- Changing a field from optional to required
- Narrowing enum values (removing a previously valid value)
- Changing response status codes for existing flows
- Changing authentication requirements (401/403 guard changes)

### Risky Change Examples

- Adding new optional fields to request/response schemas
- Adding new enum values
- Adding new endpoints (safe for backend, but may require client awareness)
- Changing default values for optional fields
- Adding rate limits or quotas to existing endpoints

### Safe Change Examples

- Documentation updates
- Internal implementation changes (no public contract impact)
- Test additions/modifications
- Performance optimizations (no behavior change)
- Refactoring without contract changes

---

## Contract Change Checklist (PR Gate)

Before merging any PR that modifies OpenAPI-visible contracts:

### 1. Schema Classification
- [ ] PR description includes `contract: breaking|risky|safe` label
- [ ] Classification matches actual diff impact (reviewer verifies)

### 2. OpenAPI Artifact Sync
- [ ] `make openapi` regenerated if backend schemas changed
- [ ] `make openapi-check` passes (artifacts committed)
- [ ] Determinism test green: `tests/test_openapi_determinism.py`

### 3. Client Impact Assessment
- [ ] **Web:** Frontend imports from `frontend/src/api/schema.ts` compile
- [ ] **iOS:** Manual review of affected DTO alignment (until OpenAPI codegen is enabled)
- [ ] **External:** Breaking changes documented with migration guidance

### 4. Breaking Change Protocol (if `breaking`)
- [ ] Migration path documented in PR description
- [ ] Deprecated alias created for removed/renamed endpoints (if applicable)
- [ ] Client migration tracked in `BACKLOG_LEDGER.md`
- [ ] Owner approval obtained

### 5. Rollback Plan
- [ ] Breaking changes are revertible without data migration
- [ ] Rollback procedure documented (or "revert PR" sufficient)

---

## Contract Review Checkpoint

Every non-draft PR triggers the following contract review flow:

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐
│ PR Created  │ --> │ OpenAPI Sync CI │ --> │ Schema Diff Gate │
└─────────────┘     └─────────────────┘     └──────────────────┘
                                                    │
                    ┌───────────────────────────────┴─────────────────┐
                    │                                                 │
                    v                                                 v
          ┌─────────────────┐                              ┌──────────────────┐
          │ No Schema Diff  │                              │ Schema Changed   │
          │ (auto-pass)     │                              │ (requires label) │
          └─────────────────┘                              └──────────────────┘
                                                                    │
                    ┌───────────────────────────────────────────────┴─────┐
                    │                         │                           │
                    v                         v                           v
          ┌─────────────────┐    ┌──────────────────┐      ┌──────────────────┐
          │ safe            │    │ risky            │      │ breaking         │
          │ Standard review │    │ + Impact note    │      │ + Owner approval │
          └─────────────────┘    └──────────────────┘      │ + Migration plan │
                                                           └──────────────────┘
```

---

## Backend/Web/iOS Contract Matrix

| Surface | Contract Source | Sync Mechanism | Breaking Change Impact |
|---------|-----------------|----------------|------------------------|
| **Backend** | `app/schemas/*.py` + `app/routers/*.py` | OpenAPI generation | API consumers break |
| **Web** | `frontend/src/api/schema.ts` (generated) | `make openapi` | TypeScript compile errors |
| **iOS** | Manual DTO alignment | Code review | Runtime decode failures |

### Cross-Surface Contract Rules

1. **Backend → Web:** Automatic sync via OpenAPI generation (`make openapi`)
2. **Backend → iOS:** Manual sync; breaking changes must include iOS DTO update PR (or ledger item)
3. **Web → Backend:** Frontend must not assume schema; always use generated types
4. **iOS → Backend:** Mobile must handle unknown fields gracefully (future-proofing)

---

## Evidence and Verification

### CI Gates

- `openapi-sync` job: Ensures `frontend/src/api/openapi.json` matches backend
- `test_openapi_determinism.py`: Ensures schema generation is reproducible
- PR Body Phase2 gates: Enforces contract label presence for schema-touching PRs

### Manual Verification Commands

```bash
# Regenerate OpenAPI artifacts
make openapi

# Verify artifacts are committed
make openapi-check

# Check OpenAPI diff (requires jq)
git diff origin/main -- frontend/src/api/openapi.json | head -100

# Run determinism test
pytest tests/test_openapi_determinism.py -v
```

---

## References

- OpenAPI Stability Policy: `docs/policy/openapi_stability.md`
- ADR-002 OpenAPI Schema-Only Mode: `docs/architecture/ADR-002-openapi-schema-only-mode.md`
- Product Tier Map: `docs/contracts/PRODUCT_TIER_MAP.md`
- AGENTS.md: "OpenAPI generation (determinism requirement)"

---

## KPIs (Wave 2 Target)

- **Contract-related rollback incidents:** 0
- **OpenAPI drift incidents detected pre-merge:** 100%

---

**Last updated:** 2026-02-21
# Contract Governance v2 Checklist

**Date:** 2026-02-21
**Status:** Active policy (Wave 2)
**Purpose:** Prevent contract drift and breaking changes across backend/web/iOS surfaces

---

## OpenAPI Diff Classification

Every PR that touches `app/routers/*`, `app/schemas/*`, or `app.main.app` routes must classify its OpenAPI impact:

| Label | Description | Review Gate |
|-------|-------------|-------------|
| **`breaking`** | Removes/renames endpoints, changes required fields, narrows enum values, changes response status codes | **Requires explicit owner approval + migration plan** |
| **`risky`** | Adds optional fields, widens enum values, adds new endpoints, changes default values | **Requires PR description acknowledgment + client impact note** |
| **`safe`** | Docs-only, internal refactors, no schema changes, test-only changes | **Standard review** |

### Breaking Change Examples

- Removing or renaming an endpoint path
- Removing or renaming a response field
- Changing a field from optional to required
- Narrowing enum values (removing a previously valid value)
- Changing response status codes for existing flows
- Changing authentication requirements (401/403 guard changes)

### Risky Change Examples

- Adding new optional fields to request/response schemas
- Adding new enum values
- Adding new endpoints (safe for backend, but may require client awareness)
- Changing default values for optional fields
- Adding rate limits or quotas to existing endpoints

### Safe Change Examples

- Documentation updates
- Internal implementation changes (no public contract impact)
- Test additions/modifications
- Performance optimizations (no behavior change)
- Refactoring without contract changes

---

## Contract Change Checklist (PR Gate)

Before merging any PR that modifies OpenAPI-visible contracts:

### 1. Schema Classification
- [ ] PR description includes `contract: breaking|risky|safe` label
- [ ] Classification matches actual diff impact (reviewer verifies)

### 2. OpenAPI Artifact Sync
- [ ] `make openapi` regenerated if backend schemas changed
- [ ] `make openapi-check` passes (artifacts committed)
- [ ] Determinism test green: `tests/test_openapi_determinism.py`

### 3. Client Impact Assessment
- [ ] **Web:** Frontend imports from `frontend/src/api/schema.ts` compile
- [ ] **iOS:** Manual review of affected DTO alignment (until OpenAPI codegen is enabled)
- [ ] **External:** Breaking changes documented with migration guidance

### 4. Breaking Change Protocol (if `breaking`)
- [ ] Migration path documented in PR description
- [ ] Deprecated alias created for removed/renamed endpoints (if applicable)
- [ ] Client migration tracked in `BACKLOG_LEDGER.md`
- [ ] Owner approval obtained

### 5. Rollback Plan
- [ ] Breaking changes are revertible without data migration
- [ ] Rollback procedure documented (or "revert PR" sufficient)

---

## Contract Review Checkpoint

Every non-draft PR triggers the following contract review flow:

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐
│ PR Created  │ --> │ OpenAPI Sync CI │ --> │ Schema Diff Gate │
└─────────────┘     └─────────────────┘     └──────────────────┘
                                                    │
                    ┌───────────────────────────────┴─────────────────┐
                    │                                                 │
                    v                                                 v
          ┌─────────────────┐                              ┌──────────────────┐
          │ No Schema Diff  │                              │ Schema Changed   │
          │ (auto-pass)     │                              │ (requires label) │
          └─────────────────┘                              └──────────────────┘
                                                                    │
                    ┌───────────────────────────────────────────────┴─────┐
                    │                         │                           │
                    v                         v                           v
          ┌─────────────────┐    ┌──────────────────┐      ┌──────────────────┐
          │ safe            │    │ risky            │      │ breaking         │
          │ Standard review │    │ + Impact note    │      │ + Owner approval │
          └─────────────────┘    └──────────────────┘      │ + Migration plan │
                                                           └──────────────────┘
```

---

## Backend/Web/iOS Contract Matrix

| Surface | Contract Source | Sync Mechanism | Breaking Change Impact |
|---------|-----------------|----------------|------------------------|
| **Backend** | `app/schemas/*.py` + `app/routers/*.py` | OpenAPI generation | API consumers break |
| **Web** | `frontend/src/api/schema.ts` (generated) | `make openapi` | TypeScript compile errors |
| **iOS** | Manual DTO alignment | Code review | Runtime decode failures |

### Cross-Surface Contract Rules

1. **Backend → Web:** Automatic sync via OpenAPI generation (`make openapi`)
2. **Backend → iOS:** Manual sync; breaking changes must include iOS DTO update PR (or ledger item)
3. **Web → Backend:** Frontend must not assume schema; always use generated types
4. **iOS → Backend:** Mobile must handle unknown fields gracefully (future-proofing)

---

## Evidence and Verification

### CI Gates

- `openapi-sync` job: Ensures `frontend/src/api/openapi.json` matches backend
- `test_openapi_determinism.py`: Ensures schema generation is reproducible
- PR Body Phase2 gates: Enforces contract label presence for schema-touching PRs

### Manual Verification Commands

```bash
# Regenerate OpenAPI artifacts
make openapi

# Verify artifacts are committed
make openapi-check

# Check OpenAPI diff (requires jq)
git diff origin/main -- frontend/src/api/openapi.json | head -100

# Run determinism test
pytest tests/test_openapi_determinism.py -v
```

---

## References

- OpenAPI Stability Policy: `docs/policy/openapi_stability.md`
- ADR-002 OpenAPI Schema-Only Mode: `docs/architecture/ADR-002-openapi-schema-only-mode.md`
- Product Tier Map: `docs/contracts/PRODUCT_TIER_MAP.md`
- AGENTS.md: "OpenAPI generation (determinism requirement)"

---

## KPIs (Wave 2 Target)

- **Contract-related rollback incidents:** 0
- **OpenAPI drift incidents detected pre-merge:** 100%

---

**Last updated:** 2026-02-21
# Contract Governance v2 Checklist

**Date:** 2026-02-21
**Status:** Active policy (Wave 2)
**Purpose:** Prevent contract drift and breaking changes across backend/web/iOS surfaces

---

## OpenAPI Diff Classification

Every PR that touches `app/routers/*`, `app/schemas/*`, or `app.main.app` routes must classify its OpenAPI impact:

| Label | Description | Review Gate |
|-------|-------------|-------------|
| **`breaking`** | Removes/renames endpoints, changes required fields, narrows enum values, changes response status codes | **Requires explicit owner approval + migration plan** |
| **`risky`** | Adds optional fields, widens enum values, adds new endpoints, changes default values | **Requires PR description acknowledgment + client impact note** |
| **`safe`** | Docs-only, internal refactors, no schema changes, test-only changes | **Standard review** |

### Breaking Change Examples

- Removing or renaming an endpoint path
- Removing or renaming a response field
- Changing a field from optional to required
- Narrowing enum values (removing a previously valid value)
- Changing response status codes for existing flows
- Changing authentication requirements (401/403 guard changes)

### Risky Change Examples

- Adding new optional fields to request/response schemas
- Adding new enum values
- Adding new endpoints (safe for backend, but may require client awareness)
- Changing default values for optional fields
- Adding rate limits or quotas to existing endpoints

### Safe Change Examples

- Documentation updates
- Internal implementation changes (no public contract impact)
- Test additions/modifications
- Performance optimizations (no behavior change)
- Refactoring without contract changes

---

## Contract Change Checklist (PR Gate)

Before merging any PR that modifies OpenAPI-visible contracts:

### 1. Schema Classification
- [ ] PR description includes `contract: breaking|risky|safe` label
- [ ] Classification matches actual diff impact (reviewer verifies)

### 2. OpenAPI Artifact Sync
- [ ] `make openapi` regenerated if backend schemas changed
- [ ] `make openapi-check` passes (artifacts committed)
- [ ] Determinism test green: `tests/test_openapi_determinism.py`

### 3. Client Impact Assessment
- [ ] **Web:** Frontend imports from `frontend/src/api/schema.ts` compile
- [ ] **iOS:** Manual review of affected DTO alignment (until OpenAPI codegen is enabled)
- [ ] **External:** Breaking changes documented with migration guidance

### 4. Breaking Change Protocol (if `breaking`)
- [ ] Migration path documented in PR description
- [ ] Deprecated alias created for removed/renamed endpoints (if applicable)
- [ ] Client migration tracked in `BACKLOG_LEDGER.md`
- [ ] Owner approval obtained

### 5. Rollback Plan
- [ ] Breaking changes are revertible without data migration
- [ ] Rollback procedure documented (or "revert PR" sufficient)

---

## Contract Review Checkpoint

Every non-draft PR triggers the following contract review flow:

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐
│ PR Created  │ --> │ OpenAPI Sync CI │ --> │ Schema Diff Gate │
└─────────────┘     └─────────────────┘     └──────────────────┘
                                                    │
                    ┌───────────────────────────────┴─────────────────┐
                    │                                                 │
                    v                                                 v
          ┌─────────────────┐                              ┌──────────────────┐
          │ No Schema Diff  │                              │ Schema Changed   │
          │ (auto-pass)     │                              │ (requires label) │
          └─────────────────┘                              └──────────────────┘
                                                                    │
                    ┌───────────────────────────────────────────────┴─────┐
                    │                         │                           │
                    v                         v                           v
          ┌─────────────────┐    ┌──────────────────┐      ┌──────────────────┐
          │ safe            │    │ risky            │      │ breaking         │
          │ Standard review │    │ + Impact note    │      │ + Owner approval │
          └─────────────────┘    └──────────────────┘      │ + Migration plan │
                                                           └──────────────────┘
```

---

## Backend/Web/iOS Contract Matrix

| Surface | Contract Source | Sync Mechanism | Breaking Change Impact |
|---------|-----------------|----------------|------------------------|
| **Backend** | `app/schemas/*.py` + `app/routers/*.py` | OpenAPI generation | API consumers break |
| **Web** | `frontend/src/api/schema.ts` (generated) | `make openapi` | TypeScript compile errors |
| **iOS** | Manual DTO alignment | Code review | Runtime decode failures |

### Cross-Surface Contract Rules

1. **Backend → Web:** Automatic sync via OpenAPI generation (`make openapi`)
2. **Backend → iOS:** Manual sync; breaking changes must include iOS DTO update PR (or ledger item)
3. **Web → Backend:** Frontend must not assume schema; always use generated types
4. **iOS → Backend:** Mobile must handle unknown fields gracefully (future-proofing)

---

## Evidence and Verification

### CI Gates

- `openapi-sync` job: Ensures `frontend/src/api/openapi.json` matches backend
- `test_openapi_determinism.py`: Ensures schema generation is reproducible
- PR Body Phase2 gates: Enforces contract label presence for schema-touching PRs

### Manual Verification Commands

```bash
# Regenerate OpenAPI artifacts
make openapi

# Verify artifacts are committed
make openapi-check

# Check OpenAPI diff (requires jq)
git diff origin/main -- frontend/src/api/openapi.json | head -100

# Run determinism test
pytest tests/test_openapi_determinism.py -v
```

---

## References

- OpenAPI Stability Policy: `docs/policy/openapi_stability.md`
- ADR-002 OpenAPI Schema-Only Mode: `docs/architecture/ADR-002-openapi-schema-only-mode.md`
- Product Tier Map: `docs/contracts/PRODUCT_TIER_MAP.md`
- AGENTS.md: "OpenAPI generation (determinism requirement)"

---

## KPIs (Wave 2 Target)

- **Contract-related rollback incidents:** 0
- **OpenAPI drift incidents detected pre-merge:** 100%

---

**Last updated:** 2026-02-21
