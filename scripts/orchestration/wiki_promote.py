"""Promote a lint-clean wiki page into ``promoted/`` (+ optional support-plane record).

RU: Копия страницы в promoted/; канонические ``docs/**`` и AGENTS никогда не трогаем.
EN: Fail-closed if output would resolve under repo ``docs/`` (canonical tree).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Final

from app.security import agent_control_plane as cp

from scripts.orchestration import local_support_plane as lsp
from scripts.orchestration import _wiki_compiler_support as wcs
from scripts.orchestration import wiki_lint

EXIT_OK: Final[int] = 0
EXIT_LINT: Final[int] = 1
EXIT_USAGE: Final[int] = 2

_SLUG_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,119}$")


def validate_slug(slug: str) -> None:
    if not _SLUG_RE.match(slug) or ".." in slug:
        raise ValueError("slug_invalid")


def reject_if_under_canonical_docs(path: Path, *, repo_root: Path) -> None:
    """Block writes into ``docs/**`` (canonical documentation tree)."""

    resolved = path.resolve()
    docs_root = (repo_root / "docs").resolve()
    if not docs_root.is_dir():
        return
    try:
        resolved.relative_to(docs_root)
    except ValueError:
        return
    raise ValueError("promote_forbidden_under_canonical_docs")


def promote_slug(
    slug: str,
    *,
    corpus: str,
    wiki_root: Path,
    repo_root: Path,
    write_support_plane: bool,
    allowlist: set[tuple[str, str]] | None = None,
    sp_root_override: Path | None = None,
    audit_secret: str | None = None,
    audit_log_path: Path | str | None = None,
) -> Path:
    """Copy ``pages/<slug>.md`` to ``promoted/<slug>.md`` with promotion metadata."""

    validate_slug(slug)
    layout: dict[str, Path] = wcs.corpus_layout(wcs.corpus_base(wiki_root, corpus))
    violations = wiki_lint.lint_corpus(corpus=corpus, wiki_root=wiki_root, repo_root=repo_root)
    prefix = f"{slug}.md:"
    blocking = [v for v in violations if v == "pages_directory_missing" or v.startswith(prefix)]
    if blocking:
        raise ValueError(f"lint_blocked:{blocking}")

    src = layout["pages"] / f"{slug}.md"
    if not src.is_file():
        raise FileNotFoundError(f"missing_page:{slug}")
    promoted_dir: Path = layout["promoted"]
    promoted_dir.mkdir(parents=True, exist_ok=True)
    dst: Path = promoted_dir / f"{slug}.md"
    reject_if_under_canonical_docs(dst, repo_root=repo_root)
    try:
        dst.relative_to(layout["base"].resolve())
    except ValueError as exc:
        raise ValueError("promote_path_outside_corpus") from exc

    raw_text = src.read_text(encoding="utf-8")
    meta, body = wcs.parse_frontmatter(raw_text)
    promoted_at = wcs.utc_now_iso()
    meta = {
        **{str(k): str(v) for k, v in meta.items()},
        "promoted": "true",
        "promoted_at": promoted_at,
    }
    out_text = wcs.format_frontmatter(meta) + body
    dst.write_text(out_text, encoding="utf-8")

    if write_support_plane:
        active = allowlist if allowlist is not None else cp.load_allowlist_from_env()
        payload: dict[str, Any] = {
            "corpus": corpus,
            "slug": slug,
            "promoted_at": promoted_at,
            "promoted_path": dst.relative_to(repo_root.resolve()).as_posix(),
        }
        lsp.put_record(
            f"wiki.promoted.{slug}",
            payload,
            allowlist=active,
            repo_root=repo_root,
            root_override=sp_root_override,
            audit_secret=audit_secret,
            audit_log_path=audit_log_path,
        )
    return dst


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--slug", required=True)
    p.add_argument("--corpus", default="project_internal")
    p.add_argument("--wiki-root", type=Path, default=wcs.DEFAULT_WIKI_ROOT)
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument(
        "--write-support-plane",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = wcs.resolve_repo_root(args.repo_root)
    wiki_root = args.wiki_root
    if not wiki_root.is_absolute():
        wiki_root = (repo_root / wiki_root).resolve()
    try:
        out = promote_slug(
            args.slug,
            corpus=args.corpus,
            wiki_root=wiki_root,
            repo_root=repo_root,
            write_support_plane=args.write_support_plane,
        )
    except ValueError as exc:
        err = str(exc)
        if err.startswith("lint_blocked:"):
            print(json.dumps({"error": err, "ok": False}, sort_keys=True), file=sys.stderr)
            return EXIT_LINT
        print(json.dumps({"error": err, "ok": False}, sort_keys=True), file=sys.stderr)
        return EXIT_USAGE
    except FileNotFoundError as exc:
        print(json.dumps({"error": str(exc), "ok": False}, sort_keys=True), file=sys.stderr)
        return EXIT_USAGE
    except PermissionError as exc:
        print(json.dumps({"error": str(exc), "ok": False}, sort_keys=True), file=sys.stderr)
        return EXIT_USAGE
    print(
        json.dumps(
            {
                "ok": True,
                "out": out.relative_to(repo_root.resolve()).as_posix(),
            },
            sort_keys=True,
        )
    )
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
