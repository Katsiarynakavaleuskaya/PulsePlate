# PR #1680 Fixed Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1680
Branch: `feat/design-reference-manifest-tooling-v1`
Title: `feat(design): add external reference manifest and normalization tooling`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Initial post-open mapping artifact created
- [x] Premortem / advisory findings fixed before PR open

## Local Evidence

- `python3 scripts/orchestration/check_preflight.py` -> PASS
- `python3 scripts/orchestration/check_agent_consistency.py` -> PASS
- `python3 scripts/orchestration/task_bootstrap.py ... --pr-phase pre_open` -> PASS (`artifacts/orchestration/task_packets/d7a5d322a084.json`, local/gitignored)
- `python3 scripts/orchestration/task_bootstrap.py ... --pr-phase post_open_review` -> PASS (`artifacts/orchestration/task_packets/40281bf2d2e6.json`, local/gitignored)
- `python3 scripts/design/reference_manifest.py validate-dir docs/design/reference_manifest/examples` -> PASS
- `. .venv/bin/activate && python3 -m pytest -q tests/design/test_reference_manifest.py` -> PASS (27 tests)
- `make validate-changed` -> PASS
- `make design-guard` -> PASS
- `make tokens-check` -> PASS
- `pre-commit run --all-files` -> PASS
- `git diff -- frontend/src/styles/tokens.css frontend/src/styles/tokens.ts ios/PulsePlate/DesignSystem/DesignTokens.generated.swift` -> empty

Full local `make verify` was intentionally not run by operator machine-budget policy.

## Commit Mapping

- `62a532c808a5f891b3fdd408bc53b299e8817d8c` -> `feat(design): add reference manifest validation tooling`
- `e7462a17a41cfd403f4dc409c1f633317b8ea20d` -> `fix(design): harden reference manifest validation`
- `75f24c1eb186b4f131ad138b8c4d7625fc2500e2` -> `test(design): cover reference manifest validation rules`
- `4d4fe5672dcdc425d45915cd92dcff1e77561043` -> `docs(design): add reference manifest examples and wave status`
- `72544e57c` -> `fix(design): close reference manifest review gaps`
- `5b5c08a95` -> `fix(design): close reference manifest bot review gaps`

### Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1680#pullrequestreview-4235600795 -> 72544e57c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1680#pullrequestreview-4235682587 -> 5b5c08a95
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1680#pullrequestreview-4235691089 -> 5b5c08a95
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1680#discussion_r3195008771 -> 72544e57c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1680#discussion_r3195008797 -> 72544e57c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1680#discussion_r3195087415 -> 5b5c08a95
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1680#discussion_r3195087430 -> 5b5c08a95
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1680#discussion_r3195087435 -> 5b5c08a95
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1680#discussion_r3195095771 -> 5b5c08a95

Disposition: FIXED
Commit: 72544e57c
Evidence: Cubic flagged asymmetric status/decision validation; `scripts/design/reference_manifest.py` now rejects `status=rejected` unless `adopt_adapt_reject_decision=reject`, and `tests/design/test_reference_manifest.py` covers the contradictory rejected/adapt state.

Disposition: FIXED
Commit: 72544e57c
Evidence: Cubic flagged vocabulary load failures escaping deterministic validation; `scripts/design/reference_manifest.py` now converts vocabulary JSON/read failures into `ManifestError` validation errors, and `tests/design/test_reference_manifest.py` asserts malformed vocabulary returns `ERROR:` without traceback.

Disposition: FIXED
Commit: 5b5c08a95
Evidence: CodeRabbit flagged missing PR-2 traceability; `docs/roadmap/BACKLOG_LEDGER.md` now names PR #1680 in the Design Intelligence Target PR chain.

Disposition: FIXED
Commit: 5b5c08a95
Evidence: CodeRabbit flagged source-of-truth scanning over untrusted metadata; `scripts/design/reference_manifest.py` now scans only trusted narrative policy fields, and `tests/design/test_reference_manifest.py` covers a `source_url` containing source-of-truth wording without influencing validation.

Disposition: FIXED
Commit: 5b5c08a95
Evidence: CodeRabbit flagged malformed `normalize` input producing traceback; `scripts/design/reference_manifest.py` now catches `ManifestError` in the `normalize` path, and `tests/design/test_reference_manifest.py` covers deterministic `ERROR:` output without traceback.

Disposition: FIXED
Commit: 5b5c08a95
Evidence: Cubic flagged malformed UTF-8 vocabulary reads; `scripts/design/reference_manifest.py` now converts `UnicodeDecodeError` into deterministic `ManifestError`, and `tests/design/test_reference_manifest.py` covers malformed UTF-8 vocabulary without traceback.

## Premortem Fix Evidence

Disposition: FIXED
Commit: e7462a17a41cfd403f4dc409c1f633317b8ea20d
Evidence: Premortem finding "component patterns were not vocabulary-grounded" was fixed; `scripts/design/reference_manifest.py` validates `component_patterns` against PulsePlate vocabulary ids, canonical names, and aliases; `tests/design/test_reference_manifest.py` covers unknown component patterns and accepted canonical aliases.

Disposition: FIXED

Commit: e7462a17a41cfd403f4dc409c1f633317b8ea20d
Evidence: Premortem finding "direct-copy and implementation-authority wording could bypass validation" was fixed; `scripts/design/reference_manifest.py` broadens direct-copy detection for protected elements before/after copy verbs and implementation-authority phrasing; `tests/design/test_reference_manifest.py` covers screenshot-copy, implementation-reference, and duplicate vendor layout/brand variants.

Disposition: FIXED

Commit: e7462a17a41cfd403f4dc409c1f633317b8ea20d
Evidence: Premortem finding "malformed JSON could escape as traceback instead of deterministic CLI error" was fixed; `_load_json` converts JSON/read errors into `ManifestError`; `tests/design/test_reference_manifest.py` asserts `ERROR:` output and no traceback for malformed JSON.

## Premortem

Premortem reviewed actual code/docs/tests diff and confirmed:

- external references remain read-only and non-canonical,
- no crawler, network access, Figma writes, Canva writes, external assets, or plugin architecture were introduced,
- manifest validation fails closed on status, decision, license, copy-risk, wellness-safety, component mapping, component pattern, and source-of-truth drift risks,
- PR-4 scorecard engine and PR-3 screen evidence pack remain deferred,
- no frontend, iOS, backend, OpenAPI, billing, auth, deployment, `/tokens`, or generated token mirror files are changed.

## Bug-Hunter Pass

Bug-hunter checks covered:

- examples are synthetic and valid,
- `validate-dir` checks all example JSON files,
- `normalize` output is deterministic,
- malformed JSON fails with deterministic `ERROR:` output,
- malformed UTF-8 vocabulary and malformed normalize input fail with deterministic `ERROR:` output,
- unknown component ids and component patterns fail,
- `candidate_for_brief` requires resolved license/copy fields,
- no token mirror diff,
- no runtime diff.

## Merge Readiness

Not claimed. Merge readiness remains blocked until current-head CI, review-thread dispositions, bot no-actionables, this mapping artifact, PR body mirror, mandatory wait-window, and strict `check_merge_ready.py --require-auth` pass.
