# PR #1371 — Fixed in Commit Mapping (SoT)

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Bot and human review threads must be dispositioned below when actionable comments appear; resolve conversations on GitHub after mapping.

## Fixed in Commit Mapping

- No actionable review comments

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
