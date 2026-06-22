# PR 2008 Fixed Mapping

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/34043b6a82a0.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Branch: `codex/dependency-security-inventory-2008`
- Base: `origin/main` at `feecc95dd`
- Worktree: `worktrees/pr2008-dependency-security-inventory`
- Role order executed pre-open:
  `agent-coordinator -> security-auditor -> qa-engineer-agent -> cursor-specialist-agent -> web-research-agent`
- Packet creation was treated as provenance only, not role execution.

## Scope Boundary

- In scope: `msgpack` `GHSA-6v7p-g79w-8964` remediation for repo-owned
  `requirements-dev.txt` and `requirements-lock.txt` pins, dependency security
  guard fixture, seven-alert Dependabot inventory, `msgpack` advisory doc,
  Dependabot cadence docs drift, and ledger-backed follow-up tracking.
- Out of scope: PR #2007 branch/files/review state, raw Dependabot PRs
  #2000-#2004, `requirements-ci-lite` changes without a proven current
  dependency path, faraday/Fastlane remediation, torch optional RAG/vector
  remediation, broad requirements cleanup, `requirements-all`, workflow changes,
  `verify_requirements.py`, pyproject/uv migration, and eval/data lock work.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Initial PR open: no human or bot review threads existed at artifact
  creation.
- [x] Initial fixed mapping artifact created after the implementation commit.
- [x] Post-open `qa-engineer-agent` pass completed.
- [x] Post-open `bug-hunter` pass completed.
- [x] Post-open `security-auditor` pass completed.
- [x] Codex Security diff scan / finding discovery completed.
- [x] `pulseplate-pr-review` completed.
- [x] Current actionable bot/review comments must be fixed or dispositioned
  before merge readiness.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: b3c3c4cd8a19574a047883fe43b62c9e317aad7d
Evidence: `requirements-dev.in`, `requirements-dev.txt`, `requirements-lock.txt`, `tests/fixtures/dependency_security_schema.json`, `docs/security/DEPENDABOT_ALERT_INVENTORY.md`, `docs/security/GHSA-6v7p-g79w-8964-msgpack.md`, `docs/DEPENDENCY_MANAGEMENT.md`, and `docs/roadmap/BACKLOG_LEDGER.md`.
Reason: Remediates the repo-owned vulnerable `msgpack` pins, blocks `msgpack <1.2.1` from returning through the dependency security guard, documents all seven current Dependabot alerts, records the raw Dependabot PR no-go, and tracks the ci-lite alert recheck plus broader dependency-surface contract as follow-up work.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2008 -> b3c3c4cd8a19574a047883fe43b62c9e317aad7d

## Premortem Closure

- Artifact:
  `artifacts/orchestration/premortem/pr2008-dependency-security-inventory-premortem.md`
- Decision: proceed with changes.
- Finding PM-2008-001 raw Dependabot PR drift:
  - Disposition: FIXED
  - Evidence: `docs/security/DEPENDABOT_ALERT_INVENTORY.md` records the no-go
    for raw Dependabot PRs #2000-#2004.
- Finding PM-2008-002 ci-lite msgpack scanner attribution:
  - Disposition: DEFERRED
  - Backlog:
    `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-msgpack-ci-lite-alert-recheck`
  - Evidence: `docs/security/GHSA-6v7p-g79w-8964-msgpack.md` documents the
    recheck boundary.
- Finding PM-2008-003 downgrade regression:
  - Disposition: FIXED
  - Evidence: `tests/fixtures/dependency_security_schema.json` blocks
    `msgpack <1.2.1`; `tests/test_dependency_security_guard.py` passes.
- Finding PM-2008-004 broad requirements cleanup collapse:
  - Disposition: DEFERRED
  - Backlog:
    `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-python-dependency-surface-contract`
  - Evidence: `docs/security/DEPENDABOT_ALERT_INVENTORY.md` names the future
    owner lane.
- Finding PM-2008-005 Dependabot cadence docs drift:
  - Disposition: FIXED
  - Evidence: `docs/DEPENDENCY_MANAGEMENT.md` now matches weekly/10 config.

## Experiment Runner Evidence

- Packet:
  `artifacts/orchestration/experiments/artifacts/orchestration/experiments/pr2008-dependency-security-inventory-packet.json`
- Artifact: `artifacts/orchestration/experiments/results/pr2008-dependency-security-inventory-result.json`
- Result:
  `artifacts/orchestration/experiments/results/pr2008-dependency-security-inventory-result.json`
- Status: accepted.
- Runner mode: `oracle_only_governance_reviewer`.
- Shared tree untouched: `true`.
- Source diff applied in isolated checkout: `true`.
- Source diff paths: 8.
- Failure class: `null`.
- Contribution kind: `commit_decision`.
- Co-author required: `true`.
- Commit trailer included in implementation commit
  `b3c3c4cd8a19574a047883fe43b62c9e317aad7d`:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.
- Oracle commands:
  - `git diff --check`
  - `python3 -m pytest -q tests/test_dependency_security_guard.py`
  - `make validate-changed`

## Dependency Delta Proof

- `requirements-dev.in`: adds `msgpack>=1.2.1,<2.0.0`.
- `requirements-dev.txt`: pins `msgpack==1.2.1`.
- `requirements-lock.txt`: pins `msgpack==1.2.1`.
- `tests/fixtures/dependency_security_schema.json`: blocks
  `msgpack <1.2.1`.
- Negative control: `requirements-ci-lite.in` and `requirements-ci-lite.txt`
  remain untouched by this PR.

## Local Validation Evidence

- PASS:
  `python3 scripts/orchestration/check_preflight.py --path requirements-dev.in --path requirements-dev.txt --path requirements-lock.txt --path tests/fixtures/dependency_security_schema.json --path docs/security --path docs/DEPENDENCY_MANAGEMENT.md --path docs/roadmap/BACKLOG_LEDGER.md`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python -m pytest -q tests/test_dependency_security_guard.py`
- PASS:
  `python3 scripts/ci/check_docs_phase1_gates.py --files docs/security/DEPENDABOT_ALERT_INVENTORY.md docs/security/GHSA-6v7p-g79w-8964-msgpack.md docs/DEPENDENCY_MANAGEMENT.md docs/roadmap/BACKLOG_LEDGER.md`
- PASS: `python3 scripts/ci/install_locked_python_requirements.py --preflight-only`
- PASS: `make validate-changed`
  - Note: this selected no Python/cross-surface tests for the final diff, so
    the focused dependency guard test is the changed-surface evidence.
- PASS: `pre-commit run --all-files`
- PASS: `git diff --cached --check`
- PASS: pre-push hook during `git push`, including pip-audit, backend pre-push
  pytest, and full-repo Bandit.

## Machine-Heavy Verification Deferral

Full local `make verify` was not run. The operator explicitly requested narrow
validation for this dependency-security lane. Merge readiness requires the
focused local gates above, pre-commit/pre-push evidence, current-head CI parity,
review-thread disposition, post-open role passes, Codex Security diff scan /
finding discovery, `pulseplate-pr-review`, strict merge-readiness checks with
auth, and the wait-window.

## Post-Open Review Disposition

- `qa-engineer-agent`
  - Disposition: PASS
  - Evidence: post-open role pass reported no findings.
- `bug-hunter`
  - Disposition: FIXED / NOT-A-BUG
  - Evidence: its check-state concerns were resolved by current-head CI passing
    on run `27985306636` for head
    `86e5b0c9b5a4b98d4a158cf5966284e530471c78`, including `lint`,
    `security`, `test-pr (3.13)`, `coverage-pr`, `diff-coverage`, PR body
    Phase 2 gates, docs Phase 1 gates, and merge-readiness gate. CodeRabbit was
    retriggered and reported no actionable comments.
- `security-auditor`
  - Disposition: PASS
  - Evidence: post-open role pass reported no security findings; it confirmed
    `msgpack` remediation on `requirements-dev.in`, `requirements-dev.txt`, and
    `requirements-lock.txt`, the `blocked_versions.msgpack` guard, and the
    `requirements-ci-lite` recheck boundary.
- `pulseplate-pr-review`
  - Disposition: NOT-A-BUG
  - Evidence: `pr_review_report.py` plus
    `tests/test_pr_review_report.py` passed under the resolved repo venv. The
    only advisory note was large-diff review risk (`357` changed lines), which
    is addressed by the split inventory/remediation scope, focused tests, role
    passes, and Codex Security module-scoped scan.

## Bot Review Disposition

- CodeRabbit:
  - Disposition: PASS / no actionables
  - Evidence:
    <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2008#issuecomment-4773113060>
    states "No actionable comments were generated in the recent review"; command
    reply
    <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2008#issuecomment-4773237735>
    states "Review finished."
- Sourcery:
  - Disposition: PASS / no actionables
  - Evidence:
    <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2008#issuecomment-4773113423>
    and the `Sourcery review` status check passed for the current head.
- Cubic:
  - Disposition: NOT-A-BUG
  - Evidence: `cubic - AI code reviewer` returned neutral/skipping status and
    no actionable inline comments were present.
- Codecov:
  - Disposition: PASS
  - Evidence:
    <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2008#issuecomment-4773209578>
    reports that all modified and coverable lines are covered.
- Codex connector review quota comment:
  - Disposition: NOT-A-BUG
  - Evidence:
    <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2008#issuecomment-4773112751>
    is an external review quota notice, not a code finding. It does not replace
    the Codex Security scan evidence below.

## Codex Security Evidence

- Scan id: `31875a98-b5b4-4d51-9558-04439300e95c`
- Workspace id: `4b4af96b-4d49-4413-9a6e-a69976cae476`
- Mode: `branch_diff` / module-scoped diff scan.
- Scope: PR #2008 dependency/security/governance files only; colleague-owned
  PR #2007 files were explicitly excluded as stale two-dot local-range noise and
  are not part of the GitHub PR #2008 file list.
- Result: PASS, `0` reportable findings, `9/9` reviewed rows closed.
- Report:
  `/private/var/folders/bw/12x002vn67v2bvjpbhbtm8480000gn/T/codex-security-scans-XiVaSW/pr2008-dependency-security-inventory/86e5b0c9b5a4b98d4a158cf5966284e530471c78_20260622T214943Z_uerlvlot/report.md`
- Advisory seed evidence: GitHub Advisory Database and OSV both identify
  `GHSA-6v7p-g79w-8964` as high severity, affected `msgpack <=1.2.0`, patched
  in `1.2.1`. Local Dependabot API evidence showed alerts #225, #226, and #227
  open before merge with patched version `1.2.1`.
- Local evidence: `requirements-dev.in:27`, `requirements-dev.txt:108`,
  `requirements-lock.txt:210`, and
  `tests/fixtures/dependency_security_schema.json:16`.

## Merge Readiness

- [ ] Current-head CI required checks pass with no pending required jobs after
  this mapping update commit and any final branch synchronization.
- [x] CodeRabbit, Sourcery, and Cubic have no actionable comments or every
  actionable has FIXED / NOT-A-BUG / DEFERRED disposition evidence.
- [x] `qa-engineer-agent -> bug-hunter -> security-auditor` post-open role
  pass completed.
- [x] Codex Security diff scan / finding discovery completed.
- [x] `pulseplate-pr-review` completed.
- [ ] Strict merge-readiness wrapper passes with auth.
- [ ] Final review-cycle wait completed after latest bot/review activity.
