# PR 1–50 Bug Hunter Audit (2026-03)

**Audit date:** 2026-03-11
**Scope:** PulsePlate PRs 1–50 (merged before modern gates: pre-commit, guards, diff-cov, review disposition)
**Worktree:** `worktrees/audit_pr1_50` (branch `worktree/audit-pr1-50`)
**Evidence:** `gh pr view N`, `gh pr diff N`, `git grep` scans

---

## 1. Merged PRs 1–50

| PR | Title | Merged At |
|----|-------|-----------|
| 9 | Fix failing tests and update dependencies - finalize BMI app development | 2025-09-01 |
| 13 | Fix BMI category translation inconsistencies and improve shell script quality | 2025-09-01 |
| 14 | fix: resolve Hypothesis fixture scope issue in property-based tests | 2025-09-01 |
| 37 | deps(deps): bump fastapi from 0.116.1 to 0.117.1 | 2025-09-25 |
| 41 | deps(deps): bump uvicorn from 0.35.0 to 0.36.0 | 2025-09-25 |
| 45 | ui: add Liquid Glass cards to weekly plan and shoplist | 2025-09-25 |
| 47 | chore(frontend): add package.json for Vite + React + TS setup | 2025-09-25 |
| 48 | chore(frontend): add jsdom + testing-library and vitest config | 2025-09-25 |
| 49 | chore(frontend): add jsdom + testing-library and resolve package.json conflict | 2025-09-25 |
| 50 | chore(ci): add frontend vitest build job | 2025-09-27 |

**Note:** PR 9 `gh pr diff 9 --name-only` returned empty (squash/rebased); file list unavailable.

---

## 2. Files Changed (per merged PR)

| PR | Files |
|----|-------|
| 13 | `app.py` (→ `legacy_app.py`), `ollama_diagnostic.sh`, `ollama_monitor.sh`, `tests/test_api.py` |
| 14 | `.coveragerc`, `.github/*`, `tests/test_app_cover_extras.py`, `tests/test_llm_extras.py`, `tests/test_property_based.py`, `tests/test_providers_unit.py`, `providers/stub.py`, etc. |
| 37 | `requirements-all.txt` |
| 41 | `requirements-all.txt`, `requirements.txt` |
| 45 | `frontend/src/components/GlassCard.tsx`, `frontend/src/features/plan/WeeklyPlanViewer.tsx`, `frontend/src/features/shoplist/ShoplistPreview.tsx`, `frontend/src/index.css` |
| 47 | `frontend/package.json` |
| 48 | `frontend/package.json`, `frontend/package-lock.json`, `frontend/src/test/setup.ts`, `frontend/vite.config.ts` |
| 49 | `frontend/package-lock.json` |
| 50 | `frontend/src/lib/shareFile.ts`, `frontend/src/lib/shareFile.test.ts` |

---

## 3. Findings

| PR | Files | Finding | Severity | file:line |
|----|-------|---------|----------|-----------|
| 13 | ollama_diagnostic.sh | Uses `free -h` (Linux-only); macOS fallback `vm_stat` exists but `free` may fail on macOS | P2 | ollama_diagnostic.sh:64 |
| 13 | ollama_diagnostic.sh | Uses `jq` without existence check; fails if jq not installed | P2 | ollama_diagnostic.sh:24,34,53 |
| 13 | ollama_monitor.sh | Uses `bc -l`; `bc` not installed by default on macOS; fallback `\|\| echo "0"` masks failure | P2 | ollama_monitor.sh:35-37 |
| 13 | ollama_monitor.sh | `lsof -i :11434` may require elevated permissions on some systems | P2 | ollama_monitor.sh:27 |
| 13 | tests/test_api.py | `client` fixture used without type hint; violates tests/AGENTS.md type-hint policy | P1 | tests/test_api.py:15,21,34,... |
| 14 | tests/test_llm_extras.py | Mutates `sys.modules`; conflicts with tests/AGENTS.md "Do NOT mutate sys.modules" | P0 | tests/test_llm_extras.py:17,27,37 |
| 14 | tests/test_llm_extras.py | Uses `sys.modules.pop` in restore_module; same policy concern | P0 | tests/test_llm_extras.py:29 |
| 45 | frontend/src/components/GlassCard.tsx | Redundant `!== undefined` check for typed union `GlassCardTone`; defensive but redundant | P2 | frontend/src/components/GlassCard.tsx:59,65 |
| 45 | frontend/src/features/plan/WeeklyPlanViewer.tsx | `catch (error: any)` — should use `error: unknown` per TypeScript best practices | P1 | frontend/src/features/plan/WeeklyPlanViewer.tsx:171,182,203 |
| 45 | frontend/src/features/shoplist/ShoplistPreview.tsx | `id: revokeTimeout as any` — type assertion to bypass `number \| NodeJS.Timeout`; weakens type safety | P1 | frontend/src/features/shoplist/ShoplistPreview.tsx:127 |
| 45 | frontend/src/features/shoplist/ShoplistPreview.tsx | `cleanupRef` stores `id` as number but `setTimeout` return type varies by environment | P2 | frontend/src/features/shoplist/ShoplistPreview.tsx:126-129 |
| 50 | frontend/src/lib/shareFile.ts | `downloadInBrowser` has no try/catch around `anchor.click()`; edge-case failures unhandled | P2 | frontend/src/lib/shareFile.ts:31 |
| 50 | frontend/src/lib/shareFile.ts | `arrayBufferToBase64` fallback path (no FileReader) is unreachable in browser; dead code in Node test env | P2 | frontend/src/lib/shareFile.ts:59-74 |

---

## 4. Scan Results Summary

### 4.1 Import Hygiene

- **BMI math / thresholds:** No hardcoded BMI (18.5, 24.9, 25, 30) or waist (80, 88, 94, 102) in PR 1–50 touched files. Canonical sources: `core/bmi/engine.py`, `core/bmi/risk.py`.
- **sys.path / dynamic imports:** `tests/test_llm_extras.py` uses `sys.modules` mutation. Other PR-touched files are clean.

### 4.2 Dead Code / Unreachable Paths

- `frontend/src/lib/shareFile.ts` `arrayBufferToBase64` fallback (lines 59–74): Chunked base64 encoding when `FileReader` is unavailable — unreachable in browser; only relevant in Node/test environments.

### 4.3 Error Handling

- `frontend/src/features/plan/WeeklyPlanViewer.tsx`: Uses `error: any` in catch blocks; should use `unknown` and narrow.
- `ollama_diagnostic.sh`: No explicit handling if `curl` or `jq` fail.
- `frontend/src/lib/shareFile.ts`: `downloadInBrowser` does not wrap `anchor.click()` in try/catch.

### 4.4 SOLID / Code Quality

- `frontend/src/components/GlassCard.tsx`: Redundant undefined checks for typed props (minor).
- `frontend/src/features/shoplist/ShoplistPreview.tsx`: `as any` on `revokeTimeout` weakens type safety.

### 4.5 Test Gaps

- `tests/test_api.py`: No type hints on `client` parameter (violates tests/AGENTS.md).
- `GlassCard.test.tsx`: Uses `as any` for invalid tone/padding — acceptable for boundary testing.

---

## 5. Severity Legend

| Severity | Meaning |
|----------|---------|
| P0 | Blocking: policy violation, guard failure risk |
| P1 | High: type safety, error handling, or convention violation |
| P2 | Medium: portability, minor redundancy, edge cases |

---

## 6. Recommended Actions

1. **P0 (test_llm_extras):** Either add `test_llm_extras.py` to guard allowlist with documented rationale, or refactor to use `monkeypatch.setattr` / `patch()` instead of `sys.modules` mutation.
2. **P1 (frontend/src/features/plan/WeeklyPlanViewer.tsx):** Replace `error: any` with `error: unknown` and use type guards.
3. **P1 (frontend/src/features/shoplist/ShoplistPreview.tsx):** Use `ReturnType<typeof setTimeout>` or explicit `number` with env-specific handling instead of `as any`.
4. **P1 (test_api.py):** Add `client: TestClient` type hints to all test functions.
5. **P2 (ollama scripts):** Add `command -v jq` / `command -v bc` checks or document prerequisites.
6. **P2 (frontend/src/lib/shareFile.ts):** Consider removing or guarding the `arrayBufferToBase64` fallback; add try/catch around `anchor.click()` if desired.

---

## 7. Verification Commands

```bash
# Guard tests (must pass)
pytest -q tests/test_repo_policy_guards.py
pytest -q tests/test_repo_policy_sys_modules.py

# Import hygiene
git grep -nE "sys\.modules\[|sys\.path\.insert" tests/test_llm_extras.py

# BMI thresholds (should find none in PR-touched app/frontend)
git grep -nE "\b(18\.5|24\.9|25|30)\b" frontend/src --include="*.ts" --include="*.tsx"
```

---

*Audit performed by bug-hunter agent. Evidence: `gh pr view`, `gh pr diff`, `git grep`, file reads.*
