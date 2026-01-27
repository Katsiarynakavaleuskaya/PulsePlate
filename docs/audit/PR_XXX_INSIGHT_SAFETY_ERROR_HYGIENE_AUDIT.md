## PR-0 — Insight Safety & Error Hygiene (P0)

**Status:** Draft (audit-first)
**Type:** Runtime PR (security/privacy fix)
**Owner:** @katsiaryna_kavaleuskaya
**Related ledger item:** `docs/roadmap/BACKLOG_LEDGER.md` → "P0 Audit Sweep: AI Insight — stop leaking provider exception details"

---

## Summary (intent)

P0 remediation for AI Insight endpoints:

- Remove **information leaks** in error responses for `/insight` and `/api/v1/insight`.
- Keep existing routing/tier behavior intact (no scope creep).
- Add tests that prove: **no `str(exc)` leaks to clients**.

---

## Product & Policy Decisions (frozen for this PR)

These are **canonical decisions** for this PR scope. Do not override without an explicit follow-up PR.

### A) Insight as product
- `/insight` is **user-facing FREE/PRO** for now.
- This PR does **not** change tier gates. Only safety/error hygiene.

### B) RAG philosophy
- RAG is treated as a **temporary prototype (v0)**.
- Users may see sources only as **redacted/anonymous IDs**, never filenames/paths.

### C) Providers
- **Pico is not required** for this PR; provider changes are out-of-scope except as needed for safe error handling tests.
- Runtime fallback between providers is **allowed**, but must be explicit/config-driven (not “magic”).

### D) GTM / Growth
- Insight is treated as **upgrade-hook (FREE → PRO)** (primary), and also retention value (secondary).
- Usage telemetry without PII is **allowed**, but is **scope-gated** (see section F).

---

## Audit Questions (required inputs)

### A) Contracts and surfaces
1) Which endpoints are involved?
   - `/insight`
   - `/api/v1/insight`
   - Any other aliases?

2) What HTTP status codes are returned today for provider errors?

3) Do legacy and v1 paths differ in contract (keys/status)?

### B) Current leaks (fact-finding)
4) Where is `str(exc)` used today?
   - ✅ `legacy_app.py:2490-2494` (`/api/v1/insight`)
   - ✅ `legacy_app.py:2533-2534` (`/insight`)

5) What exception types may leak? (provider/httpx/timeout/internal)

6) Does error payload leak any of:
   - provider name/model name
   - internal filenames/paths
   - stack fragments

### C) Logging (server-side)
7) Where are insight errors logged today?

8) Requirements:
   - ✅ log full exception server-side
   - ❌ do not log secrets / prompts / user input

### D) New error contract (proposal)
9) Target user-safe error payload shape:

```json
{
  "error": "INSIGHT_TEMPORARILY_UNAVAILABLE",
  "message": "Insight is temporarily unavailable. Please try again later."
}
```

10) Error classes: one code vs 2–3 classes (timeout/unavailable/internal)?

### E) Tests (mandatory)
11) Where do we write tests (unit + API)?

12) Minimal tests:
- provider failure → response does **not** contain `str(exc)`
- stable keys
- expected status code

### F) Telemetry (scope check)
13) Confirm scope:
- backend-only event emit (no frontend changes)
- no aggregation

14) Minimal event (if included in this PR):
- name: `insight_used`
- attrs: `result=success|failure`, `provider`, `latency_bucket`

If this expands scope → defer to next PR and record in ledger.

### G) Scope guard (hard)
15) This PR must **NOT**:
- change tier access
- refactor RAG (except no-leak safety constraints)
- change UX/copy
- change provider selection logic (except error hygiene needed for tests)

---

## Current Implementation Notes (evidence)

### Where the leak is today

- `/api/v1/insight` returns:
  - `detail=f"LLM provider error: {str(e)}"` at `legacy_app.py:2491-2494`
- `/insight` returns:
  - `detail=f"LLM provider error: {str(e)}"` at `legacy_app.py:2534`

### RAG usage in insight (context injection)

- When `FEATURE_RAG` is truthy, insight endpoints call:
  - `core.rag.simple_rag.retrieve_context(...)` and embed context into prompt
- Current RAG emits `# Source: <filename>` inside returned context (see `core/rag/simple_rag.py:121-123`).
  - **Note:** RAG safety boundary is a separate P0 PR (next in queue), but this PR must avoid introducing new leaks.

---

## Proposed Fix Plan (high-level)

1) Replace leaking error detail with stable message/code (privacy-safe).
2) Add server-side logging (`logger.exception`) without user input/prompt content.
3) Add tests for both endpoints:
   - simulate provider raising exception with a “sensitive-looking” message
   - assert response does not contain it
4) Verify gates: `make verify` (or at minimum: focused pytest + diff-cov in PR).

---

## Definition of Done (DoD)

- No `str(exc)` or provider internal details appear in HTTP responses for insight endpoints.
- Tests added and passing.
- No scope creep beyond safety/error hygiene.

---

## Implementation verification

**SHA:** `3ecf4a8e` (HEAD PR-611)

**Environment:** Python 3.13.6

**Note:** moved RAG redaction helper out of `legacy_app.py` into a canonical helper
(`core/insight/safety.py`) to keep legacy layer thin (AGENTS invariant).

### Commands

```bash
python -c "import legacy_app"
pytest -q tests/test_insight_error_hygiene.py
pytest -q tests/test_api.py -k "insight"
pytest -q tests/test_legacy_app_diff_coverage.py -k "insight"
make openapi-check
```

### Observed output (excerpt)

- `python -c "import legacy_app"` → exit 0
- `pytest -q tests/test_insight_error_hygiene.py` → `....` (4 passed)
- `pytest -q tests/test_api.py -k "insight"` → `s...` (skip + passes)
- `pytest -q tests/test_legacy_app_diff_coverage.py -k "insight"` → `....` (4 passed)
- `make openapi-check` → ✅ OpenAPI schema generated, no diff

**CI Status (final):**
- build: ✅ SUCCESS
- lint: ✅ SUCCESS
- diff-coverage: ✅ SUCCESS
- OpenAPI sync: ✅ SUCCESS
- tests: ✅ SUCCESS
- dependency submission: ✅ SUCCESS (initial failure was GitHub API flake, not related to PR changes; check is not required)
