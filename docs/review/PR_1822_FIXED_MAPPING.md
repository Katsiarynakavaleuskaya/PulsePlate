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
- Follow-up artifact:
  `artifacts/orchestration/experiments/results/exp-5dd169c24777.json`
- Follow-up status: accepted, `oracle_only_governance_reviewer`,
  `contribution_kind=oracle_review`, 3/3 oracle commands returned 0,
  `source_diff_applied=true`, and `shared_tree_untouched=true`.
- Co-author: required; commit `f2ed27c0b` includes
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.
- Latest artifact:
  `artifacts/orchestration/experiments/results/exp-241a503ee4f6.json`
- Latest status: accepted, `oracle_only_governance_reviewer`,
  `contribution_kind=oracle_review`, 2/2 runner-executable oracle commands
  returned 0, and `shared_tree_untouched=true`.
- Co-author: required; commit `3aa36f850` includes
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.
- Discipline-rail artifact:
  `artifacts/orchestration/experiments/results/exp-pr1822-discipline-rails-oracle.json`
- Discipline-rail status: accepted, `oracle_only_governance_reviewer`,
  `contribution_kind=oracle_review`, 2/2 runner-executable oracle commands
  returned 0, and `shared_tree_untouched=true`.
- Co-author: required; commit `33e57821f` includes
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.
- A3 gate-wording artifact:
  `artifacts/orchestration/experiments/results/exp-pr1822-a3-gate-wording-oracle.json`
- A3 gate-wording status: accepted, `oracle_only_governance_reviewer`,
  `contribution_kind=oracle_review`, 3/3 runner-executable oracle commands
  returned 0, and `shared_tree_untouched=true`.
- Co-author: required; commit `52216f2f9` includes
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.
- Path/encoding hardening artifact:
  `artifacts/orchestration/experiments/results/exp-pr1822-path-encoding-oracle.json`
- Path/encoding hardening status: accepted,
  `oracle_only_governance_reviewer`, `contribution_kind=oracle_review`, 3/3
  runner-executable oracle commands returned 0, and
  `shared_tree_untouched=true`.
- Co-author: required; commit `5372841b2` includes
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.
- Windows/symlink leak hardening artifact:
  `artifacts/orchestration/experiments/results/exp-pr1822-windows-symlink-leak-oracle.json`
- Windows/symlink leak hardening status: accepted,
  `oracle_only_governance_reviewer`, `contribution_kind=oracle_review`, 3/3
  runner-executable oracle commands returned 0, and
  `shared_tree_untouched=true`.
- Co-author: required; commit `fba701c10` includes
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.
- POSIX/edge-space leak hardening artifact:
  `artifacts/orchestration/experiments/results/exp-pr1822-posix-edge-space-oracle.json`
- POSIX/edge-space leak hardening status: accepted,
  `oracle_only_governance_reviewer`, `contribution_kind=oracle_review`, 3/3
  runner-executable oracle commands returned 0, and
  `shared_tree_untouched=true`.
- Co-author: required; commit `9ba654437` includes
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.
- Finditer/symlink hardening artifact:
  `artifacts/orchestration/experiments/results/exp-pr1822-finditer-symlink-oracle.json`
- Finditer/symlink hardening status: accepted,
  `oracle_only_governance_reviewer`, `contribution_kind=oracle_review`, 3/3
  runner-executable oracle commands returned 0, and
  `shared_tree_untouched=true`.
- Co-author: required; commits `a8cb56911`, `328be5c3f`, `2f56f505b`, and
  `b1f820608` include
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
Evidence: Anchors: `.github/workflows/ci.yml:285`, `.github/workflows/ci.yml:350`, `tests/test_ci_workflow_pr_size_governance_contract.py:318`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295258831 -> cee47cad2
Disposition: FIXED
Commit: cee47cad2
Evidence: `scripts/ci/check_philosophy_source_corpus_index.py` validates per-source `source_family` and `language` with regression tests.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:818`, `scripts/ci/check_philosophy_source_corpus_index.py:796`, `tests/test_philosophy_source_corpus_index.py:152`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295258832 -> cee47cad2
Disposition: FIXED
Commit: cee47cad2
Evidence: `validate_file_contents()` skips binary and non-UTF-8 artifacts while continuing to scan text PR-5 files for local path or credential-like leaks.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:984`, `scripts/ci/check_philosophy_source_corpus_index.py:993`, `tests/test_philosophy_source_corpus_index.py:860`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295258833 -> cee47cad2
Disposition: FIXED
Commit: cee47cad2
Evidence: `repo_truth_links` and `out_of_scope_paths` are exact deterministic arrays in the source-corpus checker with regression coverage.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:1148`, `scripts/ci/check_philosophy_source_corpus_index.py:1156`, `tests/test_philosophy_source_corpus_index.py:773`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295275874 -> cee47cad2
Disposition: FIXED
Commit: cee47cad2
Evidence: `.github/workflows/ci.yml` excludes generic `BACKLOG_LEDGER.md` and semantic-cache roadmap edits from the PR-5 changed-path switch.
Evidence: Anchors: `.github/workflows/ci.yml:285`, `.github/workflows/ci.yml:350`, `tests/test_ci_workflow_pr_size_governance_contract.py:318`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295275875 -> 412dba126
Disposition: FIXED
Commit: 412dba126
Evidence: `.github/workflows/ci.yml` excludes `scripts/ci/check_docs_phase1_gates.py` from the PR-5 changed-path switch.
Evidence: Anchors: `.github/workflows/ci.yml:285`, `.github/workflows/ci.yml:350`, `tests/test_ci_workflow_pr_size_governance_contract.py:327`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295313833 -> 975f1c6ac
Disposition: FIXED
Commit: 975f1c6ac
Evidence: `sources` and `research_basis` now reject non-object rows before filtered projections can hide malformed corpus entries.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:477`, `scripts/ci/check_philosophy_source_corpus_index.py:1068`, `scripts/ci/check_philosophy_source_corpus_index.py:1209`, `tests/test_philosophy_source_corpus_index.py:140`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295313836 -> 975f1c6ac
Disposition: FIXED
Commit: 975f1c6ac
Evidence: `repo_truth_links` and `out_of_scope_paths` now reject non-string entries before exact canonical-list comparison.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:487`, `scripts/ci/check_philosophy_source_corpus_index.py:1148`, `scripts/ci/check_philosophy_source_corpus_index.py:1156`, `tests/test_philosophy_source_corpus_index.py:785`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295313837 -> 975f1c6ac
Disposition: FIXED
Commit: 975f1c6ac
Evidence: the schema guard now validates exact `repo_truth_links` and `out_of_scope_paths` array type, item type, and cardinality constraints.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:952`, `docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.schema.json:326`, `tests/test_philosophy_source_corpus_index.py:645`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295313838 -> 975f1c6ac
Disposition: FIXED
Commit: 975f1c6ac
Evidence: `source_policy` index validation now enforces every expected governance-policy constant, not only the wellness boundary.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:1178`, `scripts/ci/check_philosophy_source_corpus_index.py:1187`, `tests/test_philosophy_source_corpus_index.py:833`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295313840 -> 975f1c6ac
Disposition: FIXED
Commit: 975f1c6ac
Evidence: each source record now validates scalar string fields and nested string arrays, with regressions for non-string drift.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:1093`, `scripts/ci/check_philosophy_source_corpus_index.py:1096`, `tests/test_philosophy_source_corpus_index.py:181`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295323147 -> 16cb37399
Disposition: FIXED
Commit: 16cb37399
Evidence: source metadata arrays now reject non-string `theme_families`, `discipline_rails`, and `linked_repo_anchors` entries with dedicated regressions.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:1096`, `tests/test_philosophy_source_corpus_index.py:194`, `tests/test_philosophy_source_corpus_index.py:248`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295323148 -> 16cb37399
Disposition: FIXED
Commit: 16cb37399
Evidence: the schema guard now validates source-array `items.type`, `minItems`, and discipline enum constraints for source metadata arrays.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:823`, `docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.schema.json:199`, `tests/test_philosophy_source_corpus_index.py:660`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295323149 -> 16cb37399
Disposition: FIXED
Commit: 16cb37399
Evidence: the schema guard now validates research-basis nested field types plus URI/date formats for URL and access-date metadata.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:937`, `scripts/ci/check_philosophy_source_corpus_index.py:942`, `scripts/ci/check_philosophy_source_corpus_index.py:947`, `tests/test_philosophy_source_corpus_index.py:684`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295323151 -> 16cb37399
Disposition: FIXED
Commit: 16cb37399
Evidence: touched-file leakage scanning now decodes UTF-16/UTF-32 text artifacts before falling back to binary skip, with UTF-16 leak regression coverage.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:984`, `scripts/ci/check_philosophy_source_corpus_index.py:1006`, `tests/test_philosophy_source_corpus_index.py:873`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295342438 -> 79823c296
Disposition: FIXED
Commit: 79823c296
Evidence: the schema guard now enforces source scalar schema types, including `title.type == string`, with focused regression coverage.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:777`, `docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.schema.json:160`, `tests/test_philosophy_source_corpus_index.py:432`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295342439 -> 79823c296
Disposition: FIXED
Commit: 79823c296
Evidence: the schema guard now requires `runtime_flags.type == object`, with focused regression coverage.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:852`, `docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.schema.json:233`, `tests/test_philosophy_source_corpus_index.py:454`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295342441 -> 79823c296
Disposition: FIXED
Commit: 79823c296
Evidence: the schema guard now enforces top-level `sources.type == array` and `sources.items.type == object`, with focused regression coverage.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:750`, `scripts/ci/check_philosophy_source_corpus_index.py:760`, `docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.schema.json:132`, `tests/test_philosophy_source_corpus_index.py:419`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295342442 -> 79823c296
Disposition: FIXED
Commit: 79823c296
Evidence: runtime flag schema properties now require `type: boolean` plus `const: false`, with focused regression coverage.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:871`, `docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.schema.json:245`, `tests/test_philosophy_source_corpus_index.py:473`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295432296 -> c37adb4ec
Disposition: FIXED
Commit: c37adb4ec
Evidence: `research_basis` now requires `type: array`, `items.type == object`, and `use.type == string`, with focused regression coverage.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:890`, `scripts/ci/check_philosophy_source_corpus_index.py:900`, `scripts/ci/check_philosophy_source_corpus_index.py:920`, `tests/test_philosophy_source_corpus_index.py:582`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295432297 -> c37adb4ec
Disposition: FIXED
Commit: c37adb4ec
Evidence: `source_policy` now requires `type: object` and string-typed policy constants, with focused regression coverage.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:721`, `scripts/ci/check_philosophy_source_corpus_index.py:746`, `docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.schema.json:86`, `tests/test_philosophy_source_corpus_index.py:549`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3295432300 -> c37adb4ec
Disposition: FIXED
Commit: c37adb4ec
Evidence: `semantic_cache_markers` now requires `type: object` and boolean-typed marker constants, with focused regression coverage.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:688`, `scripts/ci/check_philosophy_source_corpus_index.py:705`, `docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.schema.json:58`, `tests/test_philosophy_source_corpus_index.py:515`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3297211726 -> adcfe6c03
Disposition: FIXED
Commit: adcfe6c03
Evidence: every Fixed in Commit Mapping entry now keeps its explicit commit binding and adds concrete file:line evidence anchors.
Evidence: Anchors: `docs/review/PR_1822_FIXED_MAPPING.md:49`, `docs/review/PR_1822_FIXED_MAPPING.md:112`, `docs/review/PR_1822_FIXED_MAPPING.md:175`, `docs/review/PR_1822_FIXED_MAPPING.md:180`, `docs/review/PR_1822_FIXED_MAPPING.md:182`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#pullrequestreview-4355582770 -> 8af44cc69
Disposition: FIXED
Commit: 8af44cc69
Evidence: the CodeRabbit review-level request for file:line anchors is covered by parser-valid `Evidence: Anchors:` lines across every FIXED disposition.
Evidence: Anchors: `docs/review/PR_1822_FIXED_MAPPING.md:52`, `docs/review/PR_1822_FIXED_MAPPING.md:112`, `docs/review/PR_1822_FIXED_MAPPING.md:184`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#pullrequestreview-4355944032 -> 004a6ef31
Disposition: FIXED
Commit: 004a6ef31
Evidence: the CodeRabbit review-level request for type-strict JSON Schema numeric keyword checks is covered by exact integer validation for `minimum` and `minLength`.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:815`, `scripts/ci/check_philosophy_source_corpus_index.py:818`, `scripts/ci/check_philosophy_source_corpus_index.py:839`, `tests/test_philosophy_source_corpus_index.py:511`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3297399786 -> 5f3142b14
Disposition: FIXED
Commit: 5f3142b14
Evidence: aggregate counts now require exact JSON integer values, so `6.0`, `102.0`, and boolean/numeric drift cannot pass by Python equality.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:531`, `scripts/ci/check_philosophy_source_corpus_index.py:1154`, `scripts/ci/check_philosophy_source_corpus_index.py:1157`, `tests/test_philosophy_source_corpus_index.py:125`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3297399789 -> 5f3142b14
Disposition: FIXED
Commit: 5f3142b14
Evidence: touched-artifact text scanning now attempts UTF-32 before UTF-16 and has a UTF-32 regression that detects local-path leakage.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:994`, `scripts/ci/check_philosophy_source_corpus_index.py:1016`, `tests/test_philosophy_source_corpus_index.py:923`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3297399794 -> 5f3142b14
Disposition: FIXED
Commit: 5f3142b14
Evidence: schema `const` comparisons are type-aware, so boolean-to-numeric and integer-to-float drift cannot pass by Python equality.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:535`, `scripts/ci/check_philosophy_source_corpus_index.py:558`, `tests/test_philosophy_source_corpus_index.py:430`, `tests/test_philosophy_source_corpus_index.py:443`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3297445015 -> 2f5ef5169
Disposition: FIXED
Commit: 2f5ef5169
Evidence: the schema oracle now validates the canonical JSON Schema draft URI and rejects metaschema drift.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:651`, `tests/test_philosophy_source_corpus_index.py:628`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3297445019 -> 2f5ef5169
Disposition: FIXED
Commit: 2f5ef5169
Evidence: the schema oracle now validates `page_count.minimum == 1` and has a regression for deleted minimum drift.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:806`, `scripts/ci/check_philosophy_source_corpus_index.py:810`, `tests/test_philosophy_source_corpus_index.py:469`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3297445021 -> 2f5ef5169
Disposition: FIXED
Commit: 2f5ef5169
Evidence: the schema oracle now validates source scalar pattern and minimum-length constraints for source identifiers, hashes, titles, filenames, summaries, and handoff text.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:811`, `scripts/ci/check_philosophy_source_corpus_index.py:820`, `tests/test_philosophy_source_corpus_index.py:490`, `tests/test_philosophy_source_corpus_index.py:517`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3297445025
Disposition: NOT-A-BUG
Evidence: duplicate current-head finding; the branch already enforces type-aware schema `const` equality through commit `5f3142b14`, and the same class is mapped above under `discussion_r3297399794`.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:535`, `scripts/ci/check_philosophy_source_corpus_index.py:558`, `tests/test_philosophy_source_corpus_index.py:430`, `tests/test_philosophy_source_corpus_index.py:443`.
Reason: no additional code change is needed because the current PR head already rejects boolean/numeric `const` drift.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3297445030
Disposition: NOT-A-BUG
Evidence: duplicate current-head finding; the branch already enforces exact JSON integer aggregate counts through commit `5f3142b14`, and the same class is mapped above under `discussion_r3297399786`.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:531`, `scripts/ci/check_philosophy_source_corpus_index.py:1185`, `scripts/ci/check_philosophy_source_corpus_index.py:1188`, `tests/test_philosophy_source_corpus_index.py:125`.
Reason: no additional code change is needed because the current PR head already rejects `6.0` / `102.0` aggregate count drift.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3297525346 -> 004a6ef31
Disposition: FIXED
Commit: 004a6ef31
Evidence: schema numeric keyword checks now require exact JSON integers for `minimum` and `minLength`, closing `True == 1` and `40.0 == 40` false-greens.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:815`, `scripts/ci/check_philosophy_source_corpus_index.py:818`, `scripts/ci/check_philosophy_source_corpus_index.py:839`, `tests/test_philosophy_source_corpus_index.py:511`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3297529356 -> 004a6ef31
Disposition: FIXED
Commit: 004a6ef31
Evidence: touched-artifact decoding now switches to UTF-32/UTF-16 first when NUL bytes indicate wide text and rejects decoded text with embedded NULs before scanning.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:1034`, `scripts/ci/check_philosophy_source_corpus_index.py:1040`, `scripts/ci/check_philosophy_source_corpus_index.py:1048`, `tests/test_philosophy_source_corpus_index.py:1059`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3297529364 -> 004a6ef31
Disposition: FIXED
Commit: 004a6ef31
Evidence: source-row validation now mirrors source text minimum-length constraints for title, sanitized filename, summary, and future handoff text.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:98`, `scripts/ci/check_philosophy_source_corpus_index.py:1152`, `scripts/ci/check_philosophy_source_corpus_index.py:1156`, `tests/test_philosophy_source_corpus_index.py:205`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3297595474 -> 7b7eef081
Disposition: FIXED
Commit: 7b7eef081
Evidence: source-corpus validation now scans the semantic-cache roadmap and gate-open precondition report text for local path and credential-like leakage, with focused regressions for both companion inputs.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:1403`, `scripts/ci/check_philosophy_source_corpus_index.py:1410`, `tests/test_philosophy_source_corpus_index.py:925`, `tests/test_philosophy_source_corpus_index.py:937`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3297595482
Disposition: NOT-A-BUG
Evidence: current-head `_decode_text_artifact()` detects NUL-bearing wide text before UTF-8 fallback, attempts UTF-32/UTF-16 first, rejects decoded text with embedded NULs, and the BOM-less UTF-16LE regression detects the constructed local-path leak.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:1034`, `scripts/ci/check_philosophy_source_corpus_index.py:1036`, `scripts/ci/check_philosophy_source_corpus_index.py:1043`, `tests/test_philosophy_source_corpus_index.py:1087`.
Reason: no additional code change is needed because the composed BOM-less UTF-16LE local-path sample decodes to plain text at current head and is scanned by the existing regression.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3297654612 -> 21fef7eac
Disposition: FIXED
Commit: 21fef7eac
Evidence: touched-artifact decoding now includes explicit BOM-less UTF-32BE/LE candidates and scans every valid NUL-free decoding candidate instead of returning after the first ambiguous decode.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:1093`, `scripts/ci/check_philosophy_source_corpus_index.py:1104`, `scripts/ci/check_philosophy_source_corpus_index.py:1114`, `tests/test_philosophy_source_corpus_index.py:1165`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3297654616 -> 21fef7eac
Disposition: FIXED
Commit: 21fef7eac
Evidence: touched-artifact decoding now includes explicit BOM-less UTF-16BE/LE candidates and scans every valid NUL-free decoding candidate to prevent wrong-endian false-greens.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:1093`, `scripts/ci/check_philosophy_source_corpus_index.py:1097`, `scripts/ci/check_philosophy_source_corpus_index.py:1114`, `tests/test_philosophy_source_corpus_index.py:1139`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3297654621 -> 21fef7eac
Disposition: FIXED
Commit: 21fef7eac
Evidence: `research_basis.minItems` and `research_basis.maxItems` now use the exact JSON-integer schema keyword helper, with regression coverage for float drift.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:584`, `scripts/ci/check_philosophy_source_corpus_index.py:975`, `scripts/ci/check_philosophy_source_corpus_index.py:983`, `tests/test_philosophy_source_corpus_index.py:819`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3297654625 -> 21fef7eac
Disposition: FIXED
Commit: 21fef7eac
Evidence: `sources.minItems` and `sources.maxItems` now use the exact JSON-integer schema keyword helper, with regression coverage for float drift.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:584`, `scripts/ci/check_philosophy_source_corpus_index.py:787`, `scripts/ci/check_philosophy_source_corpus_index.py:795`, `tests/test_philosophy_source_corpus_index.py:832`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3297654627 -> 21fef7eac
Disposition: FIXED
Commit: 21fef7eac
Evidence: scope-link arrays now use the exact JSON-integer schema keyword helper for `repo_truth_links` and `out_of_scope_paths` bounds, with regression coverage for float drift.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:584`, `scripts/ci/check_philosophy_source_corpus_index.py:1052`, `scripts/ci/check_philosophy_source_corpus_index.py:1060`, `tests/test_philosophy_source_corpus_index.py:940`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3297736953 -> 3b16c3e11
Disposition: FIXED
Commit: 3b16c3e11
Evidence: the intermediate routing fix ensured PR-5 oracle coverage was represented in docs Phase1 workflow tests; current-head follow-up `f2ed27c0b` supersedes the broad docs-gate trigger by keeping PR-5 activation limited to source-corpus-owned files and preserving concrete workflow-contract coverage.
Evidence: Anchors: `.github/workflows/ci.yml:284`, `.github/workflows/ci.yml:289`, `tests/test_ci_workflow_pr_size_governance_contract.py:318`, `tests/test_ci_workflow_pr_size_governance_contract.py:344`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3297736959 -> 3b16c3e11
Disposition: FIXED
Commit: 3b16c3e11
Evidence: leakage detection errors now redact the matched value while preserving the fail-closed signal, with regressions proving local-path and credential-like payloads are not echoed.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:1076`, `scripts/ci/check_philosophy_source_corpus_index.py:1082`, `tests/test_philosophy_source_corpus_index.py:341`, `tests/test_philosophy_source_corpus_index.py:356`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3298347737 -> f2ed27c0b
Disposition: FIXED
Commit: f2ed27c0b
Evidence: PR-5 CI activation is now limited to source-corpus-owned files only; `scripts/ci/check_docs_phase1_gates.py` no longer triggers the PR-5 oracle path.
Evidence: Anchors: `.github/workflows/ci.yml:284`, `.github/workflows/ci.yml:285`, `.github/workflows/ci.yml:289`, `tests/test_ci_workflow_pr_size_governance_contract.py:339`, `tests/test_ci_workflow_pr_size_governance_contract.py:344`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3298347743 -> f2ed27c0b
Disposition: FIXED
Commit: f2ed27c0b
Evidence: the workflow contract test now extracts the actual PR-5 `case "$path"` block before asserting source-corpus trigger inclusion and docs Phase1 trigger exclusion, closing the prior broad-section false-green.
Evidence: Anchors: `tests/test_ci_workflow_pr_size_governance_contract.py:326`, `tests/test_ci_workflow_pr_size_governance_contract.py:331`, `tests/test_ci_workflow_pr_size_governance_contract.py:332`, `tests/test_ci_workflow_pr_size_governance_contract.py:344`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3299252790 -> 33e57821f
Disposition: FIXED
Commit: 33e57821f
Evidence: source-corpus validation now rejects `discipline_rails` values outside the canonical `EXPECTED_DISCIPLINE_RAILS` enum, closing the `totally_invalid_rail` false-green.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:113`, `scripts/ci/check_philosophy_source_corpus_index.py:1266`, `scripts/ci/check_philosophy_source_corpus_index.py:1273`, `tests/test_philosophy_source_corpus_index.py:315`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3299452726 -> 5372841b2
Disposition: FIXED
Commit: 5372841b2
Evidence: Docs Phase1 workflow now trusts the pull-request merge-ref parent `HEAD^1` only when `HEAD^2` exists; otherwise it falls back to the PR base SHA.
Evidence: Anchors: `.github/workflows/ci.yml:237`, `.github/workflows/ci.yml:245`, `tests/test_ci_workflow_pr_size_governance_contract.py:295`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3299452728 -> 5372841b2
Disposition: FIXED
Commit: 5372841b2
Evidence: touched-path normalization now preserves literal POSIX backslashes instead of rewriting them to slashes, while still rejecting Windows drive paths as outside-repo input.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:617`, `scripts/ci/check_philosophy_source_corpus_index.py:621`, `tests/test_philosophy_source_corpus_index.py:1123`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3299452730 -> 5372841b2
Disposition: FIXED
Commit: 5372841b2
Evidence: touched-artifact text scanning now attempts CP1251 and Windows-1252 fallback decoding after Unicode candidates so common non-UTF text artifacts are scanned for local-path and credential-like leaks.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:421`, `scripts/ci/check_philosophy_source_corpus_index.py:1092`, `tests/test_philosophy_source_corpus_index.py:1150`, `tests/test_philosophy_source_corpus_index.py:1165`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3299600291 -> fba701c10
Disposition: FIXED
Commit: fba701c10
Evidence: touched-artifact leakage scanning now rejects Windows drive-root local paths on any drive, including non-C user directories.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:411`, `tests/test_philosophy_source_corpus_index.py:1137`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3299600292 -> fba701c10
Disposition: FIXED
Commit: fba701c10
Evidence: touched-artifact leakage scanning now rejects non-user Windows drive-root paths and UNC share paths without allowing raw leak strings in test source.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:411`, `scripts/ci/check_philosophy_source_corpus_index.py:412`, `tests/test_philosophy_source_corpus_index.py:1154`, `tests/test_philosophy_source_corpus_index.py:1168`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3299600296 -> fba701c10
Disposition: FIXED
Commit: fba701c10
Evidence: touched-file scanning now validates symlink targets before content reads, including broken symlinks and targets that escape the repository root.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:1164`, `scripts/ci/check_philosophy_source_corpus_index.py:1168`, `scripts/ci/check_philosophy_source_corpus_index.py:1171`, `tests/test_philosophy_source_corpus_index.py:1185`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3299774947 -> 9ba654437
Disposition: FIXED
Commit: 9ba654437
Evidence: touched-artifact leakage scanning now rejects generic POSIX absolute local-path fixtures, while keeping the repo-neutral Python shebang allowed.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:410`, `scripts/ci/check_philosophy_source_corpus_index.py:1099`, `tests/test_philosophy_source_corpus_index.py:1123`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3299774948 -> 9ba654437
Disposition: FIXED
Commit: 9ba654437
Evidence: touched-path normalization now preserves the exact raw git filename, including leading and trailing spaces, so content scanning reads the actual touched artifact.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:632`, `tests/test_philosophy_source_corpus_index.py:1136`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3299923104 -> a8cb56911
Disposition: FIXED
Commit: a8cb56911
Evidence: source-corpus leakage scanning now iterates every match for each leakage pattern, so an allowed `/usr/bin/env` occurrence cannot hide a later forbidden absolute local path.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:1101`, `scripts/ci/check_philosophy_source_corpus_index.py:1102`, `tests/test_philosophy_source_corpus_index.py:1166`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3299923108 -> a8cb56911
Disposition: FIXED
Commit: a8cb56911
Evidence: source-corpus touched-file scanning now stops content reads after detecting an absolute or repository-escaping symlink target, preserving fail-closed symlink validation without reading outside-repo content.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:1177`, `scripts/ci/check_philosophy_source_corpus_index.py:1192`, `tests/test_philosophy_source_corpus_index.py:1257`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3299923099 -> 328be5c3f
Disposition: FIXED
Commit: 328be5c3f
Evidence: the premortem and oracle closure FIXED bullets now use explicit `FIXED (Commit: <sha>)` wording with `Evidence: Anchors:` file-line tuples for the affected current-head closure entries.
Evidence: Anchors: `docs/review/PR_1822_FIXED_MAPPING.md:534`, `docs/review/PR_1822_FIXED_MAPPING.md:557`, `docs/review/PR_1822_FIXED_MAPPING.md:650`, `docs/review/PR_1822_FIXED_MAPPING.md:670`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#pullrequestreview-4358738987 -> 328be5c3f
Disposition: FIXED
Commit: 328be5c3f
Evidence: the CodeRabbit review-level request is closed by the same mapping-format hardening plus the code fixes mapped to `a8cb56911` for the two scanner bypass findings.
Evidence: Anchors: `docs/review/PR_1822_FIXED_MAPPING.md:444`, `docs/review/PR_1822_FIXED_MAPPING.md:450`, `docs/review/PR_1822_FIXED_MAPPING.md:456`, `scripts/ci/check_philosophy_source_corpus_index.py:1101`, `scripts/ci/check_philosophy_source_corpus_index.py:1177`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3299928701 -> b1f820608
Disposition: FIXED
Commit: b1f820608
Evidence: the source-corpus leakage scanner now iterates every regex match before applying allowlist skips, preserving detection after an allowed `/usr/bin/env` or route literal.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:1117`, `scripts/ci/check_philosophy_source_corpus_index.py:1131`, `tests/test_philosophy_source_corpus_index.py:1254`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3299928706 -> b1f820608
Disposition: FIXED
Commit: b1f820608
Evidence: route literals are now classified through a route-specific helper instead of the generic local-path prefix allowlist, with non-file route regression coverage.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:1115`, `scripts/ci/check_philosophy_source_corpus_index.py:1122`, `tests/test_philosophy_source_corpus_index.py:1166`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3299928710 -> b1f820608
Disposition: FIXED
Commit: b1f820608
Evidence: credential field names no longer count as leaks unless paired with a value-shaped assignment, with allow/reject regressions for identifier names and values.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:432`, `tests/test_philosophy_source_corpus_index.py:1222`, `tests/test_philosophy_source_corpus_index.py:1238`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3299966762 -> b1f820608
Disposition: FIXED
Commit: b1f820608
Evidence: all-match scanning now catches the forbidden opt-work PDF fixture after earlier allowlisted route or shebang literals.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:1117`, `scripts/ci/check_philosophy_source_corpus_index.py:1131`, `tests/test_philosophy_source_corpus_index.py:1254`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3299966764 -> b1f820608
Disposition: FIXED
Commit: b1f820608
Evidence: non-file route literals such as `/health/db` are accepted by the route helper without treating them as local filesystem paths.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:447`, `scripts/ci/check_philosophy_source_corpus_index.py:1122`, `tests/test_philosophy_source_corpus_index.py:1166`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3299966765 -> b1f820608
Disposition: FIXED
Commit: b1f820608
Evidence: file-like API PDF values are no longer blanket-allowlisted as routes and are rejected as local-path leakage.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:1122`, `scripts/ci/check_philosophy_source_corpus_index.py:1125`, `tests/test_philosophy_source_corpus_index.py:1182`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3299966766
Disposition: NOT-A-BUG
Evidence: PR-5 intentionally excludes `scripts/ci/check_docs_phase1_gates.py` from the source-corpus trigger so shared docs-gate maintenance does not force unrelated PRs through PR-5 source-corpus runtime-path bans.
Evidence: Anchors: `.github/workflows/ci.yml:288`, `.github/workflows/ci.yml:292`, `tests/test_ci_workflow_pr_size_governance_contract.py:348`, `tests/test_ci_workflow_pr_size_governance_contract.py:351`.
Reason: this matches the operator-approved PR #1822 finish plan; direct docs Phase1 validation remains responsible for shared gate-script changes.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#discussion_r3300014896 -> f7cb6a423
Disposition: FIXED
Commit: f7cb6a423
Evidence: `~` allowlisting now applies only to path-shaped matches (`~/<path>`), which blocks `~sk-...` token leaks and still allows `~/.cache/...` path-like entries.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:1117`, `scripts/ci/check_philosophy_source_corpus_index.py:1119`, `tests/test_philosophy_source_corpus_index.py:1222`, `tests/test_philosophy_source_corpus_index.py:1235`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1822#pullrequestreview-4358844503 -> f7cb6a423
Disposition: FIXED
Commit: f7cb6a423
Evidence: the review-level CodeRabbit request is covered by the same tilde path-only allowlist fix in `f7cb6a423`; token-like values such as `~sk-...` are now rejected while path-shaped home-dir forms are still allowed.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:1117`, `scripts/ci/check_philosophy_source_corpus_index.py:1119`, `tests/test_philosophy_source_corpus_index.py:1222`, `tests/test_philosophy_source_corpus_index.py:1235`.

## CI Failure Closure

- CI: `test-main (3.11, 60)`, run `26413427211`, job `77752795738`
Disposition: FIXED
Commit: 52216f2f9
Evidence: current-head CI failed after `origin/main` introduced the A3 bounded-context closeout guard and the PR-5 semantic-cache roadmap note let the guard reconstruct `OpenAPI does not iOS changes` as a forbidden positive scope claim.
Evidence: `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md` now keeps PR-5 outside semantic-cache runtime admission and says cache reads/writes, serving, providers, `/insight`, Redis, GPTCache, embeddings, vector search, DB, OpenAPI, frontend, and iOS remain out of scope.
Evidence: Anchors: `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md:103`, `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md:104`, `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md:106`.

- CI: `Docs Phase1 gates`, run `26419224340`, job `77770254681`
Disposition: FIXED
Commit: 3a4d09e6e
Evidence: source-corpus leakage scanning now preserves generic POSIX absolute local-path detection while allowing repo-neutral API route and null-device literals that are not local environment leaks.
Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:434`, `scripts/ci/check_philosophy_source_corpus_index.py:1106`, `tests/test_philosophy_source_corpus_index.py:1156`.

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
- FIXED: post-open review found remaining schema nested-array, research-basis
  schema, and UTF-16 leakage-scan gaps. Evidence: commit `16cb37399` validates
  source metadata array schema constraints, research metadata types/formats, and
  scans UTF-16/UTF-32 text artifacts.
- FIXED: post-open review found final schema-type false-greens for source
  arrays, source scalar fields, runtime flag object shape, and runtime flag
  boolean properties. Evidence: commit `79823c296` closes these with schema
  validation and regression tests.
- FIXED: post-open review found remaining section/const schema-type false-greens
  for `research_basis`, `source_policy`, and `semantic_cache_markers`. Evidence:
  commit `c37adb4ec` generalizes the type contract across top-level constants,
  section objects/arrays, section constants, and focused regressions.
- FIXED: current-head review found numeric/boolean equality false-greens and
  UTF decoding order leakage risk. Evidence: commit `5f3142b14` adds exact
  JSON-integer checks, type-aware schema `const` comparison, UTF-32-before-UTF-16
  scanning, and focused regressions.
- FIXED: current-head review found schema-oracle constraint drift for the
  canonical `$schema` URI, `page_count.minimum`, and source scalar
  pattern/minimum-length constraints. Evidence: commit `2f5ef5169` validates
  those schema constraints and adds focused regressions.
- NOT-A-BUG: repeated integer/type-aware review comments after `5f3142b14`
  describe classes already enforced at current head. Evidence: those duplicate
  threads are mapped as NOT-A-BUG with code/test anchors.
- FIXED (Commit: 004a6ef31): current-head review found type-loose schema numeric keywords,
  BOM-less UTF-16 leakage-scan bypass, and source-row text constraint drift.
  Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:815`,
  `scripts/ci/check_philosophy_source_corpus_index.py:1034`,
  `scripts/ci/check_philosophy_source_corpus_index.py:1152`,
  `tests/test_philosophy_source_corpus_index.py:511`.
- FIXED (Commit: 7b7eef081): current-head review found companion roadmap/report
  leakage-scan gaps. Evidence: Anchors:
  `scripts/ci/check_philosophy_source_corpus_index.py:1403`,
  `scripts/ci/check_philosophy_source_corpus_index.py:1410`,
  `tests/test_philosophy_source_corpus_index.py:925`,
  `tests/test_philosophy_source_corpus_index.py:937`.
- NOT-A-BUG: repeated UTF-16/UTF-32 decoding review comment after `004a6ef31`
  describes behavior already enforced at current head. Evidence: current
  `_decode_text_artifact()` returns plain text for the composed BOM-less
  UTF-16LE local-path sample and the regression test scans that artifact class.
- FIXED (Commit: 21fef7eac): latest current-head review found BOM-less
  big-endian UTF-16/UTF-32
  leakage bypasses and float cardinality false-greens for schema bounds.
  Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:1093`,
  `scripts/ci/check_philosophy_source_corpus_index.py:1104`,
  `scripts/ci/check_philosophy_source_corpus_index.py:584`,
  `tests/test_philosophy_source_corpus_index.py:1165`.
- FIXED (Commit: f2ed27c0b): latest current-head review found PR-5 CI trigger
  and leakage error hygiene gaps. Evidence: Anchors: `.github/workflows/ci.yml:284`,
  `.github/workflows/ci.yml:289`,
  `tests/test_ci_workflow_pr_size_governance_contract.py:339`,
  `scripts/ci/check_philosophy_source_corpus_index.py:1076`.
- FIXED (Commit: 3aa36f850): current-head CI found Docs Phase1 used a stale
  `github.event.pull_request.base.sha` after `main` advanced, pulling unrelated
  Experiment Runner Slack files into the PR-5 source-corpus touched-file scan.
  Evidence: Anchors: `.github/workflows/ci.yml:237`,
  `.github/workflows/ci.yml:245`,
  `tests/test_ci_workflow_pr_size_governance_contract.py:295`.
- FIXED (Commit: 33e57821f): current-head review found discipline rail enum
  false-greens. Evidence: Anchors:
  `scripts/ci/check_philosophy_source_corpus_index.py:113`,
  `scripts/ci/check_philosophy_source_corpus_index.py:1266`,
  `tests/test_philosophy_source_corpus_index.py:315`.
- FIXED (Commit: 52216f2f9): current-head CI after `origin/main` advanced found
  the PR-5 roadmap wording tripped the new A3 bounded-context guard.
  Evidence: Anchors: `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md:103`,
  `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md:104`,
  `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md:106`.
- FIXED (Commit: 5372841b2): current-head review found Docs Phase1 could trust
  `HEAD^1` even when the checkout was not a pull-request merge commit.
  Evidence: Anchors: `.github/workflows/ci.yml:237`,
  `.github/workflows/ci.yml:245`,
  `tests/test_ci_workflow_pr_size_governance_contract.py:295`.
- FIXED (Commit: 5372841b2): current-head review found touched-path normalization
  could rewrite literal POSIX backslashes and skip a real file.
  Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:617`,
  `scripts/ci/check_philosophy_source_corpus_index.py:621`,
  `tests/test_philosophy_source_corpus_index.py:1123`.
- FIXED (Commit: 5372841b2): current-head review found CP1251/Windows-1252 text
  artifacts could be skipped before content leakage scanning.
  Evidence: Anchors: `scripts/ci/check_philosophy_source_corpus_index.py:421`,
  `scripts/ci/check_philosophy_source_corpus_index.py:1092`,
  `tests/test_philosophy_source_corpus_index.py:1150`.
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
  routes only source-corpus-owned contract, packet, guard, and test
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
- FIXED: Codex review found source metadata array, research-basis schema, and
  UTF-16 leakage-scan gaps. Evidence: commit `16cb37399` closes those with
  validators and regression tests.
- FIXED: QA and bug-hunter final pass found four remaining schema-type
  false-greens. Evidence: commit `79823c296` enforces `sources.type`,
  `sources.items.type`, source scalar property types, `runtime_flags.type`, and
  runtime flag `type: boolean` declarations with targeted tests.
- FIXED: the latest Codex review found section-level schema-type drift for
  `research_basis`, `source_policy`, and `semantic_cache_markers`. Evidence:
  commit `c37adb4ec` enforces these section types plus string/boolean typed
  constants across the source-corpus schema oracle.
- FIXED: the current-head Codex review found aggregate count type drift,
  UTF-32 leakage-scan ordering, and Python equality false-greens in schema
  `const` checks. Evidence: commit `5f3142b14` closes all three classes in the
  checker and regression suite.
- FIXED: the current-head Codex review found missing schema-oracle assertions
  for `$schema`, `page_count.minimum`, and source scalar pattern/minLength
  constraints. Evidence: commit `2f5ef5169` closes these with schema checks and
  regressions.
- NOT-A-BUG: repeated current-head Codex comments for the already-fixed
  integer/type-aware classes require no extra code. Evidence: `5f3142b14` and
  the focused tests already reject those exact drifts.
- FIXED (Commit: 004a6ef31): current-head CodeRabbit/Codex review found remaining
  oracle comparison and decoding gaps. Evidence: Anchors:
  `scripts/ci/check_philosophy_source_corpus_index.py:815`,
  `scripts/ci/check_philosophy_source_corpus_index.py:1034`,
  `tests/test_philosophy_source_corpus_index.py:511`.
- FIXED (Commit: 7b7eef081): latest Codex review found roadmap/report companion
  text was not scanned for local path or credential leakage. Evidence: Anchors:
  `scripts/ci/check_philosophy_source_corpus_index.py:1403`,
  `scripts/ci/check_philosophy_source_corpus_index.py:1410`,
  `tests/test_philosophy_source_corpus_index.py:925`.
- NOT-A-BUG: latest repeated decoding comment is already covered by current-head
  wide-text decoding. Evidence: `_decode_text_artifact()` decodes the BOM-less
  UTF-16LE sample into plain text and the existing regression catches its leak.
- FIXED (Commit: 21fef7eac): latest Codex review found BOM-less
  UTF-16BE/UTF-32BE decode gaps and
  float cardinality false-greens for `sources`, `research_basis`, and scope-link
  schema bounds. Evidence: Anchors:
  `scripts/ci/check_philosophy_source_corpus_index.py:1093`,
  `scripts/ci/check_philosophy_source_corpus_index.py:584`,
  `tests/test_philosophy_source_corpus_index.py:1165`.
- FIXED (Commit: f2ed27c0b): latest Codex review found source-corpus oracle
  trigger and leakage error hygiene gaps. Evidence: Anchors:
  `.github/workflows/ci.yml:284`, `.github/workflows/ci.yml:289`,
  `tests/test_ci_workflow_pr_size_governance_contract.py:339`,
  `scripts/ci/check_philosophy_source_corpus_index.py:1076`.
- FIXED (Commit: f2ed27c0b): follow-up Codex review found the PR-5 CI activation class was
  over-broad and the workflow test could false-green by checking the full docs
  Phase1 section instead of the actual PR-5 case block. Evidence: Anchors:
  `.github/workflows/ci.yml:284`, `.github/workflows/ci.yml:285`,
  `tests/test_ci_workflow_pr_size_governance_contract.py:326`.
- FIXED (Commit: 3aa36f850): current-head Docs Phase1 CI still failed after `main` advanced because
  changed-file detection used the stale PR event base SHA instead of the
  current merge-ref parent. Evidence: Anchors: `.github/workflows/ci.yml:237`,
  `.github/workflows/ci.yml:245`,
  `tests/test_ci_workflow_pr_size_governance_contract.py:295`.
- FIXED (Commit: 33e57821f): current-head Codex review found source
  `discipline_rails` accepted non-enum values. Evidence: Anchors:
  `scripts/ci/check_philosophy_source_corpus_index.py:113`,
  `scripts/ci/check_philosophy_source_corpus_index.py:1266`,
  `tests/test_philosophy_source_corpus_index.py:315`.
- FIXED (Commit: 52216f2f9): current-head A3 closeout guard found forbidden reconstructed
  OpenAPI/iOS scope wording in the PR-5 semantic-cache roadmap note. Evidence:
  Anchors: `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md:103`,
  `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md:104`,
  `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md:106`.
- FIXED (Commit: 5372841b2): latest Codex review found workflow base-ref,
  touched-path normalization, and non-UTF text artifact scan gaps.
  Evidence: Anchors: `.github/workflows/ci.yml:237`,
  `scripts/ci/check_philosophy_source_corpus_index.py:617`,
  `tests/test_philosophy_source_corpus_index.py:1123`.
- FIXED (Commit: fba701c10): latest Codex review found Windows absolute
  local-path and symlink target scan gaps. Evidence: Anchors:
  `scripts/ci/check_philosophy_source_corpus_index.py:411`,
  `scripts/ci/check_philosophy_source_corpus_index.py:1164`,
  `tests/test_philosophy_source_corpus_index.py:1185`.
- FIXED (Commit: 9ba654437): latest Codex review found remaining generic POSIX
  local-path and exact touched-filename normalization gaps. Evidence: Anchors:
  `scripts/ci/check_philosophy_source_corpus_index.py:410`,
  `scripts/ci/check_philosophy_source_corpus_index.py:1099`,
  `tests/test_philosophy_source_corpus_index.py:1123`.
- FIXED (Commit: 3a4d09e6e): current-head Docs Phase1 found the generic POSIX detector also matched
  repo-neutral absolute route and null-device literals in workflow/backlog/test
  files. Evidence: Anchors:
  `scripts/ci/check_philosophy_source_corpus_index.py:434`,
  `scripts/ci/check_philosophy_source_corpus_index.py:1106`,
  `tests/test_philosophy_source_corpus_index.py:1156`.
- FIXED (Commit: a8cb56911): latest CodeRabbit review found allowed-first
  leakage matches and escaping symlink targets could bypass the scanner or read
  outside-repo content. Evidence: Anchors:
  `scripts/ci/check_philosophy_source_corpus_index.py:1101`,
  `scripts/ci/check_philosophy_source_corpus_index.py:1177`,
  `tests/test_philosophy_source_corpus_index.py:1166`,
  `tests/test_philosophy_source_corpus_index.py:1257`.
- FIXED (Commit: 328be5c3f): latest CodeRabbit review found closure bullets
  without explicit commit/evidence tuples. Evidence: Anchors:
  `docs/review/PR_1822_FIXED_MAPPING.md:534`,
  `docs/review/PR_1822_FIXED_MAPPING.md:557`,
  `docs/review/PR_1822_FIXED_MAPPING.md:650`,
  `docs/review/PR_1822_FIXED_MAPPING.md:670`.
- FIXED (Commit: 2f56f505b): all-match leakage scanning exposed repo-neutral
  infrastructure literals in workflow/backlog text after the scanner stopped
  short-circuiting on the first allowed match. Evidence: Anchors:
  `scripts/ci/check_philosophy_source_corpus_index.py:436`,
  `scripts/ci/check_philosophy_source_corpus_index.py:1106`,
  `tests/test_philosophy_source_corpus_index.py:1166`.
- FIXED (Commit: b1f820608): latest Codex comments found route-literal
  false positives, blanket `/api/` route false negatives, and credential-name
  false positives. Evidence: Anchors:
  `scripts/ci/check_philosophy_source_corpus_index.py:432`,
  `scripts/ci/check_philosophy_source_corpus_index.py:1115`,
  `scripts/ci/check_philosophy_source_corpus_index.py:1122`,
  `tests/test_philosophy_source_corpus_index.py:1166`,
  `tests/test_philosophy_source_corpus_index.py:1222`.
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
- `$VENV_PYTHON -m pytest -q tests/test_philosophy_source_corpus_index.py` PASS after the discipline-rail enum regression.
- `$VENV_PYTHON -m pytest -q tests/test_philosophy_source_corpus_index.py tests/test_ci_workflow_pr_size_governance_contract.py tests/test_docs_phase1_gates.py` PASS after the path/encoding hardening regressions.
- `$VENV_PYTHON -m pytest -q tests/test_philosophy_source_corpus_index.py` PASS after the Windows/symlink leak hardening regressions.
- `$VENV_PYTHON -m pytest -q tests/test_philosophy_source_corpus_index.py tests/test_semantic_cache_gate.py` PASS after the POSIX/edge-space leak hardening regressions.
- `python3 scripts/ci/check_philosophy_source_corpus_index.py --check --files $(git diff --name-only $(git merge-base origin/main HEAD)...HEAD)` PASS after the repo-neutral absolute route allowlist regression.
- `$VENV_PYTHON -m pytest -q tests/test_philosophy_source_corpus_index.py` PASS after the repo-neutral absolute route allowlist regression.
- `python3 scripts/ci/check_philosophy_source_corpus_index.py --check --files scripts/ci/check_philosophy_source_corpus_index.py tests/test_philosophy_source_corpus_index.py docs/review/PR_1822_FIXED_MAPPING.md` PASS after the allowed-first match and escaping-symlink hardening regressions.
- `$VENV_PYTHON -m pytest -q tests/test_philosophy_source_corpus_index.py` PASS after the allowed-first match and escaping-symlink hardening regressions.
- `$VENV_PYTHON -m mypy --explicit-package-bases --follow-imports=skip scripts/ci/check_philosophy_source_corpus_index.py tests/test_philosophy_source_corpus_index.py` PASS after the allowed-first match and escaping-symlink hardening regressions.
- `python3 scripts/ci/check_philosophy_source_corpus_index.py --check --files $(git diff --name-only $(git merge-base origin/main HEAD)...HEAD)` PASS after the repo-neutral infrastructure literal regression.
- `python3 scripts/ci/check_philosophy_source_corpus_index.py --check --files $(git diff --name-only $(git merge-base origin/main HEAD)...HEAD)` PASS after the route/credential scanner refinement.
- `$VENV_PYTHON -m pytest -q tests/test_philosophy_source_corpus_index.py` PASS after the route/credential scanner refinement.
- `python3 scripts/ci/check_ai_bounded_context_a3_closeout.py` PASS after the PR-5 semantic-cache roadmap wording fix.
- `$VENV_PYTHON -m pytest -q tests/test_ai_bounded_context_a3_closeout.py::test_checker_passes_on_current_repository` PASS.
- `$VENV_PYTHON -m mypy --explicit-package-bases --follow-imports=skip scripts/ci/check_philosophy_source_corpus_index.py tests/test_philosophy_source_corpus_index.py` PASS.
- `git diff --check` PASS after the path/encoding hardening diff.
- Codex-security-style diff scan: no new secret/local-path payloads in the
  touched diff; only scanner-function context matched the word `secret`.
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
