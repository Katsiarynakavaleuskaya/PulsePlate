# 🎬 Инструкция по настройке MP4 анимаций FitChef

## 📁 **Текущее состояние:**
- MP4 файлы находятся в `ios/PulsePlate/Resources/`
- Компоненты созданы: `VideoPlayerView.swift`, `AnimationTestView.swift`
- Тестовый экран добавлен в ProfileView

## 🔧 **Что нужно сделать в Xcode:**

### 1. **Добавить MP4 файлы в проект:**
1. Откройте `ios/PulsePlate.xcodeproj`
2. В Project Navigator найдите папку `PulsePlate`
3. Правой кнопкой → "Add Files to 'PulsePlate'"
4. Выберите папку `Resources/` с MP4 файлами
5. Убедитесь, что "Add to target: PulsePlate" отмечен
6. Нажмите "Add"

### 2. **Проверить Bundle Resources:**
1. Выберите проект в Project Navigator
2. Выберите Target "PulsePlate"
3. Перейдите на вкладку "Build Phases"
4. Разверните "Copy Bundle Resources"
5. Убедитесь, что MP4 файлы там есть

### 3. **Тестирование:**
1. Запустите приложение
2. Перейдите на вкладку "Profile"
3. Нажмите "Test FitChef Animation"
4. Проверьте, что видео воспроизводится

## 🎯 **Ожидаемый результат:**
- Видео должно воспроизводиться в тестовом экране
- Кнопки "Previous/Next" должны переключать между анимациями
- Если видео не загружается, будет показана ошибка

## 🐛 **Если не работает:**
1. Проверьте, что MP4 файлы добавлены в Bundle
2. Убедитесь, что имена файлов совпадают с кодом
3. Проверьте консоль на ошибки загрузки

## 📱 **Использование в коде:**
```swift
// Простое видео
VideoPlayerView(videoName: "20250913_1212_FitChef Cat Animation_simple_compose_01k515hmynfk7amcg36rv5eqba")

// Анимированный FitChef
AnimatedFitChefVideo()

// Облачко с анимацией
AnimatedMascotBubbleVideo(textKey: "Привет!")
```
