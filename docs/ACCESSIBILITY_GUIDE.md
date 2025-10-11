# 🚪 Accessibility Guide for PulsePlate

## Overview

PulsePlate implements a comprehensive "Accessibility Gatekeeper" system to ensure all UI components meet WCAG 2.1 AA standards and provide an inclusive user experience.

## 🛠️ Accessibility Tools

### 1. ESLint Accessibility Plugin

- **File**: `frontend/.eslintrc.accessibility.js`
- **Purpose**: Catches accessibility issues during development
- **Usage**: `npm run lint:accessibility`

### 2. Accessible Components

- **File**: `frontend/src/components/ui/AccessibleIcon.tsx`
- **Components**: `AccessibleIcon`, `SvgIcon`, `ImageIcon`
- **Feature**: Mandatory accessibility labels with development-time validation

### 3. Playwright Accessibility Tests

- **File**: `frontend/tests/accessibility.spec.ts`
- **Purpose**: Automated accessibility testing in CI/CD
- **Usage**: `npm run test:accessibility`

### 4. GitHub Actions Workflow

- **File**: `.github/workflows/accessibility-check.yml`
- **Purpose**: Automated accessibility checks on PR/CI
- **Features**: Linting, auditing, and gatekeeper validation

## 📋 Accessibility Standards

### Required Attributes

#### Images

```tsx
// ✅ Correct
<img src="logo.png" alt="PulsePlate logo" />

// ❌ Incorrect
<img src="logo.png" />
```

#### Icons

```tsx
// ✅ Correct
<AccessibleIcon icon={HeartIcon} label="Add to favorites" />

// ❌ Incorrect
<HeartIcon />
```

#### Interactive Elements

```tsx
// ✅ Correct
<button aria-label="Close dialog">×</button>
<a href="/profile" aria-label="Go to user profile">Profile</a>

// ❌ Incorrect
<button>×</button>
<a href="/profile">Profile</a>
```

#### Form Elements

```tsx
// ✅ Correct
<label htmlFor="email">Email Address</label>
<input id="email" type="email" />

// ✅ Alternative
<input type="email" aria-label="Email Address" />
```

### ARIA Landmarks

```tsx
// ✅ Correct structure
<header role="banner">
  <nav role="navigation">
    <main role="main">
      <aside role="complementary">
        <footer role="contentinfo">
```

## 🚀 Development Workflow

### 1. Pre-commit Checks

```bash
# Run accessibility linting
npm run lint:accessibility

# Run accessibility tests
npm run test:accessibility
```

### 2. Component Development

```tsx
import { AccessibleIcon } from '@/components/ui/AccessibleIcon';

// Always use accessible components
const MyComponent = () => (
  <div>
    <AccessibleIcon
      icon={UserIcon}
      label="User profile"
      size="md"
    />
    <button aria-label="Save changes">
      <AccessibleIcon icon={SaveIcon} label="Save" />
    </button>
  </div>
);
```

### 3. Testing

```bash
# Local accessibility testing
npm run test:accessibility

# CI accessibility testing
npm run test:accessibility:ci
```

## 🚪 Accessibility Gatekeeper

### PR Requirements

Every PR must pass the Accessibility Gatekeeper:

1. **ESLint Accessibility Checks** ✅
2. **Playwright Accessibility Tests** ✅
3. **ARIA Landmarks Validation** ✅
4. **Keyboard Navigation Tests** ✅
5. **Color Contrast Verification** ✅
6. **Screen Reader Compatibility** ✅

### Gatekeeper Status

- ✅ **PASSED**: PR can be merged
- ❌ **FAILED**: PR blocked until accessibility issues are resolved

## 📊 Accessibility Checklist

### Visual Design

- [ ] Color contrast ratio ≥ 4.5:1 for normal text
- [ ] Color contrast ratio ≥ 3:1 for large text
- [ ] Information not conveyed by color alone
- [ ] Text can be resized up to 200% without loss of functionality

### Keyboard Navigation

- [ ] All interactive elements are keyboard accessible
- [ ] Tab order is logical and intuitive
- [ ] Focus indicators are visible
- [ ] No keyboard traps

### Screen Reader Support

- [ ] All images have descriptive alt text
- [ ] All icons have accessible labels
- [ ] Form elements have proper labels
- [ ] ARIA landmarks are properly implemented
- [ ] Error messages are announced

### Content Structure

- [ ] Proper heading hierarchy (h1 → h2 → h3)
- [ ] Page has descriptive title
- [ ] Language is specified (html lang attribute)
- [ ] Content is organized with proper landmarks

## 🔧 Common Issues & Solutions

### Issue: Missing alt text

```tsx
// ❌ Problem
<img src="chart.png" />

// ✅ Solution
<img src="chart.png" alt="Sales chart showing 25% increase in Q3" />
```

### Issue: Icon without label

```tsx
// ❌ Problem
<button><HeartIcon /></button>

// ✅ Solution
<button aria-label="Add to favorites">
  <AccessibleIcon icon={HeartIcon} label="Add to favorites" />
</button>
```

### Issue: Form without labels

```tsx
// ❌ Problem
<input type="email" placeholder="Email" />

// ✅ Solution
<label htmlFor="email">Email Address</label>
<input id="email" type="email" />
```

## 📚 Resources

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [WebAIM Accessibility Resources](https://webaim.org/)
- [axe-core Testing Library](https://github.com/dequelabs/axe-core)

## 🎯 Goals

1. **100% WCAG 2.1 AA Compliance**
2. **Zero Accessibility Violations in Production**
3. **Inclusive Design for All Users**
4. **Automated Accessibility Testing**
5. **Developer Education & Best Practices**

---

**Remember**: Accessibility is not a feature—it's a fundamental requirement for inclusive software development.
