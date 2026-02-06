## Audit Meta

- **PR**: PR-654
- **Scope**: backend security hardening (legacy nutrition alias guard)
- **Primary risk**: auth/tier guard bypass via direct handler call
- **Non-goals**: redesign of nutrition contracts, iOS feature work, subscription DB implementation

---

## Context (repo-truth)

### Canonical endpoint (SoT)

- `GET /api/v1/pro/nutrition/daily` is guarded with `require_pro_tier`.

### Deprecated legacy alias (compat-only)

- `GET /api/nutrition/{date_str}` exists for backward compatibility (legacy iOS path).
- Before PR-654 it extracted `X-API-Key` but **did not enforce** `require_pro_tier`, and directly called the
  canonical handler function — bypassing FastAPI dependency injection.

---

## Decision

- **Keep the alias for compatibility** (for now), but:
  - **Enforce `require_pro_tier`** in the alias handler.
  - **Hide** the legacy alias from OpenAPI (`include_in_schema=False`) to prevent new clients from adopting it.
  - Mark as **deprecated** in runtime routing metadata (`deprecated=True`).

Rationale: removes the bypass risk without breaking legacy clients immediately.

---

## Evidence (key facts)

### 1) Legacy alias exists in `legacy_app.py`

Command:

```bash
rg -n "\\/api\\/nutrition\\/\\{date_str\\}" legacy_app.py
```

Observed output:

```text
877:    "/api/nutrition/{date_str}",
```

Exit code: `0`

### 2) PRO guard implementation is `require_pro_tier`

Command:

```bash
rg -n "async def require_pro_tier" app/middleware/api_tiers.py
```

Observed output:

```text
165:async def require_pro_tier(x_api_key: Optional[str] = Security(api_key_header)) -> str:
```

Exit code: `0`

### 3) Canonical route is `/api/v1/pro/nutrition/daily`

Command:

```bash
rg -n "\\/nutrition\\/daily" app/routers/pro.py
```

Observed output:

```text
13:- /api/v1/pro/nutrition/daily - Daily nutrition tracking (Plate view)
370:    "/nutrition/daily",
```

Exit code: `0`

---

## Changes (behavioral)

- Legacy alias `/api/nutrition/{date_str}` now **requires a PRO API key** (`require_pro_tier`).
- Legacy alias is **deprecated and hidden from OpenAPI** (prevents new client adoption).
- Canonical endpoint behavior is unchanged.

---

## Tests (deterministic)

Command:

```bash
pytest -q tests/test_nutrition_daily.py
```

Observed output:

```text
..........................                                               [100%]
```

Exit code: `0`

Coverage note: tests explicitly assert 401/403/200 transitions on the legacy path to prevent regressions.

---

## Follow-ups / Deferred

- **Preferred long-term**: remove `/api/nutrition/{date_str}` entirely after iOS migration is complete.
- **iOS next step after PR-654**: move Plate to call canonical `GET /api/v1/pro/nutrition/daily` and treat the
  legacy alias as forbidden SoT (see `BACKLOG_LEDGER` P1 item).
