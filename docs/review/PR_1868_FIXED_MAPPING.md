# PR #1868 - Fixed in Commit Mapping

**Title:** `fix(security): submit frontend npm dependency graph`
**Branch:** `codex/frontend-dependency-graph-alert-153`
**Scope:** Add explicit `/frontend` npm dependency submission so GitHub
dependency graph can ingest the already-patched Vitest `4.1.8` frontend
lockfile state for Dependabot alert `#153`.
**Primary implementation commits:** `4cc76042c`, `4d7951f47`, `e705444ee`,
`66de78461`, `2138af99e`, `a992afdca`, `d882f7ad5`, `88e27602a`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1868#discussion_r3343593209 -> 4d7951f478c1bffb52c7750848a5cd185728d8dc
Disposition: FIXED
Commit: 4d7951f478c1bffb52c7750848a5cd185728d8dc
Evidence: `.github/workflows/npm-dependency-submission.yml:62`, `.github/workflows/npm-dependency-submission.yml:75`, `tests/guards/test_security_devtooling_regression_guards.py:447`, and `tests/guards/test_security_devtooling_regression_guards.py:453` prove the temp graph root preserves `frontend/package-lock.json`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1868#discussion_r3343622098 -> 4d7951f478c1bffb52c7750848a5cd185728d8dc
Disposition: FIXED
Commit: 4d7951f478c1bffb52c7750848a5cd185728d8dc
Evidence: Same frontend source-location fix as `discussion_r3343593209`; the workflow no longer uses `filePath: frontend`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1868#discussion_r3343606382 -> 4d7951f478c1bffb52c7750848a5cd185728d8dc
Disposition: FIXED
Commit: 4d7951f478c1bffb52c7750848a5cd185728d8dc
Evidence: `tests/guards/test_security_devtooling_regression_guards.py:447` asserts the root npm dependency-submission job has no `filePath`, or only a repo-root indicator.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1868#discussion_r3343622109 -> 4d7951f478c1bffb52c7750848a5cd185728d8dc
Disposition: FIXED
Commit: 4d7951f478c1bffb52c7750848a5cd185728d8dc
Evidence: Same root job scope guard as `discussion_r3343606382`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1868#discussion_r3343606373 -> 4d7951f478c1bffb52c7750848a5cd185728d8dc
Disposition: FIXED
Commit: 4d7951f478c1bffb52c7750848a5cd185728d8dc
Evidence: The Philosophy PR-5 ledger closeout and its guard were removed; `git diff --name-only origin/main...HEAD` no longer includes `docs/roadmap/BACKLOG_LEDGER.md`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1868#pullrequestreview-4412654906 -> 4d7951f478c1bffb52c7750848a5cd185728d8dc
Disposition: FIXED
Commit: 4d7951f478c1bffb52c7750848a5cd185728d8dc
Evidence: `.github/workflows/npm-dependency-submission.yml:37`, `.github/workflows/npm-dependency-submission.yml:55`, `.github/workflows/npm-dependency-submission.yml:41`, and `.github/workflows/npm-dependency-submission.yml:59` cover timeout and checkout hardening.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1868#discussion_r3343625559 -> 4d7951f478c1bffb52c7750848a5cd185728d8dc
Disposition: FIXED
Commit: 4d7951f478c1bffb52c7750848a5cd185728d8dc
Evidence: Commit `4d7951f478c1bffb52c7750848a5cd185728d8dc` includes the canonical Experiment Runner trailer; earlier runner-shaped commits `4cc76042c` and `c59653e99` do too.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1868#discussion_r3343625561 -> e705444eeb151e9703245d99c9b4e5d2e3db91c7
Disposition: FIXED
Commit: e705444eeb151e9703245d99c9b4e5d2e3db91c7
Evidence: Commit `e705444eeb151e9703245d99c9b4e5d2e3db91c7` replaces the stale `No actionable review comments` entry with explicit FIXED dispositions for the live review comments.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1868#discussion_r3343928770 -> a992afdca30e095340ff7eb26220269dd9e7f676
Disposition: FIXED
Commit: a992afdca30e095340ff7eb26220269dd9e7f676
Evidence: Commit `a992afdca30e095340ff7eb26220269dd9e7f676` adds explicit squash-attribution evidence and itself includes the canonical `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` trailer.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1868#discussion_r3343928772 -> a992afdca30e095340ff7eb26220269dd9e7f676
Disposition: FIXED
Commit: a992afdca30e095340ff7eb26220269dd9e7f676
Evidence: Commit `a992afdca30e095340ff7eb26220269dd9e7f676` corrects the invalid `e705444eec6976ec48c5bf7ef7042a38d8ebdc09` mapping typo to the real in-history commit `e705444eeb151e9703245d99c9b4e5d2e3db91c7` and records live-head ancestry checks for the mapping SHAs.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1868#pullrequestreview-4413154282
Disposition: NOT-A-BUG
Evidence: `git diff --name-only origin/main...HEAD -- docs/roadmap/BACKLOG_LEDGER.md` prints no files, and `git diff --name-only origin/main...HEAD` lists only the six workflow/docs/security/guard files in this PR.
Reason: Cubic identified a stale mixed-scope ledger concern from pre-narrowing context; the final branch does not change `docs/roadmap/BACKLOG_LEDGER.md` and cannot reopen the Philosophy PR-5 backlog item.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1868#discussion_r3344153212 -> d882f7ad518d3355ee9403c0db51bc3d7720034b
Disposition: FIXED
Commit: d882f7ad518d3355ee9403c0db51bc3d7720034b
Evidence: Commit `d882f7ad518d3355ee9403c0db51bc3d7720034b` gates both npm dependency submission jobs with `if: github.event_name != 'pull_request'`, adds a read-only PR validation job, and updates the guard test so Dependabot/fork PRs do not call the dependency submission API with read-only tokens.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1868#discussion_r3344017744
Disposition: NOT-A-BUG
Evidence: `git log --format=%B origin/main..HEAD` shows each branch commit made after Experiment Runner contribution carries `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`; the synthetic reviewed commit `ccc5cbb7abfe` is not the live branch head used by the canonical mapping guard.
Reason: The repo's pre-merge disposition contract maps proof to branch commits and separately requires the squash merge operator to preserve the canonical trailer in the final squash commit message.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1868#discussion_r3344153206
Disposition: NOT-A-BUG
Evidence: Same Experiment Runner trailer evidence as `discussion_r3344017744`; the synthetic reviewed commit `23b7dc66058e` is not the live branch head used by the canonical mapping guard.
Reason: The final squash commit must preserve the canonical trailer, but the synthetic review hash is not the canonical pre-merge branch-history proof.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1868#discussion_r3344017753
Disposition: NOT-A-BUG
Evidence: `git merge-base --is-ancestor a992afdca30e095340ff7eb26220269dd9e7f676 HEAD` and `git merge-base --is-ancestor 4d7951f478c1bffb52c7750848a5cd185728d8dc HEAD` pass on the live branch; the synthetic reviewed commit `ccc5cbb7abfe` is not the live branch head.
Reason: The canonical review-thread mapping guard validates live branch history before merge, not speculative squash-preview commit ancestry.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1868#discussion_r3344153201
Disposition: NOT-A-BUG
Evidence: Same live branch ancestry evidence as `discussion_r3344017753`; the synthetic reviewed commit `23b7dc66058e` is not the live branch head.
Reason: The mapping artifact is valid against the PR branch history enforced by the repo guard; the squash merge operator must preserve the mapped evidence and trailer in the final merge record.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1868#discussion_r3344230798
Disposition: NOT-A-BUG
Evidence: `docs/ENGINEERING_LESSONS.md` records the synthetic squash-preview no-loop rule, and the live branch history remains the canonical pre-merge mapping proof; the synthetic reviewed commit `c3813a01` is not the PR branch head.
Reason: This is the same synthetic squash-preview mapping loop already dispositioned; adding another mapping-only fix for each synthetic hash would perpetuate the loop.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1868#discussion_r3344241205 -> 88e27602abf20435088a5a7ab4b3abb81e93a189
Disposition: FIXED
Commit: 88e27602abf20435088a5a7ab4b3abb81e93a189
Evidence: Commit `88e27602abf20435088a5a7ab4b3abb81e93a189` updates `docs/security/CVE-2026-47429-vitest.md` to reference `.github/workflows/npm-dependency-submission.yml:68` for the frontend job and line `79` for the temp graph-root preparation step.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1868#pullrequestreview-4413417602 -> 88e27602abf20435088a5a7ab4b3abb81e93a189
Disposition: FIXED
Commit: 88e27602abf20435088a5a7ab4b3abb81e93a189
Evidence: Same CVE evidence line-number fix as `discussion_r3344241205`.

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
- Post-open `security-auditor` - PASS; no finding after review of token scope,
  `pull_request` vs `pull_request_target`, action pinning, checkout credential
  persistence, temp-root filesystem handling, no script execution, and
  Python/private-index drift boundaries.
- Post-open `cursor-specialist-agent` - PASS; role dispatch manifest preserved
  packet order and local ignored artifacts were kept out of the branch.
- Post-open `web-research-agent` - PASS; live GitHub alert/SBOM evidence and
  advisory facts remained scoped to Dependabot alert #153 graph convergence.

## Codex Security Evidence

- Scan directory:
  `/tmp/codex-security-scans/frontend-dependency-graph-alert-153/66de78461_20260602T192355Z`
- Mode: diff-scoped security scan / finding discovery for `origin/main...HEAD`.
- Result: no findings.
- Coverage: 6/6 rows in
  `artifacts/02_discovery/deep_review_input.csv` have receipts in
  `artifacts/02_discovery/work_ledger.jsonl`.
- Final reports written:
  - `report.md`
  - `report.html`
- Reviewed files:
  - `.github/workflows/npm-dependency-submission.yml`
  - `docs/audit/DEPENDABOT_RECURRING_SECURITY_DRIFT_AUDIT_2026-04-10.md`
  - `docs/review/PR_1868_FIXED_MAPPING.md`
  - `docs/review/PR_DEPENDENCY_GRAPH_ALERT_153_PREMORTEM.md`
  - `docs/security/CVE-2026-47429-vitest.md`
  - `tests/guards/test_security_devtooling_regression_guards.py`

## PulsePlate PR Review Evidence

- Context artifact: `/tmp/pulseplate_pr_1868_review_context.json`
- Markdown report: `/tmp/pulseplate_pr_1868_review_report.md`
- JSON report: `/tmp/pulseplate_pr_1868_review_report.json`
- Result: no blocking deterministic findings.
- Advisory note: large-diff review risk due governance/docs evidence volume;
  dispositioned as reviewed/no code action because final diff remains six
  scoped workflow/docs/guard files and no longer includes
  `docs/roadmap/BACKLOG_LEDGER.md`.

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
- Original oracle `source_diff_paths` before post-open scope narrowing:
  - `.github/workflows/npm-dependency-submission.yml`
  - `docs/audit/DEPENDABOT_RECURRING_SECURITY_DRIFT_AUDIT_2026-04-10.md`
  - `docs/review/PR_DEPENDENCY_GRAPH_ALERT_153_PREMORTEM.md`
  - `docs/roadmap/BACKLOG_LEDGER.md` (removed from the final PR diff after
    mixed-scope review feedback)
  - `docs/security/CVE-2026-47429-vitest.md`
  - `tests/guards/test_security_devtooling_regression_guards.py`
- Final branch diff excludes `docs/roadmap/BACKLOG_LEDGER.md`; the final PR is
  Dependabot alert #153 dependency-graph scope only.
- `mutated_paths=[]`
- `shared_tree_untouched=true`
- `coauthor_required=true`
- Commit trailer used on Experiment Runner-shaped commits:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

## Squash Attribution / Live-Head Evidence

- Live PR head when the synthetic-head review was triaged:
  `2138af99ede4aed36b11f7eb4b5f36409e83eece`.
- The synthetic reviewed commit `7d4d1ed0` is not the live branch head used for
  local ancestry proof; `gh pr view 1868 --json headRefOid` returned
  `2138af99ede4aed36b11f7eb4b5f36409e83eece` before this mapping hardening.
- `git merge-base --is-ancestor 4d7951f478c1bffb52c7750848a5cd185728d8dc HEAD`
  passes.
- `git merge-base --is-ancestor e705444eeb151e9703245d99c9b4e5d2e3db91c7 HEAD`
  passes.
- `git merge-base --is-ancestor 66de784615442b2d27a6cc9c129c1884ae0b0246 HEAD`
  passes.
- `git merge-base --is-ancestor a992afdca30e095340ff7eb26220269dd9e7f676 HEAD`
  passes after the mapping hardening commit is applied.
- `git cat-file -e e705444eeb151e9703245d99c9b4e5d2e3db91c7^{commit}`
  passes; the earlier `e705444eec6976ec48c5bf7ef7042a38d8ebdc09`
  mapping typo was invalid and has been corrected above.
- Every branch commit made after Experiment Runner materially shaped this lane
  includes the canonical trailer:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.
- If this PR is squash-merged, the final squash commit message must preserve
  that exact trailer; the PR body also mirrors the trailer for merge-message
  copy.

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
- `pre-commit run --all-files` - PASS.
- `DEV_PYTHON=<repo-root>/.venv/bin/python VENV_PYTHON=<repo-root>/.venv/bin/python PATH=<repo-root>/.venv/bin:$PATH make validate-changed` - PASS.

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

Latest local head includes fix commit `4d7951f47`, mapping commit `e705444ee`,
self-reference mapping commit `66de78461`, and this evidence refresh. These
commits have not yet been pushed. Current GitHub CI status still belongs to PR
head `c59653e99`; merge readiness is not claimed.

## Thread Disposition Status

All live actionable Codex, CodeRabbit, and Cubic comments known at this mapping
update are listed above with FIXED dispositions. Sourcery is rate-limited and
posted no actionable code finding. CodeRabbit's docstring coverage warning is a
repo-external advisory on this docs/workflow/test PR and does not identify a
diff-scoped missing-docstring defect.
