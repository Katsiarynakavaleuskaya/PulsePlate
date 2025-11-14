#!/usr/bin/env python3
"""
App Icon Generator for PulsePlate
Генерирует все необходимые размеры иконок из базового изображения 1024x1024
"""

import os
import sys

# Add script directory to path for imports
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("❌ Pillow (PIL) is not installed!")
    print("📦 Please install it with: pip install Pillow")
    print("   or: brew install pillow (on macOS)")
    sys.exit(1)

from icon_constants import IOS_ICON_SIZES  # noqa: E402


def create_pulseplate_icon(size: int) -> Image.Image:
    """Создает иконку PulsePlate с заданным размером

    Валидация размера предотвращает деление на ноль и некорректные расчеты
    для слишком маленьких, отрицательных и нецелочисленных значений.
    """
    # Early validation for size to avoid malformed drawing or ZeroDivision errors
    if not isinstance(size, int):
        raise TypeError(f"size must be an integer (received {type(size).__name__})")

    MIN_SIZE = 16
    if size < MIN_SIZE:
        raise ValueError(f"size must be >= {MIN_SIZE} pixels to render properly (got {size})")

    # Создаем изображение с прозрачным фоном
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Цвета бренда
    navy = (15, 23, 42, 255)  # #0F172A
    primary = (51, 159, 255, 255)  # #339FFF
    accent = (32, 201, 151, 255)  # #20C997
    heart = (255, 93, 93, 255)  # #FF5D5D

    # Рисуем фон (круг)
    margin = size // 8
    draw.ellipse([margin, margin, size - margin, size - margin], fill=navy)

    # Рисуем пульсирующий круг (внешний)
    pulse_margin = size // 6
    pulse_color = (*primary[:3], 100)  # Полупрозрачный
    draw.ellipse(
        [pulse_margin, pulse_margin, size - pulse_margin, size - pulse_margin], fill=pulse_color
    )

    # Рисуем внутренний круг
    inner_margin = size // 4
    draw.ellipse(
        [inner_margin, inner_margin, size - inner_margin, size - inner_margin], fill=accent
    )

    # Рисуем сердце в центре
    heart_size = size // 3
    heart_x = (size - heart_size) // 2
    heart_y = (size - heart_size) // 2

    # Простое сердце из двух кругов и треугольника
    heart_radius = heart_size // 4
    left_circle = (heart_x + heart_radius, heart_y + heart_radius)
    right_circle = (heart_x + heart_size - heart_radius, heart_y + heart_radius)

    # Два круга для верха сердца
    draw.ellipse(
        [
            left_circle[0] - heart_radius,
            left_circle[1] - heart_radius,
            left_circle[0] + heart_radius,
            left_circle[1] + heart_radius,
        ],
        fill=heart,
    )
    draw.ellipse(
        [
            right_circle[0] - heart_radius,
            right_circle[1] - heart_radius,
            right_circle[0] + heart_radius,
            right_circle[1] + heart_radius,
        ],
        fill=heart,
    )

    # Треугольник для низа сердца
    triangle_points = [
        (heart_x + heart_size // 2, heart_y + heart_size - heart_radius),
        (heart_x + heart_radius, heart_y + heart_size // 2),
        (heart_x + heart_size - heart_radius, heart_y + heart_size // 2),
    ]
    draw.polygon(triangle_points, fill=heart)

    return img


def generate_all_icons() -> bool:
    """Генерирует все необходимые размеры иконок"""

    # Путь к папке с иконками (относительно расположения скрипта)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icons_dir = os.path.join(
        script_dir, "..", "PulsePlate", "Assets.xcassets", "AppIcon.appiconset"
    )
    icons_dir = os.path.normpath(icons_dir)

    if not os.path.exists(icons_dir):
        print(f"❌ Папка {icons_dir} не найдена!")
        return False

    print("🎨 Генерируем иконки PulsePlate...")

    success_count = 0
    total_count = len(IOS_ICON_SIZES)

    for filename, size in IOS_ICON_SIZES.items():
        try:
            # Создаем иконку
            icon = create_pulseplate_icon(size)

            # Сохраняем
            filepath = os.path.join(icons_dir, filename)
            icon.save(filepath, "PNG")

            print(f"✅ {filename} ({size}x{size})")
            success_count += 1

        except (OSError, ValueError, TypeError, KeyError) as e:
            print(f"❌ Ошибка при создании {filename}: {e}")

    print(f"\n🎯 Готово! Создано {success_count}/{total_count} иконок")
    return success_count == total_count


if __name__ == "__main__":
    # Генерируем иконки
    if generate_all_icons():
        print("\n🎉 Все иконки успешно созданы!")
        print("📱 Теперь можно открыть проект в Xcode")
    else:
        print("\n❌ Произошли ошибки при создании иконок")
        sys.exit(1)
