# Design Bridge Operationalization Packet

- Date: 2026-04-11
- Coordinator: `agent-coordinator`
- PR intent: operational evidence lane for the design bridge after the merged
  realignment baseline
- PR title: `feat(design-ops): operationalize bridge preflight, capture, and first parity pack`

## Decision question

How should PulsePlate convert the merged design-bridge baseline into a governed
review/evidence lane that proves web and iOS parity without reopening the
merged bridge PRs or widening into deploy/runtime mutations?

## Success criteria

- A new backlog item defines `PR21` as a separate design-ops lane that does
  not modify the colleague-owned bridge-closeout lane
- One canonical packet defines pre-open, post-open, and merge-ready behavior
  for the operationalization lane
- The lane documents one evidence pipeline with:
  - Storybook-first web review
  - simulator-based iOS verification
  - one first parity pack limited to representative already-realized surfaces
- Cloudflare preview/deploy stays non-blocking and outside merge truth
- No public runtime, API, OpenAPI, or product-surface mutation is introduced

## Scope

### IN

- Design-bridge preflight contract
- Storybook-first web evidence path
- iOS simulator verifier path using `ios/PulsePlate.xcworkspace`
- First parity pack for:
  - `ios.home`
  - `web.plate`
  - `web.progress`
- Shared evidence artifact reuse
- Explicit post-open `qa-engineer-agent -> bug-hunter` review contract

### OUT

- Bridge closeout / ledger normalization already covered by PR `#1386`
- Any retroactive reimplementation of merged PR1-PR3 work
- Any use of the reserved `design-agent PR4` slot
- Cloudflare Pages/Workers deploy gates
- New backend endpoints, frontend runtime behavior changes, or iOS product flow
  mutations

## Exact routing for this PR

This lane is operationalization-only, but it follows the normal initiative
runtime execution order because it validates the review/evidence path rather
than acting as a docs-only bridge.

- Primary: `agent-coordinator`
- Execution order:
  1. `creative-designer`
  2. `frontend-engineer`
  3. `qa-engineer-agent`
- Advisory: `cursor-specialist-agent`
- Optional consult: `architecture-specialist`
- Mandatory post-open lane: `qa-engineer-agent -> bug-hunter`

## Scope separation from the bridge-closeout lane

- PR `#1219` is the merged realignment bridge baseline
- PR `#1386` is treated as the active colleague-owned closeout lane for
  residual bridge/ledger drift
- This packet defines a separate `PR21` operationalization lane and must not
  edit or depend on the unresolved review state of `#1386`
- This lane does not consume the reserved `design-agent PR4` slot

## Sync points

### SP1: Packet + backlog alignment

- backlog item explicitly names `PR21` as a separate design-ops lane
- backlog wording states that the lane is adjacent to, but not part of, the
  bridge-closeout work

### SP2: Evidence contract alignment

- web review source is explicitly Storybook-first
- iOS review source is explicitly simulator-based
- parity pack is limited to representative baseline surfaces only

### SP3: Review-governance alignment

- `qa-engineer-agent -> bug-hunter` is documented as mandatory post-open
- Cloudflare preview/deploy stays advisory and non-blocking
- merge-ready claims still require repo-global gates and PR governance checks

## Acceptance packet contract

`qa-engineer-agent` must return the following before review-ready is
claimed:

- acceptance checklist
- regression matrix
- required commands
- expected pass/fail outcomes
- residual risks
- blocked scenarios, if any

Minimum command set for this lane:

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `cd frontend && npm run build`
- `cd frontend && npm run build-storybook`
- iOS simulator sanity for workspace `ios/PulsePlate.xcworkspace` and scheme
  `PulsePlate`
- `pre-commit run --all-files`

Before merge-ready, the repo-wide hard gate remains mandatory:

- `make verify`

## Bug packet contract

`bug-hunter` must return either:

1. a structured bug packet with:
   - `root_cause`
   - `file:line`
   - `minimal_fix_scope`
   - `tests_to_add_or_update`
2. or explicit `no findings`

For this lane, `bug-hunter` is specifically checking:

- packet vs backlog drift
- incorrect evidence references
- Storybook/iOS parity-surface scope creep
- any accidental conversion of Cloudflare preview into merge truth

## PR open -> review-ready -> merge-ready loop

### 1. Pre-open

- coordinator confirms isolated worktree and preflight pass
- operationalization work stays scoped to the packet, backlog item, and related evidence artifacts
- parity pack stays limited to `ios.home`, `web.plate`, `web.progress`

### 2. Open PR

- Keep the PR in `draft` until the following are true:
  - preflight pair passed
  - packet exists
  - first evidence bundle exists for the current lane scope
- PR body declares design-ops / evidence-only scope
- PR body states that:
  - the lane does not touch the colleague-owned bridge-closeout PR `#1386`
  - the lane does not consume the reserved `design-agent PR4` slot
  - Cloudflare remains advisory only
- After the PR number exists, create the standard governance artifact:
  - `docs/review/PR_<N>_FIXED_MAPPING.md`
- Mirror the required governance sections into the PR body:
  - `Discussion Thread Pass`
  - `Fixed in Commit Mapping`
  - `Merge Readiness`

### 3. Post-open review loop

- `qa-engineer-agent` completes acceptance packet
- `bug-hunter` completes mandatory post-open pass
- coordinator resolves any packet/evidence/governance drift found in that loop

The PR must not be called `review-ready` until both outputs exist.

### 4. Merge-ready loop

- run the local command set above
- run `make verify`
- run the canonical PR governance checks for the active PR number
- verify current-head merge-readiness state before any final readiness claim

## Evidence artifacts reused by this lane

- Session evidence template source:
  - `docs/runbooks/FIGMA_MCP_SESSION_EVIDENCE_TEMPLATE.md`
- Session evidence artifact:
  - `docs/runbooks/sessions/DESIGN_TOOLING_SESSION_2026-04-11_design-bridge-ops-parity-pack.md`
- Review packet template source:
  - `docs/design/PENPOT_CTA_REVIEW_PACKET_TEMPLATE.md`
- Parity pack artifact:
  - `docs/design/DESIGN_BRIDGE_FIRST_PARITY_PACK_2026-04-11.md`

## Assumptions

- Storybook remains the canonical review surface for web design-system parity
- The representative parity pack can be validated without opening any new
  backend/runtime surface
- iOS evidence uses the existing PulsePlate workspace and simulator tooling
- If a real runtime gap is discovered while collecting evidence, it is deferred
  into a separate follow-up packet and separate code PR
