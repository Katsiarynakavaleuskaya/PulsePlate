# PR #2116 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2116

Branch: `codex/experiment-runner-mac-strict-backend`

## Summary

Add a strict, evidence-only Apple Container execution backend for the local
PulsePlate Experiment Runner while preserving `network_budget=0`, immutable
image identity, fail-closed capability classification, and result-v1
compatibility.

## Lane Start Provenance

Packet: `artifacts/orchestration/task_packets/pr2116-post-open.json`
Starter: `scripts/orchestration/start_pr_lane.sh`

- The packet and role outputs are retained locally under the gitignored
  `artifacts/orchestration/` control plane.
- The coordinator-owned post-open order
  `qa-engineer-agent -> bug-hunter -> security-auditor` completed before the
  final ordinary `pulseplate-pr-review` pass.

## Implementation Commits

- `788450377` - add strict backend dispatch and capability probing.
- `0687a408d` - add the immutable non-root Runner image.
- `0451069be` - cover backend selection, mounts, redaction, and compatibility.
- `81d20e42b` - document strict macOS operations and authority boundaries.
- `dbae5283d` - make dispatcher result typing strict.
- `939104f5c` - classify pre-run capability drift as non-retryable.
- `affdb0e17` - guarantee resource cleanup on Runner failures.
- `b2915e00a` - close provenance, network-budget, filesystem-containment,
  cleanup, and post-probe capability false-green paths.
- `0684d9b43` - bind the positive-control canary to an exact host address and
  remove the wildcard-listener security finding.

## Discussion Thread Pass

- [x] Discussion-thread pass completed.
- [x] Fixed in commit mapping completed.
- [x] Post-open `qa-engineer-agent -> bug-hunter -> security-auditor` completed.
- [x] Ordinary `pulseplate-pr-review` completed on current head.
- [ ] Canonical current-head CI completed.
- [ ] Strict authenticated merge readiness and mandatory wait window completed.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 0684d9b43
Evidence: `scripts/orchestration/experiment_runner_dispatch.py` now resolves and binds one exact non-loopback host IPv4 address, never persists that address, and uses it only for the context-managed fixed-response positive control; `tests/test_experiment_runner_dispatch.py::test_host_bind_address_is_exact_non_loopback_ipv4` covers the selection contract and a real Apple probe returned `strict_isolation: true`.
Reason: The wildcard listener was eliminated while preserving the Apple VM host-reachability control required to prove that guest `unshare` actually removes connectivity.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2116#discussion_r3572512959 -> 0684d9b43

Disposition: FIXED
Commit: b2915e00a0c01060586decc71a89ed7dbbe82e00
Evidence: `scripts/orchestration/experiment_contract.py:886-909`, the capability schema `allOf` mapping, and `tests/test_experiment_runner_dispatch.py:415-447` reject mismatched and impossible backend provenance.
Reason: Backend name, isolation method, guest support, preflight state, result status, and capability failure class now form one coherent contract.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2116#discussion_r3572747164 -> b2915e00a0c01060586decc71a89ed7dbbe82e00

Disposition: FIXED
Commit: b2915e00a0c01060586decc71a89ed7dbbe82e00
Evidence: `scripts/orchestration/experiment_runner_dispatch.py` no longer imports `stat`; full local Ruff, flake8-bearing CI lint, and pre-commit validation cover the module.
Reason: The collector imports `stat` only inside its isolated source string, so the unused host-module import was removed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2116#discussion_r3572747168 -> b2915e00a0c01060586decc71a89ed7dbbe82e00

Disposition: FIXED
Commit: b2915e00a0c01060586decc71a89ed7dbbe82e00
Evidence: `_inspect_image` and `_cleanup_container` now use one common bounded argv; parametrized cleanup tests prove Apple and Docker force deletion still runs after graceful-stop errors.
Reason: The redundant branches were removed without changing backend-specific deletion behavior.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2116#pullrequestreview-4687150927 -> b2915e00a0c01060586decc71a89ed7dbbe82e00

Disposition: NOT-A-BUG
Evidence: Repo-required Black, Ruff, MyPy, pre-commit, focused tests, and current-head diff coverage are the canonical gates; the external docstring-per-function metric is not a PulsePlate contract.
Reason: Adding boilerplate docstrings to internal bounded helpers would expand this security-sensitive diff without improving an enforced interface or invariant.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2116#issuecomment-4960413001

Disposition: NOT-A-BUG
Evidence: Sourcery posted no code finding and states only that its external weekly character quota was exhausted; repo-native and current-head gates remain authoritative.
Reason: An external service quota is not a defect in this PR.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2116#pullrequestreview-4686868398

Disposition: NOT-A-BUG
Evidence: CodeRabbit's current-head review at `cfd6d3e3a` has an empty review body and created no unresolved discussion thread.
Reason: The current-head external review contains no actionable finding.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2116#pullrequestreview-4688294693

## Experiment Runner Evidence

Artifact: `artifacts/orchestration/experiments/results/mac-strict-oracle-current-head.json`

- Local-only, gitignored evidence at current source diff: `accepted`,
  `failure_class: null`, `shared_tree_untouched: true`, two oracle return codes
  `0`, `network_budget=0`, Apple Container 1.1.0, and immutable image digest
  `sha256:cefe9cfa20a89e2b24b4041c50d02f9bc202664d44e81470f962d5b72f063e13`.
- Candidate-mode evidence is also accepted with the same strict provenance and
  remains local-only.

## Validation Evidence

- PASS: orchestration preflight and agent consistency.
- PASS: 188 focused Runner, dispatcher, sandbox, and review-pattern tests.
- PASS: focused Ruff and MyPy.
- PASS: `make validate-changed`.
- PASS: `pre-commit run --all-files`.
- PASS: pre-push MyPy, pip-audit, backend tests, full-repo Bandit, and
  Containerfile build test.
- PASS: real Apple capability probe, oracle-only run, and candidate run.
- PENDING: canonical current-head GitHub CI and strict authenticated merge
  readiness.

Full local `make verify` was not run because repository policy prohibits that
machine-heavy invocation without a one-time human override.

## Security Review

- PASS: repo-native `security-auditor`, Bandit, Trivy,
  immutable-image history/config inspection, negative-network canaries, and
  mount-write controls produced no unresolved actionable defect at this head.
- PENDING: GitHub CodeQL confirmation of the exact-address canary fix on the
  new current head.
- The separate Codex Security plugin workflow was canceled by the operator
  after repeated platform safety-filter aborts. No incomplete or draft scan
  output is used as evidence, and the workflow must not be restarted for this
  PR.

## Risks / Rollback

Apple runtime or image drift, cleanup failure, unsupported filesystem
containment, and any ambiguous network state fail closed. Rollback is one PR
revert plus deletion of the local OCI image; no backend, OpenAPI, web, iOS,
database, GitHub App, or Slack rollback is required.

## Deferred / Follow-ups

- Apple Container remains opt-in local tooling.
- Native Linux remains on the existing direct Runner path until strict
  filesystem containment reaches parity.
- Public distribution, GitHub App, Slack, OCW/OSW, semantic cache, generic
  extraction, automatic promotion, merge, and deploy remain outside scope.
