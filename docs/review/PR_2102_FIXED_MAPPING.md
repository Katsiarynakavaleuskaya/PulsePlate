# PR #2102 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102

Branch: `codex/canonicalize-app-api-key-dependency`

## Summary

Move app-client API-key dependency ownership from `legacy_app.py` to
`app/routers/api_key.py` while preserving exact auth behavior, FastAPI callable
identity, route registration, app identity, and OpenAPI output. The same commit
closes every bounded pre-open defect found in the touched auth/bootstrap graph.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/b6706fba26f3.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Required pre-open order executed:
  `agent-coordinator -> architecture-specialist -> backend-engineer -> security-auditor -> qa-engineer-agent -> bug-hunter`.
- Creative-Code remained oracle-only; no app-layer mutation authority or
  candidate-patch promotion was granted.

## Implementation Commit

- `2c4aaa00c5c4bd66839d5b45d415cc090bfb6ec0` - canonicalize API-key
  dependency ownership, exact compatibility aliases, production consumers,
  fail-closed guards, behavior/identity tests, and scoped architecture guidance.

## Discussion Thread Pass

- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed
- [x] Pre-open packet role order completed and every bounded finding closed.
- [ ] Mandatory post-open `qa-engineer-agent -> bug-hunter -> security-auditor` pass completed.
- [ ] Codex Security current-diff scan completed.
- [ ] `pulseplate-pr-review` completed.
- [ ] CodeRabbit, Sourcery, and Cubic current-head reviews contain no actionables.
- [ ] Current-head CI completed.
- [ ] Strict authenticated merge readiness and mandatory wait window completed.

Future actionable human, bot, role, or security findings must be fixed or
dispositioned here before thread resolution or merge-readiness claims.

## Fixed in Commit Mapping

No GitHub review thread has been resolved yet. Thread-specific mappings will be
added only after an actionable is fixed or evidence supports `NOT-A-BUG` or
`DEFERRED` disposition under repository policy.

## Pre-Implementation Role Findings

### Agent Coordinator

Disposition: NOT-A-BUG
Evidence: Packet `b6706fba26f3` bounded ownership to the canonical API-key
module, exact compatibility aliases, direct production consumers, focused
guards/tests, and scoped documentation.
Reason: No task-routing or authority blocker remained after fresh-main
preflight.

### Architecture Specialist

Disposition: FIXED
Commit: `2c4aaa00c`
Evidence: `app/routers/api_key.py` is the sole implementation owner;
`legacy_app.py` contains exact aliases; `app/__init__.py` exposes the same
objects; production consumers import the canonical dependency directly.
Reason: The reverse import and wrapper risks are removed without claiming
isolated-module reload compatibility.

### Backend Engineer

Disposition: FIXED
Commit: `2c4aaa00c`
Evidence: All 13 default and five conditional protected route registrations are
covered by exact-object dependency tests, while `/premium_bmr` remains the
intentional unprotected compatibility exception.
Reason: The complete consumer cutover preserves route and response behavior.

### Security Auditor

Disposition: FIXED
Commit: `2c4aaa00c`
Evidence: Dynamic override results reject non-string and blank values;
unexpected failures keep generic 500 envelopes and omit exception messages,
tracebacks, and credential values from logs; warn-once state is lock-protected.
Reason: Every bounded secret-handling and fail-closed defect found in the
touched graph is closed.

### QA Engineer Agent

Disposition: FIXED
Commit: `2c4aaa00c`
Evidence: The 12-case compatibility matrix freezes exact 403 details,
environment precedence, dev leniency/normalization, and warning behavior; guard
bypass, route identity, and warning-as-error regressions pass.
Reason: The initially missing acceptance cases and false-green guard paths are
covered deterministically.

### Bug Hunter

Disposition: FIXED
Commit: `2c4aaa00c`
Evidence: Focused Flake8 passes; live route dependency traversal uses exact
callable identity; the legacy guard rejects reverse imports, qualified/dynamic
lookups, alias rebinding, and stale header reintroduction.
Reason: No remaining lint, dependency-override, or ownership-guard actionable
survived the closure pass.

## Premortem

- Callable wrappers break FastAPI override identity: FIXED through exact aliases
  and exact-object route assertions.
- Partial consumer cutover leaves legacy ownership: FIXED for the complete
  default and conditional route inventories.
- Lenient-mode concurrency floods logs: FIXED with lock-protected process-once
  state and deterministic concurrency coverage.
- Credential-bearing exception text reaches logs: FIXED with stable
  classification-only logging and explicit redaction assertions.
- AST guard is false-green through qualified lookup or rebinding: FIXED with
  direct, dynamic-import, assignment, annotation, augmented-assignment, and
  named-expression negative controls.
- Test infrastructure advertises a stale dependency override: FIXED by removing
  the unused `get_api_key` override from `tests/conftest.py`.
- Active validation emits Pydantic serializer warnings: FIXED by providing the
  declared `set` type in the affected test fixtures and verifying under warning
  escalation.

Decision: `proceed`; no premortem finding remains open.

## Experiment Runner Evidence

Artifact: `artifacts/orchestration/experiments/results/exp-6fdd2ed789f8.json`

- Mode: `oracle_only_governance_reviewer`
- Status: `accepted`
- Contribution: `commit_decision`
- Immutable oracles: 3/3 passed
- `mutated_paths: []`; `shared_tree_untouched: true`
- Co-author required: true; the canonical trailer is present on material commit
  `2c4aaa00c`.
- SHA-256:
  `bb3632c4e3dd19fee8b2b7520b1a773199b00ffd7769243ac5b464472363b32d`.
- `promotion_ready: false`; no candidate patch or promotion authority was used.

Preceding attempt `exp-4ee89b07e873` was rejected as an infrastructure flake
because the macOS network-disabled sandbox lacked `unshare`; no oracle ran and
that artifact is not used as review or attribution evidence.

## Validation Evidence

- PASS: execute-mode preflight and agent consistency.
- PASS: focused 17-file auth/bootstrap/security regression suite.
- PASS: warning-as-error regression for corrected Pydantic fixtures.
- PASS: focused MyPy and legacy growth guard.
- PASS: `make openapi-check` with zero generated diff.
- PASS: `make validate-changed` after commit; 13 changed backend/security test
  files selected and completed.
- PASS: `pre-commit run --all-files`; no final hook modifications.
- PASS: pre-push MyPy, pip-audit, backend tests, full Bandit, and Docker build.
- PASS: `git diff --check`, conflict check, and local-artifact check.
- Not run: local full `make verify`, per repository machine-budget policy.

## Merge Readiness

Not claimed. The implementation is published at `2c4aaa00c`; current-head CI,
external bot review, mandatory post-open role/security review, fixed mapping,
strict authenticated merge readiness, and the final wait window remain
required.

## Deferred / Follow-ups

- Application metadata and OpenAPI policy extraction.
- Remaining canonical-to-legacy dependency cutovers.
- App-factory ownership inversion.
- Compatibility inventory and final `legacy_app.py` deletion.

These remain tracked by the existing `Complete legacy_app.py migration` ledger
item and are intentionally outside this auth-ownership PR.
