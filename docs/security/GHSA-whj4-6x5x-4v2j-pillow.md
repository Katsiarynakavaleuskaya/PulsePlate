# GHSA-whj4-6x5x-4v2j — pillow runtime/dev lock remediation

## Summary

- Advisory: `GHSA-whj4-6x5x-4v2j`
- Package: `pillow`
- Fixed floor adopted by this repo: `pillow>=12.2.0`
- Tracked repo surfaces remediated by this PR:
  - `requirements.in`
  - `requirements-dev.in`
  - `requirements-ci-lite.in`
  - `constraints.txt`
  - `requirements.txt`
  - `requirements-dev.txt`
  - `requirements-ci-lite.txt`
  - `requirements-lock.txt`
  - `tests/fixtures/dependency_security_schema.json`
  - `scripts/ci/emergency_python_wheels.json`

## Reason

`pip-audit` blocked the standard pre-push workflow because the repo baseline on
`origin/main` still pinned `pillow==12.1.1`, which is below the safe version
required by the advisory. This was a repository-wide dependency blocker, not a
regression introduced by the Figma docs-only audit branch.

Current-head CI then showed a second repo-side blocker: Linux `--only-binary`
Docker and OpenAPI lanes could not install `pillow==12.2.0` from the approved
private proxy while that proxy lagged the upstream binary wheel, so this PR also
adds the exact Pillow wheel to the emergency fallback manifest already used for
other security-patched dependencies.

## Remediation Contract

The security-unblock PR applies the fix on all relevant dependency surfaces:

- `requirements.in:15` adds the canonical runtime floor
- `requirements-dev.in:21` and `requirements-dev.in:23` mirror the floor for dev tooling surfaces
- `requirements-ci-lite.in:20` and `requirements-ci-lite.in:34` mirror the floor for lightweight CI installs
- `constraints.txt:40` and `constraints.txt:54` mirror the security floors for locked installs
- `requirements.txt:39` and `requirements.txt:161` pin the resolved safe versions
- `requirements-dev.txt:44` and `requirements-dev.txt:133` pin the resolved safe versions
- `requirements-ci-lite.txt:58` and `requirements-ci-lite.txt:228` pin the resolved safe versions used by Docker/OpenAPI lanes
- `requirements-lock.txt:76` and `requirements-lock.txt:329` pin the resolved safe versions
- `tests/fixtures/dependency_security_schema.json:3` and `tests/fixtures/dependency_security_schema.json:4` enforce the dependency-security guard floor
- `scripts/ci/emergency_python_wheels.json:5-25` records the exact Linux wheel fallback for `pillow==12.2.0` while the approved private proxy catches up

## Evidence Anchors

- `requirements.in:15`
- `requirements-dev.in:21`
- `requirements-dev.in:23`
- `requirements-ci-lite.in:20`
- `requirements-ci-lite.in:34`
- `constraints.txt:40`
- `constraints.txt:54`
- `requirements.txt:39`
- `requirements.txt:161`
- `requirements-dev.txt:44`
- `requirements-dev.txt:133`
- `requirements-ci-lite.txt:58`
- `requirements-ci-lite.txt:228`
- `requirements-lock.txt:76`
- `requirements-lock.txt:329`
- `tests/fixtures/dependency_security_schema.json:3`
- `tests/fixtures/dependency_security_schema.json:4`
- `scripts/ci/emergency_python_wheels.json:5-25`

## Verification

Run:

```bash
rg -n "^(pillow|cryptography)" requirements.in requirements-dev.in requirements-ci-lite.in constraints.txt requirements.txt requirements-dev.txt requirements-ci-lite.txt requirements-lock.txt
python3 - <<'PY'
import json
from pathlib import Path
manifest = json.loads(Path('scripts/ci/emergency_python_wheels.json').read_text())
print(any(item['package'] == 'pillow' and item['version'] == '12.2.0' for item in manifest['artifacts']))
PY
pytest -q tests/test_dependency_security_guard.py
python scripts/ci/check_docs_phase1_gates.py --files docs/security/GHSA-whj4-6x5x-4v2j-pillow.md
pre-commit run --all-files
```
