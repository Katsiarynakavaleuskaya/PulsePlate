---
name: Liquid Glass API Migration
about: Track migration from visual approximation to official Apple API
title: 'Migrate liquidGlass to official API when available'
labels: 'enhancement, ios, tech-debt'
assignees: ''
---

## Context

The `liquidGlass` design token is currently implemented as a **visual approximation** using available system APIs (blur effects, materials, opacity). This is a temporary solution until Apple releases official APIs for glass/frosted materials.

**Current Implementation:**
- Location: `ios/PulsePlate/Extensions/ShapeStyle+Theme.swift`
- Uses: `.ultraThinMaterial` with blur radius adjustments
- Fallback: Solid fills on older iOS versions

## Migration Checklist

### 1. Monitor Apple Releases
- [ ] Watch WWDC sessions for new material APIs
- [ ] Check iOS SDK release notes for glass/frosted effects
- [ ] Review HIG updates for official design patterns

### 2. API Availability
- [ ] Official API announced (document WWDC session / release notes)
- [ ] API available in public SDK (minimum iOS version: `___`)
- [ ] API tested in Xcode beta

### 3. Migration Tasks
- [ ] Update `ShapeStyle+Theme.swift` to use official API
- [ ] Update documentation comments (remove "visual approximation" warnings)
- [ ] Add `@available` checks for backward compatibility
- [ ] Update fallback behavior for older iOS versions

### 4. Testing
- [ ] Visual comparison: old approximation vs. official API
- [ ] Test on multiple devices (iPhone, iPad)
- [ ] Test on minimum supported iOS version
- [ ] Verify accessibility (VoiceOver, Reduce Transparency)

### 5. Code Cleanup
- [ ] Remove legacy blur-based approximation code
- [ ] Update all call sites using `liquidGlass`
- [ ] Remove issue template comments from implementation
- [ ] Close this issue

## Example Migration

**Before (visual approximation):**
```swift
public static var liquidGlass: some ShapeStyle {
    if #available(iOS 17.0, *) {
        // Visual approximation using blur + material
        return .ultraThinMaterial.opacity(0.8)
    } else {
        // Fallback for older versions
        return Color.white.opacity(0.2)
    }
}
```

**After (official API):**
```swift
@available(iOS 18.0, *)  // Example: hypothetical iOS 18 API
public static var liquidGlass: some ShapeStyle {
    // Official Apple glass material
    return .glassMaterial
}

// Legacy support
public static var liquidGlassLegacy: some ShapeStyle {
    if #available(iOS 18.0, *) {
        return .glassMaterial
    } else {
        // Keep approximation for older versions
        return .ultraThinMaterial.opacity(0.8)
    }
}
```

## Documentation to Update

- [ ] `ShapeStyle+Theme.swift` inline comments
- [ ] Design system documentation (if exists)
- [ ] SwiftUI component usage examples
- [ ] HIG compliance notes

## Related Files

- `ios/PulsePlate/Extensions/ShapeStyle+Theme.swift`
- `ios/PulsePlate/Views/Components/GlassCard.swift`
- Any components using `.liquidGlass` styling

## Decision Log

**Why visual approximation?**
- No official API exists as of iOS 17
- Design team requested glass effect for premium features
- Approximation provides acceptable visual quality

**When to migrate?**
- Official API becomes available in stable iOS SDK
- Team decides minimum iOS version includes official API
- Visual quality improvement justifies migration effort

## Notes

- Keep this issue open until official API is released
- Update checklist as Apple announces new APIs
- Tag team members when migration becomes possible

---

**Created:** 2025-12-15
**Status:** Waiting for Apple API release
