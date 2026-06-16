# PR 1985 Fixed in Commit Mapping

## Lane Start Provenance

Packet: `artifacts/orchestration/task_packets/63a747529fee.json`
- Post-open packet: `artifacts/orchestration/task_packets/39f82da35c37.json`
- Branch: `codex/fix-frontend-dompurify-js-yaml-alerts`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Base: `origin/main` at `46d93e628444a5ef70e9283152297e98bb42a4e1`.
- Current PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1985>
- Role order executed pre-open:
  `agent-coordinator -> security-auditor -> frontend-engineer -> qa-engineer-agent -> bug-hunter -> architecture-specialist -> cursor-specialist-agent -> web-research-agent`
- Operator override: `main` was accepted for PR start while current-head jobs
  were pending without a new failed job.
- Operator approval: approved for frontend dependency security evidence lane.
- Frontend/backend mix approval: approved for frontend dependency manifests
  with security evidence docs.

## Scope Boundary

- In scope: frontend dependency manifest overrides, frontend lockfile
  regeneration for `dompurify` and `js-yaml`, frontend dependency guard tests,
  security evidence docs, and a backlog entry for the remaining out-of-scope
  Storybook `ws` audit finding.
- Out of scope: torch/RAG/vector policy, Bandit lower-severity inventory,
  Storybook `ws` remediation, backend runtime behavior, OpenAPI changes,
  frontend UI behavior, iOS/macOS, legacy routes, BMI/planning, FoodDB,
  premium, exports, and insight routes.
- Scope-governance proof: PR body records `Operator approval: approved` and
  `Frontend/backend mix approval: approved`; PR labels include
  `scope/operator-approved` and `scope/frontend-backend-mix-approved`.

## Premortem Closure

- Artifact:
  `artifacts/orchestration/premortem/63a747529fee_frontend_dependency_premortem.md`
- Decision: proceed with a narrow frontend dependency-security fix.
- `PM-1985-001`: false-green top-level package checks miss nested `js-yaml`.
  Disposition: FIXED. Evidence: `tests/test_frontend_dependency_guards.py`
  now scans every lock entry ending in `node_modules/js-yaml`, requires
  `>=4.2.0`, and rejects non-registry provenance.
- `PM-1985-002`: `npm audit` remains red because of unrelated `ws`.
  Disposition: DEFERRED. Backlog:
  `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-storybook-ws-ghsa-96hv`.
- `PM-1985-003`: lock regeneration could cause broad OpenAPI/tooling churn.
  Disposition: NOT-A-BUG. Evidence: only `frontend/package-lock.json` changed
  in the frontend lock surface, `npm run generate-types` produced no generated
  API diff, and frontend build/test gates passed locally.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/frontend-dompurify-js-yaml-oracle-packet.json`
- Artifact: `artifacts/orchestration/experiments/results/exp-8fde291e58c6.json`
- Status: accepted.
- Runner mode: `oracle_only_governance_reviewer`.
- Contribution kind: `oracle_review`.
- Co-author required: `true`.
- Source diff paths reviewed:
  `frontend/package.json`, `frontend/package-lock.json`,
  `tests/test_frontend_dependency_guards.py`, `docs/security/*dompurify*`,
  `docs/security/GHSA-h67p-54hq-rp68-js-yaml.md`, and
  `docs/roadmap/BACKLOG_LEDGER.md`.
- Oracles verified `dompurify==3.4.10`, all resolved `js-yaml==4.2.0`, no
  nested Redocly `js-yaml` lock entry, and `git diff --check`.
- Implementation commit `d3fc69d67fa61edc3de339e8fa88eeae7983737b` includes:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.

## Discussion Thread Pass

- [x] Discussion-thread pass completed for initial PR open.
- [x] Fixed in commit mapping completed
- [x] Post-open `qa-engineer-agent` pass completed.
- [x] Post-open `bug-hunter` pass completed.
- [x] Post-open `security-auditor` pass completed.
- [x] Codex Security diff scan / finding discovery completed.
- [x] CodeRabbit review completed when authenticated.
- [x] `pulseplate-pr-review` completed.
- [ ] Current actionable bot/review comments must be fixed or dispositioned
  before merge readiness.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: d3fc69d67fa61edc3de339e8fa88eeae7983737b
Evidence: `frontend/package.json`, `frontend/package-lock.json`, `tests/test_frontend_dependency_guards.py`, `docs/security/GHSA-39q2-94rc-95cp-dompurify.md`, `docs/security/CVE-2026-0540-dompurify.md`, `docs/security/GHSA-h67p-54hq-rp68-js-yaml.md`, and `docs/roadmap/BACKLOG_LEDGER.md`.
Reason: Raises DOMPurify and js-yaml security floors, narrows lockfile regeneration to the frontend dependency surface, adds deterministic guard coverage for every resolved js-yaml lock entry, refreshes advisory evidence, and records the separate Storybook `ws` residual as a follow-up.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1985 -> d3fc69d67fa61edc3de339e8fa88eeae7983737b

Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-storybook-ws-ghsa-96hv`
Evidence: `cd frontend && npm audit --audit-level=moderate --package-lock-only` reports only the out-of-scope Storybook `ws` advisory `GHSA-96hv-2xvq-fx4p`; target packages `dompurify`, `js-yaml`, `jspdf`, and `@redocly/openapi-core` are absent from the audit vulnerability set after this change.
Reason: The `ws` finding is not part of Dependabot alerts #164-#171 and needs a separate frontend tooling dependency lane to avoid broad Storybook churn in this PR.

## Role Review Finding Disposition

- `qa-engineer-agent`: PASS on the dependency-remediation surface and FIXED for
  local path hygiene before commit. Evidence: QA confirmed scoped lockfile
  changes, all-entry `js-yaml` guard coverage, registry provenance, documented
  `ws` deferral, and scope-governance labels/body. QA flagged local absolute
  paths in the uncommitted mapping update; those paths were removed before this
  artifact update.
- `bug-hunter`: PASS on nested lock-entry risk, npm override semantics,
  lockfile churn, residual audit wording, scope-governance proof, and
  parser/local docs checks. Evidence: bug-hunter confirmed the only remaining
  blockers were uncommitted mapping/body parity and current-head readiness, not
  dependency-security logic.
- `security-auditor`: PASS with no security-blocking findings. Evidence:
  security-auditor confirmed override floors, npm registry-backed lock
  provenance, deterministic guard coverage, no audit overclaim, live scope
  labels/body, Codex Security zero-findings evidence, CodeRabbit NOT-A-BUG
  disposition, and no absolute local path leakage.
- `Codex Security diff scan`: NOT-A-BUG. Evidence:
  scan bundle
  `codex-security-scans/fix-frontend-dompurify-js-yaml-alerts/bcf82a26ebef_20260616T182320Z`
  reports zero findings after reviewing the diff-scoped manifests, guard test,
  docs, backlog, and mapping artifact; report-format validation passed.
- `CodeRabbit CLI`: NOT-A-BUG for the minor suggestion to replace
  `.venv/bin/python -m pytest -q tests/test_frontend_dependency_guards.py`
  with `python3 -m pytest ...` in
  `docs/security/GHSA-39q2-94rc-95cp-dompurify.md`. Evidence:
  `AGENTS.md` states direct local pytest runs outside Make should use the repo
  virtualenv, `AGENTS.md` also says to use `.venv/bin/python` for repo Python
  commands and coordinator bootstrap, and `Makefile` defines
  `VENV_PYTHON ?= .venv/bin/python`. Reason: the documented validation command
  intentionally matches repo Python gate conventions and the operator-approved
  PR validation plan.
- `pulseplate-pr-review`: NOT-A-BUG for the advisory large-diff note. Evidence:
  local report `pulseplate_pr1985_review_report.md` flags only review-planning evidence
  for a diff above the 300-line review-risk threshold; this artifact documents
  the split rationale and scope exception, `make validate-changed` passed, and
  `.venv/bin/python -m pytest tests/test_pr_review_report.py -q` passed.

## Dependency Delta Proof

- `frontend/package.json` override: `dompurify` -> `3.4.10`.
- `frontend/package.json` override: `js-yaml` -> `4.2.0`.
- Lock proof: `node_modules/dompurify` resolves to `3.4.10` from
  `https://registry.npmjs.org/dompurify/-/dompurify-3.4.10.tgz`.
- Lock proof: `node_modules/js-yaml` resolves to `4.2.0` from
  `https://registry.npmjs.org/js-yaml/-/js-yaml-4.2.0.tgz`.
- Negative control: no nested
  `node_modules/@redocly/openapi-core/node_modules/js-yaml` lock entry remains.

## Local Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS:
  `.venv/bin/python -m pytest -q tests/test_frontend_dependency_guards.py tests/test_ci_workflow_pr_size_governance_contract.py::test_node24_runtime_baseline_surfaces_stay_coherent`
- PASS:
  `python3 scripts/ci/check_docs_phase1_gates.py --files docs/security/GHSA-h67p-54hq-rp68-js-yaml.md docs/security/GHSA-39q2-94rc-95cp-dompurify.md docs/security/CVE-2026-0540-dompurify.md docs/roadmap/BACKLOG_LEDGER.md`
- PASS: `cd frontend && npm install --package-lock-only --ignore-scripts`
- PASS: `cd frontend && npm ci --ignore-scripts`
- PASS: `cd frontend && npm ls dompurify js-yaml --package-lock-only --all`
- PASS: `cd frontend && npm run build`
- PASS: `cd frontend && npm run test:ci`
- PASS:
  `cd frontend && npm run generate-types && git diff --exit-code src/api/openapi.json src/api/schema.ts`
- DEFERRED/OUT-OF-SCOPE:
  `cd frontend && npm audit --audit-level=moderate --package-lock-only`
  still reports Storybook `ws` advisory `GHSA-96hv-2xvq-fx4p`; tracked in
  backlog as `ledger-p1-storybook-ws-ghsa-96hv`.
- PASS: target-audit classifier confirmed `dompurify`, `js-yaml`, `jspdf`, and
  `@redocly/openapi-core` are absent from `npm audit --json`
  vulnerabilities.
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS during push hooks: frontend tests, backend changed-file pytest,
  `pip-audit`, full-repo Bandit, and docker build test.

## Machine-Heavy Verification Deferral

Full local `make verify` was not run. This PR uses the operator-approved
machine-heavy exception for a narrow frontend dependency-security lane. Merge
readiness requires the focused local gates above, pre-commit/pre-push evidence,
current-head CI parity, review-thread disposition, strict merge-readiness
checks with auth, and the wait-window.

## Merge Readiness

Not ready at latest artifact update. Required before merge:

- [ ] Numbered fixed-mapping artifact committed and PR body mirror updated.
- [x] Post-open role-agent review sequence completed.
- [x] Codex Security diff scan / finding discovery completed.
- [ ] CodeRabbit/Sourcery/Cubic actionable comments fixed or dispositioned.
- [x] `pulseplate-pr-review` completed.
- [ ] Current-head CI parity on latest pushed commit.
- [ ] Strict merge-readiness check with `--require-auth`.
- [ ] No unresolved actionable review or bot comments.
- [ ] Mandatory wait-window after latest bot/review activity.
