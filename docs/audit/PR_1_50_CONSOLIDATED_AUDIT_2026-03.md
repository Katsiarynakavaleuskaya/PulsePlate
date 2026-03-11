# Consolidated Audit: PRs 1–50 (Pre-Gates)

**Audit date:** 2026-03-11
**Scope:** PulsePlate PRs 1–50 (merged before modern gates)
**Worktree:** `worktrees/audit_pr1_50` (branch `worktree/audit-pr1-50`)
**Agents:** bug-hunter, security-auditor
**Sources:** `docs/audit/PR_1_50_BUG_HUNTER_AUDIT_2026-03.md`, `docs/audit/PR_1_50_SECURITY_AUDIT_2026-03.md`, `docs/audit/PR_1_50_AUDIT_STATUS_VERIFICATION_2026-03.md`

---

## 1. Merged PRs 1–50

| PR | Title | Merged | Type |
|----|-------|--------|------|
| 9 | Fix failing tests and update dependencies - finalize BMI app development | 2025-09-01 | App finalization |
| 13 | Fix BMI category translation inconsistencies and improve shell script quality | 2025-09-01 | i18n + scripts |
| 14 | fix: resolve Hypothesis fixture scope issue in property-based tests | 2025-09-01 | Tests |
| 37 | deps(deps): bump fastapi from 0.116.1 to 0.117.1 | 2025-09-25 | Deps |
| 41 | deps(deps): bump uvicorn from 0.35.0 to 0.36.0 | 2025-09-25 | Deps |
| 45 | ui: add Liquid Glass cards to weekly plan and shoplist | 2025-09-25 | Frontend |
| 47 | chore(frontend): add package.json for Vite + React + TS setup | 2025-09-25 | Frontend |
| 48 | chore(frontend): add jsdom + testing-library and vitest config | 2025-09-25 | Frontend |
| 49 | chore(frontend): add jsdom + testing-library and resolve package.json conflict | 2025-09-25 | Frontend |
| 50 | chore(ci): add frontend vitest build job | 2025-09-27 | CI |

**Note:** PRs 1–8, 10–12, 15–36, 38–40, 42–44, 46 were CLOSED (not merged).

---

## 2. P0 Findings (Blocking)

| ID | Source | Location | Finding | Fix |
|----|--------|----------|---------|-----|
| **BH-P0-1** | bug-hunter | `tests/test_llm_extras.py:17,27,37,29` | `sys.modules` mutation vs tests/AGENTS.md | Add allowlist or refactor to `monkeypatch` |
| **SA-P0-1** | security-auditor | `tests/test_db_realistic_coverage.py:52-53,201-208` | SQL f-strings with fake data; `execute_query` may be dead | Remove or use parameterized queries |
| **SA-P0-2** | security-auditor | `tests/core/catalog/test_sqlite_fk_integrity.py:27` | SQL identifier interpolation `f"PRAGMA foreign_key_list('{table}')"` | Parameterize or allowlist `table` |

---

## 3. P1 Findings (High)

| ID | Source | Location | Finding | Fix |
|----|--------|----------|---------|-----|
| **BH-P1-1** | bug-hunter | `WeeklyPlanViewer.tsx:171,182,203` | `catch (error: any)` — use `unknown` | Replace with `error: unknown` + type guard |
| **BH-P1-2** | bug-hunter | `ShoplistPreview.tsx:127` | `id: revokeTimeout as any` weakens type safety | Use `ReturnType<typeof setTimeout>` |
| **BH-P1-3** | bug-hunter | `tests/test_api.py` | Missing type hints on `client` | Add `client: TestClient` |
| **SA-P1-1** | security-auditor | `run_coverage_tests.py:17` | Subprocess without nosec/absolute path | Add nosec or `shutil.which()` |
| **SA-P1-2** | security-auditor | `agent_run_summary.py:48-50` | SHA256 truncation for run IDs | Document as non-crypto; no fix needed |

---

## 4. P2 Findings (Medium)

| ID | Source | Location | Finding |
|----|--------|----------|---------|
| **BH-P2-1** | bug-hunter | `ollama_diagnostic.sh` | `jq`, `free -h` — Linux-only; no existence check |
| **BH-P2-2** | bug-hunter | `ollama_monitor.sh` | `bc -l` not default on macOS |
| **BH-P2-3** | bug-hunter | `GlassCard.tsx:59,65` | Redundant undefined checks |
| **BH-P2-4** | bug-hunter | `shareFile.ts:31,59-74` | No try/catch on `anchor.click()`; unreachable fallback |
| **SA-P2-1** | security-auditor | Test files | Hardcoded secrets (allowlisted) |
| **SA-P2-2** | security-auditor | `ProgressCharts.test.tsx`, `docs/graph/viewer/app.js` | innerHTML (test/docs only) |
| **SA-P2-3** | security-auditor | Bayesian analyzer tests | eval() for detection tests |

---

## 5. Verified Safe

- **BMI math:** No hardcoded thresholds in PR-touched files
- **CORS:** `worker.js` uses `WORKER_ALLOWED_ORIGINS` allowlist
- **SQL (production):** `food_store`, `restaurant_store`, `recipe_store`, `vector_rag` — parameterized
- **Auth:** Tier guards on `/api/v1/pro/*`, `/api/v1/vip/*`
- **Information disclosure:** No stack traces or PII in logs

---

## 6. Recommended Actions

### Immediate (P0)

1. **test_llm_extras.py:** Refactor to `monkeypatch` or add guard allowlist with rationale
2. **test_db_realistic_coverage.py:** Confirm `execute_query` status; remove or refactor
3. **test_sqlite_fk_integrity.py:** Use parameterized PRAGMA or table allowlist

### Short-term (P1)

1. **WeeklyPlanViewer:** `error: unknown` + type guard
2. **ShoplistPreview:** Fix `revokeTimeout` typing
3. **test_api.py:** Add type hints
4. **run_coverage_tests.py:** Add nosec B603 or `shutil.which()`

### Backlog (P2)

1. Ollama scripts: document `jq`/`bc` prerequisites
2. shareFile.ts: optional try/catch, dead-code cleanup

---

## 7. Verification

```bash
pytest -q tests/test_repo_policy_guards.py
pytest -q tests/test_repo_policy_sys_modules.py
bandit -r app core -f json
```

## 8. Current State Verification Snapshot

- `docs/audit/PR_1_50_AUDIT_STATUS_VERIFICATION_2026-03.md` confirms the audit findings against the repository state as of `2026-03-11`.
- Production-impact items still present:
  - `frontend/src/features/plan/WeeklyPlanViewer.tsx:172`
  - `frontend/src/features/shoplist/ShoplistPreview.tsx:124`
- Test/dev-only items still present:
  - `tests/test_llm_extras.py:17`
  - `tests/core/catalog/test_sqlite_fk_integrity.py:27`
  - `run_coverage_tests.py:17`
- Mitigated / inactive path:
  - `tests/test_db_realistic_coverage.py:48` imports `execute_query` / `get_db_connection`, but `core/db.py` does not export them, so the unsafe SQL branch is currently inactive.

---

*Consolidated from bug-hunter and security-auditor outputs. Evidence: file:line.*
