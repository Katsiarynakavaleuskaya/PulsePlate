# Experiment Runner Slack Socket Operator Runbook

**Status:** operator live-smoke runbook. Slack remains display and bounded
operator-command infrastructure only; it is not Git attribution, review-thread,
merge-readiness, merge, PR creation, or autonomous workflow authority.

## Runtime Secrets

Configure these outside the repository, for example as GitHub Actions secrets:

- `SLACK_APP_TOKEN`: Slack app-level Socket Mode credential.
- `SLACK_BOT_TOKEN`: Slack bot credential used by the optional live bridge.
- Optional `GH_TOKEN` / `GITHUB_TOKEN`: GitHub dispatch credential for the
  execute-mode fixed workflow dispatch path. Execute mode also requires
  `EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED=reviewed-dry-run-dispatch`. It
  defaults to workflow input `dry_run: true`; `dry_run: false` is allowed only
  when the reviewed live-dispatch approval digest matches exactly.
- Optional `EXPERIMENT_SLACK_SOCKET_LIVE_APPROVAL_SHA256`: SHA256 digest that
  authorizes a single reviewed live dispatch for one specific
  `branch_ref` + `hypothesis` pair. When absent, dispatch defaults to
  `dry_run: true`. When present, the bridge computes
  `SHA256(branch_ref + "\0" + hypothesis)` and allows `dry_run: false`
  only on exact match.
- Optional `EXPERIMENT_OPERATOR_LEDGER_TASK_PACKET_ID`: local operator-ledger
  packet id for bridge write-through. If absent, the bridge uses the safe static
  id `operator-plane-slack-bridge`. Malformed values fail closed before
  dispatch and must not be printed.

Do not commit token values, token prefixes, approval digests, Slack webhook
URLs, raw Slack payloads, or real workspace channel/user IDs as repository
defaults.

## Runtime Allowlists

The manual smoke workflow requires operator-supplied allowlists at dispatch
time:

- `EXPERIMENT_NOTIFICATION_SLACK_CHANNEL_ALLOWLIST`: comma-separated Slack
  channel IDs approved for operator bridge traffic.
- `EXPERIMENT_NOTIFICATION_SLACK_USER_ALLOWLIST`: comma-separated Slack user IDs
  approved to issue the bounded command.
- `EXPERIMENT_NOTIFICATION_SLACK_TEAM_ALLOWLIST`: optional workspace/team ID
  allowlist for local dry-run config checks, and required for live-smoke,
  live-listener, and execute-mode paths.

Use the approved `#experiment-runner` channel ID only as a runtime input. The
repository must not hardcode it as a default.

## Slack App Manifest

The secret-free operator setup manifest lives at
`docs/orchestration/EXPERIMENT_RUNNER_SLACK_APP_MANIFEST.yml`.

The manifest documents the repo-approved Socket Mode shape only: Experiment
Runner app identity, Slack-safe bot display `experiment-runner`,
`/run-experiment`, `/pulseplate-runner` (with `help | status | kpp-status |
mvp-evidence`), bot scopes `commands` and `chat:write`,
`socket_mode_enabled: true`, `org_deploy_enabled: false`, and `is_hosted:
false`.

The manifest must not contain token values, token prefixes, webhook URLs,
request URLs, real workspace/team/channel/user IDs, or repository defaults for
operator allowlists. App-level Socket Mode token creation and the
`connections:write` scope remain external operator setup, stored only in the
runtime secret store.

This bridge intentionally uses Slack Socket Mode and does not expose an HTTP
request URL. `SLACK_SIGNING_SECRET` is therefore not used by this PR.
Any future HTTP Slack ingress must add Slack signature verification, timestamp
freshness checks, and replay protection before parsing a payload.

## Slack App Asset Policy

Slack App assets are secret-free operator setup material only. App icons,
screenshots, or branding files must not contain workspace identifiers, token
fragments, webhooks, local paths, or unreleased product claims.

The operator-provided `experiment_runner_logo_slack.png` can be promoted into
the repository only after source, ownership, and allowed use are documented in
repo-reviewed docs. Until that evidence exists, the manifest remains text-only
and the asset stays outside committed Slack App truth.

## Manual Live Smoke

Run `.github/workflows/experiment-runner-slack-socket-smoke.yml` manually with
`workflow_dispatch`.

Manual live smoke is operator evidence only. It is not a required CI gate, not merge-readiness proof,
and not a substitute for the deterministic no-secret Slack/Experiment Runner
operator-plane CI gate.

For config-only validation, keep `dry_run` as `true`. This validates the bridge
without Slack network access.

For bounded live-smoke validation, set `dry_run` to `false` and provide:

- runtime channel allowlist,
- runtime user allowlist,
- runtime workspace/team allowlist,
- a safe branch reference,
- a SHA256 digest of the hypothesis, not raw Slack text,
- audit retention days.

The workflow first runs a secret-presence diagnostic. The workflow shell prints
only public required environment names with `present` / `missing` status, then
passes the runtime environment to the Python bridge. The Python bridge derives
presence from runtime environment variables and returns only the fail-closed
exit code for that check; it does not print a secret-presence payload. The
diagnostic must not print secret values, token prefixes, raw channel/user IDs,
raw hypotheses, local absolute paths, Slack payload bodies, GitHub tokens,
oracle stdout/stderr, or patch text.

The live-smoke network check is bounded and exits. It validates the app-level
Socket Mode credential by opening a temporary Socket Mode connection URL with
Slack `apps.connections.open`, validates the bot credential with Slack
`auth.test`, discards all Slack response identifiers and WebSocket URLs, and
prints only a sanitized pass/fail status. The workflow must not start the
long-running Socket Mode listener path for evidence collection.

Committed PR evidence may record only:

- workflow run URL and status,
- job names and pass/fail conclusion,
- secret names as `present` / `missing`,
- `channel_allowlist=present` and `user_allowlist=present`,
- `team_allowlist=present`,
- audit retention report status,
- redaction assertion status.

Do not commit workflow logs, raw stdout/stderr dumps, raw Slack IDs, raw
hypothesis text, Slack WebSocket URLs, Slack payloads, token values, token
prefixes, GitHub tokens, local absolute paths, oracle output, or patch text.

## Current Activation Diagnostics

Live smoke activation is a runtime configuration check, not a repository
authority grant. `SLACK_APP_TOKEN` must be an `xapp-` app-level Socket Mode
token, `SLACK_BOT_TOKEN` must be an `xoxb-` bot token, and channel, user, and
workspace/team allowlists must be supplied at workflow dispatch time.

If live smoke reports an invalid token class, treat it as an operator secret
configuration issue outside the repository. A later passing manual live smoke
run can supersede an earlier failed run only as current operator evidence; the
repository must not preserve raw logs, token prefixes beyond class labels, Slack
workspace identifiers, WebSocket URLs, or response bodies.

## Semantic-Cache Gate Recheck

This Slack operator-plane lane does not open the product AI runtime semantic
cache rail. The recheck command is:

```bash
python3 scripts/ci/check_semantic_cache_gate.py --doc docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md
```

The expected markers remain `closed / false / false / true`. Passing this
checker is evidence that the gate remains closed; it does not authorize
GraphRAG, semantic-cache implementation, runtime cache reads or writes,
provider activation, OpenAPI changes, DB changes, or product-serving behavior.

## Einstein Arena / HTTPS Ingress Boundary

This operator app remains Socket Mode in this PR. Einstein Arena or any other
HTTPS Slack ingress requires a separate reviewed PR before implementation. That
future PR must add Slack signature verification, timestamp freshness, replay
protection, rate limiting, runtime allowlists, and a redacted audit contract
before parsing or acting on any HTTP Slack payload.

## Failure Interpretation

- Missing `SLACK_APP_TOKEN`: configure the app-level Socket Mode secret outside
  the repository.
- Missing `SLACK_BOT_TOKEN`: configure the bot credential outside the
  repository.
- Missing channel or user allowlist: provide runtime allowlist inputs; this is
  a fail-closed operator configuration issue.
- Missing team allowlist: provide the runtime workspace/team allowlist for live
  smoke, live listener, or execute-mode dry-run dispatch.
- Optional Slack SDK unavailable: install the operator Slack SDK runtime only
  for the explicit long-running listener path. Bounded manual live smoke uses
  fixed Slack Web API checks and must not require the SDK.
- Live smoke validation failed: inspect the operator Slack app configuration
  and token classes outside the repository. The repository must not print Slack
  response bodies, WebSocket URLs, workspace identifiers, or token prefixes.
- Invalid token class: use the correct credential class for the expected
  runtime variable.
- Rate limit active or duplicate event: the bridge already recorded a recent or
  duplicate operator event; wait or inspect the local hash-only audit artifact.

## Live-Dispatch Approval Gate

Live Experiment Runner dispatch (workflow input `dry_run: false`) is gated by a
reviewed approval digest.

1. A human reviewer generates the approval digest offline:
   ```python
   import hashlib
   digest = hashlib.sha256((branch_ref + "\0" + hypothesis).encode("utf-8")).hexdigest()
   ```
2. The digest is supplied to the runtime environment as
   `EXPERIMENT_SLACK_SOCKET_LIVE_APPROVAL_SHA256`.
3. The bridge computes the same digest from the Slack operator command and
   allows `dry_run: false` only on exact match.
4. A mismatch rejects the command with a clear error and writes an audit record.
5. The digest is treated as a single-use secret: rotate it after each live
dispatch or when leaked.

Dry-run remains the default when the approval env is absent or does not match.
Operators must not post raw approval digests, branch names, or hypotheses into
Slack.

For an approved `dry_run: false` dispatch, the Slack-visible reply may include
only sanitized evidence: fixed workflow file/ref, branch hash, hypothesis hash,
approval hash prefix, local ledger status/reference, and the explicit statement
that Slack is not merge readiness. The manual workflow summary must keep
`approval_hash_prefix: none` unless the workflow itself can prove the
branch/hypothesis approval binding; the bridge remains the authority for that
bounded approval check. Neither surface may include raw branch refs, raw
hypotheses, raw approval digests, Slack IDs, workflow logs, provider logs, local
paths, or patch text.

See also: `docs/orchestration/PREMORTEM_SLACK_LIVE_DISPATCH_APPROVAL.md` for
reviewed risk analysis and failure modes.

## Audit Retention

Slack bridge audit artifacts live under
`artifacts/orchestration/experiments/slack_socket_bridge/` and are local,
gitignored, and hash-only.

The default retention window is 14 days. The workflow reports retention state by
default. Cleanup is explicit-only through the bridge CLI and must remain
confined under `artifacts/orchestration`; traversal and symlink paths are
rejected before deletion.

## Local Operator Ledger and Report

The local operator ledger lives under
`artifacts/orchestration/experiments/operator_ledger/`. It is gitignored,
local-only, and advisory. It can summarize Experiment Runner operator-plane
activity for a developer or reviewer, but it is not product analytics, runtime
truth, fixed-mapping proof, review-thread disposition proof, or merge-readiness
evidence by itself.

Allowed ledger fields are limited to schema/policy version, task packet id,
dispatch mode, fixed workflow file/ref, hash-only branch and hypothesis
identifiers, safe artifact references, failure class, co-author decision, human
review outcome, retention policy, and explicit authority-boundary booleans that
must remain false for PR creation, review-thread resolution, merge-readiness
claims, and product runtime changes. Observability reports may also project
validated Experiment Runner result metadata from local result artifacts, but only
when the file SHA-256 matches the ledger's `oracle_result_hash`. The sanitized
metadata allowlist is schema version, experiment-id hash prefix, runner mode,
status, failure class, mutated-path count, shared-tree untouched,
promotion-ready, contribution kind, and co-author-required state. Latest-event
report summaries include dispatch mode, co-author decision/required state, and
human review outcome as display-only operator evidence.

The ledger and report must not store raw Slack text, Slack channel/user/team
IDs, trigger IDs, raw branch refs, raw hypotheses, local absolute paths, health
or wellness payloads, provider logs, token values or prefixes, approval
digests, oracle stdout/stderr, workflow logs, or patch text.
Malformed, missing, traversal, or symlinked result artifacts must degrade to a
sanitized artifact status and must not print file contents, local paths, oracle
output, patches, provider logs, or validator details. Local reports may be
rendered as JSON, Markdown, or a deterministic escaped single-file HTML report
under `artifacts/orchestration/experiments/`. Report payloads include source
counts, malformed/missing artifact counts, and a redaction summary that keeps
Slack, provider, patch, approval, health, and local-path data marked as absent.

Generate the local operator observability report set from the repository root:

```bash
python3 scripts/orchestration/experiment_operator_ledger.py --write-report-set
```

The command writes only gitignored local files under
`artifacts/orchestration/experiments/operator_observability/`. Delete that
directory when the local evidence is no longer needed; do not commit generated
report files.

`/pulseplate-runner status` may include a sanitized latest-ledger summary when a
valid local ledger event exists. If no event exists, the status shows an absent
local ledger. If a local ledger artifact is malformed, the status reports only a
sanitized `invalid_local_artifact` class and does not print paths or contents.
The bridge writes one local ledger record after Slack audit finalization for
`dry_run`, `dispatched`, `failed`, and `rejected` outcomes. Duplicate Slack
events are blocked by the existing audit idempotency check before a second
ledger record can be created. No new Slack command or Slack authority is added
by the local observability report set.

## Authority Boundary

The Slack operator bridge may validate configuration, report status, render
redacted Guided Planning MVP evidence contract summaries, and in explicit execute mode dispatch only the fixed
`.github/workflows/experiment-runner-dispatch.yml` workflow with typed,
sanitized inputs. The dispatch workflow is manual-only, defaults to `dry_run:
true`, and allows `dry_run: false` only when the reviewed approval digest
matches the requested branch and hypothesis exactly. It must not:

- create or update pull requests,
- resolve review threads,
- claim merge readiness,
- satisfy Git co-author attribution,
- run arbitrary workflows,
- execute shell commands from Slack text,
- auto-run experiments by default.

Allowed operator display commands are bounded and redacted:

- `/pulseplate-runner help`: static command summary and authority boundary.
- `/pulseplate-runner status`: bridge mode, allowlist presence, fixed workflow
  metadata, rate-limit setting, local audit-retention setting, and optional
  sanitized latest local operator-ledger summary only.
- `/pulseplate-runner kpp-status`: static KPP outcome catalog and
  security-sensitive routing note; no experiment artifacts, local paths, Slack
  IDs, hypotheses, or provider logs.
- `/pulseplate-runner mvp-evidence`: static Guided Planning MVP evidence contract
  coverage summary for #1842-#1844 event hooks; no raw user events, PII, health data,
  hypotheses, local paths, Slack IDs, or provider logs.
- `/run-experiment <branch> <hypothesis>`: existing dry-run-first fixed workflow
  path; Slack-visible preview uses hashes for branch and hypothesis values.

Operators must not put emails, names, phone numbers, BMI/weight/height values,
health conditions, diagnostic claims, payment state, raw user wellness text, or
other sensitive user data into Slack hypotheses. Use repo artifact references or
hashes instead.

These commands are operator convenience views only. They do not create PRs,
resolve reviews, satisfy fixed-mapping evidence, prove merge readiness, or
replace GitHub Actions/current-head truth.

The earlier `.github/workflows/experiment-runner-slack-socket-smoke.yml`
workflow remains the separate manual live-smoke validation path for runtime
Slack secrets and allowlists.
