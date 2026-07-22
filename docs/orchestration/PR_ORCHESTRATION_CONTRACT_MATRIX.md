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
| 4     | PR body                                 | summary + artifact link        |

Evidence:
- Level 2: `AGENTS.md:39`, `AGENTS.md:102`, `AGENTS.md:103`, `AGENTS.md:434`, `AGENTS.md:435`
- Level 2a: `scripts/orchestration/review_mapping_artifact.py:24`, `scripts/orchestration/review_mapping_artifact.py:84`, `scripts/orchestration/review_mapping_artifact.py:110`
- Level 3: `scripts/ci/check_pr_merge_readiness.py:349`, `scripts/ci/check_pr_merge_readiness.py:369`, `scripts/ci/check_pr_merge_readiness.py:400`
- Level 4: `scripts/ci/check_pr_body_phase2_gates.py:162`, `scripts/ci/check_pr_body_phase2_gates.py:182`

## 3. Governance Phases

| Phase   | Gate                    | Artifact                                                         | Blocks Merge |
| ------- | ----------------------- | ---------------------------------------------------------------- | ------------ |
| Phase 1 | CI hygiene              | workflows/checks                                                 | yes          |
| Phase 2 | artifact-first contract | canonical artifact (authoritative) + PR body link                | yes          |
| Phase 2b | pre-closeout validation | uncommitted artifact + live bot inventory + true Markdown link | blocks closeout commit |
| Phase 3 | Merge readiness         | unresolved threads + actionable mapping                          | yes          |
| Phase 4 | Disposition proof       | script semantics                                                 | yes          |

Canonical operator entrypoint:

- `scripts/orchestration/check_merge_ready.py` runs Phase 2, merge-readiness, and disposition proof as one verdict.
- Before the sole mapping commit, its local-only `--pre-closeout --require-auth`
  mode reads the uncommitted canonical artifact, requires both `GH_TOKEN` and
  `GITHUB_TOKEN`, requires the mapping artifact to be the only dirty path,
  explicitly maps every live actionable bot issue comment, bot inline comment,
  and top-level bot review, and requires exactly one true
  same-repository `blob/<exact-live-head-ref>/docs/review/...` Markdown link to
  that artifact in the live PR body. The ref path must equal the authenticated
  PR `head.ref`; repo-relative PR-body links do not count. It skips
  thread-resolution, current-head-CI, and wait-window gates and is never
  merge-readiness evidence.
- Underlying gate scripts remain authoritative for their own contract semantics.

## 4. Phase 2 Contract (Canonical Artifact)

Canonical source: `docs/review/PR_<N>_FIXED_MAPPING.md`.

The PR body keeps Goal, Scope, Tests/validation, Security notes,
Risks/Rollback, and one link to the canonical artifact. It does not mirror
review-thread URL→SHA entries. Required `## Experiment Runner Evidence` lives
in the canonical artifact:

- full URL→SHA mapping lines exist only in the canonical artifact
- required `## Experiment Runner Evidence` in the canonical artifact:
  non-trivial PRs must include an oracle-only artifact by default, and
  `Not applicable` requires an explicit coordinator/operator reason

Canonical runtime behavior is artifact-first when `pr_number` is available.
PR-body parsing is a temporary compatibility seam for legacy local/body-only
checks. It is not authority and must not cause agents to copy mapping blocks.

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
- Required `## Experiment Runner Evidence` with `Artifact: artifacts/orchestration/experiments/results/<id>.json` or `Not applicable: <reason>` in the canonical artifact. Non-trivial PRs must create oracle-only evidence by default; local artifact load/write failures are infrastructure blockers and are not valid `Not applicable` reasons. Malformed evidence is rejected.
- Required premortem evidence for non-trivial PRs: `pulseplate-premortem-risk-review`
  must run against the actual diff before PR open, and every finding must be
  `FIXED`, `NOT-A-BUG`, or `DEFERRED` with evidence/backlog proof.
  Premortem evidence is a creative future-state risk view and must be
  diff-specific: each finding names the concrete failure mode, affected surface,
  plausible user/business/project/security/governance impact, closure surface,
  and proof. For code, runtime, schema, security, workflow, orchestration, CI,
  or governance risks, `FIXED` proof must cite an enforceable mitigation in the
  PR, such as code, schema, validator, workflow guard, deterministic test,
  policy guard, or fail-closed behavior. A docs-only note is valid `FIXED`
  proof only when the underlying risk is documentation-only. Otherwise use
  `DEFERRED` with backlog proof or `NOT-A-BUG` with contract evidence.
- Required learning-loop evidence when triggered: `pulseplate-agent-learning-loop`
  is conditionally required when the operator asks for it or when the PR exposes
  a repeated role-agent, premortem, review, workflow, architecture, or
  successful-iteration pattern. Records must use
  `agent_learning_record.v1`, distinguish `pattern_kind`, include bounded
  `learning_metrics`, stay redacted and proposal-only, and require reviewed
  repo-diff promotion before becoming canonical instructions. If the pattern
  affects the current PR scope, close it with code/schema/test/guard/policy
  changes, not a learning note alone.
- Required bootstrap role-agent evidence: `task_bootstrap.py` packet creation
  does not execute roles. The packet/runbook-declared role order must be run in
  order before implementation or before the phase it governs; missing role
  execution blocks readiness unless `agent-coordinator` records an explicit
  disposition with evidence.
- Required custom-role dispatch evidence:
  run the packet-provided
  `role_agent_dispatch_contract.dispatch_manifest_command` with the actual
  packet path, preserving any `--mode runtime --implementation-owner <role>`
  flags the coordinator packet emits. Historical `qoder_dispatch_bridge.py`
  invocations are compatibility-only. Role bindings in the packet's legacy
  `advisory` collection with `required_role_pass: true` are mandatory
  custom-role passes; that collection name is metadata only, not permission to
  skip.

Valid mapping forms in the canonical artifact:

- `- <url> -> <sha>`
- `- <url>`
- `- No actionable review comments`

Legacy body mirrors and 7–40-character SHAs remain readable for pre-activation
PRs. V1 artifacts require full 40-character FIXED SHAs and the embedded closed
JSON block `PULSEPLATE_PR_REVIEW_SEAL_V1`. The activation boundary is the
governance PR number + 1; the governance PR may opt in with
`Review-Seal-Version: v1`.

### Material review seal v1

- The gate snapshots live base/head, fully paginates the PR commit connection,
  reads the artifact from that exact checked-out head, and rechecks refs before
  PASS. A change returns `SNAPSHOT_CHANGED`.
- The material base is the unique real merge-base. The digest is canonical JSON
  over merge-base, file status/path, old/new modes, full blob OIDs, and the
  classification-policy version.
- Every path is material except the exact current-PR mapping artifact. PR-body
  edits are outside Git. Other docs, AGENTS/runbook, workflows, tests,
  dependencies, schemas, and policies remain material.
- The trusted submitted Codex review object's real GitHub `commit_id` must be
  the frozen material head. A direct PR-root reaction from the official Codex
  Connector may instead use the normal `seal --review-ref` path as a nonblocking
  terminal source response only for `+1`,
  `heart`, `hooray`, or `rocket`, after live verification of its immutable
  GitHub account identity, exact PR-root URL, a live PR head equal to the caller's
  full snapshotted material head at seal time, and a server-timestamped GitHub Actions
  `pull_request` run linked to that same PR and head strictly preceding the
  reaction, with no later force-push or head-restoration event. This chronology
  proves only that GitHub observed the material head before the response; it is
  not Connector-owned reviewed-commit provenance. Authenticated
  validation after the one canonical mapping-only closeout commit may accept the
  descendant live head only after material-digest equality is re-established.
  When that automatic mapping-only cycle replaces the sealed reaction, the
  validator may accept only a newer live positive reaction from the same trusted
  Connector with the same content; the sealed receipt remains unchanged and the
  completed security scan is not restarted.
  The receipt uses `binding_kind=seal_context_only`, `review_claim=none`, and
  `blocking=false`. This is a verified positive Connector response, not exact-head
  review proof, a native GitHub approval, Codex Security evidence, or
  thread-resolution authority. The optional advisory rendering path remains
  non-authoritative and may be omitted with a warning. An official unedited no-findings issue comment
  is accepted only when the trusted Codex GitHub App identity and its short
  reviewed-commit marker resolve through the Commit API to that same full head;
  reviewer-execution/synthetic refs never satisfy this proof. The selected
  review-evidence variant and one completed final Codex Security diff scan bind
  to the same digest. A systemic MCP `-32001 Request timed out` outage may use a
  distinct `operator_outage_override` evidence variant only when an unedited GitHub
  comment from an `OWNER` or `MEMBER` binds the immutable GitHub user id, exact
  PR, material head, and material digest, declares `scan_id: none`, remains
  within its TTL, and the current-head `security`, `CodeQL`, `security-scan`,
  private-proxy, and Trivy policy checks from their expected GitHub Apps and
  workflows all succeed. PR `#2142` is the one-time bootstrap. Future PRs that
  change the override verifier, merge gate, current-head check identity parser,
  any CI/security workflow or local GitHub Action, or implementations/policy
  inputs of the substitute security checks cannot use the override. This variant records tool
  unavailability and must never be represented as a scan or no-findings result.
  The embedded scan record is a
  `human_asserted_content_receipt`: CI verifies schema, hashes, coverage, range,
  and content binding but does not claim signed/plugin attestation.
- If the trusted connector returns an exact known rate-limit or usage-limit
  response, the seal uses the tagged
  `pulseplate.codex-review-source-unavailability/v1` variant. The canonical
  same-PR, unedited trusted Codex GitHub App comment is terminal unavailable
  evidence: no retry, substitute review, prior review, operator override, or
  TTL is required. It is recorded as `source_degraded=true`,
  `fallback_required=false`, and `blocking=false`, and binds the current
  material head/digest with `binding_kind=seal_context_only` and
  `review_claim=none`; it is not review, approval, PASS, or no-findings
  evidence. Its exact negative projection is `retry_required=false`,
  `substitute_review_required=false`, `prior_review_required=false`,
  `operator_override_required=false`, and `ttl_required=false`.
  Unknown/changed bodies and identity, URL, timestamp, body-hash, PR/repository,
  or material-binding drift fail closed. The same immutable quota reference may
  be reverified after a later material change, but the material seal itself must
  be regenerated.
- Historical PR `#2142` `operator_review_credit_exhaustion_override` receipts
  remain parseable everywhere but are live-authenticated only for PR `#2142`.
  The legacy multi-reference override is not an active authoring mode for later
  PRs.
- `pr_review_closeout.py` keeps `init`, `freeze`, and `add-disposition` state
  gitignored. `seal` is the only tracked authoring step; mapping and seal publish
  in one batched governance-closeout commit. Resealing after a base sync is
  accepted only when Git proves both the base and the previously sealed material
  head advanced by ancestry and the replacement preserves every disposition
  proof block.
- Before publishing the one closeout commit, the pre-closeout gate must require
  the mapping artifact to be the only dirty path and validate the local sealed
  artifact against the complete live actionable bot inventory.
  In this pre-commit mode an actionable top-level review requires its own
  mapping even when all actionable child comments are mapped. The PR body must
  contain exactly one rendered same-repository blob Markdown link whose ref is
  the authenticated PR `head.ref` and whose destination is
  `docs/review/PR_<N>_FIXED_MAPPING.md`; plain text, repo-relative links,
  inline-code examples, and fenced examples do not count.
  Before PASS, the gate re-reads the live body and content-bound actionable
  inventory and fails closed on new, removed, or edited concurrent bot activity.

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
- Activated PRs must have a current material review seal and real mapped FIX
  commits in the complete live PR graph
- Cancelled/stale runs do not define mergeability
- PR lifecycle packets may distinguish `post_open_review` from `merge_ready`,
  but both phases still use current-head truth and the canonical artifact
  `docs/review/PR_<N>_FIXED_MAPPING.md`
- `post_open_review` is the packet-level phase where the canonical
  `qa-engineer-agent -> bug-hunter -> security-auditor` lane is synthesized,
  with Codex Security diff scan / finding discovery as the plugin scan that
  follows role review plus `pulseplate-pr-review`; `merge_ready` keeps the
  current-head merge-wrapper contract explicit without widening the review lane

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
- V1 SHA must be full length, GitHub-addressable, in the live PR commit set, and
  reachable from live head
- Commit must not be trigger-only
- Commit-after-comment applies
- An off-live-PR original comment commit/ref is reviewer-execution context only
  when the root comment author is exactly
  `chatgpt-codex-connector` (the authenticated GraphQL login). It never supplies
  FIX proof: the mapped FIX
  must still be a real live-PR commit reachable from the live head.
  `API_UNKNOWN` remains terminal, and off-graph refs from any other bot or
  human remain untrusted.

### NOT-A-BUG

- Requires written reasoning/evidence
- Thread URL must still be listed in Fixed in Commit Mapping
- No commit proof required

The only mapping-less duplicate exception is a trusted Codex/App
`unavailable_review_ref_ancestry` finding with the same material digest and
verified real FIX SHA as a canonical fingerprint record. An authorized
`OWNER|MEMBER|COLLABORATOR` reply must use the exact closed structured fields,
come after the finding in the same explicitly resolved thread, and the cited
review ref must resolve as unavailable (not API-unknown). The exception creates
no docs commit and does not restart review/security scans.

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
| Local       | Narrow validation bundle | Hard gate | Agents must run `check_preflight`, `check_agent_consistency`, focused tests for the touched surface, and `make validate-changed`; full local `make verify` is not a default agent command |
| Local / PR process | `task_bootstrap.py` + `role_dispatch_bridge.py` role-agent dispatch | Hard gate | Packet creation is not execution; every bootstrap/runbook assigned role and every required readonly/custom-role pass must run in declared order or carry an explicit coordinator disposition with evidence |
| Local / PR process | `pulseplate-premortem-risk-review` | Hard gate | Every non-trivial PR must run premortem on the actual diff before PR open; findings are creative future-state risk forecasts for user/business/project/security/governance impact, but require FIXED / NOT-A-BUG / DEFERRED evidence; FIXED for code/runtime/schema/security/workflow/orchestration/CI/governance risks requires enforceable closure in the PR, not docs-only risk recording |
| Local / PR process | `pulseplate-agent-learning-loop` | Conditional hard gate | Required when operator-triggered or when repeated failure/successful-iteration patterns appear; use redacted `agent_learning_record.v1` with `pattern_kind`, bounded `learning_metrics`, proposal-only authority, and reviewed repo-diff promotion before canonical instruction changes |
| Local / PR process | Experiment Runner oracle evidence | Hard gate | Every non-trivial PR must create oracle-only evidence by default; artifact load/write failures are infrastructure blockers, and material contribution requires governed attribution |
| Post-open review | `qa-engineer-agent -> bug-hunter -> security-auditor` plus Codex Security plus `pulseplate-pr-review` | Hard gate | After material freeze, role passes, one final Codex Security diff scan / finding discovery, and `pulseplate-pr-review` must complete for that digest; rerun only after material change, failed/incomplete run, coordinator reroute, or explicit operator override |
| GitHub PR CI | Full/heavy verification signal | Hard gate | Current-head CI must be green for `lint`, required/current-head checks for the touched PR surface, relevant `test-main` matrix, `diff-coverage` ≥97%, applicable security/governance checks, and merge-readiness; this replaces default local full `make verify` on agent machines |
| GitHub PR CI | Operator-approved machine-heavy deferral | Hard gate | PR body and fixed mapping document the deferral, the narrow local bundle passes, canonical current-head CI parity is green, relevant `test-main` matrix passes when selected, `diff-coverage` ≥97% is preserved when selected, and security/governance checks remain strict |
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
| `.github/workflows/trivy.yml` (`trivy`) | Main / scheduled / manual image-security lane | Soft gate | Internal image-security reporting lane that stays outside ordinary PR merge truth unless branch protection explicitly promotes it elsewhere | Demoted out of PR-time blocking path |
| `.github/workflows/frontend-ci.yml` (`Frontend CI`) | Frontend specialized lane | Hard gate when attached | Blocks merge only for frontend/design-token/OpenAPI-sync surfaces when attached by path or required checks | Specialized add-on lane |
| `.github/workflows/accessibility.yml` (`Accessibility Tests`) | Frontend specialized lane | Soft gate by default | Advisory frontend quality signal unless branch protection requires it | Specialized add-on lane |
| `.github/workflows/ci.yml` (`iOS unit tests`, `iOS UI smoke`) | iOS specialized lane | Hard gate when attached | Blocks merge for iOS / workflow-change surfaces when attached; note current path router also attaches on `.github/workflows/**` and `.github/actions/**` changes | Specialized add-on lane with current workflow-change coupling |
| `.github/workflows/greenlight-ios.yml` (`Greenlight iOS Preflight`) | iOS specialized lane | Soft gate | Report-only preflight (`GREENLIGHT_BLOCKING=false`) | Advisory iOS lane |
| `.github/workflows/build.yml` (`Docker Build and Push`) | Release / image lifecycle lane | Hard gate for release / image claims, not ordinary PR merge by default | Required before publish/image assertions; ordinary code-only PRs treat it as release-ops | Specialized release lane retained in PR2+ |

Bot governance distinction (Tier 1 baseline):

- Third-party bot **status checks** remain `External` and advisory unless GitHub marks them required.
- Third-party or first-party bot **review comments** remain merge-blocking when they contain actionable items, because review governance/disposition policy is separate from status-check classification.
- Contributors must use `CI` as the canonical backend/shared PR lane for operator decisions; `pr-tests.yml` and `pr-coverage.yml` are no longer active PR lanes, `security.yml` is a scheduled/manual audit lane, and `trivy.yml` is a `main`/schedule/manual non-PR image-security lane.
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
- `.github/workflows/trivy.yml:12`
- `.github/workflows/trivy.yml:177`
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
- Repo-approved Python interpreters for direct Python subprocesses
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
- Local `--pre-closeout` is valid only with `--require-auth` and both
  `GH_TOKEN` and `GITHUB_TOKEN`; it fails before network validation when either
  is absent.

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
