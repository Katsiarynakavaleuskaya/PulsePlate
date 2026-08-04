# Historical: `cryptography` approved-index availability advisory

## Status

This historical note originally tracked the temporary approved-index fallback
for `cryptography==46.0.7`, followed by the 48.0.1 security-floor rotation. Both
states are now superseded by
`docs/security/CRYPTOGRAPHY_50_0_0_ADVISORY_CLUSTER.md`. The history remains here
for audit continuity; it is not current runtime authority.

Current repo truth:

- minimum shared floor: `cryptography>=50.0.0,<51.0.0`;
- pinned runtime/dev/lock version: `cryptography==50.0.0`;
- emergency fallback: none; `scripts/ci/emergency_python_wheels.json` is an
  empty retired compatibility marker with `artifacts: []`;
- current advisory authority:
  `docs/security/CRYPTOGRAPHY_50_0_0_ADVISORY_CLUSTER.md`.

Current evidence is anchored by `requirements.in:43`, `requirements.txt:39`,
`tests/fixtures/dependency_security_schema.json:4`, and the retired empty
emergency marker at `scripts/ci/emergency_python_wheels.json:5`.

Historically, the exact-wheel fallback was a time-boxed mirror-lag bridge only.
It was retired after approved-proxy parity and must not be described as active
or reactivated by this advisory rotation.

## Prohibited Shortcuts

- Do not repin below `50.0.0` to make CI green.
- Do not add ignores or waivers for the current GHSA cluster.
- Avoid broad `--extra-index-url` or unrestricted public PyPI installs.
- Do not widen this manifest into a generic package bypass lane.

## References

- `docs/security/SFTY-20260615-python-runtime-floors.md`
- `docs/security/CRYPTOGRAPHY_50_0_0_ADVISORY_CLUSTER.md`
- `scripts/ci/emergency_python_wheels.json`
- `scripts/ci/install_locked_python_requirements.py`
- `.github/actions/python-setup/action.yml`
- `Dockerfile`
