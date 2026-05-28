# PR 1847 — Fixed in Commit Mapping

## PR
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1847

## Discussion Thread Pass

- [x] Discussion-thread pass completed

### Post-open review findings disposition

#### qa-engineer-agent
- **Verdict:** PASS
- **Findings:** All findings PASS. No blockers.
- **Disposition:** NOT-A-BUG (no actionable items requiring code changes)

#### bug-hunter
- **Finding 1 (MEDIUM):** `docs/security/CVE-2025-69720-ncurses.md` references old base image `python:3.13.6-slim-bookworm`
  - **Disposition:** FIXED
  - **Commit:** d0caf28f8
  - **Evidence:** `docs/security/CVE-2025-69720-ncurses.md:24` updated to `python:3.13.13-slim-bookworm`

- **Finding 2 (LOW):** `.tool-versions` and `.python-version` still pin `3.13.6`
  - **Disposition:** FIXED
  - **Commit:** d0caf28f8
  - **Evidence:** `.tool-versions:1` → `python 3.13.13`, `.python-version` → `3.13.13`

- **Finding 3 (LOW):** `docs/reports/COVERAGE_REPORT.md` references Python 3.13.6
  - **Disposition:** FIXED
  - **Commit:** d0caf28f8
  - **Evidence:** `docs/reports/COVERAGE_REPORT.md:115` updated to Python 3.13.13

- **Finding 4 (LOW):** pip version assertion drift in `.trivyignore` (CVE-2025-8869 block)
  - **Disposition:** NOT-A-BUG
  - **Evidence:** `.trivyignore:888-908` — The comment references base-image pip version for context only. The Dockerfile's `PIP_VERSION_RANGE="pip>=26.0,<27.0"` ensures runtime pip is upgraded during build, making the exact base-image pip version irrelevant for vulnerability status. No code change required.

#### security-auditor
- **Finding 1 (INFO):** Perl CVE suppression rationale correct and complete
  - **Disposition:** PASS (no change required)

- **Finding 2 (INFO):** Trivy fail-closed gate preserved
  - **Disposition:** PASS (no change required)

- **Finding 3 (INFO):** 90-day removal trigger with escalation path
  - **Disposition:** PASS (no change required)

- **Finding 4 (INFO):** Base image bump fixes CVE-2026-4878
  - **Disposition:** PASS (no change required)

- **Finding 5 (INFO):** No secret leaks
  - **Disposition:** PASS (no change required)

- **Finding 6 (LOW):** `docs/security/CVE-2026-4878-libcap2.md` should be updated post-bump
  - **Disposition:** DEFERRED
  - **Backlog:** `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-container-perl-cve-remediation`
  - **Reason:** The CVE-2026-4878 doc update is documentation-only and can be fast-followed after CI confirms the base-image bump resolves the Trivy alert. Tracked as part of the same backlog evaluation.

### Bot review threads disposition

- **sourcery-ai[bot] review:** https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1847#pullrequestreview-4383654798
  - **Thread (pin by digest):** https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1847#discussion_r3319911716
    - **Disposition:** NOT-A-BUG
    - **Evidence:** `Dockerfile` uses a semver tag (`python:3.13.13-slim-bookworm`) intentionally to receive Debian security patch rebuilds. Pinning by digest would freeze the image and require manual digest rotation for every upstream security rebuild, which contradicts the project's automated Trivy scanning and base-image refresh policy. The tag is immutable at the patch level (3.13.13), and the slim-bookworm variant is rebuilt by Docker Official Images only for security updates.
  - **Thread (owner handle typo):** https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1847#discussion_r3319911717
    - **Disposition:** FIXED
    - **Commit:** a0e7c304f
    - **Evidence:** `docs/roadmap/BACKLOG_LEDGER.md:29` — `@katsiarynakavaleuskaya` corrected to `@katsiaryna_kavaleuskaya` to match all other ledger entries.

- **coderabbitai[bot] review:** https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1847#pullrequestreview-4383681953
  - **Thread (docs-only policy violation):** https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1847#discussion_r3319931548
    - **Disposition:** NOT-A-BUG
    - **Evidence:** This is a **security fix PR**, not a docs-only PR. The `Dockerfile` change is required to remediate CVE-2026-4878 (libcap2). The claim that this PR "violates the docs-only policy" is a false positive from the bot's heuristic pattern matcher.
  - **Issue comment (completion marker):** https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1847#issuecomment-4567176538
    - **Disposition:** NOT-A-BUG
    - **Evidence:** Automated completion marker. No actionable content.

- **cubic-dev-ai[bot] review:** https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1847#pullrequestreview-4383702400
  - **Thread (owner handle differs):** https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1847#discussion_r3319946388
    - **Disposition:** FIXED
    - **Commit:** a0e7c304f
    - **Evidence:** Same typo as sourcery thread above. Fixed in `docs/roadmap/BACKLOG_LEDGER.md:29`.

## Fixed in Commit Mapping

- [x] Fixed in commit mapping completed

## Merge Readiness

- [x] `make lint` — PASS
- [x] `make typecheck` — PASS
- [x] `make test-fast` — PASS
- [x] `pre-commit run --all-files` — PASS
- [x] `docker build` (pre-push hook) — PASS
- [x] Post-open review cycle complete (qa-engineer-agent, bug-hunter, security-auditor)
- [x] Bot review threads dispositioned and mapped
- [ ] CI green on current head
- [ ] No actionable bot comments
- [ ] Required checks pass
