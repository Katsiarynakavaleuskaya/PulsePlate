# PR #1822 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822
Branch: `codex/philosophy-epic-v2-pr5-source-corpus-index`
Scope: Philosophy Epic V2 PR-5 philosophical source corpus / interdisciplinary synthesis index.

## Summary

This PR is docs/governance/test-only. It indexes the six operator-provided
philosophy PDFs as canonical source-corpus design evidence, adds a schema,
deterministic source-corpus oracle, docs Phase1/CI routing, and regression
tests.

It does not open the semantic-cache gate and does not change Redis/GPTCache,
embeddings, vector search, provider/client, DB, OpenAPI, frontend, iOS,
`/insight`, cache read/write, serving, or runtime activation behavior.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/9883839145a4.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Dispatch manifest: `qoder_dispatch_bridge.py --packet artifacts/orchestration/task_packets/9883839145a4.json --pretty`
- Role order preserved: `agent-coordinator -> philosophy-agent -> web-research-agent -> architecture-specialist -> qa-engineer-agent -> security-auditor -> bug-hunter -> cursor-specialist-agent`
- Post-open PR: #1822, ready-for-review, not draft.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/exp-16755634fdf6.json`
- Status: accepted
- Mode: `oracle_only_governance_reviewer`
- Contribution: `oracle_review`
- Co-author: required; commit `14faf95b5` includes
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

CodeRabbit reported a review-capacity skip and did not provide actionable
findings. GitHub review threads opened after PR #1822 initial post-open pass
are mapped below. They remain unresolved until the fix commits are pushed,
CI/gates are rerun, the PR body mirror is updated, and strict disposition
checks pass.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295258830 -> cee47cad2
Disposition: FIXED
Commit: cee47cad2
Evidence: `.github/workflows/ci.yml` limits `PR5_SOURCE_CORPUS_CHANGED` to source-corpus-specific contract, packet, guard, and test surfaces.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295258831 -> cee47cad2
Disposition: FIXED
Commit: cee47cad2
Evidence: `scripts/ci/check_philosophy_source_corpus_index.py` validates per-source `source_family` and `language` with regression tests.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295258832 -> cee47cad2
Disposition: FIXED
Commit: cee47cad2
Evidence: `validate_file_contents()` skips binary and non-UTF-8 artifacts while continuing to scan text PR-5 files for local path or credential-like leaks.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295258833 -> cee47cad2
Disposition: FIXED
Commit: cee47cad2
Evidence: `repo_truth_links` and `out_of_scope_paths` are exact deterministic arrays in the source-corpus checker with regression coverage.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295275874 -> cee47cad2
Disposition: FIXED
Commit: cee47cad2
Evidence: `.github/workflows/ci.yml` excludes generic `BACKLOG_LEDGER.md` and semantic-cache roadmap edits from the PR-5 changed-path switch.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295275875 -> 412dba126
Disposition: FIXED
Commit: 412dba126
Evidence: `.github/workflows/ci.yml` excludes `scripts/ci/check_docs_phase1_gates.py` from the PR-5 changed-path switch.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295313833 -> 975f1c6ac
Disposition: FIXED
Commit: 975f1c6ac
Evidence: `sources` and `research_basis` now reject non-object rows before filtered projections can hide malformed corpus entries.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295313836 -> 975f1c6ac
Disposition: FIXED
Commit: 975f1c6ac
Evidence: `repo_truth_links` and `out_of_scope_paths` now reject non-string entries before exact canonical-list comparison.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295313837 -> 975f1c6ac
Disposition: FIXED
Commit: 975f1c6ac
Evidence: the schema guard now validates exact `repo_truth_links` and `out_of_scope_paths` array type, item type, and cardinality constraints.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295313838 -> 975f1c6ac
Disposition: FIXED
Commit: 975f1c6ac
Evidence: `source_policy` index validation now enforces every expected governance-policy constant, not only the wellness boundary.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295313840 -> 975f1c6ac
Disposition: FIXED
Commit: 975f1c6ac
Evidence: each source record now validates scalar string fields and nested string arrays, with regressions for non-string drift.

## Premortem And Oracle Closure

- Premortem skill: `pulseplate-premortem-risk-review`
- Decision: `proceed with changes`
- Frame: six months from now, PR-5 failed because source evidence looked
  canonical while leaking artifacts, weakening gate-closed semantics, or
  allowing arbitrary research anchors to masquerade as repo truth.

- FIXED: source corpus could omit one of the six PDFs. Evidence:
  `scripts/ci/check_philosophy_source_corpus_index.py` requires exact source
  IDs, grouped SHA-256 fingerprints, page counts, and total pages.
- FIXED: PDF extraction could leak local paths or credential-like URLs.
  Evidence: the source-corpus checker scans all passed PR-5 touched files.
- FIXED: source evidence could be mistaken for runtime truth. Evidence:
  all source runtime flags remain false and semantic-cache roadmap markers stay
  closed/false.
- FIXED: arbitrary external research links could pass. Evidence:
  `research_basis` is an exact allowlisted rationale-only register with access
  dates, verification status, and boundary notes.
- FIXED: object-array and exact string-array false-greens could hide malformed
  source, research, repo-truth, or no-runtime boundary entries. Evidence:
  `scripts/ci/check_philosophy_source_corpus_index.py` rejects non-object
  `sources`/`research_basis` entries and non-string `repo_truth_links` /
  `out_of_scope_paths` entries in commit `056409bde`, with regression coverage.
- FIXED: post-open review found broader schema/source-policy/scalar type drift
  false-greens. Evidence: commit `975f1c6ac` enforces exact scope-link schema
  constraints, source-policy constants, source scalar string fields, and nested
  source string arrays.
- NOT-A-BUG: no full local `make verify` was run. Evidence: operator-approved
  narrow-gate path applies; `make validate-changed`, focused gates,
  `pre-commit run --all-files`, pre-push hooks, and current-head CI remain the
  readiness path.

## Oracle Recommendation Closure

- FIXED: External research sources could be arbitrary HTTPS references. Evidence:
  `research_basis` is exact-allowlisted with id, label, URL, rail, source kind,
  access date, verification status, boundary note, and rationale-only use.
- FIXED: PubMed CBT context could imply product efficacy or therapy authority.
  Evidence: the PubMed boundary note states clinical-context caution only and
  excludes product efficacy, therapy, diagnosis, treatment, and runtime
  authority.
- FIXED: CI could miss PR-5 guard execution. Evidence: `.github/workflows/ci.yml`
  routes source-corpus-specific contract, packet, guard, and test
  changes into
  `check_philosophy_source_corpus_index.py --check --files "${ALL_CHANGED_FILES[@]}"`.
- FIXED: PR-5 CI routing could trigger on unrelated backlog/runtime PRs.
  Evidence: the PR-5 changed-path switch intentionally excludes generic
  `BACKLOG_LEDGER.md` and semantic-cache roadmap edits while direct docs Phase1
  validation still covers those files when they are touched.
- FIXED: schema drift could weaken false runtime flags. Evidence: the checker
  validates exact schema shape and every runtime flag property remains
  `const: false`.
- FIXED: leakage scan could miss non-JSON artifacts. Evidence:
  `validate_file_contents()` scans every passed PR-5 UTF-8 text artifact path
  and intentionally treats binary/non-UTF-8 artifacts as out of text-scan scope.
- FIXED: bug-hunter found array filtering false-greens after post-open review.
  Evidence: commit `056409bde` adds strict array validators and tests that reject
  non-object source / research entries and non-string repo-truth / out-of-scope
  boundary entries.
- FIXED: Codex review found schema scope-link, source-policy, and source scalar
  type gaps. Evidence: commit `975f1c6ac` closes those with validators and
  regression tests.
- FIXED: raw SHA fingerprints triggered secret-scanner false positives.
  Evidence: fingerprints use grouped SHA-256 form and `pre-commit run
  --all-files` passes.

## Validation Evidence

- `python3 scripts/ci/check_philosophy_source_corpus_index.py --check --files ...` PASS.
- `python3 scripts/ci/check_docs_phase1_gates.py --files ...` PASS.
- `python3 scripts/ci/check_semantic_cache_gate.py` PASS.
- `python3 scripts/ci/check_philosophy_gate_open_preconditions.py --check --files ...` PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` PASS.
- `$VENV_PYTHON -m pytest -q tests/test_philosophy_source_corpus_index.py tests/test_semantic_cache_gate.py tests/test_docs_phase1_gates.py tests/test_ci_workflow_pr_size_governance_contract.py` PASS.
- `$VENV_PYTHON -m bandit -q scripts/ci/check_philosophy_source_corpus_index.py scripts/ci/check_docs_phase1_gates.py` PASS.
- `DEV_PYTHON=$VENV_PYTHON VENV_PYTHON=$VENV_PYTHON make validate-changed` PASS.
- `pre-commit run --all-files` PASS.
- Pre-push hooks PASS, including mypy changed files, pip-audit, backend pytest
  pre-push, full-repo Bandit, and Docker build test.

## Deferred / Follow-ups

- PR-A2/runtime prerequisite work remains a separate line.
- Future runtime or semantic-cache work must still cite PR-2 policy oracle,
  PR-3 dry-run report, PR-4 precondition report, PR #1789 alignment-rule
  schema, and this PR-5 corpus index before any separate gate-open review.
