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

## Discussion Thread Pass

- [ ] Discussion-thread pass completed.
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
- PENDING: sealed Codex Security scan, canonical current-head CI, and strict
  authenticated merge readiness.

Full local `make verify` was not run because repository policy prohibits that
machine-heavy invocation without a one-time human override.

## Security Review

Pending one sealed Codex Security scan for the final material diff. The change
adds no network, provider, retry, promotion, product-runtime, or cache
authority; rejected receipts remain sanitized and fail closed.

## Risks / Rollback

Risk is limited to taxonomy compatibility. Accepted results continue to reject
non-null failure classes. Rollback is a revert of PR #2119; no database,
runtime, API, provider, cache, client, or migration rollback is required.

## Deferred / Follow-ups

After terminal merge and post-merge evidence, begin a fresh RAG pilot revision
from current `origin/main`. Do not repair, rebase, or retry the retained r4
terminal run. Any execution-backend or isolation-authority change requires a
separate governed lane.
