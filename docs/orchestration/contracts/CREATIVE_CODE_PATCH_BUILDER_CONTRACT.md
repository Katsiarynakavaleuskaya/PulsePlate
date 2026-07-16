# CreativeCodePatchBuildRequest / CreativeCodePatchResult Contract

Status: PR-2 local sandbox candidate-patch contract. No runtime impact.

PR-2 opens only isolated local candidate-patch generation and evaluation. It
does not authorize shared repository writes, branch creation, push, PR creation,
review-thread disposition, merge readiness, promotion, product runtime AI,
OpenAPI/client changes, Slack/GitHub authority, or public multi-tenant use.
PR-3 consumes accepted PR-2 results through a separate
`CreativeCodePRPromotion` contract; PR-2 result artifacts themselves still keep
`promotion_ready=false`.
Before PR-3 promotion planning, the local artifact lifecycle guard must pass
`assert-ready-for-promotion --patch-run-id <run-id>`. The guard validates
canonical PR-2 sidecars and current-base evidence, but it does not create,
restore, promote, or delete PR-2 artifacts.

## Artifacts

- Request schema:
  `docs/orchestration/contracts/creative_code_patch_request.v1.schema.json`
- Result schema:
  `docs/orchestration/contracts/creative_code_patch_result.v1.schema.json`
- Request/result reference contract:
  this document plus the strict schemas above
- Generation gate schema:
  `docs/orchestration/contracts/creative_code_patch_generation_gate.v1.schema.json`
- Generation receipt schema:
  `docs/orchestration/contracts/creative_code_patch_generation_receipt.v1.schema.json`
- Request/result validator:
  `python -m scripts.orchestration.creative_code_patch_contract`
- Local builder CLI:
  `python -m scripts.orchestration.creative_code_patch_builder`
- Local gate/execute wrapper:
  `python -m scripts.orchestration.creative_code_patch_generation`

## Required Source

Admission starts from a valid PR-1 `CreativeCodeSpecificationBundle`. The
request must bind exactly to the full source bundle fingerprint, source bundle
ID, source packet ID, selected variant ID, selected variant fingerprint, and the
exact `origin/main` base SHA.

The selected variant must be the deterministic PR-1 synthesis selection and
must have complete passing skeptic reviews. A selected variant alone is not
sufficient; PR-2 additionally requires an explicit human admission block:

```json
{
  "decision": "approved_for_sandbox_generation",
  "approval_ref": "operator-pr2-reference"
}
```

## Request Authority

`CreativeCodePatchBuildRequest.authority` has a narrow true set:

- `generate_candidate_patch`
- `write_isolated_workspace`
- `evaluate_candidate_patch`
- `call_local_codex_exec`

All shared repo, branch, PR, review-thread, merge, release, product runtime,
arbitrary network, OpenAPI/client, semantic-cache, public multi-tenant, and
Slack/GitHub authority flags remain false.

The executor is fixed to the local Codex CLI profile:

```text
codex exec --ignore-user-config \
  -c 'approval_policy="never"' \
  -c 'sandbox_workspace_write.network_access=false' \
  -c 'web_search="disabled"' \
  -c 'apps._default.enabled=false' \
  --sandbox workspace-write --ephemeral --json --cd <checkout> -
```

The prompt is passed on stdin and is not persisted in the request, result, or
sanitized summaries.

## Generation Gate Wrapper

`creative_code_patch_generation.py` is the local Gate+execute wrapper over the
existing PR-2 builder. It does not prepare admissions and does not implement a
second patch-result contract.

The wrapper exposes:

```bash
python -m scripts.orchestration.creative_code_patch_generation validate-run-plan \
  --admission <creative_spec_patch_admission.json> \
  --run-id <prepared-run-id> \
  --output-dir artifacts/orchestration/creative_code/patch_generation/<run-id>

python -m scripts.orchestration.creative_code_patch_generation generate-candidate \
  --gate artifacts/orchestration/creative_code/patch_generation/<run-id>/generation_gate.json

python -m scripts.orchestration.creative_code_patch_generation finalize-dispatched-result \
  --gate artifacts/orchestration/creative_code/patch_generation/<run-id>/generation_gate.json \
  --dispatch-result artifacts/orchestration/experiments/results/<experiment-result>.json
```

`validate-run-plan` writes `generation_gate.json` only after it revalidates:

- admission/source/request/finalize/human bindings;
- builder prepare proof and exact prepared run state;
- request/source bundle/selected variant identity;
- current local `origin/main` base SHA;
- clean shared worktree;
- budget, oracle, metric, allowed-path, and immutable-oracle fingerprints;
- absence of preexisting `candidate.patch`, patch metadata, experiment packet,
  or result artifacts;
- optional coordinator advisory hints as advisory-only with no role-order,
  patch-generation, provider, repo-write, PR, Slack/GitHub, product runtime,
  semantic-cache, or graph-truth authority.

`generate-candidate` must revalidate the gate immediately before execution,
call only `creative_code_patch_builder.generate(run_id=...)`, recheck current
base/tree, call only `creative_code_patch_builder.evaluate(run_id=...)`, then
write a sanitized `generation_receipt.json` that links:

- `generation_gate.json`;
- existing local `candidate.patch`;
- existing `patch_metadata.json`;
- existing `experiment_packet.json`;
- existing `result.json`;
- request/source/gate/result IDs and fingerprints;
- `patch_metadata.json` and `experiment_packet.json` fingerprints.

The receipt stores named pass/fail checks and `passed_checks` /
`total_checks`; it does not introduce subjective scores. A valid rejected
`CreativeCodePatchResult` may still produce a receipt, but `promotion_ready`
remains `false`. Builder or wrapper failures exit non-zero and must not emit a
success receipt.

On hosts where direct candidate evaluation raises the bounded Runner capability
signal after generation, `finalize-dispatched-result` is the only supported
resume seam. The operator runs the existing trusted Experiment Runner dispatcher
against the already-generated `experiment_packet.json` and `candidate.patch`,
then passes its sanitized result artifact to this command. The command does not
generate, modify, rebase, or retry the candidate.

Before publishing the canonical `result.json` and `generation_receipt.json`, the
resume seam revalidates:

- the stored generation gate and its admission, request, source-bundle, selected
  variant, budget, path, oracle, metric, and immutable-oracle bindings;
- derivation of the current generated state from the gate-bound prepared-state
  fingerprint;
- current `origin/main`, a clean shared tree, destroyed generation checkout, and
  removed checkout origin;
- exact current patch bytes, metadata, changed paths, experiment packet, and
  selected variant; the selected variant must equal the complete canonical
  variant from the validated source bundle, not merely repeat its stored ID and
  fingerprint fields;
- a dispatch result contained under
  `artifacts/orchestration/experiments/results/`, with no symlink traversal;
- normal candidate runner mode, the stable `candidate.patch` marker, exact
  experiment ID, passed execution-backend preflight provenance, one attempt,
  zero retries, packet-identical budgets and oracle commands, bounded mutated
  paths, no promotion/material-attribution claim, and an untouched shared tree;
  the packet, dispatch result, and canonical creative-code result must carry one
  recomputed patch fingerprint;
- every configured oracle passing before an accepted result can be published.
- every oracle-derived rejection binding the candidate paths and retaining the
  executed failure evidence required by its failure class.

The resume seam acquires a cooperative fd-backed per-run lock before final
revalidation and publication. A concurrent finalizer fails closed before it can
publish or roll back another invocation's result, state, or receipt artifacts;
process termination releases ownership without leaving a stale sentinel.

Rejected trusted results remain valid terminal evidence when their failure class
and observations satisfy the Experiment Runner contract. The seam persists only
the existing sanitized creative-code result and receipt projections; raw oracle
stdout/stderr, local paths, prompts, patches, provider payloads, and reasoning do
not enter those projections. A pre-existing result or receipt, stale base,
tampered sidecar, missing backend provenance, partial publication, or divergent
replay fails closed. It does not authorize a second generation attempt.
If bounded publication fails, receipt removal, state restoration, and result
removal are attempted independently so one cleanup error cannot suppress the
remaining rollback actions. Receipt rollback removes only content matching the
current invocation, preserving a colliding foreign artifact; any incomplete
rollback remains an explicit terminal error.

`validate-artifacts` must re-read the linked local sidecars before reporting
success. It recomputes the current `candidate.patch` summary, validates
`patch_metadata.json` with an exact key set, validates `experiment_packet.json`
through the Experiment Runner packet contract, requires every sidecar ref to be
the canonical file under `patch_runs/<receipt.run_id>/`, and compares all
sidecar fingerprints against the receipt. Cross-run sidecar refs, sidecar
drift, unexpected metadata keys, unsafe text, changed packet budgets/oracles,
or stale result metadata fail the receipt validation.

The wrapper must not expose commands or flags that promote candidates, write
branches, push, open or edit PRs, resolve review threads, edit fixed mappings,
claim readiness, merge, release, call providers, call product runtime, modify
workflows, use semantic cache, write graph truth, or mutate Slack/GitHub App
settings.

## Workspace Lifecycle

The builder must:

- verify the request base SHA equals current local `origin/main`;
- reject dirty shared worktrees before generation;
- clone with `git clone --no-hardlinks`;
- check out the exact base SHA in detached mode;
- remove `origin` and verify no remotes remain;
- export `candidate.patch` only above the generation checkout under gitignored
  creative-code artifacts;
- destroy the generation checkout in a `finally` path;
- expose `cleanup --run-dir <run>` that removes only the contained run directory.

Ordinary derived cache cleanup is allowed. Cleanup of
`artifacts/orchestration/creative_code/**` requires
`creative_code_artifact_inventory.py assert-ready-for-cleanup` to pass first;
that guard is read-only and never deletes artifacts.

## Patch Policy

Patch validation must inspect git status, name-status, raw mode records,
numstat, summary, whitespace checks, and clean `git apply --check` before
Experiment Runner handoff.

PR-2 rejects:

- no-op, empty, malformed, or already-applied candidates;
- deletions, renames, copies, type changes, binary diffs, mode changes,
  executable-bit changes, symlinks, submodules, `.gitmodules`, and git metadata;
- untracked files outside `allowed_new_paths`;
- paths outside the selected variant target paths;
- overlap with immutable oracle paths;
- governance, review, security, CI, tests, AGENTS, OpenAPI/client, frontend,
  iOS, DB, dependency, local artifact, and worktree surfaces;
- budget breaches: one generation attempt, default max 3 changed files, hard max
  5 changed files, max diff lines, and max patch bytes.

## Runner Integration

`evaluate` builds a normal candidate-mode experiment packet with
`experiment_bootstrap.build_experiment_packet(...)` and calls
`experiment_runner.evaluate_candidate(packet, candidate_patch_path)` directly.
It must not call `experiment_pipeline.py`, oracle-only runner mode, notification
wrappers, promotion wrappers, GitHub/Slack actions, or review-thread tooling.

PR-2 candidate evaluation artifacts are local evidence for the builder only.
They are not PR Experiment Runner oracle-only governance evidence, fixed-mapping
evidence, review disposition evidence, merge-readiness evidence, product runtime
truth, or promotion authority.

PR-3 may later validate and promote an accepted PR-2 result only through
`docs/orchestration/contracts/CREATIVE_CODE_PR_PROMOTION_CONTRACT.md`. That
separate lane requires a promotion plan, isolated pre-open validation, explicit
TTY approval, new `experiment/*` branch, non-draft PR creation, and GitHub
readback. It does not change PR-2 authority.

## Sanitized Result

`CreativeCodePatchResult` stores only:

- status and failure class;
- selected source identifiers and fingerprints;
- changed repo-relative paths;
- patch fingerprint, byte count, and diff-line count;
- workspace proof booleans;
- runner status/count/fingerprint metadata;
- explicit non-authority flags.

It must not store raw patch text, raw Codex output, prompts, provider payloads,
oracle stdout/stderr, local absolute paths, GitHub/Slack IDs, secrets, tokens,
or reasoning.

## Rollback

Rollback removes the PR-2 request/result contracts, patch-builder scripts, tests,
and PR-2 references. Because PR-2 adds no product runtime behavior, providers,
workflows, external app settings, OpenAPI/client changes, semantic-cache
activation, shared repo-write automation, or DB state, rollback requires no data
migration, OpenAPI regeneration, Slack/GitHub App change, or release
coordination.
