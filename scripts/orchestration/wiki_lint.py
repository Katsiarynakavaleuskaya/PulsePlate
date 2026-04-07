"""Lint advisory wiki pages (frontmatter + raw hash presence).

RU: Проверка полей метаданных и наличия raw-копии; только локально.
EN: Read-only; no network; does not modify support plane.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Final

from scripts.orchestration import _wiki_compiler_support as wcs

EXIT_OK: Final[int] = 0
EXIT_VIOLATIONS: Final[int] = 1
EXIT_USAGE: Final[int] = 2

_REQUIRED_KEYS = ("advisory", "corpus", "content_hash", "ingested_at")


def lint_corpus(
    *,
    corpus: str,
    wiki_root: Path,
    repo_root: Path,
) -> list[str]:
    """Return human-readable violation messages (empty if OK)."""

    violations: list[str] = []
    layout = wcs.corpus_layout(wcs.corpus_base(wiki_root, corpus))
    pages_dir = layout["pages"]
    raw_dir = layout["raw"]
    if not pages_dir.is_dir():
        violations.append("pages_directory_missing")
        return violations
    for page in sorted(pages_dir.glob("*.md")):
        text = page.read_text(encoding="utf-8")
        meta, _ = wcs.parse_frontmatter(text)
        for key in _REQUIRED_KEYS:
            if key not in meta:
                violations.append(f"{page.name}:missing_meta:{key}")
        if meta.get("advisory") != "true":
            violations.append(f"{page.name}:advisory_not_true")
        ch = str(meta.get("content_hash", ""))
        if not ch:
            violations.append(f"{page.name}:empty_content_hash")
            continue
        raw_path = raw_dir / f"{ch}.md"
        if not raw_path.is_file():
            violations.append(f"{page.name}:missing_raw:{ch}")
    return violations


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corpus", default="project_internal")
    p.add_argument("--wiki-root", type=Path, default=wcs.DEFAULT_WIKI_ROOT)
    p.add_argument("--repo-root", type=Path, default=None)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = wcs.resolve_repo_root(args.repo_root)
    wiki_root = args.wiki_root
    if not wiki_root.is_absolute():
        wiki_root = (repo_root / wiki_root).resolve()
    try:
        violations = lint_corpus(corpus=args.corpus, wiki_root=wiki_root, repo_root=repo_root)
    except OSError as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True), file=sys.stderr)
        return EXIT_USAGE
    print(
        json.dumps(
            {
                "corpus": args.corpus,
                "ok": not violations,
                "violations": violations,
            },
            sort_keys=True,
        )
    )
    return EXIT_OK if not violations else EXIT_VIOLATIONS


if __name__ == "__main__":
    raise SystemExit(main())
