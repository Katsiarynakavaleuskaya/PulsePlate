# PR 1–50 Audit: Verification of Current Code State

**Date:** 2026-03-11
**Purpose:** Verify whether findings from bug-hunter and security-auditor audits are still present in production code or have been fixed.
**Evidence:** `grep`, `read_file`, current repo state

---

## Summary

| Finding | Status | In Prod? | Notes |
|---------|--------|----------|-------|
| BH-P0: test_llm_extras sys.modules | ❌ **Still present** | Test code (runs in CI) | Guard only enforces `tests/vip/**` |
| SA-P0-1: test_db_realistic SQL f-strings | ⚠️ **Mitigated** | Test code | `execute_query` not in core/db.py → ImportError → path never runs |
| SA-P0-2: test_sqlite_fk_integrity SQL interpolation | ❌ **Still present** | Test code | `f"PRAGMA foreign_key_list('{table}')"` line 27 |
| BH-P1: WeeklyPlanViewer error: any | ❌ **Still present** | **Production** | `frontend/src/features/plan/WeeklyPlanViewer.tsx:172,183,193,204` |
| BH-P1: ShoplistPreview as any | ❌ **Still present** | **Production** | `frontend/src/features/shoplist/ShoplistPreview.tsx:129` |
| BH-P1: test_api.py type hints | ❌ **Still present** | Test code | `def test_v1_health(client):` no type |
| SA-P1: run_coverage_tests subprocess | ❌ **Still present** | Dev script | No nosec B603 |
| BH-P2 / SA-P2: shareFile, GlassCard, ollama, etc. | ❌ **Still present** | Mixed | See details below |

---

## 1. P0 Findings — Current State

### 1.1 BH-P0: tests/test_llm_extras.py — sys.modules mutation

**Status:** ❌ **Still present**

**Evidence:**
```
tests/test_llm_extras.py:17,18  sys.modules[module_name] = module_obj
tests/test_llm_extras.py:27,29  sys.modules[module_name] = original; sys.modules.pop(module_name, None)
tests/test_llm_extras.py:36-38  del sys.modules["llm"]
```

**Guard scope:** `tests/test_repo_policy_sys_modules.py` enforces only `tests/vip/**/*.py`.
`test_llm_extras.py` is in `tests/` (not `tests/vip/`), so it is **not scanned** and the guard passes.

**In production:** Test code runs in CI; no direct production runtime impact, but violates tests/AGENTS.md policy.

**Verification triplet:**
Command:
```bash
sh -c 'git grep -n "sys.modules" tests/test_llm_extras.py; code=$?; printf "EXIT_CODE=%s\n" "$code"'
```
Output:
```text
tests/test_llm_extras.py:17:    sys.modules[module_name] = module_obj
tests/test_llm_extras.py:27:        sys.modules[module_name] = original
tests/test_llm_extras.py:29:        sys.modules.pop(module_name, None)
```
Exit code:
```text
0
```

---

### 1.2 SA-P0-1: tests/test_db_realistic_coverage.py — SQL f-strings

**Status:** ⚠️ **Mitigated (dead code path)**

**Evidence:**
- `core/db.py` does **not** export `execute_query` or `get_db_connection`.
- `tests/test_db_realistic_coverage.py:48` — `from core.db import execute_query, get_db_connection` → raises `ImportError`.
- Test catches `ImportError` and passes; the unsafe SQL branches are never executed.

**Risk:** If `execute_query` is added to `core/db.py` later, the vulnerable pattern would become active.

**Recommendation:** Remove or refactor the unsafe test block.

**Verification triplets:**
Command:
```bash
sh -c 'rg -n "execute_query|get_db_connection" core/db.py; code=$?; if [ "$code" -eq 1 ]; then echo "no matches"; fi; printf "EXIT_CODE=%s\n" "$code"'
```
Output:
```text
no matches
EXIT_CODE=1
```
Exit code:
```text
1
```

Command:
```bash
sh -c 'rg -n "execute_query|get_db_connection" tests/test_db_realistic_coverage.py | head -n 3; code=$?; printf "EXIT_CODE=%s\n" "$code"'
```
Output:
```text
23:            from core.db import get_db_connection
36:                        if conn := get_db_connection():
48:            from core.db import execute_query, get_db_connection
```
Exit code:
```text
0
```

---

### 1.3 SA-P0-2: tests/core/catalog/test_sqlite_fk_integrity.py — SQL interpolation

**Status:** ❌ **Still present**

**Evidence:**
```python
# tests/core/catalog/test_sqlite_fk_integrity.py:27
rows = conn.execute(f"PRAGMA foreign_key_list('{table}');").fetchall()
```

`table` comes from function parameter `_fk_targets(conn, table)`; caller is `test_sku_aliases_has_fk_region_id_to_regions_region_id` with fixture-controlled table names. **Low risk** (test-only, no user input).

**Verification triplet:**
Command:
```bash
sh -c 'rg -n "PRAGMA foreign_key_list" tests/core/catalog/test_sqlite_fk_integrity.py; code=$?; printf "EXIT_CODE=%s\n" "$code"'
```
Output:
```text
27:    rows = conn.execute(f"PRAGMA foreign_key_list('{table}');").fetchall()
```
Exit code:
```text
0
```

---

## 2. P1 Findings — Current State

### 2.1 BH-P1: WeeklyPlanViewer.tsx — error: any

**Status:** ❌ **Still present** | **Production code**

**Evidence:**
```
frontend/src/features/plan/WeeklyPlanViewer.tsx:172  } catch (error: any) {
frontend/src/features/plan/WeeklyPlanViewer.tsx:183  } catch (error: any) {
frontend/src/features/plan/WeeklyPlanViewer.tsx:193  } catch (error: any) {
frontend/src/features/plan/WeeklyPlanViewer.tsx:204  } catch (error: any) {
```

**Verification triplet:**
Command:
```bash
sh -c 'rg -n "error: any" frontend/src/features/plan/WeeklyPlanViewer.tsx; code=$?; printf "EXIT_CODE=%s\n" "$code"'
```
Output:
```text
172:    } catch (error: any) {
183:    } catch (error: any) {
193:    } catch (error: any) {
```
Exit code:
```text
0
```

---

### 2.2 BH-P1: ShoplistPreview.tsx — as any

**Status:** ❌ **Still present** | **Production code**

**Evidence:**
```
frontend/src/features/shoplist/ShoplistPreview.tsx:124-129
const revokeTimeout = setTimeout(() => { ... });
...
id: revokeTimeout as any,
```

**Verification triplet:**
Command:
```bash
sh -c 'rg -n "as any" frontend/src/features/shoplist/ShoplistPreview.tsx; code=$?; printf "EXIT_CODE=%s\n" "$code"'
```
Output:
```text
129:      id: revokeTimeout as any,
```
Exit code:
```text
0
```

---

### 2.3 BH-P1: tests/test_api.py — missing type hints

**Status:** ❌ **Still present**

**Evidence:** `def test_v1_health(client):` and similar — no `client: TestClient` type hint.

**Verification triplet:**
Command:
```bash
sh -c 'rg -n "def test_v1_health\\(client\\)|def test_.*\\(client\\):" tests/test_api.py; code=$?; printf "EXIT_CODE=%s\n" "$code"'
```
Output:
```text
14:def test_v1_health(client):
20:def test_v1_bmi_happy(client):
33:def test_v1_bmi_invalid_height(client):
```
Exit code:
```text
0
```

---

### 2.4 SA-P1: run_coverage_tests.py — subprocess without nosec

**Status:** ❌ **Still present**

**Evidence:**
```python
# run_coverage_tests.py:17
result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
```

No `# nosec B603`; `cmd` from hardcoded list with `sys.executable`. Dev-only script.

**Verification triplet:**
Command:
```bash
sh -c 'rg -n "subprocess.run" run_coverage_tests.py; code=$?; printf "EXIT_CODE=%s\n" "$code"'
```
Output:
```text
17:    result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
```
Exit code:
```text
0
```

---

## 3. P2 Findings — Current State

| File | Finding | Status |
|------|---------|--------|
| `ollama_diagnostic.sh` | jq, free -h | ❌ Present (script exists) |
| `ollama_monitor.sh` | bc -l | ❌ Present |
| `frontend/src/components/GlassCard.tsx` | Redundant undefined checks | ❌ Present |
| `frontend/src/lib/shareFile.ts` | No try/catch on anchor.click(); fallback dead code | ❌ Present |
| `scripts/orchestration/agent_run_summary.py` | SHA256 truncation for run IDs | Documented non-crypto; no fix needed |

---

## 4. Production Code Impact

**Findings that affect production code:**

1. **WeeklyPlanViewer.tsx** — `error: any` (4 catch blocks) → type safety
2. **ShoplistPreview.tsx** — `id: revokeTimeout as any` → type safety

**Findings in test/dev only:**

- test_llm_extras.py, test_db_realistic_coverage.py, test_sqlite_fk_integrity.py
- test_api.py
- run_coverage_tests.py
- shareFile.ts fallback (Node/test env only)
- GlassCard redundant checks
- Ollama scripts

---

## 5. Recommendations

### Immediate (production)

1. **WeeklyPlanViewer.tsx:** Replace `error: any` with `error: unknown` and use type guards.
2. **ShoplistPreview.tsx:** Replace `as any` with `ReturnType<typeof setTimeout>` or explicit `number` handling.

### Short-term (tests / policy)

1. **test_llm_extras.py:** Refactor to `monkeypatch` or add to sys.modules guard scope.
2. **test_db_realistic_coverage.py:** Remove or refactor the `execute_query` block (dead code).
3. **test_sqlite_fk_integrity.py:** Use parameterized PRAGMA or table allowlist.
4. **run_coverage_tests.py:** Add `# nosec B603` with justification.

### Backlog (P2)

- Ollama scripts: document jq/bc prerequisites
- shareFile.ts: optional try/catch, dead-code cleanup

---

## 6. Verification Commands

```bash
# Confirm sys.modules in test_llm_extras (not in vip/)
git grep -n "sys.modules" tests/test_llm_extras.py

# Confirm execute_query absent from core/db
git grep -n "execute_query\|get_db_connection" core/db.py

# Confirm error: any in production
git grep -n "error: any" frontend/src

# Confirm as any in ShoplistPreview
git grep -n "as any" frontend/src/features/shoplist/ShoplistPreview.tsx
```

---

*Verification performed 2026-03-11. Source: grep, file reads, guard test scope analysis.*
