# PR #1769 Premortem: Dependabot #1757 Quality Tooling Replacement

## Summary

Plan: replace Dependabot PR `#1757` from fresh `origin/main`, preserving only
`black 26.5.0`, `mypy 2.1.0`, `ruff 0.15.13`, and the mechanically required
`librt 0.11.0` transitive floor for `mypy`.

Failure frame: it is 48 hours from now and this dependency tooling PR made the
main branch harder to install or verify.

## Most Likely Failure

The approved private index lags the new tool versions and CI fails despite local
success. The coordinator and security pass confirmed the proxy currently serves
HTTP 200 but does not expose `mypy==2.1.0` or `ruff==0.15.13`, so the PR must
carry exact emergency-wheel entries for those two packages.

Containment: keep the fallback private-index-only in behavior, exact-wheel-only
in scope, and SHA256-pinned in `scripts/ci/emergency_python_wheels.json`.

Disposition: FIXED in this PR by updating only the `mypy` and `ruff` emergency
manifest entries and adding regression coverage tying active fallback versions
to the dependency surfaces.

## Most Dangerous Failure

The replacement PR silently widens into broad lockfile churn or a public-index
bypass. That would weaken the supply-chain boundary the dependency installer is
meant to enforce.

Containment: do not change installer code, do not add a `black` emergency wheel,
and keep all public-host usage limited to existing exact emergency artifact
staging with digest verification.

Disposition: FIXED in this PR by keeping installer semantics unchanged and
testing that `black` is not present in the active emergency fallback set.

## Hidden Assumption

The original Dependabot diff can be copied directly. It cannot: `mypy 2.1.0`
requires `librt>=0.11.0`, and the emergency manifest must move with `mypy` and
`ruff` to avoid private-index false-green drift.

## Revised Plan

- Preserve the quality tool bumps across `constraints.txt`,
  `requirements-all.txt`, `requirements-dev.in`, `requirements-dev.txt`, and
  `requirements-lock.txt`.
- Carry `librt==0.11.0` only as the `mypy 2.1.0` transitive requirement.
- Update only the active `mypy` and `ruff` emergency wheel entries with exact
  PyPI filenames, URLs, and SHA256 digests.
- Add focused regression coverage for the quality-tooling replacement contract.
- Document the machine-heavy `make verify` deferral in the PR body and final
  fixed mapping.

## Pre-Merge Checklist

- `check_preflight.py` and `check_agent_consistency.py` pass.
- Focused dependency/supply-chain tests pass.
- `make lint` and `make typecheck` pass under the repo venv so the bumped
  `ruff` and `mypy` toolchain is exercised directly.
- `make validate-changed` passes.
- `pre-commit run --all-files` passes, including generated `.secrets.baseline`
  updates if any.
- Current-head PR CI reaches terminal/pass for required touched surfaces.
- Review threads and bot findings are mapped in `docs/review/PR_1769_FIXED_MAPPING.md`.

## Decision

Proceed with changes. No unresolved premortem blocker remains before opening the
replacement PR.
