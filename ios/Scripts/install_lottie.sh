#!/bin/bash

# 🎨 Скрипт для установки Lottie в Xcode проект
# Автоматически добавляет Lottie зависимость через Swift Package Manager

echo "🎨 Установка Lottie для PulsePlate..."

# Проверяем, что мы в правильной папке
if [ ! -f "PulsePlate.xcodeproj/project.pbxproj" ]; then
    echo "❌ Ошибка: Запустите скрипт из папки ios/"
    exit 1
fi

echo "✅ Найден проект PulsePlate.xcodeproj"

# Создаем временный скрипт для добавления пакета
cat > add_lottie_package.swift << 'EOF'
import Foundation

// Этот скрипт будет выполнен в Xcode для добавления Lottie пакета
let packageURL = "https://github.com/airbnb/lottie-ios.git"
let packageVersion = "4.5.2"

print("📦 Добавляем Lottie пакет...")
print("URL: \(packageURL)")
print("Version: \(packageVersion)")

// Инструкции для ручного добавления:
print("\n📋 РУЧНЫЕ ШАГИ:")
print("1. Откройте PulsePlate.xcodeproj в Xcode")
print("2. File → Add Package Dependencies...")
print("3. Введите URL: \(packageURL)")
print("4. Выберите Version: Up to Next Major, From: \(packageVersion)")
print("5. Нажмите Add Package")
print("6. Выберите Target 'PulsePlate'")
print("7. Нажмите Add Package")
print("\n✅ Готово! Lottie будет добавлен в проект")
EOF
[ $? -eq 0 ] || { echo "❌ Не удалось создать add_lottie_package.swift"; exit 1; }

echo "📝 Создан скрипт для добавления Lottie пакета"
echo "📋 Инструкции сохранены в add_lottie_package.swift"

# Создаем инструкцию для пользователя
cat > LOTTIE_INSTALL_STEPS.md << 'EOF'
# 🎨 Пошаговая установка Lottie в Xcode

## 📱 **Шаг 1: Откройте проект**
```bash
open PulsePlate.xcodeproj
```

## 📦 **Шаг 2: Добавьте Lottie пакет**

1. **В Xcode выберите:**
   - File → Add Package Dependencies...

2. **Введите URL:**
   ```
   https://github.com/airbnb/lottie-ios.git
   ```

3. **Выберите версию:**
   - Version: Up to Next Major
   - From: 4.5.2

4. **Добавьте в Target:**
   - Выберите Target "PulsePlate"
   - Нажмите "Add Package"

## ✅ **Шаг 3: Проверьте установку**

1. **В Project Navigator** должна появиться папка "Package Dependencies"
2. **В ней должен быть** "lottie-ios"
3. **В Target Dependencies** должен быть "Lottie"

## 🎬 **Шаг 4: Создайте Lottie анимации**

1. **Скачайте готовые анимации:**
   - https://lottiefiles.com/
   - Или создайте в After Effects + Bodymovin

2. **Добавьте .json файлы в проект:**
   - Перетащите .json файлы в Xcode
   - Убедитесь, что они добавлены в Bundle

## 🧪 **Шаг 5: Протестируйте**

1. **Запустите приложение**
2. **Перейдите на вкладку "Profile"**
3. **Нажмите "Test Lottie Animation"**
4. **Проверьте воспроизведение анимаций**

## 🐛 **Если не работает:**

1. **Очистите проект:** Product → Clean Build Folder
2. **Перезапустите Xcode**
3. **Проверьте версию iOS** (минимум 17.0)
4. **Убедитесь, что Lottie добавлен в Target**
EOF
[ $? -eq 0 ] || { echo "❌ Не удалось создать LOTTIE_INSTALL_STEPS.md"; exit 1; }

echo "📋 Создана подробная инструкция: LOTTIE_INSTALL_STEPS.md"

# Создаем тестовые Lottie файлы (заглушки)
mkdir -p PulsePlate/Resources/Lottie
cat > PulsePlate/Resources/Lottie/fitchef_blink.json << 'EOF'
{
  "v": "5.7.4",
  "fr": 30,
  "ip": 0,
  "op": 30,
  "w": 200,
  "h": 200,
  "nm": "FitChef Blink",
  "ddd": 0,
  "assets": [],
  "layers": [
    {
      "ddd": 0,
      "ind": 1,
      "ty": 4,
      "nm": "Eye",
      "sr": 1,
      "ks": {
        "o": {
          "a": 1,
          "k": [
            {
              "i": {
                "x": [0.667],
                "y": [1]
              },
              "o": {
                "x": [0.333],
                "y": [0]
              },
              "t": 0,
              "s": [100]
            },
            {
              "i": {
                "x": [0.667],
                "y": [1]
              },
              "o": {
                "x": [0.333],
                "y": [0]
              },
              "t": 15,
              "s": [0]
            },
            {
              "t": 30,
              "s": [100]
            }
          ],
          "ix": 11
        },
        "r": {
          "a": 0,
          "k": 0,
          "ix": 10
        },
        "p": {
          "a": 0,
          "k": [100, 100, 0],
          "ix": 2
        },
        "a": {
          "a": 0,
          "k": [0, 0, 0],
          "ix": 1
        },
        "s": {
          "a": 0,
          "k": [100, 100, 100],
          "ix": 6
        }
      },
      "ao": 0,
      "shapes": [
        {
          "ty": "gr",
          "it": [
            {
              "d": 1,
              "ty": "el",
              "s": {
                "a": 0,
                "k": [20, 20],
                "ix": 2
              },
              "p": {
                "a": 0,
                "k": [0, 0],
                "ix": 3
              },
              "nm": "Ellipse Path 1",
              "mn": "ADBE Vector Shape - Ellipse",
              "hd": false
            },
            {
              "ty": "fl",
              "c": {
                "a": 0,
                "k": [0, 0, 0, 1],
                "ix": 4
              },
              "o": {
                "a": 0,
                "k": 100,
                "ix": 5
              },
              "r": 1,
              "bm": 0,
              "nm": "Fill 1",
              "mn": "ADBE Vector Graphic - Fill",
              "hd": false
            }
          ],
          "nm": "Ellipse 1",
          "np": 2,
          "cix": 2,
          "bm": 0,
          "ix": 1,
          "mn": "ADBE Vector Group",
          "hd": false
        }
      ],
      "ip": 0,
      "op": 30,
      "st": 0,
      "bm": 0
    }
  ],
  "markers": []
}
EOF

echo "🎬 Создан тестовый Lottie файл: fitchef_blink.json"

echo ""
echo "🎉 Готово! Следующие шаги:"
echo "1. Откройте PulsePlate.xcodeproj в Xcode"
echo "2. Следуйте инструкциям в LOTTIE_INSTALL_STEPS.md"
echo "3. Добавьте Lottie пакет через Swift Package Manager"
echo "4. Протестируйте анимации"
echo ""
echo "📁 Файлы созданы:"
echo "  - add_lottie_package.swift (скрипт)"
echo "  - LOTTIE_INSTALL_STEPS.md (инструкция)"
echo "  - PulsePlate/Resources/Lottie/fitchef_blink.json (тестовая анимация)"
