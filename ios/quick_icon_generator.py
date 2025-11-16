#!/usr/bin/env python3
"""
Быстрый генератор иконок для PulsePlate

Использование: python quick_icon_generator.py path/to/your/icon.png

Это обёртка над ios/Scripts/quick_icon_generator_script.py для удобства использования.
"""

import sys
from pathlib import Path

# Add Scripts directory to path for imports
_scripts_dir = Path(__file__).parent / "Scripts"
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore

from quick_icon_generator_script import create_icons_from_source  # noqa: E402


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
