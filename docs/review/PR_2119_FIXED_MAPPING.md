# PR #2119 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119

Branch: `codex/align-pr2-runner-failure-taxonomy`

## Summary

Align the creative-code PR-2 result and generation-receipt taxonomies with the
canonical Experiment Runner `capability_mismatch` outcome so an unavailable
isolation capability is retained as a sanitized terminal rejection without a
retry or promotion path. The replacement also permits that exact rejection
when backend preflight passed but the isolation primitive was lost during
execution, while all accepted/failure and rejected/promotion combinations stay
fail closed. A capability loss on the first execution attempt remains the
non-retryable `capability_mismatch 1/0` outcome; if an infrastructure failure
already consumed a retry, the compound terminal sequence is retained as the
sanitized `infra_flake 2/1` outcome instead of producing an artifact that the
closed contracts cannot validate. Accepted standalone result and receipt
validation now requires complete runner proof, and every published Oracle
execution counter is bound to the Oracle evidence retained in the artifact.
Every admitted `capability_mismatch`, including post-preflight `1/0`, now also
requires trusted backend/preflight provenance; dispatch injects that trusted
provenance before strict validation instead of accepting caller metadata.
Public CLI status output is now selected only from local `accepted`/`rejected`
constants before artifact publication; any other runner-controlled value fails
closed with a constant dispatcher error and cannot reach stdout, stderr, or the
result artifact. Direct runner capability loss is now a data-free internal
signal and produces no standalone artifact; only dispatch, after a passed
backend probe and successful cleanup, can construct the strict-valid rejected
`capability_mismatch 1/0` result with trusted provenance. Direct builder and
promotion consumers translate that signal to fixed domain errors, create no
result or validation artifacts, and preserve cleanup without fabricating
retryable outcomes or backend proof.

## Split Justification

The 18-file owner surface is the operator-approved consolidation of the
existing 14-file result/receipt/telemetry contract with the two exact source
paths from PR #2130 and the two bounded Experiment Runner paths required to fix
current-head review finding `discussion_r3587200566`. Splitting the validator,
runner classifier, and regressions from the owner taxonomy would temporarily
leave reachable terminal outcomes incoherent across Experiment Runner, receipt,
and telemetry consumers. No public API, OpenAPI, setup/dependency, product
runtime, or unrelated backend surface is included. The later current-head
findings `discussion_r3587568042` and `discussion_r3587568047` are corrected
inside those same 18 paths. The later zero-attempt proof finding
`discussion_r3588115330` and its missing-backend reproduction are also closed
inside the existing surface. Final findings `discussion_r3588654515` and
`discussion_r3588716979` close incomplete accepted proof and a stale
mixed-failure Oracle counter inside the same published file set. Final finding
`discussion_r3588809763` closes backendless post-preflight capability proof in
the existing contract/dispatch/test surface. GitHub CodeQL alert `#632` is
closed in the same dispatch/test paths without changing result schemas, backend
selection, public APIs, or OpenAPI.

## Lane Start Provenance

Packet: `artifacts/orchestration/task_packets/910a4151ec61.json`

Replacement packet: `artifacts/orchestration/task_packets/7492c83d4ee9.json`

Mixed-failure corrective packet:
`artifacts/orchestration/task_packets/378d20859cdd.json`

Final post-open packet: `artifacts/orchestration/task_packets/845bc26a3b44.json`

Current-head provenance corrective packet:
`artifacts/orchestration/task_packets/21207672e486.json`

Zero-attempt proof corrective packet:
`artifacts/orchestration/task_packets/afaa24da2da2.json`

Final runner-proof coherence packet:
`artifacts/orchestration/task_packets/807fdae1c4b4.json`

Final backend-provenance packet:
`artifacts/orchestration/task_packets/8e30e32ac3dd.json`

CodeQL status-output corrective packet:
`artifacts/orchestration/task_packets/6a4f7409cb4c.json`

Direct capability-provenance corrective packet:
`artifacts/orchestration/task_packets/28a934c1905c.json`

Direct consumer corrective packet:
`artifacts/orchestration/task_packets/c93c79c4a833.json`

- Fresh `origin/main` at `7c149a84c44406f698d73fbd0dee0bd34b64d085`
  was merged without history rewriting in
  `d998a82e8dd1ca1d1ab961f77b4acc143838f1d1`.
- Replacement role order completed as declared by the executable manifest:
  `agent-coordinator -> architecture-specialist -> security-auditor ->
  backend-engineer -> cursor-specialist-agent`.
- The earlier post-open order completed on prior material head
  `b5f8f07937161b428a547f5d57b389da77b85a83`; it is retained as historical
  evidence rather than presented as the current corrective pass.
- The current corrective pre-implementation order completed as declared:
  `agent-coordinator -> architecture-specialist -> security-auditor ->
  backend-engineer`.
- The terminal material review tail completed on published head
  `21343ba5560d71d5dc484feef86a92783558ae7f` in exact order:
  `architecture-specialist -> security-auditor -> backend-engineer ->
  qa-engineer-agent -> bug-hunter -> security-auditor`; every role returned
  `PROCEED` with no findings, and the post-security seal marked the tail
  terminal.
- The bounded CodeQL corrective order completed as coordinator-declared:
  `agent-coordinator -> architecture-specialist -> security-auditor ->
  backend-engineer -> qa-engineer-agent -> bug-hunter -> security-auditor`.
  The final `qa-engineer-agent -> bug-hunter -> security-auditor` tail ran on
  exact material head `9320795d6f57b67c112b9a4ca985817b43aeefa4`; every
  role returned `PROCEED` with no findings and the final security pass marked
  the tail terminal. The auto-routed `cursor-specialist-agent` was removed by
  the coordinator because no Cursor, packet-schema, or agent-definition
  surface changed.
- The direct capability-provenance correction completed in the declared order:
  `agent-coordinator -> architecture-specialist -> security-auditor ->
  backend-engineer -> qa-engineer-agent -> bug-hunter -> security-auditor`.
  The final three roles reviewed exact material head
  `da7650b0b1f7cc9c481639f66559a8f4652c8d0c`; every role returned `PROCEED`
  with no findings. Native scanning remained `operator_directed_stop`.
- The direct consumer correction completed in the declared order:
  `agent-coordinator -> architecture-specialist -> security-auditor ->
  backend-engineer -> qa-engineer-agent -> bug-hunter -> security-auditor`.
  The terminal three roles reviewed exact material head
  `05e6e0105d07ae82a3c8716319cf9c27766b4f48`; every role returned `PROCEED`
  with no findings and confirmed zero MyPy errors on changed lines. Native
  scanning remained `operator_directed_stop`.
- Local packets, role outputs, and Experiment Runner artifacts remain
  gitignored control-plane evidence.
- Experiment Runner oracle evidence materially shaped commit
  `3698beae144485d59ce97c1c742ebd1e66696059`, which carries the canonical
  co-author trailer. Later review-driven corrective commits did not use Runner
  evidence for their commit decisions and do not require another trailer.

## Implementation Commit

- `5803593d8d36b0645c214ff29606a6998cc3b261` - align all closed failure-class
  enum sites and add parity, persistence, sanitization, no-retry, and
  no-promotion regression coverage.
- `8241a9fd7` - reject unknown receipt failure tokens and contradictory
  top-level versus runner states while preserving legitimate wrapper-level
  rejection.
- `d6a74f3e3` - centralize result/receipt status, failure, runner, and workspace
  coherence so both validators report compound violations in the same order.
- `e203a39f8` - preserve `capability_mismatch` as a closed, non-retryable PR-4
  telemetry class instead of degrading it to `unknown`.
- `3698beae144485d59ce97c1c742ebd1e66696059` - admit only the coherent
  post-preflight rejected capability mismatch, reject accepted failures and
  rejected promotion authority, preserve trusted Apple backend provenance,
  and add deterministic sanitization/tamper regressions.
- `a8f8cbba895c88eee48334983734b0026d70eb60` - reject retried
  `capability_mismatch` observations across Experiment Runner, result, receipt,
  telemetry, and schemas while preserving `infra_flake 2/1`.
- `12893eee63ce1888ba093783d45c630e9cadf705` - require rejected root and
  rejected runner failure provenance to match without removing the legitimate
  rejected-wrapper / accepted-runner outcome.
- `2a3b277be40209bf1a116cafa77fedd072d0e243` - return the validated exact
  boolean from telemetry authority checks and reject bool-like values.
- `b5f8f07937161b428a547f5d57b389da77b85a83` - classify capability loss after
  a consumed infrastructure retry as a sanitized terminal `infra_flake`, while
  preserving direct capability loss as non-retryable `capability_mismatch`.
- `97ddb482cbfa642400e2ec00f4f1ccd025a5c4ae` - normalize a returned
  capability mismatch after an infrastructure retry through the same sanitized
  terminal path and require matching rejected runner proof in Python and JSON
  result/receipt contracts.
- `efa91adecac6adbc89b34a7117754ea56fed3c65` - reject zero-attempt
  capability summaries that report mutated paths or executed oracles across
  raw, result, receipt, and JSON Schema consumers while preserving configured
  oracles and direct `1/0` capability loss.
- `208d11c4fbe37cfd7d5258727b32f8cbaa3bd411` - require explicit failed backend
  preflight provenance for raw zero-attempt capability results.
- `8a2b0d8324750c103063aada7f25a9da2b9e9e27` - require complete accepted
  runner proof in standalone result/receipt validators and both schemas,
  derive terminal Oracle counters from retained evidence, and reject raw
  counter/list mismatches.
- `21343ba5560d71d5dc484feef86a92783558ae7f` - require trusted backend
  provenance for every capability mismatch and inject/overwrite dispatch-owned
  passed-probe metadata before strict validation.
- `9320795d6f57b67c112b9a4ca985817b43aeefa4` - convert runner-controlled CLI
  status to local `accepted`/`rejected` constants before artifact publication,
  fail closed on every other value, and add deterministic no-leak coverage for
  both terminal paths.
- `da7650b0b1f7cc9c481639f66559a8f4652c8d0c` - replace backendless direct
  capability artifacts with a data-free runner signal and let only dispatch
  attach trusted post-preflight provenance after successful cleanup.
- `05e6e0105d07ae82a3c8716319cf9c27766b4f48` - translate that signal at the
  direct builder and promotion callers before generic fallbacks, preserve
  promotion cleanup, emit fixed domain errors, and write no result or
  validation artifact.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Source PR #2130 replacement mapping recorded below.
- [x] Terminal material tail completed on final material head
  `05e6e0105d07ae82a3c8716319cf9c27766b4f48` in the bounded corrective
  order declared above; the final `qa-engineer-agent -> bug-hunter ->
  security-auditor` tail returned empty findings and the post-security seal
  marked the material tail terminal.
- [x] Earlier Codex Security scans marked superseded; operator-directed native
  scan stop recorded without a PASS claim or restart.
- Current-head CI, authenticated merge readiness, the mandatory wait window,
  and human merge authorization are live PR-state gates; they are intentionally
  not frozen as completed in this artifact.

## Local Role Findings

- FIXED in `8241a9fd77aa22123c7d9f7b891c991cf7949e68`: the post-open
  `bug-hunter` found unsupported receipt failure tokens and contradictory
  top-level versus runner states. The runtime validators, schemas, and
  deterministic tamper tests now enforce the canonical closed taxonomy and
  accepted/rejected coherence.
- NOT-A-BUG: the local `pulseplate-pr-review` dry run emitted only the
  mechanical `large-diff-risk` note. The 18-file surface is the smallest
  atomic result/receipt/telemetry/schema/test/governance propagation that
  prevents `capability_mismatch` from degrading to `unknown` and fixes the
  reachable mixed infrastructure/capability sequence reported on the published
  review head.
- FIXED in `3698beae144485d59ce97c1c742ebd1e66696059`: architecture and
  security review found that the direct PR #2130 deletion would also admit
  `accepted + failure_class`, while rejected results could retain promotion
  authority. General fail-closed outcome checks and the full canonical failure
  matrix now close both escalation paths.
- FIXED in `3698beae144485d59ce97c1c742ebd1e66696059`: the actual-diff
  premortem found a false-green sanitizer fixture that exercised only the
  generic `token=` redactor. The regression now uses an unlabeled bare GitHub
  token pattern and independently proves path and credential redaction.
- NOT-A-BUG: the runtime omitted the symlinked `pulseplate-workflow` slug from
  its cached skill catalog. The tracked worktree mirror and repo source resolve
  to identical content; the source skill was loaded explicitly and no skill
  installation or workflow-file change belongs in this PR.
- FIXED in `a8f8cbba895c88eee48334983734b0026d70eb60`: post-open review found that
  a non-retryable capability mismatch could carry retry observations. One
  shared validator and mirrored schemas now admit only direct `0/0` or `1/0`
  capability-loss observations.
- FIXED in `12893eee63ce1888ba093783d45c630e9cadf705`: post-open review found that
  rejected root and runner failure classes could disagree while identities
  remained valid. Shared outcome coherence, schema pairs, and telemetry now
  reject both mismatch directions before emission.
- FIXED in `2a3b277be40209bf1a116cafa77fedd072d0e243`: focused MyPy found an `Any`
  return in the telemetry boolean helper. Exact bool narrowing closes the type
  gap without weakening runtime checks.
- FIXED in `b5f8f07937161b428a547f5d57b389da77b85a83`: current-head review found a
  reachable `infra_flake -> retry -> capability loss` result that the strict
  capability contract would reject. The runner now stops immediately with a
  constant sanitized `infra_flake 2/1`; direct capability loss remains
  `capability_mismatch 1/0`.
- FIXED in `97ddb482cbfa642400e2ec00f4f1ccd025a5c4ae`: current-head review found
  that `_run_oracles()` could return `capability_mismatch` after a consumed
  infrastructure retry instead of raising `CapabilityMismatchError`. The
  returned result is now discarded and rebuilt as constant sanitized
  `infra_flake 2/1`; a retry-budget-two regression proves exactly two calls and
  absence of path, credential, and prior-infra canaries.
- FIXED in `97ddb482cbfa642400e2ec00f4f1ccd025a5c4ae`: architecture review found
  that top-level `capability_mismatch` could retain an accepted runner summary.
  Shared result/receipt coherence and both JSON Schemas now require rejected,
  matching runner proof while preserving legitimate wrapper-stage
  `guard_failure` over an accepted runner.
- FIXED in `efa91adecac6adbc89b34a7117754ea56fed3c65`: current-head review found
  that zero-attempt capability summaries could report mutation or executed
  oracle evidence. A shared validator, raw/result/receipt consumers, both
  schemas, and deterministic positive/negative tests now enforce coherent
  execution proof without constraining configured oracles or direct `1/0`.
- FIXED in `208d11c4fbe37cfd7d5258727b32f8cbaa3bd411`: the material bug-hunter tail
  proved that raw zero-attempt capability evidence could omit backend
  provenance. The raw validator now requires failed-preflight proof while
  preserving backend-less legacy accepted results and direct `1/0` outcomes.
- FIXED in `8a2b0d8324750c103063aada7f25a9da2b9e9e27`: exact-head review proved that
  standalone accepted results and receipts could omit full runner success
  proof. Shared coherence and both closed schemas now require at least one
  configured Oracle, exact configured/executed equality, and untouched shared
  tree proof before acceptance.
- FIXED in `8a2b0d8324750c103063aada7f25a9da2b9e9e27`: exact-head review reproduced a
  stale non-zero Oracle counter after an infra retry was converted to terminal
  `infra_flake` with no retained Oracle records. Result construction now
  derives the counter from retained evidence and raw validation rejects any
  present counter/list mismatch.
- FIXED in `21343ba5560d71d5dc484feef86a92783558ae7f`: exact-head review proved that
  raw post-preflight `capability_mismatch 1/0` could omit backend provenance.
  Strict validation now requires provenance for both `0/0` and `1/0`, while
  dispatch copies the raw result and injects exact trusted passed-probe
  provenance before validation; failed `0/0` evidence cannot be laundered.
- FIXED in `9320795d6f57b67c112b9a4ca985817b43aeefa4`: current-head CodeQL alert
  `#632` traced container result status into clear-text CLI output. Both run
  paths now select only literal-backed public constants before writing the
  artifact; a secret-like invalid status returns exit `2`, emits only the
  constant error, produces no stdout, and writes no artifact.
- FIXED in `da7650b0b1f7cc9c481639f66559a8f4652c8d0c`: current-head review found
  that direct runner APIs could still return backendless capability artifacts
  rejected by the strict validator. Direct raised and returned capability loss
  now becomes one data-free signal; the CLI writes no artifact, while dispatch
  alone converts exact exit `3` into strict-valid trusted `1/0` proof after
  successful cleanup. Shared-tree drift, cleanup failure, failed preflight
  `0/0`, and post-retry `2/1` retain precedence.
- FIXED in `05e6e0105d07ae82a3c8716319cf9c27766b4f48`: current-head review found
  that the PR-2 builder broad exception fallback could persist the internal
  signal as retryable `infra_flake`. The builder now catches only the exact
  signal first, emits a fixed domain error with suppressed chaining, leaves
  evaluation state unset, and writes no result or receipt artifact; ordinary
  runtime failures retain the existing sanitized fallback.
- FIXED in `05e6e0105d07ae82a3c8716319cf9c27766b4f48`: current-head review found
  that PR-3 fresh-oracle validation could expose the internal signal. The gate
  runner now translates only that signal to a fixed promotion-domain error;
  existing `finally` cleanup destroys the validation checkout and no
  validation, approval, receipt, or promotion path can proceed.
- FIXED in `05e6e0105d07ae82a3c8716319cf9c27766b4f48`: QA found two MyPy errors on
  newly added test lines. Runtime narrowing establishes the checkout dirname
  and run directory as typed paths, and a typed transport cast closes the
  fake-transport boundary. Automated intersection of MyPy diagnostics with
  changed-line ranges reports zero in-diff errors.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 8241a9fd77aa22123c7d9f7b891c991cf7949e68
Evidence: Both result and generation-receipt JSON Schemas require accepted outcomes to carry a null failure class, full workspace proof, and an accepted runner summary.
Reason: Schema-only consumers now reject the same contradictory accepted artifacts as the Python validators.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#discussion_r3575304858 -> 8241a9fd77aa22123c7d9f7b891c991cf7949e68

Disposition: FIXED
Commit: e203a39f8774c512ee2db0f6081bfa1b50f684bb
Evidence: The telemetry mapper, closed Python taxonomy, reference taxonomy, event and rollup schemas, and deterministic tests preserve `capability_mismatch` as `patch_evaluation / medium / not_retryable / dev-operator`.
Reason: PR-4 telemetry no longer loses the terminal capability or environment signal by mapping it to `unknown`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#discussion_r3575304857 -> e203a39f8774c512ee2db0f6081bfa1b50f684bb

Disposition: FIXED
Commit: d6a74f3e3ed8d1eedc27efcf05fdb20aa6d0a8b3
Evidence: Shared coherence classifiers are used by result and receipt validators, and compound-invalid regression cases prove identical runner-status precedence before workspace proof.
Reason: The duplicated coherence rules and divergent error precedence reported by CodeRabbit are removed without changing accepted artifact semantics.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#pullrequestreview-4690143681 -> d6a74f3e3ed8d1eedc27efcf05fdb20aa6d0a8b3

Disposition: FIXED
Commit: 44276b9af4d6fc153922bd5e9317358bcd78909d
Evidence: The canonical mapping marks `Discussion-thread pass completed` and contains disposition-specific proof for every actionable Codex and CodeRabbit review item.
Reason: The parser-required discussion-thread checkbox reflects the completed review audit.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#discussion_r3575382511 -> 44276b9af4d6fc153922bd5e9317358bcd78909d

Disposition: FIXED
Commit: e5a5b422e446bc92538da37e78ead0875de20d63
Evidence: The canonical artifact marks the exact `Discussion-thread pass completed` and `Fixed in commit mapping completed` checkboxes and records disposition-specific proof for every current review thread.
Reason: Checklist state and FIXED proof now agree on the final material head.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#discussion_r3586717095 -> e5a5b422e446bc92538da37e78ead0875de20d63

Disposition: FIXED
Commit: e5a5b422e446bc92538da37e78ead0875de20d63
Evidence: The parser-required `Fixed in commit mapping completed` checkbox is restored as its own exact line, while the source PR #2130 replacement note remains a separate checked item.
Reason: The Phase 2 artifact gate can now validate both required checklist labels without losing replacement provenance.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#discussion_r3586985650 -> e5a5b422e446bc92538da37e78ead0875de20d63

Disposition: NOT-A-BUG
Evidence: `git merge-base --is-ancestor <mapped_sha> b5f8f07937161b428a547f5d57b389da77b85a83` exits 0 for `8241a9fd`, `e203a39f`, `d6a74f3e`, and `44276b9a`; all four proof commits are in the current PR history.
Reason: The review referenced a non-current `ea1bd478` snapshot. Current local and published PR head truth contains every mapped FIXED commit.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#discussion_r3586985668

Disposition: NOT-A-BUG
Evidence: `_validate_gate_context()` rebuilds and validates the generation gate before `_generate_candidate()` checks the receipt path; `test_generate_candidate_persists_capability_mismatch_without_retry_or_promotion` passes on the current head.
Reason: A second generation request reaches the prepared-run stale-candidate guard before the receipt-exists check, so the asserted error matches the production control flow.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#discussion_r3586985674

Disposition: FIXED
Commit: b5f8f07937161b428a547f5d57b389da77b85a83
Evidence: The Experiment Runner classifies capability loss after a consumed infrastructure retry as rejected `infra_flake` with attempts `2`, retries `1`, `promotion_ready=false`, and a constant sanitized error; the deterministic regression also proves direct capability loss remains `capability_mismatch 1/0`.
Reason: The reachable mixed failure now produces a valid, honest terminal artifact without permitting a retry after capability loss or adding fallback authority.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#discussion_r3587200566 -> b5f8f07937161b428a547f5d57b389da77b85a83

Disposition: FIXED
Commit: 97ddb482cbfa642400e2ec00f4f1ccd025a5c4ae
Evidence: The retry loop checks successful attempt results after the infra-retry handler, discards a returned capability-mismatch payload after attempt one, and emits constant sanitized `infra_flake 2/1`; the retry-budget-two regression proves exactly two calls, no promotion, validator acceptance, and no raw canaries.
Reason: Returned and raised capability loss now share the same honest terminal outcome after an infrastructure retry without creating a third attempt or leaking runner details.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#discussion_r3587568042 -> 97ddb482cbfa642400e2ec00f4f1ccd025a5c4ae

Disposition: FIXED
Commit: 97ddb482cbfa642400e2ec00f4f1ccd025a5c4ae
Evidence: Shared Python coherence plus result and generation-receipt JSON Schemas require top-level `capability_mismatch` to carry runner `status=rejected`, matching `failure_class=capability_mismatch`, attempts `0/1`, and retries `0`; builder and receipt tests reject accepted runner proof and retain the valid wrapper-stage guard rejection.
Reason: Capability loss can no longer be attributed to a successful runner or survive with contradictory backend provenance.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#discussion_r3587568047 -> 97ddb482cbfa642400e2ec00f4f1ccd025a5c4ae

Disposition: NOT-A-BUG
Evidence: Published head `208d11c4fbe37cfd7d5258727b32f8cbaa3bd411` is the PR head, and `git merge-base --is-ancestor <mapped_sha> 208d11c4fbe37cfd7d5258727b32f8cbaa3bd411` exits 0 for every FIXED proof SHA in this artifact, including `8241a9fd`, `e203a39f`, `d6a74f3e`, `44276b9a`, `e5a5b422`, `b5f8f079`, and `97ddb482`.
Reason: The review reasoned from synthetic snapshot `eaebf23b`, which is neither the reviewed commit recorded by GitHub nor the published PR head; the mapped proof commits are present in current history.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#discussion_r3588115320

Disposition: NOT-A-BUG
Evidence: Material Oracle-shaped commit `3698beae144485d59ce97c1c742ebd1e66696059` and its replacement-evidence commit `8248afba40411444f1fc78791b29d3b605374121` contain the exact `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` trailer. Later review-driven commits did not use Runner evidence for their commit decisions.
Reason: The review again reasoned from non-current snapshot `eaebf23b`; the public material commit identified by the artifact already satisfies the attribution invariant.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#discussion_r3588115328

Disposition: FIXED
Commit: efa91adecac6adbc89b34a7117754ea56fed3c65
Evidence: Raw, result, and generation-receipt validators plus both JSON Schemas reject `capability_mismatch` with attempts `0` when mutation or executed-oracle evidence is nonzero; configured-but-unexecuted oracles and direct `1/0` remain valid. Follow-up commit `208d11c4fbe37cfd7d5258727b32f8cbaa3bd411` also requires failed backend-preflight provenance for the raw zero-attempt path.
Reason: A failed-preflight-shaped artifact can no longer carry impossible execution evidence or omit the backend proof that explains why no attempt ran.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#discussion_r3588115330 -> efa91adecac6adbc89b34a7117754ea56fed3c65

Disposition: FIXED
Commit: 8a2b0d8324750c103063aada7f25a9da2b9e9e27
Evidence: Standalone result and generation-receipt validators plus both JSON Schemas require accepted runner status, null failure, one or more configured Oracles, exact configured/executed equality, and untouched shared-tree proof; negative result/receipt and bounded schema-parity tests cover every reported bypass.
Reason: Telemetry and other standalone consumers can no longer accept incomplete runner success evidence.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#discussion_r3588654515 -> 8a2b0d8324750c103063aada7f25a9da2b9e9e27

Disposition: FIXED
Commit: 8a2b0d8324750c103063aada7f25a9da2b9e9e27
Evidence: The terminal result builder derives `oracle_commands_executed` from retained `oracle_results`, raw validation rejects counter/list mismatches, and the mixed infra/capability regression proves calls `2`, attempts/retries `2/1`, empty Oracle evidence, counter `0`, no third retry, sanitized `infra_flake`, and no promotion.
Reason: Discarded retry-attempt Oracle evidence can no longer leave a contradictory execution counter in the terminal artifact.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#discussion_r3588716979 -> 8a2b0d8324750c103063aada7f25a9da2b9e9e27

Disposition: NOT-A-BUG
Evidence: GitHub object lookup for synthetic `a5768c97` returns null, while every cited FIXED proof SHA is an ancestor of published head `21343ba5560d71d5dc484feef86a92783558ae7f` under `git merge-base --is-ancestor`.
Reason: The review again reasoned from a synthetic squash that is not the PR head; the unsquashed public owner history contains every mapped fix.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#discussion_r3588809755

Disposition: NOT-A-BUG
Evidence: Public ancestor commit `3698beae144485d59ce97c1c742ebd1e66696059` contains the exact `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` trailer, and later review-driven commits did not use Runner evidence for their commit decisions.
Reason: The attribution invariant applies to the material commit shaped by Runner evidence, not to a nonexistent synthetic squash or every later governance/review commit.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#discussion_r3588809759

Disposition: FIXED
Commit: 21343ba5560d71d5dc484feef86a92783558ae7f
Evidence: Raw validation rejects backendless capability mismatch for attempts `0` and `1`; dispatch injects exact trusted passed-probe provenance into a copy before validation, overwrites spoofed metadata, leaves caller input unchanged, and rejects failed-preflight `0/0` evidence under a passed probe.
Reason: Standalone raw consumers can no longer admit a post-preflight capability signal without trusted backend proof, while the dispatch boundary remains the sole authority that can attach that proof.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#discussion_r3588809763 -> 21343ba5560d71d5dc484feef86a92783558ae7f

Disposition: NOT-A-BUG
Evidence: GitHub marks this thread outdated on governance commit `693532fe9ecf523e030721a76ebf8439d5dfd15f`; published head `0ddcd0b4f7e753a512570672c11e678db2d76a50` contains ancestor `21343ba5560d71d5dc484feef86a92783558ae7f`, whose raw validator and dispatch regressions already reject or repair every reported backendless capability path.
Reason: The automatic reviewer repeated `discussion_r3588809763` against an older commit after the correction was already published; the current implementation is correct and no new execution path exists.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#discussion_r3589076057

Disposition: NOT-A-BUG
Evidence: GitHub object lookup for synthetic `ea3878f8` returns null, while every FIXED proof SHA listed in this artifact is an ancestor of published head `0ddcd0b4f7e753a512570672c11e678db2d76a50` under `git merge-base --is-ancestor`.
Reason: The automatic reviewer again reasoned from a synthetic squash that is neither a GitHub commit object nor the PR head; the unsquashed owner history contains every mapped fix.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#discussion_r3589076065

Disposition: NOT-A-BUG
Evidence: Public ancestor commit `3698beae144485d59ce97c1c742ebd1e66696059` contains the exact `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` trailer, and later review/governance commits did not use Runner evidence for their commit decisions.
Reason: The attribution invariant applies to the public material commit shaped by Runner evidence, not to nonexistent synthetic squash `ea3878f8` or every later governance commit.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#discussion_r3589076070

Disposition: FIXED
Commit: da7650b0b1f7cc9c481639f66559a8f4652c8d0c
Evidence: Direct candidate and Oracle runner paths emit a data-free signal and no artifact; the CLI uses fixed exit `3`, and dispatch converts only that exit after passed backend preflight and successful cleanup into validated rejected `capability_mismatch` with trusted provenance, attempts `1`, retries `0`, and promotion disabled.
Reason: Direct runner consumers can no longer publish backendless capability proof or fabricate execution provenance; failed preflight, cleanup/shared-tree failures, and post-infra-retry outcomes remain fail closed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#discussion_r3589281986 -> da7650b0b1f7cc9c481639f66559a8f4652c8d0c

Disposition: NOT-A-BUG
Evidence: Published head `e5d19d7fef92f0e3f65c526874b25f6a9542720e` contains ancestor `da7650b0b1f7cc9c481639f66559a8f4652c8d0c`; its direct candidate and Oracle paths raise the data-free `RunnerCapabilitySignal`, the CLI exits `3` without writing an artifact, and the full runner/dispatch suites pass.
Reason: The automatic reviewer repeated the already-fixed direct-producer finding while reasoning from synthetic commit `81223267`; the current published implementation cannot emit the backendless capability artifact described by the comment.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#discussion_r3590431927

Disposition: NOT-A-BUG
Evidence: GitHub attaches this thread to published commit `e5d19d7fef92f0e3f65c526874b25f6a9542720e`, whose unsquashed owner history contains every FIXED proof commit; the canonical ancestry evidence is the published PR head, not reviewer-generated synthetic commit `81223267`.
Reason: The automatic reviewer repeated the earlier synthetic-squash ancestry claim without identifying a GitHub PR-head commit or a missing fix in the published owner history.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#discussion_r3590431932

Disposition: FIXED
Commit: 05e6e0105d07ae82a3c8716319cf9c27766b4f48
Evidence: The builder catches exact `RunnerCapabilitySignal` before its generic fallback, raises a fixed `CreativeCodePatchBuilderError` with suppressed chaining, writes no `result.json`, leaves `candidate_patch_evaluated` unset, and its CLI test proves no canary or traceback; generic `RuntimeError` still produces the existing sanitized `infra_flake` artifact.
Reason: PR-2 generation can no longer persist the internal capability signal as a retryable false artifact or fabricate backend provenance.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#discussion_r3590772779 -> 05e6e0105d07ae82a3c8716319cf9c27766b4f48

Disposition: FIXED
Commit: 05e6e0105d07ae82a3c8716319cf9c27766b4f48
Evidence: `GateRunner.run_fresh_oracle()` translates exact `RunnerCapabilitySignal` to a fixed `CreativeCodePRPromotionError` with suppressed chaining; validation cleanup destroys the checkout, no validation artifact is written, and the terminal test proves canary absence.
Reason: PR-3 validation now fails deterministically inside its public domain contract instead of exposing an internal traceback, while no promotion authority or provenance is synthesized.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#discussion_r3590772783 -> 05e6e0105d07ae82a3c8716319cf9c27766b4f48

## Source PR #2130 Replacement Mapping

| Source evidence | Disposition | Owner replacement | Evidence |
| --- | --- | --- | --- |
| PR #2130 head `5538147f5f8db9d7188b1612422b552775f3ce9a` | SUPERSEDED | `3698beae144485d59ce97c1c742ebd1e66696059` | Reimplemented the narrow relaxation with general accepted/failure and rejected/promotion fail-closed checks instead of applying the source diff directly. |
| [Sourcery discussion r3578862151](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2130#discussion_r3578862151) | FIXED | `3698beae144485d59ce97c1c742ebd1e66696059` | The Apple Container regression asserts `status=rejected`, exact trusted backend provenance, attempts `1`, retries `0`, `promotion_ready=false`, sanitized runner error, and spoofed-provenance overwrite. |

## Experiment Runner Evidence

Artifact:
`artifacts/orchestration/experiments/results/pr2119-post-preflight-capability-oracle-result.json`

Experiment `exp-bad0eafaee64` was accepted through the explicit
`apple-container` backend, runtime `1.1.0`, immutable image digest
`sha256:8b95aa8a94d989ff18af7449fbb0feae6783623a7bf49434f0e16341bd61c483`,
and `apple_internal_no_dns_plus_linux_unshare`. All three immutable oracle
commands passed with network budget zero, one attempt, zero retries, no mutated
paths, and no promotion authority. The accepted evidence shaped the commit
decision, so the implementation commit carries the canonical Experiment Runner
co-author trailer. The artifact is local-only and gitignored.

The older
`pr2-capability-mismatch-taxonomy-oracle-strict-result.json` artifact is
superseded by this replacement-head evidence.

## Validation Evidence

- PASS on material head `b5f8f07937161b428a547f5d57b389da77b85a83`:
  18-path scoped execution preflight and agent consistency.
- PASS: the full six-file focused contract, Experiment Runner, dispatch,
  patch-builder, generation, and telemetry regression bundle.
- PASS: the exact direct-capability, mixed-failure, and infra-retry tests; the
  mixed result also passes `validate_experiment_result` as sanitized rejected
  `infra_flake 2/1` with no promotion authority.
- PASS: Ruff and canonical MyPy with no incremental cache across all six
  changed orchestration source files.
- PASS: commit hooks, including detect-secrets, Ruff, type-hint checks, Bandit,
  and changed backend tests.
- PASS: `make validate-changed` and the exact `BRANCH_DIFF_MODE=1`
  pre-commit backend-test path; both selected the five changed owner/runner
  test files and passed.
- PASS: `pre-commit run --all-files`, including detect-secrets, workflow
  checks, Black, Ruff, Bandit, frontend tests, changed backend tests, and iOS
  syntax; hooks made no file changes.
- PASS: `git diff --check`.
- PASS: actual-diff premortem on the final two-file corrective diff, with no
  actionable findings.
- PASS on code head `97ddb482cbfa642400e2ec00f4f1ccd025a5c4ae`:
  eight-test targeted regression selection; full runner/builder/generation
  suites; and the six-suite runner/dispatch/pipeline/builder/generation/
  telemetry bundle.
- PASS on code head `97ddb482cbfa642400e2ec00f4f1ccd025a5c4ae`:
  Black, Ruff, pre-push-shape MyPy, commit hooks, and `git diff --check`.
- PASS: actual-diff premortem for the current eight-file corrective delta;
  loop control, third-retry, raw-result leakage, Python/schema parity, and
  wrapper-rejection compatibility risks are covered by deterministic tests.
- PASS on final material head
  `208d11c4fbe37cfd7d5258727b32f8cbaa3bd411`: targeted zero-attempt tests,
  full dispatch suite, the committed-diff five-suite bundle, Black, Ruff,
  canonical changed-file MyPy, pre-commit, pip-audit, full Bandit, and Docker
  pre-push hooks.
- PASS: actual-diff premortem covers Python/schema drift, configured-oracle
  over-constraint, direct `1/0` regression, and missing backend provenance;
  every material finding is fixed in executable validators and tests.
- PASS on final material head
  `208d11c4fbe37cfd7d5258727b32f8cbaa3bd411`: final
  `qa-engineer-agent -> bug-hunter -> security-auditor` tail returned
  `PROCEED` with no findings. Native Codex Security remained
  `operator_directed_stop` and was not invoked.
- PASS on terminal material head
  `8a2b0d8324750c103063aada7f25a9da2b9e9e27`: targeted reproducers and the
  full five-suite runner/dispatch/builder/generation/telemetry bundle;
  canonical changed-file MyPy; Black, Ruff, `git diff --check`, committed-diff
  `make validate-changed`, full pre-commit, pip-audit, full Bandit, backend,
  and Docker pre-push hooks.
- PASS: actual-diff premortem covers Python/schema drift, rejected-wrapper
  compatibility, discarded Oracle evidence, and optional legacy counter
  compatibility; all four risks are closed in code/tests.
- PASS on terminal material head
  `8a2b0d8324750c103063aada7f25a9da2b9e9e27`: serial
  `architecture-specialist -> security-auditor -> backend-engineer ->
  qa-engineer-agent -> bug-hunter` tail returned `PROCEED` with no findings.
  Native Codex Security remained `operator_directed_stop` and was not invoked.
- PASS on terminal material head
  `21343ba5560d71d5dc484feef86a92783558ae7f`: seven targeted provenance
  cases, full dispatch suite, committed-diff five-suite selection, canonical
  MyPy, Black, Ruff, `git diff --check`, full pre-commit, pip-audit, backend,
  full Bandit, and Docker pre-push hooks.
- PASS: final backend-provenance premortem covers validation order, spoofed
  metadata, failed-preflight laundering, caller mutation, and legacy
  non-capability compatibility; every risk is closed in code/tests.
- PASS on terminal material head
  `21343ba5560d71d5dc484feef86a92783558ae7f`: serial
  `architecture-specialist -> security-auditor -> backend-engineer ->
  qa-engineer-agent -> bug-hunter -> security-auditor` returned `PROCEED` with
  no findings; the final security seal marked `material_tail: TERMINAL` and
  native scanning remained `operator_directed_stop`.
- PASS on final material head
  `9320795d6f57b67c112b9a4ca985817b43aeefa4`: accepted/rejected constant
  mapping and secret-like invalid-status no-leak tests; full dispatch suite;
  committed-diff five-suite selection; canonical MyPy with explicit package
  bases; Black, Ruff, `git diff --check`; exact pre-commit backend selector;
  and `pre-commit run --all-files` including detect-secrets and Bandit.
- PASS: actual-diff CodeQL premortem covers stderr echo, write-before-check,
  early network-budget divergence, exit-code drift, and static-analysis taint;
  the first four risks are closed in code/tests and current-head CodeQL is the
  final proof for the fifth.
- PASS on final material head
  `9320795d6f57b67c112b9a4ca985817b43aeefa4`: bounded
  `agent-coordinator -> architecture-specialist -> security-auditor ->
  backend-engineer -> qa-engineer-agent -> bug-hunter -> security-auditor`
  pass returned `PROCEED` with no findings. The final security seal marked
  `material_tail: TERMINAL`; native scanning remained
  `operator_directed_stop` and was not invoked.
- PASS on final material head
  `da7650b0b1f7cc9c481639f66559a8f4652c8d0c`: complete runner and dispatch
  suites plus notify, promote, patch-builder, generation, and telemetry;
  Black, Ruff, canonical MyPy with explicit package bases, `git diff --check`,
  scoped preflight, agent consistency, `make validate-changed`, exact backend
  selector, and `pre-commit run --all-files`.
- PASS: direct capability-signal premortem covers exit-code collision,
  cleanup/shared-tree precedence, artifact and canary leakage, direct-consumer
  fail-closed behavior, and preservation of `0/0`, `1/0`, and `2/1` outcomes.
- PASS on final material head
  `da7650b0b1f7cc9c481639f66559a8f4652c8d0c`: serial
  `qa-engineer-agent -> bug-hunter -> security-auditor` tail returned
  `PROCEED` with no findings; native scanning remained
  `operator_directed_stop` and was not invoked.
- PASS on final material head
  `05e6e0105d07ae82a3c8716319cf9c27766b4f48`: complete builder and promotion
  suites, the seven-suite runner/dispatch/builder/generation/promotion/
  telemetry/promote bundle, Black, Ruff, canonical production MyPy,
  `git diff --check`, scoped preflight, agent consistency,
  committed-diff `make validate-changed`, exact backend selector, and full
  pre-commit.
- PASS: automated MyPy-to-diff intersection reports zero diagnostics on added
  or modified lines after QA's two in-diff findings were fixed.
- PASS: direct consumer premortem covers retryable false artifacts, domain
  error leakage, cleanup precedence, generic-failure preservation,
  provenance fabrication, and higher-level generation error handling.
- PASS on final material head
  `05e6e0105d07ae82a3c8716319cf9c27766b4f48`: serial
  `qa-engineer-agent -> bug-hunter -> security-auditor` tail returned
  `PROCEED` with no findings; native scanning remained
  `operator_directed_stop` and was not invoked.
- ADVISORY: `pulseplate-pr-review` on final material head
  `9320795d6f57b67c112b9a4ca985817b43aeefa4` found no deterministic
  security or architecture issue; its only notes were the already-justified
  large-diff risk and the expected pre-publish local/remote head mismatch.
  Published-head context refresh remains a live readiness check and does not
  reopen material review.
- LOOP STOP: material evidence is anchored to code head
  `05e6e0105d07ae82a3c8716319cf9c27766b4f48`; this mapping/body
  reconciliation is governance-only. The ancestry and trailer comments were
  closed by evidence without a material restart; the direct producer finding
  identified one genuinely new execution path and received one bounded
  corrective wave. The later builder/promotion comments identified two real
  direct consumers and received one final bounded consumer correction. The
  current-head CodeQL HIGH likewise received one bounded correction earlier.
  Equivalent duplicate or stale review text does not trigger another role or
  security wave. The operator disabled Codex GitHub automatic reviews; one
  already-queued review still arrived and is fully dispositioned above. The
  bounded alternatives and stop rule are
  recorded locally in
  `artifacts/orchestration/pr2119-review-loop-brainstorm.md`.
- PASS: explicit Apple Container oracle evidence, three of three commands.
- HISTORICAL FAILURE: Docker build run `29311424356` failed only while
  preparing source artifacts because `review_by: 2026-07-13` was stale.
- REMEDIATED OUTSIDE THIS PR: PR #2133, merge
  `b432aeb78a6b18cdedf760bb7872daf9241dacd6`, contains commit
  `ad381545dc487764f1ed1ad54a311c03b05e4467`, which refreshed the Docker
  source-artifact review window. Current-main Docker run `29398196158`
  completed successfully on `7861b960e8ab02b839ae1cf36e77d2bdcc9da717`.
- SUPERSEDED: Codex Security scan
  `3062dc47-44f4-4cdd-b7c0-eedcf726103a` found zero issues on exact head
  `b156a4f690e190d6581e5d60553d524f015f8d27`; later security-relevant review
  fixes changed the material diff.
- SUPERSEDED: Codex Security scan
  `7ab0578d-f469-4149-a2e3-025a3e532dfa` covered all four changed
  source-like files at exact material head
  `5463ac2a5a6f310cc510e46c1cfcb6aa2c50d11d`, snapshot
  `b6de86840ef62d42488cce7b1e8ee07e5dd07807711041daa575b943a11eaaee`,
  with complete coverage and zero findings on that older material. Commit
  `3698beae144485d59ce97c1c742ebd1e66696059` changed security-relevant
  validator and sanitizer tests, so that sealed scan is not current evidence.
- OPERATOR-DIRECTED STOP: native Codex Security scanning is disabled for this
  lane after repeated unstable scan/session transport. No replacement scan was
  run and no scan PASS is claimed. Deterministic security evidence consists of
  the ordered security-auditor pass, Bandit/detect-secrets hooks, redaction and
  provenance-tamper tests, mixed-failure canary tests, the Apple Container
  oracle, and pending current-head CI security.
- LIVE FINAL GATE: current-head CodeQL must close alert `#632`; current-head CI,
  authenticated merge readiness, bot dispositions, the mandatory wait window,
  and human authorization must still complete on the published replacement
  head.

Full local `make verify` was not run because repository policy prohibits that
machine-heavy invocation without a one-time human override.

## Security Review

Both earlier sealed scans are superseded by the replacement material commit.
Under the explicit operator stop, no native scan was run or claimed. The
replacement adds no network, provider, fallback, promotion, product-runtime,
or cache authority; ordered security review plus deterministic tests prove
that untrusted backend provenance is overwritten, local paths and credentials
are redacted, accepted failures are rejected, rejected results cannot retain
promotion authority, zero-attempt capability results require failed-preflight
backend proof and contain no execution evidence, and capability loss after an
infrastructure retry cannot leak the underlying exception. Runner-controlled
status now crosses a constant-only CLI boundary before artifact publication;
unknown values fail with a fixed error and are absent from stdout, stderr, and
the output artifact. Direct runner capability loss is data-free and
artifact-free; dispatch recognizes only exact exit `3` after passed preflight,
successful cleanup, and trusted probe ownership. Direct builder and promotion
consumers translate only the exact signal to fixed domain errors, emit no
traceback/canary, fabricate no provenance, and retain cleanup. Current-head
CodeQL and CI security remain live gates.

## Risks / Rollback

Risk is limited to internal outcome validation and taxonomy compatibility.
Accepted results reject every non-null canonical failure, rejected results
cannot be promotion-ready, and failed preflight still requires a rejected
capability mismatch with explicit backend provenance, zero attempts, and no
mutation or executed-oracle evidence. Compound infrastructure/capability
failure is classified as `infra_flake` only after an infrastructure retry was
already consumed. CLI status output remains exactly `accepted` or `rejected`,
with invalid internal status failing closed before publication. Rollback is a
revert of PR #2119; no database, runtime, public API, provider, cache, client,
or migration rollback is required.

## Deferred / Follow-ups

After terminal merge and post-merge evidence, begin a fresh RAG pilot revision
from current `origin/main`. Do not repair, rebase, or retry the retained r4
terminal run. Any execution-backend or isolation-authority change requires a
separate governed lane.
