# Security Audit: PulsePlate PRs 1–50 (Pre–Modern Security Gates)

**Audit date:** 11 March 2026
**Scope:** Merged PRs 1–50 and codebase state predating CodeQL, Bandit, Dependabot, RAG sanitizer, agent input guard, sandbox
**Method:** Repo scan + grep-based pattern search + Bandit-style review
**Worktree:** `worktrees/audit_pr1_50`

---

## 1. PR Inventory (Merged 1–50)

| PR | Merge SHA | Title |
|----|-----------|-------|
| 9 | 3063b8ac | Fix failing tests and update dependencies - finalize BMI app development |
| 13 | e07b09de | Fix BMI category translation inconsistencies and improve shell script quality |
| 14 | e5f4a6fa | fix: resolve Hypothesis fixture scope issue in property-based tests |
| 37 | 3d1e9f1f | deps(deps): bump fastapi from 0.116.1 to 0.117.1 |
| 41 | 101d3833 | deps(deps): bump uvicorn from 0.35.0 to 0.36.0 |
| 45 | a7c4c649 | ui: add Liquid Glass cards to weekly plan and shoplist |
| 50 | 31b42d30 | (merged; SHA may not exist in current history) |

**Note:** PRs 1–8, 10–12, 15–36, 38–40, 42–44, 46–49 are CLOSED (not merged). Only the above PRs were merged among 1–50.

---

## 2. Critical Vulnerabilities (P0)

### 2.1 [VULN-001] SQL injection risk in test coverage code

| Field | Value |
|-------|-------|
| **Location** | `tests/test_db_realistic_coverage.py:52-53`, `tests/test_db_realistic_coverage.py:201-208` |
| **Severity** | High (test code; may exercise production paths) |
| **Description** | F-strings with `fake.name()`, `fake.email()`, `fake.random_int()` passed to `execute_query()`. If `core.db.execute_query` exists and is reachable from production, this pattern could be replicated with user input. |
| **Evidence** | `tests/test_db_realistic_coverage.py:52` — `f"INSERT INTO users VALUES ('{fake.name()}', '{fake.email()}')"` |
| **Status** | Test-only; `execute_query`/`get_db_connection` not found in current `core/db.py`. If legacy, treat as dead code and remove. |
| **Fix** | Remove or refactor test to use parameterized queries; delete `execute_query` if unused. |

### 2.2 [VULN-002] SQL identifier interpolation in catalog test

| Field | Value |
|-------|-------|
| **Location** | `tests/core/catalog/test_sqlite_fk_integrity.py:27` |
| **Severity** | Low (test-only; table from fixture) |
| **Description** | `f"PRAGMA foreign_key_list('{table}');"` — table name interpolated. If `table` ever came from user input, SQL injection possible. |
| **Evidence** | `tests/core/catalog/test_sqlite_fk_integrity.py:27` |
| **Fix** | Use parameterized form or validate `table` against allowlist. |

---

## 3. High Vulnerabilities (P1)

### 3.1 [VULN-003] Subprocess calls without absolute path (Bandit B607)

| Field | Value |
|-------|-------|
| **Location** | `run_coverage_tests.py:17` |
| **Severity** | Medium |
| **Description** | `subprocess.run(cmd, ...)` with `cmd` from list. No `shutil.which()` for interpreter. Script is dev-only. |
| **Evidence** | `run_coverage_tests.py:17` — `result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())` |
| **Fix** | Use `shutil.which(sys.executable)` or document as dev-only and add nosec with justification. |

### 3.2 [VULN-004] Weak hashing for run IDs (SHA256 truncated)

| Field | Value |
|-------|-------|
| **Location** | `scripts/orchestration/agent_run_summary.py:48-50` |
| **Severity** | Low (non-cryptographic use) |
| **Description** | `_sha12()` uses SHA256 and truncates to 12 hex chars for deterministic run IDs. Not for passwords or signatures. |
| **Evidence** | `scripts/orchestration/agent_run_summary.py:48` — `return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]` |
| **Fix** | None required for run IDs; document as non-security use. |

---

## 4. Medium Vulnerabilities (P2)

### 4.1 [VULN-005] Test code with hardcoded secrets (intentional)

| Field | Value |
|-------|-------|
| **Location** | Multiple test files |
| **Severity** | Low (tests only) |
| **Description** | Tests use `api_key="test_key"`, `password="abc"`, `secret="test-secret"` with `# pragma: allowlist secret` or `# nosec B105`. |
| **Evidence** | `tests/test_signed_links.py:5,13,21,29`, `tests/test_integrated_bayesian_analyzer.py:105,160,186,230`, `tests/test_web_session_security.py:118,123` |
| **Fix** | Ensure all such usages have explicit allowlist/nosec and are test-only. |

### 4.2 [VULN-006] innerHTML usage in frontend

| Field | Value |
|-------|-------|
| **Location** | `frontend/src/features/progress/__tests__/ProgressCharts.test.tsx:92`, `docs/graph/viewer/app.js:169,177` |
| **Severity** | Low (test cleanup; docs viewer) |
| **Description** | `document.body.innerHTML = ''` in test; `typeFilter.innerHTML = ""` in docs viewer. Not user-controlled. |
| **Evidence** | `frontend/src/features/progress/__tests__/ProgressCharts.test.tsx:92`, `docs/graph/viewer/app.js:169` |
| **Fix** | Document as safe (no user input); avoid innerHTML for user content. |

### 4.3 [VULN-007] eval() in Bayesian analyzer tests

| Field | Value |
|-------|-------|
| **Location** | `tests/test_integrated_bayesian_analyzer.py:161,187`, `tests/test_comprehensive_bayesian_analyzer.py:177` |
| **Severity** | Low (tests only; exercises analyzer detection) |
| **Description** | `eval("dangerous")`, `eval("bad")`, `eval("malicious_code")` — intentional to test analyzer's unsafe-code detection. |
| **Evidence** | `tests/test_integrated_bayesian_analyzer.py:161` |
| **Fix** | None; tests are for detection logic. |

---

## 5. CORS and Auth

### 5.1 CORS configuration

| Component | Finding |
|-----------|---------|
| **worker.js** | `worker.js:100-104` — CORS uses `Access-Control-Allow-Origin: origin` where `origin` is validated against `WORKER_ALLOWED_ORIGINS`. No wildcard `*` in production path. |
| **Evidence** | `worker.js:131-134` — `parseAllowedOrigins(env.WORKER_ALLOWED_ORIGINS)` |
| **Verdict** | Acceptable; origin allowlist enforced. |

### 5.2 Auth bypass

- Tier guards (`require_pro_tier`, `require_vip_tier`) are enforced per `app/middleware/api_tiers.py`.
- No unguarded sensitive endpoints found in routers for `/api/v1/pro/*`, `/api/v1/vip/*`.
- Agent input guard and RAG sanitizer added in later PRs (#1018, #1044).

---

## 6. Subprocess and Command Injection

| File | Line | Pattern | Risk |
|------|------|---------|------|
| `app/security/execution_sandbox.py` | 418 | `subprocess.Popen` | Documented nosec B603; allowlisted binary, bounded argv |
| `scripts/orchestration/check_review_threads_disposition.py` | 80,127,152,174,444,554,598 | `subprocess.run` | Documented nosec B603; fixed argv |
| `scripts/orchestration/experiment_runner.py` | 214 | `subprocess.run` | Documented nosec B603 |
| `app/security/goplus_agentguard_bridge.py` | 61 | `subprocess.run` | Documented nosec B603 |
| `run_coverage_tests.py` | 17 | `subprocess.run` | No nosec; dev script; cmd from hardcoded list |

---

## 7. SQL and Injection Patterns

| File | Line | Pattern | Risk |
|------|------|---------|------|
| `core/rag/vector_rag.py` | 125,159 | f-string SQL with `where_clause` | nosec B608; where_clause from fixed predicates + bound params |
| `app/services/food_store.py` | 409,415,491,580,770 | `con.execute(sql, params)` | Parameterized |
| `app/services/restaurant_store.py` | 296,312,350,380,401 | `con.execute(...)` | Parameterized or fixed SQL |
| `app/services/recipe_store.py` | 144,166 | Parameterized | Safe |
| `tests/test_db_realistic_coverage.py` | 52-53,201-208 | f-string with fake data | See VULN-001 |

---

## 8. Information Disclosure

| Check | Result |
|-------|--------|
| Stack traces in production | No `traceback.print_exc()` or similar in app routers |
| Debug in prod | `TELEMETRY_CLIENT_DEBUG_FULL` gated; no `DEBUG=true` in prod path |
| PII in logs | No direct `log.info(request.body)` patterns in app |
| Error messages | FastAPI `HTTPException` used; no raw exception leakage in responses |

---

## 9. Rate Limit and PII

- Rate limiting: `@limit_if_available` on LLM and export endpoints per `app/security/rate_limit.py`.
- PII: No evidence of PII logged without redaction in app code.
- Agent input guard: `app/security/agent_input_guard.py` screens AI inputs (added post-PR50).

---

## 10. Recommendations

### Immediate (P0)

1. **VULN-001:** Confirm `execute_query`/`get_db_connection` status in `core/db.py`. If absent, remove or fix `tests/test_db_realistic_coverage.py` to avoid exercising unsafe patterns.
2. **VULN-002:** Refactor `test_sqlite_fk_integrity.py:27` to use parameterized PRAGMA or table allowlist.

### Short-term (P1)

1. **VULN-003:** Add `# nosec B603` with justification to `run_coverage_tests.py` or use `shutil.which()` for interpreter path.
2. Run `bandit -r app core` and `pip-audit` in CI; address any new findings.

### Long-term (P2)

1. Ensure all subprocess calls use absolute paths per `tests/guards/test_subprocess_uses_absolute_binaries.py`.
2. Keep RAG input sanitizer and agent input guard enabled; verify coverage for all AI entrypoints.

---

## 11. Verification Commands

```bash
# Reproduce PR list
gh pr view 9 --json state,mergedAt,mergeCommit,title
gh pr view 13 --json state,mergedAt,mergeCommit,title
# ... for 14, 37, 41, 45, 50

# Security scans
bandit -r app core -f json
pip-audit
pytest -q tests/test_repo_policy_guards.py
pytest -q tests/guards/test_subprocess_uses_absolute_binaries.py
```

---

## 12. Summary

| Severity | Count | Addressed by later PRs |
|----------|-------|------------------------|
| Critical (P0) | 2 | Partially (execute_query may be dead) |
| High (P1) | 2 | No |
| Medium (P2) | 3 | No (tests/docs) |

**Conclusion:** PRs 1–50 introduced foundational code before modern security gates. The main residual risks are in test/coverage code (SQL f-strings) and a dev script (subprocess). Production paths use parameterized SQL, tier guards, and documented subprocess patterns. RAG sanitizer, agent input guard, and sandbox were added in later PRs (#1018, #1044, #1013).
