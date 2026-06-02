# PR #1865 - Experiment Runner Evidence Summary

## Purpose

Committed summary for the local Experiment Runner oracle result used by PR
#1865. Raw Experiment Runner JSON artifacts remain under gitignored
`artifacts/` by repo policy, so this document records the verifiable fields used
for PR governance without tracking local runtime artifacts.

## Local Result

- Path: `artifacts/orchestration/experiments/results/coaching-structured-wave-contract-oracle.json`
- SHA-256: `bdd0477de4957b03f7088b7459ab3df2103b9b67492911fcc04a01c5fa88bb70`
- Experiment ID: `exp-e3e7a64a1319`
- Status: `accepted`
- Runner mode: `oracle_only_governance_reviewer`
- Contribution kind: `oracle_review`
- Mutated paths: `[]`
- Source diff paths:
  - `docs/contracts/API_CANONICAL_MAP.md`
  - `docs/contracts/FITCHEF_STRUCTURED_COACH_CONTRACT.md`
  - `docs/contracts/PRODUCT_TIER_MAP.md`
  - `docs/insights/CBT_COACHING_PRODUCT_WAVE.md`
  - `docs/roadmap/BACKLOG_LEDGER.md`
- Attribution scope: this committed summary records the accepted oracle result
  and does not treat review-tool synthetic squash-preview SHAs as branch commits
  or proof targets.

## Oracle Commands

- `git diff --check` - PASS, return code 0.
- `python3 scripts/ci/check_docs_phase1_gates.py --files docs/roadmap/BACKLOG_LEDGER.md docs/insights/CBT_COACHING_PRODUCT_WAVE.md docs/contracts/FITCHEF_STRUCTURED_COACH_CONTRACT.md docs/contracts/API_CANONICAL_MAP.md docs/contracts/PRODUCT_TIER_MAP.md` - PASS, return code 0.
- `python3 scripts/ci/check_philosophy_source_corpus_index.py --check` - PASS, return code 0.
- `python3 scripts/ci/check_semantic_cache_gate.py` - PASS, return code 0; semantic-cache gates remained closed.

## Attribution Scope

Material Experiment Runner attribution remains governed by repo commit and
merge policy. This summary records the accepted oracle result; it does not
assert trailer compliance for non-local review-tool evaluated SHAs.

Review-tool synthetic squash-preview SHAs are not branch-history proof. The
canonical proof surface for this artifact is the committed PR branch and the
repo's merge-readiness/disposition checks.
