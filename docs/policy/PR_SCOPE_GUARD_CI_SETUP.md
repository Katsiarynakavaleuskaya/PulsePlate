# PR Scope Guard CI Setup

**Status:** Mandatory
**Last updated:** 2026-01-08
**Applies to:** CI configuration

---

## Context

`scripts/ci/pr_scope_guard.sh` enforces PR scope rules (prevents PR-494-style bloat).
Must run as fail-fast check in CI before tests.

---

## Solution

Add separate `pr_scope_guard` job that runs first and blocks other jobs on violation.

**Patch (applied to `.github/workflows/ci.yml` and `.github/workflows/pr-tests.yml`):**

```yaml
jobs:
  pr_scope_guard:
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    timeout-minutes: 2
    steps:
      - name: Checkout
        uses: actions/checkout@<version>
        with:
          fetch-depth: 0

      - name: PR Scope Guard
        run: bash scripts/ci/pr_scope_guard.sh

  lint:
    needs: pr_scope_guard
    ...
```

**Dependencies:** Other PR jobs must declare `needs: pr_scope_guard`.

---

## Done Criteria

- ✅ PR checks show `pr_scope_guard` job
- ✅ Runtime PR with `docs/pr/*_ROADMAP.md` fails immediately
- ✅ Runtime PR with `docs/pr/*.py` fails immediately
- ✅ Docs-only PRs not affected (guard skips non-PR contexts)

---

## Local Test

```bash
bash scripts/ci/pr_scope_guard.sh
```

Expected: exit code `0` (ok) or `1` (blocked).

---

## Reference

- **PR Scope Rules:** [`PR_SCOPE_RULES.md`](./PR_SCOPE_RULES.md)
- **Guard Script:** [`../../scripts/ci/pr_scope_guard.sh`](../../scripts/ci/pr_scope_guard.sh)
