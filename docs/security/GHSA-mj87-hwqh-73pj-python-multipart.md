# GHSA-mj87-hwqh-73pj - python-multipart pre-push unblock

## Status

This historical unblock note is superseded for current dependency-floor truth.
The repo now requires `python-multipart>=0.0.31` after the June 2026 Safety
findings documented in
`docs/security/SFTY-20260615-python-runtime-floors.md`.

## Summary

- Advisory: `GHSA-mj87-hwqh-73pj`
- Package: `python-multipart`
- Historical floor adopted by this unblock: `python-multipart>=0.0.26`
- Tracked repo surfaces remediated by this unblock:
  - `requirements.in`
  - `requirements-ci-lite.in`
  - `constraints.txt`
  - `requirements.txt`
  - `requirements-ci-lite.txt`
  - `requirements-lock.txt`
  - `tests/fixtures/dependency_security_schema.json`

## Reason

`git push` was blocked by the mandatory pre-push `pip-audit` hook because the branch still pinned `python-multipart==0.0.22` in locked runtime surfaces. This is a repository security-floor unblock required to publish the monetization branch without bypassing hooks.

The CI and Docker install lanes also rely on the approved private package proxy. When that proxy lags a newly adopted safe wheel, the locked installer falls back only to artifacts declared in `scripts/ci/emergency_python_wheels.json`. This unblock therefore also adds the exact `python-multipart==0.0.26` wheel to the emergency fallback manifest so `build`, `build-and-test`, and `security` can install the patched floor without relaxing the proxy policy.

## Evidence Anchors

- `requirements.in:19`
- `requirements-ci-lite.in:24`
- `constraints.txt:43`
- `requirements.txt:195`
- `requirements-ci-lite.txt:301`
- `requirements-lock.txt:441`
- `scripts/ci/emergency_python_wheels.json:5`
- `scripts/ci/emergency_python_wheels.json:85`
- `tests/fixtures/dependency_security_schema.json:13`
