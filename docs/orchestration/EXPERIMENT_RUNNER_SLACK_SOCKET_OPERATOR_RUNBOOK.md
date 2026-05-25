# Experiment Runner Slack Socket Operator Runbook

**Status:** operator live-smoke runbook. Slack remains display and bounded
operator-command infrastructure only; it is not Git attribution, review-thread,
merge-readiness, merge, PR creation, or autonomous workflow authority.

## Runtime Secrets

Configure these outside the repository, for example as GitHub Actions secrets:

- `SLACK_APP_TOKEN`: Slack app-level Socket Mode credential.
- `SLACK_BOT_TOKEN`: Slack bot credential used by the optional live bridge.

Do not commit token values, token prefixes, Slack webhook URLs, raw Slack
payloads, or real workspace channel/user IDs as repository defaults.

## Runtime Allowlists

The manual smoke workflow requires operator-supplied allowlists at dispatch
time:

- `EXPERIMENT_NOTIFICATION_SLACK_CHANNEL_ALLOWLIST`: comma-separated Slack
  channel IDs approved for operator bridge traffic.
- `EXPERIMENT_NOTIFICATION_SLACK_USER_ALLOWLIST`: comma-separated Slack user IDs
  approved to issue the bounded command.
- `EXPERIMENT_NOTIFICATION_SLACK_TEAM_ALLOWLIST`: optional workspace/team ID
  allowlist for local live runs.

Use the approved `#experiment-runner` channel ID only as a runtime input. The
repository must not hardcode it as a default.

## Manual Live Smoke

Run `.github/workflows/experiment-runner-slack-socket-smoke.yml` manually with
`workflow_dispatch`.

For config-only validation, keep `dry_run` as `true`. This validates the bridge
without Slack network access.

For live prerequisite validation, set `dry_run` to `false` and provide:

- runtime channel allowlist,
- runtime user allowlist,
- a safe branch reference,
- a SHA256 digest of the hypothesis, not raw Slack text,
- audit retention days.

The workflow first runs a secret-presence diagnostic. The workflow shell prints
only public required environment names with `present` / `missing` status, then
passes explicit CLI booleans from GitHub expressions to the Python bridge. The
Python bridge returns only the fail-closed exit code for that check; it does not
print a secret-presence payload. The diagnostic must not print secret values,
token prefixes, raw channel/user IDs, raw hypotheses, local absolute paths,
Slack payload bodies, GitHub tokens, oracle stdout/stderr, or patch text.

## Failure Interpretation

- Missing `SLACK_APP_TOKEN`: configure the app-level Socket Mode secret outside
  the repository.
- Missing `SLACK_BOT_TOKEN`: configure the bot credential outside the
  repository.
- Missing channel or user allowlist: provide runtime allowlist inputs; this is
  a fail-closed operator configuration issue.
- Optional Slack SDK unavailable: install the operator Slack SDK runtime for
  live Socket Mode; dry-run and diagnostics do not require it.
- Invalid token class: use the correct credential class for the expected
  runtime variable.
- Rate limit active or duplicate event: the bridge already recorded a recent or
  duplicate operator event; wait or inspect the local hash-only audit artifact.

## Audit Retention

Slack bridge audit artifacts live under
`artifacts/orchestration/experiments/slack_socket_bridge/` and are local,
gitignored, and hash-only.

The default retention window is 14 days. The workflow reports retention state by
default. Cleanup is explicit-only through the bridge CLI and must remain
confined under `artifacts/orchestration`; traversal and symlink paths are
rejected before deletion.

## Authority Boundary

The Slack operator bridge may validate configuration, report status, and in
explicit execute mode dispatch only the fixed smoke workflow with typed,
sanitized inputs. It must not:

- create or update pull requests,
- resolve review threads,
- claim merge readiness,
- satisfy Git co-author attribution,
- run arbitrary workflows,
- execute shell commands from Slack text,
- auto-run experiments by default.
