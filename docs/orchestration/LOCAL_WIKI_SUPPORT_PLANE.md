# Local advisory wiki (support plane)

<!-- markdownlint-disable MD013 -->

This document describes the **advisory** local wiki compiler that sits on top of the
experimental local support plane (`scripts/orchestration/local_support_plane.py`).
It is **not** a second source of truth for product, orchestration, or contracts.

## Evidence anchors (implementation)

- Ingest / filesystem writes: `scripts/orchestration/wiki_ingest.py:1`
- Read-only query: `scripts/orchestration/wiki_query.py:1`
- Page lint: `scripts/orchestration/wiki_lint.py:1`
- Promote (filesystem + optional metadata): `scripts/orchestration/wiki_promote.py:1`
- Shared slug/hash helpers: `scripts/orchestration/_wiki_compiler_support.py:1`
- Support-plane policy gate: `scripts/orchestration/local_support_plane.py:105`
- Key validation: `scripts/orchestration/local_support_plane.py:58`

## Purpose and boundaries (IN / OUT)

**In scope**

- Operator-local compiled memory under gitignored `artifacts/orchestration/wiki/`.
- Optional metadata keys `wiki.source.*`, `wiki.page.*`, `wiki.promoted.*` via `put_record`
  when `AGENT_CONTROL_ALLOWLIST` includes `local_support_plane:artifacts_kv` and execution
  mode allows mutations (see `app/security/agent_control_plane.py`).

**Out of scope**

- Canonical documentation under `docs/**`, root `AGENTS.md`, or `docs/roadmap/BACKLOG_LEDGER.md`
  — the promote path **must not** resolve under `docs/`; ingest/promote never edit those trees.
- Embeddings, vector databases, network retrieval, OpenAPI, `app/**`, or client runtimes.
- Replacing KPP, bootstrap packets, or orchestration SoT documents.

## Directory layout

Default wiki root: `artifacts/orchestration/wiki/` (gitignored).

Per corpus (default name `project_internal`):

- `pages/` — markdown pages with YAML-style frontmatter (ingest output).
- `raw/` — raw snapshots named `<sha256>.md`.
- `promoted/` — copies after `wiki_promote.py` adds promotion metadata.
- `index.md` — regenerated listing of pages.
- `log.md` — append-only ingest log.

## CLI usage (from repo root)

```bash
python3 scripts/orchestration/wiki_ingest.py --source path/under/repo.md --corpus project_internal
python3 scripts/orchestration/wiki_query.py --mode list --corpus project_internal
python3 scripts/orchestration/wiki_query.py --mode search --needle foo --corpus project_internal
python3 scripts/orchestration/wiki_query.py --mode detail --slug your.slug --corpus project_internal
python3 scripts/orchestration/wiki_lint.py --corpus project_internal
python3 scripts/orchestration/wiki_promote.py --slug your.slug --corpus project_internal
```

Use `--no-write-support-plane` on ingest/promote when you only want filesystem artifacts.

## Support-plane keys

Keys must satisfy `normalize_key` (`^[a-zA-Z0-9][a-zA-Z0-9._-]*$`, max length 128). Slugs derived
from paths strip `.md` and sanitize path segments so keys remain valid (see tests in
`tests/test_wiki_compiler_keys.py`).

## Security notes

- Mutations use the same allowlist + execution-mode gate as `local_support_plane.put_record`
  (`scripts/orchestration/local_support_plane.py:105`).
- Treat wiki content as **non-secret** unless you explicitly classify sources; artifacts are
  local and gitignored but not encrypted by these tools.

## Related docs

- `docs/orchestration/AUTOMATION_READINESS_MATRIX.md` — automation readiness vs repo-only tools.
- `docs/security/AGENT_CONTROL_PLANE_SECURITY_BASELINE.md` — control-plane baseline.
- `scripts/AGENTS.md` — script-level conventions and support-plane note.
