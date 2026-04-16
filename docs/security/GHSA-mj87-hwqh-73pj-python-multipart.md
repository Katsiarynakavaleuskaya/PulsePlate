# GHSA-mj87-hwqh-73pj - python-multipart pre-push unblock

## Summary

- Advisory: `GHSA-mj87-hwqh-73pj`
- Package: `python-multipart`
- Fixed floor adopted by this repo: `python-multipart>=0.0.26`
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

## Evidence Anchors

- `requirements.in`
- `requirements-ci-lite.in`
- `constraints.txt`
- `requirements.txt`
- `requirements-ci-lite.txt`
- `requirements-lock.txt`
- `tests/fixtures/dependency_security_schema.json`
