# PR 1236 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1236#pullrequestreview-4009703811 -> 5dc63a36
Disposition: FIXED
Commit: 5dc63a36
Evidence: `.pre-commit-config.yaml:132`, `docs/security/GHSA-gc5v-m9x4-r6x2-requests.md:1`, `docs/security/GHSA-5239-wwwm-4pmq-pygments.md:1`
Reason: replaced brittle line-specific dependency-location prose with stable tracked-surface documentation plus explicit `file:line` evidence anchors, and linked the temporary `pip-audit` exception comment directly to `ledger-p1-remove-pygments-pip-audit-ignore`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1236#pullrequestreview-4009743183
Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-unyank-numpy-runtime-pin`
Evidence: `constraints.txt:39`, `docs/roadmap/BACKLOG_LEDGER.md:7562`, PR body `## Why now`
Reason: the bundled CodeRabbit review mixed one in-scope traceability nit with one out-of-scope dependency-hygiene follow-up. The traceability ask was addressed by adding the GHSA comment on `requests>=2.33.0` and by clarifying the sequencing exception in the PR body; the yanked `numpy==2.4.0` pin remains intentionally postponed to a separate narrow follow-up per the new ledger item above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1236#discussion_r2990933339 -> d37cf9ee
Disposition: FIXED
Commit: d37cf9ee
Evidence: `docs/architecture/ADR_PIP_AUDIT_PYGMENTS_SUPPRESSION_SEAM_2026-03-25.md:1`, `docs/roadmap/BACKLOG_LEDGER.md:7554`
Reason: the thread asked to either split the mixed CVE actions or document the exception clearly. The lane remains intentionally combined because both GHSA actions unblock the same `pip-audit` gate, and the temporary suppression seam is now anchored by an explicit ADR plus ledger exit criteria.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1236#discussion_r2990987290 -> d37cf9ee
Disposition: FIXED
Commit: d37cf9ee
Evidence: `docs/architecture/ADR_PIP_AUDIT_PYGMENTS_SUPPRESSION_SEAM_2026-03-25.md:1`, `docs/roadmap/BACKLOG_LEDGER.md:7554`
Reason: CodeRabbit requested an ADR-backed rationale for the temporary `Pygments` suppression seam. The new ADR documents why the ignore exists, the narrow boundary where it is allowed, and the exit path for removal.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1236#pullrequestreview-4009809996 -> d37cf9ee
Disposition: FIXED
Commit: d37cf9ee
Evidence: `docs/architecture/ADR_PIP_AUDIT_PYGMENTS_SUPPRESSION_SEAM_2026-03-25.md:1`, `docs/roadmap/BACKLOG_LEDGER.md:7554`
Reason: the current-head CodeRabbit review was satisfied by adding a canonical ADR and tightening the backlog entry so the temporary suppression has explicit guardrails and a removal path.

## Merge Readiness
- Status: in progress; PR is ready for review, local gates are green, and current bot intake is being processed on the pushed head.
- Current fix commits:
  - `bfee71de` — `fix(security): unblock pip-audit baseline`
  - `20e52648` — `docs(review): add PR 1236 mapping artifact`
  - `5dc63a36` — `fix(docs): stabilize security advisory evidence`
  - `03536cf0` — `chore(deps): track follow-up dependency hygiene`
  - `d37cf9ee` — `docs(adr): define pygments suppression seam`
- Current scope discipline:
  - remediate `requests` baseline to `2.33.0` across tracked dependency surfaces
  - document a temporary `pip-audit` ignore for `GHSA-5239-wwwm-4pmq`
  - track ignore removal in `docs/roadmap/BACKLOG_LEDGER.md`
- Local validation executed on this lane:
  - `python3 scripts/orchestration/check_preflight.py`
  - `pytest -q tests/test_dependency_security_guard.py`
  - `pre-commit run --hook-stage pre-push pip-audit --all-files`
  - `pre-commit run --all-files`
  - `make verify`
- Required before merge:
  - refresh this artifact after any new bot/human review comments arrive
  - resolve threads only after disposition evidence exists
  - confirm current-head required checks are green with no pending required jobs
  - confirm no actionable bot comments remain
