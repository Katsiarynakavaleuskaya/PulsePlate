# Design-Agent Runtime PR Chain

Date created: March 21, 2026 (America/New_York)
Status: Active initiative
Scope: coordinator-led expansion of the code-native design runtime

## 1. Summary

PulsePlate will extend the existing `code-native design runtime` rather than
creating a parallel "designer super-agent" platform.

Baseline direction:

- `tooling-first`
- `web/browser-first`
- `HITL-governed`

This means the first wave allows agents to generate, visualize, and adapt the
presentation layer inside governed contracts, but it does not allow them to
change live product UI or become a new source of truth for domain logic.

## 2. Operating assumptions

- One PR = one dedicated worktree.
- Do not reuse `worktrees/design_gen_pr2_code_native` for this initiative.
- Preferred worktree naming:
  - `worktrees/design-agent-pr1-brainstorm`
  - `worktrees/design-agent-pr2-runtime`
  - `worktrees/design-agent-pr3-preview`
  - `worktrees/design-agent-pr4-creative-research`
- Human approval remains required for promotion of visual or runtime changes.
- `bug-hunter` is mandatory after each PR is opened and before review-ready
  status is claimed.

## 3. Source of truth

Canonical pipeline:

```text
/tokens
-> docs/design/ui_component_vocabulary.json
-> governed instruction contract
-> pulseplate_canvas_v1
```

Subordinate lanes:

- Figma / Tokens Studio
- Penpot
- Storybook
- external AI layout tools

These lanes may review or reference the runtime, but they must not override the
repo-first contract chain.

## 4. Agent orchestration

Primary flow:

```text
agent-coordinator
-> creative-designer
-> frontend-engineer
-> qa-engineer-agent
```

Advisory path:

- `architecture-specialist` for boundary and invariant review
- `cursor-specialist-agent` for orchestration and docs hygiene
- `designer-artist-agent` for asset and visual family generation only
- `web-research-agent` only when PR1 requires evidence beyond repo SoT

Mandatory post-open lane:

```text
qa-engineer-agent
-> bug-hunter
```

`bug-hunter` owns first-pass regression triage after PR open:

- CI/local gate failures
- guard and diff-cover failures
- contract drift
- deterministic test regressions

Required bug packet fields:

- `root_cause`
- `file:line`
- `minimal_fix_scope`
- `tests_to_add_or_update`

## 5. PR chain

### PR1: Brainstorm + Scope Contract

Deliverables:

- coordinator task framing
- routing card
- brainstorm artifact
- synthesis decision
- promotion log
- backlog linkage

Rules:

- docs-only scope
- no runtime changes
- no new public endpoints
- lock the initiative goal:
  - `AI handles design execution, visualization, and adaptive presentation
    without replacing domain truth or live governance.`

### PR2: Adaptive Design Runtime Semantics

Add an additive `interaction_contract` block to the governed instruction payload
and `pulseplate_canvas_v1`.

Required fields:

- `interaction_mode`
- `checkpoint_policy`
- `adaptation_scope`
- `modality_hints`
- `explanation_strategy`

Rules:

- `adaptation_scope` is presentation-only:
  - copy
  - layout
  - modality
  - order of disclosure
- domain/business logic changes are forbidden
- validation must fail closed on unknown values

### PR3: Browser/HTML Preview Surface

Add an internal deterministic browser/HTML preview lane that consumes
`pulseplate_canvas_v1`.

Rules:

- read-only
- internal only
- no new public backend endpoint
- no live self-modifying UI
- preview must not become a second topology source

### PR4: Optional Bounded Creative Research Lane

Open only after PR2 and PR3 stabilize.

Rules:

- internal only
- experimentation protocol constrained
- fixed budgets
- immutable oracles
- promotion / defer / discard decisions required

## 6. Interfaces and contract changes

### Public contracts

- PR1: unchanged
- PR2: unchanged
- PR3: unchanged
- PR4: unchanged

### Internal contracts

- PR2 changes:
  - instruction JSON
  - canvas artifact contract
  - adapter result metadata
  - verification contract
- PR3 adds:
  - internal preview CLI
  - generated HTML artifact / local preview output
- PR4 changes:
  - experimentation artifacts only

## 7. Tests and acceptance

### PR1

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- docs quality checks for changed initiative artifacts
- explicit ledger links and DoD references

### PR2

- unit tests for:
  - `scripts/design/contracts.py`
  - `scripts/design/canvas_artifact.py`
  - `scripts/design/execution_adapters.py`
  - `scripts/design/generate_figma_instructions.py`
- positive and fail-closed tests for `interaction_contract`
- regression tests proving one topology source remains canonical

### PR3

- deterministic tests for HTML/browser preview renderer
- alignment tests: preview output vs `pulseplate_canvas_v1`
- representative preview tests for:
  - `ios.home`
  - `web.plate`
  - `web.progress`
- verification coverage for preview metadata

### PR4

- experiment packet tests
- offline evaluation tests
- budget and stop-condition tests
- proof that mutable forbidden surfaces remain untouched

## 8. Merge-readiness rule for this initiative

For every PR in this chain, after push:

1. `qa-engineer-agent` performs acceptance and readiness review.
2. `bug-hunter` performs a mandatory post-open bug-fix pass and returns either:
   - fixes, or
   - explicit `no findings`

The PR must not be called review-ready before both steps complete.

Standard local merge gates still apply:

- `pre-commit run --all-files`
- `make verify`

## 9. Related backlog items

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-design-agent-runtime-pr-chain`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-design-execution-adapter-seam`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-design-layout-archetype-templates`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-screen-content-template-convergence`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-design-html-preview`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-design-prompt-canvas-compiler`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-design-tooling-phase2-env-api`

## 10. Security Notes

- Adaptive design semantics must not bypass route guards, entitlement truth, or
  backend-owned state.
- Preview artifacts remain internal and deterministic.
- External tools remain review/reference lanes until separately promoted.
- Creative research must stay bounded under immutable-oracle rules.

## 11. Marketing & GTM

This initiative supports a stronger product story:

- not "AI draws pretty mockups"
- but "the product can generate, preview, and govern design execution from one
  repo-native runtime"

That is a stronger foundation for launch visuals, internal speed, and future
agent-native design operations without hiring a full design production team for
every iteration.
