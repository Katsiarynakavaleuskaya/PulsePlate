<!-- markdownlint-disable MD003 MD022 MD032 MD033 MD041 -->

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

## Out of scope
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

## Discussion Thread Pass
- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed

<!-- phase2-pre-closeout: final-security-pending -->

### Fixed in Commit Mapping
- Pending final clean scan and the single mapping/closeout commit.
- URL→SHA and disposition details belong only in the canonical artifact.

## Deferred / Follow-ups
- [ ] Ledger item(s): <link or None>
- [ ] GitHub issue(s): <link> (if any)

👉 Общие проверки: [docs/pr-checks.md](../../docs/pr-checks.md)

<!-- markdownlint-enable MD003 MD022 MD032 MD033 MD041 -->
