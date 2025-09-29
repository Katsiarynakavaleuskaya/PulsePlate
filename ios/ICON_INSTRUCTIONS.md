# 📱 Инструкция по созданию иконок PulsePlate

## 🎯 Что нужно сделать:

1. **Поместите вашу иконку высокого качества** в папку `ios/`
   - Формат: PNG или JPG
   - Размер: минимум 1024x1024 пикселей
   - Название: например `my_icon.png`

2. **Запустите скрипт генерации:**
   ```bash
   cd ios/
   python3 quick_icon_generator.py my_icon.png
   ```

   **Примечание:** На macOS 12.3+ команда `python` недоступна. Убедитесь, что Python 3 установлен и доступен как `python3`.

3. **Проверьте результат:**
   - Все иконки будут созданы в `PulsePlate/Assets.xcassets/AppIcon.appiconset/`
   - Откройте проект в Xcode для проверки

## 🔧 Альтернативный способ:

Если у вас есть готовые иконки разных размеров, просто замените файлы в папке:
```
ios/PulsePlate/Assets.xcassets/AppIcon.appiconset/
```

## 📋 Требуемые размеры:

- **AppIcon-1024.png** (1024x1024) - App Store
- **AppIcon-20@1x.png** (20x20) - iPad
- **AppIcon-20@2x.png** (40x40) - iPhone/iPad
- **AppIcon-20@3x.png** (60x60) - iPhone
- **AppIcon-29@1x.png** (29x29) - iPad
- **AppIcon-29@2x.png** (58x58) - iPhone/iPad
- **AppIcon-29@3x.png** (87x87) - iPhone
- **AppIcon-40@1x.png** (40x40) - iPad
- **AppIcon-40@2x.png** (80x80) - iPhone/iPad
- **AppIcon-40@3x.png** (120x120) - iPhone
- **AppIcon-60@2x.png** (120x120) - iPhone
- **AppIcon-60@3x.png** (180x180) - iPhone
- **AppIcon-76@1x.png** (76x76) - iPad
- **AppIcon-76@2x.png** (152x152) - iPad
- **AppIcon-83.5@2x.png** (167x167) - iPad Pro

## 🚀 Быстрый старт:

1. Скопируйте вашу иконку в `ios/` папку
2. Запустите: `python3 quick_icon_generator.py ваша_иконка.png`
3. Откройте проект в Xcode
