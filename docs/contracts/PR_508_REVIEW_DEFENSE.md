# PR-508: Review Defense Plan

**Created:** 2026-01-10
**Target Review:** 2026-01-11
**Status:** Ready for review

---

## Scope & Invariants (for reviewers)

### ✅ What PR-508 does

1. **Fixes OpenAPI determinism**: `make openapi` now produces identical output across runs
2. **Fixes TypeScript type drift**: `schema.ts` is now deterministic
3. **Adds CI guardrails**: CI fails if generated artifacts are out of sync
4. **Establishes canonical generation path**: `scripts/generate_openapi.py` is single source of truth

### ⚠️ What PR-508 does NOT do (intentionally)

1. ❌ **Does NOT restore full schema** (premium/pro routers excluded in schema-only mode)
2. ❌ **Does NOT fix `unknown` types** in `schema.ts` (deferred to PR-509)
3. ❌ **Does NOT refactor import-time ORM deps** (deferred to PR-509)
4. ❌ **Does NOT add Pydantic response models** (deferred to PR-509)

**Why:** PR-508 is a **baseline/tooling PR**, not a full contract refactoring. Full schema restoration requires architectural changes (removing import-time ORM dependencies), which is out of scope.

---

## Expected Review Comments & Responses

### A) "Schema-only mode is a hidden API contract degradation"

**Reviewer concern:** OpenAPI schema is incomplete (missing premium/pro endpoints), frontend types are incomplete.

**Response:**
- This is **not production logic**, this is a **schema generation mode** to fix determinism
- Without this, OpenAPI generation **flaps** and CI **cannot guarantee contract** at all
- Schema-only mode is **explicitly marked** in OpenAPI schema:
  - `x-openapi-mode: "schema-only"`
  - `x-excluded-routers: ["premium_week", "pro"]`
  - Description includes warning about excluded routers
- Follow-up PR-509 will restore full schema after eliminating import-time ORM dependencies
- See `docs/contracts/PR_509_STUB.md` for detailed plan

**What we can do in PR-508 (if requested):**
- ✅ Already added: OpenAPI schema markers (`x-openapi-mode`, `x-excluded-routers`)
- ✅ Already added: Description warning about excluded routers
- ✅ Already documented: Follow-up PR-509 plan

---

### B) "Installing requirements.txt twice / non-canonical"

**Reviewer concern:** `python-setup` action should be source of truth, why duplicate installation?

**Response:**
- `python-setup` action installs `requirements.txt` **without constraints**
- OpenAPI generation requires **deterministic dependency resolution**
- Added step with `-c constraints.txt` ensures **reproducible builds**
- This is **intentional hardening**, not duplication
- `pip install` with `-c constraints.txt` is idempotent (safe to run twice)

**What we can do in PR-508 (if requested):**
- Update `python-setup` action to accept `constraints-file` parameter (but this is a separate PR to avoid scope creep)

---

### C) "Why `os.environ["X"]="..."` in generator is dirty"

**Reviewer concern:** Don't mutate environment inside script.

**Response:**
- We're fixing **deterministic build artifact**, not runtime behavior
- OpenAPI generation depends on feature flags/environment (routers conditionally register)
- Generator script must be **self-contained** and **repeatable**
- Environment variables are set **before** importing app (no side effects on runtime)

**What we can do in PR-508 (if requested):**
- Add CLI flags (`--openapi-mode schema-only`, `--env test`) and set env from CLI
- But this is "improvement" that can be done in follow-up PR

---

### D) "You updated workflow + secrets baseline in one PR"

**Reviewer concern:** This is "noise" - baseline should be separate.

**Response:**
- Baseline updated only due to `line_number` shift (added `openapi-sync` job)
- Otherwise CI/pre-commit **will fail** (baseline must match current state)
- This is **mechanically linked** change (cannot be separated)

**What we can do in PR-508 (if requested):**
- Commit reorder: baseline in same commit as `ci.yml` change (already done)

---

## What We Will NOT Do in PR-508

To avoid scope creep:

- ❌ **Will NOT** fix `unknown` types in `schema.ts` (PR-509)
- ❌ **Will NOT** restore premium/VIP routers in OpenAPI now (PR-509)
- ❌ **Will NOT** refactor SQLAlchemy import-time side effects now (PR-509)
- ❌ **Will NOT** change `python-setup` action architecture now (separate PR)

**Why:** PR-508 is "contract tooling stabilization", not "contract completeness". Full contract restoration requires architectural refactoring (PR-509).

---

## Review Response Strategy

### If review is "light" (only nits/docs)

- ✅ Add `x-openapi-mode` marker (already done)
- ✅ Fix wording in PR description/AGENTS.md
- ✅ Squash merge

### If review is "hard" (demand full schema restoration)

**Honest answer:** **No**, this is PR-509 scope.

In PR-508, we can only:
- ✅ Add guardrails: log/print "Excluded routers: premium_week, pro" (already done via schema markers)
- ✅ Add link to follow-up issue/PR-509 (already documented)
- ✅ Add CI check "ensure excluded routers list stable" (optional, can add if requested)

---

## Follow-up PR-509

**See:** `docs/contracts/PR_509_STUB.md` for detailed plan.

**Summary:**
- Remove import-time ORM dependencies from routers
- Add Pydantic response models for VIP/PRO endpoints
- Restore full schema generation
- Eliminate `unknown` types in `schema.ts`

---

## Pinned Comment for PR (GitHub)

```markdown
## Scope & Invariants

**This PR fixes OpenAPI determinism and establishes baseline contract tooling.**

### ✅ What this PR does:
- Fixes OpenAPI schema drift (deterministic generation)
- Fixes TypeScript type drift (deterministic schema.ts)
- Adds CI guardrails (fails on schema drift)
- Establishes canonical generation path

### ⚠️ What this PR does NOT do (intentionally):
- ❌ Does NOT restore full schema (premium/pro routers excluded in schema-only mode)
- ❌ Does NOT fix `unknown` types in schema.ts
- ❌ Does NOT refactor import-time ORM deps

**Why:** This is a baseline/tooling PR. Full schema restoration requires architectural refactoring (removing import-time ORM dependencies), which is deferred to PR-509.

### 📋 Follow-up:
- **PR-509:** Restore full schema generation (see `docs/contracts/PR_509_STUB.md`)

### 🔍 Schema-only mode:
- Explicitly marked in OpenAPI schema: `x-openapi-mode: "schema-only"`
- Excluded routers listed: `x-excluded-routers: ["premium_week", "pro"]`
- Description includes warning about excluded routers

**Please review scope and invariants before requesting full schema restoration.**
```

---

## Success Criteria

- ✅ OpenAPI generation is deterministic
- ✅ TypeScript type generation is deterministic
- ✅ CI fails if artifacts are out of sync
- ✅ Schema-only mode is explicitly marked and documented
- ✅ Follow-up PR-509 plan is documented

---

**Ready for review!** 🚀
