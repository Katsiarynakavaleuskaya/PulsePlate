# PR #2114 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2114

Branch: `codex/canonicalize-application-metadata-openapi-policy`

## Summary

Move application metadata and public OpenAPI policy ownership out of
`legacy_app.py` while preserving the single FastAPI instance, route inventory,
public schema, generated clients, and compatibility surface. The canonical
builder validates state before bootstrap mutation, installs after additive route
registration, and invalidates only stale input/cache state.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/196755830970.json`
  (local-only, gitignored).
- Post-open packet: `artifacts/orchestration/task_packets/567173457719.json`
  (local-only, gitignored).
- Pre-open role order executed: `agent-coordinator -> architecture-specialist ->
  backend-engineer -> security-auditor -> qa-engineer-agent -> bug-hunter`.
- Final material-head post-open order executed:
  `qa-engineer-agent -> bug-hunter -> security-auditor`.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Pre-open packet role order completed
- [x] Actual-diff premortem completed
- [x] Post-open `qa-engineer-agent -> bug-hunter -> security-auditor` completed
- [x] Codex Security exact-material-diff scan completed with 0 findings
- [x] `pulseplate-pr-review` completed
- [x] All current review threads dispositioned and resolved
- [ ] Canonical current-head CI completed
- [ ] Strict authenticated merge readiness and mandatory wait-window completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: aa64cf79b68094c56695a8c6e2a24a0b9d3a5c98
Evidence: `legacy_app.py` preserves the explicit compatibility export contract; `scripts/ci/check_legacy_growth_guard.py` limits rebind analysis to module scope, rejects package-form `app.main` imports, and enforces canonical export identity; the corresponding regression matrix is in `tests/test_legacy_growth_guard.py`.
Reason: The first CodeRabbit pass identified four bounded ownership-guard and coverage gaps. Commit `aa64cf79b68094c56695a8c6e2a24a0b9d3a5c98`, made after the comments, closes all four without widening runtime behavior.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2114#discussion_r3571013369 -> aa64cf79b68094c56695a8c6e2a24a0b9d3a5c98
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2114#discussion_r3571013375 -> aa64cf79b68094c56695a8c6e2a24a0b9d3a5c98
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2114#discussion_r3571013377 -> aa64cf79b68094c56695a8c6e2a24a0b9d3a5c98
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2114#discussion_r3571013383 -> aa64cf79b68094c56695a8c6e2a24a0b9d3a5c98

Disposition: FIXED
Commit: 8e90fd4e7647f654263ad61219b572849f52200f
Evidence: `scripts/ci/check_legacy_growth_guard.py` now covers mutating namespace mapping methods, package `__import__` fromlists, mapping-based installer lookups, and assignment-chain aliases; `tests/test_legacy_growth_guard.py` contains the deterministic regression cases. Commit `091fbe82cfd816bd94eb25d2b54bef7849df9828` subsequently preserved typed fromlist analysis without changing the closed behavior.
Reason: The second CodeRabbit pass identified four concrete AST bypasses. Commit `8e90fd4e7647f654263ad61219b572849f52200f`, made after the comments, closes the reported paths and their direct variants.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2114#discussion_r3571995134 -> 8e90fd4e7647f654263ad61219b572849f52200f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2114#discussion_r3571995141 -> 8e90fd4e7647f654263ad61219b572849f52200f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2114#discussion_r3571995144 -> 8e90fd4e7647f654263ad61219b572849f52200f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2114#discussion_r3571995153 -> 8e90fd4e7647f654263ad61219b572849f52200f

## Post-open Role Findings

### QA Engineer Agent

Disposition: NOT-A-BUG
Evidence: Exact-head read-only review at
`35d94ed441eda9877f2e2f9fb82efd2f61140e1e` confirmed statement-order alias
tracking, safe-reassignment handling, nested-scope isolation, and passing focused
guard tests.
Reason: No actionable correctness defect remained on the final material head.

### Bug Hunter

Disposition: NOT-A-BUG
Evidence: Exact-head bounded review found no reproducible bypass inside the
approved metadata/OpenAPI/bootstrap/guard graph after the alias-mutation fix.
Reason: No actionable defect remained in the reviewed material diff.

### Security Auditor

Disposition: NOT-A-BUG
Evidence: Exact-head defensive review confirmed that the guard rejects aliased
current-module mutation while preserving safe reassignment and nested shadowing;
the canonical builder continues to fail closed on stale, foreign, wrong-app, and
protocol-drift states.
Reason: No reportable security defect remained on the final material head.

### Codex Security

Disposition: NOT-A-BUG
Evidence: Sealed scan `05929524-682a-4887-9fbd-080a819cc21e` covered the exact
material range `5b4afe7ac928cf8cb78d7d8536e7429591d3e743...35d94ed441eda9877f2e2f9fb82efd2f61140e1e`,
completed all 6 worklist rows, and reported 0 findings.
Reason: No candidate survived the defensive discovery, validation, and attack-path
reportability gates.

### PulsePlate PR Review

Disposition: FIXED
Evidence: The review reported only the missing canonical mapping/body mirror and
the already-approved large-diff scope advisory. This artifact supplies the
mapping; the PR body mirror is updated in the same governance pass. Focused
runtime, OpenAPI, guard, MyPy, and repository narrow gates are recorded below.
Reason: No product correctness or security finding was emitted; the remaining
gap was required governance evidence.

## Experiment Runner Evidence

Artifact: artifacts/orchestration/experiments/results/canonical-openapi-policy-preopen-20260713-r4.json

The accepted local-only oracle artifact records 2/2 immutable oracle passes,
`mutated_paths=[]`, and contribution kind `oracle_review`. The canonical
Experiment Runner co-author trailer is present in the implementation commit.

## Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`.
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`.
- PASS: focused metadata/OpenAPI/bootstrap/guard test bundle.
- PASS: full `tests/test_legacy_growth_guard.py` after the final guard fix.
- PASS: focused MyPy with explicit package bases.
- PASS: `python3 scripts/ci/check_legacy_growth_guard.py`.
- PASS: `make openapi-check` with the repo interpreter first in `PATH`; generated
  backend/frontend OpenAPI and TypeScript artifacts have zero diff.
- PASS: `make validate-changed`.
- PASS: `pre-commit run --all-files` after formatter changes were retained and
  focused checks rerun.
- PASS: pre-push MyPy, pip-audit, backend tests, full-repository Bandit, and Docker
  build test.
- Not run: local full `make verify`, per repository machine-budget policy.
- PENDING: canonical current-head GitHub CI and strict authenticated merge
  readiness.

## Security Review

- Public filtering remains deny-by-allowlist and users routes stay internalized.
- Builder validation jointly requires live callable identity, marker identity,
  target-app identity, and protocol version.
- Early/default and changed-input caches are invalidated; no-op bootstrap preserves
  valid cache identity.
- Final material diff has one sealed Codex Security scan with 0 findings; no
  duplicate scan is required for governance-only mapping/body changes.

## Risks / Rollback

- Main risks are accidental public schema exposure, stale or foreign builder
  takeover, cache leakage/reuse, compatibility drift, and generated-client drift.
- Controls are the exact builder-state matrix, route/schema identity oracles,
  cache-isolation tests, ownership guard, and OpenAPI zero-diff validation.
- Rollback is one revert. There is no DB, persisted-state, route, client, or
  deployment migration.

## Merge Readiness

Not claimed. Canonical current-head CI, the required coverage signal, strict
authenticated merge readiness, and the mandatory review wait-window must pass
before human-authorized merge.

## Deferred / Follow-ups

- Remaining canonical-to-legacy cutovers.
- App-factory ownership inversion.
- Compatibility inventory and final `legacy_app.py` deletion.

These remain under the existing `Complete legacy_app.py migration` ledger item.
