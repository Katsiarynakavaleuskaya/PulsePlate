# PR Evidence Sidecar v1

## Purpose and boundary

`scripts/orchestration/pr_evidence_sidecar.py` records a local, immutable start
receipt after task bootstrap and an optional terminal receipt after a PR reaches
`merged` or `closed_unmerged`. It can aggregate structural integer counts over
the whole bounded local store. The receipts are gitignored operational records,
not repository, GitHub, review, CI, release, enrollment, causality, external
terminal-semantics, promotion, or merge authority.

The first eligible receipt belongs to the next freshly started lane after this
contract lands. This PR must not manufacture a retrospective receipt for
itself. PR #2341 remains a distinct docs-only work result; it is neither a start
nor terminal receipt for this implementation lane.

## Fixed storage and identity

The only store is:

```text
artifacts/orchestration/pr_evidence_sidecars/<sha256-id>/start.json
artifacts/orchestration/pr_evidence_sidecars/<sha256-id>/terminal.json
```

There is no root override. The start identity binds the v1 schema and policy,
repository identity, task-packet id, raw packet-byte SHA-256 fingerprint,
lowercase 40-character base commit, and exact applicable-rail set. Directories
are private and files are mode `0600`. Publication is atomic and no-replace:
an identical canonical replay performs no write, while divergent content fails.
Public operations cooperate through one process-local reentrant lock plus a
shared/exclusive `flock` on a no-follow directory descriptor for the fixed
store. Prepare/finalize hold the exclusive lock through publication and
postvalidation; validate/report hold the shared lock through complete reads.
Canonical receipts are visible only with link count one, while external
hardlinks remain invalid.
Each receipt is staged as one unique mode-`0600` file in the fixed sibling
`artifacts/orchestration/` directory, then published with Darwin
`renameatx_np(RENAME_EXCL)` or Linux `renameat2(RENAME_NOREPLACE)` across safely
opened directory descriptors. The destination directory is fsynced. A crash
before rename can leave only that out-of-store stage; a crash after rename
leaves a canonical link-count-one receipt. Finalization removes only its own
inode-bound remaining stage and never sweeps arbitrary residue.
V1 deliberately has no link/unlink fallback: if the platform no-replace rename
symbol is unavailable, publication fails closed as `STORAGE_UNAVAILABLE` because
a crash between link and unlink could expose a canonical receipt plus an extra
stage alias.
Prepare accepts only the canonical packet path
`artifacts/orchestration/task_packets/<task_packet_id>.json`; the filename must
match the parsed id. Packet, terminal-input, and receipt reads use bounded
descriptor reads with no-follow semantics and reject linked or replaced paths.

## Commands

```bash
$VENV_PYTHON scripts/orchestration/pr_evidence_sidecar.py prepare \
  --packet artifacts/orchestration/task_packets/<id>.json \
  --base-sha <lowercase-40-sha> \
  --applicable-rail experiment_runner

$VENV_PYTHON scripts/orchestration/pr_evidence_sidecar.py finalize \
  --sidecar-id sha256:<64-lowercase-hex> \
  --terminal-input <repo-relative-terminal-input.json>

$VENV_PYTHON scripts/orchestration/pr_evidence_sidecar.py validate \
  --sidecar-id sha256:<64-lowercase-hex>

$VENV_PYTHON scripts/orchestration/pr_evidence_sidecar.py report
```

`prepare` accepts repeatable applicability rails from the closed set
`teleology`, `euler`, and `experiment_runner`. The starter includes
`experiment_runner` by default. Starter integration is advisory: unavailable
storage/tooling is rendered as `unavailable`, and malformed/conflicting output
as `invalid`; either state continues bootstrap without creating authority.

## Terminal truth

The exact terminal input records a positive PR number, operator-supplied
`observed_pr_terminal_state` (`merged` or `closed_unmerged`), material head, a
state-compatible merge SHA, all three rail records, and bounded mechanical
`operator_observations`. Each rail has exactly one valid shape:

| Applicable | Status | Reference fingerprint |
| --- | --- | --- |
| `false` | `not_applicable` | `null` |
| `true` | `referenced` | full `sha256:<64>` |
| `true` | `unknown` | `null` |

Applicability must exactly match the start receipt. Operator minutes are a
nonnegative integer or `unknown`; review cycles and repair cycles are
nonnegative integers. The terminal receipt adds the exact start fingerprint,
`causal_status=not_assessed`, a false authority map, and its own fingerprint.
Reference fingerprints are explicitly non-verifying. The sidecar does not
semantically verify referenced records or claim that the observed state was
caused by any rail.

GitHub owns authenticated PR state, repository review governance owns review
semantics, and `CreativeCodeTerminalOutcome` owns its separate creative-code
terminal/outcome semantics. `observed_pr_terminal_state` is only an
operator-supplied local observation. It is not verified, authenticated, or
authoritative, even when its merge-SHA shape passes the local cross-field rule.

## Threat model and report behavior

The parser rejects BOMs, invalid UTF-8, duplicate keys, trailing content,
unknown schema keys, wrong primitive types, oversized inputs, traversal,
symlinks, hardlinks, and nonregular files. The reporter validates every store
directory and receipt before emitting stdout. Any unknown or malformed entry
fails the whole report with no partial counts. Starts without terminals count
as `start_only_receipts`. One report accepts at most 128 discovered sidecar
directories and processes them in sidecar-id order. Output contains integer
counts and totals only—no averages, GO/NO-GO, causality, enrollment, or quality
inference.
Exclusive prepare enforces the same strict root index before creating a new id
directory. Exact replay is allowed at capacity; a distinct id is rejected
before directory creation.

Validation reports only `receipt_state=start_recorded|terminal_recorded`.
Aggregate keys are qualified as `start_receipts`, `terminal_receipts`,
`start_only_receipts`, `observed_merged`, and
`observed_closed_unmerged`, plus `operator_minutes_unknown`. Totals are
`operator_minutes_known`, `review_cycles`, and `repair_cycles`; these names do
not authenticate external state.

The filesystem boundary covers at-rest aliases and cooperating local sidecar
processes. It does not claim protection against a hostile same-UID process that
continuously replaces parent directories between syscalls; widening that
threat model requires a separate portability and hardening lane. The gitignored
store is not durable evidence: deletion or loss removes only local support
records and cannot change repository, PR, review, CI, or product truth.

This is a structural sidecar, not a replacement for TaskNormative N1
`p1-05`, any future N2 gate, the paused Euler cohort/admission boundary, or
Experiment Runner evidence. Those rails and their authorities remain unchanged.
