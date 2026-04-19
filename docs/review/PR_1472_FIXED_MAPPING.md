# PR #1472 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:58-60`.

- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed

This artifact is created immediately after lane setup per repo governance.
Record every new review or bot disposition here before resolving threads on
GitHub.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1472#issuecomment-4275078933
Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md` (`P1: Fix invalid Dependabot assignee configuration warning`)
Reason: The invalid Dependabot assignee remains a live repo-wide config defect in `.github/dependabot.yml`, but fixing that global automation surface is intentionally deferred out of the narrow `#1472` quality remediation lane.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1472#pullrequestreview-4135421139 -> b8ac67908
Disposition: FIXED
Evidence: `requirements.txt:41`, `requirements.txt:43`, `requirements.txt:139`, `requirements.txt:304`, `requirements-lock.txt:41`, `requirements-lock.txt:43`, `requirements-lock.txt:139`, `requirements-lock.txt:304`
Reason: cubic found that Dependabot regenerated unconditional CUDA / Triton pins on the shared requirement surfaces; the remediation restores the established Linux / `x86_64` markers so macOS installs remain portable while preserving the `mypy` / `ruff` bump.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1472#discussion_r3106217704 -> b8ac67908
Disposition: FIXED
Evidence: `requirements.txt:41`, `requirements.txt:43`, `requirements.txt:139`, `requirements.txt:304`, `requirements-lock.txt:41`, `requirements-lock.txt:43`, `requirements-lock.txt:139`, `requirements-lock.txt:304`
Reason: cubic found the same portability issue on the inline thread at `requirements.txt:41`; the remediation restores Linux / `x86_64` platform markers for the CUDA / Triton packages introduced by Dependabot regeneration.

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Current-head CI is green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green on latest pushed head
- [ ] `make verify` green on latest pushed head

## Notes

- Initial lane entry truth:
  - the quality bump itself is `mypy 1.20.0 -> 1.20.1` and `ruff 0.15.10 -> 0.15.11`
  - live cubic review identifies unconditional CUDA pins in `requirements.txt`
    as the active portability defect
  - governance-only failures remain expected until this artifact and the PR
    body mirror are synchronized
- Local latest-head evidence already collected:
  - `pre-commit run --all-files` passed
  - `make verify` passed end-to-end on the remediation head
- Canonical lane packet:
  `docs/orchestration/DEPENDABOT_PR_1472_QUALITY_GROUP_REMEDIATION_PACKET_2026-04-19.md`
