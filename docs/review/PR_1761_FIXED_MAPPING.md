# PR #1761 — Fixed in Commit Mapping

**PR:** docs(philosophy): add semantic-cache admission contract (gate-closed)
**Branch:** `codex/philosophy-epic-v2-pr1-admission-contract`

## Discussion Thread Pass

All premortem, code-review, and bot-review findings dispositioned below.

## Fixed in Commit Mapping

### Premortem Findings

- Validator scan scope distinguishes mention from assertion
  Disposition: FIXED
  Commit: 31c1eb98b
  Evidence: scripts/ci/check_semantic_cache_gate.py

- Contract uses exact "No Redis imports", "No GPTCache imports", "No embeddings" guard wording
  Disposition: FIXED
  Commit: 31c1eb98b
  Evidence: docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_CONTRACT.md

- Backlog entry exists; PR-0 closed by reference to PR #1744
  Disposition: FIXED
  Commit: 31c1eb98b
  Evidence: docs/roadmap/BACKLOG_LEDGER.md

- Wellness-only scope, falsifiability, risk-class machine slug wording recorded
  Disposition: FIXED
  Commit: 31c1eb98b
  Evidence: docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_CONTRACT.md

- Keeping `cb1db8b40` as schema/checker const is intentional traceability
  Disposition: NOT-A-BUG
  Evidence: Contract names coordinated update set; intentional SC-G5 merge anchor traceability

### Code Review Findings

- Missing negative tests for forbidden claims
  Disposition: FIXED
  Commit: d6d5eb173
  Evidence: tests/test_philosophy_semantic_cache_admission_contract.py

- SC-G5 SHA coupling risk
  Disposition: NOT-A-BUG
  Evidence: Contract prose documents coordination requirement

- Validator heuristic scope limitation
  Disposition: NOT-A-BUG
  Evidence: Heuristic works for current contract; manual review remains required

- Missing negative test for admission classes
  Disposition: FIXED
  Commit: d6d5eb173
  Evidence: tests/test_philosophy_semantic_cache_admission_contract.py

- Schema additionalProperties check cascading
  Disposition: NOT-A-BUG
  Evidence: Reporting all errors is intentional design

- SC-G5 reference SHA staleness risk
  Disposition: NOT-A-BUG
  Evidence: Contract explicitly documents update coordination

### Bot Review Findings (Sourcery, CodeRabbit, Cubic)

- Sourcery/CodeRabbit/Cubic: `references` type validation — no guard before membership check
  Disposition: FIXED
  Commit: this commit
  Evidence: scripts/ci/check_semantic_cache_gate.py:1388-1391 — added isinstance guard

- Sourcery: duplicated metadata between contract JSON and checker constants
  Disposition: DEFERRED
  Backlog: docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-philosophy-epic-v2-pr1-admission
  Reason: Architectural improvement; current duplication is intentional for checker independence

- Sourcery: repeated file reads in validator functions
  Disposition: DEFERRED
  Backlog: docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-philosophy-epic-v2-pr1-admission
  Reason: Performance optimization; acceptable while gate closed

- CodeRabbit: MD036 bold text used as headers in packet doc
  Disposition: FIXED
  Commit: this commit
  Evidence: docs/orchestration/PHILOSOPHY_EPIC_V2_PR1_PACKET_2026-05-17.md:33,43 — replaced with ### headers

- Cubic: array schema field coverage
  Disposition: NOT-A-BUG
  Evidence: Fix 1 (references type validation) covers the array guard; schema validation is separate layer

- Cubic: inconsistent default admission class
  Disposition: NOT-A-BUG
  Evidence: Contract defines `runtime_only` as canonical default; checker validates exact set match

- Cubic: set comparison in tests
  Disposition: DEFERRED
  Backlog: docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-philosophy-epic-v2-pr1-admission
  Reason: Tests work correctly; stylistic improvement

- Cubic: fragile string replacements in tests
  Disposition: DEFERRED
  Backlog: docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-philosophy-epic-v2-pr1-admission
  Reason: Tests work correctly; refactoring deferred

- Codex: missing sections in mapping artifact
  Disposition: FIXED
  Commit: this commit
  Evidence: docs/review/PR_1761_FIXED_MAPPING.md — rewritten to canonical format

- Codex: stale SHA reference
  Disposition: FIXED
  Commit: this commit
  Evidence: docs/review/PR_1761_FIXED_MAPPING.md — updated with current SHAs

- Codex: non-canonical mapping format
  Disposition: FIXED
  Commit: this commit
  Evidence: docs/review/PR_1761_FIXED_MAPPING.md — canonical disposition format

- Codex: bare `python` instead of `python3` in packet validation commands
  Disposition: FIXED
  Commit: this commit
  Evidence: docs/orchestration/PHILOSOPHY_EPIC_V2_PR1_PACKET_2026-05-17.md:55-58

- Codex: deferred candidates unconstrained
  Disposition: DEFERRED
  Backlog: docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-philosophy-epic-v2-pr1-admission
  Reason: Acceptable while semantic-cache gate remains closed

## Merge Readiness

- [x] PR body includes `## Discussion Thread Pass`, `### Fixed in Commit Mapping`, `## Merge Readiness`
- [x] `docs/review/PR_1761_FIXED_MAPPING.md` created with canonical format
- [x] All premortem findings dispositioned (FIXED/NOT-A-BUG/DEFERRED)
- [x] All code-review findings dispositioned
- [x] All bot-review findings dispositioned (Sourcery/CodeRabbit/Cubic)
- [ ] Canonical CI current-head parity before merge-ready claim
- [ ] No semantic-cache gate markers changed to open
- [ ] Mandatory wait-window elapsed after latest review activity
