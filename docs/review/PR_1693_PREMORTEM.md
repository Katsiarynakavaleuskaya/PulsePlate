# PR #1693 Premortem

Mode: `pr-premortem`
Coordinator packet: `artifacts/orchestration/task_packets/954153912a69.json`

## Summary

PR #1693 prevents placeholder scalar values from counting as design evidence
and centralizes the evidence-value helper so scorecard and screen evidence pack
semantics cannot drift.

Frame: It is 48 hours from now. This design-evidence hotfix made the evidence
contract weaker. We are looking backward to understand why.

Changed files inspected:

- `scripts/design/evidence_utils.py`
- `scripts/design/design_scorecard.py`
- `scripts/design/screen_evidence_pack.py`
- `tests/design/test_design_scorecard.py`
- `tests/design/test_screen_evidence_pack.py`
- `docs/review/PR_1693_PREMORTEM.md`
- `docs/review/PR_1693_FIXED_MAPPING.md`

## Risk Table

| Priority | Failure mode | Finding | Required fix | Evidence | Disposition |
| --- | --- | --- | --- | --- | --- |
| P0 | Placeholder scalar still counts as evidence | `None`, `False`, `0`, blank strings, and whitespace-only strings return false. | Keep helper string-only and recursive. | `scripts/design/evidence_utils.py`; design tests | FIXED |
| P0 | Nested placeholder list/dict still counts | Nested placeholders return false unless a non-empty string exists. | Add nested placeholder and nested valid string tests. | `tests/design/test_design_scorecard.py`; `tests/design/test_screen_evidence_pack.py` | FIXED |
| P1 | Helper logic diverges between modules | Helper is centralized in `scripts/design/evidence_utils.py`. | Remove duplicate helper definitions from both modules. | `tests/design/test_design_scorecard.py::test_design_evidence_helper_is_shared` | FIXED |
| P1 | Circular imports introduced | Both modules import the helper from a standalone utility module with direct-run fallback. | Avoid importing either design module from the other. | Focused design tests and CLI-compatible import fallback | FIXED |
| P1 | `status=validated` accepts fake evidence | Placeholder-only evidence still triggers validation errors. | Keep `_dict_has_evidence` on shared helper. | `tests/design/test_screen_evidence_pack.py` | FIXED |
| P1 | Scorecard accepts `False`/`0` as evidence | Placeholder scalar scorecard dimensions stay zero. | Preserve scalar rejection tests. | `tests/design/test_design_scorecard.py` | FIXED |
| P2 | Tests only cover happy path | Negative and nested-positive cases are covered. | Add targeted negative and nested-positive tests. | Focused design test suite | FIXED |

## Decision

PASS. No unresolved P0/P1 findings remain. The Codex numeric/boolean evidence
suggestion is NOT-A-BUG for this PR because the explicit task contract requires
only non-empty strings to count as evidence.

## Validation Evidence

- `python3 scripts/orchestration/check_preflight.py` PASS
- `python3 scripts/orchestration/check_agent_consistency.py` PASS
- `. .venv/bin/activate && pytest -q tests/design/test_design_scorecard.py tests/design/test_screen_evidence_pack.py` PASS
- `. .venv/bin/activate && pytest -q tests/test_repo_policy_guards.py` PASS
- `make validate-changed` PASS
- `pre-commit run --all-files` PASS
