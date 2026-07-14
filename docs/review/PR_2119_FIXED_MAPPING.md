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
- [ ] Codex Security scan completed for the final material diff.
- [ ] Canonical current-head CI completed.
- [ ] Strict authenticated merge readiness and mandatory wait window completed.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: `8241a9fd7`
Evidence: `scripts/orchestration/creative_code_patch_generation.py` now rejects
unsupported top-level and nested receipt failure classes; focused tamper tests
cover both fields with recomputed deterministic identities.
Reason: The runtime receipt validator now enforces the same canonical closed
taxonomy as the Python result contract and both JSON Schemas.
- Post-open `bug-hunter` finding: unsupported receipt failure tokens.

Disposition: FIXED
Commit: `8241a9fd7`
Evidence: result and receipt validators plus their JSON Schemas now require an
accepted top-level outcome to contain an accepted runner summary, couple runner
status to failure nullability, and retain the valid top-level rejected / runner
accepted wrapper case.
Reason: Contradictory accepted/rejected states can no longer be sealed with a
recomputed identity.
- Post-open `bug-hunter` finding: top-level and runner status incoherence.

Disposition: FIXED
Commit: `8241a9fd77aa22123c7d9f7b891c991cf7949e68`
Evidence: both result and generation-receipt JSON Schemas now use accepted and
rejected `allOf` branches that require accepted outcomes to carry a null
failure class, full workspace proof, and an accepted runner summary.
Reason: schema-only consumers now reject the same contradictory accepted
artifacts as the Python validators.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#discussion_r3575304858 -> 8241a9fd77aa22123c7d9f7b891c991cf7949e68

Disposition: FIXED
Commit: `e203a39f8774c512ee2db0f6081bfa1b50f684bb`
Evidence: `creative_code_telemetry.py`, the closed Python taxonomy, reference
taxonomy, event/rollup schemas, and deterministic telemetry tests now preserve
`capability_mismatch` as `patch_evaluation / medium / not_retryable /
dev-operator`.
Reason: PR-4 telemetry no longer loses the terminal capability/environment
signal by mapping it to `unknown`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#discussion_r3575304857 -> e203a39f8774c512ee2db0f6081bfa1b50f684bb

Disposition: FIXED
Commit: `d6a74f3e3ed8d1eedc27efcf05fdb20aa6d0a8b3`
Evidence: `classify_failure_class_coherence()` and
`classify_terminal_outcome_coherence()` are shared by result and receipt
validators; compound-invalid regression cases prove runner-status precedence
before workspace proof in both domains.
Reason: the duplicated coherence rules and divergent error precedence reported
by CodeRabbit are removed without changing accepted artifact semantics.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#pullrequestreview-4690143681 -> d6a74f3e3ed8d1eedc27efcf05fdb20aa6d0a8b3

Disposition: FIXED
Commit: `44276b9af4d6fc153922bd5e9317358bcd78909d`
Evidence: the canonical mapping now marks `Discussion-thread pass completed`
and contains disposition-specific proof for every current actionable Codex and
CodeRabbit review item.
Reason: the parser-required discussion-thread checkbox now reflects the
completed review audit instead of remaining stale.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2119#discussion_r3575382511 -> 44276b9af4d6fc153922bd5e9317358bcd78909d

No GitHub review thread has been resolved. Any later actionable thread must be
added here with its disposition-specific proof before resolution.

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
  fixes changed the material diff, so a fresh sealed scan is required.
- PENDING: fresh sealed Codex Security scan, canonical current-head CI, and
  strict authenticated merge readiness.

Full local `make verify` was not run because repository policy prohibits that
machine-heavy invocation without a one-time human override.

## Security Review

The initial sealed scan found zero issues but is superseded by the subsequent
coherence and telemetry fixes. A fresh exact-head scan remains required. The
change adds no network, provider, retry, promotion, product-runtime, or cache
authority; rejected receipts and telemetry remain sanitized and fail closed.

## Risks / Rollback

Risk is limited to taxonomy compatibility. Accepted results continue to reject
non-null failure classes. Rollback is a revert of PR #2119; no database,
runtime, API, provider, cache, client, or migration rollback is required.

## Deferred / Follow-ups

After terminal merge and post-merge evidence, begin a fresh RAG pilot revision
from current `origin/main`. Do not repair, rebase, or retry the retained r4
terminal run. Any execution-backend or isolation-authority change requires a
separate governed lane.
