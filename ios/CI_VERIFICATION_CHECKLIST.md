# iOS CI Verification Checklist

## После следующего CI run проверьте:

### 1. Xcode Pinning

В логах шага "Select Xcode" должна быть строка:
```
Selected DEVELOPER_DIR: /Applications/Xcode_16.4.app/Contents/Developer
```
(или 16.3, если 16.4 нет)

### 2. Xcode Version

После выбора Xcode:
```
xcodebuild -version
```
Должен показать `Xcode 16.4` (или 16.3), не 16.2.

### 3. Available Destinations

После boot симулятора:
```
xcodebuild -showdestinations -project PulsePlate.xcodeproj -scheme PulsePlate
```

**Ожидаемый результат:**
- ✅ Должен показать список eligible iOS Simulator destinations
- ❌ НЕ должно быть "iOS 18.2 is not installed" или "Ineligible destinations"

### 4. Test Execution

```
xcodebuild test -destination platform=iOS Simulator,id=<UDID> ...
```

**Ожидаемый результат:**
- ✅ Должен стартовать (не падать на destination resolution)
- ✅ Может падать на реальных тестах/сборке — это нормально (новый уровень ошибок)

## Что присылать для диагностики

Если CI всё ещё падает, пришлите:

1. **Строку с выбранным Xcode:**
   ```
   Selected DEVELOPER_DIR: ...
   ```

2. **Первые 10 строк после `xcodebuild -showdestinations`:**
   ```
   { platform:iOS Simulator, ... }
   ...
   ```

3. **Если упало — первые 5 строк ошибки:**
   ```
   error: ...
   ```

## Текущее состояние (локально)

✅ **Info.plist configuration:**
- Все три файла в `membershipExceptions`: `Info.plist`, `Info-Debug.plist`, `Info-Release.plist`
- `INFOPLIST_FILE` правильно настроен: Debug → `Info-Debug.plist`, Release → `Info-Release.plist`
- Локально нет warning про Copy Bundle Resources

✅ **Xcode pinning:**
- CI шаг "Select Xcode" выбирает 16.4 → 16.3 → 16.2 по приоритету
- `DEVELOPER_DIR` экспортируется через `GITHUB_ENV`

✅ **AGENTS.md:**
- Обновлена политика про "latest" (убрана двусмысленность)
- Добавлено правило про Xcode pinning
- Добавлено правило про Info.plist Target Membership
