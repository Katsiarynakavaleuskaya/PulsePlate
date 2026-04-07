"""Shared helpers for advisory wiki compiler CLIs (non-canonical, local-only).

RU: Вспомогательные функции для ingest/query/lint/promote; не SoT.
EN: Advisory wiki artifacts live under gitignored ``artifacts/orchestration/wiki/``.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

# Default layout under repo (gitignored).
DEFAULT_WIKI_ROOT: Final[Path] = Path("artifacts") / "orchestration" / "wiki"

_SLUG_SEGMENT_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def repo_root_default() -> Path:
    """Repository root (directory containing ``app/``)."""

    return Path(__file__).resolve().parents[2]


def resolve_repo_root(explicit: Path | None) -> Path:
    return explicit.resolve() if explicit is not None else repo_root_default()


def corpus_base(wiki_root: Path, corpus: str) -> Path:
    """Base directory for one corpus (e.g. ``project_internal``)."""

    safe_corpus = _sanitize_key_segment(corpus, fallback="corpus")
    return (wiki_root / safe_corpus).resolve()


def corpus_layout(base: Path) -> dict[str, Path]:
    """Standard subdirectories for a corpus."""

    return {
        "base": base,
        "pages": base / "pages",
        "raw": base / "raw",
        "promoted": base / "promoted",
        "index": base / "index.md",
        "log": base / "log.md",
    }


def _sanitize_key_segment(raw: str, *, fallback: str) -> str:
    """Produce a single path segment safe for filesystem and support-plane keys."""

    s = raw.strip().lower()
    s = _SLUG_SEGMENT_RE.sub("_", s)
    s = s.strip("._-") or fallback
    if not s[0].isalnum():
        s = f"x{s}"
    return s[:120]


def path_to_slug(rel_path: Path) -> str:
    """Derive wiki page slug from a path relative to repo root."""

    raw_parts = [p for p in rel_path.parts if p not in (".", "")]
    if not raw_parts:
        return "root"
    parts: list[str] = []
    for i, p in enumerate(raw_parts):
        is_last = i == len(raw_parts) - 1
        name = Path(p).stem if is_last and p.lower().endswith(".md") else p
        seg = _sanitize_key_segment(name, fallback="part")
        parts.append(seg)
    slug = ".".join(parts)
    return slug[:120]


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_frontmatter(body: str) -> tuple[dict[str, Any], str]:
    """Split YAML-like frontmatter (simple key: value lines) from markdown body."""

    lines = body.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, body
    meta: dict[str, Any] = {}
    i = 1
    while i < len(lines):
        line = lines[i]
        if line.strip() == "---":
            rest = "\n".join(lines[i + 1 :])
            return meta, rest if rest else ""
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
        i += 1
    return {}, body


def format_frontmatter(meta: dict[str, str]) -> str:
    lines = ["---"]
    for k in sorted(meta.keys()):
        lines.append(f"{k}: {meta[k]}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"
