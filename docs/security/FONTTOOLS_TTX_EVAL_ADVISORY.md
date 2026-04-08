# fonttools TTX `eval()` advisory (remediation)

## Summary

PyPI `fonttools` releases before the fix used unsafe `eval()` when parsing certain TTX data. The upstream project replaced that path with restricted evaluation.

## Remediation

- **Minimum fixed version:** `fonttools==4.62.1` on all pinned requirement surfaces (`requirements.txt`, `requirements-ci-lite.txt`, `requirements-lock.txt`).
- **Requirement surfaces (guard):** `tests/test_dependency_security_guard.py:22` includes `requirements.txt` in `REQUIREMENT_SURFACES`.

## References

- Upstream fix reference in advisory text: `https://github.com/fonttools/fonttools/commit/9caa12715c17ca5b846c6a640aaa5d3503fdbaa2`
- Safety DB package page (context): `https://getsafety.com/p/pypi/fonttools/97c/`
