<!-- markdownlint-disable MD013 -->
# Definition Of Done Check

**Date:** 2026-04-30

## Completed

- [x] Coordinator bootstrap packet created: `72f36df2d589`
- [x] Branch created: `codex/design-prototype-canvas-packet-v1`
- [x] Figma Make context fetched with `get_design_context`
- [x] Figma Make screenshot limitation recorded
- [x] Source precedence recorded
- [x] Canva lane constrained to reference planning
- [x] Runtime implementation explicitly deferred
- [x] Follow-up PR order recorded

## Required Local Gates

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
python3 scripts/design_guard.py --manifest docs/design/figma-manifest.json
pre-commit run --all-files
```

## Merge-Readiness Gate

No merge-ready claim is allowed until normal repo gates pass, including
`make verify`, unless an operator-approved machine-heavy exception is documented
in the PR body and review mapping.

## Heavy Gate Deferral

On 2026-04-30, `make verify` was started and passed:

- `verify-env`
- `flake8`
- `mypy`
- `tests/edges tests/test_remaining_modules.py`

The full coverage/diff-cover portion was stopped by operator instruction to
avoid local CPU overload. This lane may open as draft with narrow gate evidence,
but it must not be claimed merge-ready from the interrupted `make verify` run.

## Out Of Scope Confirmed

- [x] No backend changes
- [x] No web runtime changes
- [x] No iOS runtime changes
- [x] No Figma writes
- [x] No Canva generation or publishing
- [x] No Code Connect activation
