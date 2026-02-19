# PR Canonical Matrix Checklist

## Purpose

Single operational checklist so context is never lost during PR execution.

## Canonical Flow (Strict Order)

1. Matrix and scope lock
   - Define IN/OUT scope.
   - Confirm work package type (runtime/docs/security/etc.).
   - Start with coordinator-first routing.
2. Audit and brainstorming
   - Quick audit of touched surfaces and risks.
   - Brainstorm alternatives, choose one path, record rationale.
3. Plan and implementation
   - Create concrete step plan.
   - Implement in narrow scope only.
4. Local quality gates
   - Run relevant tests/lint/build for changed scope.
   - Fix failures before commit.
5. Commits and PR creation
   - Logical commits with canonical messages.
   - Open PR with required body sections and mapping.
6. Online CI watch
   - Monitor checks until stable pass.
   - Rerun only when transient failures are confirmed.
7. Bot and review loop
   - Answer all actionable bot comments (CodeRabbit/Sourcery/etc.).
   - Resolve all review threads.
8. Merge gate
   - Merge only when:
     - required CI is green,
     - no unresolved review threads,
     - no actionable bot comments remain.
9. Post-merge closure
   - Update backlog ledger for deferred/completed items.
   - Add follow-up docs-only ledger closure PR when policy requires.

## Hard Merge Conditions

- No unresolved review threads.
- Required checks are PASS.
- No unaddressed actionable bot comments.
- PR scope stays within declared matrix.

## Operator Notes

- Never skip matrix/audit/plan stages.
- Never mark "ready" before full gate closure.
- If context drifts, return to this checklist and restart at step 1.
