# iOS: Migrate GlassCard to official Liquid Glass API when stable

## Goal

Replace current GlassCard "visual approximation" (Color.liquidGlass) with Apple's official Liquid Glass API once it is publicly documented and stable.

## Current state

GlassCard uses:
- **iOS 17–25**: `.thinMaterial`
- **iOS 26+**: `Color.liquidGlass` (visual approximation, not system API)

**Implementation:** `ios/PulsePlate/Views/Components/GlassCard.swift`

## Why

- Official API should provide real refraction/lensing and system-consistent rendering
- Reduce maintenance cost and align with platform capabilities
- Eliminate confusion about whether we're using actual system features

## Acceptance criteria

- [ ] Use official API (e.g., `glassEffect(...)` or official materials) behind availability checks
- [ ] Keep Reduce Transparency accessibility behavior correct
- [ ] Update documentation to reference official API docs
- [ ] Snapshot tests updated/added for glass appearance across states
- [ ] Verify visual consistency with system design language

## Implementation notes

Current implementation pattern:
```swift
@ViewBuilder
private var background: some View {
    let shape = RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
    if reduceTransparency {
        shape.fill(.background)
    } else {
        if #available(iOS 26.0, *) {
            shape.fill(Color.liquidGlass)  // Visual approximation
        } else {
            shape.fill(.thinMaterial)
        }
    }
}
```

Future pattern (example):
```swift
if #available(iOS 27.0, *) {  // Or whenever official API ships
    shape.glassEffect(.standard)  // Hypothetical official API
} else {
    // Fallback to current implementation
}
```

## Tracking

- [ ] Monitor WWDC sessions for Liquid Glass announcements
- [ ] Track Apple developer forums for API availability
- [ ] Review beta release notes for new material APIs
- [ ] Update when API signature is confirmed and documented

## Related

- Documentation: `docs/architecture/weekly-plan-reference.md`
- Memory: "Anticipatory UI: Liquid Glass Visual Approximation Guidelines"
- PR: #351 (feat/weekly-plan-reader)

---

**Labels:** enhancement, ios, ui-components, future-api
**Priority:** Low (blocked on Apple)
**Assignee:** TBD
