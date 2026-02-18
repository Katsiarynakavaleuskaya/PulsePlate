# 03 Synthesis Decision (Seed)

## Decision

Adopt a full Figma Git runbook plus packs index under `docs/figma`.
Require context refresh before each Figma task.

## Rationale

- Prevent context loss and brand drift.
- Make handoff deterministic across Design -> Sora -> FE/iOS.
- Keep implementation scope fixed to H+P+Pr.

## Trade-offs

- Slightly higher docs maintenance overhead.
- Lower ambiguity and faster execution in exchange.

## forced_decision

- forced_decision: `false`
