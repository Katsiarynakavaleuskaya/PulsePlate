# PR #1760 Replacement Premortem

**Mode:** `pr-premortem`
**Task packet:** `artifacts/orchestration/task_packets/4640174232c5.json`
**Coordinator order:** `agent-coordinator -> cursor-specialist-agent -> security-auditor -> qa-engineer-agent -> bug-hunter -> agent-coordinator`
**Scope:** replace Dependabot PR #1760 only by moving optional RAG vector `sentence-transformers` pins and the exact emergency wheel fallback from `5.4.1` to `5.5.0`.

## Summary

It is 6 months from now. This dependency replacement failed because a narrow lockfile and emergency-wheel update looked harmless but left governance, fallback, or current-head CI evidence inconsistent.

## Failure Modes

### 1. Emergency fallback drifted from the lock surfaces

**Failure story:** The RAG vector lock surfaces moved to `sentence-transformers==5.5.0`, but the private-index emergency manifest kept an older wheel or an unverified hash. A future private-index mirror lag then installed from the fallback path and either failed at install time or silently bypassed the intended exact dependency.

**Underlying assumption:** A lockfile bump and a fallback manifest bump are naturally kept in sync.

**Early warning signs:** Manifest version differs from the RAG vector pins, or wheel URL/hash provenance is not independently reproducible from PyPI metadata.

**Containment action:** Keep the fallback exact and sha256-pinned, and add focused coverage that asserts the active emergency manifest version appears in all RAG vector `.in` and `.txt` surfaces.

**Disposition:** FIXED by adding manifest-to-RAG-profile regression coverage in `tests/test_install_locked_python_requirements.py` and pinning `sentence_transformers-5.5.0-py3-none-any.whl` with exact sha256 in `scripts/ci/emergency_python_wheels.json`.

### 2. Governance artifact stayed placeholder-only

**Failure story:** The replacement PR opened with code that was correct, but the fixed mapping still referenced pending commits, missing test surfaces, or the superseded Dependabot PR without a clear local validation plan. Merge-readiness checks then failed late, after CI had already consumed cycles.

**Underlying assumption:** A replacement PR can inherit Dependabot context without its own canonical mapping artifact.

**Early warning signs:** `docs/review/PR_1760_FIXED_MAPPING.md` contains `pending` evidence after commit, omits touched tests, or lacks the machine-heavy deferral note.

**Containment action:** Keep the mapping artifact in the branch from the start, update it with real commit evidence after the first commit exists, and mirror deferrals in the PR body after open.

**Disposition:** FIXED for pre-open planning by adding the fixed mapping artifact and including the touched regression test in the local validation command list. Final commit SHA replacement remains a required post-commit governance step.

### 3. Machine-heavy exception masked a current-head failure

**Failure story:** Full local `make verify` was deferred correctly, but the PR treated narrow local gates as equivalent to merge readiness. A required current-head CI job or diff coverage gate failed after push, making the branch look green locally but not mergeable.

**Underlying assumption:** Narrow local gates are enough for a dependency-only PR.

**Early warning signs:** PR body or fixed mapping says full verify is deferred but does not name current-head CI parity, strict merge readiness, or review-thread disposition as required acceptance criteria.

**Containment action:** Document the deferral explicitly and keep merge readiness blocked until latest-head required checks, review-thread disposition, and strict readiness scripts pass.

**Disposition:** FIXED in governance language for pre-open scope; final PR body mirror and strict GitHub checks are post-open requirements.

### 4. Scope creep contaminated the two-lane Dependabot train

**Failure story:** While replacing #1760, the branch accidentally pulled quality-tooling updates for #1757 or philosophy changes from #1761. Reviewers could no longer reason about the dependency blast radius, and rollback would be unclear.

**Underlying assumption:** All Dependabot lanes are interchangeable because they touch dependency files.

**Early warning signs:** Diff includes `black`, `mypy`, `ruff`, philosophy docs, or unrelated orchestration artifacts.

**Containment action:** Keep #1760 and #1757 on separate fresh-main worktrees and do not start #1757 until the #1760 replacement is merged and local main is synchronized.

**Disposition:** NOT-A-BUG for the current diff: inspected touched files are limited to #1760 replacement surfaces and governance artifacts.

## Most Likely Failure

The most likely failure is governance drift: placeholder mapping evidence or missing validation references causing phase gates to fail after the implementation is already correct.

## Most Dangerous Failure

The most dangerous failure is fallback drift that weakens the private-index-only emergency wheel contract, because it could create a false install path outside the intended exact, sha256-pinned recovery model.

## Hidden Assumption

The branch assumes that PyPI wheel metadata and the private-index emergency fallback remain aligned after the package bump; this must be enforced by tests and current-head CI rather than reviewer memory.

## Revised Plan

- Keep the replacement branch isolated from #1757 and #1761.
- Preserve only the `sentence-transformers==5.5.0` RAG vector changes plus exact emergency fallback alignment.
- Add focused regression coverage for manifest-to-RAG-profile alignment.
- Update fixed mapping with real commit evidence after committing code changes.
- Use the machine-heavy exception only with documented narrow local gates and latest-head CI parity.

## Pre-Merge Checklist

- `check_preflight.py` and `check_agent_consistency.py` pass on the changed paths.
- Focused pytest covers the new emergency-fallback/RAG-profile alignment guard.
- `make validate-changed` passes from the replacement branch.
- `pre-commit run --all-files` passes with no uncommitted hook output.
- PR body mirrors fixed mapping, machine-heavy deferral, review-thread disposition, and current-head CI acceptance.
- `check_pr_body_phase2_gates.py`, `check_review_threads_disposition.py --require-auth`, and `check_pr_merge_readiness.py` pass after PR open.

## Decision

`proceed with changes`: continue only after explicit role-agent review, the mapping-plan fix, focused local gates, and post-open current-head CI evidence.
