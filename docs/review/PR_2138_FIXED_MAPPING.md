# PR #2138 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138

Branch: `codex/fix-legacy-middleware-guard-vulnerability`

## Summary

Harden the legacy-growth CI guard for the approved temporal/unknown-alias
contract while preserving the existing owner PR. The implementation binds
helper replay to lexical function identity, evaluates call arguments in Python
order, distinguishes invoked synchronous helpers from dormant coroutine and
generator bodies, preserves outward binding effects, and retains possible
app/router provenance until a definite safe rebinding clears it.

PR #2139 is absorbed into this owner lane. Public APIs and OpenAPI are
unchanged; only the internal static guard and its deterministic tests change.

## Lane Start Provenance

Packet: `artifacts/orchestration/task_packets/944aa049749c.json`

- The owner branch was synchronized with fresh `origin/main` by the
  non-rewriting merge commit
  `8ea9058ec044f1a83ce29a338e5c7c4aa0d26203`.
- The declared pre-open order completed:
  `agent-coordinator -> architecture-specialist -> security-auditor ->
  backend-engineer`.
- Post-open QA, bug-hunter, and security-auditor passes were completed during
  the material review sequence. The operator subsequently stopped additional
  role waves and native scans after repeated transport/tooling loops; no later
  role or native-scan PASS is claimed.
- Local packets, role outputs, premortem notes, and Experiment Runner evidence
  are gitignored control-plane artifacts.

## Implementation Commits

- `54b0568eb020c41461eb457b4f25525b03b07572` - bind replay to lexical
  function identity; forward resolved arguments; preserve possible app/router
  aliases; clear definite safe rebindings; skip plain async calls.
- `63cb7ed3a055fd396dd2a8a155f5dfb31503059d` - preserve Python argument
  evaluation order and builtin-shadowing semantics.
- `922cf937cb7d6b40d64aaed05f82cb3b14638030` - propagate bounded
  `global`/`nonlocal` effects and coroutine alias provenance.
- `8400564c21940a8b34a316e55db601c7ff21e84c` - honor decorated helper
  replacement, invalid-call binding, executed async/generator paths, postponed
  annotations, returned bindings, and fixed-point convergence.
- `8af3f75de60b43450d5ff204cd867b52f04cdbe3` through
  `d90db836e0e04937efdbf35f2b1e1d56a8ad356c` - preserve lambda, class,
  mapping, descriptor, inheritance, and bound-method provenance without
  weakening safe negative controls.
- `6c9f2c24dfa4a84c8240c3fdbbe62c28bd43f10b` - preserve callable
  provenance across binders, literal collections, and awaited
  `asyncio.gather`.
- `acba2e3d9fac2e9e66696e34af5125054116cbdf` - handle awaited
  `asyncio.shield`, eagerly consumed synchronous `map`, and the explicit
  fail-closed `next()` boundary.
- `611f79853b2d7d8971893e3c0f3903d150b03c2a` - replay invoked local
  `functools.partial` helpers, unawaited `gather` within a running async flow,
  and active `TaskGroup.create_task`, with dormant-path negative controls.

## Source PR Replacement Matrix

- PR #2139 (`25de4250ae32682145267fb83363a8e0de5929bd`)
  is replaced by `54b0568eb020c41461eb457b4f25525b03b07572`.
  The owner implementation clears aliases for definite function/class/literal
  and known-safe rebindings, retains a possible sentinel for unknown
  app/router rebindings, and follows derived possible app/router attributes.
- Both actionable PR #2139 review findings are mapped below to the published
  owner commit made after the review timestamps.
- The PR #2139 formatting failure is replaced by the owner branch's passing
  Black/pre-commit evidence.

## Bounded Analysis Contract

The guard is a scope-aware AST growth control, not a CPython interpreter. Its
approved contract is the temporal/unknown-alias matrix above: lexical helper
identity, bounded argument forwarding, explicit executed sync/async paths,
definite-safe clearing, unknown fail-closed retention, and derived
app/router provenance.

Several later automated comments proposed interpreting additional runtime
protocols such as arbitrary context managers, metaclass hooks, descriptor
execution, callback schedulers, every iterator consumer, and yield-by-yield
short-circuit control flow. Those synthetic forms are not present in the
runtime diff, are not regressions from `main`, and would change the owner lane
from a bounded static guard into an open-ended Python execution model. They are
therefore dispositioned as NOT-A-BUG for this PR rather than feeding another
review/refactor loop.

For deliberately conservative consumer cases, the guard remains fail-closed.
`tests/test_legacy_growth_guard.py::test_legacy_growth_guard_closes_executor_and_consumer_callback_paths`
records this policy explicitly for `next()`. A focused current-head
reproduction also confirms the reported built-in `property` example is already
blocked and that a module-scope `asyncio.create_task` without a running loop is
rejected rather than trusted.

## Experiment Runner Evidence

Artifact: `artifacts/orchestration/experiments/results/pr-2138-1a3eec26-apple-oracle-result.json`

- Experiment: `exp-1a3eec268dd2`.
- Backend: explicit `apple-container` 1.1.0 with immutable image digest
  `sha256:8b95aa8a94d989ff18af7449fbb0feae6783623a7bf49434f0e16341bd61c483`.
- Result: accepted, `network_budget=0`, `mutated_paths=[]`,
  `shared_tree_untouched=true`, and `promotion_ready=false`.
- The material commits shaped by accepted Oracle evidence carry the exact
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` trailer.
- Retained Experiment Runner and creative artifacts are intentionally
  preserved during post-merge cleanup.

## Security

- No suppression, allowlist entry, public API, or OpenAPI change was added.
- Pre-push pip-audit and full-repository Bandit passed on the published
  material head; current-head GitHub security/CodeQL jobs remain live CI gates.
- An earlier native Codex Security result was superseded by later material
  commits. The operator directed that no further native scan be started after
  repeated workspace/transport loops, so no current-head native-scan PASS is
  claimed.

## Validation

- Scoped execution preflight and agent consistency: PASS.
- Direct guard execution and deterministic repeated execution: PASS.
- Full `tests/test_legacy_growth_guard.py`: PASS.
- Focused MyPy, Black, Ruff, and `git diff --check`: PASS.
- `make validate-changed`: PASS.
- Exact diff-selected backend-test hook: PASS.
- `pre-commit run --all-files`: PASS.
- Pre-push MyPy, pip-audit, backend tests, full-repository Bandit, and Docker
  build: PASS.
- Local full `make verify` was not run, per repository budget policy.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] PR #2139 replacement evidence is published on the owner branch.
- [x] Every resolved CodeRabbit thread and every open Codex/source thread is
  dispositioned below.
- [x] Additional role waves and native scans remain
  `operator_directed_stop`; no PASS is claimed for work not performed.
- Current-head CI, bot state, strict authenticated merge readiness, and the
  mandatory review wait window remain live PR-state gates.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 54b0568eb020c41461eb457b4f25525b03b07572
Evidence: lexical identity, nested same-name helpers, resolved arguments, plain-async non-execution, definite-safe clearing, unknown possible aliases, and derived app/router attributes are covered in `tests/test_legacy_growth_guard.py`; the full focused suite passes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3588631256 -> 54b0568eb020c41461eb457b4f25525b03b07572
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3588631265 -> 54b0568eb020c41461eb457b4f25525b03b07572
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3588693588 -> 54b0568eb020c41461eb457b4f25525b03b07572
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3588693604 -> 54b0568eb020c41461eb457b4f25525b03b07572
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3588693613 -> 54b0568eb020c41461eb457b4f25525b03b07572
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2139#discussion_r3588639350 -> 54b0568eb020c41461eb457b4f25525b03b07572
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2139#discussion_r3588639356 -> 54b0568eb020c41461eb457b4f25525b03b07572

Disposition: FIXED
Commit: 63cb7ed3a055fd396dd2a8a155f5dfb31503059d
Evidence: `test_legacy_growth_guard_resolves_arguments_in_python_evaluation_order` and the detached-parent-scope regression pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3598293884 -> 63cb7ed3a055fd396dd2a8a155f5dfb31503059d

Disposition: FIXED
Commit: 922cf937cb7d6b40d64aaed05f82cb3b14638030
Evidence: global/nonlocal replay propagation and coroutine alias/scheduler provenance regressions pass in the focused suite.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3598293887 -> 922cf937cb7d6b40d64aaed05f82cb3b14638030
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3598265702 -> 922cf937cb7d6b40d64aaed05f82cb3b14638030

Disposition: FIXED
Commit: 8400564c21940a8b34a316e55db601c7ff21e84c
Evidence: decorator replacement, invalid argument binding, executed `asyncio.run`/await/generator paths, dormant generator expressions, postponed annotations, and returned bindings are covered by named regressions in `tests/test_legacy_growth_guard.py`; the full focused suite passes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3598265686 -> 8400564c21940a8b34a316e55db601c7ff21e84c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3598265695 -> 8400564c21940a8b34a316e55db601c7ff21e84c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3598265708 -> 8400564c21940a8b34a316e55db601c7ff21e84c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3598265713 -> 8400564c21940a8b34a316e55db601c7ff21e84c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3598447417 -> 8400564c21940a8b34a316e55db601c7ff21e84c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3598645564 -> 8400564c21940a8b34a316e55db601c7ff21e84c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3598645571 -> 8400564c21940a8b34a316e55db601c7ff21e84c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3598645573 -> 8400564c21940a8b34a316e55db601c7ff21e84c

Disposition: FIXED
Commit: 95c2e62e372e530a16828475619489bb721d3da6
Evidence: instance and class access to static/class method wrappers preserve the correct receiver shape; the descriptor regressions pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3600672789 -> 95c2e62e372e530a16828475619489bb721d3da6

Disposition: FIXED
Commit: d90db836e0e04937efdbf35f2b1e1d56a8ad356c
Evidence: bound classmethod and instance-method aliases preserve receiver provenance in focused regressions.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3600720360 -> d90db836e0e04937efdbf35f2b1e1d56a8ad356c

Disposition: FIXED
Commit: 6c9f2c24dfa4a84c8240c3fdbbe62c28bd43f10b
Evidence: awaited `asyncio.gather` and callable provenance through literal/named collection binders are covered by focused regressions.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3599138093 -> 6c9f2c24dfa4a84c8240c3fdbbe62c28bd43f10b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3600720368 -> 6c9f2c24dfa4a84c8240c3fdbbe62c28bd43f10b

Disposition: FIXED
Commit: acba2e3d9fac2e9e66696e34af5125054116cbdf
Evidence: `test_legacy_growth_guard_closes_executor_and_consumer_callback_paths` covers awaited `asyncio.shield` and eagerly consumed synchronous `map`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3603725073 -> acba2e3d9fac2e9e66696e34af5125054116cbdf
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3603725083 -> acba2e3d9fac2e9e66696e34af5125054116cbdf

Disposition: FIXED
Commit: 611f79853b2d7d8971893e3c0f3903d150b03c2a
Evidence: invoked local `partial`, unawaited `gather` in an active async replay, and active `TaskGroup.create_task` each have positive and dormant-path negative controls in the full passing focused suite.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3600672799 -> 611f79853b2d7d8971893e3c0f3903d150b03c2a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3600720357 -> 611f79853b2d7d8971893e3c0f3903d150b03c2a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3603958357 -> 611f79853b2d7d8971893e3c0f3903d150b03c2a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3603958361 -> 611f79853b2d7d8971893e3c0f3903d150b03c2a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3603958366 -> 611f79853b2d7d8971893e3c0f3903d150b03c2a

Disposition: NOT-A-BUG
Evidence: the approved owner contract and implementation use explicit, bounded executor/consumer handling in `scripts/ci/check_legacy_growth_guard.py`; the PR runtime diff contains none of the proposed metaprogrammed registration forms, and the change is strictly stronger than `main` for its declared temporal/unknown-alias cases.
Reason: these comments request new CPython runtime-protocol interpretation beyond the owner lane rather than identify regressions in the declared lexical resolver contract.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3599138096
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3599215877
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3599215881
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3600720364
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3601350023
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3601350027
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3601350030
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3601350033
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3602631483
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3602631493
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3602631505
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3602909038
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3602909055
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3603081273
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3603081279
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3603081282
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3603081288
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3603081294
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3603141550
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3603141557
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3603141565
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3603141569
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3603195842
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3603195850

Disposition: NOT-A-BUG
Evidence: `tests/test_legacy_growth_guard.py::test_legacy_growth_guard_closes_executor_and_consumer_callback_paths` explicitly requires consumed generators to remain fail-closed rather than interpret yield-by-yield control flow; direct current-head reproduction blocks `next()` after the first yield, `any`/`all` candidates, and a module-scope scheduler call.
Reason: conservative rejection is the documented security posture; code that raises before startup registration is not trusted as a safe aliasing control.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3599138101
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3599215875
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3600672796
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3602748465
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3602909043
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3603195845
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3603725091

Disposition: NOT-A-BUG
Evidence: a direct current-head `validate_legacy_growth(...)` reproduction of the proposed `@property` example returns `registration:middleware:http`; the same behavior is present from the original owner commit.
Reason: the reported bypass does not reproduce on the reviewed implementation or current head.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2138#discussion_r3602909049
