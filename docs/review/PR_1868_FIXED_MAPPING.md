# PR #1868 - Fixed in Commit Mapping

**Title:** `fix(security): submit frontend npm dependency graph`
**Branch:** `codex/frontend-dependency-graph-alert-153`
**Scope:** Add explicit `/frontend` npm dependency submission so GitHub
dependency graph can ingest the already-patched Vitest `4.1.8` frontend
lockfile state for Dependabot alert `#153`. The PR also closes the already
merged Philosophy PR-5 source-corpus backlog row with PR #1822 evidence.
**Primary commit:** `4cc76042c`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- No actionable review comments

## Dependency Scope / Private-Index Notes

- No `frontend/package.json` or `frontend/package-lock.json` changes.
- No `.github/dependabot.yml`, Python dependency, private-index, backend,
  OpenAPI, product API, Docker, Trivy, frontend runtime, or semantic-cache
  runtime files changed.
- Python setup validation used the explicit private index:
  `python3 scripts/ci/install_locked_python_requirements.py --preflight-only --index-url "$PULSEPLATE_PYTHON_INDEX_URL" --emergency-wheel-manifest scripts/ci/emergency_python_wheels.json`.
- No public-PyPI bypass, `PIP_INDEX_URL` / `PIP_EXTRA_INDEX_URL` ambient
  override, or emergency-wheel widening was introduced.

## Implementation Evidence

Disposition: FIXED
Commit: `4cc76042c`
Evidence:

- `.github/workflows/npm-dependency-submission.yml` now triggers on
  `frontend/package.json` and `frontend/package-lock.json`.
- `.github/workflows/npm-dependency-submission.yml` keeps the root npm
  submission root-scoped and still excludes `frontend`.
- `.github/workflows/npm-dependency-submission.yml` adds
  `frontend-dependency-submission` with `correlator:
  npm-dependency-submission-frontend`, `filePath: frontend`,
  `detectorsCategories: Npm`, lockfile v3 detector args, and local-artifact
  exclusions.
- `tests/guards/test_security_devtooling_regression_guards.py` asserts the
  root/frontend workflow split, frontend path triggers, no `pull_request_target`,
  minimal workflow permissions, and Philosophy PR-5 closeout evidence.
- `docs/security/CVE-2026-47429-vitest.md` documents alert `#153`,
  `GHSA-5xrq-8626-4rwp`, patched floor `4.1.0`, repo lock truth `4.1.8`, stale
  SBOM truth `3.2.4`, and why Docker/Trivy do not directly close this graph
  alert.
- `docs/roadmap/BACKLOG_LEDGER.md` marks
  `ledger-p1-philosophy-epic-v2-pr5-source-corpus-index` complete with PR #1822
  merge evidence while preserving blocked semantic-cache/runtime markers.

## Role-Agent Evidence

Pre-open role order from packet
`artifacts/orchestration/task_packets/85771c03a883.json`:

- `agent-coordinator` - PASS; accepted combined scope if the Philosophy edit
  stayed status-only and guarded.
- `security-auditor` - PASS; required no permission widening, no
  `pull_request_target`, pinned actions, distinct frontend correlator, and no
  Python/private-index drift.
- `architecture-specialist` - PASS; confirmed root-only npm submission was
  structurally insufficient for `/frontend` graph truth and PR #1822 ledger
  closeout was bounded.
- `frontend-engineer` - PASS; confirmed no runtime frontend changes or package
  lock changes were needed.
- `qa-engineer-agent` - PASS after coherent diff; accepted deterministic guard
  coverage and mixed-scope ledger closeout.
- `bug-hunter` - PASS after coherent diff; checked YAML parsing, action inputs,
  stale line anchors, and overclaim risk.
- `cursor-specialist-agent` - PASS; confirmed mapping/body order and local
  artifact non-commit policy.
- `web-research-agent` - PASS; confirmed live alert/SBOM facts and Docker/Trivy
  closure boundary.
- Final `security-auditor` diff closure - PASS; no findings.

## Premortem Evidence

- Artifact: `docs/review/PR_DEPENDENCY_GRAPH_ALERT_153_PREMORTEM.md`
- Decision: proceed with changes.
- Findings closed:
  - `PM-153-001` frontend graph submission gap - FIXED.
  - `PM-153-002` dependency/permission scope widening - FIXED.
  - `PM-153-003` Philosophy closeout reopening runtime gates - FIXED.
  - `PM-153-004` full npm audit moderate findings misread as Vitest blocker -
    NOT-A-BUG with scope evidence.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/frontend-dependency-graph-alert-153-oracle-result.json`
- Mode: `oracle_only_governance_reviewer`
- Result: accepted.
- Oracle commands: 3 configured, 3 executed, all passed.
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
- Commit trailer used on `4cc76042c`:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

## Local Validation

- `python3 scripts/orchestration/check_preflight.py --mode analyze ...` - PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- `python3 scripts/ci/install_locked_python_requirements.py --preflight-only --index-url "$PULSEPLATE_PYTHON_INDEX_URL" --emergency-wheel-manifest scripts/ci/emergency_python_wheels.json` - PASS.
- `<repo-root>/.venv/bin/python -m pytest -q tests/guards/test_security_devtooling_regression_guards.py` - PASS, 13 tests.
- `python3 scripts/ci/check_docs_phase1_gates.py --files docs/roadmap/BACKLOG_LEDGER.md docs/audit/DEPENDABOT_RECURRING_SECURITY_DRIFT_AUDIT_2026-04-10.md docs/review/PR_DEPENDENCY_GRAPH_ALERT_153_PREMORTEM.md docs/security/CVE-2026-47429-vitest.md` - PASS.
- `python3 scripts/ci/check_philosophy_source_corpus_index.py --check --files docs/roadmap/BACKLOG_LEDGER.md docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.json scripts/ci/check_philosophy_source_corpus_index.py tests/test_philosophy_source_corpus_index.py` - PASS.
- `<repo-root>/.venv/bin/python -m pytest -q tests/test_philosophy_source_corpus_index.py` - PASS.
- `cd frontend && npm audit --audit-level=high --json` - PASS, 0 high/critical.
- `cd frontend && npm audit --json` - expected nonzero from pre-existing
  moderate `brace-expansion` and `ws` transitives; no Vitest high/critical
  finding.
- `pre-commit run --all-files` - PASS.
- `DEV_PYTHON=<repo-root>/.venv/bin/python VENV_PYTHON=<repo-root>/.venv/bin/python PATH=<repo-root>/.venv/bin:$PATH make validate-changed` - PASS.
- Pre-push hooks - PASS, including pip-audit, backend pre-push tests, and
  full-repo Bandit; Docker build hook skipped because no Docker-surface files
  changed.

## GitHub Evidence

- `gh api repos/Katsiarynakavaleuskaya/PulsePlate/dependabot/alerts/153` -
  alert still `open`, package `vitest`, manifest `frontend/package-lock.json`,
  affected `<4.1.0`, patched `4.1.0`, advisory
  `GHSA-5xrq-8626-4rwp` / `CVE-2026-47429`.
- `gh api repos/Katsiarynakavaleuskaya/PulsePlate/dependency-graph/sbom` -
  still reports `vitest@3.2.4` before frontend graph submission runs on `main`.

## Current CI Status

Pending on initial current-head CI for PR #1868. Merge readiness is not claimed.
After merge, closure still requires confirming `NPM Dependency Submission` runs
on `main` and the frontend graph no longer reports `vitest@3.2.4`.

## Thread Disposition Status

No actionable review comments existed when this initial mapping artifact was
created. If CodeRabbit, Sourcery, Cubic, or human review posts actionable
comments, this artifact must be updated with FIXED / NOT-A-BUG / DEFERRED
dispositions before any readiness claim.
