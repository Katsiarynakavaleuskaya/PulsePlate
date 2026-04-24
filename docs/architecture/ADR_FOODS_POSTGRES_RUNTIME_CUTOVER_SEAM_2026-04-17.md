# ADR: Foods PostgreSQL Runtime Cutover Seam

**Effective date:** 2026-04-17 (`America/New_York`)
**Status:** Accepted temporary seam

## Context
- PR-A, PR-B1, PR-B2, and PR-B3 are already merged, but the production/runtime authority for foods and restaurant reads is still SQLite/local-first.
- PR `#1462` is a docs/governance closeout lane only and must not invent runtime cutover behavior.
- The repo still needs one bounded migration follow-up lane before any runtime authority switch: `ledger-p1-foods-foundation-downgrade-ownership`.

## Decision
- Runtime authority cutover from SQLite to PostgreSQL remains out of scope until a separate governed post-B3 cutover packet and PR explicitly approve the read-switch.
- Any document that mentions the deferred cutover seam must cite this ADR and the owning backlog items instead of implying that cutover is already scheduled or implemented.

## Exit Criteria
1. PR `#1462` merges and the post-B3 closeout packet becomes canonical repo truth.
2. `ledger-p1-foods-foundation-downgrade-ownership` lands with deterministic migration coverage and green current-head gates.
3. A dedicated post-B3 cutover packet defines exact runtime source-selection behavior, rollback plan, and owner-reviewed scope boundaries.
4. Deterministic tests prove runtime source selection, parity expectations, and fail-safe rollback behavior for the cutover lane.
5. The cutover PR passes `pre-commit run --all-files`, `make verify`, and the strict current-head merge-readiness wrapper.

## Backlog Link
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-foods-postgres-foundation-followthrough`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-foods-foundation-downgrade-ownership`

## Consequences
- SQLite remains canonical runtime authority until this ADR is retired by a later governed cutover lane.
- Docs/governance closeout work may point to this ADR as the authoritative temporary-seam contract without widening into runtime or deploy scope.
