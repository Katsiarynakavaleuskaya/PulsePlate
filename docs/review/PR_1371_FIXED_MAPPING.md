# PR #1371 — Fixed in Commit Mapping (SoT)

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Bot and human review threads must be dispositioned below when actionable comments appear; resolve conversations on GitHub after mapping.

## Fixed in Commit Mapping

Disposition: FIXED

Commit: 11120d62b9ce12a47dcfe3de5c7ecc9348456b69

Evidence: `docs/orchestration/LOCAL_WIKI_SUPPORT_PLANE.md` (MD036: real `####` headings for In/Out scope); `scripts/orchestration/wiki_promote.py` (`reject_if_under_canonical_docs` before `promoted/` mkdir); `scripts/orchestration/wiki_ingest.py` (`validate_wiki_slug` after `path_to_slug`); `scripts/orchestration/wiki_lint.py` (64-char lowercase hex `content_hash` before raw filename); prior branch commits already cover external-wiki SP paths, promote `unlink` on SP failure, cross-run `slug_collision_existing`, and ingest best-effort SP semantics documented in LOCAL_WIKI.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1371#pullrequestreview-4070641652 -> 11120d62b9ce12a47dcfe3de5c7ecc9348456b69
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1371#pullrequestreview-4070678463 -> 11120d62b9ce12a47dcfe3de5c7ecc9348456b69
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1371#pullrequestreview-4070686110 -> 11120d62b9ce12a47dcfe3de5c7ecc9348456b69
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1371#pullrequestreview-4070759857 -> 11120d62b9ce12a47dcfe3de5c7ecc9348456b69
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1371#discussion_r3047331822 -> 11120d62b9ce12a47dcfe3de5c7ecc9348456b69
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1371#discussion_r3047331852 -> 11120d62b9ce12a47dcfe3de5c7ecc9348456b69
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1371#discussion_r3047331861 -> 11120d62b9ce12a47dcfe3de5c7ecc9348456b69
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1371#discussion_r3047339228 -> 11120d62b9ce12a47dcfe3de5c7ecc9348456b69
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1371#discussion_r3047339232 -> 11120d62b9ce12a47dcfe3de5c7ecc9348456b69
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1371#discussion_r3047339239 -> 11120d62b9ce12a47dcfe3de5c7ecc9348456b69
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1371#discussion_r3047339244 -> 11120d62b9ce12a47dcfe3de5c7ecc9348456b69
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1371#discussion_r3047400690 -> 11120d62b9ce12a47dcfe3de5c7ecc9348456b69

## Merge Readiness

- [ ] Current-head CI green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates

### Local verification

- Evidence: `make verify` on branch `feat/local-workforce-pr-d-advisory-wiki-compiler` before merge (operator-local)

## Agent pass register (plan steps 6–12)

| Step | Agent / gate | Result | Evidence |
|------|----------------|--------|----------|
| 2 | `check_preflight.py` + `check_agent_consistency.py` | PASS | Operator-local exit 0 |
| 6 | architecture-specialist | Addressed in code | Ingest now mirrors promote: `reject_if_under_canonical_docs` on corpus base (`wiki_ingest.py` + `wcs.reject_if_under_canonical_docs`); shared guard in `_wiki_compiler_support.py` |
| 7 | security-auditor | Addressed in code | `wiki_query.detail_page` calls `validate_wiki_slug`; slug length capped to 114 for `wiki.page.*` / `wiki.promoted.*` key budget (`MAX_WIKI_SLUG_CHARS`, `_WIKI_SLUG_RE`) |
| 8 | rag-systems / data-scientist / ml-engineer | Advisory N/A | No embeddings, vector, or model code in scope; ledger OUT unchanged |
| 11–12 | qa + bug-hunter bundle | `make verify` | Re-run after fixes; wiki tests: `pytest tests/test_wiki_*.py tests/test_wiki_compiler_keys.py` |
| follow-up | bug-hunter (ordering / `main` out) | Addressed in code | Promote: `dst.write_text` then `put_record`; `unlink` on SP failure; `main()` `out` via `path_for_support_plane_record` (wiki outside repo) |
| follow-up | qa (cross-run slug / external wiki SP path) | Addressed in code | Ingest: `slug_collision_existing` when existing page `source_rel_path` differs (`wiki_ingest.py`); tests `test_ingest_slug_collision_existing_across_runs`, `test_promote_support_plane_external_wiki_root` |
