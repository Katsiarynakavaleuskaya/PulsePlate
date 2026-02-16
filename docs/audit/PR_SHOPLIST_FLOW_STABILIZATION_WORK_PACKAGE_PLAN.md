# Shoplist Flow Stabilization — Runtime Work-Package Plan

## Goal

Deliver one deterministic user outcome in a single PR package:
`plan -> shoplist`.

This plan intentionally avoids ultra-atomic "3-file PR" fragmentation while preserving strict scope control.

## PR Title

`feat(shoplist): stabilize contract-only helpers into end-to-end user flow`

## Why now

- PR #763, #764, #765 removed blockers and improved baseline determinism.
- PR-764 enabled helper contracts, but not the full flow outcome.
- Next step should be one reversible value package, not a sequence of micro-PRs.

## Evidence anchors

- `core/shoplist.py:1`
- `tests/core/test_shoplist_contract.py:1`
- `docs/audit/PR_764_SHOPLIST_HELPERS_ENABLE_AUDIT.md:1`

## Scope (IN)

1. Flow-level wiring for `plan -> shoplist` within existing canonical/compat boundaries.
2. Contract stability:
   - response shape checks for 200 and key failures (422/401/403/429 when applicable),
   - explicit content-type assertions,
   - stable error envelope assertions.
3. Integration coverage:
   - one deterministic happy path across the full flow,
   - one deterministic edge/negative matrix.
4. Determinism and guard compatibility:
   - no import hygiene regressions,
   - no bypass of guard order.
5. Minimal documentation update in the same PR (how to call flow + expected error envelope).

## Scope (OUT)

- New AI/RAG endpoints or new "smart generation" surfaces.
- Large frontend/iOS initiatives.
- Security suppression/CVE config changes.
- Unrelated refactor/cleanup outside this flow package.

## Inclusion criteria (must be true)

- The change set produces one complete, testable flow outcome (not scaffolding-only).
- All touched parts are required for this single outcome.
- Rollback is possible via one PR revert (no cascade dependency on other pending PRs).

## Exclusion criteria (must stay out)

- Any change whose value is independent from `plan -> shoplist`.
- Any change requiring a different rollout, risk owner, or quality gate set.
- Any "while we are here" refactor not tied to this flow.

## Test strategy (minimum)

1. Contract tests
   - Validate request/response contract for flow entrypoints.
   - Assert content-type and key error envelope fields.

2. Integration test
   - One deterministic end-to-end happy path: `plan -> shoplist`.

3. Negative tests
   - Invalid inputs and missing/invalid auth or tier context where applicable.
   - Assert expected status and stable error envelope.

4. Anti-flake controls
   - deterministic fixtures only,
   - no `--lf` dependency,
   - no patched builtins or mutable shared global state.

## Security notes (must-have)

- Keep guard dependencies explicit and testable (`require_pro_tier` / `require_vip_tier` where relevant).
- Validate that protected paths cannot be accessed via bypass aliases.
- For rate-limited paths, ensure deterministic 200->429 transition tests where applicable.
- Do not expose tokens, secrets, or upstream exception internals in payload/log wording.

## Risks and mitigations

1. Risk: Scope creep into adjacent domains.
   - Mitigation: strict IN/OUT checklist in PR body.

2. Risk: Determinism regressions in tests.
   - Mitigation: fixed fixtures and explicit anti-flake constraints.

3. Risk: Hidden contract drift.
   - Mitigation: response shape + content-type + error envelope assertions.

## Rollback plan

- Revert one PR if package causes instability.
- No migration-heavy or non-reversible changes in this package.
- Keep compat behavior stable; only stabilize delegation and tests.

## Ready-to-merge gates

- `pre-commit run --all-files`
- `make verify`
- targeted pytest run for new flow tests + relevant guards
- no unresolved review threads or actionable bot comments

## Metrics block (work-package vs atomic PR)

Evaluation window: 8-12 weeks (compare with previous 8-12 weeks baseline).

1. PRs merged per week
2. Median time-to-merge
3. Review cycles per PR
4. Revert/hotfix rate within 14 days
5. First-run CI pass rate
6. Average comments per PR
7. Package completion rate (planned scope delivered in one PR package)

Success signal:
- equal or better throughput with lower review churn and no quality regression.

## Delivery sequence

Now (this package):
- Implement full backend flow outcome + tests + minimal docs.

Next (separate package):
- Deferred items only, recorded in `docs/roadmap/BACKLOG_LEDGER.md` with owner/DoD/target PR.

## Task matrix with checkpoints (A/B/C/D)

| Phase | Objective | Responsible | Checkpoint (objective evidence) | Hard gate |
|---|---|---|---|---|
| A. Docs PR closure | Merge docs-only package governance updates | Coordinator + Author | PR has docs-only diff and is merged | `python scripts/ci/check_docs_phase1_gates.py --files ...` |
| B. Runtime package execution | Implement `plan -> shoplist` in one scoped package | Runtime Owner + Bug Hunter | Local verification is green and scope IN/OUT is respected | `pre-commit run --all-files` + `make verify` |
| C. Review/bot/CI closure | Resolve all reviewer and bot actionables | Author + Reviewers | No unresolved threads, bots have no actionables, required CI checks pass | required checks PASS on PR |
| D. Merge readiness | Final go/no-go and merge | Coordinator + Maintainer | Merge criteria are all satisfied, then merge | no open review threads + no red checks |

### RACI-lite

| Step | Responsible | Reviewer | Approver |
|---|---|---|---|
| Freeze package scope (IN/OUT) | Architecture Specialist | Logic Agent | Coordinator |
| Test matrix freeze | Bug Hunter | Data Scientist Agent | Coordinator |
| Security acceptance | Security Auditor | Architecture Specialist | Coordinator |
| CI/bot closure | Runtime Author | Reviewers | Maintainer |
| Final merge decision | Coordinator | Reviewers | Maintainer |

### Fail-path protocol

1. CI red:
   - capture failing command output and `file:line:error`,
   - fix root cause (no masking with `|| true`),
   - re-run `make verify`.
2. Bot actionables present:
   - resolve each actionable or document a justified deferral,
   - close related review threads.
3. Unresolved review threads:
   - merge is blocked until all required threads are resolved.

### KPI checkpoint block (work-package effectiveness)

Evaluation window: 8-12 weeks (vs previous 8-12 week baseline).

- Lead time to merge (median)
- Review cycles per PR
- First-run CI pass rate
- Revert/hotfix rate within 14 days
- Package completion rate (planned scope delivered in one package)

## Checklists

### Pre-push

- [ ] `pre-commit run --all-files`
- [ ] `make verify`
- [ ] targeted pytest for flow + relevant guards
- [ ] diff reviewed: no unrelated refactor/security suppression changes

### Post-merge

- [ ] Link merged PR in `docs/roadmap/BACKLOG_LEDGER.md` and close the corresponding item.
- [ ] Confirm no deferred work is left untracked.
