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
   - From: 4.4.0

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
