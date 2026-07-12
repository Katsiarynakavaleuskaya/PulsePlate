# PR - Pyarrow 25 Fixed in Commit Mapping

Branch: `codex/deps-pyarrow-25-data-profile`

## Summary

Controlled replacement for Dependabot PR #2106. Pins the offline/manual data-build
lockfile to `pyarrow==25.0.0` while preserving the policy floor
`pyarrow>=20.0.0,<26.0.0` in `requirements-data.in`.

## Lane Start Provenance

- Packet: pending local bootstrap before PR open
- Required role order:
  `agent-coordinator -> backend-engineer -> security-auditor -> qa-engineer-agent -> bug-hunter`

## Discussion Thread Pass

- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed
- [ ] Post-open `qa-engineer-agent` pass completed
- [ ] Post-open `bug-hunter` pass completed
- [ ] Post-open `security-auditor` pass completed
- [ ] `pulseplate-pr-review` completed
- [ ] Codex Security diff scan explicitly unavailable or completed

## Fixed in Commit Mapping

- No actionable review comments yet

## Replacement Findings

Disposition: FIXED
Commit: pending
Evidence: `requirements-data.txt` pins `pyarrow==25.0.0`; `requirements-data.in`
keeps `pyarrow>=20.0.0,<26.0.0`.
Reason: Supersedes Dependabot #2106 with a current-main, user-owned data-profile
lane that preserves the 20.0.0 minimum floor.

## Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/ci/check_python_dependency_surfaces.py`
- PASS: `python3 verify_requirements.py`
- PASS: focused dependency/supply-chain pytest bundle
- PASS: `PULSEPLATE_PYTHON_INDEX_URL=https://packages.pulseplate.app/root/pulseplate/+simple/
  python3 scripts/ci/check_private_python_proxy_health.py --requirements-file
  requirements-data.txt --project pyarrow --python-version 3.11
  --python-version 3.12 --python-version 3.13 --max-bytes 5000000`
  - Output: `project name=pyarrow status=200 expected=25.0.0 bytes=383305 reason=ok`
- PASS: `pre-commit run --all-files`

## Merge Readiness

- [ ] Current-head required CI is green
- [ ] Post-open role chain is complete
- [ ] No unresolved/actionable review comments remain
- [ ] Strict merge-readiness check passes
