# 🚀 PulsePlate Project Update Guide

## Проблема с терминалом

У нас возникли проблемы с выполнением команд через терминал. Вот пошаговое руководство для ручного обновления проекта.

## 📋 План обновления

### 1. Проверка текущего состояния

```bash
# Проверить версии
python --version
node --version
npm --version
swift --version

# Проверить состояние проекта
git status
```

### 2. Обновление Python окружения

```bash
# Создать новое виртуальное окружение
python -m venv .venv_new
source .venv_new/bin/activate  # Windows: .venv_new\Scripts\activate

# Обновить pip
python -m pip install --upgrade pip setuptools wheel

# Установить зависимости
pip install -r requirements-dev.txt
pip install -r requirements.txt

	# Заменить старое окружение
	deactivate
	rm -rf .venv
	mv .venv_new .venv

	# Активировать новое окружение
	source .venv/bin/activate  # Windows: .venv\Scripts\activate
	```

### 3. Обновление Node.js зависимостей

```bash
# Очистить кэш
npm cache clean --force

# Переустановить зависимости (reproducible)
rm -rf node_modules

# Использовать npm ci если есть lockfile (рекомендуется)
if [ -f package-lock.json ]; then
  npm ci
else
  npm install
fi

# Или для обновления зависимостей (только если нужно):
# npm update
```

### 4. Обновление iOS инструментов

```bash
cd ios

# Обновить SwiftLint и SwiftFormat
brew upgrade swiftlint swiftformat

# Обновить Swift Package Manager зависимости
swift package update

# Очистить build кэш
rm -rf .build
rm -rf build
```

### 5. Обновление iOS зависимостей

```bash
cd ios

# Обновить Lottie
swift package update

# Проверить Package.resolved
cat Package.resolved
```

### 6. Тестирование после обновления

```bash
# Python тесты
python -m pytest tests/ -v --cov=core --cov-report=html

# Проверка линтинга
python -m flake8 core/ app/
python -m black --check core/ app/

# iOS тесты
cd ios
xcodebuild test -scheme PulsePlate -destination 'platform=iOS Simulator,name=iPhone 15'
```

### 7. Обновление документации

```bash
# Обновить версии в README
# Обновить requirements.txt если нужно
# Обновить Package.swift если нужно
```

## 🔧 Troubleshooting

### Проблема: "Permission denied"

```bash
chmod +x *.sh
chmod +x ios/Scripts/*.sh
```

### Проблема: "Module not found"

```bash
# Переустановить виртуальное окружение
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Проблема: "Swift package not found"

```bash
cd ios
swift package resolve
swift build
```

### Проблема: "Xcode build failed"

```bash
cd ios
# Очистить DerivedData
rm -rf ~/Library/Developer/Xcode/DerivedData
# Очистить build папку
rm -rf build
# Пересобрать
xcodebuild clean
xcodebuild build
```

## 📝 Чек-лист обновления

- [ ] Python окружение обновлено
- [ ] Node.js зависимости обновлены
- [ ] iOS инструменты обновлены
- [ ] Swift зависимости обновлены
- [ ] Все тесты проходят
- [ ] Линтинг проходит без ошибок
- [ ] Документация обновлена
- [ ] Git статус чистый

## 🎯 Следующие шаги

1. Выполните команды по порядку
2. Проверьте каждый шаг
3. Зафиксируйте изменения в git
4. Обновите CI/CD если нужно

## 📞 Если нужна помощь

Если возникнут проблемы:

1. Проверьте логи ошибок
2. Убедитесь что все зависимости установлены
3. Попробуйте очистить кэши
4. Перезапустите терминал/IDE
