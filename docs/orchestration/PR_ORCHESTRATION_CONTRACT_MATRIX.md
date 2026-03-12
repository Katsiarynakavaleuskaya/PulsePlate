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

Evidence:
- Level 2: `AGENTS.md:39`, `AGENTS.md:102`, `AGENTS.md:103`, `AGENTS.md:434`, `AGENTS.md:435`
- Level 2a: `scripts/orchestration/review_mapping_artifact.py:24`, `scripts/orchestration/review_mapping_artifact.py:84`, `scripts/orchestration/review_mapping_artifact.py:110`
- Level 3: `scripts/ci/check_pr_merge_readiness.py:349`, `scripts/ci/check_pr_merge_readiness.py:369`, `scripts/ci/check_pr_merge_readiness.py:400`
- Level 4: `scripts/ci/check_pr_body_phase2_gates.py:162`, `scripts/ci/check_pr_body_phase2_gates.py:182`

## 3. Governance Phases

| Phase   | Gate                    | Artifact                                                         | Blocks Merge |
| ------- | ----------------------- | ---------------------------------------------------------------- | ------------ |
| Phase 1 | CI hygiene              | workflows/checks                                                 | yes          |
| Phase 2 | artifact-first contract | canonical artifact (authoritative) + optional PR body mirror     | yes          |
| Phase 3 | Merge readiness         | unresolved threads + actionable mapping                          | yes          |
| Phase 4 | Disposition proof       | script semantics                                                 | yes          |

Canonical operator entrypoint:

- `scripts/orchestration/check_merge_ready.py` runs Phase 2, merge-readiness, and disposition proof as one verdict.
- Underlying gate scripts remain authoritative for their own contract semantics.

## 4. Phase 2 Contract (Canonical Artifact)

Canonical source: `docs/review/PR_<N>_FIXED_MAPPING.md`.

PR body **may mirror** the same review-governance sections for human review and fallback runs:

- `## Discussion Thread Pass`
- `### Fixed in Commit Mapping`
- completed checkboxes matching the artifact
- full URL→SHA mapping lines are required only in the canonical artifact when `pr_number` is available

Canonical runtime behavior is artifact-first when `pr_number` is available.
PR-body parsing is a temporary compatibility seam for local/body-only checks and human-readable review context. When `pr_number` is available, Phase 2 treats the artifact as authoritative and the PR body as an optional mirror-only surface.

Temporary seam tracking:

- ADR: `docs/architecture/ADR_FIXED_MAPPING_PR_BODY_FALLBACK_SEAM_2026-03-07.md`
- Backlog: `docs/roadmap/BACKLOG_LEDGER.md:186`

Exit criteria for removing PR-body fallback:

1. CI/event paths always provide `pr_number` for Phase 2 and merge-readiness flows.
2. Local tooling supports deterministic artifact lookup without PR-body parsing.
3. The fallback branch in `scripts/ci/check_pr_body_phase2_gates.py` can be removed without losing local validation ergonomics.

Required sections:

- `## Discussion Thread Pass`
- Checkbox contract (completed / mapping completed)
- `## Fixed in Commit Mapping` in the canonical artifact
- `### Fixed in Commit Mapping` in the optional PR-body mirror

Valid mapping forms in the canonical artifact:

- `- <url> -> <sha>`
- `- <url>`
- `- No actionable review comments`

PR body mirror requires the section headings and completed checkboxes only when the mirror is present. Mapping-line duplication in the body is optional once the canonical artifact exists. Use `render_phase2_body_mirror()` to generate the mirror block from the canonical artifact path.

Evidence:
- `scripts/orchestration/review_mapping_artifact.py:44`
- `scripts/orchestration/review_mapping_artifact.py:84`
- `scripts/orchestration/review_mapping_artifact.py:110`
- `scripts/ci/check_pr_body_phase2_gates.py:162`
- `scripts/ci/check_pr_body_phase2_gates.py:169`
- `scripts/ci/check_pr_body_phase2_gates.py:182`
- `docs/architecture/ADR_FIXED_MAPPING_PR_BODY_FALLBACK_SEAM_2026-03-07.md:1`
- `docs/roadmap/BACKLOG_LEDGER.md:186`

Artifact-only governance findings are fixed in the canonical artifact itself, but the proof block must still cite the validator/runtime enforcement that makes the artifact contract merge-blocking.

## 5. Merge Readiness Contract

- Unresolved review threads must be zero
- Actionable bot comments must be mapped
- Cancelled/stale runs do not define mergeability

Evidence:
- `scripts/ci/check_pr_merge_readiness.py:1`
- `scripts/ci/check_pr_merge_readiness.py:135`
- `scripts/ci/check_pr_merge_readiness.py:219`
- `scripts/ci/check_pr_merge_readiness.py:349`
- `scripts/ci/check_pr_merge_readiness.py:369`
- `scripts/ci/check_pr_merge_readiness.py:383`

## 6. FIXED / NOT-A-BUG / DEFERRED Semantics

### FIXED

- Requires commit proof
- SHA must be valid
- Commit must not be trigger-only
- Commit-after-comment applies

### NOT-A-BUG

- Requires written reasoning/evidence
- Thread URL must still be listed in Fixed in Commit Mapping
- No commit proof required

### DEFERRED

- Requires ledger reference
- Thread URL must still be listed in Fixed in Commit Mapping
- No commit proof required

Evidence:
- `scripts/orchestration/check_review_threads_disposition.py:38`
- `scripts/orchestration/check_review_threads_disposition.py:298`
- `scripts/orchestration/check_review_threads_disposition.py:467`
- `AGENTS.md:47`
- `AGENTS.md:64`
- `AGENTS.md:81`

## 7. Trigger-only Commit Ban

- Empty commit = invalid FIXED proof
- Rerun/trigger subject = invalid FIXED proof

Evidence:
- `scripts/orchestration/check_review_threads_disposition.py:181`
- `scripts/orchestration/check_review_threads_disposition.py:197`
- `scripts/orchestration/check_review_threads_disposition.py:528`
- `AGENTS.md:103`

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

Evidence:
- `scripts/ci/check_pr_merge_readiness.py:349`
- `scripts/ci/check_pr_merge_readiness.py:400`
- `scripts/ci/check_pr_body_phase2_gates.py:162`
- `scripts/ci/check_pr_body_phase2_gates.py:182`

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

Evidence:
- `scripts/orchestration/check_review_threads_disposition.py:8`
- `scripts/orchestration/check_review_threads_disposition.py:60`
- `scripts/orchestration/check_review_threads_disposition.py:117`
- `scripts/orchestration/check_review_threads_disposition.py:394`
- `AGENTS.md:120`

## 12. Auth Mode Semantics

- **Local default / advisory:** disposition guard may skip when no usable `gh` auth is available.
- **Local strict parity:** `--require-auth` upgrades the disposition guard to CI-like behavior and requires `GH_TOKEN`.
- **CI strict:** `CI=true` requires `GH_TOKEN` and `gh auth status` before any GraphQL.
- `GITHUB_TOKEN` remains the merge-readiness sub-gate token; `GH_TOKEN` is the canonical disposition/GraphQL token.
- Advisory `SKIP` is not merge evidence; operators must use enforced mode before claiming strict local parity.

Evidence:
- `AGENTS.md:120`
- `RUNBOOK_AGENT.md:246`
- `docs/orchestration/COORDINATOR_MERGE_READINESS_RULES.md:45`
- `scripts/orchestration/check_review_threads_disposition.py:9`
- `scripts/orchestration/check_review_threads_disposition.py:623`
- `scripts/ci/check_pr_merge_readiness.py:308`

## 13. Roadmap / Future Hardening

- ~~Move Fixed Mapping SoT from PR body to repo file~~ ✅ Merged via PR #998 on 2026-03-07
- Stabilize allowlist keys
- AST subprocess guard
- Path-aware trigger proof
