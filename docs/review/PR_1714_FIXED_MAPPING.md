<!-- markdownlint-disable MD013 MD034 -->
# PR 1714 Fixed In Commit Mapping

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1714>
- Branch: `docs/public-repo-hardening-readme`
- Title: `docs(readme): harden public repo presentation and licensing boundary`
- Initial reviewed head: `3d06c9b87029b7cebe65a40ccb55816d80e22878`
- Review-fix commit: `f64bd06b3`
- Status: docs-only PR, not draft.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Open review-bot actionables were reviewed before mapping. GitHub review threads must remain unresolved until this artifact, the PR-body mirror, and current-head validation agree.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1714#pullrequestreview-4255329404 -> f64bd06b3
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1714#pullrequestreview-4255336698 -> f64bd06b3
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1714#discussion_r3211320859 -> f64bd06b3
Disposition: FIXED
Commit: f64bd06b3
Evidence: README.md removes the token parameter from the Codecov badge URL.
Evidence: README.md adds a maintainer/reviewer entrypoint to AGENTS.md, RUNBOOK_AGENT.md, and docs/dev/AGENT_COMPATIBILITY_ONBOARDING.md without restoring public bootstrap or deployment instructions.
Evidence: README.md anchors licensing precedence to LICENSE and clarifies that the repository is not a public self-hosting distribution, library, or SDK without separate written license.

## Local Validation Evidence

- `python3 scripts/orchestration/check_preflight.py --path README.md` - PASS
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS
- `python3 scripts/orchestration/task_bootstrap.py ... --path README.md --requested-agent agent-coordinator --pr-phase merge_ready` - PASS, packet `2024817f65aa`
- `git diff --check` - PASS before mapping artifact creation

## Security Notes

- Docs-only change. No runtime, auth, billing, entitlement, data, deploy, or CI behavior changes.
- Public README no longer exposes a tokenized Codecov badge URL.
- README licensing language is non-authoritative summary text; LICENSE remains authoritative.

## Risks / Rollback

- Risk: public README may under-serve external developers looking for setup details. Mitigation: authorized maintainers and reviewers are pointed to repo-governed AGENTS/RUNBOOK onboarding.
- Rollback: revert the README and mapping commits from PR #1714 if the public-facing positioning needs to be replaced.

## Deferred / Follow-Ups

- No deferred runtime or governance work in this PR.
