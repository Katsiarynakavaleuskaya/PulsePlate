# Route Family Migration Proof Checklist

This checklist is a non-runtime review artifact for future canonical route-family
migrations. It does not authorize route registration, OpenAPI mutation, legacy
alias growth, or merge-readiness claims.

Use `docs/orchestration/contracts/route_family_migration_proof.v1.schema.json`
and `scripts/orchestration/check_route_family_migration_proof.py` when a PR moves
a route family into canonical bootstrap ownership.

Required proof sections:

- `owner_proof`: canonical owner module, bootstrap registration owner, and removal
  of competing route owners are evidenced.
- `auth_proof`: canonical and legacy alias auth dependencies are checked.
- `openapi_proof`: canonical response models, visibility, and alias exposure are
  checked against generated OpenAPI expectations.
- `duplicate_route_proof`: method/path duplicate registration is checked.
- `partial_registration_proof`: missing-family-member or partial bootstrap failure
  behavior is checked.
- `legacy_growth_proof`: legacy alias additions, dynamic-import bypass, and
  compatibility-only scope are checked.
- `rollback_proof`: rollback path and touched files are explicit.

Minimum artifact rule: every proof section must set `checked: true`, include a
short `summary`, and provide at least one repo-relative `evidence_refs` entry.
`runtime_mutation_allowed` must stay `false`.
