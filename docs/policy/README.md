# Policy (Rules & Invariants)

This folder contains project-level rules. If a change conflicts with a policy doc, you must explain why and how risk is mitigated.

## Start here
- [`../ENGINEERING_LESSONS.md`](../ENGINEERING_LESSONS.md) — hard-won invariants and lessons
- [`../TEST_SKIP_XFAIL_POLICY.md`](../TEST_SKIP_XFAIL_POLICY.md) — xfail/skip discipline and CI expectations

## Mandatory policies
- [`DOCS_ONLY_PR_POLICY.md`](DOCS_ONLY_PR_POLICY.md) — strict separation of docs-only PRs from code changes
- [`PR_SCOPE_RULES.md`](PR_SCOPE_RULES.md) — runtime vs docs separation, PR size guidelines, contract validation

## Typical contents
- Import hygiene rules (no sys.modules mutation, no dynamic imports except allowed)
- One-source-of-truth policies (e.g., canonical engines)
- Test determinism requirements
- PR governance (docs-only, code review standards)

## When to update
Update policy docs only when the team explicitly agrees on a rule change (decision recorded in PR description or ADR).
