# ADR: Design Execution Adapter Seam (2026-03-11)

- Status: Accepted (temporary seam)
- Date: 2026-03-11
- Owner: @katsiaryna_kavaleuskaya

## Context

PulsePlate is moving toward code-first design generation, but this PR does not
introduce a live external design executor yet. The current branch only exposes a
deterministic adapter seam:

- `scripts/design/execution_adapters.py:5`
- `scripts/design/execution_adapters.py:18`
- `scripts/design/execute_design.py:72`

That seam is useful for deterministic validation and manifest/verification
contracts, but it is still temporary because no reviewed live adapter exists and
the repo has not yet promoted a code-native canvas runtime as the execution
target.

## Decision

Keep `scripts/design/execution_adapters.py` as the temporary execution seam for
Phase 1 contract work:

1. `deterministic_stub` remains the only active adapter on this branch.
2. Instruction generation, execution, and verification must all flow through
   the adapter seam even in deterministic mode.
3. Future live or code-native adapters must preserve the same instruction and
   manifest contract before they can replace the seam.

## Exit Criteria

Retire this temporary seam only when ALL are true:

1. A reviewed non-stub adapter exists for the design runtime target.
2. The replacement adapter preserves instruction, manifest, and verification
   contracts already validated by `scripts/design/contracts.py:81` and
   `scripts/design/verify_design.py:58`.
3. Local deterministic tests cover the replacement path without depending on a
   live external design tool.
4. `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md` is updated so the runtime
   baseline no longer describes `deterministic_stub` as the only implemented
   adapter.

## Backlog Link (SoT)

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-design-execution-adapter-seam`

## Consequences

- Positive: PR1 can harden contracts and verification without pretending live
  execution already exists.
- Positive: future PRs can add a code-native or external adapter behind a known
  seam.
- Negative: the docs must keep calling out that `deterministic_stub` is a
  temporary implementation, not the end-state runtime.
