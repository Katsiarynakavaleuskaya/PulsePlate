# Sprint C.1: i18n BMI Keys — Plan

## Summary

Add BMI visualization i18n keys to iOS `Localizable.strings` (RU/EN/ES) for rendering BMI scale ranges.

**Type:** i18n (iOS only, minimal scope)
**Branch:** `feat/pr-c1-i18n-bmi-keys`

---

## 🎯 Goal

Enable iOS/Web to render BMI visualization ranges with localized labels.

**Keys needed:**
- `bmi.underweight`
- `bmi.normal`
- `bmi.overweight`
- `bmi.obesity`

---

## 📋 Files to Change

### iOS Localization Files (3 files)

1. `ios/PulsePlate/en.lproj/Localizable.strings`
2. `ios/PulsePlate/ru.lproj/Localizable.strings`
3. `ios/PulsePlate/es.lproj/Localizable.strings`

---

## 🔑 Keys to Add

### English (`en.lproj/Localizable.strings`)

```strings
/* BMI Visualization Ranges */
"bmi.underweight" = "Underweight";
"bmi.normal" = "Normal";
"bmi.overweight" = "Overweight";
"bmi.obesity" = "Obesity";
```

### Russian (`ru.lproj/Localizable.strings`)

```strings
/* BMI Visualization Ranges */
"bmi.underweight" = "Недостаточная масса";
"bmi.normal" = "Норма";
"bmi.overweight" = "Избыточная масса";
"bmi.obesity" = "Ожирение";
```

### Spanish (`es.lproj/Localizable.strings`)

```strings
/* BMI Visualization Ranges */
"bmi.underweight" = "Bajo peso";
"bmi.normal" = "Normal";
"bmi.overweight" = "Sobrepeso";
"bmi.obesity" = "Obesidad";
```

---

## 📝 Commit

```bash
git add ios/PulsePlate/*/Localizable.strings
git commit -m "feat(i18n): add BMI visualization range keys (RU/EN/ES)"
```

---

## ✅ Verification

After adding keys, verify:

1. **iOS builds** (Xcode project compiles)
2. **Keys accessible** (can be looked up via `NSLocalizedString` or SwiftUI `Text`)

---

## 🔗 Related

- Follow-up to PR-492 (BMI visualization contract documentation)
- Enables Sprint C.2 (iOS BMI bootstrap)

---

## 📄 PR Description

```markdown
## Summary

Add BMI visualization i18n keys to iOS localization files.

**Type:** i18n (iOS only)
**Minimal scope:** Only 4 keys, no backend refactoring.

---

## What Changed

### Added

- BMI visualization keys to iOS `Localizable.strings`:
  - `bmi.underweight` (RU/EN/ES)
  - `bmi.normal` (RU/EN/ES)
  - `bmi.overweight` (RU/EN/ES)
  - `bmi.obesity` (RU/EN/ES)

### Changed

- `ios/PulsePlate/en.lproj/Localizable.strings`
- `ios/PulsePlate/ru.lproj/Localizable.strings`
- `ios/PulsePlate/es.lproj/Localizable.strings`

---

## Why This Change

1. **iOS needs localized labels** for BMI visualization ranges
2. **Keys match API contract** (from PR-492 documentation)
3. **Minimal scope** (only keys, no refactoring)

---

## Keys Added

| Key | EN | RU | ES |
|-----|----|----|----|
| `bmi.underweight` | Underweight | Недостаточная масса | Bajo peso |
| `bmi.normal` | Normal | Норма | Normal |
| `bmi.overweight` | Overweight | Избыточная масса | Sobrepeso |
| `bmi.obesity` | Obesity | Ожирение | Obesidad |

---

## Related

- Follow-up to PR-492 (BMI visualization contract)
- Enables Sprint C.2 (iOS BMI bootstrap)
```

---

## 🚀 Quick Start

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

## 📌 Notes

- **No backend changes** in this PR (i18n registry refactoring can be separate PR)
- **Keys match API contract** from PR-492 (`docs/bmi/visualization.md`)
- **Minimal scope** — only 4 keys, 3 files
