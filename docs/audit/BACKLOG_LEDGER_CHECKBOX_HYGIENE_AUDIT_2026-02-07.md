# Backlog Ledger Checkbox Hygiene Audit — PR-671

**Date**: 7 February 2026
**Branch**: `docs/ledger-hygiene-pr-671`
**Type**: docs-only

---

## Problem statement

After merging PR-669, the canonical backlog ledger entries for the iOS docs-drift items were still marked as
“in progress” (`[ ]`) and used a placeholder “This docs drift PR”.

Additionally, an older P1 item showed `Status: ✅ Merged (PR #644)` but the checkbox was still `[ ]`,
which is a ledger drift signal.

This PR is a **docs-only** hygiene update to bring `docs/roadmap/BACKLOG_LEDGER.md` back in sync with
repo-truth (PR links + checkbox state).

---

## Evidence (repo-truth)

### PR-669 exists (merged)

```bash
gh pr view 669 --json number,state,mergedAt,url --jq '{number:.number,state:.state,mergedAt:.mergedAt,url:.url}'
```

Raw stdout (truncated):

```json
{"mergedAt":"2026-02-07T10:27:40Z","number":669,"state":"MERGED","url":"https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/669"}
```

Exit code: 0

### BACKLOG_LEDGER entries updated to `[x]` and point to PR-669

```bash
rg -n "Docs: Canonicalize iOS API integration guide|Docs: Refresh iOS roadmap" docs/roadmap/BACKLOG_LEDGER.md
```

Raw stdout (truncated):

```text
91:- [x] Docs: Canonicalize iOS API integration guide to current Networking SoT
106:- [x] Docs: Refresh iOS roadmap to AS-IS / NEXT ACTIONS (repo-truth)
```

Exit code: 0

### PR-644 checkbox drift fixed

```bash
rg -n "Extract hardcoded constants \\(BMR, export formats\\)" docs/roadmap/BACKLOG_LEDGER.md
```

Raw stdout:

```text
408:- [x] P1: Extract hardcoded constants (BMR, export formats)
```

Exit code: 0

---

## Changes in this PR

- Marked the two iOS docs-drift items as **merged** (`[x]`) and linked them to **PR-669**.
- Fixed the checkbox for the already-merged PR-644 item (`[ ]` → `[x]`).

---

## Docs-only enforcement

```bash
git diff --name-only origin/main...HEAD | rg -v "\.md$"

# Exit code: 1
```
