# PR 1968 Fixed in Commit Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1968>

## Summary

This PR stabilizes the Docker publish path after PR #1935 correctly blocked
post-merge GHCR publish on Trivy alert `#610` / `CVE-2026-48959`. The hotfix
adds a temporary exact Rego policy disposition for the observed `perl-base`
finding without weakening fail-closed Trivy scan behavior.

## Lane Start Provenance

- Branch: `codex/stabilize-main-trivy-perl-base-cve-2026-48959`
- PR phase: `post_open_review`
- Implementation commit: `1d47d65c7aecba1700fa341b0b60fee30b3500a0`
- Sourcery doc-clarity fix commit: `1a37e7820a3764d3e11e383f5600841ed324ae78`
- Packet: `artifacts/orchestration/task_packets/7d26be3d0cc9.json`
- Pre-open packet: `artifacts/orchestration/task_packets/6338fa0a7e51.json`
- Post-open packet: `artifacts/orchestration/task_packets/7d26be3d0cc9.json`
- Machine-heavy exception: full local `make verify` is intentionally deferred
  under the operator-approved CI/tooling machine-heavy exception. Focused local
  gates plus current-head CI and Docker publish evidence are required.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Sourcery review feedback mapped with FIXED disposition.
- [x] Re-check review threads after resolving the mapped Sourcery discussion.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1968#discussion_r3405939500 -> 1a37e7820a3764d3e11e383f5600841ed324ae78
Disposition: FIXED
Commit: 1a37e7820a3764d3e11e383f5600841ed324ae78
Evidence: `docs/security/CVE-2026-48959-perl-base.md:31` replaces the ambiguous `lane` wording with `finding` for the blank fixed-version disposition.
Reason: Sourcery flagged the wording as a typo; the committed doc text now uses the reviewed finding terminology.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1968#pullrequestreview-4488809272 -> 1a37e7820a3764d3e11e383f5600841ed324ae78
Disposition: FIXED
Commit: 1a37e7820a3764d3e11e383f5600841ed324ae78
Evidence: `docs/security/CVE-2026-48959-perl-base.md:63` names `trivy/ignore-policy.rego`; `docs/security/CVE-2026-48959-perl-base.md:64` documents the generated `.trivy-ignore-policy.rego` path used by `.github/workflows/build.yml:441`.
Reason: Sourcery flagged a policy-path ambiguity; the committed doc text now separates source policy path from the workflow-generated Trivy path.

## Scope

IN:

- `trivy/ignore-policy.rego`
- `docs/security/CVE-2026-48959-perl-base.md`
- `tests/test_trivy_ignore_policy_expiry.py`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `docs/review/PR_1968_FIXED_MAPPING.md`

OUT:

- Dockerfile/base-image migration.
- Workflow or Trivy fail-closed behavior changes.
- `.trivyignore` broad CVE-only suppression for `CVE-2026-48959`.
- Product runtime, API, OpenAPI, frontend, or iOS changes.

## Role Dispatch Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/orchestration/task_bootstrap.py ... --pr-phase pre_open`
- PASS: `python3 scripts/orchestration/task_bootstrap.py ... --pr-phase post_open_review`
- Declared pre-open role order executed:
  `agent-coordinator -> security-auditor -> qa-engineer-agent -> bug-hunter -> architecture-specialist`.
- `agent-coordinator`: constrained the hotfix to exact Rego policy, security doc,
  tests, and backlog tracking.
- `security-auditor`: accepted only a temporary exact policy disposition and
  required CVE/package/version/PkgID/fixed-version-unavailable matching.
- `qa-engineer-agent`: required negative controls for populated `FixedVersion`,
  no `.trivyignore` entry, and remote Docker publish proof.
- `bug-hunter`: identified stale anchor and false-suppression risks; the new doc
  uses current anchors and tests include negative canary cases.
- `architecture-specialist`: confirmed this is policy/docs/tests/backlog only,
  with no Dockerfile/workflow/app changes.
- Mandatory post-open review stack executed after bot review:
  `qa-engineer-agent -> bug-hunter -> security-auditor`.
- Post-open `qa-engineer-agent`: no QA/test-sufficiency blocker; identified
  Sourcery mapping/disposition as the remaining governance blocker.
- Post-open `bug-hunter`: no Rego/Trivy implementation blocker; confirmed the
  Sourcery feedback was documentation clarity and mapping/disposition work.
- Post-open `security-auditor`: no blocking or nonblocking findings; confirmed
  the suppression remains exact, `.trivyignore` is not broadened, fail-closed
  publish behavior is unchanged, and docs/mapping do not claim premature proof.
- Codex Security diff scan: current-head report
  `/tmp/codex-security-scans/PulsePlate-main-trivy-hotfix/1b6fbf4b8b00_20260612T210539Z/report.md`
  validated with zero reportable findings.
- `pulseplate-pr-review`: dry-run report generated at
  `/tmp/pr1968_pr_review_report.md`; calibration tests passed.

## Premortem Finding Closure

- `PM-1968-001` Suppression is too broad and hides future fixed versions.
  Disposition: FIXED.
  Evidence: commit `1d47d65c7aecba1700fa341b0b60fee30b3500a0` matches exact CVE,
  package, installed version, PkgID prefix, and absent/empty/null `FixedVersion`.
- `PM-1968-002` Hotfix weakens the fail-closed publish gate.
  Disposition: NOT-A-BUG.
  Evidence: no `.github/workflows/*` files changed; PR #1935 publish gate remains
  fail-closed.
- `PM-1968-003` Temporary suppression becomes untracked debt.
  Disposition: FIXED.
  Evidence: `docs/roadmap/BACKLOG_LEDGER.md` tracks alert `#610`, removal
  conditions, and the Perl-family remediation deadline.
- `PM-1968-004` Local tests cannot prove GitHub publish SARIF behavior.
  Disposition: NOT-A-BUG.
  Evidence: current-head Docker publish evidence is required before merge.
- `PPR-1968-001` `pulseplate-pr-review` advisory large-diff note.
  Disposition: NOT-A-BUG.
  Evidence: current GitHub PR diff contains the five intended files only;
  `make validate-changed` passed; Codex Security current-head diff scan found
  zero reportable findings; the line count is expected for a security note plus
  canonical mapping artifact and does not indicate an unscoped implementation
  expansion.

## Experiment Runner Evidence

- Artifact:
  `artifacts/orchestration/experiments/results/artifacts/orchestration/experiments/results/pr-main-cve-2026-48959-oracle-result.json`
- Experiment ID: `exp-8a06dbffc0b9`
- Mode: `oracle_only_governance_reviewer`
- Status: `accepted`
- Contribution: `oracle_review`
- Co-author required: `true`; implementation commit uses
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.

## Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py --path docs/roadmap/BACKLOG_LEDGER.md --path docs/security/CVE-2026-48959-perl-base.md --path tests/test_trivy_ignore_policy_expiry.py --path trivy/ignore-policy.rego`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/ci/check_trivy_ignore_policy_expiry.py`
- PASS: `python -m pytest -q tests/test_trivy_ignore_policy_expiry.py` (`12 passed`).
- PASS: `python scripts/ci/check_docs_phase1_gates.py --files docs/security/CVE-2026-48959-perl-base.md`
- PASS: focused workflow contract pytest for publish scan and Trivy action
  contracts (`3 passed`).
- PASS: `git diff --check`
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS: commit hooks and pre-push hooks with repo-approved `VENV_PYTHON`.
- PASS: Sourcery doc-clarity focused rerun after commit
  `1a37e7820a3764d3e11e383f5600841ed324ae78`:
  `python3 scripts/ci/check_trivy_ignore_policy_expiry.py`,
  `python -m pytest -q tests/test_trivy_ignore_policy_expiry.py`
  (`12 passed`), `python scripts/ci/check_docs_phase1_gates.py --files
  docs/security/CVE-2026-48959-perl-base.md`, `git diff --check`,
  `make validate-changed`, and `pre-commit run --all-files`.
- PASS: after merging latest `origin/main` to current head
  `1b6fbf4b8b00bc5b7f9776b9f6bd320817326f97`:
  `python3 scripts/orchestration/check_preflight.py --path ...`,
  `python3 scripts/orchestration/check_agent_consistency.py`,
  `python3 scripts/ci/check_trivy_ignore_policy_expiry.py`,
  `python -m pytest -q tests/test_trivy_ignore_policy_expiry.py`
  (`12 passed`), `python scripts/ci/check_docs_phase1_gates.py --files
  docs/security/CVE-2026-48959-perl-base.md`, `git diff --check`,
  `make validate-changed`, `pre-commit run --all-files`, and pre-push hooks.
- PASS: `python3 -m pytest tests/test_pr_review_context.py
  tests/test_pr_review_report.py -q` (`13 passed`) with repo venv.
- NOT RUN: full local `make verify`; intentionally deferred under the
  operator-approved machine-heavy exception.

## Deferred / Follow-ups

- Existing backlog item `ledger-p1-container-perl-cve-remediation` tracks
  removal through fixed Debian package, base-image migration, or runtime Perl
  removal.

## Merge Readiness

- [x] Real implementation commit exists.
- [x] Canonical fixed-mapping artifact exists.
- [x] Focused local gates passed.
- [x] Full local `make verify` deferral is documented.
- [x] Post-open role loop completed after bot review.
- [ ] `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 1968 --body "$(gh pr view 1968 --repo Katsiarynakavaleuskaya/PulsePlate --json body --jq .body)"` passes after this artifact update is mirrored to the PR body.
- [ ] `GH_TOKEN="$(gh auth token)" python3 scripts/orchestration/check_review_threads_disposition.py --pr-number 1968 --require-auth` passes after this artifact update is pushed.
- [ ] `GH_TOKEN="$(gh auth token)" GITHUB_TOKEN="$(gh auth token)" python3 scripts/orchestration/check_merge_ready.py --pr-number 1968 --repo Katsiarynakavaleuskaya/PulsePlate --require-auth` passes.
- [ ] Current-head PR CI is green.
- [ ] Docker publish path proves Trivy/SARIF passes before GHCR publish on the
  relevant current head.
