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

GitHub reported this advisory for `pip` entries emitted by the repository's
former direct lock-generation workflow. Because the alert payload had no
patched `pip` release, the remediation did not repin `pip` to a nonexistent safe
version. Current locks are generated only through `make requirements-locks`,
which excludes `pip` and records Make/profile/source provenance.

## Repo Evidence

- `requirements-dev.txt` contains the governed normal pin
  `setuptools==83.0.0` and no `pip==...` pin.
- `requirements-lock.txt` contains the governed normal pin
  `setuptools==83.0.0` and no `pip==...` pin.
- `tests/fixtures/dependency_security_schema.json:15` blocks `pip<=26.0.1`
  in pinned requirement surfaces.
- GitHub Dependabot alert `#118` maps `pip` in `requirements-dev.txt` to
  `GHSA-58qw-9mgm-455v`.
- `tests/test_dependency_security_guard.py` includes
  `test_repo_managed_lock_surfaces_do_not_pin_pip` to prevent future drift.
- GitHub Dependabot alert `#119` maps `pip` in `requirements-lock.txt` to
  `GHSA-58qw-9mgm-455v`.

## Validation

```bash
rg -n "pip==|GHSA-58qw-9mgm-455v|CVE-2026-3219" requirements-dev.txt requirements-lock.txt tests/fixtures/dependency_security_schema.json docs/security docs/orchestration
.venv/bin/python -m pytest -q tests/test_dependency_security_guard.py
pre-commit run --all-files
make validate-changed
```

## Notes

- `pip-api`, `pip-audit`, `pip-requirements-parser`, and `pip-tools` stay in
  scope as normal development tooling dependencies.
- `setuptools==83.0.0` remains a normal governed pin under its separate
  security floor; there is no tracked unsafe-package footer.
- This lane is dependency-security only; it does not change runtime behavior,
  OpenAPI, frontend, iOS, Cloudflare, Sentry, Docker, or product code.
