# Pre-commit baseline policy: detect-secrets

## Why `.secrets.baseline` can change unexpectedly

The `detect-secrets` pre-commit hook may update `.secrets.baseline` to keep line numbers in sync
after code changes. In some cases, this update can occur during a non-hook-focused commit.

## Policy (canonical)

- Prefer committing `.secrets.baseline` updates in a **separate commit**:
  `chore(pre-commit): update .secrets.baseline`
- If a baseline update accidentally lands inside a feature/fix commit, add an explicit follow-up note
  in the PR history and ensure future PRs stage + commit the baseline **first**.
