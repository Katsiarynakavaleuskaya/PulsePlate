# Review Pattern Oracles

Review-pattern oracles are offline, deterministic reviewer-planning helpers for
recurring PulsePlate PR failure modes. They are proposal-only evidence and do
not post GitHub comments, resolve review threads, update fixed mapping, or claim
merge readiness.

Canonical helper/CLI: `scripts/orchestration/review_pattern_oracles.py`.
Schema: `docs/orchestration/contracts/review_pattern_oracles.v1.json`.

The default oracle catalog uses stable compact IDs:

- `schema_validator_parity`
- `fail_closed_security_edge`
- `deterministic_content_oracle`
- `canonical_route_ownership_guard`
- `evidence_hygiene_mapping_timing`
- `review_source_degraded`

Promotion of a new pattern requires a reviewed repo diff plus focused tests.
