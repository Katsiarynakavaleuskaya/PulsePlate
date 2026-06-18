# PR #1991 Fixed in Commit Mapping

## Summary

This PR locks local/manual eval and data dependency profiles without changing
runtime, Docker, CI-lite, legacy route, OpenAPI, provider, semantic-cache, or
RAG runtime ownership.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/29298b313b5c.json`
- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1991>
- Branch: `codex/lock-eval-data-deps`
- Role order executed pre-open:
  `agent-coordinator -> dev-operator -> security-auditor -> qa-engineer-agent -> cursor-specialist-agent -> web-research-agent`
- Scope: `requirements-data.in`, `requirements-data.txt`,
  `requirements-evals.in`, `requirements-evals.txt`,
  `docs/DEPENDENCY_MANAGEMENT.md`, `docs/evals/RAGAS_SETUP.md`,
  `evals/AGENTS.md`, and `tests/test_python_supply_chain_controls.py`.

## Premortem Closure

- Decision: `proceed` for a narrow dependency-governance PR.
- `PM-PR1-001`: compiled lockfiles could leak private package-proxy or local
  path data. Disposition: FIXED. Evidence: locks were regenerated with
  `--no-emit-index-url`, and `tests/test_python_supply_chain_controls.py`
  asserts no index URL, proxy env, local path, direct URL, or unpinned compiled
  entries.
- `PM-PR1-002`: eval/data dependencies could accidentally become runtime,
  Docker, or generic CI dependencies. Disposition: FIXED. Evidence:
  `tests/test_python_supply_chain_controls.py` asserts `ragas`, `datasets`,
  and `pandas` stay out of default install surfaces and that eval/data profiles
  do not join shared installer/Docker routing.
- `PM-PR1-003`: adding `pyarrow` to the data profile could be mistaken for a
  runtime ownership change. Disposition: NOT-A-BUG. Evidence:
  `docs/DEPENDENCY_MANAGEMENT.md` states the data profile preserves existing
  runtime/CI ownership, and this diff has no Dockerfile, workflow, runtime
  app/core, OpenAPI, legacy route, or `requirements-rag-vector*` changes.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/pr1-lock-eval-data-deps-oracle-packet-v2.json`
- Artifact: `artifacts/orchestration/experiments/results/exp-787b8e706155.json`
- Status: accepted.
- Runner mode: `oracle_only_governance_reviewer`.
- Contribution kind: `commit_decision`.
- Co-author required: `true`.
- Source diff applied: yes.
- Source diff paths: `docs/DEPENDENCY_MANAGEMENT.md`,
  `docs/evals/RAGAS_SETUP.md`, `evals/AGENTS.md`,
  `requirements-data.in`, `requirements-data.txt`,
  `requirements-evals.in`, `requirements-evals.txt`,
  `tests/test_python_supply_chain_controls.py`.
- Oracles: `python -m pytest -q tests/test_python_supply_chain_controls.py`;
  `python -m pytest -q tests/evals`.
- Implementation commit `ffd1341b16c4ee77f7b3c4607d9c8bcbc1a5cdbf`
  includes:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.
- Note: `python scripts/ci/install_locked_python_requirements.py
  --preflight-only` was run as local evidence outside Experiment Runner because
  the sandboxed oracle must not carry the approved package-proxy env value in
  the packet.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- No review threads were present to resolve at initial PR open.
- Post-open role passes, bot comments, current-head CI, strict disposition, and
  strict merge-readiness checks remain pending before any merge-readiness claim.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: ffd1341b16c4ee77f7b3c4607d9c8bcbc1a5cdbf
Evidence: `requirements-data.in`, `requirements-data.txt`, `requirements-evals.in`, `requirements-evals.txt`, `docs/DEPENDENCY_MANAGEMENT.md`, `docs/evals/RAGAS_SETUP.md`, `evals/AGENTS.md`, and `tests/test_python_supply_chain_controls.py`.
Reason: Adds compiled local/manual eval and data dependency locks, documents ownership boundaries, and guards against runtime/Docker/CI-lite leakage.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1991 -> ffd1341b16c4ee77f7b3c4607d9c8bcbc1a5cdbf

## Local Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/task_bootstrap.py ... --pr-phase pre_open`
  (packet `artifacts/orchestration/task_packets/29298b313b5c.json`)
- PASS: pre-open role dispatch order executed:
  `agent-coordinator -> dev-operator -> security-auditor -> qa-engineer-agent -> cursor-specialist-agent -> web-research-agent`
- PASS: `.venv/bin/python -m pytest -q tests/test_python_supply_chain_controls.py`
  (`56 passed`, existing Starlette/httpx deprecation warning)
- PASS: `.venv/bin/python -m pytest -q tests/evals`
  (`216 passed`, existing Starlette/httpx deprecation warning)
- PASS: `.venv/bin/python scripts/ci/install_locked_python_requirements.py --preflight-only`
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS: pre-push hooks during
  `git push -u origin codex/lock-eval-data-deps`, including `pip-audit`,
  backend tests, and full-repo Bandit
- PASS: Experiment Runner oracle artifact
  `artifacts/orchestration/experiments/results/exp-787b8e706155.json`
  accepted

## Merge Readiness

- [ ] Current-head CI terminal success confirmed.
- [ ] Post-open `qa-engineer-agent` pass completed.
- [ ] Post-open `bug-hunter` pass completed.
- [ ] Post-open `security-auditor` pass completed.
- [ ] Codex Security diff scan / finding discovery completed.
- [ ] `pulseplate-pr-review` completed.
- [ ] CodeRabbit / Sourcery / Cubic actionables checked and mapped or
  dispositioned on the current head.
- [ ] Strict review-thread disposition passes with auth.
- [ ] Strict merge-readiness guard passes with auth.
- [ ] Mandatory wait-window after latest bot/review activity completed.

## Deferred / Follow-ups

- Later dependency-governance PR may address `requirements-all.txt` /
  `verify_requirements.py` retirement.
- Later backend lane may continue runtime/security invariant guards or the next
  narrow legacy seam shrink.
