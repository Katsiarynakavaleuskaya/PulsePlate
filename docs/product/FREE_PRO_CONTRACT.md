# FREE / PRO / VIP Product Contract (Canonical)

**Status:** Canonical (product specification)
**Last updated:** 2026-01-15
**Scope:** All BMI and wellness calculation modules

---

## Related Docs

- `docs/product/WELLNESS_EXPLAINERS_TENSORTONIC_ADAPTATION_NOTE.md` — public-pattern
  adaptation note for future explainers and learning-cycle work; canonical for
  explainer payload naming, wellness-safe guardrails, and LLM/telemetry limits
- `docs/roadmap/BACKLOG_LEDGER.md` — canonical execution backlog for follow-up
- `docs/product/FREE_PRO_SOFT_PAYWALL.md` — current conversion language baseline

## 🎯 Product Philosophy

**Core principle:**
> FREE answers "Where am I now?"
> PRO answers "Why does this matter for me specifically?"
> VIP answers "What do I do about it every day?"

This creates a **trust-based funnel** rather than fear-based conversion, especially important for CIS/EU markets where users are cautious about paid health services.

---

## 🟢 FREE Tier — Screening & Education (Wellness)

### Purpose

- Fast self-check
- Educational function
- Low cognitive load
- Building trust through transparency

### What FREE Includes

- **BMI value** (number)
- **BMI category** (underweight / normal / overweight / obese)
- **Short explanation** (1 sentence, educational)
- **Basic Waist-to-Height Ratio (WHtR)** if waist is available

### Explicit Limitations (Must Be Communicated)

FREE **does NOT**:
- Account for sex-specific differences
- Include WHR or FFMI
- Include combined risk staging
- Assess individual health risk
- Provide medical evaluation
- Replace professional consultation

### Product Contract

**FREE is honest about its limitations.** This builds trust and sets proper expectations.

**Backend response structure:**
```json
{
  "bmi": 26.4,
  "category": "overweight",
  "whtr": 0.52,
  "explanation": "BMI in this range may indicate...",
  "limitations": [
    "no_sex_specific_context",
    "no_whr_or_ffmi",
    "no_combined_risk_staging"
  ],
  "next_step": "pro"
}
```

---

## 🔵 PRO Tier — Risk Awareness & Interpretation (Wellness)

### Purpose

- Health risk awareness
- Personalized interpretation
- Understanding "why this matters for me"

### What PRO Includes

- **All FREE features** +
- **Waist-to-Hip Ratio (WHR)** — sex-specific thresholds
- **Fat-Free Mass Index (FFMI)** — muscle mass consideration
- **Combined risk staging** — multi-factor assessment
- **Detailed explanations** — why risk is higher/lower
- **Actionable insights** — what factors contribute

### Product Contract

**PRO provides interpretation, not diagnosis.**

**Backend response structure:**
```json
{
  "bmi": 26.4,
  "category": "overweight",
  "whtr": 0.52,
  "whr": 0.88,
  "ffmi": 18.5,
  "risk_level": "moderate",
  "risk_factors": ["central_fat", "bmi_range"],
  "explanations": [
    "WHtR indicates moderate central fat distribution",
    "WHR is within normal range for your sex"
  ],
  "next_step": "vip"
}
```

### Shared Logic: BMI Pro Engine

**Important:** The BMI Pro calculation logic (WHtR, WHR, FFMI, risk interpretation) is **shared between PRO and VIP tiers**.

**Differences between tiers:**
- **PRO:** Interpretation and awareness
- **VIP:** Personalized actions and planning based on the same interpretation

**Rationale:**
- Avoids code duplication
- Ensures consistent interpretation across tiers
- VIP adds value through automation, not different calculations

---

## 🟣 VIP Tier — Personalization & Action (Wellness Lifestyle)

### Purpose

- Turn awareness into daily actions
- Personalized lifestyle automation
- Practical implementation

### What VIP Includes

**All PRO features** +
- **Personalized nutrition targets** (WHO-based, adjusted for goals)
- **Automated meal planning** (weekly menus)
- **Product recommendations** (from local stores)
- **Regional availability** (CIS / EU / US)
- **Budget optimization**
- **Dietary preferences** (vegan, keto, etc.)
- **Future:** Restaurant integration, advanced personalization

### Product Contract

**VIP translates awareness → lifestyle.**

VIP **does NOT**:
- Introduce new medical calculations
- Provide medical treatment
- Replace professional nutritionist consultation

**VIP provides:**
- Automation of healthy choices
- Convenience in meal planning
- Local product availability
- Budget-conscious options

---

## 📊 Tier Comparison Matrix

| Feature | FREE | PRO | VIP |
|---------|------|-----|-----|
| BMI calculation | ✅ | ✅ | ✅ |
| BMI category | ✅ | ✅ | ✅ |
| Basic explanation | ✅ | ✅ | ✅ |
| WHtR | ✅ | ✅ | ✅ |
| WHR (sex-specific) | ❌ | ✅ | ✅ |
| FFMI | ❌ | ✅ | ✅ |
| Risk staging | ❌ | ✅ | ✅ |
| Detailed explanations | ❌ | ✅ | ✅ |
| Nutrition targets | ❌ | ❌ | ✅ |
| Meal planning | ❌ | ❌ | ✅ |
| Product recommendations | ❌ | ❌ | ✅ |
| Regional availability | ❌ | ❌ | ✅ |

---

## 🔑 Key Product Principles

### 1. Honesty First

- FREE explicitly states limitations
- No fear-based marketing
- Educational approach builds trust

### 2. Value Progression

- Each tier adds clear, tangible value
- No artificial restrictions
- Natural upgrade path

### 3. Wellness, Not Medicine

- All tiers are wellness/education
- No medical claims
- Clear disclaimers

### 4. Regional Compatibility

- Safe for CIS / EU / US markets
- No medical regulation triggers
- Wellness-focused language

---

## 🧠 Soft Paywall Strategy

### After FREE Result

**Message:**
```text
⚠️ BMI — это только первый ориентир.

Он не учитывает:
• распределение жира
• различия между мужчинами и женщинами
• мышечную массу

→ Перейти к расширенной оценке
```

**CTA:** `[ Расширенная оценка ]` → PRO

### After PRO Result (Future)

**Message:**
```text
Вы понимаете свой риск.
Хотите превратить это в персональный план?
```

**CTA:** `[ Персональный план питания ]` → VIP

---

## 📋 Implementation Notes

### Backend

- FREE endpoints: `/api/v1/bmi/*`
- PRO endpoints: `/api/v1/pro/*`
- VIP endpoints: `/api/v1/vip/*`

### Frontend

- Soft paywall component (reusable)
- Tier-specific UI sections
- Educational messaging

### Legal

- Wellness disclaimers on all tiers
- No medical claims
- Clear limitations communication

---

## 🔄 Future Extensions

This contract applies to:
- BMI calculations (current)
- Nutrition analysis (future)
- Activity recommendations (future)
- Other wellness modules (future)

**Universal pattern:**
- FREE = basic screening
- PRO = interpretation
- VIP = automation

---

## 🟣 VIP Tier — Future Scope (Not in Current Remediation PR)

### What VIP Will Include (Future)

**All PRO features** +
- Personalized nutrition targets (goal-driven)
- Automated meal planning (weekly menus)
- Product recommendations (from local stores)
- Regional availability (CIS / EU / US)
- Budget optimization
- Dietary preferences (vegan, keto, etc.)
- Future: Restaurant integration

### Key Distinction

**PRO tier:**
- Automation of **interpretation** (calculations, risk assessment)
- "What does this mean for me?"

**VIP tier:**
- Automation of **actions** (menus, products, planning)
- "What do I do about it every day?"

### Implementation Timeline

1. **Current (P0):** Backend remediation — restore invariants
2. **Next (P1):** Product contract + soft paywall (docs only)
3. **Future:** VIP tier audit and implementation (separate PR)

**See:** `docs/audit/PR_PRODUCT_SOFT_PAYWALL_SKELETON.md` for next steps.

---

**See also:**
- `docs/product/FREE_PRO_SOFT_PAYWALL.md` — Soft paywall copy
- `docs/legal/WELLNESS_DISCLAIMER.md` — Legal disclaimers
- `docs/legal/COPY_RULES_WELLNESS.md` — Copywriting guidelines
