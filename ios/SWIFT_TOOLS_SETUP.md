# Swift Tools Setup для PulsePlate

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
cd ios
swift package resolve
swift build
```

### 2. Первый запуск

```bash
./Scripts/swift_tools.sh build
./Scripts/swift_tools.sh all
```

## 📋 Доступные команды

### Основные команды

```bash
# Проверить качество кода
./Scripts/swift_tools.sh lint

# Отформатировать код
./Scripts/swift_tools.sh format

# Проверить форматирование (без изменений)
./Scripts/swift_tools.sh check

# Запустить все инструменты
./Scripts/swift_tools.sh all

# Собрать инструменты
./Scripts/swift_tools.sh build
```

### Интеграция с Xcode

#### Автоматическая интеграция через Build Phase

1. Откройте `PulsePlate.xcodeproj`
2. Выберите проект → Target "PulsePlate"
3. Build Phases → + → New Run Script Phase
4. Вставьте содержимое `xcode_build_phase.sh`
5. Переместите скрипт перед "Compile Sources"

#### Ручная интеграция

1. **Pre-commit hook:**

```bash
# В корне проекта
cp ios/xcode_build_phase.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

2. **VS Code integration:**

```json
// .vscode/tasks.json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Swift Lint",
            "type": "shell",
            "command": "${workspaceFolder}/ios/Scripts/swift_tools.sh",
            "args": ["lint"],
            "options": {
                "cwd": "${workspaceFolder}/ios"
            },
            "group": "build"
        },
        {
            "label": "Swift Format",
            "type": "shell",
            "command": "${workspaceFolder}/ios/Scripts/swift_tools.sh",
            "args": ["format"],
            "options": {
                "cwd": "${workspaceFolder}/ios"
            },
            "group": "build"
        }
    ]
}
```

## ⚙️ Конфигурация

### SwiftLint (.swiftlint.yml)

- Настроен для health-приложений
- Специальные правила для HealthKit и StoreKit
- Apple HIG compliance
- Максимальная длина строки: 120 символов

### SwiftFormat (.swiftformat)

- Apple HIG стиль форматирования
- Автоматическое удаление неиспользуемого кода
- Сортировка импортов
- Отступы: 4 пробела

## 🔧 Troubleshooting

### Проблема: "SwiftLint not found"

```bash
swift build --product SwiftLint
```

### Проблема: "SwiftFormat not found"

```bash
swift build --product SwiftFormat
```

### Проблема: "Permission denied"

```bash
chmod +x swift_tools.sh
chmod +x xcode_build_phase.sh
```

## 📊 CI/CD Integration

### GitHub Actions

```yaml
- name: Swift Lint
  run: |
    cd ios
    swift build --product SwiftLint
    .build/debug/SwiftLint lint --config .swiftlint.yml

- name: Swift Format Check
  run: |
    cd ios
    swift build --product SwiftFormat
    .build/debug/SwiftFormat --config .swiftformat --lint PulsePlate/**/*.swift
```

## 🎯 Best Practices

1. **Всегда форматируйте перед коммитом:**

```bash
./Scripts/swift_tools.sh format
```

2. **Проверяйте качество кода:**

```bash
./Scripts/swift_tools.sh lint
```

3. **Используйте в Xcode Build Phase для автоматизации**

4. **Настройте pre-commit hooks для команды**

## 📝 Примечания

- Инструменты работают только с Swift файлами в папке `PulsePlate/`
- Конфигурация оптимизирована для health-приложений
- Поддерживается интеграция с Xcode и VS Code
- Все скрипты имеют цветной вывод для удобства
