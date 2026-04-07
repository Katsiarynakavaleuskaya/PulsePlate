# PR #1372 — Fixed in Commit Mapping (SoT)

## Discussion Thread Pass

- [x] Discussion-thread pass completed (review threads dispositioned below; resolve on GitHub after verifying)
- [x] Fixed in commit mapping completed

Bot and human review threads must be dispositioned below when actionable comments appear; resolve conversations on GitHub after mapping per `AGENTS.md`.

## Fixed in Commit Mapping

### FIXED — staging rename rollback (tmp→dst fails after dst→bak)

**Disposition:** FIXED
**Commit:** `64d6cfc87dae80e2a155814beffb4bf8ad86e4ec`

**Evidence:**

- `scripts/orchestration/wiki_promote.py:89-105` (staging try/except + tmp cleanup)
- `tests/test_wiki_promote.py` — `test_promote_restores_prior_when_tmp_replace_fails_after_backup_created`
- `docs/orchestration/LOCAL_WIKI_SUPPORT_PLANE.md:44-51`

**Threads:**

- `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1372#discussion_r3048121855` -> `64d6cfc87dae80e2a155814beffb4bf8ad86e4ec`
- `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1372#discussion_r3048112342` -> `64d6cfc87dae80e2a155814beffb4bf8ad86e4ec`
- `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1372#discussion_r3048109717` -> `64d6cfc87dae80e2a155814beffb4bf8ad86e4ec`

### FIXED — redundant `dst.unlink` before `backup_path.replace(dst)` (SP + staging rollback)

**Disposition:** FIXED
**Commit:** `ad7246efaa6de2b005d95e5731e7b776524e10e3`

**Evidence:** `scripts/orchestration/wiki_promote.py` — rollback paths use `Path.replace` / `os.replace` overwrite semantics only (no prior `dst.unlink`).

**Threads:**

- `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1372#discussion_r3048131947` -> `ad7246efaa6de2b005d95e5731e7b776524e10e3`
- `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1372#discussion_r3048121866` -> `ad7246efaa6de2b005d95e5731e7b776524e10e3`

## Merge Readiness

- [ ] Current-head CI green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates

### Local verification

- Preflight: `python3 scripts/orchestration/check_preflight.py`
- Targeted: `pytest -q tests/test_wiki_promote.py tests/test_wiki_compiler_keys.py`
- Full: `make verify` before merge (repo policy)

## Deferred / Follow-ups

- Optional single-writer / locking for concurrent `promote` same slug: **DEFERRED** — traceability `docs/orchestration/LOCAL_WIKI_SUPPORT_PLANE.md` (two-phase / layout notes) and `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-local-workforce-pr-d-advisory-wiki-compiler` (Deferred / follow-ups). No separate issue opened in this PR.

**Thread (mapping doc nits):**

- `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1372#discussion_r3048131943` -> **DEFERRED** (backlog pointer above; no code change)
