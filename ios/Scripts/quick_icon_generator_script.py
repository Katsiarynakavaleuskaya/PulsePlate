#!/usr/bin/env python3
"""
Быстрый генератор иконок для PulsePlate
Использование: python quick_icon_generator.py path/to/your/icon.png
"""

import os
import sys

# Add script directory to path for imports
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore

from icon_constants import IOS_ICON_SIZES  # noqa: E402


def create_icons_from_source(source_path: str) -> bool:
    """Создает все иконки из исходного изображения"""

    # Проверяем исходный файл
    if not os.path.exists(source_path):
        print(f"❌ Файл {source_path} не найден!")
        return False

    # Папка для иконок (относительно расположения скрипта)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icons_dir = os.path.join(
        script_dir, "..", "PulsePlate", "Assets.xcassets", "AppIcon.appiconset"
    )
    icons_dir = os.path.normpath(os.path.abspath(icons_dir))

    if not os.path.exists(icons_dir):
        print(f"❌ Папка {icons_dir} не найдена!")
        return False

    print(f"🎨 Создаем иконки из {source_path}")
    print(f"📁 Сохраняем в {icons_dir}")

    success = 0

    for filename, size in IOS_ICON_SIZES.items():
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

    print(f"\n🎯 Создано {success}/{len(IOS_ICON_SIZES)} иконок")
    return success == len(IOS_ICON_SIZES)


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
