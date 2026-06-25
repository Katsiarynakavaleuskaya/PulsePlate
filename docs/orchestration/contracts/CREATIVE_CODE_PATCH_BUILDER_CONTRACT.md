# CreativeCodePatchBuildRequest / CreativeCodePatchResult Contract

Status: PR-2 local sandbox candidate-patch contract. No runtime impact.

PR-2 opens only isolated local candidate-patch generation and evaluation. It
does not authorize shared repository writes, branch creation, push, PR creation,
review-thread disposition, merge readiness, promotion, product runtime AI,
OpenAPI/client changes, Slack/GitHub authority, or public multi-tenant use.

## Artifacts

- Request schema:
  `docs/orchestration/contracts/creative_code_patch_request.v1.schema.json`
- Request reference:
  `docs/orchestration/contracts/creative_code_patch_request.v1.json`
- Result schema:
  `docs/orchestration/contracts/creative_code_patch_result.v1.schema.json`
- Result reference:
  `docs/orchestration/contracts/creative_code_patch_result.v1.json`
- Request/result validator:
  `python -m scripts.orchestration.creative_code_patch_contract`
- Local builder CLI:
  `python -m scripts.orchestration.creative_code_patch_builder`

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
