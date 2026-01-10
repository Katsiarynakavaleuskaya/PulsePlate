# PR-508: Risk Mitigations

**Date:** 2026-01-10
**Status:** Ready for merge

---

## Risk Mitigations

### 1) Environment Parity
- **Risk**: CI and local use different entrypoints, causing schema drift.
- **Mitigation**: Both CI and local use `make openapi` (same entrypoint, same PYTHONPATH, same env vars).
- **Verification**: `openapi-sync` job uses `make openapi`; determinism test verifies identical output.

### 2) Semantic List Sorting
- **Risk**: Normalization accidentally reorders semantically significant lists (e.g., `required`, `enum`, `allOf/anyOf/oneOf`).
- **Mitigation**: Explicit denylist (`_DO_NOT_SORT_LIST_KEYS`) prevents sorting of semantic keys.
- **Verification**: Determinism test ensures no drift; manual inspection confirms semantic keys preserved.

### 3) Determinism Verification
- **Risk**: OpenAPI artifacts drift without detection, breaking frontend builds.
- **Mitigation**: Determinism test (`pytest tests/test_openapi_determinism.py`) runs in CI and fails fast on drift.
- **Verification**: Test compares SHA256 hashes of `openapi.json` and `schema.ts` across two runs.

---

## Verification Checklist

- ✅ `make openapi` produces identical output across runs (verified by determinism test)
- ✅ Paths and schemas are sorted deterministically (verified by inspection)
- ✅ No dynamic date/sha in schema (verified: `info.version` is static `0.1.0`)
- ✅ Semantic list keys are preserved (denylist enforced)
- ✅ CI uses same entrypoint as local (`make openapi`)

---

**Ready for merge!** 🚀
