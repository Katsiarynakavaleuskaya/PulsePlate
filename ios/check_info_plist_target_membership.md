# Проверка Target Membership для Info*.plist файлов

## Проблема

Xcode может показывать предупреждение "Copy Bundle Resources contains Info-Debug.plist", даже если файлы в `membershipExceptions`. Это происходит, если Target Membership установлен через Xcode UI.

## Решение (через Xcode UI)

### Шаг 1: Проверка Target Membership

Для каждого файла `Info*.plist`:

1. Открой `PulsePlate.xcodeproj` в Xcode
2. В Project Navigator выберите файл (например, `PulsePlate/Info-Debug.plist`)
3. В правой панели откройте **File Inspector** (первая иконка)
4. Найдите секцию **Target Membership**
5. **Убедитесь, что НИ ОДИН target не отмечен** (галочки должны быть сняты)

Повторите для:
- `Info.plist`
- `Info-Debug.plist`
- `Info-Release.plist`

### Шаг 2: Проверка Build Phases

1. Выберите проект в Project Navigator (синяя иконка)
2. Выберите target **PulsePlate**
3. Перейдите на вкладку **Build Phases**
4. Раскройте **Copy Bundle Resources**
5. **Убедитесь, что нет `Info*.plist` файлов** в списке
6. Если есть — удалите их (кнопка `-`)

### Шаг 3: Проверка после исправления

После снятия Target Membership:

1. **Clean Build Folder**: `Product → Clean Build Folder` (⇧⌘K)
2. **Build**: `Product → Build` (⌘B)
3. Проверьте, что предупреждение исчезло

## Автоматическая проверка (после сборки)

После сборки можно проверить, попал ли файл в bundle:

```bash
# Получить UDID симулятора (используется в -destination "platform=iOS Simulator,id=<UDID>")
xcrun simctl list devices available

# Скопируйте UDID нужного устройства (например iPhone 16e) и подставьте в команду ниже.
cd ios
xcodebuild build \
  -project PulsePlate.xcodeproj \
  -scheme PulsePlate \
  -configuration Debug \
  -destination "platform=iOS Simulator,id=<UDID>" \
  -derivedDataPath ../.derivedData

# Проверка
APP=$(find ../.derivedData -type d -name "PulsePlate.app" | head -1)
if [ -n "$APP" ]; then
  echo "Checking Info*.plist files in bundle:"
  find "$APP" -maxdepth 2 -name "Info*.plist" -print
  echo ""
  echo "Expected: Only processed Info.plist (merged from Info-Debug.plist)"
  echo "If Info-Debug.plist appears as separate file → Target Membership is ON"
fi
```

## Ожидаемый результат

- В bundle должен быть **только один** обработанный `Info.plist` (результат слияния из `Info-Debug.plist` через `INFOPLIST_FILE`)
- **НЕ должно быть** `Info-Debug.plist` или `Info-Release.plist` как отдельных файлов в bundle
