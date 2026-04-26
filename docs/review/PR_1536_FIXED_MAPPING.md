# PR #1536 Fixed Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1536>
Branch: `dependabot/pip/dev-tools-cc73f56f53`
Date: 2026-04-26

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

No actionable review comments were raised.

## Fixed in Commit Mapping

- No actionable review comments
- Dependency install resolution recovery:
  - CI resolver could not install `pre-commit==4.6.0` from the controlled index with existing `--only-binary :all:` constraints.
  - Reverted `pre-commit` pins in all touched dependency files to `4.5.1` to restore CI determinism:
    - `requirements-dev.in`: `pre-commit~=4.6.0` → `pre-commit~=4.5.1`
    - `requirements-ci-lite.in`: `pre-commit~=4.6.0` → `pre-commit~=4.5.1`
    - `requirements-dev.txt`: `pre-commit==4.6.0` → `pre-commit==4.5.1`
    - `requirements-ci-lite.txt`: `pre-commit==4.6.0` → `pre-commit==4.5.1`
    - `requirements-all.txt`: `pre-commit>=4.6.0` → `pre-commit>=4.5.1`
  - Commit: `3774016b4`
- Evidence: `gh pr checks 1536` failure logs (installation conflict for pre-commit 4.6.0), then `make validate-changed`/`make test-fast` pass in lane commit.

## Initial Evidence

- `python3 scripts/orchestration/check_preflight.py` (PASS)
- `python3 scripts/orchestration/check_agent_consistency.py` (PASS)
- `make validate-changed` (PASS)
- `make test-fast` (PASS)
- `pre-commit run --all-files` (PASS)
