# PR-520 — Key Insights from Recent PRs (PR-510 through PR-520)

**Date:** 2026-01-12
**Scope:** Analysis of patterns, lessons, and anti-patterns from last 20 PRs
**Purpose:** Capture institutional knowledge to prevent repeated mistakes and establish canonical patterns

---

## 📋 Context: PR Sequence (PR-510 → PR-520)

### PR-515 (legacy_app audit, originally PR-510)
**Type:** Docs-only
**Key insight:** Audit-first approach prevents scope creep. Documenting "what must move" before "how to move it" creates clear boundaries.

### PR-517 (VIP Guard Consistency) — PR #517
**Type:** Runtime (auth layer)
**Key insights:**
- **Guard consistency requires matrix tests** — 17 endpoints × 3 tiers = 51 tests, but single parametrized test prevents duplication
- **OpenAPI artifacts must sync** — CI gate (`git diff --exit-code`) catches drift; use `Security(APIKeyHeader)` not `Header(None)`
- **FREE tier = empty headers** — not a "FREE key"; FREE users don't provide API key
- **Guard order matters** — tier checks (403) must run before payload validation (422)

### PR-518 (VIP Guard Matrix + Test Hygiene) — PR #518
**Type:** Tests-only
**Key insights:**
- **Canonical guard matrix prevents duplication** — single source of truth in `test_vip_tier_guard_matrix.py`
- **sys.modules mutations forbidden** — use `monkeypatch.delitem/setitem`, never direct `del sys.modules[...]`
- **importlib.reload forbidden** — use `monkeypatch.setattr()` for symbol patching
- **Env cleanup required** — all vars set in `setup_method` must be cleaned in `teardown_method` (xdist safety)
- **Dependency override pattern** — if test overrides guard, don't send tier headers (guard is bypassed)

### PR-519/520 (PRO/Premium Alias Contracts)
**Type:** Runtime (contracts)
**Key insights:**
- **Canonical endpoints must exist before aliases** — cannot proxy to non-existent endpoint
- **Contract mismatch = no proxy** — `PlateResponse` ≠ `DailyNutritionResponse`; must create matching canonical endpoint
- **Guard divergence is intentional** — premium aliases legacy-guarded for backward compatibility; auth alignment is separate decision. Guard divergence is tested at the contract level; do not attempt to unify guards without explicit product decision.
- **OpenAPI schema-only mode** — `app/routers/pro.py` excluded from schema; bootstrap routes (`pro_nutrition_contracts`) included

---

## 🎯 Recurring Patterns (Anti-Patterns to Avoid)

### 1. Scope Creep in Docs-Only PRs
**Problem:** Adding "small" code changes to docs PRs
**Solution:** Strict gate: `git diff --name-only origin/main...HEAD | rg -v '\.md$'` must be empty
**Evidence:** PR-510 → PR-515 (docs-only) had to be split from PR-509 (runtime)

### 2. Force Push Abuse
**Problem:** Repeated `--force-with-lease` after every amend
**Solution:** Force push is forbidden. Update PRs by adding new commits only. If branch got messy, create fresh branch and cherry-pick.
**Evidence:** User feedback: "опять пуш форс что ты заладил"

### 3. Test Pollution (xdist)
**Problem:** Env vars leak between test workers
**Solution:** Always clean env vars in `teardown_method`; prefer `monkeypatch.setenv` in autouse fixtures
**Evidence:** PR-518 fixed `VIP_MODULE_ENABLED` cleanup

### 4. sys.modules Direct Mutations
**Problem:** Direct `del sys.modules[...]` causes xdist flakiness
**Solution:** Always use `monkeypatch.delitem/setitem`
**Evidence:** PR-518 policy enforcement

### 5. importlib.reload in Tests
**Problem:** Forbidden by repo policy (`FORBID_IMPORTLIB_RELOAD`)
**Solution:** Use `monkeypatch.setattr()` for symbol patching
**Evidence:** PR-518 removed all `importlib.reload()` calls

### 6. OpenAPI Drift
**Problem:** Schema changes not reflected in frontend artifacts
**Solution:** CI gate (`git diff --exit-code`); always run `make openapi` after router changes
**Evidence:** PR-517 required OpenAPI sync

### 7. Guard Test Duplication
**Problem:** Multiple test files assert same guard matrix
**Solution:** Single canonical matrix in `test_vip_tier_guard_matrix.py`
**Evidence:** PR-518 consolidated 17 endpoints into one parametrized test

### 8. Contract Mismatch in Proxies
**Problem:** Attempting to proxy between endpoints with different response models
**Solution:** Hard-stop rule: never proxy between different `response_model` (breaking change)
**Evidence:** PR-519/520: `PlateResponse` ≠ `DailyNutritionResponse` → created canonical `pro/nutrition/plate`

---

## 🔧 Canonical Patterns (Established)

### 1. Tier Guard Testing
```python
# FREE = empty headers (no key)
# PRO = TEST_KEY_PRO
# VIP = TEST_KEY_VIP
# Assert: status code only (not error payload shape)
```

### 2. Dependency Override Pattern
```python
# If test overrides require_vip_tier → do NOT send vip_headers
# Test name should include _with_guard_bypassed marker
```

### 3. OpenAPI Security Scheme
```python
# Use Security(api_key_header), not Header(None)
# Prevents per-operation header params in schema
```

### 4. Env Var Cleanup
```python
# setup_method sets env vars
# teardown_method restores/pops all vars set in setup
# Use monkeypatch.setenv in autouse fixtures (preferred)
```

### 5. sys.modules Mutations
```python
# Always use monkeypatch.delitem/setitem
# Never: del sys.modules[...] or sys.modules[...] = ...
```

### 6. Contract Proxy Rules
```python
# Proxy only between same request/response models
# If contracts differ → create matching canonical endpoint first
```

---

## 📊 Metrics and Gates

### Common checks (subset; final gate is `make verify`)
1. `pytest tests/test_repo_policy_guards.py` — import hygiene
2. `make test-fast` — quick smoke
3. `make cov-check` — coverage >=97%
4. `make lint` — formatting
5. `make openapi` → `git diff --exit-code` — OpenAPI sync

**Final readiness claim uses `make verify` only (see AGENTS.md).**

### Test Patterns
- **Guard tests:** Status code only (not payload shape)
- **Contract tests:** Full response model validation
- **Parity tests:** Compare alias → canonical (same request/response models)

---

## 🚨 Critical Invariants (Must Not Break)

1. **Single FastAPI app instance** — `app.main:app` is entrypoint
2. **No sys.modules mutations** — except via monkeypatch
3. **No importlib.reload** — use monkeypatch.setattr
4. **No duplicate guard matrices** — single canonical source
5. **No contract-mismatch proxies** — same request/response models
6. **OpenAPI determinism** — schema-only mode must be stable
7. **Guard order** — tier (403) before validation (422)

---

## 💡 Process Insights

### PR Sequencing
1. **Audit first** (docs-only) → identify scope
2. **Runtime changes** → guard consistency, contracts
3. **Test hygiene** → cleanup, matrix consolidation
4. **OpenAPI sync** → gate, not afterthought

### Review Strategy
- **One PR = one logical change** — don't mix concerns
- **Minimal diff** — no "while we're at it" improvements
- **Verify once** — `make verify` before claiming readiness

### Git Hygiene
- **No force push** — force push is forbidden. Use new commits or fresh branch with cherry-pick.

**Why this policy changed (single-developer safe mode):**
Historically, this repo recommended "rebase + force-with-lease" to keep history linear. In practice, automated agents/tools occasionally attempted force-push on PR branches, creating churn and risking loss of context.
Because the project is currently maintained by a single developer and PR history is squashed on merge anyway, we prefer **non-rewriting updates**: add fixup commits (or revert) and let GitHub "Squash and merge" perform history cleanup.

- **Atomic commits** — one logical change per commit
- **Pre-commit hooks** — stage auto-fixes, commit separately

---

## 🔗 Related Documents

- `docs/ENGINEERING_LESSONS.md` — project-level lessons
- `RUNBOOK_AGENT.md` — CI/debug playbook
- `AGENTS.md` — canonical policies
- `docs/contracts/PRODUCT_TIER_MAP.md` — tier mapping
- `docs/contracts/PRODUCT_TIER_REMEDIATION_PLAN.md` — remediation roadmap

---

## 🎓 Key Takeaways for Future PRs

### 1. Always Audit First (Docs-Only)
- Document "what must change" before "how to change it"
- Prevents scope creep and establishes clear boundaries
- Example: PR-515 (audit, originally PR-510) → PR-516+ (implementation)

### 2. Test Hygiene is Non-Negotiable
- Env cleanup, sys.modules via monkeypatch, no importlib.reload
- Single canonical test matrix prevents duplication
- xdist safety requires proper isolation

### 3. OpenAPI Sync is a Gate, Not Afterthought
- Always run `make openapi` after router/schema changes
- CI enforces sync via `git diff --exit-code`
- Use `Security(APIKeyHeader)` not `Header(None)`

### 4. Guard Consistency Requires Matrix Tests
- Parametrized tests covering all endpoints × all tiers
- Single source of truth prevents duplication
- Status code assertions only (not payload shape)

### 5. Contract Mismatch = No Proxy
- Cannot proxy between different request/response models
- Create matching canonical endpoint first
- Example: `PlateResponse` ≠ `DailyNutritionResponse` → created `pro/nutrition/plate`

### 6. Guard Divergence Can Be Intentional
- Legacy endpoints may use different guards for backward compatibility
- Document the decision explicitly
- Auth alignment is separate from contract alignment
- **Guard divergence is intentional and tested at the contract level; do not attempt to unify guards in PR-520/521 without explicit product decision.**

### 7. One PR = One Logical Change
- Don't mix concerns (e.g., guard consistency + contract fixes)
- Minimal diff prevents review complexity
- Verify once before claiming readiness
- **All changes after review — only in response to specific blocking feedback, no "while we're at it" improvements**

---

## ✅ Enforcement Checklist (Copy/Paste into Every PR Description)

Before claiming PR is ready, verify:

- [ ] **Scope:** One logical change, no drive-by refactors
- [ ] **Contracts:** No contract-mismatch proxies (hard stop)
- [ ] **OpenAPI:** If schema changes: OpenAPI regenerated + `openapi-check` green
- [ ] **Test hygiene:** If env vars touched in tests: monkeypatch + cleanup (xdist-safe)
- [ ] **Import policy:** No `sys.modules` direct mutations, no `importlib.reload`
- [ ] **Guards:** Tier check must win over validation (403 before 422), no duplicate guard matrices
- [ ] **Final gate:** Run `make verify` once before merge (diff-cover ≥ 97%)

**Scope creep prevention:**
- All changes after review — only in response to specific blocking feedback
- No "while we're at it" improvements
- If reviewer suggests unrelated improvements → defer to separate PR

---

**Last updated:** 2026-01-12
**Next:** Apply these insights to PR-520 and future PRs
