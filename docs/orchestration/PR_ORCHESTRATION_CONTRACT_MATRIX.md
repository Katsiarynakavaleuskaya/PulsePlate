# PR Orchestration Contract Matrix

Canonical reference for PR governance. Single source of truth to reduce drift between scripts, AGENTS, PR body expectations, and CI checks.

## 1. Purpose

- Define canonical orchestration contract for PR governance
- Remove drift between scripts, AGENTS, PR body expectations, CI checks
- Document mergeability rules

## 2. Source-of-Truth Hierarchy

| Level | Artifact                                | Role                           |
| ----- | --------------------------------------- | ------------------------------ |
| 1     | Git commit SHA                          | canonical repo state           |
| 2     | Repository files                        | canonical governance artifacts |
| 2a    | `docs/review/PR_<N>_FIXED_MAPPING.md`    | Fixed in Commit Mapping SoT    |
| 3     | Latest CI run for current HEAD          | merge decision                 |
| 4     | PR body                                 | human-readable mirror only     |

Evidence: Level 2 — this doc + `AGENTS.md`; Level 2a — `scripts/orchestration/review_mapping_artifact.py`, `scripts/ci/check_pr_body_phase2_gates.py`, `scripts/ci/check_pr_merge_readiness.py`, `scripts/orchestration/check_review_threads_disposition.py`; Level 4 — PR body mirror.

## 3. Governance Phases

| Phase   | Gate              | Artifact                                | Blocks Merge |
| ------- | ----------------- | --------------------------------------- | ------------ |
| Phase 1 | CI hygiene        | workflows/checks                        | yes          |
| Phase 2 | PR body contract  | PR body                                 | yes          |
| Phase 3 | Merge readiness   | unresolved threads + actionable mapping | yes          |
| Phase 4 | Disposition proof | script semantics                        | yes          |

## 4. Phase 2 Contract (Canonical Artifact)

Canonical source: `docs/review/PR_<N>_FIXED_MAPPING.md`. PR body is mirror/fallback.

Required sections in artifact:

- `## Discussion Thread Pass`
- Checkbox contract (completed / mapping completed)
- `## Fixed in Commit Mapping`

Valid mapping forms:

- `- <url> -> <sha>`
- `- No actionable review comments`

Evidence: `scripts/orchestration/review_mapping_artifact.py` (read, extract, validate), `scripts/ci/check_pr_body_phase2_gates.py` (artifact-first when pr_number from event).

## 5. Merge Readiness Contract

- Unresolved review threads must be zero
- Actionable bot comments must be mapped
- Cancelled/stale runs do not define mergeability

Evidence: `scripts/ci/check_pr_merge_readiness.py:1` (gate purpose), `:123` (unresolved threads), `:207` (actionable items), `:337` (unresolved check), `:350` (actionable mapping check), `:355` (mapped_urls).

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

Evidence: `scripts/orchestration/check_review_threads_disposition.py:27` (DISPOSITION_RE), `:232` (FIXED mapping check), `AGENTS.md:46` (FIXED), `:63` (NOT-A-BUG), `:80` (DEFERRED).

## 7. Trigger-only Commit Ban

- Empty commit = invalid FIXED proof
- Rerun/trigger subject = invalid FIXED proof

Evidence: `scripts/orchestration/check_review_threads_disposition.py:175` (trigger-only validation), `:188` (invalid proof error), `:518` (mapping ban), `AGENTS.md:103` (trigger-only ban).

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

Evidence: enforced via workflow `required` status; `scripts/ci/check_pr_merge_readiness.py` (hard gate), `scripts/ci/check_pr_body_phase2_gates.py` (Phase 2 hard gate).

## 10. Review Thread Lifecycle

```text
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

Evidence: `scripts/orchestration/check_review_threads_disposition.py:8` (GH_TOKEN canonical), `:50` (shutil.which for gh), `:106` (shutil.which for git), `:411` (GH_TOKEN preflight), `AGENTS.md:110` (Bandit/nosec policy, subprocess).

## 12. Roadmap / Future Hardening

- ~~Move Fixed Mapping SoT from PR body to repo file~~ ✅ Done (PR-TBD)
- Stabilize allowlist keys
- AST subprocess guard
- Path-aware trigger proof
