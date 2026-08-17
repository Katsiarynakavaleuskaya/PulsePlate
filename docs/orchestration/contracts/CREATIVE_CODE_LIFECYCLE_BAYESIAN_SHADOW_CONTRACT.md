# Creative-Code Lifecycle Bayesian Shadow Contract v1

## Purpose and authority boundary

This contract defines one local, deterministic, shadow-only rail that records a
fixed reference forecast before PR-2 candidate generation and can later score
resolved binary lifecycle outcomes. It tests prospective artifact plumbing and
exact lineage. It does not establish calibration, reliability, predictive
skill, causal effectiveness, candidate correctness, or product value.

The rail does not call a provider, network, product runtime, GitHub, or role
agent. It does not change routing, retry budgets, review roles, promotion, PR,
review, or merge decisions.

## Closed family registry and arithmetic

V1 contains exactly these families in this order:

| Family | Eligibility | Positive branch | Negative branch |
| --- | --- | --- | --- |
| `patch_evaluation_acceptance_v1` | the exact accepted specification/generation gate has one patch-result opportunity | `patch_evaluation.accepted` | `patch_evaluation.rejected` |
| `pr_opening_v1` | `promotion_approval.accepted` | `pr_open.opened` | `pr_open.blocked` |
| `pr_terminal_merge_v1` | `pr_open.opened` | `pr_terminal.merged` | `pr_terminal.closed_unmerged` |

Accepted-only intermediate stages are not forecast families because telemetry
has no closed negative branch for them. A missing successor is never converted
to a negative outcome.

Each baseline family retains separate positive, negative, censored-eligible,
and unmatched-destination counts. Only positive and negative counts enter the
fixed reference posterior:

```text
effective_observation_count = positive_outcome_count + negative_outcome_count
posterior_alpha = 1 + positive_outcome_count
posterior_beta  = 1 + negative_outcome_count
posterior_predictive_bps = round_half_up(
  10000 * posterior_alpha / (posterior_alpha + posterior_beta)
)
```

All arithmetic is integer arithmetic. For non-negative values:

```text
round_half_up(numerator / denominator) =
  (2 * numerator + denominator) // (2 * denominator)
```

The empty corpus therefore yields `Beta(1,1)`, `5000 bps`, and
`observation_state=prior_only` for every family. Any resolved binary outcome at
that reference forecast yields `250000 ppm` realized Brier loss. This is a
mechanical reference value, not a quality or effectiveness result.

Historical patch observations remain attempt-weighted because lifecycle
analytics permits more than one patch destination for one specification. This
working baseline does not assert independent observations or a whole-Pilot
success probability.

## Prospective target boundary

A forecast can be built only from an exact validated lifecycle analytics
artifact and its exact validated telemetry snapshot after a clean
`generation_gate.json` exists but before any PR-2 candidate or result artifact
exists. Baseline target leakage fails closed as
`retrospective_forecast_forbidden`.

The target identity binds all of:

- generation gate ID, fingerprint, and repo-relative ref;
- admission ID, fingerprint, and repo-relative ref;
- request ID, fingerprint, and repo-relative ref;
- source bundle ID, fingerprint, and repo-relative ref;
- selected variant ID and fingerprint;
- PR-2 run ID and prepared-state fingerprint;
- exact base commit SHA.

`task_packet_id` is not a target key. Adaptive hypothesis, role, and early
specification stages remain outside this v1 forecast boundary.

`produced_at`, `started_at`, and `scored_at` are caller-supplied,
timezone-aware RFC3339 values normalized to UTC. No command reads an internal
clock. The fixed observation cutoff is `produced_at + 14 days`. A published
score is immutable; `scored_at` cannot extend beyond that cutoff, and a later
outcome never rewrites it.

## Immutable artifacts and publication

Artifacts occupy one stable target slot:

```text
artifacts/orchestration/creative_code/bayesian_shadow/<forecast-id>/
  forecast.json
  start.json
  score.json
```

The forecast ID depends on the policy version and stable generation-gate target
identity, not on a timestamp or baseline snapshot. The artifacts are:

- `forecast.json`: exact baseline analytics/telemetry bindings, the fixed
  prior, three family rows, target gate, and cutoff;
- `start.json`: the exact forecast/gate binding written by
  `generate-candidate` before its first generate/evaluate call;
- `score.json`: exact forecast/start, outcome snapshot, generation receipt when
  a unique patch exists, promotion/terminal lineage, and per-family results.

Forecast and start are never rewritten after an outcome. Score is the only
later artifact allowed in an occupied slot. Identical replay does not write;
divergent replay preserves the first winner and fails closed.

Every artifact is canonical closed JSON containing only repo-relative refs.
Readers reject duplicate keys, BOMs, non-finite values, oversized or
non-canonical bytes, unexpected fields, traversal, symlinks, hardlinks, unsafe
file modes, and source drift. Directories use mode `0700`; files use mode
`0600`. Publication is staged, fsynced, atomic no-replace, source-rechecked,
and rolled back if a post-publication recheck fails.

Artifacts must not contain prompts, review text, patches, provider/oracle
output, absolute paths, secrets, or free-form candidate metadata.

The closed schemas are:

- `creative_code_lifecycle_bayesian_forecast.v1.schema.json`;
- `creative_code_lifecycle_bayesian_target_start.v1.schema.json`;
- `creative_code_lifecycle_bayesian_score.v1.schema.json`.

## Mechanical PR-2 binding

The ordinary unforecasted command remains available only when the target has no
shadow slot. A forecasted invocation pairs both optional arguments:

```bash
python -m scripts.orchestration.creative_code_patch_generation \
  generate-candidate \
  --gate artifacts/orchestration/creative_code/patch_generation/<run-id>/generation_gate.json \
  --shadow-forecast artifacts/orchestration/creative_code/bayesian_shadow/<forecast-id>/forecast.json \
  --started-at 2026-08-17T10:01:00Z
```

While holding the existing cooperative per-run lock, the wrapper revalidates
the gate and forecast, publishes or reads back identical `start.json`, and
rechecks their sources. It keeps that same lock through the first builder
generation mutation, preventing a duplicate invocation from reaching the
builder, then releases it before evaluation takes the existing lock without
nesting. Forecast probabilities are not passed to the builder, evaluator,
provider, routing, or role agents.

A clean retry after a stop following start publication must use identical
forecast and `started_at`. Once candidate generation has mutated the run
namespace, retrospective forecast/start creation and scoring are forbidden. An
occupied exact shadow slot also blocks an unbound invocation.

This ordering establishes only `local_dependency_order_only`. It is not an
external timestamp, tamper-evident log, cryptographic preregistration, or a
defence against same-UID deletion of all local evidence.

## Outcome lineage and scoring

Aggregate analytics is never used to select the target. The scorer reads
validated normalized events and requires the exact
`(source_bundle_id, selected_variant_id, request_id)` patch identity, checks its
result ID/fingerprint against the exact generation receipt, locates at most one
promotion plan with the same tuple/result, then follows the exact
`promotion_id` through validation, approval, PR-open, and terminal stages.
Unrelated concurrent events are permitted.

Baseline event fingerprints must remain an unchanged subset of the later
snapshot. Source drift, malformed evidence, receipt/result mismatch, or
untrusted input fails before score publication. More than one target patch or
promotion branch is a validated semantic ambiguity and produces
`measurement_invalid`; the scorer never pools or selects among branches.

Per-family states are:

- `observed_positive`;
- `observed_negative`;
- `not_reached` when eligibility did not occur;
- `right_censored` when eligibility occurred but its unique successor was
  absent at the terminal/cutoff observation;
- `measurement_invalid` for a validated ambiguous target measurement.

For a resolved family:

```text
actual_bps = 10000 for the positive branch, otherwise 0
realized_brier_loss_ppm = round_half_up(
  ((forecast_bps - actual_bps)^2 * 1000000) / 10000^2
)
```

Top-level states are `fully_scored`, `partially_scored`,
`valid_but_unscored`, and `measurement_invalid`. There is no overall Pilot,
model, agent, mean, calibration, reliability, or effectiveness score.
`valid_but_unscored` is limited to clean not-reached/censored outcomes.

## CLI

```bash
python -m scripts.orchestration.creative_code_lifecycle_bayesian_shadow build-forecast \
  --telemetry-dir <validated-baseline-snapshot> \
  --gate <canonical-generation-gate> \
  --produced-at <RFC3339>

python -m scripts.orchestration.creative_code_lifecycle_bayesian_shadow validate-forecast \
  --forecast <canonical-forecast>

python -m scripts.orchestration.creative_code_lifecycle_bayesian_shadow validate-start \
  --start <canonical-start>

python -m scripts.orchestration.creative_code_lifecycle_bayesian_shadow score-forecast \
  --forecast <canonical-forecast> \
  --telemetry-dir <validated-outcome-snapshot> \
  --scored-at <RFC3339>

python -m scripts.orchestration.creative_code_lifecycle_bayesian_shadow validate-score \
  --score <canonical-score>

python -m scripts.orchestration.creative_code_lifecycle_bayesian_shadow summarize \
  --forecast <canonical-forecast> [--score <canonical-score>]
```

`build-forecast` accepts no caller-authored counts, arbitrary analytics payload,
target manifest, or output root. The scorer publishes after a canonical
terminal stop or at the exact fixed cutoff. A semantic measurement ambiguity
without a canonical terminal stop must also wait for that cutoff; it is not an
early-score bypass. Malformed or untrusted sources publish nothing.

## Known v1 limit and rollback

The default telemetry collector does not include adaptive finalized
specification artifacts in `spec_runs`. The generation gate proves the target's
accepted-specification precondition, while the target patch outcome is read
directly from normalized telemetry. A later aggregate may therefore count that
patch as an unobserved predecessor. V1 reports this limitation and does not
create synthetic mirror events or backfill.

Rollback removes optional `--shadow-forecast`/`--started-at` use and reverts
only the shadow modules, schemas, and bounded generation hook. The ordinary
PR-2 path remains unchanged. Existing local forecast/start/score artifacts are
inert evidence and are not migrated, rewritten, or automatically deleted.
