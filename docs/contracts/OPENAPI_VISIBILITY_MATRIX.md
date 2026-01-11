# OpenAPI Visibility Matrix — What to Show/Hide

**Purpose:** Canonical policy for what endpoints appear in public OpenAPI schema
**Last updated:** 2026-01-11
**Source of truth:** This document + `AGENTS.md` section "Product tiers and API namespaces"

---

## Public OpenAPI Schema (Default)

### ✅ Show (Canonical Product Surface)

| Namespace | Tier | Status | Rationale |
|-----------|------|--------|-----------|
| `/api/v1/bmi/*` | FREE | ✅ Show | Free surface (product entry point) |
| `/api/v1/pro/*` | PRO | ✅ Show | Pro surface (canonical PRO tier) |
| `/api/v1/vip/*` | VIP | ✅ Show | VIP surface (canonical VIP tier) |

**Rule:** Only canonical namespaces appear in public OpenAPI.

---

### ❌ Hide (Deprecated / Internal / Ops)

| Category | Examples | Rationale |
|----------|----------|-----------|
| **Deprecated aliases** | `/api/v1/premium/*` | Prevent frontend from generating types for wrong paths. Force migration to canonical namespaces. |
| **Admin/Ops** | `/api/v1/admin/*`, `/admin/*` | Security: internal operations should not be exposed. |
| **Debug** | `/debug*`, `/debug_env` | Security: debug endpoints leak internal state. |
| **Test routes** | `/api/v1/test/*` | Not product surface. |
| **Internal exports/demo** | `/api/v1/*/exports/*` (if not productized) | Not ready for public consumption. |
| **Maintenance/updaters** | `/api/v1/off/update`, `/api/v1/catalog/update` | Ops endpoints, not product API. |

**Rule:** Set `include_in_schema=False` on these endpoints/routers.

---

## Implementation

### How to hide endpoints

#### Option 1: Router-level (recommended for deprecated namespaces)

```python
# app/routers/premium_week.py
router = APIRouter(
    prefix="/api/v1/premium",
    tags=["premium"],
    include_in_schema=False  # Hide entire router from OpenAPI
)
```

#### Option 2: Endpoint-level (for selective hiding)

```python
@router.post(
    "/api/v1/premium/plan/week",
    include_in_schema=False,  # Hide this specific endpoint
    deprecated=True,  # Optional: mark as deprecated if still visible
)
async def premium_plan_week(...):
    ...
```

---

## Verification

### Check what's in OpenAPI

```bash
# List all paths in OpenAPI schema
jq -r '.paths | keys[]' frontend/src/api/openapi.json | sort

# Count deprecated paths (should be 0)
jq -r '.paths | keys[]' frontend/src/api/openapi.json | grep -c "/premium" || echo "0"
# Expected: 0

# Count admin paths (should be 0)
jq -r '.paths | keys[]' frontend/src/api/openapi.json | grep -c "/admin" || echo "0"
# Expected: 0
```

### CI Gate

```bash
# In CI, fail if deprecated paths appear in schema
make openapi
if jq -r '.paths | keys[]' frontend/src/api/openapi.json | grep -q "/premium"; then
    echo "ERROR: /premium/* paths found in OpenAPI schema"
    exit 1
fi
```

---

## Exceptions (Future)

### Internal/ops schema (if needed)

If we ever need a separate OpenAPI schema for internal/ops endpoints:

- **Separate generator:** `scripts/generate_openapi_internal.py`
- **Separate output:** `frontend/src/api/openapi-internal.json`
- **Separate CI check:** Only for internal tooling, not public API

**Status:** Not implemented. Current policy: hide internal endpoints from public schema.

---

## Related Documents

- `docs/contracts/PRODUCT_TIER_MAP.md` — canonical tier mapping
- `docs/contracts/OPENAPI_PATHS_AUDIT.md` — factual inventory of paths
- `AGENTS.md` — "Product tiers and API namespaces" section
- PR-B: Schema hygiene (description will be created in PR-B branch)
