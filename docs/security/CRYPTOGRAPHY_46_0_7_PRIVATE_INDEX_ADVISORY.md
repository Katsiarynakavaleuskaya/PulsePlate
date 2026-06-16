# `cryptography` approved-index availability advisory

## Status

This note originally tracked the temporary approved-index fallback for
`cryptography==46.0.7`. That floor is superseded as of 2026-06-16 by the June
2026 Safety feed update recorded in
`docs/security/SFTY-20260615-python-runtime-floors.md`.

Current repo truth:

- minimum floor: `cryptography>=48.0.1`
  (`requirements.in:44`, `requirements-dev.in:21`)
- pinned runtime/dev/lock version: `cryptography==48.0.1`
  (`requirements.txt:35`, `requirements-dev.txt:50`,
  `requirements-lock.txt:76`)
- emergency fallback: exact `cryptography==48.0.1` Linux x86_64 wheels in
  `scripts/ci/emergency_python_wheels.json:8` and
  `scripts/ci/emergency_python_wheels.json:15`
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
