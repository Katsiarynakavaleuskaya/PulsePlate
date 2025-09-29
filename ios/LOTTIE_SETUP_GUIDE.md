# 🎨 Руководство по установке Lottie для анимаций

## 📦 **Установка Lottie через Swift Package Manager:**

### 1. **Откройте проект в Xcode:**
```bash
open ios/PulsePlate.xcodeproj
```

### 2. **Добавьте Lottie зависимость:**

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

### 3. **Проверьте установку:**

1. **В Project Navigator** должна появиться папка "Package Dependencies"
2. **В ней должен быть** "lottie-ios"
3. **В Target Dependencies** должен быть "Lottie"

## 🎬 **Создание Lottie анимаций:**

### 1. **Создайте Lottie файлы:**
- Используйте After Effects + Bodymovin
- Или скачайте готовые анимации с LottieFiles.com
- Сохраните как `.json` файлы

### 2. **Добавьте в проект:**
- Перетащите `.json` файлы в Xcode
- Убедитесь, что они добавлены в Bundle

## 📱 **Использование в коде:**

```swift
import Lottie

struct LottieAnimationView: View {
    var body: some View {
        LottieView(animation: .named("animation_name"))
            .playing(loopMode: .loop)
    }
}
```

## 🔧 **Альтернативный способ - через CocoaPods:**

Если Swift Package Manager не работает:

1. **Установите CocoaPods:**
   ```bash
   sudo gem install cocoapods
   ```

2. **Создайте Podfile:**
   ```ruby
   platform :ios, '17.0'
   use_frameworks!

   target 'PulsePlate' do
     pod 'lottie-ios'
   end
   ```

3. **Установите зависимости:**
   ```bash
   pod install
   ```

4. **Откройте .xcworkspace:**
   ```bash
   open PulsePlate.xcworkspace
   ```

## 🎯 **После установки:**

1. **Импортируйте Lottie** в нужных файлах
2. **Создайте Lottie анимации** для FitChef
3. **Интегрируйте** в существующие компоненты

## 🐛 **Если не работает:**

1. **Очистите проект:** Product → Clean Build Folder
2. **Перезапустите Xcode**
3. **Проверьте версию iOS** (минимум 17.0)
4. **Убедитесь, что Lottie добавлен в Target**
