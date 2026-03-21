# Design-Agent Runtime Realignment Packet

- Date: 2026-03-21
- Coordinator: `agent-coordinator`
- PR intent: docs/governance realignment bridge for the design-agent runtime
  chain
- PR title: `docs(orchestration): realign design-agent runtime chain to merged baseline`

## Decision question

How should PulsePlate realign the design-agent runtime initiative so the
canonical chain documents match the already merged baseline in `main`, without
re-opening or duplicating runtime work that shipped through `PR #1210`?

## Success criteria

- `docs/design/DESIGN_AGENT_RUNTIME_PR_CHAIN.md` becomes state-aware and marks
  baseline PR1-PR3 as already realized in the merged repo state
- `docs/roadmap/BACKLOG_LEDGER.md` no longer presents the initiative as
  `PR1 scaffold active`
- This bridge PR has one canonical orchestration packet describing routing,
  sync points, review-ready criteria, and merge-ready loop
- `design-agent PR4` remains reserved for optional bounded creative research
  and is not consumed by this bridge PR
- No public runtime, API, or product-surface contract changes are introduced

## Scope

### IN

- Chain status realignment
- Umbrella backlog normalization
- Docs-only coordinator packet for this bridge PR
- Explicit post-open `qa-engineer-agent -> bug-hunter` review contract

### OUT

- New runtime semantics
- New preview renderer behavior
- Public FastAPI/OpenAPI changes
- iOS or frontend product runtime changes
- Any attempt to retro-split merged baseline work into fake historical PRs

## Exact routing for this PR

This PR is docs-only, so it does not reuse the normal runtime-primary flow as
its active execution route.

- Primary: `agent-coordinator`
- Secondary: `cursor-specialist-agent`
- Reviewer: `qa-engineer-agent`
- Advisory: `architecture-specialist`
- Optional consult only: `creative-designer`, `frontend-engineer`
- Mandatory post-open lane: `qa-engineer-agent -> bug-hunter`

## Why this routing deviates from the runtime flow

The general initiative flow remains:

```text
agent-coordinator -> creative-designer -> frontend-engineer -> qa-engineer-agent
```

That flow applies to runtime and preview implementation work. This bridge PR is
docs/governance-only, so the dominant domain is `orchestration/docs`, not
`design/platform`. The coordinator therefore uses docs-first routing while
keeping the initiative-level runtime flow unchanged for future feature PRs.

## Sync points

### SP1: Canonical state alignment

- chain doc explicitly states that baseline PR1-PR3 are already realized
- chain doc explicitly keeps design-agent PR4 unopened and optional

### SP2: Backlog alignment

- umbrella ledger item status matches merged baseline reality
- bridge PR target is documented separately from reserved design-agent PR4
  numbering

### SP3: Governance packet alignment

- this packet matches chain doc wording on routing and review-ready criteria
- no contradiction remains between initiative docs and current repo truth

## Acceptance packet contract

This packet is the canonical field-level contract for the bridge PR review
loop. The initiative chain doc keeps only the higher-level invariant that
`qa-engineer-agent -> bug-hunter` must complete before review-ready.

`qa-engineer-agent` must return all of the following before review-ready is
claimed:

- acceptance checklist
- regression matrix
- required commands
- expected pass/fail outcomes
- residual risks
- blocked scenarios, if any

Minimum command set for this bridge PR:

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `python3 scripts/ci/check_docs_phase1_gates.py --files docs/design/DESIGN_AGENT_RUNTIME_PR_CHAIN.md docs/roadmap/BACKLOG_LEDGER.md docs/orchestration/DESIGN_AGENT_RUNTIME_REALIGNMENT_PACKET.md docs/library/decisions/ADR_DESIGN_AGENT_RUNTIME_PR_CHAIN_2026-03-21.md` (repo-parity docs gate; current bridge files sit outside the script's `docs/audit` / `docs/security` enforcement scope)
- `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number <active-pr-number>`
- `pre-commit run --all-files`

## Bug packet contract

`bug-hunter` must return either:

1. a structured bug packet with:
   - `root_cause`
   - `file:line`
   - `minimal_fix_scope`
   - `tests_to_add_or_update`
2. or explicit `no findings`

For this bridge PR, `bug-hunter` is specifically checking:

- docs links
- source-of-truth drift
- wording drift against merged baseline
- governance inconsistencies between packet, chain doc, and ledger state

## PR open -> review-ready -> merge-ready loop

### 1. Pre-open

- coordinator confirms isolated worktree and preflight pass
- docs changes are scoped to chain doc, ledger item, and packet

### 2. Open PR

- PR body declares docs/governance-only scope
- PR body states that this bridge PR does not consume the reserved
  `design-agent PR4` slot

### 3. Post-open review loop

- `qa-engineer-agent` completes acceptance packet
- `bug-hunter` completes mandatory post-open pass
- coordinator resolves any docs/governance drift found in that loop

The PR must not be called `review-ready` until both outputs exist.

### 4. Merge-ready loop

- run the local docs/governance command set above
- run `make verify`
- if additional branch-level gates are required by PR policy, satisfy them
- coordinator verifies current-head PR governance state through the canonical
  merge-readiness workflow before any final readiness claim

## Assumptions

- `PR #1210` is the primary evidence anchor for the merged baseline that
  realizes the original PR2 and PR3 intent
- the current `main` branch, not retroactive PR numbering, is the canonical
  evidence of realized baseline state
- older initiative artifacts such as the accepted ADR remain part of the
  historical evidence pack, but their current-state interpretation is governed
  by the realigned chain SoT and umbrella ledger item
- if a real unresolved runtime or preview gap is discovered during this bridge
  PR, it is deferred into a separate follow-up item and separate code PR
