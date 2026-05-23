<!-- markdownlint-disable MD013 -->
# PR-9 Design-System Automation Packet

## Summary

PR-9 opens a docs-only design-system automation lane for web+iOS runtime parity.

It is an implementation-opening governance PR, not a runtime PR. It creates the next packet layer after the completed PR-0 through PR-8 design runtime train, and it records that implementation must wait for a machine-readable design infrastructure layer.

This packet supersedes the prior closeout statement only for docs-governance routing: the old train remains complete through PR-8, and this PR-9 lane does not reopen any merged runtime, token, Storybook, Figma, or iOS implementation slice.

## Branch And Title

- Branch: `codex/design-runtime-pr9-design-system-automation-docs`
- Title: `docs(design): open PR-9 design system automation lane for web+iOS runtime parity`
- Classification: docs/tests/governance only, plus narrow orchestration preflight bugfix if required agents find a governance bug while executing this lane
- Runtime authority: none

## Current Repo Truth

PulsePlate already has strong design governance:

- Design-agent workflow and PR template governance.
- Storybook parity as a review/documentation lane for implemented web surfaces.
- `/tokens` authoring discipline and generated web+iOS runtime mirrors.
- Evidence automation through design intelligence packets, reference manifests, screen evidence packs, scorecards, premortem, and fixed-mapping governance.

The next bottleneck is machine-readable design infrastructure. Future implementation work must first know which component contracts exist, which bridge surfaces are covered, which visual and accessibility regression decisions fail closed, and where web+iOS token/runtime parity is allowed to start.

## Source Of Truth Boundary

Canonical:

1. Repo code, docs, tests, and reviewed contracts.
2. Backend/OpenAPI for product/runtime contract truth.
3. `/tokens` for token authoring.
4. `frontend/src/styles/tokens.css` for web runtime token truth.
5. iOS generated/runtime token mirrors as derived runtime outputs.
6. `docs/design/UI_COMPONENT_VOCABULARY.md` and `docs/design/ui_component_vocabulary.json` for current component vocabulary.

Reference/evidence only unless a later repo-reviewed contract promotes a narrower authority:

- Figma
- Canva
- Penpot
- Storybook
- Code Connect
- Browser/Chrome screenshots
- research tools
- prompt outputs
- scorecards
- evidence packs

PR-9 does not make Figma, Canva, Penpot, Storybook, or Code Connect a source of truth.

## Implementation Sequence

Future implementation must follow this order:

1. Component contract registry.
2. Bridge coverage inventory.
3. Visual regression decision gate.
4. Accessibility regression decision gate.
5. Token/runtime parity boundary.
6. Later web+iOS implementation slices.

No later step may be skipped by calling it a design prompt, evidence pass, or agent finding. If coordinator expands the role order, every coordinator-declared agent becomes mandatory and must run in order.

## PR-9 Scope

In scope:

- Add this packet.
- Add `docs/design/DESIGN_SYSTEM_AUTOMATION_SPEC.md`.
- Add `docs/orchestration/contracts/DESIGN_COMPONENT_CONTRACT_REGISTRY.md`.
- Update workflow/template/ledger pointers.
- Extend deterministic docs guards.
- Fix deterministic orchestration preflight bugs found while executing this lane, with regression tests, when the bug affects scoped path or agent-governance evidence.
- Record pre-open, post-open, and post-bot-review role-agent pass requirements.
- Record fixed mapping only after fixes or formal decisions.

Out of scope:

- Web runtime implementation.
- iOS runtime implementation.
- Storybook config or story implementation.
- Token changes or generated mirror regeneration.
- Figma, Canva, or Penpot writes.
- Code Connect activation.
- screenshots, videos, traces, or binary assets.
- backend, OpenAPI, auth, billing, StoreKit, HealthKit, deploy, or product logic changes.

## Component Contract Registry

The next mandatory layer is a machine-readable component contract registry. PR-9 adds the governance contract and defers executable schema generation to a later implementation PR.

Required future registry fields are:

- `component_id`
- `canonical_name`
- `repo_vocabulary_anchor`
- `web_runtime_anchor`
- `ios_runtime_anchor`
- `token_dependencies`
- `storybook_review_anchor`
- `figma_reference_anchor`
- `penpot_reference_anchor`
- `code_connect_anchor`
- `states`
- `variants`
- `accessibility_contract`
- `visual_regression_contract`
- `owner`
- `status`

If a value is not confirmed by repo truth, it must be recorded as `unspecified`.

## Bridge Coverage Inventory

The bridge coverage inventory must report coverage status for:

- Figma reference coverage.
- Penpot secondary-lane coverage.
- Storybook review coverage.
- Code Connect traceability coverage.
- repo vocabulary coverage.
- web runtime anchor coverage.
- iOS runtime anchor coverage.

Coverage inventory is evidence only. It does not grant external write authority or implementation permission.

## Visual And Accessibility Regression Decision

Visual and accessibility regression decision gates are mandatory fail-closed decisions before implementation PRs.

Fail-closed means:

- if no visual regression decision gate exists for a component, future implementation must stop or record `DEFERRED` with backlog evidence;
- if no accessibility regression decision gate exists for a component, future implementation must stop or record `DEFERRED` with backlog evidence;
- a screenshot, Storybook story, Figma node, or prompt review is not a substitute for a repo-reviewed visual or accessibility regression decision.

## Token And Runtime Parity Boundary

The boundary for future parity work is:

- `/tokens` remains token authoring truth.
- `frontend/src/styles/tokens.css` remains web runtime token truth.
- `frontend/src/styles/tokens.ts` remains a typed mirror/helper.
- `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift` remains generated output.
- `ios/PulsePlate/DesignSystem/DesignTokens.swift` remains iOS runtime token grouping.
- Web and iOS implementation slices must stay thin over repo/backend truth.

Exact component mappings, schema format, bridge coverage status, visual thresholds, accessibility thresholds, and Code Connect activation status are `unspecified` until later implementation PRs verify them from repo truth.

## Agent And Skill Execution

Pre-open role order is coordinator-expanded and mandatory:

1. `agent-coordinator`
2. `creative-designer`
3. `frontend-engineer`
4. `cursor-specialist-agent`
5. `architecture-specialist`
6. `security-auditor`
7. `qa-engineer-agent`
8. `bug-hunter`

Every role must produce an execution record or pass/finding note before PR open.

Required pre-open skill passes:

1. `pulseplate-workflow`
2. `pulseplate-design-launch-system`
3. `pulseplate-pr-review`
4. `pulseplate-premortem-risk-review`
5. `pulseplate-gates`
6. `pulseplate-guards`
7. `pulseplate-ledger`

Optional evidence tools remain optional unless a later coordinator packet promotes a narrower repo-reviewed use.

## Premortem

Premortem must inspect the actual diff before PR opening and again after the first bot-review cycle.

Minimum risks to check:

- lane overclaim,
- vague component contract registry,
- missing fail-closed visual or accessibility regression decision,
- drift between workflow, template, packet, spec, registry, and ledger,
- advisory wording where mandatory role order is required,
- runtime, iOS, frontend, Storybook, Figma, Canva, Penpot, Code Connect, token, generated mirror, backend, or OpenAPI scope drift,
- fixed-mapping format violations,
- stale root-checkout or full local verification commands in generated prompt surfaces.

Real findings must be fixed in docs/tests before mapping.

## PR Lifecycle

Post-open pass, immediately after PR creation:

1. `qa-engineer-agent`
2. `bug-hunter`
3. `security-auditor`
4. `pulseplate-pr-review`
5. `pulseplate-premortem-risk-review`
6. Codex Security plugin diff scan

After the first bot review, rerun on current head:

1. `agent-coordinator`
2. `qa-engineer-agent`
3. `bug-hunter`
4. `security-auditor`
5. `pulseplate-premortem-risk-review`
6. `pulseplate-pr-review`
7. Codex Security plugin diff scan

`docs/review/PR_<N>_FIXED_MAPPING.md` is created only after the PR number exists. It records evidence after fixes or formal decisions; it is not a substitute for fixing real defects.

Before merge readiness, a local Agent Run Summary must exist under `artifacts/agent_runs/` or the PR body/fixed mapping must record why host-local summary generation was unavailable. The artifact is local only and must never be committed.

## Validation

Use the worktree-local `.venv`:

```bash
.venv/bin/python scripts/orchestration/check_preflight.py
.venv/bin/python scripts/orchestration/check_agent_consistency.py
.venv/bin/python -m pytest -q tests/test_design_automation_next_lane_docs.py tests/test_orchestration_preflight.py
PATH=.venv/bin:$PATH pre-commit run --all-files
DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed
```

Do not run or prompt the full local root verification bundle for this lane.

## Merge Closeout

Merge readiness is not proven by local bounded checks alone. It requires current-head CI, review dispositions, fixed mapping, wait-window, and the strict merge wrapper.

After merge, the operator-owned local sync must verify the root project is fast-forwarded to `origin/main` and that the new PR-9 docs exist on local `main`.

Cleanup may remove only this PR-9 worktree, branch, caches, and temporary artifacts. Do not delete unrelated worktrees or collaborator branches.
