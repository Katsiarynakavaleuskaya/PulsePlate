# ADR — Wave 6 `security-floor` Unblock Seam

- **Date:** 17 April 2026
- **Status:** Accepted (temporary seam)
- **Owner:** @katsiaryna_kavaleuskaya
- **Backlog:** `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-security-floor-unblock-seam`

## Context

The Wave 6 docs/bootstrap lane is intentionally narrow and must not widen into
runtime or product implementation work. A separate dependency-remediation lane
already governs the active alert family for `python-multipart` and `dompurify`
(`docs/orchestration/DEPENDABOT_ALERTS_110_113_REMEDIATION_TASK_PACKET_2026-04-16.md:16-21`,
`docs/orchestration/DEPENDABOT_ALERTS_110_113_REMEDIATION_TASK_PACKET_2026-04-16.md:64-70`).

When that advisory blocks a docs/governance PR from staying green, the repo
needs one explicit temporary exception that is still narrow, evidence-driven,
and easy to retire.

## Decision

Allow one temporary `security-floor` unblock seam only when a known dependency
advisory blocks a docs/governance lane.

The seam is limited to these governed dependency surfaces:

- Python manifest / lock / constraint / schema surfaces already recorded in
  `docs/security/CVE-2026-40347-python-multipart.md:17-25`
  (`requirements.in`, `requirements-ci-lite.in`, `requirements-dev.in`,
  `constraints.txt`, `requirements.txt`, `requirements-dev.txt`,
  `requirements-lock.txt`, `requirements-ci-lite.txt`,
  `tests/fixtures/dependency_security_schema.json`)
- Frontend override / lock / guard surfaces already recorded in
  `docs/security/GHSA-39q2-94rc-95cp-dompurify.md:17-24`
  (`frontend/package.json`, `frontend/package-lock.json`,
  `tests/test_frontend_dependency_guards.py`)
- Lane-level CVE / GHSA evidence docs:
  `docs/security/CVE-2026-40347-python-multipart.md:15-40`,
  `docs/security/GHSA-39q2-94rc-95cp-dompurify.md:15-38`

The seam does **not** permit:

- runtime or product behavior changes
- OpenAPI or public contract mutation
- new API or UI scope
- broad dependency refreshes outside the governed alert family

## Rationale

This keeps a dependency-blocked docs lane mergeable without silently turning the
lane into a runtime/security sweep. The governed surfaces are already validated
by existing repo-backed evidence and deterministic guards, so the exception can
stay narrow and auditable.

## Exit Criteria

1. The blocking dependency-remediation lane is merged on `main` with the
   required CVE/GHSA evidence and regenerated lock surfaces.
2. Wave 6 packet and Karpathy epic both reference this ADR/backlog item instead
   of carrying divergent wording.
3. No open advisory still requires edits to the governed surfaces above for the
   current docs lane.

## Blockers

- Any proposed change that touches runtime/API/product scope instead of the
  governed dependency surfaces above.
- Missing `file:line` evidence for the affected dependency, lock, schema, or
  guard surface.
- Missing deterministic validation for the same alert family.

## Consequences

- Docs/governance lanes may acknowledge one narrow dependency unblock without
  violating the Wave 6 scope lock.
- Review artifacts must cite this ADR and the backlog item whenever the seam is
  referenced.
- Once the dependency-remediation lane is merged, this seam should be treated as
  documentation-only historical context rather than an active exception.
