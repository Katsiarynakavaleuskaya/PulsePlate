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

A Slack identity can be useful later as a notification display identity or operator-facing bot, but it is not a cryptographic Git identity and should not be introduced in this PR.

Slack integration requires a separate security-governed PR with:

- a Slack App or bot identity lifecycle,
- bot token secret storage outside the repo,
- channel allowlists,
- rate and timeout behavior,
- redacted message bodies,
- local audit artifacts,
- tests proving no secrets, raw patch text, oracle stdout/stderr, or user data are posted.

Tracked follow-up: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-experiment-runner-slack-identity-boundary`.

## Validation

Run the policy guard before claiming readiness:

```bash
python3 scripts/orchestration/check_experiment_runner_identity.py
```

The guard validates the machine-readable policy and fails closed if placeholder emails, repo-stored key material, ambiguous Slack authority, or missing signing requirements are introduced.
