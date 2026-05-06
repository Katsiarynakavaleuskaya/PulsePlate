# PR 1685 Fixed Mapping

## Summary

PR #1685 hardens `scripts/design/generate_design_md.py` so invalid declared
component evidence paths fail closed before runtime fallback. The PR remains
narrowly scoped to the DESIGN.md generator, focused tests, and this review
mapping artifact.

## Discussion Thread Pass

- Sourcery overall review:
  https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1685#pullrequestreview-4236488355
- Codex inline review thread:
  https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1685#discussion_r3195828290
- CodeRabbit nitpick review:
  https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1685#pullrequestreview-4236507785
- Cubic review:
  https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1685#pullrequestreview-4236514753

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1685#pullrequestreview-4236488355 -> 1ff2f40e7837fa26e29e4f2a4b165b1afa26a71e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1685#discussion_r3195828290 -> 1ff2f40e7837fa26e29e4f2a4b165b1afa26a71e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1685#pullrequestreview-4236507785 -> d72d352ebdf8e012e6cdda0f0aea7ecf7f1c31ce

## Review Dispositions

- Disposition: FIXED
  Source: Sourcery overall review.
  Commit: 1ff2f40e7837fa26e29e4f2a4b165b1afa26a71e
  Evidence: `scripts/design/generate_design_md.py:108` resolves `repo_root`
  once per evidence lookup, `scripts/design/generate_design_md.py:111` returns
  `invalid-declared-path` before fallback when the declared path is invalid, and
  `scripts/design/generate_design_md.py:100` relies on `Path.is_relative_to`
  without the redundant equality check.

- Disposition: FIXED
  Source: Codex inline review thread on invalid declared paths being masked by
  runtime fallback.
  Commit: 1ff2f40e7837fa26e29e4f2a4b165b1afa26a71e
  Evidence: `scripts/design/generate_design_md.py:111` short-circuits invalid
  declared evidence paths before `RUNTIME_COMPONENT_FALLBACKS`, and
  `tests/design/test_generate_design_md.py:101` proves a `select` fallback path
  is not rendered when the declared path is invalid.

- Disposition: FIXED
  Source: CodeRabbit nitpick requesting inside-repo but outside allowed-prefix
  coverage.
  Commit: d72d352ebdf8e012e6cdda0f0aea7ecf7f1c31ce
  Evidence: `tests/design/test_generate_design_md.py:145` rejects
  `docs/design/not_a_component.tsx` as `invalid-declared-path` and renders
  `none`.

- Disposition: NOT-A-BUG
  Source: Cubic review.
  Evidence: Cubic found no issues across the two changed files. No code change
  or follow-up was required from that review.

## Tests / Bounded Checks

- `python3 scripts/orchestration/check_preflight.py` -> PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` -> PASS.
- `python3 scripts/design/generate_design_md.py --check` -> PASS.
- `python3 -m py_compile scripts/design/generate_design_md.py tests/design/test_generate_design_md.py` -> PASS.
- `python3 -m pytest -q tests/design/test_generate_design_md.py` -> BLOCKED in system Python by missing `fastapi` import from root `conftest.py`.
- `.venv/bin/python -m pytest -q tests/design/test_generate_design_md.py` -> PASS, 14 tests.
- `make validate-changed` -> PASS, selected `tests/design/test_generate_design_md.py`, 14 tests.
- `make design-guard` -> PASS.
- `make tokens-check` -> PASS.
- Token mirror diff check for `frontend/src/styles/tokens.css`,
  `frontend/src/styles/tokens.ts`, and
  `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift` -> no diff.

Full local `make verify` was intentionally not run per operator instruction.

## Premortem

It is 48 hours from now and this security hardening made the design governance
lane worse. The most likely failure would be mapping the review without changing
the fail-closed order, leaving invalid declared paths masked by runtime fallback.
The fix changes the decision order before mapping and adds tests for fallback
masking, absolute paths, traversal paths, and in-repo non-frontend paths.

Checks:

- Absolute paths cannot leak into generated DESIGN.md evidence rows.
- `..` traversal paths cannot leak into generated DESIGN.md evidence rows.
- Invalid declarations cannot be masked by runtime fallback.
- Paths outside repo root are rejected.
- Paths inside repo but outside allowed frontend prefixes are rejected.
- Generated token mirrors were not modified.
- Scope stayed limited to generator/tests plus this review artifact.
- Mapping was created after code and test fixes existed.

Decision: proceed with bounded governance checks and current-head CI/review
loop; do not claim merge readiness from local bounded checks alone.

## Bug-hunter pass

- Before mapping, PR diff was limited to
  `scripts/design/generate_design_md.py` and
  `tests/design/test_generate_design_md.py`.
- After mapping, only `docs/review/PR_1685_FIXED_MAPPING.md` is added.
- No frontend runtime, iOS runtime, backend, OpenAPI, generated token mirror,
  Figma, or Canva files were changed.
- Invalid declared paths fail closed before runtime fallback.
- Focused tests cover the exploit class and CodeRabbit's allowed-prefix gap.
- PR body must not claim full local `make verify`.

## Merge Readiness

Not claimed by this artifact alone. Merge readiness still requires:

- current-head PR checks complete with required checks passing,
- no actionable bot comments,
- no unresolved actionable review threads,
- PR body mirror aligned with this artifact,
- mandatory wait-window satisfied,
- strict `check_merge_ready.py --require-auth` wrapper passing.
