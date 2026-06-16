# `cryptography` approved-index availability advisory

## Status

This note originally tracked the temporary approved-index fallback for
`cryptography==46.0.7`. That floor is superseded as of 2026-06-16 by the June
2026 Safety feed update recorded in
`docs/security/SFTY-20260615-python-runtime-floors.md`.

Current repo truth:

- minimum floor: `cryptography>=48.0.1`
- pinned runtime/dev/lock version: `cryptography==48.0.1`
- emergency fallback: exact `cryptography==48.0.1` Linux x86_64 wheels in
  `scripts/ci/emergency_python_wheels.json`
- removal backlog:
  `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-cryptography-private-index-sync`

The fallback remains a time-boxed mirror-lag bridge only. The approved private
Python proxy is still the primary package source, and the manifest is not a
generic public-index bypass.

## Prohibited Shortcuts

- Do not repin below `48.0.1` to make CI green.
- Do not add Safety ignores or waivers for `SFTY-20260615-96125`.
- Do not add broad `--extra-index-url` or unrestricted public PyPI installs.
- Do not widen this manifest into a generic package bypass lane.

## References

- `docs/security/SFTY-20260615-python-runtime-floors.md`
- `scripts/ci/emergency_python_wheels.json`
- `scripts/ci/install_locked_python_requirements.py`
- `.github/actions/python-setup/action.yml`
- `Dockerfile`
