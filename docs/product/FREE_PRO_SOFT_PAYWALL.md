# FREE → PRO Soft Paywall (Canonical Copy)

**Status:** Canonical (product copy)
**Last updated:** 2026-01-15
**Purpose:** Educational conversion, not fear-based marketing

---

## 🎯 Philosophy

**Soft paywall is education, not sales.**

- ❌ Does not scare
- ❌ Does not blame
- ✅ Educates
- ✅ Logically continues the user journey

---

## 📝 Primary Soft Paywall (After FREE BMI Result)

### RU Version

```
⚠️ BMI — это только первый ориентир.

Он не учитывает:
• распределение жира
• различия между мужчинами и женщинами
• мышечную массу

Хотите лучше понять свой уровень риска?
```

**CTA Button:**
```
[ Узнать расширенную оценку ]
```

**Alternative CTA (softer):**
```
[ Узнать больше о своём здоровье ]
```

---

### EN Version

```
⚠️ BMI is only a starting point.

It does not account for:
• fat distribution
• sex-specific differences
• muscle mass

Want a deeper understanding of your health risk?
```

**CTA Button:**
```
[ Get Extended Assessment ]
```

**Alternative CTA (softer):**
```
[ Learn More About Your Health ]
```

---

### ES Version (Future)

```
⚠️ El IMC es solo un punto de partida.

No tiene en cuenta:
• la distribución de grasa
• las diferencias entre hombres y mujeres
• la masa muscular

¿Quieres entender mejor tu nivel de riesgo?
```

**CTA Button:**
```
[ Obtener Evaluación Extendida ]
```

---

## 🔄 Universal Template (For All FREE Modules)

### RU

```
⚠️ Этот результат — предварительный.

Он не учитывает индивидуальные факторы,
которые существенно влияют на оценку.

→ Перейти к расширенной оценке
```

### EN

```
⚠️ This result is preliminary.

It does not include individual risk factors
that significantly affect the assessment.

→ Explore Extended Insights
```

---

## 🧠 PRO → VIP Upsell (Future)

### After PRO Result

**RU:**
```
Вы понимаете свой уровень риска.
Хотите превратить это в персональный план питания?
```

**CTA:**
```
[ Персональный план питания ]
```

**EN:**
```
You understand your risk level.
Want to turn this into a personalized nutrition plan?
```

**CTA:**
```
[ Personalized Nutrition Plan ]
```

---

## 📋 Component Specification

### Soft Paywall Component Props

```typescript
interface SoftPaywallProps {
  tier: "free" | "pro";
  limitations: string[];
  ctaText: string;
  ctaAction: () => void;
  language: "ru" | "en" | "es";
}
```

### Backend Response Hook

**FREE response includes:**
```json
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

**Frontend renders soft paywall based on `limitations` and `next_step`.**

---

## 🎨 Visual Guidelines

### Tone

- **Educational** (not salesy)
- **Honest** (not manipulative)
- **Caring** (not pushy)

### Design

- Warning icon (⚠️) — informational, not alarming
- Bullet points — clear, scannable
- CTA button — primary color, clear action

### Placement

- **After** FREE result
- **Before** any PRO features
- **Not** blocking FREE result visibility

---

## 📊 A/B Testing Ideas (Future)

### Variant A (Current)

Educational, limitation-focused

### Variant B (Alternative)

Benefit-focused:
```
Хотите узнать, как распределение жира влияет на ваше здоровье?
```

### Variant C (Question-based)

```
Знаете ли вы, что риск при одинаковом BMI разный для мужчин и женщин?
```

---

## ⚖️ Legal Compliance

All soft paywall copy must:

- ✅ Not make medical claims
- ✅ Not promise treatment
- ✅ Not create fear
- ✅ Be educational
- ✅ Be truthful

**See:** `docs/legal/COPY_RULES_WELLNESS.md`

---

## 🔄 Scalability

This soft paywall pattern applies to:

- BMI calculations (current)
- Nutrition analysis (future)
- Activity recommendations (future)
- Other wellness modules (future)

**Universal structure:**
1. Acknowledge limitation
2. Explain what's missing
3. Offer next step
4. Clear CTA

---

**See also:**
- `docs/product/FREE_PRO_CONTRACT.md` — Full tier contract
- `docs/legal/WELLNESS_DISCLAIMER.md` — Legal disclaimers
