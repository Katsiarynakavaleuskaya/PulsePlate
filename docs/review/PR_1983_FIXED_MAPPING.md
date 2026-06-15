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
- Co-author trailer required and used on the real branch commit range
  `origin/main..HEAD`; `git log --format=%B origin/main..HEAD` shows the
  canonical `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`
  trailer on every branch commit.

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
    `d1ac585edc1b0eae6c4370e438c6d3b98f1d679c`
  - Evidence: this replacement PR carries the intended
    `transformers==5.12.0` deltas and the emergency-fallback governance that
    raw #1975 did not include.
- Replacement PR #1983 review threads: none at artifact creation time.
- Post-open Codex review:
  - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1983#discussion_r3414537483`
    - Disposition: FIXED.
    - Commit: `f31420e3607d78622418efe9111b04ede41651a3`
    - Evidence: raw #1975 replacement proof now points at real branch ancestor
      `d1ac585edc1b0eae6c4370e438c6d3b98f1d679c`, not sibling
      `e834962f3b3733afafac0a26b0a7d607e912078a`.
  - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1983#discussion_r3414537495`
    - Disposition: FIXED.
    - Commit: `f31420e3607d78622418efe9111b04ede41651a3`
    - Evidence: validation now records the real approved-proxy
      `pip download --no-deps transformers==5.12.0` wheel probe instead of
      relying only on installer preflight.
  - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1983#discussion_r3414537498`
    - Disposition: FIXED.
    - Commit: `f31420e3607d78622418efe9111b04ede41651a3`
    - Evidence: Experiment Runner attribution evidence now refers to the real
      branch commit range `origin/main..HEAD`, whose commits carry the
      canonical trailer.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: e34a357f25d2aba717465c675595581e64301126
Evidence: PR #1981 removed the invalid `.github/dependabot.yml` assignee config on `main`; that commit is reachable from the base of this replacement PR.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1975#issuecomment-4700568423 -> e34a357f25d2aba717465c675595581e64301126

Disposition: FIXED
Commit: d1ac585edc1b0eae6c4370e438c6d3b98f1d679c
Evidence: this replacement PR carries the intended `transformers==5.12.0` deltas and the emergency-fallback governance that raw #1975 did not include; `d1ac585edc1b0eae6c4370e438c6d3b98f1d679c` is an ancestor of the current PR branch and includes the dependency/fallback/mapping stack.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1975 -> d1ac585edc1b0eae6c4370e438c6d3b98f1d679c

Disposition: FIXED
Commit: f31420e3607d78622418efe9111b04ede41651a3
Evidence: mapping evidence now points at a real PR-branch ancestor, fallback retirement validation records the approved-proxy `pip download --no-deps transformers==5.12.0` probe, and Experiment Runner attribution evidence is aligned with the real branch commit range.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1983#discussion_r3414537483 -> f31420e3607d78622418efe9111b04ede41651a3
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1983#discussion_r3414537495 -> f31420e3607d78622418efe9111b04ede41651a3
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1983#discussion_r3414537498 -> f31420e3607d78622418efe9111b04ede41651a3

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
- `python3 -m pip download --isolated --index-url "$PULSEPLATE_PYTHON_INDEX_URL" --only-binary=:all: --no-deps --dest "$tmp_wheelhouse" transformers==5.12.0`: PASS; the approved private proxy downloaded `transformers-5.12.0-py3-none-any.whl`.

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

## Post-Open Review Closure

- PASS after fix: `qa-engineer-agent` found Phase2 parser-shape blockers and
  a test gap. Commit `141b1a21960cf393431aea5365d008b137d6033b` repaired the
  parser-safe artifact/body mirror and made the guard assert exact
  `transformers==5.12.0`.
  Current branch containment was rechecked after the post-open review:
  `git merge-base --is-ancestor 141b1a21960cf393431aea5365d008b137d6033b HEAD`
  passed at head `d4b4e77df481bd55f642e66c64f72e6c22390b6e`.
- PASS: `bug-hunter` found no regressions or false-green findings after
  `141b1a21960cf393431aea5365d008b137d6033b`.
- PASS: `security-auditor` found no supply-chain/security findings after
  `141b1a21960cf393431aea5365d008b137d6033b`.
- PASS: Codex Security diff scan / finding discovery completed with 9/9
  explicit worklist receipts and no candidate findings:
  `/tmp/codex-security-scans/BMI-App_2025_clean/pr1983_141b1a21960c_20260615T150718Z/report.md`.
- PASS: `pulseplate-pr-review` dry-run report produced no deterministic
  findings:
  `/tmp/pulseplate_pr1983_review_report.md`.
- PASS: `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 1983 --body "$(gh pr view 1983 --repo Katsiarynakavaleuskaya/PulsePlate --json body --jq .body)" --commit-range origin/main..HEAD --experiment-runner-evidence-mode required`.
- PASS: `GH_TOKEN="$(gh auth token)" python3 scripts/orchestration/check_review_threads_disposition.py --pr-number 1983 --require-auth`.

## Merge Readiness

Not ready yet. Required current-head CI, strict merge-readiness auth check, and
mandatory wait-window still need final confirmation after the latest push and
bot activity.
