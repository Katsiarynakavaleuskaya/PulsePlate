from __future__ import annotations

import argparse
import re
from pathlib import Path

PR_TBD_RE = re.compile(r"(?im)^\s*(?:[-*+]\s+)?(?:\*\*PR:\*\*|PR:)\s*TBD\b")
EVIDENCE_ANCHOR_RE = re.compile(
    r"(?:^|(?<=\s)|(?<=`)|(?<=\())"
    r"(?:"
    r"(?:\.github|docs|tests|app|core|scripts|frontend|ios|providers|deploy|alembic)"
    r"/[A-Za-z0-9_./-]+\.[A-Za-z0-9]+"
    r"|(?:AGENTS\.md|RUNBOOK_AGENT\.md|README\.md)"
    r"):\d+\b"
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read_text(relpath: str) -> str:
    return (REPO_ROOT / relpath).read_text(encoding="utf-8", errors="replace")


def _is_audit_path(relpath: str) -> bool:
    return relpath.startswith("docs/audit/") and relpath.endswith(".md")


def _is_security_or_audit_path(relpath: str) -> bool:
    return (
        relpath.startswith("docs/audit/") or relpath.startswith("docs/security/")
    ) and relpath.endswith(".md")


def check_docs_phase1_guards(markdown_files: list[str]) -> list[str]:
    errors: list[str] = []
    for relpath in markdown_files:
        fullpath = REPO_ROOT / relpath
        if not fullpath.exists():
            continue
        content = _read_text(relpath)

        if _is_audit_path(relpath) and PR_TBD_RE.search(content):
            errors.append(
                f"{relpath}: contains unresolved placeholder `PR: TBD` "
                "(replace with final PR number or commit SHA)."
            )

        if _is_security_or_audit_path(relpath) and not EVIDENCE_ANCHOR_RE.search(content):
            errors.append(
                f"{relpath}: missing `file:line` evidence anchor "
                "(example: `tests/test_repo_policy_guards.py:264`)."
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 1 docs quality gates.")
    parser.add_argument(
        "--files",
        nargs="*",
        default=[],
        help="Explicit markdown files to check (relative paths).",
    )
    args = parser.parse_args()

    markdown_files = [path for path in args.files if path]
    if not markdown_files:
        print("phase1-docs-gates: no markdown files provided; skipping.")
        return 0

    errors = check_docs_phase1_guards(markdown_files=markdown_files)
    if errors:
        print("ERROR: phase1 docs gates failed:")
        for item in errors:
            print(f"- {item}")
        return 1

    print("phase1-docs-gates: passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
