# feat(iOS): <scope>

## Goal
SwiftUI/StoreKit/HealthKit. Что реализовано.

## Files
- Приложи ключевые файлы (Views, Managers).

## Acceptance Criteria
- Сборка Xcode OK, SwiftUI Previews
- Dynamic Type, VO-лейблы
- StoreKitTest сценарии / HealthKit разрешения

## Tests
- Unit (StoreKitTest)
- UI Tests (VO, доступность кнопок)

## Run locally
1) Открой `.xcworkspace`/`.xcodeproj`
2) Выбери схему и устройство
3) Запусти

## Security
- HealthKit — read-only (раскрытие в UI)
- StoreKit — без тестовых ключей в коде
