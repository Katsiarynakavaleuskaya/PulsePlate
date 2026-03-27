# PR 1255 - Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1255#pullrequestreview-4019517221
Disposition: NOT-A-BUG
Evidence: `package.json:28`, `tests/test_root_npm_dependency_guards.py:56`, `tests/test_root_npm_dependency_guards.py:91`, `docs/security/GHSA-f886-m6hf-6m8v-brace-expansion.md:43`
Reason: the high-level Sourcery summary is advisory rather than a separate defect. Repo-root overrides are intentional because this PR remediates the root npm graph, not only one nested subtree, and the strict lockfile guards are deliberate policy tests for the canonical AgentGuard dependency path and npm registry source.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1255#pullrequestreview-4019524382 -> 65bdf110
Disposition: FIXED
Commit: 65bdf110
Evidence: `docs/security/GHSA-f886-m6hf-6m8v-brace-expansion.md:45`
Reason: the review asked for explicit `file:line` evidence anchors in the security remediation note, and commit `65bdf110` updated the Evidence Anchors block accordingly.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1255#pullrequestreview-4020582709
Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-runner-disk-reclaim-centralization`, `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-runner-disk-reclaim-safety-guards`
Evidence: `tests/test_python_supply_chain_controls.py:215`, `tests/test_root_npm_dependency_guards.py:56`, `docs/roadmap/BACKLOG_LEDGER.md:7922`
Reason: the Sourcery summary bundles two in-scope test gaps and two broader workflow hardening follow-ups. The order-check and nested `brace-expansion` guard gaps were fixed in commit `65bdf110`; the reclaim-step centralization and destructive-shell safety hardening are intentionally deferred to the linked follow-up ledger items to keep PR `#1255` scoped to the current dependency-security lane.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1255#discussion_r3000499426
Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-runner-disk-reclaim-centralization`
Evidence: `.github/workflows/ci.yml:479`, `.github/workflows/build.yml:34`, `.github/workflows/docker-image.yml:28`
Reason: extracting the reclaim shell into a shared composite action or reusable workflow is valid maintainability work, but it is intentionally deferred so PR `#1255` stays narrow and focused on the active security unblock.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1255#discussion_r3000499429
Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-runner-disk-reclaim-safety-guards`
Evidence: `.github/workflows/build.yml:34`, `.github/workflows/ci.yml:479`, `.github/workflows/docker-image.yml:28`
Reason: the `sudo rm -rf` safety hardening is a valid follow-up, but it changes the operational contract of every reclaim step and is postponed to a dedicated hardening PR rather than being mixed into the current dependency remediation lane.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1255#discussion_r3000499435 -> 65bdf110
Disposition: FIXED
Commit: 65bdf110
Evidence: `tests/test_python_supply_chain_controls.py:215`
Reason: the Docker workflow guard now asserts that the reclaim step appears before each canonical build marker, so the regression the thread described is covered directly by the test.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1255#discussion_r3000499445 -> 65bdf110
Disposition: FIXED
Commit: 65bdf110
Evidence: `tests/test_root_npm_dependency_guards.py:56`
Reason: the lockfile guard now scans every `packages` entry ending in `/brace-expansion` and verifies both the patched minimum version and the expected npm registry source.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1255#discussion_r3000501502 -> 65bdf110
Disposition: FIXED
Commit: 65bdf110
Evidence: `tests/test_root_npm_dependency_guards.py:56`
Reason: Codex's P2 finding is addressed by validating every lockfile `brace-expansion` node instead of only the top-level package entry.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1255#pullrequestreview-4020589651 -> 65bdf110
Disposition: FIXED
Commit: 65bdf110
Evidence: `tests/test_python_supply_chain_controls.py:215`
Reason: the only actionable CodeRabbit review on the current head asked for a before-build ordering assertion, which is now present in the Docker workflow reclaim test.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1255#pullrequestreview-4020778214
Disposition: FIXED
Commit: PENDING
Evidence: `docs/roadmap/BACKLOG_LEDGER.md:7926`, `docs/roadmap/BACKLOG_LEDGER.md:7945`
Reason: the follow-up ledger entries now use canonical deterministic `PR-TBD-*` target identifiers instead of prose-only target text.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1255#discussion_r3000506224 -> 65bdf110
Disposition: FIXED
Commit: 65bdf110
Evidence: `tests/test_python_supply_chain_controls.py:215`
Reason: the thread's requested relative-order assertion was implemented using workflow-specific canonical build markers, keeping the test intent explicit and deterministic.

## Merge Readiness
- Status: in progress; local `pre-commit run --all-files` and `make verify` passed on top of commit `65bdf110`, and review-governance cleanup is being applied to the current head.
- Current fix commits:
  - `2d1fcf6f` — `fix(ci): raise lint timeout`
  - `65bdf110` — `test(security): tighten supply chain guards`
- Deferred follow-ups:
  - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-runner-disk-reclaim-centralization`
  - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-runner-disk-reclaim-safety-guards`
