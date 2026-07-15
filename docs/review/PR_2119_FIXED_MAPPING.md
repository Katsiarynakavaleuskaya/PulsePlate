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
closed contracts cannot validate.

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
inside those same 18 paths; they do not expand the published file surface.

## Lane Start Provenance

Packet: `artifacts/orchestration/task_packets/910a4151ec61.json`

Replacement packet: `artifacts/orchestration/task_packets/7492c83d4ee9.json`

Mixed-failure corrective packet:
`artifacts/orchestration/task_packets/378d20859cdd.json`

Final post-open packet: `artifacts/orchestration/task_packets/845bc26a3b44.json`

Current-head provenance corrective packet:
`artifacts/orchestration/task_packets/21207672e486.json`

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
- The current material review tail completed on governance review head
  `b9e146455745c184f2f8f93e6ba6297007b98883` in exact order:
  `qa-engineer-agent -> bug-hunter -> security-auditor`.
- Local packets, role outputs, and Experiment Runner artifacts remain
  gitignored control-plane evidence.
- Experiment Runner oracle evidence materially shaped the commit decision; the
  implementation commit carries the canonical co-author trailer.

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

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Source PR #2130 replacement mapping recorded below.
- [x] Post-open `qa-engineer-agent -> bug-hunter -> security-auditor` rerun
  completed on governance review head
  `b9e146455745c184f2f8f93e6ba6297007b98883`; QA found no implementation
  defect and its governance-only stale-role wording finding is corrected in
  this closeout.
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
- PASS on governance review head
  `b9e146455745c184f2f8f93e6ba6297007b98883`: QA reported no implementation
  findings and one governance-only stale-role wording correction; bug-hunter
  and security-auditor then returned `PROCEED` with no findings. This closeout
  incorporates the QA correction without restarting the material role chain.
- ADVISORY: `pulseplate-pr-review` on local governance head `b9e146455745`
  found only the already-justified large-diff note plus the expected warning
  that the two local commits were not yet published. Published-head context
  refresh remains a live readiness check and does not reopen material review.
- LOOP STOP: material evidence is anchored to code head
  `97ddb482cbfa642400e2ec00f4f1ccd025a5c4ae`; this mapping/body reconciliation
  is governance-only. Equivalent duplicate or stale review text does not
  trigger another role or security wave. The bounded alternatives and stop
  rule are recorded locally in
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
- LIVE FINAL GATE: current-head CI, authenticated merge readiness, bot
  dispositions, the mandatory wait window, and human authorization must still
  complete on the published replacement head.

Full local `make verify` was not run because repository policy prohibits that
machine-heavy invocation without a one-time human override.

## Security Review

Both earlier sealed scans are superseded by the replacement material commit.
Under the explicit operator stop, no native scan was run or claimed. The
replacement adds no network, provider, fallback, promotion, product-runtime,
or cache authority; ordered security review plus deterministic tests prove
that untrusted backend provenance is overwritten, local paths and credentials
are redacted, accepted failures are rejected, rejected results cannot retain
promotion authority, and capability loss after an infrastructure retry cannot
leak the underlying exception. Current-head CI security remains a live gate.

## Risks / Rollback

Risk is limited to internal outcome validation and taxonomy compatibility.
Accepted results reject every non-null canonical failure, rejected results
cannot be promotion-ready, and failed preflight still requires a rejected
capability mismatch. Compound infrastructure/capability failure is classified
as `infra_flake` only after an infrastructure retry was already consumed.
Rollback is a revert of PR #2119; no database, runtime, public API, provider,
cache, client, or migration rollback is required.

## Deferred / Follow-ups

After terminal merge and post-merge evidence, begin a fresh RAG pilot revision
from current `origin/main`. Do not repair, rebase, or retry the retained r4
terminal run. Any execution-backend or isolation-authority change requires a
separate governed lane.
