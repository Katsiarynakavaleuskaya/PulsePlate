# iOS CI Verification Checklist

## После следующего CI run проверьте:

Для CAB-06 сохраните четыре отдельных результата текущего PR head:
`iOS unit tests (iphone, xcodebuild)`, `iOS unit tests (ipad, xcodebuild)`,
`iOS UI smoke (iphone, xcodebuild)` и `iOS UI smoke (ipad, xcodebuild)`.
Каждый должен завершиться `success`; `pending`, `skipped` и `failure` не доказывают
приёмку. Для PR без iOS/workflow изменений оба матричных job ожидаются `skipped`.

### 1. Xcode Pinning

В логах шага "Select Xcode" должна быть строка:
```text
Selected DEVELOPER_DIR: /Applications/Xcode_27.2.0.app/Contents/Developer
```
(или `Xcode_27.2.app` / `Xcode.app`, только если фактическая версия ровно 27.2)

### 2. Xcode Version

После выбора Xcode:
```bash
xcodebuild -version
```
Проверьте точную версию `Xcode 27.2` и запишите фактический `Build version`.
На проверенном Mac наблюдались сборка `27B52` и `Apple Swift 6.4.2`.
В том же отчёте подтвердите семейство Apple Swift 6.4, оба SDK `iphoneos`
и `iphonesimulator` версии 27.2 и значения `ImageOS` и `ImageVersion` runner.

### 3. Family-specific destinations

В каждом матричном row проверьте `family`, `ios_runtime_id`, `device_name`,
`udid` и UDID-only `destination` из selector output. Выбранный device type
должен иметь соответствующий `productFamily` в `simctl list devicetypes -j`;
отсутствующее семейство завершает row ошибкой. В каждой строке
ожидается `com.apple.CoreSimulator.SimRuntime.iOS-27-2`.

После boot симулятора:
```bash
xcodebuild -showdestinations -project PulsePlate.xcodeproj -scheme PulsePlate
```

**Ожидаемый результат:**
- ✅ Должен показать список eligible iOS Simulator destinations
- ❌ НЕ должно быть "Ineligible destinations" или отсутствующего iOS 27.2 runtime при выбранном Xcode 27.2

### 4. Test Execution

```bash
xcodebuild test-without-building -destination platform=iOS Simulator,id=<UDID> ...
```

**Ожидаемый результат:**
- ✅ Должен стартовать (не падать на destination resolution)
- ✅ Три собственных Swift targets должны собираться с `SWIFT_TREAT_WARNINGS_AS_ERRORS=YES` в Debug и Release
- ℹ️ Сообщение `appintentsmetadataprocessor` атрибутируется отдельно; Swift gate не доказывает отсутствие всех сообщений Xcode

### 5. Targeted device family

Для `PulsePlate`, `PulsePlateTests` и `PulsePlateUITests` в Debug и Release
проверьте effective `TARGETED_DEVICE_FAMILY = 1,2` через `xcodebuild -showBuildSettings`.
В собранном app bundle проверьте `UIDeviceFamily` с iPhone (1) и iPad (2).
Это не подтверждает Mac Catalyst или macOS admission.

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
- CI шаг "Select Xcode" выбирает точные alias 27.2.0 → 27.2 → `Xcode.app` по приоритету
- После выбора CI валидирует ровно Xcode 27.2, Swift 6.4 и iOS SDK 27.2; выбор симулятора требует iOS 27.2 и UDID-only destination
- CAB-06 разделяет iPhone и iPad в матрице; отсутствие каждого семейства блокирует его row и merge gate
- `DEVELOPER_DIR` экспортируется через `GITHUB_ENV`

✅ **AGENTS.md:**
- Обновлена политика про "latest" (убрана двусмысленность)
- Добавлено правило про Xcode pinning
- Добавлено правило про Info.plist Target Membership
