# Agent instructions (scope: scripts/ and subdirectories)

## Scope and layout

- This AGENTS.md applies to: `scripts/` and below.
- Scripts are repo automation utilities; run from repo root.

## Conventions

- Treat scripts as production automation: avoid breaking flags or outputs.
- Prefer small, focused edits; update any dependent docs or Make targets if needed.
- Avoid adding network calls to scripts used in CI unless explicitly required.

## Governed Experimentation Runner

- Canonical entrypoints for the experimentation lane are `scripts/orchestration/experiment_bootstrap.py` and `scripts/orchestration/experiment_runner.py`.
- Run both scripts from repo root so path validation and artifact resolution stay deterministic.
- `experiment_runner.py` accepts a validated packet plus a prebuilt unified diff
  via `--packet <packet.json> --candidate-patch <candidate.patch> [--output ...]`
  for default `candidate_patch` mode.
- In `oracle_only_governance_reviewer` mode, `experiment_runner.py` accepts
  `--packet <packet.json> [--output ...]` without `--candidate-patch`, runs only
  immutable oracle commands in an isolated checkout, applies the current tracked
  worktree diff to that checkout for evidence freshness, and writes a local
  evidence artifact. This mode is mandatory evidence for non-trivial PRs, but
  remains review-only authority: it must not promote, resolve review threads,
  claim merge readiness, or mutate governance surfaces.
- Experiment Runner PR creative-context artifacts stay local under
  `artifacts/orchestration/experiments/creative_context/`. The
  `experiment_runner_pr_creative_context.py` CLI may only emit sanitized
  context maps, 3-5 bounded hypotheses for eligible orchestration/creative
  surfaces, validated operator-supplied local model intake packets,
  coordinator-owned routing proposals, coordinator dispatch handoffs, oracle
  attachment summaries, and human-approval reservations. Operator intake is
  local structured JSON only: the repo validates, normalizes, fingerprints, and
  routes it without calling a provider/model, storing raw model payloads, or
  trusting external hypothesis IDs. It must not read raw PR/review bodies,
  patches, prompts, provider payloads, Codex JSONL, oracle stdout/stderr,
  secrets, token values, or local absolute paths, and it must not generate
  patches, modify the worktree, change workflows, dispatch workflows, create or
  write branches, push, open PRs, edit PR bodies, post comments, resolve review
  threads, edit fixed mappings, claim readiness, merge, release, call providers,
  call product runtime, use semantic cache, or mutate GitHub App / Slack
  settings. The post-open Codex Security / review chain is
  single-pass-per-material-diff; later comments use fixed mapping and targeted
  gates unless the security-relevant diff changes, the coordinator records an
  evidence-backed reroute, or the operator explicitly requests another run.
- Approved creative-hypothesis specification bridge artifacts stay local under
  `artifacts/orchestration/creative_code/spec_bridge/`. The
  `creative_hypothesis_spec_bridge.py` CLI may only consume validated
  creative-context context maps, hypothesis packets, coordinator dispatch
  handoffs, and human approval packets; emit a validated
  `creative_hypothesis_specification_bridge.json`,
  `CreativeCodeCandidatePacket`, deterministic `bridge_metrics.json`, and
  existing PR-1 `creative_code_spec_pipeline.prepare` artifacts; and validate
  those artifacts. It must not widen `CreativeCodeCandidatePacket.target_surface`
  beyond the existing `validate_mutable_candidate_surface(...)` allowlist,
  execute agents, finalize bundles, generate patches, create/write branches,
  push, open or edit PRs, resolve review threads, edit fixed mappings, claim
  readiness, merge, release, call providers, call product runtime, change
  workflows, use semantic cache, write graph truth, or mutate GitHub App /
  Slack settings.
- Reviewed creative-code specification finalization artifacts stay local under
  `artifacts/orchestration/creative_code/spec_bridge/<bridge-id>/spec_finalize_reviewed/`.
  The `creative_specification_skeptic_review.py` CLI may only read a prepared
  bridge run, read operator-supplied sanitized local skeptic-review evidence,
  copy immutable `spec_prepare/` inputs into the sibling reviewed run,
  normalize `skeptic_reviews.json`, call the existing PR-1
  `creative_code_spec_pipeline.finalize`, and emit
  `skeptic_review_attachment.json` plus `finalize_receipt.json`. It must not
  rewrite `spec_prepare/`, execute agents, call providers, generate patches,
  create/write branches, push/open PRs, edit fixed mappings, resolve review
  threads, modify workflows, call product runtime, use semantic cache, write
  graph truth, or claim readiness.
- Creative spec learning rollup artifacts stay local under
  `artifacts/orchestration/creative_code/learning_rollup/<rollup-id>/`. The
  `creative_spec_learning_rollup.py` CLI may only read validated bridge
  metrics, skeptic-review attachment, finalize receipt, and
  `CreativeCodeSpecificationBundle` artifacts; emit proposal-only
  `agent_learning_record.v1` records and coordinator advisory hints; and
  validate those local artifacts. Hints may be surfaced in `task_bootstrap.py`
  packets with `--creative-learning-hints`, but only as reviewer-focus context.
  They must not change primary/reviewer/role order, execute agents, auto-route
  roles, skip required roles, generate patches, create/write branches,
  push/open PRs, post GitHub comments, edit fixed mappings, resolve review
  threads, claim readiness, merge, release, call providers, call product
  runtime, use semantic cache, write graph truth, or mutate GitHub App / Slack
  settings.
- Creative spec patch admission artifacts stay local under
  `artifacts/orchestration/creative_code/patch_admission/<admission-id>/`. The
  `creative_spec_patch_admission.py` CLI may only read validated finalized
  creative-spec bundle and receipt artifacts plus an explicit operator human
  admission, build an existing PR-2 `CreativeCodePatchBuildRequest` through
  `build_creative_code_patch_build_request(...)`, validate the request, and
  optionally call patch-builder `prepare` only. It must not call patch-builder
  `generate` or `evaluate`, call Codex, produce `candidate.patch`, execute
  Experiment Runner candidate mode, promote candidates, create or write
  branches, push/open PRs, resolve review threads, edit fixed mappings, claim
  readiness, merge, release, call providers, call product runtime, modify
  workflows, use semantic cache, write graph truth, or mutate GitHub App / Slack
  settings.
- The runner must apply patches only inside an isolated temporary checkout and must leave the shared working tree untouched.
- Mutable surfaces, immutable oracles, budgets, and promotion boundaries are defined by `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`; do not duplicate or relax them here.
- Runner mutation of `scripts/ci/**`, `docs/review/**`, `AGENTS.md`, merge
  gates, review-thread scripts, tests, fixtures, or policy docs is forbidden
  unless a separate threat-model PR explicitly opens a narrow allowlist with
  tests and rollback notes.
- The current validator-script mutation threat model is fail-closed: no active
  runner mutation of `scripts/ci/**` is allowed until a later PR promotes a
  reviewed allowlist, forbidden-surface tests, identity checks, and rollback
  notes.
- Result artifacts stay local under `artifacts/orchestration/experiments/results/` and are evidence only, not merge-ready or promotion-ready output.
- `experiment_runner_dispatch.py` is the strict local backend boundary for
  macOS Experiment Runner execution. It may probe, build the dedicated local
  image, create a self-contained temporary repository snapshot, and execute the
  existing runner only after one backend passes capability checks. `auto`
  precedence is Apple Container then Docker; backend selection is final before
  oracle execution. The dispatcher must never change `network_budget`, retry
  with network access, add broad Linux capabilities, mount host home/keychain/
  agent/runtime sockets, persist raw runtime output, or treat capability/result
  artifacts as readiness or promotion authority. Missing strict isolation is
  `capability_mismatch`, not `infra_flake`.
- Strict dispatch requires `network_budget=0` and container-equivalent
  filesystem containment. The existing native Linux Runner remains compatible,
  but `native-linux` capability probing must report
  `filesystem_isolation_unavailable` until that containment is implemented.
- Container-backed dispatch must not expose a host-writable result bind to the
  untrusted runner. Use a private named volume, force-delete the uniquely named
  runner after PID 1 exits, and extract the bounded regular result through a
  separate read-only trusted collector inside guest `unshare`; delete the
  volume on every path. Apple gateway canaries must use runtime network inspect,
  never a hard-coded host address.
- PR-2 creative-code patch-builder artifacts stay local under
  `artifacts/orchestration/creative_code/patch_runs/`. The builder CLI
  `creative_code_patch_builder.py` is not role dispatch, PR lifecycle
  automation, merge governance, or promotion authority. Its `evaluate` command
  may call Experiment Runner candidate-patch mode for local candidate evaluation,
  but that result is not the mandatory PR oracle-only governance evidence and
  must not be used as fixed-mapping, review-disposition, or merge-readiness
  proof.
- PR-2 creative-code generation gate artifacts stay local under
  `artifacts/orchestration/creative_code/patch_generation/`. The
  `creative_code_patch_generation.py` CLI may only validate an already prepared
  patch admission, emit `generation_gate.json`, call the existing PR-2 builder
  `generate` / `evaluate` commands through `generate-candidate`, and emit a
  sanitized `generation_receipt.json`. Receipt validation must re-read linked
  `candidate.patch`, `patch_metadata.json`, `experiment_packet.json`, and
  `result.json` sidecars, require them to be the canonical files under the
  receipt's `patch_runs/<run_id>/` directory, and fail closed when any sidecar
  drifts or carries unsafe/unsupported metadata. It must not change role order,
  mark role passes complete, create/write branches, push/open PRs, resolve
  review threads, edit fixed mappings, claim readiness, promote candidates, call
  providers, call product runtime, modify workflows, use semantic cache, write
  graph truth, or mutate GitHub App / Slack settings.
- PR-3 creative-code PR promotion artifacts stay local under
  `artifacts/orchestration/creative_code/promotions/`. The promoter CLI
  `creative_code_pr_promotion.py` may only plan, validate, TTY-approve, and
  promote one accepted PR-2 patch into a new non-draft `experiment/*` PR. It
  must not open drafts, update existing branches, force-push, request reviews,
  submit reviews, resolve review threads, edit fixed mappings, claim merge
  readiness, merge, release, call Slack/GitHub App authority paths, or call
  `experiment_pipeline.py`, `experiment_promote.py`, or notification wrappers.
- PR-4 creative-code telemetry artifacts stay local under
  `artifacts/orchestration/creative_code/telemetry/`. The telemetry CLI
  `creative_code_telemetry.py` may only read already-sanitized local PR-1/PR-2
  / PR-3 creative-code artifacts and emit advisory event/rollup/taxonomy
  sidecars. It must not read raw patches, prompts, provider payloads, oracle
  stdout/stderr, Slack/GitHub payloads, review-thread bodies, PR bodies,
  secrets, token values, or local absolute paths, and it must not create
  branches, open PRs, resolve review threads, edit fixed mappings, claim merge
  readiness, merge, release, call providers, call product runtime, or call
  Slack/GitHub authority paths.
- PR-5 creative-code review-disposition artifacts stay local under
  `artifacts/orchestration/creative_code/review_disposition/`. The
  `creative_code_review_disposition.py` CLI may only read sanitized
  `pr_review_context.py` output or explicit read-only fixtures and emit
  advisory feedback-record, disposition-packet, and repair-launch sidecars. It
  must not preserve raw review bodies, PR bodies, patches, prompts, provider
  payloads, oracle output, secrets, token values, or local absolute paths, and
  it must not call GitHub write endpoints, resolve review threads, edit fixed
  mappings, create branches, write branches, push, open PRs, claim merge
  readiness, call providers, call product runtime, or call Slack/GitHub App
  authority paths.
- PR-6 creative-code applied-candidate run-plan artifacts stay local under
  `artifacts/orchestration/creative_code/applied_candidates/`. The
  `creative_code_applied_candidate_pr6.py` CLI may only validate PR-5
  `CreativeCodeRepairLaunchPacket` inputs, bind the first applied candidate
  target to `docs/prompts/cv/program.md`, and emit a deterministic local
  PR-1 / PR-2 / PR-3 / PR-4 command checklist. It must not execute patch
  generation, call Codex or providers, create or write branches, push, open PRs,
  resolve review threads, edit fixed mappings, claim merge readiness, merge,
  release, call product runtime, change GitHub App or Slack settings, or widen
  the generated candidate mutation surface beyond the selected prompt/program
  document.
- Creative-code private-pilot loop artifacts stay local under
  `artifacts/orchestration/creative_code/private_pilot/`. The
  `creative_code_private_pilot_loop_operator.py` CLI may only read sanitized
  GitHub PR/head/check/run metadata, read already-sanitized PR-4 telemetry /
  PR-5 review-disposition / PR-6 run-plan refs, compare current-head check/run
  SHAs to the PR head SHA, and emit `pilot_state.json` plus checklist-only
  `candidate_plan.json` artifacts. It must not read raw PR/review bodies,
  execute PR-1 / PR-2 / PR-3 commands, generate candidates, create or write
  branches, push, open PRs, resolve review threads, edit fixed mappings, claim
  readiness, merge, release, call providers, call product runtime, change
  workflows, read secrets, use semantic cache, or change GitHub App / Slack
  settings. Candidate plans remain bound to `docs/prompts/cv/program.md` as the
  only checklist-only candidate-plan target surface.
- `experiment_notify.py` follows the notification contract in
  `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`: local artifact output
  is the default, SMTP email and Slack delivery are explicit opt-in only, and no
  notification sink may expose raw patches, oracle stdout/stderr, secrets,
  absolute local paths, or user data. Slack delivery must remain channel
  allowlisted, runtime-secret backed, timeout/rate/idempotency bounded, and
  audit-backed.
- `experiment_slack_socket_bridge.py` is an operator-only Socket Mode command
  boundary, not a lane-start authority. It must keep Slack SDK/Bolt imports
  optional and lazy, run `--help` and dry-run validation without optional Slack
  packages, require runtime Socket Mode/bot credentials only for live use, and
  require channel plus user allowlists before handling operator input. Default
  dispatch mode must stay dry-run; execute mode may dispatch only fixed
  allowlisted workflows with explicit GitHub runtime auth. Audit artifacts must
  stay local and hash-only, with no raw Slack payloads, tokens, channel/user
  IDs, local absolute paths, oracle output, patch text, or raw hypotheses.
- `experiment_pipeline.py` is the governed completion wrapper for
  runner -> promotion -> notification sequencing. Email reports are automatic
  only inside that wrapper when `--email-reports` is explicitly present; the
  wrapper must use the fixed governed v1 recipient and must delegate SMTP,
  redaction, idempotency, and audit behavior to `experiment_notify.py`.
- Experiment Runner Git attribution must follow
  `docs/orchestration/GOVERNED_NON_HUMAN_IDENTITY_POLICY.md`; placeholder
  identities such as `runner@example.com` are not allowed for new attribution.
  When Experiment Runner materially contributes to a commit, use exactly:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.
  Oracle-only results can be material contributions even when
  `mutated_paths: []`; use the trailer only when the referenced result artifact
  actually shaped the plan, validation, mapping, review disposition, or commit
  decision.
- `scripts/orchestration/check_experiment_runner_identity.py` validates the
  machine-readable identity policy. It must remain offline, deterministic, and
  must not generate, read, or persist signing key material.
- `role_dispatch_bridge.py` is the runtime-agnostic custom role dispatch
  manifest CLI. The older `qoder_dispatch_bridge.py` filename is a compatibility
  facade only; new packets should point at `role_dispatch_bridge.py`.
- `creative_pilot_workspace.py` is the local adaptive production-adjacent
  planning entrypoint. It may bind one or two exact tracked files only under
  `core/rag/` or `core/insight/`, reuses the existing mutable-surface validator
  unchanged, and writes only gitignored adaptive-pilot artifacts. All pilot
  dispatch items are read-only. Handoff approval requires an interactive TTY
  and exact phrase; provider, patch, repository, runtime, cache, graph-truth,
  GitHub, Slack, review-thread, and merge authority stay closed.
- `creative_pilot_workspace resume-pr1` may consume one retained, approved v2
  pilot and exact `CreativeAdaptivePr1VariantIntakeV1` declarations only after
  current `origin/main`, target blobs/content, and immutable-oracle
  blobs/content match the retained target manifest. It publishes a new-only
  `spec_bridge/<resume-id>/` bundle through complete staging and leaves the
  original adaptive pilot byte-identical. Identical replay is no-write;
  all prepared sidecars are recomputed and compared, and nested symlinks,
  partial, divergent, or stale bindings fail closed. The adaptive
  context/packet/workspace/synthesis/approval/bridge/candidate lineage and
  terminal `handoff_ref` must be reconstructed before source fingerprinting;
  valid-but-substituted artifacts fail closed before publication. Resume and
  intake pilot IDs plus all original candidate/source/prepare refs must bind to
  one exact `adaptive_pilots/<pilot-id>/` root. Adaptive downstream
  attach/validate/finalize re-entry must reuse complete exact-prepare validation
  so altered context packs or re-fingerprinted pending reviews fail closed. The
  adaptive
  source bindings must come from the validated in-memory lineage and canonical
  retained-prepare snapshots, with pinned disk revalidation before replay and
  immediately before atomic publication; a second unconstrained source read
  must never become binding truth. Publication must use an atomic kernel
  no-replace directory rename and fail as `adaptive_publish_collision` rather
  than replacing any concurrent canonical resume directory. The adaptive
  intake identity is the documented compatibility alias for existing
  attachment `metrics_*` fields; no fake v1 metrics artifact or widened
  attachment/finalize schema is allowed. Patch/provider/network/runtime/cache,
  graph-truth, repository, GitHub, Slack, PR-2, and PR-3 authority remain false.
- Adaptive resume/attach hardening stops at cooperative locking, safe at-rest
  no-symlink reads, owned same-parent staging, kernel no-replace publication,
  parent fsync, and deterministic replay validation. Finalize commits bundle
  then receipt-last. Do not add directory exchange, canonical cleanup,
  hostile same-UID syscall-seam tests, or repeated terminal/path/ctime seals;
  those exceed the local artifact threat model and require a separate reviewed
  threat-model lane if ever needed.
- The role dispatch bridge treats `readonly: true` in `.cursor/agents/*.md` as
  the safe default. In `--mode runtime`, write-capable dispatch for a native
  bridge `execution_mode: read_write` primary/secondary role must be explicit
  via repeated `--implementation-owner <role>` flags on a coordinator packet
  invocation (`--packet ...`); ad-hoc `--roles` invocations must fail closed.
  The accepted owner slugs must stay aligned with native read-write profiles in
  `scripts/orchestration/native_subagent_bridge.py`, and the CLI must validate
  requested owners against the packet bridge bindings before clearing readonly.
  The manifest records `implementation_owner_override: true` for those entries.

## Pre-push backend tests (smart diff runner)

The `run-backend-tests-pre-commit.sh` script is used by pre-commit framework to run backend pytest only when Python files changed.

First-class repo wrappers:

- `make validate-changed` is the supported repo-root command for this diff-based path and runs the script with the repo `.venv` on `PATH`.
- `scripts/quick_check.sh` is a separate convenience helper: it runs `make validate-min` first, then staged-file format/import/syntax checks.
- `scripts/orchestration/local_session_bootstrap.sh` is an **opt-in** raw-session helper: runs `check_preflight.py --mode analyze` from repo root and prints how to invoke `task_bootstrap.py`. It does not replace a machine-local launcher and does not auto-start Codex/Cursor sessions.

**Coordinator cold-start precedence (host):**

1. Opt-in **machine-local launcher** (operator-installed; see `docs/dev/LOCAL_COORDINATOR_LAUNCHER_ROLLOUT.md` + `docs/templates/pulseplate-coordinator-launch.example.sh`)
2. Repo helper `scripts/orchestration/local_session_bootstrap.sh` (preflight + printed recipe)
3. Direct `python3 scripts/orchestration/task_bootstrap.py ...` after `check_preflight.py`
- `scripts/orchestration/local_support_plane.py` is an **experimental non-canonical** operator KV store under gitignored `artifacts/orchestration/local_support_plane/` (override via `LOCAL_SUPPORT_PLANE_ROOT`). Mutations require `AGENT_CONTROL_ALLOWLIST` to include `local_support_plane:artifacts_kv` and a compatible `AGENT_CONTROL_EXECUTION_MODE` (see `app/security/agent_control_plane.py`). It is not orchestration SoT.
- **Advisory wiki compiler** (local-only, gitignored): `wiki_ingest.py`, `wiki_query.py`, `wiki_lint.py`, `wiki_promote.py` under `scripts/orchestration/` with shared `_wiki_compiler_support.py`. Writes markdown under `artifacts/orchestration/wiki/` and may mirror metadata to the support plane using `wiki.*` keys. See `docs/orchestration/LOCAL_WIKI_SUPPORT_PLANE.md`.

**Change detection order:**

1. If upstream exists: diff `upstream..HEAD`
2. Else: diff from merge-base against (origin/main|origin/master|main|master)
3. If base cannot be resolved: fallback to last N commits (diagnostic mode)

**Debug mode:**

- Set `PREPUSH_DEBUG=1` to print resolved upstream/base and file list
- Example: `PREPUSH_DEBUG=1 git push` will show detailed change detection info

**Skip tests:**

- Set `SKIP_TESTS=1` to bypass backend tests (useful for documentation-only commits)

## Evaluation validity

For evaluation-validity work, follow `docs/evals/PULSEPLATE_EVAL_VALIDITY_CONTRACT.md`.
Eval artifact sidecars with predictable filenames must use symlink-safe,
fail-closed writers. Eval JSONL validators must reject malformed fields with
`ValueError`, must not coerce raw values into accepted schema fields, and must
defensively copy validated mutable containers.

## Security/dev-tooling regression guards

When touching Makefile devcontainer project-name generation, dependency audit
helpers, dependency-submission filters, CI risk routing, or eval artifact
writers, update the focused guards in
`tests/guards/test_security_devtooling_regression_guards.py`. Optional
RAG/vector dependency profiles must be covered consistently by pip-audit,
Python dependency submission, and CI risk-profile routing.
