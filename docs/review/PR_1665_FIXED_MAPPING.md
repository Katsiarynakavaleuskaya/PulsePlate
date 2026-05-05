# PR #1665 Fixed in Commit Mapping

Canonical review-governance artifact for PR #1665:
<https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1665>

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

### Actionable findings fixed by this PR

Disposition: FIXED
Commit: 02c183294
Evidence:
- `tests/test_run_safety_audit.py` adds execution-level CPU Safety manifest artifact coverage and high-risk aggregate failure coverage.
- `tests/test_python_supply_chain_controls.py` adds structured dependency-submission path assertions and behavioral `pip-audit` helper invocation coverage for `requirements-rag-vector-cpu.txt`.
- `tests/test_ci_risk_profile.py` parametrizes CPU `.in` and `.txt` routing and checks emitted CI outputs.

Internal role findings fixed by commit `02c183294`:
- Local QA finding: pip-audit inclusion was only string-tested.
- Local QA finding: dependency-submission filters were not structurally asserted.
- Local QA finding: CPU `.in` risk routing was untested.
- Local bug-hunter finding: Safety CPU coverage lacked execution proof.

### Existing bot comments

Disposition: NOT-A-BUG
Evidence: Current external bot comments are rate-limit, summary, or no-issue comments rather than actionable code findings. Cubic reported no issues; CodeRabbit and Sourcery were rate-limited/comment-only at the inspected head.

Mappings:
- <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1665#issuecomment-4374157329>
- <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1665#issuecomment-4374157741>
- <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1665#issuecomment-4374254089>

## Merge Readiness

- [x] Canonical mapping artifact exists.
- [x] Focused tests passed: `.venv/bin/python -m pytest -q tests/test_run_safety_audit.py tests/test_python_supply_chain_controls.py tests/test_ci_risk_profile.py`.
- [ ] `pre-commit run --all-files` passed.
- [ ] `make validate-changed` passed.
- [ ] Strict merge-readiness wrapper passed on current head.
- [ ] Current-head GitHub CI parity is green.

Local full `make verify` is operator-deferred for this CI/security tooling PR unless explicitly requested. The PR must rely on focused local gates, `pre-commit run --all-files`, `make validate-changed`, current-head CI parity, and `check_merge_ready.py --require-auth`.

## Deferred / Follow-ups

- Broader future optional ML lockfile prevention is deferred to the PR-5 guard lane. This PR remains limited to the existing CPU RAG/vector profile and does not introduce a generic optional-manifest registry.
- Existing `scripts/ci_pip_audit.sh` advisory/fail-open behavior is not broadened in this hotfix. Making pip-audit fail-closed requires a separately scoped coordinator decision because this PR is limited to ensuring the CPU profile is included wherever the existing helper runs.
