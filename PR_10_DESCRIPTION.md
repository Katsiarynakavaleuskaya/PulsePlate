# PR-10: Weekly Plan Hardening (draft)

## Goal

Unify error handling for weekly plan endpoints and harden the weekly plan pipeline.

**No new features** — only stabilization, unified error envelope, and pipeline hardening.

---

## Scope

### ✅ What's included

1. **Unified error handling**
   - `safe_call()` wrapper for consistent error handling
   - `weekly_plan_error_envelope()` for unified error format
   - Production-safe: no exception details in responses

2. **Pipeline hardening**
   - Enforce pipeline stages: validation → auth/tier → generation → enrichment
   - No partial states: either success with valid payload or error envelope
   - Fail-fast on invalid state

3. **Hooks scaffolding** (no-op, for future analytics/explainability)
   - Interface for pipeline hooks
   - No actual analytics logic

4. **Targeted tests**
   - Error path coverage
   - Pipeline stage ordering guards
   - No brittle snapshots

---

## Commits

1. ✅ **add safe_call and unified error envelope** (done)
   - Created `app/services/weekly_plan/safety.py`
   - `safe_call()` with production masking
   - `weekly_plan_error_envelope()` with stage tracking

2. 🔄 **apply safe_call to weekly generation** (next)
   - PRO endpoint: `app/routers/pro.py::generate_week_plan()`
   - Premium endpoint: `app/routers/premium_week.py::generate_week_plan()`
   - Keep `HTTPException` for validation errors
   - Use `safe_call` only for generation stage

3. ⏳ **enforce pipeline ordering**
   - Fix stage order and return points
   - No partial state guarantees

4. ⏳ **add hooks interface (no-op)**
   - Pipeline hooks scaffolding
   - No analytics logic

5. ⏳ **targeted tests**
   - Error path coverage
   - Stage ordering guards

---

## Non-goals

- ❌ No new product features
- ❌ No Gradio/analytics implementation
- ❌ No infrastructure changes
- ❌ No VIP endpoint changes (already stabilized in PR-8b/8c/9d)
- ❌ No API contract changes (except unifying error format)

---

## Invariants

- **No public contract changes** (except error format unification)
- No I/O, no time/random nondeterminism in core
- Error responses: unified format (`status`, `code`, `detail`, `error`, optional `stage`)
- Small commits, each commit = green CI

---

## Security

- Production masking: no exception details in production responses
- `debug_ctx` excluded from production responses
- Centralized error handling reduces risk of information leaks

---

## Related PRs

- PR-8b: VIP Shoplist PDF export (stabilized VIP endpoints)
- PR-8c: VIP contract hardening
- PR-9d: Engineering lessons and policy guards
