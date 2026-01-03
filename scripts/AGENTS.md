# Agent instructions (scope: scripts/ and subdirectories)

## Scope and layout
- This AGENTS.md applies to: `scripts/` and below.
- Scripts are repo automation utilities; run from repo root.

## Conventions
- Treat scripts as production automation: avoid breaking flags or outputs.
- Prefer small, focused edits; update any dependent docs or Make targets if needed.
- Avoid adding network calls to scripts used in CI unless explicitly required.

## Pre-push backend tests (smart diff runner)

The `run-backend-tests-pre-commit.sh` script is used by pre-commit framework to run backend pytest only when Python files changed.

**Change detection order:**
1. If upstream exists: diff `upstream..HEAD`
2. Else: diff from merge-base against (origin/main|origin/master|main|master)
3. If base cannot be resolved: fallback to last N commits (diagnostic mode)

**Debug mode:**
- Set `PREPUSH_DEBUG=1` to print resolved upstream/base and file list
- Example: `PREPUSH_DEBUG=1 git push` will show detailed change detection info

**Skip tests:**
- Set `SKIP_TESTS=1` to bypass backend tests (useful for documentation-only commits)
