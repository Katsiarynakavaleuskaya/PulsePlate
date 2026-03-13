# PulsePlate — Agent Runbook (CI Failures)

**Last updated:** 2025-12-24 (PR #403 Import Hygiene)

**What this is:** Quick reference for diagnosing CI failures and import hygiene regressions.
**When to use:** CI fails, tests hang, import errors, SQLAlchemy mapper issues.
**Related:** See root `AGENTS.md` for fast triage commands, `tests/test_repo_policy_guards.py` for enforced rules.

## Canonical Policy Links

- **Coordinator-first rule + definition of "task":** see `AGENTS.md` (Agent Coordination section)
- **Quality gates (procedure):** see `RUNBOOK_AGENT.md` (`## Quality Gates (Canonical)`)
- **Quality gate thresholds / policy:** see `AGENTS.md` (Hard Gates / Coverage rule sections)

---

## Agent Coordination (Automatic)

> Note: This section describes **operational** steps only. Policy/definitions live in `AGENTS.md`.

**When creating any task, the agent-coordinator should be automatically invoked.**

**Canonical workflow:** See `docs/orchestration/workflow.md`

**Templates (copy-paste ready):**
- Task Analysis: `docs/orchestration/task_analysis.template.md`
- Work Review: `docs/orchestration/work_review.template.md`
- Synthesis: `docs/orchestration/synthesis.template.md`
- DoD: `docs/orchestration/dod.template.md`

The coordinator will:
1. **Analyze the task** and identify which domain(s) it touches
2. **Route to appropriate agent(s)** based on capabilities:
   - `ai-innovation-specialist`: AI/ML, RAG, computer vision, research
   - `architecture-specialist`: Code structure, patterns, invariants
   - `bug-hunter`: Bugs, tests, quality gates, coverage
   - `creative-designer`: UI/UX, brand assets, visuals
   - `marketing-strategist`: ASO, growth, conversion, strategy
   - `security-auditor`: Vulnerabilities, penetration testing
3. **Coordinate multi-agent workflows** when tasks span domains
4. **Synthesize outputs** from multiple agents into coherent solutions
5. **Provide quality assurance** and final conclusions
6. **Generate brainstorming tasks** for scientific and creative innovation

**Usage:**
```text
Use the agent-coordinator subagent to [task description]
```

The coordinator will automatically delegate to specialized agents and synthesize their work.

**Starting a new task:**
- See canonical definition: `AGENTS.md` (Agent Coordination section)
- Templates: `docs/orchestration/*.template.md`
- Full workflow: `docs/orchestration/workflow.md`

**Postponed items:** Always record in `docs/roadmap/BACKLOG_LEDGER.md` immediately.

---

## Agent Orchestration Protocols

**Purpose:** Canonical protocols for multi-agent coordination.

**Location:** `docs/orchestration/`

### Protocol Index

| Protocol | Purpose | When to Use |
|----------|---------|-------------|
| [Task Evaluation Contract](docs/orchestration/AGENT_TASK_EVALUATION_CONTRACT.md) | Success criteria per task class | Every task (pass/fail criteria) |
| [Context Map](docs/orchestration/AGENT_CONTEXT_MAP.md) | Define which files each agent must load | Every task (Pre-flight Checklist) |
| [Capability Matrix](docs/orchestration/AGENT_CAPABILITY_MATRIX.md) | Agent routing guide (advisory) | Task assignment |
| [Handoff Protocol](docs/orchestration/AGENT_HANDOFF_PROTOCOL.md) | Sequential agent delegation | Multi-agent tasks (A → B → C) |
| [Dialogue Template](docs/orchestration/AGENT_DIALOGUE_TEMPLATE.md) | Multi-agent brainstorming | Multiple valid approaches |
| [Parallel Work Protocol](docs/orchestration/PARALLEL_WORK_PROTOCOL.md) | Parallel agent execution | Independent subtasks |

### Pre-flight Checklist (Canonical)

Canonical Pre-flight Checklist is defined only here:
`docs/orchestration/workflow.md` → “Canonical Pre-flight Checklist (SoT)”

Rule: RUNBOOK does not duplicate checklists; it only links to the canonical source.

---

### E2E Example: Multi-Agent Task

**Task:** “Implement RAG endpoint for VIP tier with frontend UI and tests”

**Execution (high-level):**

1. **Coordinator:** Pre-flight Checklist (load required `AGENTS.md`, contract docs, runbook)
2. **Track 1 (Backend):** Architecture + AI Innovation → endpoint + OpenAPI
3. **Track 2 (Frontend):** Creative Designer → UI component
4. **Track 3 (Tests):** Bug Hunter → contract tests + coverage
5. **Sync Points:** SP1 (OpenAPI ready), SP2 (UI ready), SP3 (tests green)
6. **Post-flight Verification:** all sync points passed; deliverables returned
7. **Synthesis:** coordinator merges tracks into one coherent outcome
8. **DoD:** verify quality gates + record postponements in `BACKLOG_LEDGER.md`

## Quality Gates (Canonical)

**Before merge, verify:**
- `make verify` green (lint → typecheck → test-fast → diff-cov)
- Guard tests pass (architectural invariants)
- Coverage / diff-coverage gates pass (see `AGENTS.md` for thresholds)
- Security scans pass when applicable (see `AGENTS.md` for policy and tools)

**This is the authoritative procedural checklist.** Thresholds/policy live in `AGENTS.md`.

## Guard Coverage Step (EVMbench-inspired)

**Purpose:** Ensure comprehensive coverage — address *all* related violations, not just one.

**When:** Before closing any guard/security PR.

**Steps:**

1. **Run full guard suite:**
   ```bash
   pytest -q tests/test_repo_policy_guards.py
   ```

2. **Confirm no related violations in changed modules:**
   - If PR touches `app/routers/`, verify no BMI math violations
   - If PR touches `core/`, verify no duplicate module patterns
   - If PR touches security config, verify Trivy/bandit pass

3. **Scope check:**
   - All violations of the same class should be fixed in this PR
   - If additional violations exist, either fix them or track in `BACKLOG_LEDGER.md`

4. **Route guard check for tiered surfaces:**
   - When a PR touches canonical `/api/v1/pro/*` or `/api/v1/vip/*` routing,
     run `pytest -q tests/test_pro_vip_route_dependency_guard.py`
   - This guard inspects the live `app.main.app` route table and fails on missing
     `require_pro_tier` / `require_vip_tier` coverage or undocumented alias drift.

**Rationale:** EVMbench scores on comprehensive coverage. Partial fixes (fix one, leave others) result in low scores and technical debt.

## Oracle / Known-Good Gate Behavior (EVMbench-inspired)

**Purpose:** Define expected behavior of quality gates on known-good input for deterministic validation.

**Rationale:** EVMbench uses logic/grading oracles to objectively evaluate agent success. For PulsePlate, our quality gates (`make verify`, guard tests, merge-readiness checks) serve as oracles. Documenting known-good behavior allows us to:
1. Validate gate implementations (gate passes on valid input)
2. Detect gate drift (gate fails on previously-passing input)
3. Establish baseline for agent evaluation (agent achieves "first-run pass" if gate passes without iteration)

### Known-Good Gate Specifications

| Gate | Known-Good Input | Expected Behavior | Evidence Anchor |
|------|------------------|-------------------|-----------------|
| `make verify` | Clean repo, all tests passing | Exit 0, no warnings | `Makefile:134` |
| `merge_readiness_gate` | PR with all checkboxes checked + valid commit mapping | Exit 0 | `scripts/ci/check_pr_merge_readiness.py:251` |
| `dependency_security_guard` | `requirements.txt` with all deps at floor versions, no blocked packages | Test passes | `tests/test_dependency_security_guard.py:1` |
| `pr_body_phase2_gates` | PR body with `[x]` checkboxes + `- No actionable review comments` | Exit 0 | `scripts/ci/check_pr_body_phase2_gates.py:107` |
| `guard_tests` | Codebase with no policy violations | All guards pass | `tests/test_repo_policy_guards.py:1` |

**Verification commands:**
- `make verify`: `make verify && echo "PASS"`
- `merge_readiness_gate`: `python scripts/ci/check_pr_merge_readiness.py --pr-number <N>`
- `dependency_security_guard`: `pytest -k dependency_security_guard -q`
- `pr_body_phase2_gates`: `python scripts/ci/check_pr_body_phase2_gates.py --body "..."`
- `guard_tests`: `pytest -q tests/test_repo_policy_guards.py`

### Gate Validation Protocol

When modifying a gate or its inputs:

1. **Baseline capture:** Run gate on known-good input, record exit code + output.
2. **Change implementation:** Make modification.
3. **Re-validate:** Run gate on same known-good input; must produce same result.
4. **Negative test:** Run gate on known-bad input; must produce expected failure.

**Known-bad input examples:**
- `merge_readiness_gate`: PR with unchecked boxes, unmapped bot comments
- `dependency_security_guard`: `requirements.txt` with blocked package (`cryptography==41.0.0`)
- `guard_tests`: Code with BMI math outside `core/bmi/`

## Minimal Agent Metrics (EVMbench-inspired)

**Purpose:** Define minimal metrics to evaluate agent task performance objectively.

**Rationale:** EVMbench evaluates agents on objective success rates. For PulsePlate agent workflows, we track:
1. **First-run pass rate** — did the agent get it right on the first attempt?
2. **Iteration count** — how many cycles to achieve green CI?
3. **Gate coverage** — did the agent address all violations or just one?

### Core Metrics

| Metric | Definition | Target | Evidence Anchor |
|--------|------------|--------|-----------------|
| **CI Fix: First-Run Pass** | PR passes `make verify` on first push | ≥70% | CI logs: first commit → green (`Makefile:134`) |
| **CI Fix: Iteration Limit** | Maximum pushes to achieve green CI | ≤3 | Git log: commit count on PR branch |
| **Merge Readiness: First-Run** | PR passes merge-readiness gate on first attempt | ≥50% | `scripts/ci/check_pr_merge_readiness.py:251` exit 0 |
| **Guard Coverage** | All violations of same class fixed in one PR | 100% | `tests/test_repo_policy_guards.py` after PR |
| **Docs Accuracy** | Documentation updates match code changes | 100% | Manual review + file anchors present |

### Metric Collection (Operational)

Metrics are captured from existing CI artifacts:

1. **First-run pass:** Compare first CI run status vs final merge status
2. **Iteration count:** Count commits on PR branch from open to merge
3. **Guard coverage:** Run guard suite before/after PR; compare violation counts

**Current tracking:** Manual (ledger notes). Future: automated dashboard (P2 backlog).

### Success Criteria per Task Class (Reference)

Full success criteria per task class are defined in:
`docs/orchestration/AGENT_TASK_EVALUATION_CONTRACT.md`

This metrics section provides **quantitative targets**; the evaluation contract provides **qualitative gates**.

## Pre-push hygiene checklist (mandatory)

## Clean-Clone Verify Parity

If `make verify` fails before the real code gates because the clean-clone `.venv`
is incomplete, use the canonical repo recovery path:

```bash
make venv
make verify
```

If `.venv` already exists but drift is suspected, refresh it from the locked
requirements before retrying:

```bash
make venv-sync
make verify
```

`make verify` now starts with `verify-env`, a non-mutating preflight that fails
fast when verify-critical modules such as `opentelemetry-*`, `flake8`,
`diff-cover`, `coverage`, `pytest`, or `mypy` are missing from `.venv`.

Run from repo root before any push/PR:

1. `git status --porcelain` → must be empty (or only intentional expected files)
2. `git ls-files worktrees | wc -l` → must be `0`
3. `git check-ignore -v worktrees/` → must show an ignore rule
4. `pre-commit run --all-files`
5. `make verify`

## PR operating lifecycle (mandatory for coordinator-led work)

Use this as the canonical operating loop from branch creation to merge window:

1. **Coordinator start**
   - Run `python3 scripts/orchestration/check_preflight.py`
   - Read `AGENTS.md`, `RUNBOOK_AGENT.md`, and the nearest scoped `AGENTS.md`
   - Decide scope, risk, and which sub-agents or helpers are needed before edits
2. **Open / maintain draft**
   - Keep the PR in draft while scope, artifact strategy, or local gates are still unstable
   - Create or confirm the canonical artifact path `docs/review/PR_<N>_FIXED_MAPPING.md`
3. **Before each push**
   - Run `pre-commit run --all-files`
   - Run the required local gates for the touched scope; for merge claims this still means `make verify`
   - Commit hook changes separately when hooks modify files
4. **After each push**
   - Watch the latest-head CI run, not stale `gh pr checks` history
   - Treat `scripts/orchestration/check_merge_ready.py` as the canonical current-head verdict
5. **After each new review / bot activity**
   - Fix code/docs first when needed
   - Update `docs/review/PR_<N>_FIXED_MAPPING.md` next
   - Update the optional PR-body mirror only after the canonical artifact is correct
   - Re-run merge-readiness checks; do not assume a previous pass still holds
6. **Before merge**
   - Re-run the strict merge wrapper after the latest bot/review activity
   - Confirm no pending required jobs remain
   - Wait one review cycle after the final green state

If any part of this loop is skipped, the PR must not be described as ready.

## Pre-merge readiness pass (mandatory for non-draft PRs)

Run before merge after latest commit and latest bot/review activity:

1. `python scripts/orchestration/check_merge_ready.py --pr-number <PR_NUMBER> --repo Katsiarynakavaleuskaya/PulsePlate --require-auth`
2. `gh pr view <PR_NUMBER> --json mergeStateStatus,reviewDecision,isDraft`
3. **Zero bot comments (hard rule):** Merge only when (a) **0 unresolved review threads** and (b) **every actionable bot comment is mapped** in the canonical artifact `docs/review/PR_<N>_FIXED_MAPPING.md`. PR body is mirror-only when `pr_number` is available. **Do not** report "0 comments" or "ready to merge" based only on unresolved thread count — new bot comments can appear after a check; use the canonical script (below) and re-run after bot activity.
4. When a human-readable PR-body mirror is kept, confirm these sections are complete:
   - `## Discussion Thread Pass`
   - `### Fixed in Commit Mapping`
   - `## Merge Readiness`
5. CI `Merge readiness gate` must be green on latest PR commit.

**Phase2 PR body gates (CI):** To pass `check_pr_body_phase2_gates.py` and merge-readiness:
- In PR description, if you keep a human-readable mirror, under **Discussion Thread Pass**: check `[x] Discussion-thread pass completed` and `[x] Fixed in commit mapping completed`.
- In the canonical artifact `docs/review/PR_<N>_FIXED_MAPPING.md`: list each bot comment as `- <comment-url> -> <commit-sha>` or `- <comment-url>` depending on disposition, or use exactly `- No actionable review comments`.
- Under **### Fixed in Commit Mapping** in the PR body: the mirror block is optional once the canonical artifact exists; if you keep it, generate it from the artifact helper instead of hand-maintaining mapping lines.
- Local artifact-first check: `python scripts/ci/check_pr_body_phase2_gates.py --pr-number <PR_NUMBER>`
- Local body-only fallback check: `python scripts/ci/check_pr_body_phase2_gates.py --body "$(cat .github/pr_body_*.md)"`

**Canonical verification (required before claiming "0 comments" or "ready to merge"):** Run the orchestration wrapper so Phase 2, merge-readiness, and disposition proof are checked together. Policy: see `docs/orchestration/COORDINATOR_MERGE_READINESS_RULES.md`.

```bash
# Local default: advisory disposition auth, strict PR API auth.
export GITHUB_TOKEN="..."
python scripts/orchestration/check_merge_ready.py \
  --pr-number <PR_NUMBER> \
  --repo Katsiarynakavaleuskaya/PulsePlate
```

```bash
# Local strict parity with CI for the disposition guard.
export GITHUB_TOKEN="..."
export GH_TOKEN="${GITHUB_TOKEN}"
python scripts/orchestration/check_merge_ready.py \
  --pr-number <PR_NUMBER> \
  --repo Katsiarynakavaleuskaya/PulsePlate \
  --require-auth
```
Exit 0 = Phase 2 + merge-readiness + disposition proof all pass. Exit 1 = do not merge; fix and re-run.

Raw `gh pr checks <PR_NUMBER>` remains diagnostic only. It can include superseded
historical failures from older runs, so final merge triage must rely on the
filtered current-head view emitted by `check_merge_ready.py`.

**Optional: unresolved thread count only** (not sufficient alone):

```bash
gh api graphql -f query='
query { repository(owner: "Katsiarynakavaleuskaya", name: "PulsePlate") {
  pullRequest(number: <PR_NUMBER>) {
    reviewThreads(first: 50) { totalCount nodes { id isResolved } }
  }
} }' --jq '.data.repository.pullRequest.reviewThreads | "total: \(.totalCount), unresolved: \([.nodes[] | select(.isResolved == false)] | length)"'
```

Before merge: `unresolved` must be `0`. Resolve all threads in GitHub UI (Conversation → resolve thread) and map any actionable bot comments in the canonical artifact.

**Loop until zero comments (canonical cycle):** Repeat until merge-readiness script exits 0 and CI is green:

1. **Commit** (fixes for code/docs); **push** to PR branch.
2. **Watch CI:** `gh run list --branch "$(git branch --show-current)" --limit 3` then `gh run watch <RUN_ID> --exit-status` (or wait for run completion).
3. **Check comments/governance:** `python scripts/orchestration/check_merge_ready.py --pr-number <PR_NUMBER> --repo Katsiarynakavaleuskaya/PulsePlate --require-auth`. If exit 1 → inspect the failing sub-gate output and fix before re-running.
4. **Fix:** Resolve each new review thread (GitHub UI or GraphQL `resolveReviewThread`); add every UNMAPPED comment URL to `docs/review/PR_<N>_FIXED_MAPPING.md`; if the bot asked for a code/docs change, implement it, commit, push, and use that commit sha in the mapping. Update the PR body mirror only after the canonical artifact is correct.
5. **Re-run** step 3. If exit 0 and CI green → zero comments; only then is the PR ready for merge per AGENTS.md.

Do not report "ready to merge" or "0 comments" until the script passes and CI is green.

## Agent Control Plane Security Ops (Wave 1 baseline)

Use this checklist when operating agent automation or closing a token/secrets incident.

**Detailed per-credential rotation protocols:** `docs/security/AGENT_CONTROL_PLANE_SECURITY_BASELINE.md` section "Credential Rotation Protocols" (R1-R5).

1. **Containment**
   - Stop agent runtime and disable auto-start service.
   - Quarantine local runtime state for forensics.
2. **Secrets rotation** (follow protocol R1-R5 per credential class)
   - R1: HMAC Audit Signing Key (`AGENT_CONTROL_AUDIT_SIGNING_KEY`)
   - R2: HMAC Broker Key (`AGENT_CONTROL_BROKER_HMAC_KEY`)
   - R3: Bot Tokens (GitHub App, Telegram, CI bots)
   - R4: API Provider Keys (LLM, external services)
   - R5: Webhook Secrets
   - For each: generate new → update secret store → restart → verify → revoke old → confirm revoked.
   - Reset webhook endpoints and confirm `getWebhookInfo` reports empty/expected URL.
3. **Verification**
   - Ensure no active runtime process/socket remains for disabled agent service.
   - Confirm privileged automation path is routed through policy gate only.
   - Run canonical security verification (see baseline doc, section "Canonical Security Verification").
4. **Documentation**
   - Record evidence and follow-ups in `docs/roadmap/BACKLOG_LEDGER.md`.
   - Keep controls aligned with `docs/security/AGENT_CONTROL_PLANE_SECURITY_BASELINE.md`.
   - Verify security release gate conditions pass (see baseline doc, section "Security Release Gate").
## 0.1) CI: `actions/upload-artifact` fails with `FinalizeArtifact 403 Forbidden`

**Reference:** Documentation: [PR #712](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/712). Fix required a
repo-admin setting change (`default_workflow_permissions=write`; no repo commit).

**Symptom (GitHub Actions logs):**

- `Error: Failed to FinalizeArtifact: ... (403) Forbidden`
- often in steps like “Upload JUnit test report” / “Upload coverage artifact”

**Likely cause:** repository-level **default** workflow token permissions were set to `read`, which can break artifact
finalization even when the byte upload succeeded.

**Check (repo setting):**

```bash
gh api repos/<OWNER>/<REPO>/actions/permissions/workflow
```

Expected (for this repo’s CI, which uploads/downloads artifacts):

```json
{"default_workflow_permissions":"write", ...}
```

**Fix (requires repo admin):**

**Scope note:** changing repository-level `default_workflow_permissions` affects **all workflows** in this repository.
Coordinate with repo owners / security if needed before changing the default.

**Reference docs:** GitHub Actions `GITHUB_TOKEN` permissions:
`https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication`

```bash
gh api -X PUT repos/<OWNER>/<REPO>/actions/permissions/workflow -f default_workflow_permissions=write
```

**Also verify workflow/job permissions:** the job that uploads artifacts should request `actions: write`.
(Example: in CI workflows, see job-level `permissions:` blocks for test jobs.)

**Post-fix:** re-run the failed workflow run (`gh run rerun <RUN_ID> --failed`) and confirm artifact steps pass.

## 0) Golden Rule

Before editing imports / `__init__` / sys.path / sys.modules:
**Run guard checks first.** If guards fail, fix the policy violation before anything else.

## 1) Fast Local Triage (run from repo root)

```bash
make lint
make test-fast
pytest -q tests/test_repo_policy_guards.py
```

## 2) PR #403 Specific Checks (Import Hygiene)

### 2.0 SQLAlchemy Model Registration (WeeklyPlan/DayPlan not found)

**Problem:** `expression 'WeeklyPlan' failed to locate a name` → model not registered in ORM.

**A. Where classes are declared:**

```bash
rg -n "class WeeklyPlan\b|class DayPlan\b" app/models -S
```

**B. Where DayPlan references WeeklyPlan:**

```bash
rg -n "relationship\(\s*[\"']WeeklyPlan[\"']" app/models -S
rg -n "Mapped\[[\"']WeeklyPlan" app/models -S
```

**C. Model exports (CRITICAL - must export both classes):**

```bash
rg -n "from app\.models\.plans import|from \.plans import" app/models -S
sed -n '1,200p' app/models/__init__.py 2>/dev/null || true
```

**D. Who imports models at startup:**

```bash
rg -n "import app\.models|from app\.models import|import models" app legacy_app.py app/main.py core -S
```

**Fix pattern:**
- Keep `WeeklyPlan` and `DayPlan` in same module with `WeeklyPlan` declared **before** `DayPlan`
- Export both from `app/models/__init__.py`:
  ```python
  from .plans import WeeklyPlan, DayPlan  # noqa: F401
  __all__ = [..., "WeeklyPlan", "DayPlan"]
  ```
- Ensure startup imports `app.models` package (not individual modules)

### 2.1 Import hygiene regressions (dynamic import / exec_module)

**Problem:** `spec_from_file_location / exec_module` returns → Dual Base + Pydantic TypeAdapter issues.

```bash
git grep -nE "spec_from_file_location|module_from_spec|exec_module\(" -- app core tests
```

**Offender list (excluding whitelisted script tests):**

```bash
git grep -nE "spec_from_file_location|module_from_spec|exec_module\(" -- tests \
  | grep -vE "test_test_pro_access_coverage\.py|test_ensure_database_versions\.py|conftest\.py"
```

### 2.2 sys.path.insert in tests (masks import path bugs)

**Problem:** Breaks xdist isolation, hides real import errors.

```bash
git grep -n "sys\.path\.insert" -- tests
```

**Exclude allowlist (conftest + guards):**

```bash
git grep -n "sys\.path\.insert" -- tests \
  | grep -vE "tests/conftest\.py|tests/test_test_pro_access_coverage\.py|tests/test_import_hygiene_guard\.py|tests/test_repo_policy_guards\.py"
```

### 2.3 sys.modules mutation (main source of Dual Base)

**Problem:** `sys.modules["x"]=...` and `del sys.modules["x"]` create separate namespaces.

```bash
git grep -nE "sys\.modules\[[^]]+\]\s*=|del\s+sys\.modules\[" -- .
```

**Only in tests:**

```bash
git grep -nE "sys\.modules\[[^]]+\]\s*=|del\s+sys\.modules\[" -- tests
```

### 2.4 Public surface app package (missing attributes)

**Problem:** Tests fail with:
- `module 'app' has no attribute build_nutrition_targets`
- `... get_update_scheduler`
- `... resolve_attr`

**Check what tests expect from app:**

```bash
git grep -nE "from app import |app\.(resolve_attr|build_nutrition_targets|get_update_scheduler|make_weekly_menu)" -- tests
```

**Verify what's actually exported:**

```bash
sed -n '1,200p' app/__init__.py
```

**Run surface guard tests:**

```bash
pytest -q tests/test_app_public_surface.py
pytest -q -k "public_surface or env_guards or import_hygiene"
```

### 2.5 ENV gating / порядок установки TESTING

**Problem:** `EXPORTS_ENABLED`/`VIP` computed at import time, env set later → tests get 404/422.

```bash
git grep -nE "EXPORTS_ENABLED|VIP_ENABLED|TESTING|DEBUG" -- app legacy_app.py core tests
```

**Check pytest_configure:**

```bash
git grep -n "os\.environ\[" -- tests/conftest.py
git grep -n "pytest_configure" -- tests/conftest.py
```

### 2.6 Recipe store tests (_con missing)

**Problem:** `module 'recipe_store' has no attribute '_con'` - symptom of wrong module import path.

**Anti-pattern check:**

```bash
git grep -n "sys\.modules\.get\(\"recipe_store\"\)" tests
git grep -nE "spec_from_file_location\(\"recipe_store\"" tests
```

**Correct pattern:**
- ❌ Don't: `sys.modules.get("recipe_store")`
- ✅ Do: `import app.services.recipe_store as rs`

**Verify import works:**

```bash
python -c "import app.services.recipe_store as rs; print(hasattr(rs,'_con'), rs._con)"
```

### 2.7 VIP router 422 vs 404

**Problem:** Router registered but disabled by logic → 422/401 instead of 404.

```bash
git grep -nE "include_router\(.*vip|VIP|vip_router" app
git grep -nE "VIP_ENABLED|VIP_MODULE_ENABLED|FEATURE_VIP" app core legacy_app.py
```

### 2.8 Docker build (COPY app.py not found / entrypoint drift)

**Problem:** Dockerfile copies `app.py` but file was renamed/moved.

```bash
rg -n "COPY .*app\.py|COPY .*legacy_app\.py" Dockerfile
rg -n "uvicorn\s+app(:|\.main:app)|legacy_app" Dockerfile Makefile docker-compose.yaml -S
```

**Check entrypoint matches canonical:**

```bash
rg -n "app\.main:app" Dockerfile Makefile docker-compose.yaml -S
```

**Expected:** `app.main:app` (current canonical entrypoint, not `legacy_app:app`).

### 2.9 Fast triage - top failure patterns

**When CI shows many failures, extract first 50:**

```bash
pytest -q --maxfail=50
```

**Build error frequency histogram:**

```bash
pytest -q --maxfail=200 2>&1 | rg -o "E\s+[A-Za-z_]+Error|sqlalchemy\.[A-Za-z_]+" | sort | uniq -c | sort -nr | head -30
```

This reveals patterns like:
- `NoForeignKeysError` → model relationship issue
- `InvalidRequestError: Table already defined` → duplicate model registration
- `AttributeError: module 'app' has no attribute` → missing public surface export

---

## 3) If LINT Fails

### 3.1 Ruff / formatting

```bash
ruff check . --fix
black .
```

### 3.2 Explain-only (to see the real errors)

```bash
ruff check . -v
```

## 4) If TESTS Fail

### 4.1 Narrow first

```bash
pytest -q -k "<failing_test_name_or_keyword>"
pytest -q tests/<path_to_file>.py
```

### 4.2 Import hygiene suspects

See section 2 (PR #403 Specific Checks) above for detailed grep commands.

### 4.3 ENV gating suspects (exports/vip)

```bash
git grep -n "EXPORTS_ENABLED|VIP_ENABLED|TESTING|DEBUG"
```

Ensure `TESTING=true` is set before importing `legacy_app`.

## 5) If DOCKER Build Fails

See section 2.8 above for Docker-specific checks.

## 6) If COVERAGE Guard Fails

### 6.1 Identify uncovered lines

```bash
pytest --cov --cov-report=term-missing
```

Then add micro-tests for uncovered branches (avoid flaky tests).

## 7) If xdist Hangs / Mapper / Dual Base Symptoms

### 7.1 Confirm no dynamic loader

```bash
pytest -q tests/test_repo_policy_guards.py
```

### 7.2 Confirm single Base identity (if guard exists)

```bash
pytest -q -k "single_base or import_hygiene"
```

## 8) What NOT to Do (Hard Rules)

- Never mock `builtins.__import__` or `builtins.float`
- Never mutate `sys.modules` in tests
- Never reintroduce `exec_module` / dynamic import patterns
- No network calls in unit tests (use `providers/stub.py`)

## 9) Import Hygiene Checklist (Before Any PR)

See `AGENTS.md` for the full checklist. Quick version:

1. No dynamic imports (except whitelisted test files)
2. No `sys.path.insert` (except whitelisted test files)
3. No `sys.modules` mutations
4. Verify PEP 562 shim in `app/__init__.py`
5. `TESTING=true` set before app import
6. Guard tests pass
7. Export routes registered when feature-flagged

## 10) Common CI Failure Patterns

### Pattern: "ModuleNotFoundError: No module named 'app'"

**Cause**: Import path broken, likely due to `sys.path` manipulation or missing `__init__.py`.

**Fix**:
```bash
# Check package structure
find app core -name "__init__.py"

# Verify imports use package paths
git grep -n "from app import" tests
```

### Pattern: "Multiple mapper registry conflicts"

**Cause**: Dual Base - models importing different `Base` instances.

**Fix**:
```bash
# Run Dual Base guard
pytest -q -k "single_base"

# Check all models import from core.db
git grep -n "from core.db import Base" app/models core
```

### Pattern: "pytest hangs on teardown"

**Cause**: Background threads/processes not cleaned up (common in coverage-smoke tests).

**Fix**: Exclude heavy import tests from xdist:
```python
# In conftest.py or pyproject.toml
# Mark tests: @pytest.mark.no_xdist
```

## 11) Emergency: Revert to Known Good State

```bash
# Check last green CI commit
git log --oneline -20

# Soft reset to that commit
git reset --soft <commit-sha>

# Review changes
git diff HEAD
```
