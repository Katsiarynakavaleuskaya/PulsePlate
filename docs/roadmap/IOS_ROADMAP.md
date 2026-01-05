# iOS Development Roadmap

> **Статус**: Frontend готов к синхронизации | **Владелец**: iOS Team | **Каденция**: По мере необходимости

## 📱 iOS Synchronization Status

### ✅ Frontend Ready (PR #2.7 Completed)
- [x] **iOS-compatible localization keys** added to all locales (EN/RU/ES)
- [x] **Chart, week, health, units sections** prepared for iOS sync
- [x] **Language, profile, mascot, settings keys** aligned with iOS format
- [x] **Accessibility labels** ready for iOS integration

### 🔄 iOS Development Tasks (When iOS Development Resumes)
- [ ] **Update iOS Localizable.strings** to match frontend structure
- [ ] **Implement SwiftUI components** using new localization keys
- [ ] **Synchronize navigation flow** between iOS and frontend
- [ ] **Align micro-animations** and iconography
- [ ] **Test cross-platform consistency** (RU/EN/ES locales)
- [ ] **HealthKit integration** using prepared health.* keys
- [ ] **Profile and settings screens** using profile.* and settings.* keys
- [ ] **Mascot messages** using mascot.* keys for consistency

## 📋 iOS Development Roadmap (When Ready)

### Phase 1: Localization Update
- [ ] **Update iOS Localizable.strings** with new key structure
- [ ] **Migrate existing keys** to new hierarchical structure
- [ ] **Validate all translations** match frontend versions

### Phase 2: Core Screens Implementation
- [ ] **Implement SwiftUI screens** using prepared localization keys
- [ ] **Home screen** with mascot integration
- [ ] **Settings screen** with language selection
- [ ] **Profile screen** with legal sections

### Phase 3: Health Integration
- [ ] **HealthKit integration** with health.* keys
- [ ] **Permission handling** using health.permissionMessage
- [ ] **Health data display** with proper localization

### Phase 4: User Interface
- [ ] **Profile and settings screens** with profile.* and settings.* keys
- [ ] **Navigation consistency** between iOS and frontend
- [ ] **Accessibility implementation** using accessibility.* keys

### Phase 5: Data Visualization
- [ ] **Chart and progress screens** with chart.* and week.* keys
- [ ] **Weekly progress display** with proper localization
- [ ] **Data visualization consistency**

### Phase 6: User Experience
- [ ] **Mascot integration** with mascot.* keys
- [ ] **Micro-animations** alignment
- [ ] **Iconography consistency**

### Phase 7: Quality Assurance
- [ ] **Cross-platform testing** and consistency validation
- [ ] **Performance testing** with longer Russian strings
- [ ] **Accessibility testing** across all screens
- [ ] **Localization testing** for all supported languages

## 🎯 Key Localization Sections Ready

### Chart & Data Visualization
```swift
// Ready keys: chart.day, chart.kcal, week.*
```

### Health & Permissions
```swift
// Ready keys: health.permissionMessage, health.request, health.alertTitle
```

### Units & Abbreviations
```swift
// Ready keys: units.kg, units.kcal, units.gram, abbreviations.*
```

### Language & Profile
```swift
// Ready keys: language.*, profile.*, settings.*
```

### Mascot & Accessibility
```swift
// Ready keys: mascot.*, accessibility.*
```

## ⚠️ Important Notes

### String Length Considerations
- **Russian strings** can be up to 4x longer than English
- **UI components** must handle longer strings without layout issues
- **Test thoroughly** with Russian locale for layout stability

### Cross-Platform Consistency
- **Navigation flow** should match frontend patterns
- **Terminology** must be consistent across platforms
- **User experience** should feel unified

## 🔗 Related Documents
- [GLOBAL_ROADMAP_2025.md](./GLOBAL_ROADMAP_2025.md) - Main project roadmap
- [frontend/src/locales/](./frontend/src/locales/) - Frontend localization files
- [ios/PulsePlate/*.lproj/](./ios/PulsePlate/) - iOS localization files
