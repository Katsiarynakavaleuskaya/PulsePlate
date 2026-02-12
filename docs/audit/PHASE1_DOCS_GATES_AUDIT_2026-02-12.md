# Phase1 Docs Gates Audit (2026-02-12)

**Date:** 2026-02-12
**Scope:** PR hygiene hardening (Phase 1):
`PR: TBD` blocker, `file:line` evidence gate,
markdownlint on changed markdown
**PR:** in-progress branch `fix/phase1-docs-auto-gates`

---

## Task analysis and brainstorming

Coordinator-first orchestration was used before implementation.

- Coordinator task analysis: `docs/orchestration/task_analysis.template.md:1`
- Workflow reference: `docs/orchestration/workflow.md:1`
- Guard policy context: `AGENTS.md:1`

Applied specialist perspectives:

- `architecture-specialist`: minimal-risk placement in `scripts/ci/` + CI wiring
- `bug-hunter`: false-positive/false-negative risk review and
  deterministic test cases

---

## Implemented controls

1. **Gate A: block unresolved `PR: TBD` in changed `docs/audit/*.md`**
   - Regex policy and gate logic: `scripts/ci/check_docs_phase1_gates.py:8`
   - Gate execution function: `scripts/ci/check_docs_phase1_gates.py:50`

2. **Gate B: require `file:line` evidence anchors in changed docs under
   `docs/audit/` and `docs/security/`**
   - Anchor matcher: `scripts/ci/check_docs_phase1_gates.py:9`
   - Enforcement branch: `scripts/ci/check_docs_phase1_gates.py:64`

3. **Gate C: markdownlint on changed `.md` files only**
   - Changed-file resolver in CI step: `.github/workflows/ci.yml:140`
   - `markdownlint-cli2` invocation in CI step: `.github/workflows/ci.yml:148`

4. **CI integration**
   - New CI job: `.github/workflows/ci.yml:110`
   - Execution step: `.github/workflows/ci.yml:134`

5. **Deterministic tests**
   - Guard tests: `tests/test_docs_phase1_gates.py:12`
   - Missing-anchor negative path: `tests/test_docs_phase1_gates.py:24`
   - Valid-anchor positive path: `tests/test_docs_phase1_gates.py:36`

---

## Local verification evidence

### Command 1

```bash
pytest -q tests/test_docs_phase1_gates.py
```

### Raw output 1 (excerpt)

```text
...                                                                      [100%]
```

Exit code: `0`

### Command 2

```bash
python scripts/ci/check_docs_phase1_gates.py --files docs/audit/PHASE1_DOCS_GATES_AUDIT_2026-02-12.md
```

### Raw output 2 (excerpt)

```text
phase1-docs-gates: passed.
```

Exit code: `0`

### Command 3

```bash
npx --yes markdownlint-cli2 docs/audit/PHASE1_DOCS_GATES_AUDIT_2026-02-12.md
```

### Raw output 3 (excerpt)

```text
Summary: 0 error(s)
```

Exit code: `0`

---

## Risks and mitigations

- **Risk:** false positives from strict evidence-anchor requirements.
  **Mitigation:** Phase 1 scope is changed files only
  (`git diff base...HEAD`), not whole-repo historical docs.
- **Risk:** CI environment without Node toolchain for markdownlint.
  **Mitigation:** dedicated `setup-node` before markdownlint execution (`.github/workflows/ci.yml:127`).
- **Risk:** placeholder drift in new audit docs.
  **Mitigation:** explicit blocker on `PR: TBD` for changed audit docs (`scripts/ci/check_docs_phase1_gates.py:58`).
