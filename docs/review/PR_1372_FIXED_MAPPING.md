# PR #1372 — Fixed in Commit Mapping (SoT)

## Discussion Thread Pass

- [x] Discussion-thread pass completed (staging-gap addressed in code; paste exact GitHub discussion URLs into the mapping line below, then resolve threads)
- [x] Fixed in commit mapping completed for staging rollback item

Bot and human review threads must be dispositioned below when actionable comments appear; resolve conversations on GitHub after mapping per `AGENTS.md`.

## Fixed in Commit Mapping

### FIXED — staging rename rollback (tmp→dst fails after dst→bak)

**Disposition:** FIXED
**Commit:** `64d6cfc87dae80e2a155814beffb4bf8ad86e4ec`

**Evidence:**

- `scripts/orchestration/wiki_promote.py:89-107`
- `tests/test_wiki_promote.py` — `test_promote_restores_prior_when_tmp_replace_fails_after_backup_created`
- `docs/orchestration/LOCAL_WIKI_SUPPORT_PLANE.md:44-51` (promote fail-closed row + evidence span)

**Thread mapping (replace placeholder with your PR review conversation URL):**

- `- <PR_1372_inline_review_thread_url> -> 64d6cfc87dae80e2a155814beffb4bf8ad86e4ec`

## Merge Readiness

- [ ] Current-head CI green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates

### Local verification

- Preflight: `python3 scripts/orchestration/check_preflight.py`
- Targeted: `pytest -q tests/test_wiki_promote.py tests/test_wiki_compiler_keys.py`
- Full: `make verify` before merge (repo policy)

## Deferred / Follow-ups

- Optional backlog: single-writer / locking for concurrent `promote` same slug (see `LOCAL_WIKI_SUPPORT_PLANE.md`).
