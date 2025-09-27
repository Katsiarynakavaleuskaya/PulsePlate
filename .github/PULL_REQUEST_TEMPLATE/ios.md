---
name: iOS Feature
about: SwiftUI / StoreKit / HealthKit changes
title: "feat(iOS): "
labels: [iOS, feat]
---

## Summary
- Что реализовано и для кого (ссылка на задачу).

## Scope
- Основные экраны/модули (Views, Managers).
- Out-of-scope / TODO.

## iOS Notes
- Dynamic Type / VoiceOver / доступность.
- StoreKit / HealthKit взаимодействия, разрешения.
- Инструменты (StoreKitTest, Mock data).

## Testing
- [ ] Xcode build / SwiftUI previews
- [ ] Unit (StoreKitTest / бизнес-логика)
- [ ] UI / интеграция (если есть)
- Ручные проверки (устройств/симуляторов).

```bash
# Быстрый старт
open ios/PulsePlate.xcodeproj
# выбери схему и устройство, запусти ✅
```

## Security & Privacy
- HealthKit — только чтение? пояснение в UI.
- StoreKit — без тестовых ключей в коде.
