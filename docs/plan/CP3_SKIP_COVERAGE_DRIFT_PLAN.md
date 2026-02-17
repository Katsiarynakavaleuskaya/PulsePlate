# CP3 Plan: Skip-Heavy Coverage Drift Follow-Up

## Goal

Convert CP3 from "cleanup by assumption" to evidence-driven execution.

- A1 in narrow scope is no-op (already canonical).
- Next step is controlled audit expansion with strict scope guards.

## Scope guard (hard)

- This plan is docs-and-audit only.
- No runtime code changes.
- No test behavior rewrites without new evidence.
- No new skip mechanics beyond canonical protocol.

## A1 summary (input state)

- A1 files:
  - `tests/test_remaining_modules.py`
  - `tests/test_zero_coverage_modules.py`
- Outcome:
  - canonical `require_feature_or_raise(...)` usage
  - no ad-hoc `pytest.skip(...)`
  - canonical `feature_disabled:<key>` reasons only

Reference: `docs/audit/CP3_SKIP_HEAVY_A1_NOOP_AUDIT_2026-02-16.md`

## Falsifiable hypotheses (next audit stage)

1. Expanded CP3 scope still contains only canonical skip protocol usage.
2. Any non-canonical skip in expanded scope is attributable to a concrete file and line and can be fixed without runtime edits.
3. "No-op" remains true for scoped files unless a new test drift is introduced.

### Promotion criteria to execution PR

Promote only if at least one of the following is true:

- Non-canonical skip pattern found in expanded scope.
- Missing `require_feature_or_raise(...)` in an ImportError gating path.
- Contract drift found between skip reason key and ledger key.

Otherwise, keep CP3 as no-op with documented evidence.

## KPI baseline and thresholds

### Baseline (A1 scoped files)

| Key | Current skipped count |
| --- | --- |
| `weekly_plan_helpers` | 1 |
| `utils_pack` | 3 |
| `sports_disclaimers_lifestage` | 3 |
| `exports_recipes_products` | 5 |

### Thresholds

- Canonical skip compliance: `100%` required.
- Ad-hoc skip strings: `0` allowed.
- Protocol regressions (`require_feature_or_raise` missing where required): `0` allowed.

## Uncertainty and stop/degrade policy

- Confidence labels for findings: High / Medium / Low.
- Stop expansion if evidence quality is Low and cannot be improved by one additional audit pass.
- Degrade behavior under low evidence:
  - reduce to smallest reproducible file slice
  - avoid speculative rewrites
  - create/update ledger follow-up instead of forcing code churn

## Logic and architecture invariants

- Skip protocol SoT remains canonical and singular.
- No policy-guard weakening.
- No runtime path changes in CP3.
- Matrix-style negative checks remain status-only where applicable.

## Security and bug-risk controls

- Prevent false-green outcomes:
  - no hidden failures via ad-hoc skips
  - no mask patterns (`|| true`, broad skip wrappers) in CP3 changes
- Every deferred finding must map to a backlog item with owner and DoD.

## Evidence and traceability format

For each CP3 phase:

1. exact command
2. 1-3 raw output lines
3. exit code
4. file:line anchors
5. decision (no-op / actionable)

## Verification commands (for CP3 docs and audits)

```bash
pytest -q -rs tests/test_remaining_modules.py tests/test_zero_coverage_modules.py | rg -n "SKIPPED|feature_disabled:"
rg -n "require_feature\\(|require_feature_or_raise\\(" tests/test_remaining_modules.py tests/test_zero_coverage_modules.py
rg -n "pytest\\.skip|skip\\(" tests/test_remaining_modules.py tests/test_zero_coverage_modules.py
```

## Stakeholder framing

- This phase optimizes delivery predictability and trust by avoiding cosmetic rewrites.
- Value is risk reduction and audit precision, not artificial code churn.
