#!/usr/bin/env python3
"""
App Icon Generator from Source Image
Создает все размеры иконок iOS из одного изображения высокого качества
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PIL import Image
from ios.Scripts.icon_constants import IOS_APPICON_SIZES


def resize_icon(source_path: str, output_dir: str, filename: str, size: int) -> bool:
    """Создает иконку нужного размера из исходного изображения"""
    try:
        # Загружаем исходное изображение
        with Image.open(source_path) as img:
            # Конвертируем в RGBA если нужно
            if img.mode != "RGBA":
                img = img.convert("RGBA")

            # Изменяем размер с сохранением качества
            resized = img.resize((size, size), Image.Resampling.LANCZOS)

            # Сохраняем
            output_path = os.path.join(output_dir, filename)
            resized.save(output_path, "PNG", optimize=True)

            print(f"✅ {filename} ({size}x{size})")
            return True

    except Exception as e:
        print(f"❌ Ошибка при создании {filename}: {e}")
        return False


def generate_all_icons_from_source(source_path: str) -> bool:
    """Генерирует все необходимые размеры иконок из исходного изображения"""

    icon_sizes: Dict[str, int] = IOS_APPICON_SIZES.copy()

    # Путь к папке с иконками
    icons_dir = "PulsePlate/Assets.xcassets/AppIcon.appiconset"

    if not os.path.exists(icons_dir):
        print(f"❌ Папка {icons_dir} не найдена!")
        return False

    if not os.path.exists(source_path):
        print(f"❌ Исходный файл {source_path} не найден!")
        return False

    print(f"🎨 Создаем иконки из {source_path}...")
    print(f"📁 Сохраняем в {icons_dir}")

    success_count = 0
    total_count = len(icon_sizes)

    for filename, size in icon_sizes.items():
        if resize_icon(source_path, icons_dir, filename, size):
            success_count += 1

    print(f"\n🎯 Готово! Создано {success_count}/{total_count} иконок")
    return success_count == total_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Генератор иконок iOS из исходного изображения")
    parser.add_argument("source", help="Путь к исходному изображению (PNG, JPG)")

    args = parser.parse_args()

    # Проверяем наличие PIL
    try:
        import PIL  # noqa: F401
    except ImportError:
        print("❌ Требуется библиотека Pillow:")
        print("pip install Pillow")
        sys.exit(1)

    # Генерируем иконки
    if generate_all_icons_from_source(args.source):
        print("\n🎉 Все иконки успешно созданы!")
        print("📱 Теперь можно открыть проект в Xcode")
    else:
        print("\n❌ Произошли ошибки при создании иконок")
        sys.exit(1)


if __name__ == "__main__":
    main()
