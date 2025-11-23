#!/usr/bin/env python3
"""
App Icon Generator from Source Image
Создает все размеры иконок iOS из одного изображения высокого качества
"""

import argparse
import os
import sys
from typing import TYPE_CHECKING

# Add script directory to path only when executed as a script
_script_dir = os.path.dirname(os.path.abspath(__file__))
if (__package__ in (None, "")) and _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

if TYPE_CHECKING:
    from PIL import Image
else:
    try:
        from PIL import Image
    except ImportError:
        Image = None  # type: ignore

try:
    from .icon_constants import IOS_ICON_SIZES  # noqa: E402
except ImportError:
    # Fallback for when script is run directly (not as module)
    from icon_constants import IOS_ICON_SIZES  # noqa: E402


def _process_image_for_icon(img: "Image.Image", size: int) -> "Image.Image":
    """Обрабатывает изображение для создания иконки"""

    # Конвертируем в RGBA если нужно
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    # Изменяем размер с сохранением качества
    return img.resize((size, size), Image.Resampling.LANCZOS)


def resize_icon(source_path: str, output_dir: str, filename: str, size: int) -> bool:
    """Создает иконку нужного размера из исходного изображения"""
    try:
        from PIL import Image

        # Загружаем исходное изображение
        with Image.open(source_path) as img:
            # Обрабатываем изображение
            resized = _process_image_for_icon(img, size)

            # Сохраняем
            output_path = os.path.join(output_dir, filename)
            resized.save(output_path, "PNG", optimize=True)

            print(f"✅ {filename} ({size}x{size})")
            return True

    except (OSError, ValueError, ImportError) as e:
        print(f"❌ Ошибка при создании {filename}: {e}")
        return False


def generate_all_icons_from_source(source_path: str) -> bool:
    """Генерирует все необходимые размеры иконок из исходного изображения"""
    if Image is None:
        print("❌ Требуется библиотека Pillow: pip install Pillow")
        return False

    # Путь к папке с иконками (относительно расположения скрипта или из переменной окружения)
    env_icons_dir = os.getenv("IOS_APPICONSET_DIR")
    if env_icons_dir:
        icons_dir = os.path.normpath(os.path.abspath(os.path.expanduser(env_icons_dir)))
    else:
        script_dir: str = os.path.dirname(os.path.abspath(__file__))
        icons_dir: str = os.path.join(
            script_dir, "..", "PulsePlate", "Assets.xcassets", "AppIcon.appiconset"
        )
        icons_dir = os.path.normpath(icons_dir)

    if not os.path.exists(icons_dir):
        print(f"⚠️  Папка {icons_dir} не найдена, создаём...")
        os.makedirs(icons_dir, exist_ok=True)

    if not os.path.exists(source_path):
        print(f"❌ Исходный файл {source_path} не найден!")
        return False

    print(f"🎨 Создаем иконки из {source_path}...")
    print(f"📁 Сохраняем в {icons_dir}")

    total_count = len(IOS_ICON_SIZES)
    success_count = sum(
        resize_icon(source_path, icons_dir, filename, size)
        for filename, size in IOS_ICON_SIZES.items()
    )

    print(f"\n🎯 Готово! Создано {success_count}/{total_count} иконок")
    return success_count == total_count


def main() -> None:
    # Check Pillow availability
    try:
        import PIL  # noqa: F401
    except ImportError:
        print("❌ Требуется библиотека Pillow:")
        print("   pip install Pillow")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Генератор иконок iOS из исходного изображения")
    parser.add_argument("source", help="Путь к исходному изображению (PNG, JPG)")

    args = parser.parse_args()

    # Генерируем иконки
    if generate_all_icons_from_source(args.source):
        print("\n🎉 Все иконки успешно созданы!")
        print("📱 Теперь можно открыть проект в Xcode")
    else:
        print("\n❌ Произошли ошибки при создании иконок")
        sys.exit(1)


if __name__ == "__main__":
    main()
