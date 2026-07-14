# PR #2119 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119

Branch: `codex/align-pr2-runner-failure-taxonomy`

## Summary

Align the creative-code PR-2 result and generation-receipt taxonomies with the
canonical Experiment Runner `capability_mismatch` outcome so an unavailable
isolation capability is retained as a sanitized terminal rejection without a
retry or promotion path.

## Lane Start Provenance

Packet: `artifacts/orchestration/task_packets/910a4151ec61.json`

- Coordinator-first pre-open routing and every assigned role pass completed in
  packet order.
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

## Discussion Thread Pass

- [x] Discussion-thread pass completed.
- [x] Fixed in commit mapping completed.
- [x] Post-open `qa-engineer-agent -> bug-hunter -> security-auditor` completed.
- [x] Codex Security scan completed for the final material diff.
- [ ] Canonical current-head CI completed.
- [ ] Strict authenticated merge readiness and mandatory wait window completed.

## Local Role Findings

- FIXED in `8241a9fd77aa22123c7d9f7b891c991cf7949e68`: the post-open
  `bug-hunter` found unsupported receipt failure tokens and contradictory
  top-level versus runner states. The runtime validators, schemas, and
  deterministic tamper tests now enforce the canonical closed taxonomy and
  accepted/rejected coherence.
- NOT-A-BUG: the local `pulseplate-pr-review` dry run emitted only the
  mechanical `large-diff-risk` note. The 14-file surface is the smallest
  atomic result/receipt/telemetry/schema/test/governance propagation that
  prevents `capability_mismatch` from degrading to `unknown`.

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

## Experiment Runner Evidence

Artifact:
`artifacts/orchestration/experiments/results/pr2-capability-mismatch-taxonomy-oracle-strict-result.json`

The strict oracle-only run was accepted under Apple Container isolation with
network budget zero, zero retries, no mutated paths, and no promotion
authority. The artifact is local-only and gitignored.

## Validation Evidence

- PASS: expanded creative-code contract, generation, inventory, Experiment
  Runner, and dispatcher tests after both post-open fixes.
- PASS: review-pattern oracle tests.
- PASS: `make validate-changed` (78 tests post-commit).
- PASS: orchestration preflight and agent consistency.
- PASS: `pre-commit run --all-files`.
- PASS: pre-push Black, Ruff, MyPy, pip-audit, backend tests, Bandit, and Docker
  hooks.
- PASS: mandatory post-open QA, bug-hunter, and security role chain.
- PASS: focused patch-contract, generation, and telemetry suites after review
  fixes, including compound coherence precedence and non-retryable telemetry
  preservation.
- SUPERSEDED: Codex Security scan
  `3062dc47-44f4-4cdd-b7c0-eedcf726103a` found zero issues on exact head
  `b156a4f690e190d6581e5d60553d524f015f8d27`; later security-relevant review
  fixes changed the material diff.
- PASS: final Codex Security scan
  `7ab0578d-f469-4149-a2e3-025a3e532dfa` covered all four changed
  source-like files at exact material head
  `5463ac2a5a6f310cc510e46c1cfcb6aa2c50d11d`, snapshot
  `b6de86840ef62d42488cce7b1e8ee07e5dd07807711041daa575b943a11eaaee`,
  with complete coverage and zero findings.
- PENDING: parser-safe mapping/body publication, canonical current-head CI,
  and strict authenticated merge readiness.

Full local `make verify` was not run because repository policy prohibits that
machine-heavy invocation without a one-time human override.

## Security Review

The final sealed scan found zero issues across the exact result, receipt, and
telemetry material diff. The change adds no network, provider, retry, promotion,
product-runtime, or cache authority; rejected receipts and telemetry remain
sanitized and fail closed.

## Risks / Rollback

Risk is limited to taxonomy compatibility. Accepted results continue to reject
non-null failure classes. Rollback is a revert of PR #2119; no database,
runtime, API, provider, cache, client, or migration rollback is required.

## Deferred / Follow-ups

After terminal merge and post-merge evidence, begin a fresh RAG pilot revision
from current `origin/main`. Do not repair, rebase, or retry the retained r4
terminal run. Any execution-backend or isolation-authority change requires a
separate governed lane.
