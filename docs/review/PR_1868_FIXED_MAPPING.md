# PR #1868 - Fixed in Commit Mapping

**Title:** `fix(security): submit frontend npm dependency graph`
**Branch:** `codex/frontend-dependency-graph-alert-153`
**Scope:** Add explicit `/frontend` npm dependency submission so GitHub
dependency graph can ingest the already-patched Vitest `4.1.8` frontend
lockfile state for Dependabot alert `#153`.
**Primary implementation commits:** `4cc76042c`, `4d7951f47`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1868#discussion_r3343593209 -> 4d7951f478c1bffb52c7750848a5cd185728d8dc
Disposition: FIXED
Evidence: `.github/workflows/npm-dependency-submission.yml:62`, `.github/workflows/npm-dependency-submission.yml:75`, `tests/guards/test_security_devtooling_regression_guards.py:447`, and `tests/guards/test_security_devtooling_regression_guards.py:453` prove the temp graph root preserves `frontend/package-lock.json`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1868#discussion_r3343622098 -> 4d7951f478c1bffb52c7750848a5cd185728d8dc
Disposition: FIXED
Evidence: Same frontend source-location fix as `discussion_r3343593209`; the workflow no longer uses `filePath: frontend`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1868#discussion_r3343606382 -> 4d7951f478c1bffb52c7750848a5cd185728d8dc
Disposition: FIXED
Evidence: `tests/guards/test_security_devtooling_regression_guards.py:447` asserts the root npm dependency-submission job has no `filePath`, or only a repo-root indicator.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1868#discussion_r3343622109 -> 4d7951f478c1bffb52c7750848a5cd185728d8dc
Disposition: FIXED
Evidence: Same root job scope guard as `discussion_r3343606382`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1868#discussion_r3343606373 -> 4d7951f478c1bffb52c7750848a5cd185728d8dc
Disposition: FIXED
Evidence: The Philosophy PR-5 ledger closeout and its guard were removed; `git diff --name-only origin/main...HEAD` no longer includes `docs/roadmap/BACKLOG_LEDGER.md`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1868#pullrequestreview-4412654906 -> 4d7951f478c1bffb52c7750848a5cd185728d8dc
Disposition: FIXED
Evidence: `.github/workflows/npm-dependency-submission.yml:37`, `.github/workflows/npm-dependency-submission.yml:55`, `.github/workflows/npm-dependency-submission.yml:41`, and `.github/workflows/npm-dependency-submission.yml:59` cover timeout and checkout hardening.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1868#discussion_r3343625559 -> 4d7951f478c1bffb52c7750848a5cd185728d8dc
Disposition: FIXED
Evidence: Commit `4d7951f478c1bffb52c7750848a5cd185728d8dc` includes the canonical Experiment Runner trailer; earlier runner-shaped commits `4cc76042c` and `c59653e99` do too.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1868#discussion_r3343625561
Disposition: FIXED
Evidence: This mapping artifact replaces the stale `No actionable review comments` entry with explicit FIXED dispositions; the immediate follow-up governance commit will add the concrete mapping commit SHA for this self-reference.

## Dependency Scope / Private-Index Notes

- No `frontend/package.json` or `frontend/package-lock.json` changes.
- No `.github/dependabot.yml`, Python dependency, private-index, backend,
  OpenAPI, product API, Docker, Trivy, frontend runtime, ledger, or
  semantic-cache runtime files changed in the final PR diff.
- Python setup validation uses the explicit private index:
  `python3 scripts/ci/install_locked_python_requirements.py --preflight-only --index-url "$PULSEPLATE_PYTHON_INDEX_URL" --emergency-wheel-manifest scripts/ci/emergency_python_wheels.json`.
- No public-PyPI bypass, `PIP_INDEX_URL` / `PIP_EXTRA_INDEX_URL` ambient
  override, or emergency-wheel widening was introduced.

## Implementation Evidence

Disposition: FIXED
Commit: `4d7951f478c1bffb52c7750848a5cd185728d8dc`
Evidence:

- `.github/workflows/npm-dependency-submission.yml` triggers on
  `frontend/package.json` and `frontend/package-lock.json`.
- The root npm submission remains root-scoped, has no `filePath`, and excludes
  `frontend`, `node_modules`, `worktrees`, and `.venv`.
- The frontend npm submission has its own `correlator:
  npm-dependency-submission-frontend`, `Npm` detector, lockfile v3 detector
  args, and local-artifact exclusions.
- The frontend job prepares a temporary graph root containing
  `frontend/package.json` and `frontend/package-lock.json`, then passes the temp
  root as the action `filePath`; this avoids the pinned action normalizing the
  manifest to plain `package-lock.json`.
- `tests/guards/test_security_devtooling_regression_guards.py` asserts the
  root/frontend workflow split, frontend path triggers, no `pull_request_target`,
  minimal workflow permissions, root-scope `filePath` behavior, checkout
  hardening, timeout governance, and frontend temp graph-root behavior.
- `docs/security/CVE-2026-47429-vitest.md` documents alert `#153`,
  `GHSA-5xrq-8626-4rwp`, patched floor `4.1.0`, repo lock truth `4.1.8`, stale
  SBOM truth `3.2.4`, and why Docker/Trivy do not directly close this graph
  alert.

## Role-Agent Evidence

Pre-open role order from packet
`artifacts/orchestration/task_packets/85771c03a883.json`:

- `agent-coordinator` - PASS; accepted combined scope before review feedback.
- `security-auditor` - PASS; required no permission widening, no
  `pull_request_target`, pinned actions, distinct frontend correlator, and no
  Python/private-index drift.
- `architecture-specialist` - PASS; confirmed root-only npm submission was
  structurally insufficient for `/frontend` graph truth.
- `frontend-engineer` - PASS; confirmed no runtime frontend changes or package
  lock changes were needed.
- `qa-engineer-agent` - PASS after coherent diff; accepted deterministic guard
  coverage.
- `bug-hunter` - PASS after coherent diff; checked YAML parsing, action inputs,
  stale line anchors, and overclaim risk.
- `cursor-specialist-agent` - PASS; confirmed mapping/body order and local
  artifact non-commit policy.
- `web-research-agent` - PASS; confirmed live alert/SBOM facts and Docker/Trivy
  closure boundary.
- Post-open `agent-coordinator` - BLOCK until CI/review actionables were fixed.
- Post-open `qa-engineer-agent` - BLOCK; identified the `filePath: frontend`
  source-location false-green, missing root-scope guard, checkout hardening,
  timeout governance, and mixed Philosophy closeout issue.
- Post-open `bug-hunter` - BLOCK only on stale governance mirrors after the
  workflow/test fix was applied; required mapping/body updates.

## Premortem Evidence

- Artifact: `docs/review/PR_DEPENDENCY_GRAPH_ALERT_153_PREMORTEM.md`
- Decision: proceed with changes.
- Findings closed:
  - `PM-153-001` frontend graph submission gap - FIXED.
  - `PM-153-002` dependency/permission scope widening - FIXED.
  - `PM-153-003` bundled Philosophy ledger closeout violating ledger closeout
    policy - FIXED by removing the ledger change from this PR.
  - `PM-153-004` full npm audit moderate findings misread as Vitest blocker -
    NOT-A-BUG with scope evidence.

## Experiment Runner Evidence

- Artifact:
  `artifacts/orchestration/experiments/results/frontend-dependency-graph-alert-153-oracle-result.json`
- Mode: `oracle_only_governance_reviewer`
- Result: accepted.
- Oracle commands: 2 configured, 2 executed, all passed.
- `source_diff_applied=true`
- `source_diff_paths`:
  - `.github/workflows/npm-dependency-submission.yml`
  - `docs/audit/DEPENDABOT_RECURRING_SECURITY_DRIFT_AUDIT_2026-04-10.md`
  - `docs/review/PR_DEPENDENCY_GRAPH_ALERT_153_PREMORTEM.md`
  - `docs/roadmap/BACKLOG_LEDGER.md`
  - `docs/security/CVE-2026-47429-vitest.md`
  - `tests/guards/test_security_devtooling_regression_guards.py`
- `mutated_paths=[]`
- `shared_tree_untouched=true`
- `coauthor_required=true`
- Commit trailer used on Experiment Runner-shaped commits:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

## Local Validation

- `python3 scripts/orchestration/check_preflight.py --mode analyze ...` - PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- `python3 scripts/ci/install_locked_python_requirements.py --preflight-only --index-url "$PULSEPLATE_PYTHON_INDEX_URL" --emergency-wheel-manifest scripts/ci/emergency_python_wheels.json` - PASS.
- `<repo-root>/.venv/bin/python -m pytest -q tests/guards/test_security_devtooling_regression_guards.py` - PASS, 12 tests after scope narrowing.
- `python3 scripts/ci/check_docs_phase1_gates.py --files docs/roadmap/BACKLOG_LEDGER.md docs/audit/DEPENDABOT_RECURRING_SECURITY_DRIFT_AUDIT_2026-04-10.md docs/review/PR_DEPENDENCY_GRAPH_ALERT_153_PREMORTEM.md docs/security/CVE-2026-47429-vitest.md` - PASS.
- `cd frontend && npm audit --audit-level=high --json` - PASS, 0 high/critical.
- `cd frontend && npm audit --json` - expected nonzero from pre-existing
  moderate `brace-expansion` and `ws` transitives; no Vitest high/critical
  finding.
- Commit hook for `4d7951f47` - PASS after `black` reformatted the guard test
  and the focused guard/docs gates were rerun.
- `pre-commit run --all-files` - pending rerun before the next push.
- `make validate-changed` - pending rerun before the next push.

## GitHub Evidence

- `gh api repos/Katsiarynakavaleuskaya/PulsePlate/dependabot/alerts/153` -
  alert still `open`, package `vitest`, manifest `frontend/package-lock.json`,
  affected `<4.1.0`, patched `4.1.0`, advisory
  `GHSA-5xrq-8626-4rwp` / `CVE-2026-47429`.
- `gh api repos/Katsiarynakavaleuskaya/PulsePlate/dependency-graph/sbom` -
  still reports `vitest@3.2.4` before frontend graph submission runs on `main`.
- `NPM Dependency Submission` passed on the earlier PR head, but that run used
  the stale `filePath: frontend` implementation. The fixed temp-root
  implementation must run after the next push and again on `main` after merge.

## Current CI Status

Latest local head includes fix commit `4d7951f47` and mapping updates that have
not yet been pushed. Current GitHub CI status still belongs to PR head
`c59653e99`; merge readiness is not claimed.

## Thread Disposition Status

All live actionable Codex, CodeRabbit, and Cubic comments known at this mapping
update are listed above with FIXED dispositions. Sourcery is rate-limited and
posted no actionable code finding. CodeRabbit's docstring coverage warning is a
repo-external advisory on this docs/workflow/test PR and does not identify a
diff-scoped missing-docstring defect.
