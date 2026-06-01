# PR #1863 - Trivy alert #602 premortem

## Summary

Plan: add an exact, time-boxed Trivy Rego policy disposition for GitHub
code-scanning alert #602, `CVE-2026-48962`, `perl-base 5.36.0-7+deb12u3`.

Failure frame: it is 48 hours from now, this security PR made the Trivy signal
less trustworthy or created a false readiness claim.

## Most likely failure

The Rego rule is too broad or is not tested precisely enough. This could happen
if the PR only asserts that `CVE-2026-48962` appears somewhere in
`trivy/ignore-policy.rego`, while the actual ignore rule would also match future
patched package versions or unrelated Perl packages.

Early warning signs:

- The test only checks loose substrings instead of the CVE block and exact
  package/version/PkgID constraints.
- The CVE is added to `.trivyignore`, which is CVE-only and cannot enforce the
  package/version scope.

Containment:

- Keep the suppression in Rego only.
- Assert exact `VulnerabilityID`, `PkgName`, `InstalledVersion`, and `PkgID`
  matching in `tests/test_trivy_ignore_policy_expiry.py`.

## Most dangerous failure

The PR is presented as remediation or alert closure when it is only a temporary
policy disposition. That would weaken security governance by implying Debian or
the production image has been fixed when the vulnerable OS package remains
present.

Early warning signs:

- PR text says the CVE is fixed, remediated, closed, or dismissed.
- Local Docker/Trivy evidence is described as passing even though Docker and the
  local `trivy` CLI are unavailable.

Containment:

- State that this is not upstream remediation in the security doc and PR body.
- Document local Docker/Trivy image scan as unavailable unless the tools are
  actually available and run.
- Require current-head Docker/Trivy/SARIF evidence after push before any
  readiness claim.

## Hidden assumption

The hidden assumption is that current Debian and Trivy metadata will stay
unfixed during implementation. If Debian bookworm publishes a fixed
`perl`/`perl-base` package or Trivy/GitHub starts reporting a fixed version for
alert #602 before closeout, this PR must switch from policy disposition to real
remediation.

## Revised plan

- Re-check GitHub alert #602, Debian, and NVD status before final closeout.
- Keep the diff limited to `trivy/ignore-policy.rego`, the security doc,
  backlog ledger, focused test, and this premortem artifact.
- Do not touch `.trivyignore`, Dockerfile, workflows, or product runtime code.
- Add static tests that fail on broad matching and on any `.trivyignore` entry.
- Record local Docker/Trivy gaps as unavailable local tooling, not as passed
  evidence.

## Pre-open checklist

- `python3 scripts/orchestration/check_preflight.py --path docs/review/PR_TRIVY_602_PREMORTEM.md --path docs/roadmap/BACKLOG_LEDGER.md --path docs/security/CVE-2026-48962-perl-base.md --path tests/test_trivy_ignore_policy_expiry.py --path trivy/ignore-policy.rego`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `python3 scripts/ci/check_trivy_ignore_policy_expiry.py`
- `.venv/bin/python -m pytest -q tests/test_trivy_ignore_policy_expiry.py`
- `python3 scripts/ci/check_docs_phase1_gates.py --files docs/security/CVE-2026-48962-perl-base.md`
- `make validate-changed`
- `.venv/bin/pre-commit run --all-files`
- Experiment Runner oracle evidence, with every finding fixed or dispositioned.

## Decision

Proceed with changes. The plan is acceptable only as a narrow, time-boxed
policy disposition with exact Rego matching, explicit local-tooling limitations,
and current-head SARIF verification after push.

## Discussion Thread Pass

The canonical review-thread source of truth is
`docs/review/PR_1863_FIXED_MAPPING.md`.

### Fixed in Commit Mapping

Canonical artifact: `docs/review/PR_1863_FIXED_MAPPING.md`.

## Merge Readiness

Not merge-ready. Current-head CI, post-open role passes, bot disposition,
strict merge-readiness, and alert #602 SARIF verification remain pending.
