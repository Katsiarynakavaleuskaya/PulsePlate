# Governed Non-Human Identity Policy

<!-- markdownlint-disable MD013 -->

**Status:** Canonical policy for Experiment Runner attribution. No runtime impact.

**Scope:** This policy defines how the dev-only Experiment Runner may be identified in PulsePlate PR lanes and what cryptographic and authority boundaries must exist before any stronger machine identity is treated as trusted.

## Identity

The governed Experiment Runner identity is:

```text
PulsePlate Experiment Runner <pulseplate@pm.me>
```

When the Experiment Runner materially contributes to a commit, the canonical
co-author trailer is:

```text
Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>
```

The email address is public Git attribution metadata only. It is not an experiment result delivery channel, an SMTP recipient by implication, or proof that a commit was produced by a trusted machine.

The placeholder `runner@example.com` is forbidden for new Experiment Runner attribution. Historical references may remain only when they describe prior behavior or review evidence.

The machine-readable source of truth is `docs/orchestration/GOVERNED_NON_HUMAN_IDENTITY_POLICY.json`.

## Cryptographic Boundary

Git author and co-author trailers are unauthenticated text unless backed by a verified account and commit signature. A production-capable non-human identity therefore requires operator-managed cryptographic setup outside the repository.

Allowed signing routes are:

- SSH commit signing with an operator-managed key outside the repo.
- GPG commit signing with an operator-managed key outside the repo.
- GitHub App verified signatures with least-privilege installation permissions.

Forbidden in this repository:

- committing private keys, passphrases, signing tokens, or bot credentials,
- generating long-lived signing keys from repo automation,
- treating a Git email address as proof of machine authorship,
- granting the Experiment Runner merge rights,
- allowing the Experiment Runner to resolve review threads or claim merge readiness.
- allowing the Experiment Runner to mutate `scripts/ci/**` validator scripts
  without a later threat-model PR that defines a narrow allowlist, forbidden
  surfaces, tests, identity checks, and rollback notes.

The Experiment Runner may be a co-author or local PR-lane author only when a human/coordinator-owned process keeps normal PR governance in force.

For oracle-only PR participation, attribution is evidence-based. Add the
canonical co-author trailer only when the local Experiment Runner result
artifact materially shaped the human-reviewed commit. Do not add the trailer to
unrelated human-only commits merely because the PR lane ran the advisory oracle.
The runner artifact records this decision with `contribution_kind`,
`coauthor_required`, and `coauthor_reason`. `mutated_paths: []` is the
oracle-only safety invariant, not evidence that the runner made no contribution.

If an Experiment Runner artifact is included as evidence and influenced the
plan, validation approach, admission decision, fixed mapping, review
disposition, or commit decision, the affected commit uses the canonical
co-author trailer. If the runner only launched, the artifact was rejected or not
used, or the PR records `Not applicable: <reason>`, the trailer is not required.

Every non-trivial PR lane should record Experiment Runner participation in an
`Experiment Runner Evidence` block: either a local oracle-only result artifact
under `artifacts/orchestration/experiments/results/` or an explicit
`Not applicable:` reason. Phase2 can run this evidence check in `advisory` or
`required` mode. Advisory mode reports absence as a diagnostic; required mode
fails closed when the block is missing or lacks a valid artifact/not-applicable
reason. Malformed evidence is rejected in every mode because it can
misrepresent runner participation.

For non-trivial lanes, failure to load or write the local result artifact
because the active Python interpreter lacks FastAPI/runtime dependencies is an
environment parity problem, not evidence that the runner is inapplicable. Use
repo Python (`VENV_PYTHON` or the repo `.venv`) for runner evidence commands
and treat persistent artifact load/write failure as an infrastructure blocker.

The Experiment Runner is never the lane-start authority. It joins after the
repo coordinator bootstrap (`check_preflight.py` -> `task_bootstrap.py` ->
`agent-coordinator`) as oracle/review/design-of-experiment evidence. A runner
artifact can still require co-author attribution when its insight shapes the
engineering decision, even though the runner did not mutate files.

## Notification Boundary

Experiment result delivery is governed by `scripts/orchestration/experiment_notify.py`, `scripts/orchestration/experiment_pipeline.py`, and `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`.

Default delivery is a local artifact. Email delivery is explicit opt-in and requires an allowlisted recipient plus runtime SMTP secrets. The Git attribution email does not cause email delivery.

Automatic email reports are available only through the governed completion
wrapper when `experiment_pipeline.py --email-reports` is explicitly used. The
recipient remains the v1 governed recipient `pulseplate@pm.me`, and SMTP
configuration remains runtime-secret backed.

## Slack Boundary

Slack is now defined only as an operator-facing notification and bounded
operator-command display identity for Experiment Runner work. It is not a
cryptographic Git identity, a Git attribution identity, a review-thread actor,
a merge-readiness authority, or a generic project bot.

Slack delivery is available only through explicit `experiment_notify.py`
operator intent:

- `--slack` and `--slack-channel` must both be provided;
- bot credentials are runtime secrets outside the repo;
- channel delivery is fail-closed behind a runtime allowlist;
- messages use the governed redacted experiment notification body;
- local Slack audit artifacts record hashes/status only;
- delivery is idempotent, timeout-bounded, and rate-limited before send;
- tests prove no secrets, raw patch text, oracle stdout/stderr, cwd, local
  absolute paths, or user data are posted or written into audits.

The Slack Socket Mode operator bridge is allowed only as a dry-run-first
operator command boundary. It may parse a narrow `/run-experiment <branch>
<hypothesis>` style request and report what would be dispatched. Any real
workflow dispatch must be explicitly selected by an operator, use a fixed
workflow allowlist, require GitHub runtime auth, and remain idempotent and
audit-backed.

Socket Mode uses runtime credentials outside the repository. Operators configure
the app-level Socket Mode credential as `SLACK_APP_TOKEN` and the bot credential
as `SLACK_BOT_TOKEN` in their secret store; the repository may reference those
runtime secret names in workflow wiring, but must never commit token values.
HTTP Events and `SLACK_SIGNING_SECRET` are out of scope for this boundary.

The operator-selected `#experiment-runner` channel remains runtime
configuration, not checked-in repo truth. The bridge must require channel and
user allowlists before parsing operator intent. Audit artifacts are local and
hash-only: no raw Slack payload, channel or user identifier, token, local
absolute path, oracle stdout/stderr, patch text, or raw hypothesis may be
written.

## Validation

Run the policy guard before claiming readiness:

```bash
python3 scripts/orchestration/check_experiment_runner_identity.py
```

The guard validates the machine-readable policy and fails closed if placeholder emails, repo-stored key material, ambiguous Slack authority, or missing signing requirements are introduced.
