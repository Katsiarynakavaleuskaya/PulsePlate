from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_SRC = REPO_ROOT / "frontend" / "src"
HEX_RE = re.compile(r"#[0-9a-fA-F]{6}\b")

# Explicit allowlist for token definition files and non-runtime test/story files.
ALLOWLIST_FILES = {
    FRONTEND_SRC / "styles" / "tokens.css",
    FRONTEND_SRC / "styles" / "tokens.ts",
}
ALLOWLIST_NAME_PARTS = (".test.", ".spec.", ".stories.")
SCAN_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx", ".css"}


def _is_allowlisted(path: Path) -> bool:
    if path in ALLOWLIST_FILES:
        return True
    return any(part in path.name for part in ALLOWLIST_NAME_PARTS)


def test_frontend_runtime_has_no_raw_hex_outside_allowlist() -> None:
    violations: list[str] = []

    for file_path in FRONTEND_SRC.rglob("*"):
        if not file_path.is_file() or file_path.suffix not in SCAN_EXTENSIONS:
            continue
        if _is_allowlisted(file_path):
            continue

        text = file_path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            match = HEX_RE.search(line)
            if match:
                rel_path = file_path.relative_to(REPO_ROOT)
                violations.append(f"{rel_path}:{line_no}:{match.group(0)}")

    assert not violations, "Raw hex colors found outside allowlist:\n" + "\n".join(violations)
