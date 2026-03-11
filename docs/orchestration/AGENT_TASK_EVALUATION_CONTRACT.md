# Agent Task Evaluation Contract

**Purpose:** Define explicit success criteria per agent task class (EVMbench-inspired).
**Source:** `docs/audit/EVMBENCH_INSPIRED_AGENT_EVALUATION_BRAINSTORM_2026-02-21.md`
**Scope:** Coordinator-routed tasks, CI/guards, security, docs-only.

**Evidence anchor:** `docs/orchestration/AGENT_TASK_EVALUATION_CONTRACT.md:1`

---

## 1. Overview

This contract defines **what "success" means** for each agent task class. It enables:

- **Deterministic evaluation:** Pass/fail criteria linked to existing gates
- **Recall-style coverage:** Checklist ensures all required items are addressed
- **Audit trail:** PR body and commit mapping provide evidence

**Principle:** An agent task is successful if and only if all success criteria for its class are met.

---

## 2. Task Classes and Success Criteria

### 2.1 CI Fix (`fix-ci`, `fix-guard`)

**Goal:** Restore green CI by fixing the failing check(s).

**Success Criteria:**

| # | Criterion | Gate / Evidence |
|---|-----------|-----------------|
| 1 | All failing checks identified and addressed | CI run shows all jobs green |
| 2 | `make verify` passes locally before push | Terminal output or pre-commit log |
| 3 | No new violations introduced | Guard tests pass: `pytest -q tests/test_repo_policy_guards.py` |
| 4 | No scope creep (fix only what's broken) | PR diff is minimal and focused |
| 5 | Pre-commit hooks pass | `pre-commit run --all-files` exit 0 |

**Recall Checklist (optional):**

- [ ] Identified root cause (job name + error class)
- [ ] Applied minimal fix targeting root cause
- [ ] Verified fix locally (`make verify` or `make test-fast`)
- [ ] Pushed and confirmed CI green
- [ ] No unrelated changes in diff

**Failure modes to avoid:**

- Fixing one failure while leaving related violations (run full guard suite)
- Over-engineering: adding features, refactoring, or "improvements" beyond the fix
- Using `# type: ignore`, `|| true`, or skips without explicit justification

---

### 2.2 Security Remediation (`fix-cve`, `security-patch`)

**Goal:** Address security vulnerability (CVE, audit finding) with minimal, focused changes.

**Success Criteria:**

| # | Criterion | Gate / Evidence |
|---|-----------|-----------------|
| 1 | Vulnerability addressed (patched or mitigated) | Dependency version bump or code fix applied |
| 2 | All requirement surfaces updated | `requirements*.txt`, `constraints.txt` consistent |
| 3 | Security guard test passes | `pytest -q tests/test_dependency_security_guard.py` |
| 4 | Evidence doc created or updated | `docs/security/CVE-<id>-<package>.md` exists |
| 5 | No new vulnerabilities introduced | Trivy/bandit checks pass |
| 6 | `make verify` passes | Full verification gate green |

**Recall Checklist (optional):**

- [ ] CVE identified and documented (ID, severity, affected package)
- [ ] Minimum fixed version determined from advisory
- [ ] All requirement files updated (`.in`, `.txt`, `constraints.txt`)
- [ ] Evidence doc with `file:line` anchors created
- [ ] Guard test updated if new version floor required
- [ ] Trivy ignore policy updated if suppression needed (with expiry)

**Failure modes to avoid:**

- Partial update: changing one requirements file but not others
- Missing evidence: no doc in `docs/security/` for CVE fix
- Suppression without expiry or tracking

---

### 2.3 Docs-Only (`docs`, `ledger-update`)

**Goal:** Update documentation without any runtime, CI, or code changes.

**Success Criteria:**

| # | Criterion | Gate / Evidence |
|---|-----------|-----------------|
| 1 | Only `.md` files changed | `git diff --name-only` shows only markdown |
| 2 | No runtime config changes | No `.yml`, `.py`, `Dockerfile`, `Makefile` in diff |
| 3 | Pre-commit hooks pass | `pre-commit run --all-files` exit 0 |
| 4 | Docs Phase1 gates pass | CI check: `Docs Phase1 gates` |
| 5 | PR body follows template | Phase2 PR body gates pass |

**Recall Checklist (optional):**

- [ ] Changes are strictly documentation
- [ ] No code, CI, or config files touched
- [ ] Evidence anchors (`file:line`) added where claims are made
- [ ] English-first for ledger entries (non-English includes summary)

**Failure modes to avoid:**

- Accidentally including code changes (check `git diff --name-only`)
- Missing evidence anchors in audit docs
- Non-English ledger entries without English summary

---

### 2.4 Feature Implementation (`feat`, `feature`)

**Goal:** Implement new functionality with tests and documentation.

**Success Criteria:**

| # | Criterion | Gate / Evidence |
|---|-----------|-----------------|
| 1 | Feature works as specified | Tests pass; manual verification if applicable |
| 2 | Tests added for new code | Coverage gate: diff-coverage ≥97% |
| 3 | No guard violations | `pytest -q tests/test_repo_policy_guards.py` |
| 4 | `make verify` passes | Full verification gate green |
| 5 | Bot reviews addressed | All actionable comments resolved |
| 6 | PR body complete | Phase2 PR body gates pass |

**Recall Checklist (optional):**

- [ ] Feature requirements understood and documented
- [ ] Implementation follows existing patterns
- [ ] Tests cover happy path and key edge cases
- [ ] No security vulnerabilities introduced
- [ ] Bot comments addressed with commit mapping
- [ ] DoD items from ledger (if tracked) checked off

**Failure modes to avoid:**

- Insufficient test coverage (check diff-coverage)
- Over-engineering beyond requirements
- Ignoring bot review comments

---

### 2.5 Refactor / Cleanup (`refactor`, `chore`)

**Goal:** Improve code quality without changing behavior.

**Success Criteria:**

| # | Criterion | Gate / Evidence |
|---|-----------|-----------------|
| 1 | Behavior unchanged | All existing tests pass |
| 2 | No new tests required (behavior same) | Or: new tests for previously untested code |
| 3 | `make verify` passes | Full verification gate green |
| 4 | Scope is focused | PR description justifies scope |

**Recall Checklist (optional):**

- [ ] Refactor does not change external behavior
- [ ] All existing tests still pass
- [ ] Dead code removed (not tested)
- [ ] No new features introduced

---

### 2.6 Creative Research (`creative_research`)

**Goal:** Run a governed creativity / discovery cycle inside the existing experimentation lane without creating runtime or governance drift.

**Success Criteria:**

| # | Criterion | Gate / Evidence |
|---|-----------|-----------------|
| 1 | Task uses the experimentation umbrella, not a competing framework | `AGENT_EXPERIMENTATION_PROTOCOL.md` + `CREATIVE_RESEARCH_SUBLANE_PROTOCOL.md` linked |
| 2 | Phase outputs are explicit | Divergence, convergence, and verification artifacts exist |
| 3 | Hypothesis contract is complete for promoted candidates | `claim`, `mechanism`, `evidence_needed`, `falsifier`, `confidence`, `known_risks`, `wellness_boundary`, `promotion_decision` |
| 4 | Scorecard contract is complete for verified candidates | Scorecard fields are present with explicit `promote` / `defer` / `discard` |
| 5 | Missing discovery fields trigger downgrade | Candidate lacking `mechanism`, `falsifier`, or `evidence_needed` is labeled `creative_ideation` |
| 6 | Next PR scope is explicit | Packet includes files, tests, docs, gates, and human review requirement |
| 7 | Deferred work is ledgered immediately | `docs/roadmap/BACKLOG_LEDGER.md` updated when applicable |
| 8 | PR wave boundaries are preserved | PR-A docs-only; PR-B offline eval only; PR-C internal-only pilot |

**Recall Checklist (optional):**

- [ ] Used coordinator-first routing and explicit sync points
- [ ] Applied Diverger / Synthesizer / Skeptic / Verifier handoffs explicitly
- [ ] Preserved human-gated chaining
- [ ] Preserved no-hidden-memory and no-autonomous-merge boundaries
- [ ] Preserved no new public heavy LLM endpoint on the core path

**Failure modes to avoid:**

- Rewriting experimentation rules in sub-lane docs
- Treating ideation as discovery without falsifier/evidence plan
- Expanding the lane into public runtime in PR-A or PR-B
- Introducing orchestration telemetry sprawl during PR-C planning
- Leaving deferred follow-ups outside the ledger

---

## 3. Common Gates (All Task Classes)

These gates apply to **all** agent tasks:

| Gate | Command / Check | Pass Criterion |
|------|-----------------|----------------|
| Pre-commit | `pre-commit run --all-files` | Exit 0 |
| Guard tests | `pytest -q tests/test_repo_policy_guards.py` | All pass |
| Lint | `make lint` | Exit 0 |
| Typecheck | `make typecheck` | Exit 0 (or non-blocking per config) |
| Diff-coverage | `make diff-cov` | ≥97% on changed lines |
| PR body | Phase2 PR body gates | CI check pass |
| Merge readiness | Merge readiness gate | CI check pass |

---

## 4. Evaluation Protocol

### 4.1 Before Pushing

1. Run `make verify` (or individual gates if faster)
2. Run `pre-commit run --all-files`
3. Confirm no merge conflicts: `git status`
4. Review diff: `git diff origin/main...HEAD`

### 4.2 After CI Run

1. Check all required CI checks pass
2. Address bot review comments (map in PR body)
3. Wait for CodeRabbit/Sourcery/Cubic reviews
4. Confirm merge readiness gate passes

### 4.3 Post-Merge

1. Verify main branch CI is green
2. Clean up worktree/branch
3. Update ledger if task was tracked

---

## 5. Linking to RUNBOOK and AGENTS

This contract is referenced from:

- `RUNBOOK_AGENT.md` — CI failure triage and merge checklist
- `AGENTS.md` — Hard gates section (make verify, pre-commit policy)
- `docs/orchestration/workflow.md` — Coordinator-first task routing

When in doubt, check the task class success criteria above before claiming a task is complete.

---

## 6. Document History

| Date       | Change |
|------------|--------|
| 2026-02-22 | Initial contract; EVMbench-inspired success criteria per task class. |
