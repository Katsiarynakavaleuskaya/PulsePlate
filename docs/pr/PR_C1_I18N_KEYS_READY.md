# Sprint C.1: i18n BMI Keys — Ready to Add

## Keys Used in API

From `core/bmi/engine.py` → `get_bmi_visual_ranges()`:

```python
return [
    (scale_min, underweight_max, "bmi.underweight"),
    (underweight_max, normal_max, "bmi.normal"),
    (normal_max, overweight_max, "bmi.overweight"),
    (overweight_max, scale_max, "bmi.obesity"),
]
```

**Keys needed:** `bmi.underweight`, `bmi.normal`, `bmi.overweight`, `bmi.obesity`

---

## Ready-to-Use Strings

### English (`ios/PulsePlate/en.lproj/Localizable.strings`)

Add after line 38 (after shopping_list keys):

```strings
/* BMI Visualization Ranges */
"bmi.underweight" = "Underweight";
"bmi.normal" = "Normal";
"bmi.overweight" = "Overweight";
"bmi.obesity" = "Obesity";
```

### Russian (`ios/PulsePlate/ru.lproj/Localizable.strings`)

Add after line 52 (after shopping_list keys):

```strings
/* BMI Visualization Ranges */
"bmi.underweight" = "Недостаточная масса";
"bmi.normal" = "Норма";
"bmi.overweight" = "Избыточная масса";
"bmi.obesity" = "Ожирение";
```

### Spanish (`ios/PulsePlate/es.lproj/Localizable.strings`)

Add after line 52 (after shopping_list keys):

```strings
/* BMI Visualization Ranges */
"bmi.underweight" = "Bajo peso";
"bmi.normal" = "Normal";
"bmi.overweight" = "Sobrepeso";
"bmi.obesity" = "Obesidad";
```

---

## Translation Notes

### Russian

- **"Недостаточная масса"** — стандартный медицинский термин (используется в `core/i18n.py:13`)
- **"Норма"** — коротко и понятно (используется в `core/i18n.py:14`)
- **"Избыточная масса"** — стандартный термин (используется в `core/i18n.py:15`)
- **"Ожирение"** — общий термин (obesity_1/2/3 агрегируются в один ключ)

### Spanish

- **"Bajo peso"** — стандартный медицинский термин
- **"Normal"** — универсально
- **"Sobrepeso"** — стандартный термин
- **"Obesidad"** — общий термин

---

## Quick Start

```bash
# 1. Create branch
git checkout main
git pull --ff-only
git checkout -b feat/pr-c1-i18n-bmi-keys

# 2. Add keys to iOS Localizable.strings (see above)

# 3. Commit
git add ios/PulsePlate/*/Localizable.strings
git commit -m "feat(i18n): add BMI visualization range keys (RU/EN/ES)"

# 4. Push
git push -u origin feat/pr-c1-i18n-bmi-keys
```

---

## Verification

After adding keys:

1. **Xcode builds** (project compiles)
2. **Keys accessible** via `NSLocalizedString("bmi.normal", comment: "")` or SwiftUI `Text("bmi.normal")`

---

## Related

- Follow-up to PR-492 (BMI visualization contract)
- Enables Sprint C.2 (iOS BMI bootstrap)

