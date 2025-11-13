import sys
from pathlib import Path


def ensure_root_in_syspath(root: Path) -> None:
    """Ensure the root path is in sys.path if not already present."""
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


ROOT = Path(__file__).resolve().parents[1]
ensure_root_in_syspath(ROOT)
