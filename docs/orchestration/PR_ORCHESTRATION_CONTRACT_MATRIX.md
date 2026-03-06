# PR Orchestration Contract Matrix

Canonical reference for PR governance. Single source of truth to reduce drift between scripts, AGENTS, PR body expectations, and CI checks.

## 1. Purpose

- Define canonical orchestration contract for PR governance
- Remove drift between scripts, AGENTS, PR body expectations, CI checks
- Document mergeability rules

## 2. Source-of-Truth Hierarchy

| Level | Artifact                       | Role                           |
| ----- | ------------------------------ | ------------------------------ |
| 1     | Git commit SHA                 | canonical repo state           |
| 2     | Repository files               | canonical governance artifacts |
| 3     | Latest CI run for current HEAD | merge decision                 |
| 4     | PR body                        | human-readable mirror only     |

## 3. Governance Phases

| Phase   | Gate              | Artifact                                | Blocks Merge |
| ------- | ----------------- | --------------------------------------- | ------------ |
| Phase 1 | CI hygiene        | workflows/checks                        | yes          |
| Phase 2 | PR body contract  | PR body                                 | yes          |
| Phase 3 | Merge readiness   | unresolved threads + actionable mapping | yes          |
| Phase 4 | Disposition proof | script semantics                        | yes          |

## 4. Phase 2 PR Body Contract

Required sections:

- `## Discussion Thread Pass`
- Checkbox contract (completed / mapping completed)
- `### Fixed in Commit Mapping`

Valid mapping forms:

- `- <url> -> <sha>`
- `- No actionable review comments`

## 5. Merge Readiness Contract

- Unresolved review threads must be zero
- Actionable bot comments must be mapped
- Cancelled/stale runs do not define mergeability

## 6. FIXED / NOT-A-BUG / DEFERRED Semantics

### FIXED

- Requires commit proof
- SHA must be valid
- Commit must not be trigger-only
- Commit-after-comment applies

### NOT-A-BUG

- Requires written reasoning/evidence
- No commit proof required

### DEFERRED

- Requires ledger reference
- No commit proof required

## 7. Trigger-only Commit Ban

- Empty commit = invalid FIXED proof
- Rerun/trigger subject = invalid FIXED proof

## 8. Required-check Truth

- Mergeability is decided by the **latest required checks for current HEAD only**
- Ignore cancelled runs
- Ignore stale runs
- External review tools do not block unless explicitly required

## 9. CI Check Classification

| Class     | Meaning                   | Blocks Merge                |
| --------- | ------------------------- | --------------------------- |
| Hard gate | canonical merge blocker   | yes                         |
| Soft gate | advisory quality signal   | no                          |
| External  | third-party review signal | only if explicitly required |

## 10. Review Thread Lifecycle

```
OPEN
→ FIXED / NOT-A-BUG / DEFERRED
→ RESOLVED
→ MERGE READINESS PASS
```

## 11. Security Invariants for Orchestration Scripts

- `GH_TOKEN` preflight
- Absolute binaries via `shutil.which()`
- Subprocess guard
- No blind `# nosec`
- Allowlist discipline

## 12. Roadmap / Future Hardening

- Move Fixed Mapping SoT from PR body to repo file
- Stabilize allowlist keys
- AST subprocess guard
- Path-aware trigger proof
