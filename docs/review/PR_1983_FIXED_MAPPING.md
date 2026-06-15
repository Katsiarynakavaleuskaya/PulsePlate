# PR #1983 Fixed Mapping

## Summary

This PR replaces raw Dependabot #1975 with a human-owned optional RAG/vector
dependency lane. It updates `transformers` from `5.10.2` to `5.12.0`, retires
the stale `transformers==5.10.2` emergency wheel fallback after approved
private-proxy evidence, and keeps torch CVE-2025-3000 out of scope while GitHub
reports no patched version.

## Lane Start Provenance

- Branch: `codex/rag-vector-transformers-1975`
- Packet: `artifacts/orchestration/task_packets/7c87d51844b6.json`
- Pre-open role order executed:
  `agent-coordinator -> security-auditor -> qa-engineer-agent -> dev-operator -> architecture-specialist`
- Implementation commit:
  `e834962f3b3733afafac0a26b0a7d607e912078a`

## Premortem

- Skill: `pulseplate-premortem-risk-review`
- Artifact:
  `artifacts/orchestration/premortem/rag-vector-transformers-1975-premortem.md`
- Decision: proceed with changes.
- Dispositions:
  - Resolver graph drift: FIXED by restoring lockfiles so only `transformers`
    changes.
  - Stale `transformers` emergency fallback: FIXED by removing the fallback
    and updating the guard test.
  - Torch CVE overclaim risk: NOT-A-BUG for this PR scope with fresh
    `patched=null` GitHub alert evidence.
  - Broader emergency fallback TTL: DEFERRED to
    `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-cryptography-private-index-sync`.

## Experiment Runner Evidence

- Packet:
  `artifacts/orchestration/experiments/rag-vector-transformers-1975-oracle-packet-v2.json`
- Artifact: `artifacts/orchestration/experiments/results/rag-vector-transformers-1975-oracle-result-v2.json`
- Mode: `oracle_only_governance_reviewer`
- Status: accepted.
- Oracle commands: 4/4 passed.
- `mutated_paths=[]`
- `shared_tree_untouched=true`
- Co-author trailer required and used on
  `e834962f3b3733afafac0a26b0a7d607e912078a`.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

- Raw Dependabot #1975 invalid-assignee bot comment:
  `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1975#issuecomment-4700568423`
  - Disposition: FIXED.
  - Commit:
    `e34a357f25d2aba717465c675595581e64301126`
  - Evidence: PR #1981 removed the invalid `.github/dependabot.yml`
    assignee config on `main`; that commit is reachable from the base of this
    replacement PR.
- Raw Dependabot #1975:
  `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1975`
  - Disposition: FIXED.
  - Commit:
    `e834962f3b3733afafac0a26b0a7d607e912078a`
  - Evidence: this replacement PR carries the intended
    `transformers==5.12.0` deltas and the emergency-fallback governance that
    raw #1975 did not include.
- Replacement PR #1983 review threads: none at artifact creation time.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: e34a357f25d2aba717465c675595581e64301126
Evidence: PR #1981 removed the invalid `.github/dependabot.yml` assignee config on `main`; that commit is reachable from the base of this replacement PR.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1975#issuecomment-4700568423 -> e34a357f25d2aba717465c675595581e64301126

Disposition: FIXED
Commit: e834962f3b3733afafac0a26b0a7d607e912078a
Evidence: this replacement PR carries the intended `transformers==5.12.0` deltas and the emergency-fallback governance that raw #1975 did not include.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1975 -> e834962f3b3733afafac0a26b0a7d607e912078a

## Validation

- `python3 scripts/orchestration/check_preflight.py`: PASS.
- `python3 scripts/orchestration/check_agent_consistency.py`: PASS.
- `python3 scripts/ci/install_locked_python_requirements.py --preflight-only`:
  PASS.
- `python3 scripts/ci/install_locked_python_requirements.py --preflight-only --requirements-profile rag-vector --rag-vector-requirements-file requirements-rag-vector.txt --emergency-wheel-manifest scripts/ci/emergency_python_wheels.json`:
  PASS.
- `python3 scripts/ci/install_locked_python_requirements.py --preflight-only --requirements-profile rag-vector --rag-vector-requirements-file requirements-rag-vector-cpu.txt --emergency-wheel-manifest scripts/ci/emergency_python_wheels.json`:
  PASS.
- `.venv/bin/python -m pytest -q tests/test_install_locked_python_requirements.py tests/test_python_supply_chain_controls.py tests/guards/test_security_devtooling_regression_guards.py`:
  PASS.
- `make validate-changed`: PASS.
- `pre-commit run --all-files`: PASS.
- Pre-push hooks: PASS, including `pip-audit`, backend tests, Bandit, and
  Docker build test.

## Security Notes

Fresh Dependabot alert query on 2026-06-15:

- Alert #160: `torch`, `requirements-rag-vector.txt`, vulnerable `<= 2.12.0`,
  `patched=null`.
- Alert #161: `torch`, `requirements-rag-vector-cpu.txt`,
  vulnerable `<= 2.12.0`, `patched=null`.
- Alert #162: `torch`, `requirements-ci-lite.txt`, vulnerable `<= 2.12.0`,
  `patched=null`.

Torch remains out of scope for PR #1983 until GitHub/Safety/upstream/private
index exposes a real patched version or a separate PR replaces/disables the
optional vector profile.

## Merge Readiness

Not ready yet. Required post-open work remains:

- Run post-open `qa-engineer-agent -> bug-hunter -> security-auditor`.
- Run Codex Security diff scan / finding discovery.
- Run `pulseplate-pr-review`.
- Confirm no unresolved review threads and no unmapped actionable bot comments.
- Confirm current-head CI parity and strict `check_merge_ready.py --require-auth`.
- Observe the mandatory wait-window after latest review/bot activity.
