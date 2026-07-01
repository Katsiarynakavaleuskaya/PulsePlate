# Dependency Ownership Premortem

Branch: `codex/deps-ownership-pyarrow-cleanup`

Frame: it is 48 hours from now, and this dependency cleanup made `main` worse. The failure review below focuses on this exact diff: dependency-surface policy, runtime/CI lockfiles, and legacy ownership boundaries.

## Role Pass Summary

- `agent-coordinator`: scope remains dependency ownership only; no route, OpenAPI, runtime behavior, Docker, SQLite, or de-legacy extraction changes.
- `architecture-specialist`: legacy import evidence must stay transitional; canonical ownership must come from app/bootstrap, routers, services, core, or providers, with `app/services/bmi_compat.py` treated as transitional unless a future BMI owner decision promotes it.
- `security-auditor`: smaller runtime/CI dependency surface is positive only if generated locks avoid unrelated unsafe `pip` stanzas, local-path leakage, and fail-open validator wording.
- `qa-engineer-agent`: acceptance requires negative tests for blocking packages and report-only tests for transitional packages.
- `bug-hunter`: highest false-green risk is a broad validator that blocks future PRs on unaudited packages or a broad lock regeneration that hides unrelated upgrades.
- `cursor-specialist-agent`: PR docs and future fixed mapping must use repo-relative paths only.

## Findings

### PM-DEPS-001: Validator becomes a broad permanent red guard

Failure story: the checker starts enforcing every import/dependency mismatch in the repository. Future PRs unrelated to dependency hygiene fail on dynamic, lazy, or transitional imports, and the team starts bypassing the checker or treating it as noisy infrastructure.

Underlying assumption: import evidence alone is enough to decide all dependency ownership.

Early warning signs: new errors mention unaudited packages; warnings are mixed into hard failures without a severity boundary.

Containment action: keep default hard failures scoped to `pyarrow`, `pandas`, `httpx2`, and legacy-only canonical authority in the audited subset.

Disposition: FIXED. `scripts/ci/check_python_dependency_surfaces.py` emits `error`, `warning`, and `info` tiers and only fails `error` findings for the first audited subset.

### PM-DEPS-002: Legacy BMI paths legitimize `matplotlib`

Failure story: because `legacy_app.py` or root `bmi_visualization.py` references BMI visualization compatibility, reviewers conclude `matplotlib` is a canonical runtime dependency. The next cleanup cannot remove or extract it because infra docs have made legacy usage permanent authority.

Underlying assumption: any runtime import is ownership evidence.

Early warning signs: docs say `matplotlib` is runtime-owned by `legacy_app.py`; checker reports it as `canonical_runtime_owner_documented`.

Containment action: classify legacy BMI evidence as `legacy_compat_transitional` and require a future BMI owner decision before canonical promotion.

Disposition: FIXED. The checker reports current `matplotlib` as `warning:legacy_compat_transitional`, and docs state that legacy usage is transitional pressure, not ownership.

### PM-DEPS-003: `pyarrow` is removed from data/eval by accident

Failure story: the cleanup removes `pyarrow` from every requirements file, breaking offline data builders and Parquet-capable eval/data workflows while claiming runtime shrink success.

Underlying assumption: non-runtime means unused everywhere.

Early warning signs: `requirements-data.in` or `requirements-data.txt` loses `pyarrow`; data profile tests no longer assert the package.

Containment action: remove `pyarrow` only from runtime, CI-lite, aggregate, and constraints surfaces while keeping data ownership explicit.

Disposition: FIXED. `requirements-data.in` and `requirements-data.txt` still carry `pyarrow`; tests assert runtime/CI-lite absence and data presence.

### PM-DEPS-004: Lock regeneration reintroduces unsafe `pip` pins or broad churn

Failure story: `pip-compile --allow-unsafe` removes `pyarrow` but also adds `pip==...` unsafe stanzas or unrelated package upgrades. The PR becomes a hidden supply-chain change instead of an ownership cleanup.

Underlying assumption: regenerated output is always acceptable as-is.

Early warning signs: diffs in `requirements-ci-lite.txt` or `requirements-lock.txt` include `pip==` or unrelated version changes.

Containment action: review lock diffs after compile and keep the lockfile diff limited to `pyarrow` removal.

Disposition: FIXED. Generated unsafe `pip==26.1.2` stanzas were rejected; final lock diff removes only `pyarrow` stanzas from runtime/CI-lite/aggregate locks.

### PM-DEPS-005: Proxy proof is misleading

Failure story: the private proxy health check is reported red because local `PULSEPLATE_PYTHON_INDEX_URL` points at `/root/pypi/+simple/`, or because the default probes include test-only packages while the command omits `requirements-test.txt`. Reviewers treat that as dependency mirror breakage from this PR.

Underlying assumption: the pasted proxy command is always self-contained in every local environment.

Early warning signs: reason `unexpected_index_path` or `missing_exact_pin_in_requirements` appears before any package mirror failure.

Containment action: run the planned requirements with canonical URL and explicit pinned projects, and run the default probe set with `requirements-test.txt` included.

Disposition: NOT-A-BUG. The canonical URL targeted check passed for `aiosqlite`, `cryptography`, `requests`, and data-only `pyarrow`; the default probe set also passed once `requirements-test.txt` supplied the expected test pins.

### PM-DEPS-006: Experiment Runner evidence is overstated

Failure story: the PR body says Experiment Runner passed without noting that the zero-network oracle was blocked locally by missing Linux `unshare`. The evidence looks stronger than it is.

Underlying assumption: all Experiment Runner accepted artifacts are equivalent.

Early warning signs: local result has `failure_class=infra_flake` and no oracle results; accepted fallback uses nonzero `network_budget`.

Containment action: record both artifacts and state that the accepted fallback is review-required evidence, not a replacement for local gates or current-head CI.

Disposition: FIXED. `docs/review/PR_DEPS_OWNERSHIP_EXPERIMENT_RUNNER_EVIDENCE.md` records the zero-network infra failure and the accepted `network_budget=1` oracle-only fallback.

## Revised Plan

- Keep hard failures limited to the audited package subset.
- Keep `matplotlib`, `numpy`, and `aiosqlite` as warning/report-only classifications.
- Remove `pyarrow` only from runtime, CI-lite, aggregate, and constraints surfaces.
- Preserve `reportlab` canonical export/PDF ownership.
- Keep docs and future PR body/fixed mapping repo-relative.
- Do not claim merge readiness until post-open roles, bot review, current-head CI, and review-thread disposition pass.

## Pre-Merge Checklist

- `python3 scripts/ci/check_python_dependency_surfaces.py`
- `python3 verify_requirements.py`
- `.venv/bin/python -m pytest -q tests/test_python_dependency_surfaces.py tests/test_python_supply_chain_controls.py`
- `.venv/bin/python -m pytest -q tests/test_openapi_namespace_guards.py tests/test_exports.py tests/test_bmi_visualization.py`
- `python3 scripts/ci/install_locked_python_requirements.py --preflight-only`
- `make validate-changed`
- `pre-commit run --all-files`
- `git diff --check`
- Current-head CI and post-open `qa-engineer-agent -> bug-hunter -> security-auditor`, Codex Security diff scan, and `pulseplate-pr-review`.

## Decision

Proceed with changes. The diff is narrow enough for PR open after local gates, with the Experiment Runner fallback clearly labeled as review-required evidence and not as merge readiness.
