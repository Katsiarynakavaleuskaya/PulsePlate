# iOS CI Verification Checklist

## После следующего CI run проверьте:

### 1. Xcode Pinning

В логах шага "Select Xcode" должна быть строка:
```text
Selected DEVELOPER_DIR: /Applications/Xcode_27.0.0.app/Contents/Developer
```
(или `Xcode_27.0.app` / `Xcode.app`, только если фактическая версия ровно 27.0)

### 2. Xcode Version

После выбора Xcode:
```bash
xcodebuild -version
```
Должен показать ровно `Xcode 27.0`; запишите фактический `Build version` (локальный baseline: `27A266a`). В том же evidence проверьте Swift 6.4, SDK `iphoneos`/`iphonesimulator` 27.0 и `ImageOS`/`ImageVersion` runner.

### 3. Available Destinations

После boot симулятора:
```bash
xcodebuild -showdestinations -project PulsePlate.xcodeproj -scheme PulsePlate
```

**Ожидаемый результат:**
- ✅ Должен показать список eligible iOS Simulator destinations
- ❌ НЕ должно быть "Ineligible destinations" или отсутствующего iOS 27.0 runtime при выбранном Xcode 27.0

### 4. Test Execution

```bash
xcodebuild test -destination platform=iOS Simulator,id=<UDID> ...
```

**Ожидаемый результат:**
- ✅ Должен стартовать (не падать на destination resolution)
- ✅ Три собственных Swift targets должны собираться с `SWIFT_TREAT_WARNINGS_AS_ERRORS=YES` в Debug и Release
- ℹ️ Сообщение `appintentsmetadataprocessor` атрибутируется отдельно; Swift gate не доказывает отсутствие всех сообщений Xcode

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
- CI шаг "Select Xcode" выбирает точные alias 27.0.0 → 27.0 → `Xcode.app` по приоритету
- После выбора CI валидирует ровно Xcode 27.0, Swift 6.4 и iOS SDK 27.0; выбор симулятора требует iOS 27.0 и UDID-only destination
- `DEVELOPER_DIR` экспортируется через `GITHUB_ENV`

✅ **AGENTS.md:**
- Обновлена политика про "latest" (убрана двусмысленность)
- Добавлено правило про Xcode pinning
- Добавлено правило про Info.plist Target Membership
