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
- PR-2 creative-code patch-builder artifacts stay local under
  `artifacts/orchestration/creative_code/patch_runs/`. The builder CLI
  `creative_code_patch_builder.py` is not role dispatch, PR lifecycle
  automation, merge governance, or promotion authority. Its `evaluate` command
  may call Experiment Runner candidate-patch mode for local candidate evaluation,
  but that result is not the mandatory PR oracle-only governance evidence and
  must not be used as fixed-mapping, review-disposition, or merge-readiness
  proof.
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
