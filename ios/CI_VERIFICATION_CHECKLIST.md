# iOS CI Verification Checklist

## После следующего CI run проверьте:

### 1. Xcode Pinning

В логах шага "Select Xcode" должна быть строка:
```text
Selected DEVELOPER_DIR: /Applications/Xcode_26.2.app/Contents/Developer
```
(или другой `Xcode_26*.app`, если `26.2` недоступен на runner)

### 2. Xcode Version

После выбора Xcode:
```bash
xcodebuild -version
```
Должен показать `Xcode 26.x`, не 16.x.

### 3. Available Destinations

После boot симулятора:
```bash
xcodebuild -showdestinations -project PulsePlate.xcodeproj -scheme PulsePlate
```

**Ожидаемый результат:**
- ✅ Должен показать список eligible iOS Simulator destinations
- ❌ НЕ должно быть "Ineligible destinations" или ошибок про отсутствующий iOS 26 runtime при выбранном Xcode 26

### 4. Test Execution

```bash
xcodebuild test -destination platform=iOS Simulator,id=<UDID> ...
```

**Ожидаемый результат:**
- ✅ Должен стартовать (не падать на destination resolution)
- ✅ Может падать на реальных тестах/сборке — это нормально (новый уровень ошибок)

## Что присылать для диагностики

Если CI всё ещё падает, пришлите:

1. **Строку с выбранным Xcode:**
   ```text
   Selected DEVELOPER_DIR: ...
   ```

2. **Первые 10 строк после `xcodebuild -showdestinations`:**
   ```text
   { platform:iOS Simulator, ... }
   ...
   ```

3. **Если упало — первые 5 строк ошибки:**
   ```text
   error: ...
   ```

## Текущее состояние (локально)

✅ **Info.plist configuration:**
- Все три файла в `membershipExceptions`: `Info.plist`, `Info-Debug.plist`, `Info-Release.plist`
- `INFOPLIST_FILE` правильно настроен: Debug → `Info-Debug.plist`, Release → `Info-Release.plist`
- Локально нет warning про Copy Bundle Resources

✅ **Xcode pinning:**
- CI шаг "Select Xcode" выбирает 26.2 → 26.1 → 26.0 → `Xcode.app` по приоритету
- После выбора CI явно валидирует, что `xcodebuild -version` возвращает Xcode 26.x
- `DEVELOPER_DIR` экспортируется через `GITHUB_ENV`

✅ **AGENTS.md:**
- Обновлена политика про "latest" (убрана двусмысленность)
- Добавлено правило про Xcode pinning
- Добавлено правило про Info.plist Target Membership
