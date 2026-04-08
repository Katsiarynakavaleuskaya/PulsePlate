# fonttools TTX `eval()` advisory (remediation)

## Summary

PyPI `fonttools` releases before the fix used unsafe `eval()` when parsing certain TTX data. The upstream project replaced that path with restricted evaluation (`fonttools>=4.62.0` addresses Safety PyUp `88739`).

## Governance (intentional waiver)

- **Owner:** @katsiaryna_kavaleuskaya
- **Remove-by:** 2026-07-08 — reassess: if the approved private index lists `fonttools>=4.62.0`, bump pins and remove PyUp `88739` from `safety-policy.yaml` in the same PR; if the index still lags, extend remove-by in this doc + ledger note (same PR).
- **Backlog:** `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-fonttools-private-index-bump`

## Production exposure (posture)

The advisory concerns **TTX/XML font parsing** paths that called `eval()`. In this repo `fonttools` is **transitive (e.g. via matplotlib)** for typical plotting; PulsePlate does **not** ingest attacker-controlled `.ttx` in product flows today. **Re-assess** if you add user font upload, `ttx` on untrusted input, or similar. Residual scanner findings are accepted only until the private index mirrors a fixed wheel.

## Current repo state (2026-04)

- **Public PyPI:** `fonttools==4.62.1` (and other `>=4.62.0` builds) satisfy the advisory.
- **Approved private CI/Docker index:** may lag public PyPI. CI has failed with
  `No matching distribution found for fonttools==4.62.1 (from versions: 4.61.1)`
  when installing from `PULSEPLATE_PYTHON_INDEX_URL` (`scripts/ci/install_locked_python_requirements.py` / Docker locked install).
- **Pins:** `requirements.txt`, `requirements-ci-lite.txt`, and `requirements-lock.txt` use **`fonttools==4.61.1`** until the private index mirrors `>=4.62.0`.
- **Safety:** PyUp `88739` is ignored via `safety-policy.yaml` with an explicit reason and removal path when the pin bumps. Workflow still runs `parse-safety-report.py` on the JSON output.

## Remediation (when mirror syncs)

1. Bump `fonttools` to `>=4.62.0` on all pinned requirement surfaces (`requirements.txt`, `requirements-ci-lite.txt`, `requirements-lock.txt`).
2. Remove the `88739` entry from `safety-policy.yaml`.
3. Re-run `make verify` / CI locked install against the private index.
4. Close or update `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-fonttools-private-index-bump` per ledger policy.

## References

- Upstream fix: `https://github.com/fonttools/fonttools/commit/9caa12715c17ca5b846c6a640aaa5d3503fdbaa2`
- Safety entry: `https://getsafety.com/v/88739/97c`
- Locked install from approved index: `scripts/ci/install_locked_python_requirements.py:277`
- Safety scan in CI: `.github/workflows/security.yml:126`
