# Bandit Lower-Severity Inventory

## Status

PulsePlate keeps Bandit HIGH findings fail-closed in canonical CI. LOW and
MEDIUM findings are warning-only inventory until each rule family is remediated
or dispositioned through normal security review.

## PR3 Baseline

PR3 adds deterministic grouping for the existing Bandit JSON report. The grouped
summary is advisory evidence only: it does not suppress findings, add `# nosec`,
or change the HIGH severity merge gate.

The summary groups below-HIGH findings by:

- Bandit rule id.
- Severity.
- Confidence.
- Path bucket.

## Follow-up Policy

Future remediation PRs should target one rule family or path bucket at a time.
Suppressions remain governed by the root `AGENTS.md` nosec policy and require a
rule id, justification, remove-by date, and tracked reference.
