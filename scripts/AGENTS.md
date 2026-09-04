# Agent instructions (scope: scripts/ and subdirectories)

## Scope and layout

- This AGENTS.md applies to: `scripts/` and below.
- Scripts are repo automation utilities; run from repo root.

## Conventions

- Treat scripts as production automation: avoid breaking flags or outputs.
- Prefer small, focused edits; update any dependent docs or Make targets if needed.
- Avoid adding network calls to scripts used in CI unless explicitly required.

## Prometheus derivative candidate

- `scripts/ci/prometheus_derivative_candidate.py` is the only public CLI and
  owns every expected value, source/execution identity, canonical digest,
  receipt, state transition, operator confirmation, publication decision, and
  fail-closed result for the candidate lane.
- `scripts/ci/_prometheus_derivative_transport.py` is a private one-way
  dependency. It may execute only controller-built absolute argv/process and
  HTTP/OCI plans, return structural observations, and perform the one bounded
  login/push/logout primitive. It must not import the controller, expose a CLI,
  discover environment credentials, define policy/state vocabulary, compare
  accepted evidence, or write canonical state.
- The controller derives its fixed state root below `artifacts/security_lab/`;
  no public output-root, tool-path, registry, schema, or state override is
  allowed. Each of the two modules must remain below 1400 physical lines; this
  is a hard bounded-carrier ceiling, not permission to add a third module or
  duplicate controller authority in the transport.
- `authorize` reads one exact line from stdin and atomically authors receipt
  `40-publication-authorization`. `publish-or-reconcile` takes no confirmation;
  only the invocation creating `50-write-intent` may read the fixed runtime
  credential and reach the single push primitive. Existing `50` is anonymous,
  zero-credential, zero-push reconciliation.
- Candidate construction/publication has no selector, Compose, deploy,
  release, or `T0` authority. The selected Prometheus manifest remains
  byte-frozen; all three canonical Compose consumers are content-bound and
  rechecked before receipts 50 and 80, and the four authority flags are derived
  from that bounded observation rather than caller input.
- The authorization tuple binds the private transport, exact Python
  interpreter, Apple system/apiserver identity, and post-build builder-image
  digest. `CONTAINER_HOST` is forbidden. Trivy scans only a validated extracted
  OCI layout with a fresh private database cache, explicit empty policy inputs,
  positive OS/prometheus/promtool coverage, and zero HIGH/CRITICAL findings.
- Receipt files use kernel atomic no-replace rename from staging outside the
  candidate directory; a hardlink-based publication window is forbidden.

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
  settings. The post-open role pass and repo-native `pulseplate-pr-review`
  remain required; provider-neutral sealing must not invoke, retry, wait for,
  substitute, or override Connector or Codex Security.
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
- On macOS, `oracle_only_governance_reviewer` is stricter than the general
  backend order: `run` requires explicit `--backend apple-container`. `auto`,
  `docker`, and `native-linux` are rejected before any runtime probe or result
  write, and an Apple capability failure is terminal `capability_mismatch`
  without Docker fallback. General probe, candidate-patch, and negative-control
  Docker surfaces remain supported.
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
  proof. New PR-2 writers must budget mutation as Git numstat additions plus
  deletions with `line_metric=numstat_added_plus_deleted_v1`; serialized U3
  patch lines are observability only. Legacy `max_diff_lines` artifacts remain
  exact-shape read-only evidence and must never be relabeled as changed lines.
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
  may optionally consume one exact accepted Apple Container dispatch result
  plus its explicitly supplied canonical PR-2 generation receipt during
  `validate`; both paths are required together and must remain under their
  canonical local artifact roots. This intake uses the existing PR-2 trusted
  binding validator instead of direct re-evaluation, must reconstruct the gate
  from canonical admission and finalized run state, and must re-read the
  packet, result, gate, and receipt after local gates. The validation artifact
  must distinguish direct evaluation from trusted Apple dispatch and bind the
  applicable evidence fingerprints. The intake must never regenerate or
  finalize PR-2 artifacts through this intake. It must not open drafts, update
  existing branches, force-push, request reviews, submit reviews, resolve review
  threads, edit fixed mappings, claim merge readiness, merge, release, call
  Slack/GitHub App authority paths, or call
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
- Terminal creative-code outcome artifacts stay local under
  `artifacts/orchestration/creative_code/terminal_outcomes/`. The
  `creative_code_terminal_outcome.py` CLI may only cross-bind one validated
  PR-3 plan/open receipt to one closed sanitized terminal observation and emit
  one immutable `CreativeCodeTerminalOutcomeV1`. Terminal states are exactly
  `merged` or `closed_unmerged`; unavailable terminal evidence emits no
  outcome. The outcome is the sole semantic carrier and may project into
  exactly one durable v2 `pr_terminal` telemetry event. It must not persist
  separate review/terminal/post-merge events, read raw PR/review bodies,
  comments, patches, prompts, provider/oracle output, arbitrary notes, paths,
  or URLs, call GitHub/network/providers/product runtime/Evidence Graph, create
  or write branches, edit mappings, resolve threads, claim readiness, merge,
  change workflows, or add probability/cognitive state. Identical replay is
  no-write; divergent replay preserves the original artifact. Existing v1
  telemetry schemas, identities, readers, and no-terminal collector output
  remain unchanged. Terminal input and publication hardening assumes cooperative
  local artifact users: it rejects traversal, symlinks, non-regular files, and
  replacement of the canonical file, but does not promise pathname stability
  against an uncooperative same-UID process between checks. Descriptor-relative
  hostile-process hardening requires a separate reviewed portability and threat-
  model lane.
- The same terminal-outcome CLI may project one validated canonical
  `terminal_outcome.json` into its single sibling `evidence_events.json` only
  through `project-evidence --outcome ... --produced-at <RFC3339-UTC>`, and may
  validate it read-only through `validate-evidence-projection --outcome ...`.
  The destination is fixed; public output-root/output/events overrides are
  forbidden. The timestamp must be explicit, use a known UTC offset, and use
  the RFC3339 profile supported by the existing evidence-event contract;
  leap-second representations (`time-second=60`) fail closed. Accepted offsets
  are normalized to `Z`; fractional seconds drop insignificant trailing zeros
  and are omitted when all digits are zero. The timestamp is projection time
  only; clocks and filesystem times are not evidence. The
  output is one atomic no-replace, mode-`0600`, three-row control-plane
  normalization bundle using the existing `item_metadata`, `gate_metric`, and
  `gate_decision` event types. It is not three lifecycle events, telemetry,
  Evidence Graph admission, or a replacement for the single `pr_terminal`
  telemetry event. Identical replay is zero-write; different canonical bytes,
  malformed/oversized/hardlinked/symlinked files, non-regular files, and input
  identity changes fail closed without overwrite, deletion, or repair. The
  commands must not serialize local paths or the external experimental lane id,
  perform historical backfill, consume Pilot 4 adaptive evidence, or add
  provider/network/GitHub/DB/product-runtime/promotion/merge authority.
- Creative-code lifecycle transition analytics stay local under
  `artifacts/orchestration/creative_code/lifecycle_transition_analytics/<analytics-id>/`.
  `creative_code_lifecycle_transition_analytics.py` may read only the fixed
  telemetry JSONL and mixed v2 rollup names under the fixed telemetry root,
  rebuild and exactly compare the rollup, join only the closed seven-stage graph
  through typed adjacent lineage, and emit one aggregate-only `analytics.json`.
  Missing adjacent events must be counted as unobserved neighbors and never as
  inferred skip edges; rejected patches and blocked PR opens are stop branches
  for successor accounting. JSONL order, timestamps, paths, filesystem metadata,
  and the sibling three-row Evidence Eval bundle are not lifecycle joins. Output
  must not serialize event/source/candidate/promotion IDs, PR numbers, SHAs,
  paths, timestamps, review text, patches, prompts, command, provider, or oracle
  payloads. Publication is fixed-root, mode-`0600`, atomic no-replace; identical
  replay is zero-write and validation is read-only. Malformed, oversized,
  symlinked, or hardlinked inputs, source identity drift, ambiguous joins, stale
  rollups, non-canonical profiles, or divergent winners fail closed without
  overwrite, deletion, or repair. This descriptive artifact grants no routing,
  retry, promotion, review, mapping, merge, learning, Evidence Graph,
  provider/network/DB, or product-runtime authority.
- Forecasted creative-code PR-2 targets stay local under
  `artifacts/orchestration/creative_code/bayesian_shadow/<forecast-id>/`.
  `creative_code_lifecycle_bayesian_shadow.py` may build only from exact
  validated lifecycle analytics plus its fixed telemetry snapshot and one clean
  canonical generation gate. For a forecasted target, `generate-candidate`
  must receive paired `--shadow-forecast` / `--started-at`, publish or read back
  immutable canonical `start.json` under the existing cooperative run lock,
  recheck forecast/gate sources, hold that same lock through generation to
  serialize duplicate invocation, release it before evaluation takes the
  existing lock, and otherwise preserve the unchanged builder path. It must
  never pass forecast probabilities downstream.
  An occupied exact shadow slot blocks unbound generation; identical replay is
  zero-write and divergent replay preserves the first winner. Forecast/start/
  score artifacts are mode-`0600` under mode-`0700` directories and remain
  shadow-only with `calibration_state=not_assessed` and chronology claim
  `local_dependency_order_only`. They grant no routing, retry, role, candidate,
  promotion, review, PR, merge, provider, network, product-runtime, or
  predictive-quality authority.
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

## PR evidence sidecar v1

- `pr_evidence_sidecar.py` owns one fixed gitignored store under
  `artifacts/orchestration/pr_evidence_sidecars/`; do not add a root override.
- Treat start/terminal receipts and whole-store reports as structural local
  receipts only. Reference fingerprints are non-verifying. They grant no
  review, CI, merge, release, enrollment,
  causality, outcome, promotion, repository, or GitHub authority.
- `observed_pr_terminal_state` is an operator-supplied local observation only.
  GitHub owns authenticated PR state, review governance owns review semantics,
  and `CreativeCodeTerminalOutcome` owns its separate terminal ontology.
- `operator_observations` is limited to operator minutes plus review and repair
  cycle counts; do not add finding, false-positive, regression, rollback,
  quality, or external-outcome fields.
- Preserve strict bounded JSON, private modes, symlink/hardlink/nonregular-file
  rejection, sibling-stage kernel no-replace rename publication, exact replay
  at capacity, pre-creation rejection of new ids at capacity, identical
  no-write replay, and divergent replay failure. Never sweep arbitrary sibling
  stage-looking residue.
- Preserve the public-operation lock boundary: thread `RLock` plus fixed-store
  directory `flock`, exclusive for prepare/finalize and shared for
  validate/report. Internal loaders remain lock-free and canonical receipts
  must validate only at link count one.
- The first receipt is for the next freshly bootstrapped lane after the feature
  lands. Never backfill the implementation PR with a retrospective self receipt.
- Contract and terminal rail truth table:
  `docs/orchestration/PR_EVIDENCE_SIDECAR_V1.md`.

## Pre-push backend tests (smart diff runner)

The `run-backend-tests-pre-commit.sh` script is used by pre-commit framework to run backend pytest for changed Python files plus explicitly mapped cross-surface governance triggers.

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

The standalone invariant-family episode evidence writer must keep one private,
fail-closed kernel no-replace publisher for its two fixed-root/private-mode
bundle shapes. Its focused security/dev-tooling guard is mandatory; arbitrary
path selection, overwrite, repair, delete, or a second publication bypass is
forbidden.
