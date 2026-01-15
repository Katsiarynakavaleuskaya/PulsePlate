# PR: FREE → PRO Soft Paywall & Education Layer

**Type:** Product / UX Enhancement
**Priority:** P1 (After Backend P0 Remediation)
**Status:** Planned (Not Started)
**Depends on:** Backend P0 Remediation PR (must be merged, guards green)

---

## 🎯 What

Adds FREE → PRO soft paywall and education layer to communicate product tier differences and limitations.

**This PR does NOT implement UI** — it establishes:
- Product contract documentation
- Soft paywall copy (RU/EN/ES)
- Legal disclaimers (wellness positioning)
- Backend response structure for limitations/next_step

---

## Why

**Product Need:**
- FREE tier must be honest about limitations (builds trust)
- Soft paywall should educate, not sell (CIS/EU market preference)
- Clear tier differentiation prevents user confusion

**Business Need:**
- Trust-based conversion (not fear-based)
- Regulatory compliance (wellness, not medicine)
- Scalable pattern for all FREE modules

**See:**
- `docs/product/FREE_PRO_CONTRACT.md` — Product tier contract
- `docs/product/FREE_PRO_SOFT_PAYWALL.md` — Soft paywall copy
- `docs/legal/WELLNESS_DISCLAIMER.md` — Legal compliance

---

## Changes

### 1. Product Documentation

**New files:**
- `docs/product/FREE_PRO_CONTRACT.md` — Tier contract (FREE/PRO/VIP)
- `docs/product/FREE_PRO_SOFT_PAYWALL.md` — Soft paywall copy

**Purpose:** Canonical product specification for all tiers.

---

### 2. Legal Documentation

**New files:**
- `docs/legal/WELLNESS_DISCLAIMER.md` — Legal disclaimers (RU/EN/ES)
- `docs/legal/COPY_RULES_WELLNESS.md` — Copywriting guidelines
- `docs/legal/RISK_LANGUAGE_GUIDE.md` — Risk language guidelines

**Purpose:** Ensure regulatory compliance (CIS/EU/US markets).

---

### 3. Backend Response Structure (Optional, Future)

**File:** `app/routers/bmi.py` (FREE endpoint)

**Add to response:**
```python
{
    "bmi": 26.4,
    "category": "overweight",
    "limitations": [
        "no_fat_distribution",
        "no_sex_specific_context"
    ],
    "next_step": "pro"
}
```

**Note:** This is optional for this PR. Can be done in separate backend PR.

---

## Scope

### ✅ IN SCOPE

- Product documentation (tier contracts)
- Soft paywall copy (RU/EN/ES)
- Legal disclaimers
- Copywriting guidelines
- Risk language guidelines

### ❌ OUT OF SCOPE

- UI implementation
- Frontend components
- Backend API changes (optional, can be separate PR)
- Billing integration
- Design assets
- A/B testing setup

---

## Definition of Done

- [ ] All product documentation created
- [ ] Soft paywall copy ready (RU/EN/ES)
- [ ] Legal disclaimers reviewed
- [ ] Copywriting guidelines documented
- [ ] Risk language guidelines documented
- [ ] No medical claims in any copy
- [ ] Wellness positioning clear
- [ ] Regional compliance verified (CIS/EU/US)

---

## Related PRs

**Depends on:**
- Backend P0 Remediation PR (must be merged first)

**Unblocks:**
- Frontend soft paywall implementation
- VIP tier product documentation
- Other FREE module soft paywalls

---

## Next Steps (After This PR)

1. Frontend soft paywall component implementation
2. Backend response structure update (if not in this PR)
3. A/B testing setup
4. VIP tier product documentation

---

**Last updated:** 2026-01-15
**Status:** Planned (waiting for backend remediation)
