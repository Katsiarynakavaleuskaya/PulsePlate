#!/bin/bash

# 🎬 Скрипт для добавления MP4 файлов в Xcode проект

echo "🎬 Добавляем MP4 файлы в Xcode проект..."

# Проверяем, что мы в правильной папке
if [ ! -f "PulsePlate.xcodeproj/project.pbxproj" ]; then
    echo "❌ Ошибка: Запустите скрипт из папки ios/"
    exit 1
fi

echo "✅ Найден проект PulsePlate.xcodeproj"

# Создаем папку для MP4 файлов
mkdir -p PulsePlate/Resources/MP4

# Проверяем наличие исходной папки и MP4 файлов
if [ -d "temp_animation" ] && compgen -G "temp_animation/*.mp4" > /dev/null; then
    echo "📁 Копируем MP4 файлы из temp_animation..."
    if ! cp temp_animation/*.mp4 PulsePlate/Resources/MP4/; then
        echo "⚠️  Не удалось скопировать некоторые файлы"
    fi
else
    echo "⚠️  Папка temp_animation не найдена или не содержит MP4 файлов"
fi

# Дополнительная копия из корневой папки Resources (если есть)
cp PulsePlate/Resources/*.mp4 PulsePlate/Resources/MP4/ 2>/dev/null || true

# Проверяем, что файлы скопированы
echo "📋 Проверяем MP4 файлы:"
ls -la PulsePlate/Resources/MP4/

# Создаем инструкцию для добавления в Xcode
cat > ADD_MP4_TO_XCODE.md << 'EOF'
# 🎬 Добавление MP4 файлов в Xcode проект

## 📱 **Шаг 1: Откройте проект**
```bash
open PulsePlate.xcodeproj
```

## 📦 **Шаг 2: Добавьте MP4 файлы в проект**

1. **В Xcode Project Navigator:**
   - Найдите папку `PulsePlate`
   - Правой кнопкой → "Add Files to 'PulsePlate'"

2. **Выберите папку с MP4:**
   - Перейдите в `PulsePlate/Resources/MP4/`
   - Выберите все .mp4 файлы
   - Убедитесь, что "Add to target: PulsePlate" отмечен
   - Нажмите "Add"

## ✅ **Шаг 3: Проверьте Bundle Resources**

1. **Выберите проект в Project Navigator**
2. **Выберите Target "PulsePlate"**
3. **Перейдите на вкладку "Build Phases"**
4. **Разверните "Copy Bundle Resources"**
5. **Убедитесь, что MP4 файлы там есть**

## 🧪 **Шаг 4: Протестируйте**

1. **Запустите приложение**
2. **Перейдите на вкладку "Profile"**
3. **Нажмите "Test MP4 Animation"**
4. **Проверьте воспроизведение видео**

## 🐛 **Если видео не воспроизводится:**

1. **Проверьте консоль на ошибки:**
   - `❌ Video not found` - файл не найден в Bundle
   - `✅ Video loaded` - файл успешно загружен

2. **Возможные решения:**
   - Убедитесь, что MP4 файлы добавлены в Bundle
   - Проверьте, что имена файлов совпадают с кодом
   - Очистите проект: Product → Clean Build Folder

## 📱 **Ожидаемый результат:**
- Видео должно воспроизводиться в тестовом экране
- Кнопки "Previous/Next" должны переключать между анимациями
- В консоли должно быть "✅ Video loaded"
EOF

echo "📋 Создана инструкция: ADD_MP4_TO_XCODE.md"

# Генерируем список MP4 файлов динамически
MP4_FILES=""
if [ -d "PulsePlate/Resources/MP4" ] && [ "$(ls -A PulsePlate/Resources/MP4/*.mp4 2>/dev/null)" ]; then
    # Используем find для безопасной обработки файлов
    MP4_FILES=$(find PulsePlate/Resources/MP4 -maxdepth 1 -name "*.mp4" -print0 2>/dev/null | xargs -0 -I {} basename {} .mp4 | awk 'BEGIN{ORS=""} {if(NR>1) print ", "; print "        \"" $0 "\""}')
else
    MP4_FILES='        "no_files_found"'
fi

# Создаем папку для Views/Components
mkdir -p PulsePlate/Views/Components

# Создаем простой тест для проверки Bundle
cat > PulsePlate/Views/Components/BundleTestView.swift << EOF
import SwiftUI

/// RU: Тест для проверки файлов в Bundle
/// EN: Test for checking files in Bundle
struct BundleTestView: View {
    private let mp4Files = [
$MP4_FILES
    ]

    var body: some View {
        VStack(spacing: 20) {
            Text("Bundle Test")
                .font(.title)
                .bold()
                .foregroundStyle(.white)

            // Проверяем MP4 файлы
            VStack(alignment: .leading, spacing: 8) {
                Text("MP4 Files in Bundle:")
                    .font(.headline)
                    .foregroundStyle(.white)

                ForEach(mp4Files, id: \.self) { file in
                    HStack {
                        if Bundle.main.url(forResource: file, withExtension: "mp4") != nil {
                            Image(systemName: "checkmark.circle.fill")
                                .foregroundStyle(.green)
                            Text("✅ \(file)")
                                .font(.caption)
                                .foregroundStyle(.green)
                        } else {
                            Image(systemName: "xmark.circle.fill")
                                .foregroundStyle(.red)
                            Text("❌ \(file)")
                                .font(.caption)
                                .foregroundStyle(.red)
                        }
                    }
                }
            }
            .padding()
            .background(Color.white.opacity(0.1))
            .clipShape(RoundedRectangle(cornerRadius: 12))

            // Информация о Bundle
            VStack(alignment: .leading, spacing: 4) {
                Text("Bundle Info:")
                    .font(.caption)
                    .bold()
                    .foregroundStyle(.white)

                Text("Bundle path: \(Bundle.main.bundlePath)")
                    .font(.caption2)
                    .foregroundStyle(.gray)

                Text("Resources path: \(Bundle.main.resourcePath ?? "nil")")
                    .font(.caption2)
                    .foregroundStyle(.gray)
            }
            .padding()
            .background(Color.black.opacity(0.3))
            .clipShape(RoundedRectangle(cornerRadius: 8))

            Spacer()
        }
        .padding()
        .background(.navy)
        .navigationTitle("Bundle Test")
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview {
    BundleTestView()
}
EOF

echo "🧪 Создан BundleTestView для проверки файлов"

echo ""
echo "🎉 Готово! Следующие шаги:"
echo "1. Откройте PulsePlate.xcodeproj в Xcode"
echo "2. Следуйте инструкциям в ADD_MP4_TO_XCODE.md"
echo "3. Добавьте MP4 файлы в проект"
echo "4. Протестируйте в BundleTestView"
echo ""
echo "📁 Файлы готовы:"
echo "  - PulsePlate/Resources/MP4/ (MP4 файлы)"
echo "  - ADD_MP4_TO_XCODE.md (инструкция)"
echo "  - BundleTestView.swift (тест Bundle)"
