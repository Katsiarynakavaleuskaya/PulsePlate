# PR 2081 - Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2081

Branch: `codex/fix-trivy-ignore-policy-expiry`

## Summary

This PR refreshes the Trivy ignore-policy lane before returning to Dependabot
#2078 / pyarrow work. It removes the resolved Faraday scanner-lag suppression,
keeps residual Debian bookworm base-image suppressions exact-scoped, and records
production security evidence without touching runtime code, Python lockfiles,
Dockerfile, workflows, or broad `.trivyignore` entries.

## Discussion Thread Pass

- [x] Fixed mapping artifact created after GitHub assigned PR number `#2081`.
- [ ] Discussion-thread pass pending post-open bot/reviewer activity.
- [ ] Fixed in commit mapping pass pending any actionable post-open comments.
- [ ] Current-head GitHub CI/security checks pending.

## Fixed in Commit Mapping

No actionable PR review threads have been resolved yet.

## Implementation Evidence

- Commit: `040dfdd80302679845c9f6628afa45f0a850cc7a`
- Evidence: `trivy/ignore-policy.rego` no longer contains Faraday
  `CVE-2026-54297`, `GHSA-98m9-hrrm-r99r`, `faraday@1.10.5`,
  `faraday@1.10.6`, or `pkg:gem/faraday` suppression text.
- Evidence: retained `zlib1g`, util-linux family, and ncurses family rules
  remain restricted to exact CVE/package/version/PkgID scope and review-by
  `2026-07-12`.
- Evidence: `tests/test_trivy_ignore_policy_expiry.py` prevents Faraday
  suppression reintroduction in Rego or `.trivyignore` and verifies
  `faraday 1.10.6` remains locked only by `ios/Gemfile.lock`.
- Evidence: security docs and `docs/roadmap/BACKLOG_LEDGER.md` separate the
  removed Faraday scanner-lag item from residual Debian base-image suppressions.
- Evidence: `docs/review/PR_TRIVY_IGNORE_POLICY_HOTFIX_PREMORTEM.md` records the
  production premortem for hidden CVE risk, false-positive release blocking,
  Fastlane tooling risk, and local-vs-GitHub scanner divergence.

## Codex Security Evidence

- Scan id: `fe3170a1-534d-4b15-a06b-1b2da52f3a62`
- Base: `632076f92fb85156399124b520ab30c907a83194`
- Head: `040dfdd80302679845c9f6628afa45f0a850cc7a`
- Coverage: 9/9 review receipts
- Findings: 0
- Report:
  `/private/var/folders/bw/12x002vn67v2bvjpbhbtm8480000gn/T/codex-security-scans-vpvqlm/BMI-App_2025_clean/040dfdd80302679845c9f6628afa45f0a850cc7a_20260705T121222Z_10s06wz4/report.md`

Limitation: local GitHub code-scanning and Dependabot alert REST endpoints
returned HTTP 404 in this session, so this PR does not claim GitHub alert
closure before current-head GitHub CI/security evidence.

## Experiment Runner Evidence

- Artifact:
  `artifacts/orchestration/experiments/results/exp-trivy-ignore-policy-hotfix-oracle-network1-result.json`
- Result: `accepted`
- Shared tree: untouched
- Source diff applied: false
- Oracle commands passed:
  - `python3 scripts/ci/check_trivy_ignore_policy_expiry.py`
  - `python3 -m pytest -q tests/test_trivy_ignore_policy_expiry.py`
  - `git diff --check`

Infra caveat: the first zero-network local attempt was rejected because this
macOS host does not provide `unshare` for the network-disabled sandbox. The
accepted `network_budget=1` fallback kept local oracle commands only. No
Experiment Runner co-author trailer is required because the accepted oracle ran
after the implementation commit and did not materially shape that commit.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/9dcf5d232ef5.json`
- Branch: `codex/fix-trivy-ignore-policy-expiry`
- Pre-open route completed:
  `agent-coordinator -> security-auditor -> qa-engineer-agent -> bug-hunter -> architecture-specialist`
- Post-open route is still pending:
  `qa-engineer-agent -> bug-hunter -> security-auditor`, followed by
  Codex Security evidence reuse/review and `pulseplate-pr-review`.

## Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`
  - Warning observed: ambient `PULSEPLATE_PYTHON_INDEX_URL` does not match the
    canonical private proxy root shape.
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/ci/check_trivy_ignore_policy_expiry.py`
- PASS: `.venv/bin/python -m pytest -q tests/test_trivy_ignore_policy_expiry.py`
  (`14 passed`)
- PASS:
  `python3 scripts/ci/check_docs_phase1_gates.py --files docs/security/CVE-2026-54297-faraday-fastlane.md docs/security/CVE-2026-27171-zlib1g.md docs/security/CVE-2026-3184-util-linux.md docs/security/CVE-2025-69720-ncurses.md`
- PASS: `.venv/bin/python -m pytest -q tests/test_docs_phase1_gates.py`
  (`47 passed`)
- PASS: `git diff --check`
- PASS: `make validate-changed` after commit (`14 passed`)
- PASS: `pre-commit run --all-files`
- PASS during push: pre-push hooks, including `pip-audit`,
  backend tests, and full Bandit.

Docker / Trivy evidence:

- PASS: production image build with Docker server `29.5.3`, tag
  `pulseplate:trivy-local-632076f9`.
- PASS: Trivy `0.71.2` filesystem scan with `.trivyignore` and skip-dirs
  `trivy`/`worktrees` returned zero HIGH/CRITICAL findings.
- PASS: Trivy `0.71.2` iOS filesystem no-policy scan returned zero
  HIGH/CRITICAL findings and zero targeted Faraday findings.
- Evidence: Trivy `0.71.2` production-image no-policy all-severity scan still
  reports 13 targeted residual Debian findings for zlib/util-linux/ncurses.
- PASS: Trivy `0.71.2` production-image scan with policy returned zero
  HIGH/CRITICAL findings.

Not run:

- `make verify` was not run because root `AGENTS.md` forbids full local
  `make verify` without explicit human override.

## Merge Readiness

Not claimed here. Requires current-head GitHub CI/security checks, post-open
role chain completion, `pulseplate-pr-review`, bot/review disposition evidence,
and strict merge-readiness governance after the latest pushed head.
