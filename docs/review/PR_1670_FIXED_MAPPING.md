# PR #1670 Fixed in Commit Mapping

## Summary

PR #1670 remediates GitHub Code Scanning alert #590 for `libgnutls30` / `CVE-2026-33846` in the production Docker image as far as Debian bookworm currently permits.

## Scope

- `Dockerfile`
- `.trivyignore`
- `trivy/ignore-policy.rego`
- `docs/security/CVE-2026-33846-gnutls.md`
- `docs/security/CVE-2026-33845-gnutls.md`
- `docs/security/CVE-2025-14831-gnutls.md`
- `docs/roadmap/BACKLOG_LEDGER.md`

## Role Order

- [x] Declared role order preserved: `agent-coordinator -> security-auditor -> dev-operator -> architecture-specialist -> qa-engineer-agent -> bug-hunter`
- [x] Pre-open coordinator packet: `555101d9887b`
- [x] Post-open coordinator packet with declared order: `16c5c048a51f`
- [x] Mandatory post-open review lane included: `qa-engineer-agent -> bug-hunter`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- No actionable review comments

## Security Alert Disposition

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/code-scanning/590 -> da8e636a57ad5f7432b004c8a64d220449ebe481
Disposition: FIXED
Commit: da8e636a57ad5f7432b004c8a64d220449ebe481
Evidence: `Dockerfile:136` and `Dockerfile:146` explicitly install `libgnutls30` from bookworm-security; local production image inventory shows `libgnutls30:arm64 3.7.9-2+deb12u6`; `docs/security/CVE-2026-33846-gnutls.md` documents the remaining upstream-unfixed bookworm risk.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/code-scanning/590 -> da8e636a57ad5f7432b004c8a64d220449ebe481
Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-remove-trivy-suppression-gnutls-cve-2026-33846`
Reason: Debian still marks bookworm/bookworm-security vulnerable for `CVE-2026-33846` and reports a fixed version only for unstable `3.8.13-1` at triage time. The residual HIGH finding is temporarily accepted through exact package/version Rego policy until a fixed bookworm package exists.

## Premortem Summary

Frame: It is 48 hours after this container security PR merged. GitHub still reports CVE-2026-33846 or a worse runtime image regression appeared. Why?

- Different image target scanned: addressed by building and checking `--target production`, matching `.github/workflows/trivy.yml`.
- Fix misses final production image: addressed by final production image inventory after rebuild.
- Suppression hides real HIGH finding: addressed with exact CVE/package/version/PkgID Rego policy and a remove-by window.
- Package removal breaks apt/TLS: avoided; `libgnutls30` remains installed because `apt` depends on it.
- Adjacent GnuTLS policy drift: addressed by updating `CVE-2026-33845` waiver to `3.7.9-2+deb12u6` and marking `CVE-2025-14831` resolved for production image.
- CI scans a different target: current repo `.github/workflows/trivy.yml` builds and scans `target: production`; current-head CI remains required before merge readiness.

Decision: proceed with changes; do not claim full remediation until Debian bookworm publishes a fixed package.

## Validation

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/orchestration/task_bootstrap.py --pr-phase pre_open ...` -> packet `555101d9887b`
- PASS: `python3 scripts/orchestration/task_bootstrap.py --pr-phase post_open_review ...` -> packet `16c5c048a51f`
- PASS: `docker build --pull --target production ... -t pulseplate:gnutls-check .`
- PASS: production image package inventory shows `libgnutls30:arm64 3.7.9-2+deb12u6`
- PASS: container `/health` smoke on alternate host port 8009 returned `{"status":"ok", ... "environment":"ci"}`
- PASS: `python3 scripts/ci/check_trivy_ignore_policy_expiry.py`
- PASS: `python3 scripts/ci/check_docs_phase1_gates.py --files docs/security/CVE-2026-33846-gnutls.md docs/security/CVE-2026-33845-gnutls.md docs/security/CVE-2025-14831-gnutls.md`
- PASS: `git diff --check`
- PASS: `pre-commit run --all-files`
- PASS: `make validate-changed`
- PASS: pre-push hooks: `pip-audit`, backend pre-push pytest, full-repo Bandit, docker build test
- LOCAL GAP: `trivy` CLI unavailable locally (`TRIVY_LOCAL_UNAVAILABLE`); require GitHub current-head Trivy/Code Scanning evidence before merge-readiness claim.
- DEFERRED: full `make verify` / `make diff-cov` because the diff-cover path runs full `coverage run -m pytest -q` across the 11k-test suite. Partial full verify before operator stop passed `verify-env`, `flake8`, `mypy`, and `test-fast`.

## Merge Readiness

- [ ] Current-head CI green
- [ ] GitHub Trivy / Code Scanning confirms alert #590 is closed or correctly suppressed on current head
- [x] Review mapping artifact created
- [ ] No actionable bot comments remain
- [ ] Strict merge wrapper passes with auth
- [ ] Mandatory wait-window elapsed

## Phase2 Body Mirror Follow-up

- PASS: `python3 scripts/ci/check_pr_body_phase2_gates.py --body "$(cat /tmp/gnutls-pr-body-live.md)" --pr-number 1670` after updating the live PR body to include the exact required checklist item `Discussion-thread pass completed`.
- Reason: the first PR-body CI run used an older event body snapshot with extra wording after the required checklist text; live body now matches the Phase2 contract.
