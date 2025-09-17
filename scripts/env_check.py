#!/usr/bin/env python3
"""
Environment diagnostic script for PulsePlate.
- Prints Python and package versions
- Verifies basic project structure
- Does NOT mutate environment variables or PYTHONPATH
- Not collected by pytest (placed under scripts/)
"""
from __future__ import annotations

import sys
from pathlib import Path


def check_python() -> bool:
    print(f"🐍 Python version: {sys.version}")
    print(f"🐍 Python exec: {sys.executable}")
    return True


def check_imports() -> bool:
    ok = True
    for mod in ("fastapi", "pydantic", "pytest"):
        try:
            m = __import__(mod)
            print(f"✅ {mod}: {getattr(m, '__version__', 'OK')}")
        except Exception as e:
            ok = False
            print(f"❌ {mod}: {e}")
    return ok


def check_structure() -> bool:
    root = Path(__file__).resolve().parents[1]
    required = ["app", "core", "tests", "data"]
    ok = True
    for name in required:
        p = root / name
        if p.exists():
            print(f"✅ {name}: exists")
        else:
            ok = False
            print(f"❌ {name}: missing")
    return ok


def main() -> int:
    print("🚀 PulsePlate environment check")
    print("=" * 50)
    ok = True
    ok &= check_python()
    ok &= check_imports()
    ok &= check_structure()
    print("=" * 50)
    print("✅ All checks passed" if ok else "⚠️ Some checks failed")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
