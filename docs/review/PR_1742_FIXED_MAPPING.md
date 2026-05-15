# PR 1742 Fixed Mapping

## PR

- PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742
- Branch: `feat/ai-runtime-semantic-cache-backend-selection-contract`
- Title: `feat(ai-runtime): add semantic-cache backend selection contract`
- Scope: SC-G5 offline semantic-cache backend selection contract/evaluation matrix only.

## Summary

SC-G5 adds a deterministic, offline, label-only backend selection contract and matrix for future semantic-cache backend evaluation. Redis and GPTCache remain inert candidate labels only. The global semantic-cache gate remains closed.

## Scope

- Pure stdlib-only `core/ai/semantic_cache_backend_selection.py`.
- Machine-checkable SC-G5 contract doc and schema.
- CI checker and docs Phase 1 gate updates.
- Focused tests and import/call guard coverage.
- Narrow roadmap/backlog updates.

## Out Of Scope

- Runtime serving.
- `/insight` route wiring.
- Redis/GPTCache clients, imports, connection strings, probes, or activation.
- Embeddings, vector search, provider calls, DB, FastAPI/OpenAPI, migrations, frontend, or iOS.
- Raw prompt/query/response/answer persistence.

## Premortem Fixes Before PR Open

| Finding | Disposition | Commit | Evidence |
| --- | --- | --- | --- |
| Forged candidate decisions could bypass safety ranking. | FIXED | `8a974394e` | Selector recomputes candidate decisions; regression coverage in `tests/core/ai/test_semantic_cache_backend_selection.py`. |
| Machine-state checker could pass after required fields were renamed/removed. | FIXED | `8a974394e` | SC-G5 checker validates exact required keys and unexpected keys. |
| Guard missed annotated `Path` aliases. | FIXED | `8a974394e` | `AnnAssign` aliases are tracked; regression coverage added. |
| Matrix constructor accepted forged final decision / candidate decisions. | FIXED | `8a974394e` | Matrix recomputes decisions and rejects mismatches. |
| Guard missed direct/alias `Path.open(...).write(...)`. | FIXED | `a09788814` | Guard detects direct/alias Path open writes; regression coverage added. |
| Matrix constructor accepted forged `matrix_id`. | FIXED | `a09788814` | Matrix validates canonical deterministic matrix ID. |
| Guard missed context-manager `Path.open(...).write(...)`. | FIXED | `3772bba5d` | Guard tracks context manager file handles from Path.open. |
| Context-manager test was too broad and could false-green. | FIXED | `f2f3dabf4` | Dedicated test now asserts `Path.open.write` specifically. |

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Post-open bot and agent review threads were triaged after concrete fixes or explicit dispositions. Mapping was updated after fix commits existed.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 083c1eeca
Evidence: Mapping artifact checkboxes and matrix signature checks were added; local gates passed before the commit was pushed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233091753 -> 083c1eeca
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233099804 -> 083c1eeca

Disposition: FIXED
Commit: 7c745043b
Evidence: Sourcery, CodeRabbit, and Cubic findings were fixed in code/docs/tests; focused tests, mypy, semantic-cache checker, docs gate, validate-changed, and pre-commit passed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233057757 -> 7c745043b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233057761 -> 7c745043b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233091809 -> 7c745043b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233099837 -> 7c745043b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233143300 -> 7c745043b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233143327 -> 7c745043b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233143335 -> 7c745043b

Disposition: FIXED
Commit: 710920a07
Evidence: Follow-up Codex review findings were fixed in code/tests; focused tests, mypy, semantic-cache checker, docs gate, bounded regression bundle, validate-changed, and pre-commit passed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233099817 -> 710920a07
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233099830 -> 710920a07
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233099844 -> 710920a07
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233249559 -> 710920a07
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233249564 -> 710920a07
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233249572 -> 710920a07
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233249582 -> 710920a07
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233249588 -> 710920a07
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233249590 -> 710920a07
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233249591 -> 710920a07
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233249593 -> 710920a07

Disposition: NOT-A-BUG
Evidence: `tests/core/ai/test_semantic_cache_backend_selection.py` includes `test_no_core_ai_export_side_door`, which asserts SC-G5 remains unexported from `core/ai/__init__.py`.
Reason: The test import path intentionally exercises the repo import contract; SC-G5 still has no eager export or runtime serving side door.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233249567

Disposition: FIXED
Commit: 45155f837
Evidence: `_PATH_RE` is case-insensitive and `_UNSAFE_TOKEN_RE` uses boundary-aware `sk-` matching; regression coverage rejects uppercase `FILE://` metadata and accepts benign `risk-audit` evidence IDs.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233467998 -> 45155f837
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233468011 -> 45155f837

Disposition: FIXED
Commit: 34d824dd7
Evidence: Second bot-wave guard/checker gaps were fixed in code/tests: password/pwd screening, embedded and Windows local paths, direct decision consistency, exact schema drift checks, joined Path aliases, builtins/io open aliases, shutil copy helpers, os directory creation, and unknown `Path.open(**kwargs)` modes. Focused tests, mypy, semantic-cache gates, bounded regression bundle, validate-changed, and pre-commit passed. Final Codex Security scan is clean at `/tmp/codex-security-scans/ai-runtime-semantic-cache-backend-selection-contract/34d824dd7_20260513T112843Z/report.md`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#pullrequestreview-4280941032 -> 34d824dd7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233477733 -> 34d824dd7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233477741 -> 34d824dd7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233477746 -> 34d824dd7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233477749 -> 34d824dd7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233477751 -> 34d824dd7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233477755 -> 34d824dd7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233572115 -> 34d824dd7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233572116 -> 34d824dd7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233572121 -> 34d824dd7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233572125 -> 34d824dd7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233572129 -> 34d824dd7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233679571 -> 34d824dd7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233679575 -> 34d824dd7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233679577 -> 34d824dd7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233679581 -> 34d824dd7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233680564 -> 34d824dd7

Disposition: FIXED
Commit: 7c745043b
Evidence: Initial Sourcery/CodeRabbit/Cubic review summaries were closed by code/docs/tests fixes mapped above for duplicate reasons, payload fields, workforce-memory anchors, fully-qualified Path writes, and constants.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#pullrequestreview-4280240302 -> 7c745043b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#pullrequestreview-4280282003 -> 7c745043b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#pullrequestreview-4280341492 -> 7c745043b

Disposition: FIXED
Commit: 710920a07
Evidence: Follow-up CodeRabbit review summary was closed by candidate/final decision identity, duplicate candidate, canonicalization, file URI, CI proof ID, token field, environment-read, and write-mode Path.open fixes mapped above.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#pullrequestreview-4280437664 -> 710920a07

Disposition: FIXED
Commit: 45155f837
Evidence: Later CodeRabbit/Cubic review summaries were closed by boundary-aware token detection, case-insensitive file URI path detection, zero-tolerance criteria, structured proof IDs, and side-effect guard fixes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#pullrequestreview-4280688583 -> 45155f837
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#pullrequestreview-4280702807 -> 45155f837

Disposition: FIXED
Commit: 3be17053c
Evidence: Proof gates, network/file/runtime dependency machine-state anchors, path mutation guards, and human approval machine-state evidence were fixed in code/checker/tests before these threads were resolved.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233355417 -> 3be17053c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233355420 -> 3be17053c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233355426 -> 3be17053c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233355431 -> 3be17053c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233355435 -> 3be17053c

Disposition: NOT-A-BUG
Evidence: Current SC-G5 code/checker/tests already enforce the selected-decision shape, ineligible-candidate rejection shape, import/write/network/env guards, schema drift anchors, proof gates, blocked truth sources, and metadata/evidence-token screening. These review threads were posted after the corresponding code/test hardening was already present on the PR branch, so no post-comment code change was required.
Reason: The comments are valid invariants, but the current implementation and focused regression suite already satisfy them; they are recorded here as explicit dispositions rather than mapped to pre-comment fix SHAs.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233874718
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233874728
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233874736
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233874745
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3233874755
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3234121103
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3234121110
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3234121114
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3234121122
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3234121129
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3234121139
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3234121148
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3234121153
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3234474192
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3234474196
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3234474199
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3234705401
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3234705409
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3234705415
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3234705422
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3234705429
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3234816772
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3234816779
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3234816787
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3234816793
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3234816803
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3234996447
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3234996452
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3234996454
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3234996473
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3234996476

Disposition: FIXED
Commit: 0c8af9c47
Evidence: `tests/test_design_automation_next_lane_docs.py` no longer performs `git fetch`; focused pytest and mypy for the Kimi docs-only guard passed before this mapping update.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3234705435 -> 0c8af9c47

Disposition: NOT-A-BUG
Evidence: `tests/core/ai/test_semantic_cache_backend_selection.py::test_no_core_ai_export_side_door` asserts SC-G5 remains unexported from `core/ai/__init__.py`; the direct module import in tests is intentional contract coverage.
Reason: The test import path does not create an eager `core.ai` facade export or runtime serving side door.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3234474185

Disposition: NOT-A-BUG
Evidence: Current SC-G5 code/checker/tests already enforce blocked personalized/auth/provider payload metadata, blocked runtime dependencies, blocked truth sources, schema-only drift coverage, forbidden contract claims, ineligible decision consistency, unsafe capability labels, token-list shape, and structured current-head CI proof IDs.
Reason: These later review threads restated invariants already enforced by the current implementation and regression suite; no additional code change was required beyond the mapped offline docs-test fix.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3235463347
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3235463355
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3235463359
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3235463365
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3235463369
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3235463375
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3235463382
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3235905768
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3235905774
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3235905779
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3235905786

Disposition: FIXED
Commit: b05f5fb28
Evidence: Final bot-wave P2 findings were fixed in code/tests/CI: Path effect-method aliases are rejected, SC-G5 decision IDs require SC-G5 deterministic prefixes/suffixes, SC-G5 machine-state JSON validation is bound to the `Machine-Readable State` section, and `test-main` uses full checkout history so Kimi docs guard uses `origin/main...HEAD` instead of a last-commit fallback. Focused pytest and mypy passed before this mapping update.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3236379406 -> b05f5fb28
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3236379414 -> b05f5fb28
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3236379418 -> b05f5fb28
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3236379421 -> b05f5fb28

Disposition: FIXED
Commit: 74219fd13
Evidence: Latest bot-wave P2 guard/checker gaps were fixed in code/tests: built-in `open` aliases are rejected, broader `os.environ.*` calls are rejected, SC-G5 schema validation requires root `type: object` and closed-state consts, and metadata blocks colon-delimited `provider:payload`. Focused pytest, split mypy, semantic-cache checker, docs Phase1 gate, `make validate-changed`, and `pre-commit run --all-files` passed before this mapping update.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3239521135 -> 74219fd13
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3239521137 -> 74219fd13
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3239521142 -> 74219fd13
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3239521144 -> 74219fd13
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3239521149 -> 74219fd13

Disposition: FIXED
Commit: b5881b10f
Evidence: Latest follow-up bot-wave guard gaps were fixed in code/tests: SC-G5 schema validation now requires list-valued contract fields to remain arrays with `minItems`, `uniqueItems`, and string items; metadata blocks plural raw/normalized query labels and provider payload plurals; import guard rejects class-method `Path.open(..., write-mode)` calls. Focused pytest, split mypy, semantic-cache checker, docs Phase1 gate, `make validate-changed`, and `pre-commit run --all-files` passed before this mapping update.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241290733 -> b5881b10f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241290736 -> b5881b10f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241290741 -> b5881b10f

Disposition: FIXED
Commit: b6fd8ca27
Evidence: Latest sensitive-token review gaps were fixed in code/tests: evidence/proof IDs block plural raw/normalized query labels, raw model response labels, separated HealthKit labels, and provider payload labels; metadata blocks colon-delimited sensitive/truth-source labels and separated HealthKit forms; tuple proof-token fields reuse unsafe proof-token screening; structured proof IDs now require suffix evidence after their allowed prefixes. Focused pytest, split mypy, semantic-cache checker, preflight, agent consistency, `make validate-changed`, and `pre-commit run --all-files` passed before this mapping update.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241290744 -> b6fd8ca27
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241355585 -> b6fd8ca27
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241355592 -> b6fd8ca27
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241355595 -> b6fd8ca27
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241355600 -> b6fd8ca27
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241355607 -> b6fd8ca27
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241355622 -> b6fd8ca27

Disposition: FIXED
Commit: 4b4200da4
Evidence: Latest review gaps were fixed in code/checker/tests: SC-G5 candidate eligibility now requires exact SC-G2/SC-G3/SC-G4 contract evidence IDs, scalar contract/admission evidence IDs reuse unsafe evidence screening before serialization, the package facade no longer eagerly imports runtime modules when SC-G5 is imported, and the machine-state checker validates every rollback proof field. Focused pytest, split mypy, semantic-cache checker, docs Phase1 gate, preflight, agent consistency, `make validate-changed`, and `pre-commit run --all-files` passed before this mapping update.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241408441 -> 4b4200da4
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241408448 -> 4b4200da4
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241408454 -> 4b4200da4
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241408459 -> 4b4200da4

Disposition: FIXED
Commit: 1f6cec218
Evidence: Latest backend-proof review gaps were fixed in code/checker/tests: metadata/evidence screening now blocks personalized coaching-state and auth-truth labels, backend-version tokens reject runtime config/connection labels before serialization, rollback proof eligibility is bound to the candidate backend label, the machine-state checker requires every blocked truth source declared by the contract JSON, and the semantic-cache import guard tracks aliases to the `Path` constructor. Focused pytest, split mypy, semantic-cache checker, docs Phase1 gate, preflight, agent consistency, `make validate-changed`, and `pre-commit run --all-files` passed before this mapping update.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241477769 -> 1f6cec218
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241477774 -> 1f6cec218
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241477781 -> 1f6cec218
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241477786 -> 1f6cec218
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241477792 -> 1f6cec218
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241477800 -> 1f6cec218

Disposition: FIXED
Commit: 930c1149f
Evidence: Third backend-proof review wave was fixed in code/checker/tests: upstream evidence mismatches now emit distinct SC-G2/SC-G3/SC-G4 reason codes, direct decision objects reject unknown reason codes, rollback proof fields require structured machine-checkable IDs, the import guard tracks `os.environ` aliases and blocks runtime facade imports through `core.ai`, and docs Phase1 gates validate SC-G5 schema-only edits. Focused pytest, split mypy, semantic-cache checker, docs Phase1 gate, preflight, agent consistency, `make validate-changed`, and `pre-commit run --all-files` passed before this mapping update.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241547719 -> 930c1149f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241547724 -> 930c1149f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241547726 -> 930c1149f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241547729 -> 930c1149f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241547736 -> 930c1149f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241547742 -> 930c1149f

Disposition: FIXED
Commit: f1c64248a
Evidence: Fourth backend-proof review wave was fixed in code/checker/tests: rollback eligibility now verifies the backend token across the full rollback proof bundle, public candidate tuple fields reject runtime-scope labels before serialization, and the SC-G5 machine-state checker requires every blocked runtime dependency and forbidden claim already declared by the contract JSON. Focused pytest, split mypy, semantic-cache checker, docs Phase1 gate, `make validate-changed`, and `pre-commit run --all-files` passed before this mapping update.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241598060 -> f1c64248a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241598066 -> f1c64248a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241598070 -> f1c64248a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241598076 -> f1c64248a

Disposition: FIXED
Commit: 82ae60197
Evidence: Latest runtime-label review wave was fixed in code/tests: backend versions, criteria surfaces, and structured proof IDs reject runtime-scope labels before serialization, and the import guard rejects `os.getenv` aliases. Focused pytest, mypy, `make validate-changed`, and `pre-commit run --all-files` passed before this mapping update.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241707071 -> 82ae60197
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241707078 -> 82ae60197
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241707084 -> 82ae60197
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241707091 -> 82ae60197

Disposition: FIXED
Commit: eccaa2310
Evidence: Latest metadata/schema review wave was fixed in code/checker/tests: the SC-G5 schema checker now requires enum lists for allowed and candidate backend labels, metadata rejects runtime-scope labels and non-string keys before stable serialization, unsafe truth-source labels cover local support plane, plugin control-plane, and second source of truth, and safety evidence tuple IDs reject runtime-scope labels. Focused pytest, mypy, semantic-cache checker, docs Phase1 gate, preflight, agent consistency, `make validate-changed`, and `pre-commit run --all-files` passed before this mapping update.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241885721 -> eccaa2310
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241885723 -> eccaa2310
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241885730 -> eccaa2310
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241885733 -> eccaa2310
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3241885743 -> eccaa2310

Disposition: FIXED
Commit: d145aa473
Evidence: Post-update review wave was fixed in code/checker/docs/tests: runtime-scope matching is token-bound so normal SHA digest segments like `sha256:abdb...` remain valid; candidate IDs, selected/rejected IDs, policy versions, and criteria policy versions reject runtime-scope labels before serialization; rollback proof matching rejects ambiguous multi-backend proof IDs; current-head CI proof IDs must bind the evaluated head SHA; SC-G5 schema enum validation fails closed on malformed enum types; docs Phase1 workflow includes SC-G5 schema-only edits; and the semantic-cache import guard catches destructured `Path` aliases plus dynamic `getattr(Path(...), "write_text")` writes. Focused pytest, mypy, semantic-cache checker, docs Phase1 gate, `make validate-changed`, and `pre-commit run --all-files` passed before this mapping update.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3242063229 -> d145aa473
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3242063236 -> d145aa473
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3242063242 -> d145aa473
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3242063244 -> d145aa473
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3242063248 -> d145aa473

Disposition: FIXED
Commit: 6663ddb67
Evidence: Latest current-head Codex review wave was fixed in code/tests: direct ineligible decisions must reject their own candidate, selected decisions cannot also reject the selected candidate, decision ID prefixes are bound to candidate-evaluation versus matrix-selection decision kinds, scalar evidence IDs reject runtime-scope labels before stable serialization, and the import guard blocks dynamic `__import__("os").system(...)` plus aliases to effectful `os.system`/`os.open`. Focused pytest, mypy, semantic-cache/docs gates, `make validate-changed`, and `pre-commit run --all-files` passed before this mapping update.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3247788107 -> 6663ddb67
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3247788118 -> 6663ddb67
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3247788123 -> 6663ddb67
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3247788126 -> 6663ddb67
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3247788127 -> 6663ddb67
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3247788135 -> 6663ddb67

Disposition: FIXED
Commit: 0e04e1717
Evidence: Latest current-head review wave was fixed in code/tests: current-head CI proof matching now accepts the allowed natural `ci:current-head:<sha>:` proof shape, split FastAPI/OpenAPI spellings are blocked by token-sequence runtime-scope screening across surfaces/proof IDs/metadata, and the semantic-cache import guard rejects direct `os.environ` value reads such as `dict(os.environ)`, loops, comprehensions, and aliases. Focused pytest, mypy, `make validate-changed`, and `pre-commit run --all-files` passed before this mapping update.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3247884748 -> 0e04e1717
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3247884758 -> 0e04e1717
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1742#discussion_r3247884761 -> 0e04e1717

## Post-Open Agent Review Fixes

| Source | Disposition | Commit | Evidence |
| --- | --- | --- | --- |
| QA final pass: overbroad `sk-` token matching rejected benign `risk-audit`; uppercase `FILE://` metadata bypassed path blocking. | FIXED | `45155f837` | Boundary-aware token regex and case-insensitive path regex; regression tests in `tests/core/ai/test_semantic_cache_backend_selection.py`. |
| Bug-hunter final pass: caller-relaxed criteria could allow safety breaches; generic CI/human proof IDs could satisfy proof gates; import guard missed subprocess and dynamic Path.open write modes. | FIXED | `45155f837` | Criteria now enforce zero-tolerance safety gates and structured proof IDs; import guard blocks process launchers and unknown write modes with focused tests. |
| Security final pass: proof IDs accepted blocked payload/truth-source terms and emitted them in stable mappings. | FIXED | `45155f837` | Evidence/proof ID validation blocks raw-payload, HealthKit, account, billing, legal, compliance, advisory/wiki, and workforce-memory terms before serialization. |
| Codex Security final scan after substantive fix. | CLEAN | `45155f837` | `/tmp/codex-security-scans/ai-runtime-semantic-cache-backend-selection-contract/45155f837_20260513T110057Z/report.md` reports no surviving findings. |
| Second bot-wave guard/checker bypass review. | FIXED | `34d824dd7` | Guard/checker/code fixes listed in Fixed in Commit Mapping; final Codex Security scan clean at `/tmp/codex-security-scans/ai-runtime-semantic-cache-backend-selection-contract/34d824dd7_20260513T112843Z/report.md`. |
| Current-head diff-coverage artifact missed SC-G5 tests. | FIXED | `95ecc9412` | `.github/workflows/ci.yml` now includes `tests/core/ai/test_semantic_cache_backend_selection.py` and `tests/test_semantic_cache_backend_selection_contract.py` in both PR and feature `route_contract_safety` coverage suites; local SC-G5 diff-cover reproduction stayed at 99%. |
| Post-update QA review: current-head CI proof accepted stale head IDs. | FIXED | `d145aa473` | Criteria now carries `current_head_sha` and candidate CI proof IDs must contain `head-<sha>` for the evaluated head; stale-proof regression test covers the previous false-green. |
| Post-update bug-hunter review: malformed schema enums, dynamic `Path` getattr writes, and schema-only docs Phase1 workflow gap. | FIXED | `d145aa473` | Schema checker requires enum string lists, import guard blocks dynamic Path getattr writes and destructured aliases, and CI docs Phase1 gate targets SC-G5 schema JSON edits. |
| Post-update security review. | CLEAN | `d145aa473` | Security-auditor pass reported no actionable security findings for the post-update diff; subsequent code changes were fail-closed guard/checker/test hardening only. |

## Bot Review Tracking

| Source | Status | Disposition |
| --- | --- | --- |
| CodeRabbit | Pending current-head re-review after `0e04e1717` push | Prior actionables mapped above; not merge-ready until bot reports no remaining actionables or explicit dispositions. |
| Sourcery | Pending current-head re-review after `0e04e1717` push | Prior actionables mapped above; not merge-ready until bot reports no remaining actionables or explicit dispositions. |
| Cubic | Pending current-head re-review after `0e04e1717` push | Prior actionables mapped above; not merge-ready until bot reports no remaining actionables or explicit dispositions. |
| Codex Security | Clean after final substantive fix | Final scan for commit `95ecc9412` reports no surviving findings at `/tmp/codex-security-scans/ai-runtime-semantic-cache-backend-selection-contract/95ecc9412_20260513T121007Z/report.md`. |
| Codecov | Pending current-head CI parity | Historical patch coverage comment is not merge-readiness proof; canonical diff coverage remains current-head CI plus local focused diff-cover evidence. |

## Local Evidence Before PR Open

- `python scripts/orchestration/check_preflight.py` passed.
- `python scripts/orchestration/check_agent_consistency.py` passed.
- `python scripts/ci/check_semantic_cache_gate.py` passed.
- `python scripts/ci/check_docs_phase1_gates.py --files ...` passed.
- Focused semantic-cache pytest bundle passed.
- Narrow mypy passed.
- `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed` passed.
- `PATH=.venv/bin:$PATH pre-commit run --all-files` passed.
- Diff-cover for SC-G5 changed code passed at 99%.
- Latest focused post-update pytest, mypy, semantic-cache checker, docs Phase1 gate, `make validate-changed`, and `PATH=.venv/bin:$PATH pre-commit run --all-files` passed before `d145aa473`.
- Latest current-head decision/guard focused pytest, mypy, semantic-cache/docs gates, `make validate-changed`, and `PATH=.venv/bin:$PATH pre-commit run --all-files` passed before `6663ddb67`.
- Latest current-head proof/runtime-label/environment guard focused pytest, mypy, `make validate-changed`, and `PATH=.venv/bin:$PATH pre-commit run --all-files` passed before `0e04e1717`.
- Latest pre-push hooks passed during `95ecc9412` branch push, including full repo Bandit and docker build test. Pre-push must rerun before the next push.

## Merge Readiness

Not merge-ready at PR open. Required before merge:

- Current-head CI clean.
- Strict merge wrapper with auth passes.
- No unresolved review threads.
- CodeRabbit, Sourcery, Cubic have no actionables or explicit dispositions.
- Codex Security review clean or dispositioned.
- Mandatory wait-window observed.
