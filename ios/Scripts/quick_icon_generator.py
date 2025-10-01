#!/usr/bin/env python3
"""
Быстрый генератор иконок для PulsePlate
Использование: python quick_icon_generator.py path/to/your/icon.png
"""

import os
import sys

try:
    from PIL import Image
except ImportError:
    Image = None


def create_icons_from_source(source_path: str) -> bool:
    """Создает все иконки из исходного изображения"""

    # Проверяем исходный файл
    if not os.path.exists(source_path):
        print(f"❌ Файл {source_path} не найден!")
        return False

    # Папка для иконок
    icons_dir = "PulsePlate/Assets.xcassets/AppIcon.appiconset"

    if not os.path.exists(icons_dir):
        print(f"❌ Папка {icons_dir} не найдена!")
        return False

    # Размеры иконок - соответствует Contents.json
    sizes = {
        # iPhone
        "icon_iphone_20pt@2x.png": 40,
        "icon_iphone_20pt@3x.png": 60,
        "icon_iphone_29pt@2x.png": 58,
        "icon_iphone_29pt@3x.png": 87,
        "icon_iphone_40pt@2x.png": 80,
        "icon_iphone_40pt@3x.png": 120,
        "icon_iphone_60pt@2x.png": 120,
        "icon_iphone_60pt@3x.png": 180,
        # iPad
        "icon_ipad_20pt.png": 20,
        "icon_ipad_20pt@2x.png": 40,
        "icon_ipad_29pt.png": 29,
        "icon_ipad_29pt@2x.png": 58,
        "icon_ipad_40pt.png": 40,
        "icon_ipad_40pt@2x.png": 80,
        "icon_ipad_76pt.png": 76,
        "icon_ipad_76pt@2x.png": 152,
        "icon_ipad_83_5pt@2x.png": 167,
        # App Store
        "icon_marketing_1024.png": 1024,
    }

    print(f"🎨 Создаем иконки из {source_path}")
    print(f"📁 Сохраняем в {icons_dir}")

    success = 0

    for filename, size in sizes.items():
        try:
            # Загружаем и изменяем размер
            with Image.open(source_path) as img:
                if img.mode != "RGBA":
                    img = img.convert("RGBA")

                resized = img.resize((size, size), Image.Resampling.LANCZOS)

                # Сохраняем
                output_path = os.path.join(icons_dir, filename)
                resized.save(output_path, "PNG", optimize=True)

                print(f"✅ {filename} ({size}x{size})")
                success += 1

        except (OSError, ValueError) as e:
            print(f"❌ Ошибка {filename}: {e}")

    print(f"\n🎯 Создано {success}/{len(sizes)} иконок")
    return success == len(sizes)


# Main guard — remove the redundant Pillow check
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python quick_icon_generator.py path/to/your/icon.png")
        sys.exit(1)

    source_path = sys.argv[1]

    if Image is None:
        print("❌ Установите Pillow: pip install Pillow")
        sys.exit(1)

    if create_icons_from_source(source_path):
        print("\n🎉 Готово! Теперь можно открыть проект в Xcode")
    else:
        print("\n❌ Произошли ошибки")
        sys.exit(1)
