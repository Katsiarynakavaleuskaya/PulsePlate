---
name: iOS Feature
about: SwiftUI / StoreKit / HealthKit
labels: [iOS, feat]
---

# feat(iOS): <scope>

## Summary
- Что реализовано (экраны, менеджеры).
- Ссылка на задачу / issue.

## Scope
- Основные файлы (Views, Managers, StoreKit, HealthKit).
- Что осталось вне PR.

## Acceptance Criteria
- Сборка Xcode успешна, SwiftUI Previews.
- Dynamic Type, VoiceOver, доступность кнопок.
- StoreKitTest / HealthKit разрешения (если применимо).

## Tests
- [ ] Xcode build
- [ ] Unit (StoreKitTest / бизнес-логика)
- [ ] UI / интеграция (если есть)
- [ ] Ручные проверки на устройстве/симуляторе

```bash
open ios/PulsePlate.xcodeproj
# выбери схему и устройство, запусти
```

👉 Общие проверки: [docs/pr-checks.md](../../docs/pr-checks.md)
