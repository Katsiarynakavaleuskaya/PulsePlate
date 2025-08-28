import sys, pathlib

# Корень репозитория = родитель папки tests
ROOT = pathlib.Path(__file__).resolve().parent.parent
p = str(ROOT)
if p not in sys.path:
    sys.path.insert(0, p)
