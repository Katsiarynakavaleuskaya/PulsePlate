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
- required `## Experiment Runner Evidence` in the PR body mirror or canonical artifact:
  non-trivial PRs must include an oracle-only artifact by default, and
  `Not applicable` requires an explicit coordinator/operator reason

Canonical runtime behavior is artifact-first when `pr_number` is available.
PR-body parsing is a temporary compatibility seam for local/body-only checks and human-readable review context. When `pr_number` is available, Phase 2 treats the artifact as authoritative and the PR body as an optional mirror-only surface.

Temporary seam tracking:

- ADR: `docs/architecture/ADR_FIXED_MAPPING_PR_BODY_FALLBACK_SEAM_2026-03-07.md`
- Backlog: `docs/roadmap/BACKLOG_LEDGER.md:186`

Exit criteria for removing PR-body fallback:

1. CI/event paths always provide `pr_number` for Phase 2 and merge-readiness flows.
2. Local tooling supports deterministic artifact lookup without PR-body parsing.
3. The fallback branch in `scripts/ci/check_pr_body_phase2_gates.py` can be removed without losing local validation ergonomics.

Phase 2 sections and required orchestration evidence:

- `## Discussion Thread Pass`
- Checkbox contract (completed / mapping completed)
- `## Fixed in Commit Mapping` in the canonical artifact
- `### Fixed in Commit Mapping` in the optional PR-body mirror
- Required `## Experiment Runner Evidence` with `Artifact: artifacts/orchestration/experiments/results/<id>.json` or `Not applicable: <reason>` in either the PR body mirror or canonical artifact. Non-trivial PRs must create oracle-only evidence by default; local artifact load/write failures are infrastructure blockers and are not valid `Not applicable` reasons. Malformed evidence is rejected.
- Required premortem evidence for non-trivial PRs: `pulseplate-premortem-risk-review`
  must run against the actual diff before PR open, and every finding must be
  `FIXED`, `NOT-A-BUG`, or `DEFERRED` with evidence/backlog proof.
- Required bootstrap role-agent evidence: `task_bootstrap.py` packet creation
  does not execute roles. The packet/runbook-declared role order must be run in
  order before implementation or before the phase it governs; missing role
  execution blocks readiness unless `agent-coordinator` records an explicit
  disposition with evidence.

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
- PR lifecycle packets may distinguish `post_open_review` from `merge_ready`,
  but both phases still use current-head truth and the canonical artifact
  `docs/review/PR_<N>_FIXED_MAPPING.md`
- `post_open_review` is the packet-level phase where the canonical
  `qa-engineer-agent -> bug-hunter -> security-auditor` lane is synthesized,
  with Codex Security diff scan / finding discovery as the plugin scan that
  follows role review; `merge_ready` keeps the current-head merge-wrapper
  contract explicit without widening the review lane

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
- `gh pr checks <PR_NUMBER>` is diagnostic only; a non-zero exit can mean live
  `pending`/`in_progress` required jobs, not failed current-head checks
- When only one current-head job remains live, inspect the exact run/job with
  `gh run view <RUN_ID>` or `gh run view --job=<JOB_ID>` before calling the PR
  red or green

## 9. CI Check Classification

| Class     | Meaning                   | Blocks Merge                |
| --------- | ------------------------- | --------------------------- |
| Hard gate | canonical merge blocker   | yes                         |
| Soft gate | advisory quality signal   | no                          |
| External  | third-party review signal | only if explicitly required |

Canonical lane matrix:

| Lane        | Command / Surface | Class | Blocking Rule |
| ----------- | ----------------- | ----- | ------------- |
| Local       | `pre-commit run --all-files` | Hard gate | Must pass before push; hook modifications must be committed |
| Local       | `make verify` | Hard gate | Canonical code-quality bundle for merge claims |
| Local / PR process | `task_bootstrap.py` role-agent dispatch | Hard gate | Packet creation is not execution; every bootstrap/runbook assigned role must run in declared order or carry an explicit coordinator disposition with evidence |
| Local / PR process | `pulseplate-premortem-risk-review` | Hard gate | Every non-trivial PR must run premortem on the actual diff before PR open; findings require FIXED / NOT-A-BUG / DEFERRED evidence |
| Local / PR process | Experiment Runner oracle evidence | Hard gate | Every non-trivial PR must create oracle-only evidence by default; artifact load/write failures are infrastructure blockers, and material contribution requires governed attribution |
| Post-open review | `qa-engineer-agent -> bug-hunter -> security-auditor` plus Codex Security | Hard gate | Role passes and Codex Security diff scan / finding discovery must complete; any finding must be fixed or dispositioned before merge-readiness claims |
| Local / PR CI | Operator-approved machine-heavy deferral | Hard gate | Local `make verify` may be deferred only when PR body and fixed mapping document the deferral, PR-scoped narrow gates pass, canonical current-head CI parity is green (`lint`, required/current-head checks for the touched PR surface, relevant `test-main` matrix, `diff-coverage` ≥97%, applicable security/governance checks), and the strict merge wrapper passes |
| Local / CI  | `python scripts/orchestration/check_merge_ready.py ...` | Hard gate | Wrapper must pass Phase 2 + review governance + current-head required checks + disposition proof |
| PR CI       | GitHub branch-protection required checks on current HEAD | Hard gate | Pending/failed current-head required jobs block merge |
| PR CI       | Non-required jobs / informational workflows | Soft gate | Visible signal only; fix or ledger if risk is real |
| Release ops | App Store / Fastlane validation lanes | Hard gate for release, not PR merge by default | Must pass before upload/publish claims; may be out-of-scope for code-only PR merge |
| External    | CodeRabbit / Sourcery / Cubic / similar bots | External | Advisory unless GitHub explicitly marks them required |

Current repo workflow inventory (Tier 1 post-PR2 state):

| Workflow / Surface | Lane | Class | Default Merge Effect | Tier 1 status |
| ------------------ | ---- | ----- | -------------------- | ------------- |
| `.github/workflows/ci.yml` (`CI`) | Backend / shared PR lane | Hard gate | Sole canonical backend/shared PR workflow for merge claims; current-head required jobs from this lane block merge when branch protection requires them | Canonical backend/shared PR lane |
| `.github/workflows/ci.yml` (`lint`, `security`, `diff-coverage`) | Backend / shared PR lane | Hard gate | Canonical lint, PR-time security, and diff coverage live inside `CI`; failures block merge when attached to current HEAD | Canonical enforcement surface |
| `.github/workflows/ci.yml` (`OpenAPI sync`, docs gates, merge-readiness, review governance) | Backend / shared PR lane | Hard gate | Blocks merge when the corresponding job is required on current HEAD | Canonical governance surface |
| `.github/workflows/pr-tests.yml` (`PR Tests (Fast)`) | Archived / non-canonical | No current PR lane | Retired as an active PR lane after PR2; keep only as historical reference if the file still exists in branch history | Removed as active PR lane |
| `.github/workflows/pr-coverage.yml` (`PR Coverage Guard`) | Archived / non-canonical | No current PR lane | Retired as an active PR lane after PR2; keep only as historical reference if the file still exists in branch history | Removed as active PR lane |
| `.github/workflows/security.yml` (`Security Scan`) | Scheduled / manual security audit lane | Soft gate | Advisory deep-audit lane outside ordinary PR merge truth; findings still require fix-first engineering response when the surface is in scope | Demoted out of PR-time blocking path |
| `.github/workflows/trivy.yml` (`trivy`) | Scheduled / manual image-security lane | Soft gate | Internal image-security reporting lane that stays outside ordinary PR merge truth unless branch protection explicitly promotes it elsewhere | Demoted out of PR-time blocking path |
| `.github/workflows/frontend-ci.yml` (`Frontend CI`) | Frontend specialized lane | Hard gate when attached | Blocks merge only for frontend/design-token/OpenAPI-sync surfaces when attached by path or required checks | Specialized add-on lane |
| `.github/workflows/accessibility.yml` (`Accessibility Tests`) | Frontend specialized lane | Soft gate by default | Advisory frontend quality signal unless branch protection requires it | Specialized add-on lane |
| `.github/workflows/ci.yml` (`iOS unit tests`, `iOS UI smoke`) | iOS specialized lane | Hard gate when attached | Blocks merge for iOS / workflow-change surfaces when attached; note current path router also attaches on `.github/workflows/**` and `.github/actions/**` changes | Specialized add-on lane with current workflow-change coupling |
| `.github/workflows/greenlight-ios.yml` (`Greenlight iOS Preflight`) | iOS specialized lane | Soft gate | Report-only preflight (`GREENLIGHT_BLOCKING=false`) | Advisory iOS lane |
| `.github/workflows/build.yml` (`Docker Build and Push`) | Release / image lifecycle lane | Hard gate for release / image claims, not ordinary PR merge by default | Required before publish/image assertions; ordinary code-only PRs treat it as release-ops | Specialized release lane retained in PR2+ |

Bot governance distinction (Tier 1 baseline):

- Third-party bot **status checks** remain `External` and advisory unless GitHub marks them required.
- Third-party or first-party bot **review comments** remain merge-blocking when they contain actionable items, because review governance/disposition policy is separate from status-check classification.
- Contributors must use `CI` as the canonical backend/shared PR lane for operator decisions; `pr-tests.yml` and `pr-coverage.yml` are no longer active PR lanes, and `security.yml` plus `trivy.yml` are scheduled/manual non-PR security lanes.
- Canonical backend/shared PR merge truth does not imply that all other PR-triggered workflows disappear. Specialized repo-level workflows such as `Frontend CI`, `CodeQL Advanced`, and Docker/image lanes may still appear on workflow/governance PRs, but they remain non-canonical unless GitHub branch protection explicitly requires them.

Evidence:
- `scripts/ci/check_pr_merge_readiness.py:349`
- `scripts/ci/check_pr_merge_readiness.py:400`
- `scripts/ci/check_current_head_pr_checks.py:406`
- `scripts/orchestration/check_merge_ready.py:1`
- `scripts/ci/check_pr_body_phase2_gates.py:162`
- `scripts/ci/check_pr_body_phase2_gates.py:182`
- `.github/workflows/ci.yml:1`
- `.github/workflows/ci.yml:31`
- `.github/workflows/ci.yml:292`
- `.github/workflows/ci.yml:311`
- `.github/workflows/ci.yml:333`
- `.github/workflows/ci.yml:841`
- `.github/workflows/security.yml:2`
- `.github/workflows/security.yml:47`
- `.github/workflows/trivy.yml:6`
- `.github/workflows/trivy.yml:56`
- `.github/workflows/frontend-ci.yml:1`
- `.github/workflows/accessibility.yml:1`
- `.github/workflows/build.yml:1`
- `.github/workflows/build.yml:221`
- `.github/workflows/greenlight-ios.yml:2`
- `.github/workflows/greenlight-ios.yml:24`

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

## 14. Stacked PR Replacement Rule

- If a stacked child PR auto-closes because its parent base branch was merged
  and deleted, the child review lane is no longer active
- Operators must create a new branch from `origin/main`, cherry-pick the child
  commits, rerun local gates, and open a replacement PR on `main`
- Replacement PR must get a new canonical artifact path:
  `docs/review/PR_<NEW_NUMBER>_FIXED_MAPPING.md`
- Do not continue mapping/reviewing against the auto-closed PR number
