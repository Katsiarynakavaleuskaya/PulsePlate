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

#### In scope

- Operator-local compiled memory under gitignored `artifacts/orchestration/wiki/`.
- Optional metadata keys `wiki.source.*`, `wiki.page.*`, `wiki.promoted.*` via `put_record`
  when `AGENT_CONTROL_ALLOWLIST` includes `local_support_plane:artifacts_kv` and execution
  mode allows mutations (see `app/security/agent_control_plane.py`).

#### Out of scope

- Canonical documentation under `docs/**`, root `AGENTS.md`, or `docs/roadmap/BACKLOG_LEDGER.md`
  — ingest and promote **fail closed** if the corpus base would resolve under `docs/`; neither tool edits those trees.
- Embeddings, vector databases, network retrieval, OpenAPI, `app/**`, or client runtimes.
- Replacing KPP, bootstrap packets, or orchestration SoT documents.

**Name this slice honestly:** it is an **advisory filesystem wiki compiler v1** (ingest → pages/raw/index,
read-only list/search/detail, integrity lint, guarded promote). It is **not** a full “compiled-memory
reasoning layer”, knowledge graph, index-first ranked retrieval, or semantic quality gate.

## Operational semantics (filesystem vs support plane)

| Surface | On support-plane write failure | Rationale |
|--------|---------------------------------|-----------|
| **Ingest** (`wiki_ingest.py`) | **Warn and continue** (`support_plane_skip:…` on stderr); filesystem writes (raw/page/index/log) already applied | Metadata mirror is best-effort; corpus on disk is the primary ingest artifact for v1. |
| **Promote** (`wiki_promote.py`) | **Fail closed:** if **filesystem staging** fails after `dst` was moved to `.bak`, the prior file is **restored** to visible `dst` and tmp is removed. If `put_record` fails after staging succeeds, the prior promoted file (if any) is **restored** from `.bak` when that backup exists; if there was no prior file, the new promoted file is **removed**. If a prior file existed but the backup is missing (race / concurrent promote), the new content on `dst` is **kept**. | Same non-destructive goal for SP errors and staging rename errors; avoids orphan promoted files without SP. |

Do **not** describe ingest as wholly fail-closed on support-plane mutations: only canonical-path and
on-disk errors abort the run; SP failures are warnings unless you treat stderr in your operator
pipeline as fatal.

Evidence: ingest SP catch — `scripts/orchestration/wiki_ingest.py:162`; promote atomic staging,
staging (`tmp`/`bak`), `put_record`, and rollbacks — `scripts/orchestration/wiki_promote.py:83`–`scripts/orchestration/wiki_promote.py:151`.

## v1 tool semantics (what the code actually does)

### `wiki_ingest.py`

- Sources must resolve **under `repo_root`** (`relative_to`); corpus base must not sit under
  canonical `docs/**` (`reject_if_under_canonical_docs`).
- **`--source` is not restricted to `.md`:** any file may be ingested; raw snapshot is always stored
  under `raw/<sha256>.md` (filename convention only). Content is decoded as UTF-8; invalid UTF-8 uses
  replacement + `utf8_replace:*` warning — suitable for **markdown-first** internal corpora, not a
  universal binary document pipeline.
- Page frontmatter is **narrow v1 integrity metadata** (`corpus`, `source_rel_path`, `content_hash`,
  `ingested_at`, `advisory`) — not a rich page schema or knowledge graph.

### `wiki_query.py`

- **Read-only** list / search / detail over filesystem pages.
- **Search** is **substring match on page body** (JSON wrapper); there is no index-first ranking,
  ranking, or embedding retrieval. `--include-context` is opt-in and only adds deterministic
  local hit context (`heading`, `excerpt`, `match_count`) to search results; default JSON output
  remains unchanged. Calling it a “query engine” in the sense of search products would be
  **overstated** — prefer “local grep-like search over ingested pages”.

### `wiki_lint.py`

- **Integrity lint:** `pages/` presence, required frontmatter keys, `advisory == true`, matching
  `raw/<hash>.md` for declared hash. PR-B3 also checks local `index.md` / page consistency and
  stale corpus-local links to missing `pages/<slug>.md` files. It does **not** enforce contradiction
  checks, backlinks, external URL validity, product truth, or semantic freshness.

### `wiki_promote.py`

- Promotion is **review-oriented:** slug validation, per-page lint gate, `reject_if_under_canonical_docs`
  on the promoted path, optional `put_record`.
- **Two-phase contract (v1):** the durable `promoted/<slug>.md` file is updated **before** `put_record`
  succeeds, so there can be a **short window** where disk reflects the new promote while the support-plane
  record is still old or missing; on `put_record` failure, rollback **restores** the prior promoted file
  when `.bak` exists, **removes** the new file when there was no prior, or **keeps** the new file on
  `dst` if a prior existed but the backup is missing (avoids deleting the only copy). If **filesystem
  staging** fails after `dst` was moved to `.bak` but before `tmp` becomes `dst`, the prior visible file
  is **restored** from `.bak` and the tmp file is cleaned up — same non-destructive goal as SP rollback.
  This is **not**
  a single atomic transaction across filesystem + SP — acceptable for local advisory tooling; avoid
  overlapping promotes for the same slug from multiple processes.
- Support-plane key **`wiki.promoted.<slug>` is a single slot:** each successful promote **overwrites**
  the prior record for that slug. **No versioned promotion history** in SP (filesystem `promoted/`
  holds the latest file only; historical SP audit is out of scope for v1).

### Slug collisions

- Ingest detects **same slug from two different source paths** in one run and fails with
  `slug_collision:…`.
- **Across separate ingest runs:** if `pages/<slug>.md` already exists, ingest reads prior
  `source_rel_path` from frontmatter; if it differs from the current source (or is missing),
  ingest fails with `slug_collision_existing:…` instead of silently overwriting.
- **Long slugs:** when the dot-joined base would exceed the support-plane slug budget
  (`scripts/orchestration/_wiki_compiler_support.py:119`), the slug keeps a truncated **head** plus a **stable hex suffix**
  derived from SHA-256 of the source relative path (POSIX), so distinct long paths normally map to
  distinct slugs. A theoretical collision remains possible if two paths produced the same suffix
  (extremely unlikely for the configured prefix length); treat as out of scope for v1 beyond
  deterministic tests in `tests/test_wiki_compiler_keys.py`.

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
python3 -m scripts.orchestration.wiki_ingest --source path/under/repo.md --corpus project_internal
python3 -m scripts.orchestration.wiki_query --mode list --corpus project_internal
python3 -m scripts.orchestration.wiki_query --mode search --needle foo --corpus project_internal
python3 -m scripts.orchestration.wiki_query --mode search --needle foo --include-context --corpus project_internal
python3 -m scripts.orchestration.wiki_query --mode detail --slug your.slug --corpus project_internal
python3 -m scripts.orchestration.wiki_lint --corpus project_internal
python3 -m scripts.orchestration.wiki_promote --slug your.slug --corpus project_internal
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
