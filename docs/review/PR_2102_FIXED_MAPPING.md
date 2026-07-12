# PR #2102 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102

Branch: `codex/canonicalize-app-api-key-dependency`

## Summary

Move app-client API-key dependency ownership from `legacy_app.py` to
`app/routers/api_key.py` while preserving authentication behavior, FastAPI
callable identity, route registration, app identity, and OpenAPI output.

The production cutover remains intact. The later interpreter-like AST analyzer
expansion was materially rolled back. The retained guard is a bounded
architectural regression detector for trusted, reviewed repository source; it
does not claim to prove equivalence across intentionally obfuscated Python.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/b6706fba26f3.json`
- Post-open packet: `artifacts/orchestration/task_packets/05dfe3b5523c.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Pre-open role order executed:
  `agent-coordinator -> architecture-specialist -> backend-engineer ->
  security-auditor -> qa-engineer-agent -> bug-hunter`.
- Creative-Code remained oracle-only. It received no app-layer mutation or
  promotion authority.

## Implementation Commits

- `2c4aaa00c5c4bd66839d5b45d415cc090bfb6ec0` - canonical API-key dependency
  ownership, exact compatibility aliases, production-consumer cutover, and
  behavior/identity tests.
- `276ca9b6087149dc5b89a375fa4f189e64a40a3f` - bounded runtime/auth review
  repairs: sanitized failure logging, valid dynamic-guard results, warning
  concurrency, exact route identity, environment isolation, and scan-root
  controls.
- `6a9a563a69cbc5ffeefff2d8787a5edde22bc488` - preserve the canonical
  `api_key_header` facade export.
- `59c44a679` - restore the legacy-growth analyzer to its bounded baseline,
  removing the published pseudo-interpreter expansion.
- `11c0c8c04` - document the trusted-source static-guard threat model.
- `761f8faa6` - accept exact direct re-exports and reject bounded literal
  importlib, one-hop alias, and static-name `getattr` lookups.
- `9768faa66` - require module-level re-exports and fail closed when the
  canonical app-source scan root is missing.
- `a2cf1ab80` - preserve source order for ordinary top-level one-hop alias
  lookups without introducing branch or data-flow interpretation.
- `2e30227d8` - retain single-assignment ordinary aliases for top-level
  expression and nested direct-use checks while preserving safe-reassignment
  controls.
- `20914e075` - reject bounded module-scope import/loop/conditional/with/except
  rebinding and direct `legacy_app` star reverse imports.
- `c78ecac8d` - scope implementation-owner detection to module-level functions
  and preserve nested sync/async local-function safe controls.
- `f764bd5fc` - select the dedicated API-key ownership and warning suites in
  canonical `route_contract_safety` CI and cover the non-callable guard plus
  lock-race return deterministically.

## Analyzer Rollback Decision

- Analyzer escalation abandoned.
- The final uncommitted `+1818`-line wave was not published.
- The already published interpreter-like expansion was materially rolled back
  by `59c44a679`.
- Runtime API-key ownership and its bounded security repairs were retained.
- The retained detector covers exact ownership, module-level re-export
  identity, direct reverse imports, direct attribute/literal-`getattr`
  lookups, literal `importlib.import_module("legacy_app")`, and one ordinary
  top-level alias with source-order semantics.
- Control-flow graphs, abstract value propagation, mapping-state evaluation,
  closures, descriptors, pattern matching, context-manager result propagation,
  and arbitrary reflective composition are outside the documented threat
  model.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Pre-open packet role order completed.
- [x] Production/auth implementation findings fixed before mapping.
- [x] Bounded rollback threat model reviewed by architecture specialist.
- [x] Final post-open `qa-engineer-agent -> bug-hunter -> security-auditor`
  rollback pass completed.
- [x] One previously completed Codex Security diff scan retained as production
  cutover evidence; no new scan is authorized or required for guard/docs-only
  rollback commits.
- [x] `pulseplate-pr-review` completed on the final published head.
- [x] All current review threads dispositioned and resolved.
- [ ] Current-head CI completed.
- [ ] Strict authenticated merge readiness and mandatory wait window completed.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565024580 -> 276ca9b6087149dc5b89a375fa4f189e64a40a3f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565024595 -> 276ca9b6087149dc5b89a375fa4f189e64a40a3f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565024602 -> 276ca9b6087149dc5b89a375fa4f189e64a40a3f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565024857 -> 276ca9b6087149dc5b89a375fa4f189e64a40a3f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565030460 -> 276ca9b6087149dc5b89a375fa4f189e64a40a3f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565030470 -> 276ca9b6087149dc5b89a375fa4f189e64a40a3f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565030475 -> 276ca9b6087149dc5b89a375fa4f189e64a40a3f
Disposition: FIXED
Commit: 276ca9b6087149dc5b89a375fa4f189e64a40a3f
Evidence: Runtime behavior, environment isolation, generic 500 logging, process-once warning, callable identity, and ledger target tests pass on the current branch; this commit is an ancestor of the current head.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565204816 -> 6a9a563a69cbc5ffeefff2d8787a5edde22bc488
Disposition: FIXED
Commit: 6a9a563a69cbc5ffeefff2d8787a5edde22bc488
Evidence: `app.api_key_header` resolves directly to the canonical `app.routers.api_key.api_key_header` object and the compatibility ownership suite proves exact identity.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565024587 -> 761f8faa6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565024592 -> 761f8faa6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565024593 -> 761f8faa6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565024855 -> 761f8faa6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565030462 -> 761f8faa6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565030468 -> 761f8faa6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565030472 -> 761f8faa6
Disposition: FIXED
Commit: 761f8faa6
Evidence: Focused positive and safe-control tests prove direct identity-preserving imports, literal importlib assignment, one-hop ordinary aliases, and statically named `getattr` lookups. The final 341-test guard suite passes.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565024594 -> 9768faa66
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565024600 -> 9768faa66
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565030453 -> 9768faa66
Disposition: FIXED
Commit: 9768faa66
Evidence: `validate_repo()` now fails closed on a missing `app/` root and only module-level canonical imports satisfy the legacy re-export contract; focused negative tests pass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565024591 -> 20914e075
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565024601 -> 20914e075
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565030449 -> 20914e075
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565030464 -> 20914e075
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565204818 -> 20914e075
Disposition: FIXED
Commit: 20914e075
Evidence: Focused regressions reject ordinary top-level import, loop, conditional, with-target, and exception-target rebinding plus direct `from legacy_app import *`; safe nested-local and unrelated-star controls pass. The guard remains a syntactic binding check and does not evaluate branch state.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565131656
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565131657
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565152800
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565192808
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565204821
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565224748
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565279783
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565279785
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565761896
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565761898
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565761900
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565815767
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565815768
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565815769
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565899162
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565962508
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565962510
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565962512
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3566012932
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3566105000
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3566105001
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3566105004
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3566451148
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3566451151
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3566451152
Disposition: NOT-A-BUG
Evidence: `docs/architecture/LEGACY_COMPATIBILITY_SEAM.md` defines the guard as a bounded detector for trusted, reviewed source; `scripts/AGENTS.md` forbids interpreter-like control/data-flow expansion; runtime identity tests prove protected registrations use the canonical callable; repository search shows production consumers use direct canonical imports rather than adversarial forms.
Reason: These comments require intentionally obfuscated equivalences through control-flow joins, nested lexical scopes, namespace mappings, builtins loaders, containers, closures, descriptors, `attrgetter`/`methodcaller`/`itemgetter`, `partial`, comprehensions, pattern matching, or context managers. Those constructions are outside the approved trusted-source threat model; the open-ended pseudo-interpreter expansion was rolled back.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565024583
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565030465
Disposition: NOT-A-BUG
Evidence: `legacy_app.py` re-exports exactly `get_api_key` and `_get_api_key_dynamic`; `api_key_header`, `validate_app_api_key`, and `require_app_api_key` are canonical-only objects with no legacy ownership contract; runtime identity and reverse-import tests pass.
Reason: `CANONICAL_API_KEY_SYMBOLS` intentionally describes the two temporary legacy compatibility re-exports, not every object owned by the canonical auth module.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565024584
Disposition: NOT-A-BUG
Evidence: The accepted Experiment Runner artifact records `mutated_paths: []` and `shared_tree_untouched: true`; the production diff was implemented and reviewed in the coordinator-owned PR lane.
Reason: Creative-Code mutation authority remained denied, so autonomous candidate-mutation threats do not apply to these reviewed repository edits.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#discussion_r3565899163
Disposition: NOT-A-BUG
Evidence: `git merge-base --is-ancestor 2c4aaa00c HEAD` and `git merge-base --is-ancestor 276ca9b608 HEAD` both exit 0 on the current branch; all FIXED mappings above reference current-head ancestors.
Reason: The comment evaluated an ephemeral review snapshot; the published PR branch contains the implementation and repair commits used as proof.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#pullrequestreview-4678740036
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#pullrequestreview-4678749721
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#pullrequestreview-4679560869
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#pullrequestreview-4679599924
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#pullrequestreview-4679753222
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#pullrequestreview-4679767879
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#pullrequestreview-4679848127
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#pullrequestreview-4679857529
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#pullrequestreview-4680167226
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2102#pullrequestreview-4680178140
Disposition: NOT-A-BUG
Evidence: Each inline actionable from these review summaries has a thread-specific disposition above; the final bounded architecture and runtime contracts are tested independently.
Reason: Review-summary comments add no separate actionable beyond their inline threads; repeated adversarial-syntax suggestions are governed by the documented threat-model disposition above.

## Codex Security Diff Scan

- Session: `087abf69-cee7-45d6-aeb2-dc85824177bc`
- Scan ID: `ed39a46f-6432-4d54-b597-1ed772b1cf25`
- Target: `12fd4ec8366a29443fcf0fe87743eed7aeca8e24..d287b868c798ea80276fe19f06c9870ab7a1cec5`
- Result: 7/7 worklist rows closed; 0 reportable findings.
- Scope note: no production/auth file changed after this target. Later material
  commits modify only the guard, guard tests, threat-model docs, and review
  governance.
- Operator decision: do not launch another security scan. Targeted final
  security-auditor review and current-head CI cover the rollback diff.

## Post-Open Role Evidence

- Architecture specialist identified the AST feedback loop as an architectural
  `NO-GO` and approved bounded rollback with a trusted-source threat model.
- Final QA passed at `c78ecac8d` after finding and closing bounded
  source-order/single-alias gaps. It verified module binding and star-import
  checks, nested sync/async safe controls, runtime identity, the focused
  runtime/security suite, and confirmed the implementation remains syntactic
  rather than interpreter-like.
- Final bug-hunter passed the code/runtime surface at `c78ecac8d`:
  guard/ownership suites, guard CLI, production reverse-import search,
  callable identity, override, malformed-result, and log-redaction contracts
  passed. Its sole mapping wording inconsistency was corrected before commit.
- Final security-auditor passed at `c78ecac8d`: production/auth diff after the
  scanned `d287b868c` target is empty; exact aliases, fail-closed 403/500
  behavior, `compare_digest`, warning concurrency, log redaction, malformed
  result rejection, bounded threat-model dispositions, and mapped commit
  ancestry all passed. No new security scan was launched.
- `pulseplate-pr-review` dry-run completed on published head `31a67552d` with
  no deterministic correctness, security, or architecture findings. Its sole
  advisory large-diff note is dispositioned by the operator-approved coherent
  identity-cutover scope and the material analyzer rollback.
- Role passes are read-only and do not replace deterministic gates or strict
  merge readiness.

## Premortem

- Callable wrappers break FastAPI override identity: closed through exact
  aliases and exact-object route assertions.
- Partial consumer cutover leaves legacy ownership: closed by complete
  protected-route inventory tests.
- Lenient-mode concurrency floods logs: closed with lock-protected process-once
  state and deterministic concurrency coverage.
- Credential-bearing exception text reaches logs: closed with
  classification-only logging and redaction assertions.
- Guard silently skips ordinary reverse dependency forms: closed for direct
  imports, direct attribute/literal-`getattr`, literal importlib, module-level
  exact re-export, one-hop ordinary alias, source ordering, and missing scan
  roots.
- Guard grows into an incomplete Python interpreter: closed by rollback and
  the explicit bounded threat model.

## Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`.
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`.
- PASS: `python3 scripts/ci/check_legacy_growth_guard.py`.
- PASS: 341-test `tests/test_legacy_growth_guard.py` suite.
- PASS: focused ownership, warning, bootstrap, export/shoplist/moderation,
  premium-router, auth-tier/authz, business, and paid-route regression pack.
- PASS: focused MyPy for seven production/guard files.
- PASS: `DEV_PYTHON=<repo-python> make openapi-check`; generated OpenAPI and
  TypeScript artifacts have zero diff.
- PASS: `make validate-changed` on the post-rollback material diff.
- PASS: commit hooks including Black, Ruff, Bandit, backend tests, and secrets
  detection for every material rollback commit.
- PASS: final `make validate-changed` after all bounded code repairs.
- PASS: final `pre-commit run --all-files`; no hook-modified files remained.
- CI finding fixed: the first final-head run reported 83% diff coverage because
  route-risk selection omitted the dedicated auth suites; `f764bd5fc` closes
  the proven routing gap and targeted coverage now executes every previously
  missing changed line in `app/routers/api_key.py`.
- Not run: local full `make verify`, per repository machine-budget policy.

## Merge Readiness

Not claimed. Final role passes, mapping/body publication, review-thread
dispositions, current-head CI, `pulseplate-pr-review`, strict authenticated
merge readiness, and the mandatory wait window remain required.

## Deferred / Follow-ups

- Application metadata and OpenAPI policy extraction.
- Remaining canonical-to-legacy dependency cutovers.
- App-factory ownership inversion.
- Compatibility inventory and final `legacy_app.py` deletion.

These remain tracked by the existing `Complete legacy_app.py migration` ledger
item and are intentionally outside this auth-ownership PR.
