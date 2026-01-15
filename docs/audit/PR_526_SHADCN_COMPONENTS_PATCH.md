# PR-526: Introduce shadcn Input/Button/Label + Token Mapping

**Priority:** P1 (After PR-525)
**Scope:** Modern component system setup
**Estimated time:** 2-3 days

---

## 🎯 Goal

Add shadcn/ui components with proper RHF integration (Controller pattern) and design token mapping.

---

## 📋 Step-by-Step Implementation

### Step 1: Install shadcn/ui CLI

```bash
cd frontend
npx shadcn@latest init
```

**Questions:**
- **Style:** `New York` (or `Default`)
- **Base color:** `blue` (NOT "Navy" — shadcn doesn't support custom names)
- **CSS variables:** `Yes`

**Note:** We'll map "Navy" via CSS variables in `tokens.css` (see Step 3).

---

### Step 2: Add Core Components

```bash
npx shadcn@latest add input
npx shadcn@latest add button
npx shadcn@latest add label
```

This creates:
- `frontend/src/components/ui/input.tsx`
- `frontend/src/components/ui/button.tsx`
- `frontend/src/components/ui/label.tsx`

---

### Step 3: Map Design Tokens to shadcn Variables

**File:** `frontend/src/styles/tokens.css` (add to `:root`)

```css
:root {
  /* ... existing tokens ... */

  /* shadcn/ui variables mapped to PulsePlate design tokens */
  --primary: var(--color-blue-600);
  --primary-foreground: #fff;
  --secondary: var(--color-navy-100);
  --secondary-foreground: var(--color-navy-900);
  --background: var(--color-bg);
  --foreground: var(--color-text);
  --muted: var(--color-surface-muted);
  --muted-foreground: var(--color-text-muted);
  --accent: var(--pp-accent); /* #20C997 */
  --accent-foreground: #fff;
  --destructive: var(--color-heart-500);
  --destructive-foreground: #fff;
  --border: var(--color-border);
  --input: var(--color-border);
  --ring: var(--color-focus);
  --radius: 0.5rem;
}
```

---

### Step 4: Create RHF-Friendly NumberInput

**File:** `frontend/src/components/ui/number-input.tsx`

```typescript
import * as React from "react"
import { Input } from "./input"
import { cn } from "@/lib/utils"

export interface NumberInputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type" | "onChange" | "value"> {
  value?: number | string
  onValueChange?: (value: number | "") => void
  locale?: "ru" | "en"
}

/**
 * NumberInput component with locale-aware parsing.
 *
 * - Parses RU locale (comma → dot): "75,1" → 75.1
 * - Only emits valid numbers or empty string to onValueChange
 * - Keeps display value as string for smooth typing
 *
 * Use with RHF Controller:
 * ```tsx
 * <Controller
 *   name="weight_kg"
 *   control={control}
 *   render={({ field }) => (
 *     <NumberInput
 *       value={field.value ?? ""}
 *       onValueChange={field.onChange}
 *       onBlur={field.onBlur}
 *       locale="ru"
 *     />
 *   )}
 * />
 * ```
 */
const NumberInput = React.forwardRef<HTMLInputElement, NumberInputProps>(
  ({ className, value, onValueChange, locale = "en", onBlur, ...props }, ref) => {
    // Internal state for display value (string)
    const [displayValue, setDisplayValue] = React.useState<string>(() => {
      if (typeof value === "number") {
        return locale === "ru" ? value.toString().replace(/\./g, ",") : value.toString()
      }
      return value ?? ""
    })

    // Sync display value when external value changes
    React.useEffect(() => {
      if (typeof value === "number") {
        const formatted = locale === "ru"
          ? value.toString().replace(/\./g, ",")
          : value.toString()
        setDisplayValue(formatted)
      } else if (value === "" || value === undefined || value === null) {
        setDisplayValue("")
      }
    }, [value, locale])

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const raw = e.target.value.trim()

      // Update display immediately for smooth typing
      setDisplayValue(raw)

      if (raw === "") {
        onValueChange?.("")
        return
      }

      // Normalize locale: "75,1" → "75.1"
      const normalized = locale === "ru"
        ? raw.replace(/,/g, ".")
        : raw.replace(/,/g, "")

      const num = parseFloat(normalized)

      // Only emit valid numbers (or empty string)
      if (Number.isFinite(num)) {
        onValueChange?.(num)
      }
      // Invalid input stays in display but doesn't emit to form
    }

    const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
      // On blur, try to normalize display value
      const raw = displayValue.trim()
      if (raw === "") {
        setDisplayValue("")
        onBlur?.(e)
        return
      }

      const normalized = locale === "ru"
        ? raw.replace(/,/g, ".")
        : raw.replace(/,/g, "")

      const num = parseFloat(normalized)

      if (Number.isFinite(num)) {
        // Format display value on blur
        const formatted = locale === "ru"
          ? num.toString().replace(/\./g, ",")
          : num.toString()
        setDisplayValue(formatted)
        onValueChange?.(num)
      } else {
        // Invalid input: clear display
        setDisplayValue("")
        onValueChange?.("")
      }

      onBlur?.(e)
    }

    return (
      <Input
        type="text"
        inputMode="decimal"
        value={displayValue}
        onChange={handleChange}
        onBlur={handleBlur}
        className={cn(className)}
        ref={ref}
        {...props}
      />
    )
  }
)
NumberInput.displayName = "NumberInput"

export { NumberInput }
```

---

### Step 5: Update SetupForm to Use Controller + NumberInput

**File:** `frontend/src/pages/NutritionSetup/SetupForm.tsx`

```typescript
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { NumberInput } from '../../components/ui/number-input';
import { Button } from '../../components/ui/button';
import { Label } from '../../components/ui/label';
// ... other imports

export default function SetupForm({ onSubmit }: SetupFormProps) {
  const { control, handleSubmit, watch, setValue, formState: { errors } } = useForm<SetupFormValues>({
    resolver: zodResolver(setupSchema),
    defaultValues: saved ?? {
      // ... defaults
    },
  });

  // ... existing code ...

  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Age */}
        <div className="space-y-2">
          <Label htmlFor="age">{t('nutrition.age')}</Label>
          <Controller
            name="age"
            control={control}
            render={({ field }) => (
              <NumberInput
                id="age"
                value={field.value ?? ""}
                onValueChange={field.onChange}
                onBlur={field.onBlur}
                locale={getClientLocale() === 'ru' ? 'ru' : 'en'}
                placeholder="30"
              />
            )}
          />
          {errors.age && (
            <p className="text-sm text-destructive">{errors.age.message}</p>
          )}
        </div>

        {/* Height (cm) */}
        <div className="space-y-2">
          <Label htmlFor="height_cm">{t('nutrition.height_cm')}</Label>
          <Controller
            name="height_cm"
            control={control}
            render={({ field }) => (
              <NumberInput
                id="height_cm"
                value={field.value ?? ""}
                onValueChange={field.onChange}
                onBlur={field.onBlur}
                locale={getClientLocale() === 'ru' ? 'ru' : 'en'}
                placeholder="170"
              />
            )}
          />
          {errors.height_cm && (
            <p className="text-sm text-destructive">{errors.height_cm.message}</p>
          )}
        </div>

        {/* Weight (kg) */}
        <div className="space-y-2">
          <Label htmlFor="weight_kg">{t('nutrition.weight_kg')}</Label>
          <Controller
            name="weight_kg"
            control={control}
            render={({ field }) => (
              <NumberInput
                id="weight_kg"
                value={field.value ?? ""}
                onValueChange={field.onChange}
                onBlur={field.onBlur}
                locale={getClientLocale() === 'ru' ? 'ru' : 'en'}
                placeholder="65"
              />
            )}
          />
          {errors.weight_kg && (
            <p className="text-sm text-destructive">{errors.weight_kg.message}</p>
          )}
        </div>
      </div>

      {/* Submit button */}
      <Button type="submit" className="w-full" size="lg">
        {t('nutritionSetup.calculateButton')}
      </Button>
    </form>
  );
}
```

**Helper function:**
```typescript
// Add to utils or inline
const getClientLocale = (): 'ru' | 'en' | 'es' => {
  // Use i18n or browser locale
  return i18n.language as 'ru' | 'en' | 'es';
};
```

---

## ✅ Verification

1. **NumberInput with Controller:**
   - Enter `75,1` → should parse to `75.1` in form state
   - Enter invalid input → display stays, but form state doesn't update
   - On blur → invalid input clears

2. **Design tokens:**
   - Components use Navy/Blue colors from tokens
   - Consistent spacing and typography

3. **Accessibility:**
   - Labels properly associated with inputs
   - Keyboard navigation works
   - Screen reader announces correctly

---

## 📝 Commit Message

```
feat(ui): introduce shadcn input/button/label + token mapping

- Add shadcn/ui Input, Button, Label components
- Create RHF-friendly NumberInput with Controller pattern
- Map PulsePlate design tokens to shadcn CSS variables
- Update SetupForm to use new components

P1 enhancement for consistent UI components.
Depends on PR-525 (BMI form fixes).
```

---

**Last updated:** 2026-01-15
