# GHSA-58qw-9mgm-455v - pip unsafe archive ambiguity

## Summary

- Package: `pip`
- GHSA: `GHSA-58qw-9mgm-455v`
- CVE: `CVE-2026-3219`
- Severity: `medium`
- Vulnerable range reported by GitHub: `<=26.0.1`
- First patched version reported by GitHub on 2026-04-25: none
- Remediation strategy: remove vulnerable unsafe `pip` pins from repo-managed
  lock surfaces and block reintroduction of `pip<=26.0.1`.

GitHub reports this advisory for lockfile entries produced by
`pip-compile --allow-unsafe`. Because the advisory currently has no patched
`pip` release in the GitHub alert payload, this lane does not repin `pip` to a
nonexistent safe version. Instead, it removes the unsafe `pip==...` lock entries
and records a deterministic blocked-version guard.

## Repo Evidence

- `requirements-dev.txt:258` shows the unsafe package block now starts at
  `setuptools==78.1.1`; the prior `pip==26.0` entry is absent.
- `requirements-lock.txt:545` shows the unsafe package block now starts at
  `setuptools==78.1.1`; the prior `pip==26.0.1` entry is absent.
- `tests/fixtures/dependency_security_schema.json:15` blocks `pip<=26.0.1`
  in pinned requirement surfaces.
- GitHub Dependabot alert `#118` maps `pip` in `requirements-dev.txt` to
  `GHSA-58qw-9mgm-455v`.
- GitHub Dependabot alert `#119` maps `pip` in `requirements-lock.txt` to
  `GHSA-58qw-9mgm-455v`.

## Validation

```bash
rg -n "pip==|GHSA-58qw-9mgm-455v|CVE-2026-3219" requirements-dev.txt requirements-lock.txt tests/fixtures/dependency_security_schema.json docs/security docs/orchestration
.venv/bin/python -m pytest -q tests/test_dependency_security_guard.py
pre-commit run --all-files
make verify
```

## Notes

- `pip-api`, `pip-audit`, `pip-requirements-parser`, and `pip-tools` stay in
  scope as normal development tooling dependencies.
- `setuptools==78.1.1` remains pinned in the unsafe package block because it is
  governed separately by the existing `GHSA-58pv-8j8x-9vj2` security floor.
- This lane is dependency-security only; it does not change runtime behavior,
  OpenAPI, frontend, iOS, Cloudflare, Sentry, Docker, or product code.
