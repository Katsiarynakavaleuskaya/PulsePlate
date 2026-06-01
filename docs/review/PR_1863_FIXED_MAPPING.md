# PR #1863 - Fixed in Commit Mapping

**Title:** `fix(security): disposition Trivy perl-base CVE`
**Branch:** `codex/security-trivy-cve-2026-48962-perl-base`
**Scope:** Time-boxed Trivy Rego policy disposition for GitHub code-scanning
alert #602 / `CVE-2026-48962` / `perl-base 5.36.0-7+deb12u3`.
**Primary commit:** `afb1b2412962`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [ ] Post-open bot/human review disposition pending.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1863 -> afb1b2412962
Disposition: FIXED
Commit: afb1b2412962
Evidence: `trivy/ignore-policy.rego` adds exact CVE/package/version/PkgID policy matching; `tests/test_trivy_ignore_policy_expiry.py` proves exact matching, no `.trivyignore` entry, and doc/ledger coupling; `docs/security/CVE-2026-48962-perl-base.md` documents alert evidence and removal conditions; `docs/roadmap/BACKLOG_LEDGER.md` tracks remediation debt.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1863#discussion_r3335451980 -> f604c5aae
Disposition: FIXED
Commit: f604c5aae
Evidence: `docs/review/PR_TRIVY_602_PREMORTEM.md` title now uses `PR #1863`, replacing the `PR TBD` placeholder.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1863#discussion_r3335451993 -> c7be0fb64169
Disposition: FIXED
Commit: c7be0fb64169
Evidence: `docs/review/PR_TRIVY_602_PREMORTEM.md` now includes Discussion Thread Pass, Fixed in Commit Mapping, Merge Readiness, and the canonical `docs/review/PR_1863_FIXED_MAPPING.md` reference.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1863#pullrequestreview-4402674945 -> c7be0fb64169
Disposition: FIXED
Commit: c7be0fb64169
Evidence: `tests/test_trivy_ignore_policy_expiry.py` now uses a safe fallback to the end of `BACKLOG_LEDGER.md` when no later anchor exists, and the premortem PR title/linkage feedback is addressed.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1863#discussion_r3335468861 -> c7be0fb64169
Disposition: FIXED
Commit: c7be0fb64169
Evidence: `docs/review/PR_1863_FIXED_MAPPING.md` now says the validation plan required focus on Trivy policy guards.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1863#discussion_r3335478528
Disposition: NOT-A-BUG
Evidence: `git merge-base --is-ancestor afb1b2412962 HEAD` exits 0 on branch head `c7be0fb64169`, so the implementation SHA is reachable in the real PR branch history.
Reason: The bot compared `afb1b2412962` to a synthetic reviewed commit surface rather than the current branch head; the mapping remains valid for the actual PR history.

## Implementation Evidence

Disposition: FIXED
Commit: `afb1b2412962`
Evidence:

- `trivy/ignore-policy.rego:104` documents `Review-by: 2026-06-27` and removal
  conditions for the CVE-specific policy rule.
- `trivy/ignore-policy.rego:119` requires `input.VulnerabilityID`,
  `input.PkgName`, `InstalledVersion`, and `PkgID` constraints before ignoring.
- `tests/test_trivy_ignore_policy_expiry.py:136` asserts the exact policy
  contract and single file-level expiry marker.
- `tests/test_trivy_ignore_policy_expiry.py:150` asserts `CVE-2026-48962` is
  not present in `.trivyignore`.
- `tests/test_trivy_ignore_policy_expiry.py:156` asserts security-doc and
  backlog coupling.
- `docs/security/CVE-2026-48962-perl-base.md:13` states this is not upstream
  remediation and keeps the vulnerable package debt visible.
- `docs/security/CVE-2026-48962-perl-base.md:82` defines removal conditions.
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-container-perl-cve-remediation`
  tracks the Perl-family remediation path.

## Role-Agent / Premortem Pass

Pre-open read-only role order completed before implementation:

- `agent-coordinator` - completed; scope locked to Trivy alert #602 policy
  disposition and required role order.
- `dev-operator` - completed; validation plan required focus on Trivy policy
  guards, docs gate, `make validate-changed`, pre-commit, and current-head
  Docker/Trivy/SARIF follow-up.
- `architecture-specialist` - completed; confirmed no API, runtime,
  Dockerfile, workflow, frontend, iOS, or dependency changes.
- `security-auditor` - completed; required exact Rego matching, no
  `.trivyignore`, explicit expiry/review/removal conditions, and no remediation
  overclaim.
- `qa-engineer-agent` - completed; required static exactness tests,
  doc/ledger coupling, and local-tooling limitation disclosure.
- `bug-hunter` - completed; checked false-green, broad suppression, stale
  metadata, and local Docker/Trivy availability risks.
- `pulseplate-premortem-risk-review` - completed in
  `docs/review/PR_TRIVY_602_PREMORTEM.md`; decision: proceed with changes.

Post-open role order is pending:

- [ ] `qa-engineer-agent`
- [ ] `bug-hunter`
- [ ] `security-auditor`
- [ ] `pulseplate-pr-review`

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/exp-ceb1c324038e.json`
- Result: `artifacts/orchestration/experiments/results/exp-ceb1c324038e.json`
- Mode: `oracle_only_governance_reviewer`
- Result: accepted; 3/3 oracle commands passed; `mutated_paths=[]`;
  `source_diff_paths` covered the five PR files; `coauthor_required=true`.
- Commit trailer used on `afb1b2412962`:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/dbd80258a382.json`

## Codex Security Diff Scan

- Report: `/tmp/codex-security-scans/BMI-App_2025_clean/345ef2a8a791_20260601T154118Z/report.md`
- HTML: `/tmp/codex-security-scans/BMI-App_2025_clean/345ef2a8a791_20260601T154118Z/report.html`
- Result: no reportable findings.
- Coverage: five staged PR files recorded in
  `/tmp/codex-security-scans/BMI-App_2025_clean/345ef2a8a791_20260601T154118Z/artifacts/02_discovery/work_ledger.jsonl`.

## Local Validation

- `python3 scripts/orchestration/check_preflight.py --path docs/review/PR_TRIVY_602_PREMORTEM.md --path docs/roadmap/BACKLOG_LEDGER.md --path docs/security/CVE-2026-48962-perl-base.md --path tests/test_trivy_ignore_policy_expiry.py --path trivy/ignore-policy.rego` - PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- `python3 scripts/ci/check_trivy_ignore_policy_expiry.py` - PASS.
- `.venv/bin/python -m pytest -q tests/test_trivy_ignore_policy_expiry.py` - PASS.
- `python3 scripts/ci/check_docs_phase1_gates.py --files docs/security/CVE-2026-48962-perl-base.md` - PASS.
- `make validate-changed` - PASS.
- `.venv/bin/pre-commit run --all-files` - PASS after Black reformatted
  `tests/test_trivy_ignore_policy_expiry.py` and the hook was rerun.
- Pre-push hooks - PASS, including pip-audit, backend tests, and full-repo
  Bandit; Docker build hook skipped because no Docker-surface files changed.
- `docker info` - unavailable locally because the Docker daemon socket was not
  present.
- `trivy`, `opa`, and `conftest` - unavailable locally.

## Machine-Heavy Gate Deferral

Full local `make verify` is not claimed for this security/container governance
lane. This PR uses the operator-approved machine-heavy exception: all scoped
local gates above passed, and current-head CI/Docker/Trivy/SARIF evidence must
be checked before any readiness claim.

## Merge Readiness

Not merge-ready. Pending:

- Current-head CI.
- Current-head Docker/Trivy/SARIF evidence and alert #602 verification.
- Post-open `qa-engineer-agent -> bug-hunter -> security-auditor`.
- `pulseplate-pr-review`.
- CodeRabbit, Sourcery, and Cubic disposition.
- `check_review_threads_disposition.py --require-auth`.
- Strict merge-readiness wrapper.
- Mandatory wait-window after the latest review activity.
