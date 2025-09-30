#!/usr/bin/env python3
"""
App Icon Generator from Source Image
Создает все размеры иконок iOS из одного изображения высокого качества
"""

import os
import sys
import argparse


def _process_image_for_icon(img, size: int):
    """Обрабатывает изображение для создания иконки"""
    from PIL import Image

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
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        print("❌ Требуется библиотека Pillow: pip install Pillow")
        return False

    # Размеры для iOS (в пикселях) - соответствует Contents.json
    icon_sizes = {
        # iPhone
        "icon_iphone_20pt@2x.png": 40,  # 20x20 @2x
        "icon_iphone_20pt@3x.png": 60,  # 20x20 @3x
        "icon_iphone_29pt@2x.png": 58,  # 29x29 @2x
        "icon_iphone_29pt@3x.png": 87,  # 29x29 @3x
        "icon_iphone_40pt@2x.png": 80,  # 40x40 @2x
        "icon_iphone_40pt@3x.png": 120,  # 40x40 @3x
        "icon_iphone_60pt@2x.png": 120,  # 60x60 @2x
        "icon_iphone_60pt@3x.png": 180,  # 60x60 @3x
        # iPad
        "icon_ipad_20pt.png": 20,  # 20x20 @1x
        "icon_ipad_20pt@2x.png": 40,  # 20x20 @2x
        "icon_ipad_29pt.png": 29,  # 29x29 @1x
        "icon_ipad_29pt@2x.png": 58,  # 29x29 @2x
        "icon_ipad_40pt.png": 40,  # 40x40 @1x
        "icon_ipad_40pt@2x.png": 80,  # 40x40 @2x
        "icon_ipad_76pt.png": 76,  # 76x76 @1x
        "icon_ipad_76pt@2x.png": 152,  # 76x76 @2x
        "icon_ipad_83_5pt@2x.png": 167,  # 83.5x83.5 @2x
        # App Store
        "icon_marketing_1024.png": 1024,  # 1024x1024
    }

    # Путь к папке с иконками (относительно расположения скрипта)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icons_dir = os.path.join(
        script_dir, "..", "PulsePlate", "Assets.xcassets", "AppIcon.appiconset"
    )
    icons_dir = os.path.normpath(icons_dir)

    if not os.path.exists(icons_dir):
        print(f"❌ Папка {icons_dir} не найдена!")
        return False

    if not os.path.exists(source_path):
        print(f"❌ Исходный файл {source_path} не найден!")
        return False

    print(f"🎨 Создаем иконки из {source_path}...")
    print(f"📁 Сохраняем в {icons_dir}")

    total_count = len(icon_sizes)
    success_count = sum(
        resize_icon(source_path, icons_dir, filename, size) for filename, size in icon_sizes.items()
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
