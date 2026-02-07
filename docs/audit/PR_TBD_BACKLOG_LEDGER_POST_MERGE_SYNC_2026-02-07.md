# PR-TBD Audit — BACKLOG_LEDGER post-merge sync (PR-673, PR-674)

**Date**: 7 February 2026
**PR**: TBD (GitHub PR number is source of truth)
**Branch**: `docs/ledger-sync-post-merge-pr-676` (legacy slot name; PR# is SoT)
**Type**: Docs-only

## Summary

Update `docs/roadmap/BACKLOG_LEDGER.md` to reflect repo-truth after two merged runtime PRs:

- PR #673 — iOS: Mount WeeklyPlanReader behind feature flag
- PR #674 — iOS: Wire soft paywall CTA to real paywall router

## Repo-truth evidence (GitHub)

```json
{"mergedAt":"2026-02-07T17:41:01Z","number":673,"state":"MERGED","title":"feat(ios): mount WeeklyPlanReader behind feature flag","url":"https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/673"}
{"mergedAt":"2026-02-07T18:33:27Z","number":674,"state":"MERGED","title":"feat(ios): wire soft paywall CTA to paywall router","url":"https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/674"}
```

## Changes

### 1) Mark PR-673 backlog item as merged

- Evidence: `docs/roadmap/BACKLOG_LEDGER.md:504-520`

### 2) Mark PR-674 backlog item as merged

- Evidence: `docs/roadmap/BACKLOG_LEDGER.md:869-881`

## Docs-only enforcement

```bash
git diff --name-only origin/main...HEAD | rg -v "\.md$"
```

Output:

```text

```

Exit code: 1
