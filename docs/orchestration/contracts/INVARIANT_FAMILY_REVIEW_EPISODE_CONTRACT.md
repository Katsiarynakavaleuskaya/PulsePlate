# Invariant-family review episode evidence contract (Euler L2-EVAL v1)

## Purpose and authority boundary

Euler L2-EVAL v1 is a prospective, local evidence rail for one repository and
one positive pull-request number. It records whether a finding identity class
in an explicitly enrolled invariant family was first observed after the
inclusive logic/philosophy joint abstraction pass and no later than the pull
request terminal event.

The rail is descriptive only. Its timestamps, correspondences, source digests,
and cumulative inventories are human assertions. A valid artifact proves only
that the submitted assertion has the closed shape, content binding, ordering,
and local-store properties defined here. It does not authenticate an author or
time, infer semantic identity, establish causality, assess safety or
effectiveness, approve a change, resolve a review, authorize L3, or authorize a
merge. All sixteen downstream grants are literal JSON `false`. The CLI's own
fixed local create-only transport is described separately and grants no action
to a consumer.

The implementation is one standalone standard-library CLI. It does not import
or invoke L1/L2 processors, task bootstrap, Qoder/dispatch, product runtime,
GitHub/provider clients, network code, subprocesses, databases, learning,
reflection, mapping, review, or merge machinery. There is no production
consumer or workflow wiring in v1.

There is no automatic L3 decision. L3 remains closed until real prospective
observations exist and a separate future human decision opens a new scope.

## Episode and observation model

An episode is identified only by the fixed repository slug and positive PR
number. Its lifecycle is `ABSENT -> ENROLLED_AWAITING_TERMINAL ->
TERMINAL_OBSERVED`. The first valid enrollment and first valid terminal are
immutable. Byte-identical replay is accepted without a write; divergent,
partial, malformed, or unsafe state fails closed and is never repaired.

For each enrolled family `f`:

- `T_f` is the trigger identity-class set;
- `J_f` is the cumulative set at the inclusive joint-pass boundary;
- `C_f` is the cumulative set through the terminal event.

Comparable observations require `T_f ⊆ J_f ⊆ C_f`. The measured set is
`R_f = C_f - J_f`, never `C_f - T_f`. Its interval is
`(joint_pass_completed_at, terminal_event_at]`. Equality is allowed at every
adjacent timestamp boundary because the contract has one-second precision. An
identity at the joint-pass second belongs to `J_f`; one at the terminal second
belongs to `C_f`. A completed pass may therefore have an empty open interval.

Identity classes and `family_key` values are episode-local. Finding and family
IDs are phase-local. Equal spelling across phases establishes no identity:
correspondence exists only when a human places the phase-qualified IDs in the
same closed identity-class row. Splits, merges, many-to-many, disputed, fuzzy,
embedding-based, or ontology-based mappings are not inferred.

Multiple distinct L2 identity digests do not create another episode and do not
remove it from the cohort. They project recurrence as
`non_comparable/multi_trigger`. An absent terminal projects as
`unknown/missing_terminal`; no third receipt is persisted. A terminal can be
only `merged` or `closed_unmerged`. Reopen, amend, supersede, repair, delete,
post-merge observation, and `inconclusive` are outside v1.

## Joint-pass boundary

`validate` checks the exact enrollment binding, explicit trigger-to-joint
crosswalk, `T_f ⊆ J_f`, family correspondence, and timestamp ordering. It
returns a domain-separated content digest and performs no store mutation. It
also rejects validation after a terminal receipt exists, because that would
permit retrospective construction of `J`.

The operator retains the normalized baseline value and digest. A terminal with
an available baseline embeds both; `terminal` recomputes them and requires an
exact match. If the pass completed but that retained baseline is unavailable,
the result is `unknown/joint_pass_baseline_unavailable`; `J` is not recreated
from memory. If the pass did not complete before terminal, the result is
`not_applicable/not_completed_before_terminal`.

For a baseline-available terminal the whole document is validated before
episode-level precedence is applied. Confirmed families carry exact `J`, `C`,
and `C-J`; unknown and non-comparable families carry no fabricated inventory,
zero, boolean, or count. Precedence is: multi-trigger; pass not completed;
baseline unavailable; any confirmed positive; any unknown family; any
non-comparable family; otherwise observed zero.

## Cohorts and reports

`report` always scans the complete current fixed store. `cohort_as_of` is a
caller-asserted consistency boundary, not a historical filtering query. It
must be at least every enrollment, joint-pass, terminal-event, and recording
timestamp in the current receipts; otherwise `E_ORDER` is returned. The caller
cannot supply a subset or manifest.

Every enrolled prospective episode remains in `N`. Missing terminal is unknown
and remains in the eligible denominator. Multi-trigger is non-comparable and
also remains there. Only terminal-confirmed pass-not-completed episodes are
not-applicable. With `D = N - N_not_applicable` and
`I = N_positive + N_zero`, reports emit unreduced integer ratios and never
floats. A zero denominator has the closed `not_applicable/zero_denominator`
shape. Accrual labels use only `I`: `<5`, `5..9`, and `>=10`. Retrospective
references have separate status counts and never enter primary ratios or
accrual labels. Family counts are not summed as independent findings.

Reports are immutable generations. Their complete sorted manifest binds each
enrollment digest and the exact terminal digest or `missing_terminal`. A prior
generation remains valid when a formerly missing terminal is later added: its
own embedded manifest and referenced immutable receipts are validated, rather
than compared with the later store snapshot. `all_eligible_episodes_claim` is
always false because a local gitignored store does not prove the external
population.

JSON and Markdown are rendered in memory. Markdown is generated only from the
closed safe projection. Its exact bytes are hashed before the JSON report
digest is computed. The JSON/Markdown pair is published as one no-replace
directory bundle; there is no mutable `latest` pointer.

## Parser, store, and threat boundary

Input is one bounded strict UTF-8 JSON document. BOM, duplicate keys, trailing
JSON, null, floats, exponent notation, non-finite values, coercion, extra or
missing fields, booleans as integers, non-ASCII/control data, unsafe IDs,
credential-shaped values, raw paths/URLs/prose/diffs/prompts/responses/reasoning,
and provider payloads are rejected. Timestamps are calendar-valid UTC seconds
and are assertions; the module reads no system clock, environment, cwd, or
filesystem timestamp as semantic input.

The fixed store uses only full lowercase SHA-256 directory names. Shared
existing `artifacts/` parents must be owned directories with no group/world
write. The module root, lane, staging, and bundle directories are exact `0700`;
leaves are owned regular `0600` files with one link. Traversal and reads are
descriptor-relative, no-follow, bounded, and metadata-stable. Cooperative
sessions first lock the fixed `artifacts/orchestration` parent while opening or
creating the complete module-root namespace, then retain the module-root lock:
writers use nonblocking exclusive locks and `validate` uses nonblocking shared
locks. Unexpected entries, orphan stages, symlinks, special files, hardlinks,
wrong ownership/modes, unstable reads, malformed bundles, and partial report
pairs fail closed and remain untouched.

The sole private publisher stages a complete closed bundle, fsyncs and
revalidates it, then uses only the platform kernel no-replace primitive:
Linux `renameat2(RENAME_NOREPLACE)` or Darwin
`renameatx_np(RENAME_EXCL)`. Unsupported symbols/filesystems fail closed; there
is no ordinary rename, replace, hardlink fallback, overwrite, or canonical
repair. A concurrent winner is fully validated. A parent-fsync failure after a
successful rename preserves the artifact and reports durability unconfirmed as
`E_PUBLISH_FAILED`. Prepublication cleanup is limited to the exact invocation-
owned staging inode and expected children. Readers never clean old residue.

This protects a cooperative local POSIX evidence store from malformed bounded
input, traversal, link/special-file attacks, partial publication, accidental
overwrite, cooperative races, changed-during-read, unsupported publication,
and diagnostic leakage. It does not claim isolation from a continuously
hostile process under the same UID, root/privileged or mount attackers,
NFS/SMB/FUSE/cloud semantics, hardware-loss durability, authenticated
provenance/nonrepudiation, semantic DLP, backup/restore, privacy deletion,
migration, archive, or garbage collection.

## Canonical policy projection

The uniquely marked JSON object below is the machine-readable policy source.
The Python module exports a recursively frozen `POLICY_PROJECTION`; focused
tests require exact structural equality.

POLICY_PROJECTION_BEGIN
{
  "acknowledgment": {
    "common_fields": [
      "schema_version",
      "status",
      "operation"
    ],
    "operation_fields": {
      "enroll": [
        "episode_digest",
        "enrollment_receipt_digest"
      ],
      "report": [
        "cohort_id",
        "report_digest",
        "markdown_sha256"
      ],
      "terminal": [
        "episode_digest",
        "terminal_receipt_digest"
      ],
      "validate": [
        "episode_digest",
        "joint_pass_baseline_digest"
      ]
    },
    "schema_version": "invariant_family_review_episode.ack.v1",
    "status": "ok"
  },
  "authority_fields": [
    "side_effects_allowed",
    "posting_allowed",
    "thread_resolution_allowed",
    "mapping_authority",
    "implementation_authority",
    "approval_authority",
    "review_authority",
    "security_authority",
    "runtime_authority",
    "learning_authority",
    "reflection_authority",
    "kpp_authority",
    "oracle_authority",
    "routing_authority",
    "promotion_authority",
    "merge_authority"
  ],
  "claims": {
    "receipt": {
      "causal_status": "not_assessed",
      "claim_type": "descriptive_observation",
      "observation_basis": "human_digest_referenced"
    },
    "report_extra": {
      "all_eligible_episodes_claim": false
    }
  },
  "cli": {
    "exact_argv_count": 1,
    "stdin_documents": 1,
    "verbs": [
      "enroll",
      "terminal",
      "validate",
      "report"
    ]
  },
  "digest": {
    "algorithm": "sha256",
    "domains": {
      "cohort": "pulseplate.invariant-family-review-episode.cohort.v1",
      "enrollment_receipt": "pulseplate.invariant-family-review-episode.enrollment-receipt.v1",
      "episode": "pulseplate.invariant-family-review-episode.episode.v1",
      "joint_pass_baseline": "pulseplate.invariant-family-review-episode.joint-pass-baseline.v1",
      "report": "pulseplate.invariant-family-review-episode.report.v1",
      "terminal_receipt": "pulseplate.invariant-family-review-episode.terminal-receipt.v1"
    },
    "encoding": "canonical_ascii_json_without_lf",
    "separator": "NUL"
  },
  "enums": {
    "accrual_bands": [
      "collecting_lt_5",
      "interim_5_to_9",
      "target_count_gte_10"
    ],
    "episode_classes": [
      "prospective_primary",
      "retrospective_reference"
    ],
    "episode_observation_reasons": [
      "positive",
      "zero",
      "multi_trigger",
      "not_completed_before_terminal",
      "joint_pass_baseline_unavailable",
      "family_observation_unknown",
      "family_observation_non_comparable",
      "missing_terminal"
    ],
    "episode_observation_statuses": [
      "observed",
      "unknown",
      "non_comparable",
      "not_applicable"
    ],
    "family_confirmed_reasons": [
      "same_scope_confirmed"
    ],
    "family_non_comparable_reasons": [
      "family_redefined",
      "family_missing",
      "membership_disputed",
      "non_bijective_identity"
    ],
    "family_observation_statuses": [
      "confirmed",
      "unknown",
      "non_comparable"
    ],
    "family_unknown_reasons": [
      "joint_pass_baseline_unavailable",
      "human_correspondence_unresolved",
      "terminal_cumulative_inventory_incomplete"
    ],
    "joint_pass_statuses": [
      "not_completed",
      "completed_baseline_unavailable",
      "completed_baseline_available"
    ],
    "phases": [
      "trigger",
      "joint_pass",
      "terminal"
    ],
    "ratio_statuses": [
      "defined",
      "not_applicable"
    ],
    "recommended_resolutions": [
      "bounded_object_fix",
      "family_fix",
      "mechanism_fix",
      "authority_rescope",
      "no_change_required",
      "unknown_requires_human"
    ],
    "terminal_states": [
      "merged",
      "closed_unmerged"
    ]
  },
  "errors": [
    "E_USAGE",
    "E_INPUT_TOO_LARGE",
    "E_JSON_INVALID",
    "E_SCHEMA",
    "E_LIMIT",
    "E_IDENTITY",
    "E_ORDER",
    "E_DEPENDENCY",
    "E_STORE_UNSAFE",
    "E_LOCK_BUSY",
    "E_REPLAY_DIVERGENT",
    "E_PUBLISH_UNSUPPORTED",
    "E_PUBLISH_FAILED",
    "E_REPORT_MANIFEST",
    "E_STDOUT"
  ],
  "limits": {
    "aggregate_receipt_scan_bytes": 16777216,
    "enrollment_bundles": 128,
    "enrollment_receipt_json_bytes": 262144,
    "families": 32,
    "family_membership_refs": 4096,
    "hierarchy_depth_below_lane_root": 3,
    "identity_correspondence_rows_per_table": 512,
    "json_depth": 12,
    "json_nodes": 16384,
    "report_bundle_bytes": 4194304,
    "report_generations": 64,
    "report_json_bytes": 2097152,
    "report_markdown_bytes": 2097152,
    "scalar_ascii_bytes": 256,
    "source_finding_id_refs_per_document": 2048,
    "source_finding_ids": 2048,
    "staging_name_attempts": 32,
    "stderr_bytes": 4096,
    "stdin_bytes": 1048576,
    "stdout_bytes": 4096,
    "terminal_bundles": 128,
    "terminal_receipt_json_bytes": 262144,
    "trigger_identities": 16
  },
  "parser": {
    "commit_sha_pattern": "^[a-f0-9]{40}$",
    "credential_denylist_flags": "ASCII_IGNORECASE",
    "credential_denylist_pattern": "(?:access[_-]?key|aiza|ak[is]a|api[_-]?key|authorization|bearer|client[_-]?secret|credential|gh[prous]_|github[_-]?pat|gitlab[_-]?pat|glpat-|npm_|password|private[_-]?key|secret|sk-[A-Za-z0-9_-]{12,}|sk[_-]?(?:live|test|proj)|token|xapp-|xox[abcdeprst]-)",
    "digest_pattern": "^[a-f0-9]{64}$",
    "duplicate_keys": "reject_at_every_depth",
    "id_ascii_bytes": 64,
    "id_pattern": "^[A-Za-z0-9](?:[A-Za-z0-9_-]{0,62}[A-Za-z0-9])?$",
    "json_numbers": "integers_only_where_schema_allows",
    "null": "reject",
    "task_packet_id_pattern": "^[a-f0-9]{12}$",
    "timestamp_pattern": "YYYY-MM-DDTHH:MM:SSZ_calendar_valid_utc",
    "utf8": "strict_no_bom_ascii_scalars"
  },
  "policy_version": "invariant_family_review_episode.policy.v1",
  "report": {
    "accrual_basis": "identified_episode_count",
    "cohort_semantics": "complete_current_store_as_of_must_cover_every_current_receipt_boundary",
    "primary_formulas": {
      "eligible_denominator_count": "enrollment_count-not_applicable_count",
      "identified_episode_count": "positive_count+zero_count",
      "identified_coverage_ratio": "identified_episode_count/eligible_denominator_count",
      "recurrence_lower_bound_ratio": "positive_count/eligible_denominator_count",
      "recurrence_upper_bound_ratio": "(positive_count+unknown_count+non_comparable_count)/eligible_denominator_count",
      "terminal_coverage_ratio": "terminal_receipt_count/enrollment_count"
    },
    "primary_fields": [
      "enrollment_count",
      "terminal_receipt_count",
      "positive_count",
      "zero_count",
      "unknown_count",
      "non_comparable_count",
      "not_applicable_count",
      "eligible_denominator_count",
      "identified_episode_count",
      "recurrence_lower_bound_ratio",
      "recurrence_upper_bound_ratio",
      "terminal_coverage_ratio",
      "identified_coverage_ratio",
      "accrual_band"
    ],
    "ratio_shapes": {
      "defined_fields": [
        "status",
        "numerator",
        "denominator"
      ],
      "not_applicable_fields": [
        "status",
        "reason"
      ],
      "zero_denominator_reason": "zero_denominator"
    },
    "retrospective_fields": [
      "enrollment_count",
      "terminal_receipt_count",
      "positive_count",
      "zero_count",
      "unknown_count",
      "non_comparable_count",
      "not_applicable_count"
    ]
  },
  "repository_slug": "Katsiarynakavaleuskaya/PulsePlate",
  "schemas": {
    "enrollment_input": {
      "fields": [
        "schema_version",
        "episode_class",
        "pull_request_number",
        "trigger_observed_at",
        "enrollment_recorded_at",
        "material_head_sha",
        "source",
        "identity_classes",
        "families"
      ],
      "schema_version": "invariant_family_review_episode.enrollment_input.v1"
    },
    "enrollment_identity": {
      "fields": [
        "identity_class_id",
        "trigger_finding_id"
      ]
    },
    "enrollment_family": {
      "fields": [
        "family_key",
        "trigger_family_id",
        "trigger_identity_class_ids"
      ]
    },
    "enrollment_receipt": {
      "fields": [
        "schema_version",
        "policy_version",
        "repository_slug",
        "pull_request_number",
        "episode_digest",
        "enrollment_receipt_digest",
        "episode_class",
        "trigger_observed_at",
        "enrollment_recorded_at",
        "material_head_sha",
        "source",
        "identity_classes",
        "families",
        "claims",
        "downstream_grants",
        "transport_capability"
      ],
      "schema_version": "invariant_family_review_episode.enrollment_receipt.v1"
    },
    "identity_class": {
      "fields": [
        "identity_class_id",
        "phase_bindings"
      ],
      "phase_binding_fields": [
        "phase",
        "finding_id"
      ]
    },
    "joint_pass_union": {
      "completed_baseline_available_fields": [
        "status",
        "baseline",
        "joint_pass_baseline_digest",
        "identity_classes",
        "family_observations"
      ],
      "completed_baseline_unavailable_fields": [
        "status",
        "reason",
        "joint_pass_completed_at"
      ],
      "not_completed_fields": [
        "status",
        "reason"
      ]
    },
    "family_observation_input": {
      "confirmed_fields": [
        "status",
        "reason",
        "family_key",
        "terminal_family_id",
        "terminal_cumulative_identity_class_ids"
      ],
      "non_observed_fields": [
        "status",
        "reason",
        "family_key"
      ]
    },
    "family_observation_receipt_confirmed": {
      "fields": [
        "status",
        "reason",
        "family_key",
        "joint_pass_family_id",
        "terminal_family_id",
        "joint_pass_cumulative_identity_class_ids",
        "terminal_cumulative_identity_class_ids",
        "recommended_resolution",
        "post_joint_same_family_first_observed_identity_class_ids",
        "post_joint_same_family_first_observed_count"
      ]
    },
    "joint_pass_baseline": {
      "family_fields": [
        "family_key",
        "joint_pass_family_id",
        "joint_pass_cumulative_identity_class_ids",
        "recommended_resolution"
      ],
      "fields": [
        "schema_version",
        "episode_digest",
        "enrollment_receipt_digest",
        "joint_pass_completed_at",
        "identity_classes",
        "families"
      ],
      "schema_version": "invariant_family_review_episode.joint_pass_baseline_input.v1"
    },
    "report": {
      "fields": [
        "schema_version",
        "policy_version",
        "repository_slug",
        "cohort_as_of",
        "cohort_id",
        "report_digest",
        "markdown_sha256",
        "manifest",
        "prospective_primary",
        "retrospective_reference",
        "claims",
        "downstream_grants",
        "transport_capability"
      ],
      "schema_version": "invariant_family_review_episode.report.v1"
    },
    "report_manifest_row": {
      "fields": [
        "episode_digest",
        "episode_class",
        "enrollment_receipt_digest",
        "terminal_receipt_digest",
        "observation_status",
        "observation_reason"
      ]
    },
    "report_request": {
      "fields": [
        "schema_version",
        "cohort_as_of"
      ],
      "schema_version": "invariant_family_review_episode.report_request.v1"
    },
    "recurrence": {
      "non_observed_fields": [
        "status",
        "reason"
      ],
      "observed_fields": [
        "status",
        "reason",
        "value"
      ]
    },
    "source": {
      "fields": [
        "l2_task_packet_id",
        "l2_task_packet_digest",
        "l1_artifact_fingerprint",
        "l1_idempotency_key",
        "trigger_rule",
        "membership_source"
      ],
      "membership_source": "explicit_input_only",
      "trigger_rule": "explicit_family_cardinality_gte_2"
    },
    "terminal_input": {
      "fields": [
        "schema_version",
        "episode_digest",
        "enrollment_receipt_digest",
        "terminal_state",
        "terminal_event_at",
        "terminal_recorded_at",
        "terminal_material_head_sha",
        "observed_l2_identity_digests",
        "joint_pass"
      ],
      "schema_version": "invariant_family_review_episode.terminal_input.v1"
    },
    "terminal_receipt": {
      "fields": [
        "schema_version",
        "policy_version",
        "repository_slug",
        "pull_request_number",
        "episode_digest",
        "enrollment_receipt_digest",
        "terminal_receipt_digest",
        "episode_class",
        "terminal_state",
        "terminal_event_at",
        "terminal_recorded_at",
        "terminal_material_head_sha",
        "observed_l2_identity_digests",
        "joint_pass",
        "recurrence",
        "claims",
        "downstream_grants",
        "transport_capability"
      ],
      "schema_version": "invariant_family_review_episode.terminal_receipt.v1"
    }
  },
  "semantics": {
    "cohort_filtering": "none_complete_current_store",
    "episode_identity_fields": [
      "repository_slug",
      "pull_request_number"
    ],
    "lifecycle": [
      "ABSENT",
      "ENROLLED_AWAITING_TERMINAL",
      "TERMINAL_OBSERVED"
    ],
    "observation_interval": "(joint_pass_completed_at,terminal_event_at]",
    "recurrence_set_difference": "C_f_minus_J_f",
    "timestamp_order": [
      "trigger_observed_at",
      "enrollment_recorded_at",
      "joint_pass_completed_at",
      "terminal_event_at",
      "terminal_recorded_at"
    ]
  },
  "store": {
    "bundle_shapes": {
      "receipt": [
        "receipt.json"
      ],
      "report": [
        "report.json",
        "report.md"
      ]
    },
    "directory_mode": "0700",
    "file_mode": "0600",
    "layout": {
      "enrollments": "enrollments/<episode_digest>/receipt.json",
      "reports": "reports/<report_digest>/{report.json,report.md}",
      "terminals": "terminals/<episode_digest>/receipt.json"
    },
    "lock": "parent_initialization_flock_then_module_root_nonblocking_exclusive_publish_shared_validate",
    "no_replace": {
      "darwin": "renameatx_np_RENAME_EXCL",
      "linux": "renameat2_RENAME_NOREPLACE",
      "fallback": "none"
    },
    "root": "artifacts/orchestration/review_invariant_family_episodes",
    "supported_platforms": [
      "darwin",
      "linux"
    ]
  },
  "transport_capability": "fixed_local_create_only"
}
POLICY_PROJECTION_END

## Stable CLI outcome

The public commands are exactly `enroll`, `terminal`, `validate`, and `report`.
Success emits one canonical acknowledgment document plus LF. Create, exact
replay, and an identical concurrent winner intentionally produce the same
acknowledgment; the output does not make a historical creation claim. Failure
emits only one stable error code plus LF on stderr, no stdout, submitted value,
path, exception detail, or traceback. The closed error vocabulary and exact
operation-specific acknowledgment fields are part of the canonical projection.

## Retention and rollback

The CLI has no update, delete, repair, migration, archive, or garbage-collection
command. Reports are content-addressed generations. A Git revert can stop new
authoring but cannot remove ignored local evidence. Backup/restore, compliance
deletion, privacy handling, schema migration, and retention policy require
separate authority and scope. No synthetic primary episode is created by this
implementation PR, and no empirical 5/10 cohort is claimed.
