# PR 1942 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1942#pullrequestreview-4477183535 is a Sourcery rate-limit notice and contains no code-actionable finding.
Reason: External reviewer quota notice; no repository code or documentation change is requested by the bot comment.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1942#pullrequestreview-4477183535

Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1942#issuecomment-4681091305 is a Codex review quota notice and contains no code-actionable finding.
Reason: External reviewer quota notice; no repository code or documentation change is requested by the bot comment.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1942#issuecomment-4681091305

Disposition: FIXED
Commit: 841b0ce6769a9f7b420532c1049d98e3e8c9eda4
Evidence: scripts/ci/run_safety_audit.py:425 adds transitive requirement/constraint include collection with cycle protection; scripts/ci/run_safety_audit.py:444 uses it when preparing the temp scan target.
Evidence: scripts/ci/run_safety_audit.py:581 folds non-zero Safety exit codes into the aggregate workflow verdict; scripts/ci/run_safety_audit.py:659 prints non-zero Safety exits as errors in main.
Evidence: tests/test_run_safety_audit.py:177 covers nested include copying; tests/test_run_safety_audit.py:198 covers include cycles; tests/test_run_safety_audit.py:310 covers non-zero Safety exits with below-HIGH parsed findings.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1942#pullrequestreview-4477432600 -> 841b0ce6769a9f7b420532c1049d98e3e8c9eda4
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1942#discussion_r3396494884 -> 841b0ce6769a9f7b420532c1049d98e3e8c9eda4

Disposition: FIXED
Commit: 5bda41d10cf08514fc1fe726db556b9d8cabfef5
Evidence: current-head `security` job failed because authenticated Safety Platform scan reported `fonttools` vulnerability `88739` as `ignored: null` while the repo policy carries a non-expired waiver for the private-index lag.
Evidence: scripts/ci/run_safety_audit.py:256 loads active repo policy waivers; scripts/ci/run_safety_audit.py:469 moves matching active Safety findings to ignored only when the waiver is valid; scripts/ci/run_safety_audit.py:737 keeps non-zero Safety exits fail-closed unless explained by repo-policy waivers.
Evidence: follow-up commit 530cf9b6ceaa5e4a51d60f597ec32a5dad354a83 loads PyYAML dynamically so the pre-push mypy hook does not require import stubs or a `type: ignore` suppression.
Evidence: tests/test_run_safety_audit.py:265 covers the cloud-policy-not-ignored case; tests/test_run_safety_audit.py:294 covers expired waiver blocking; tests/test_run_safety_audit.py:418 covers non-zero Safety exits with only repo-policy-waived findings.
Evidence: focused gates PASS: `pytest -q tests/test_run_safety_audit.py tests/test_python_supply_chain_controls.py tests/guards/test_security_devtooling_regression_guards.py`; `make validate-changed`; `pre-commit run --all-files`.

Disposition: FIXED
Commit: 066b6b8749b6de1e59b028fd1dbe194e10a0bbee
Evidence: scripts/ci/run_safety_audit.py:585 validates every top-level and nested requirement/constraint manifest source against the resolved repo root before reading it.
Evidence: scripts/ci/run_safety_audit.py:614 now passes the resolved repo root into recursive manifest collection, so nested out-of-root references fail through the intended SafetyAuditError path before any nested read.
Evidence: tests/test_run_safety_audit.py:154 covers the Cubic-reported nested manifest escape case.
Evidence: focused gates PASS: `pytest -q tests/test_run_safety_audit.py tests/test_python_supply_chain_controls.py tests/guards/test_security_devtooling_regression_guards.py`; `ruff check scripts/ci/run_safety_audit.py tests/test_run_safety_audit.py tests/test_python_supply_chain_controls.py`; `pre-commit run mypy --hook-stage pre-push --files scripts/ci/run_safety_audit.py`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1942#pullrequestreview-4477542316 -> 066b6b8749b6de1e59b028fd1dbe194e10a0bbee
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1942#discussion_r3396586707 -> 066b6b8749b6de1e59b028fd1dbe194e10a0bbee
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1942#discussion_r3397707944 -> 066b6b8749b6de1e59b028fd1dbe194e10a0bbee
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1942#discussion_r3397707946 -> 066b6b8749b6de1e59b028fd1dbe194e10a0bbee

Disposition: FIXED
Commit: d2e87590c8aca82cc9c1725eeff3e2ae8e2104d9
Evidence: scripts/ci/run_safety_audit.py:260 skips repo waiver overlay parsing for non-YAML policy files so TOML policies remain Safety-owned instead of failing through PyYAML.
Evidence: scripts/ci/run_safety_audit.py:539 wraps repo-policy waiver loading and application in the same write-and-reraise diagnostic path used by Safety report normalization.
Evidence: tests/test_run_safety_audit.py:344 covers TOML policy skip behavior; tests/test_run_safety_audit.py:351 covers malformed YAML policy errors writing the safety summary artifact before failing closed.
Evidence: focused gates PASS: `pytest -q tests/test_run_safety_audit.py tests/test_python_supply_chain_controls.py tests/guards/test_security_devtooling_regression_guards.py`; `ruff check scripts/ci/run_safety_audit.py tests/test_run_safety_audit.py tests/test_python_supply_chain_controls.py`; `ruff format --check scripts/ci/run_safety_audit.py tests/test_run_safety_audit.py tests/test_python_supply_chain_controls.py`; `pre-commit run mypy --hook-stage pre-push --files scripts/ci/run_safety_audit.py`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1942#pullrequestreview-4478857702 -> d2e87590c8aca82cc9c1725eeff3e2ae8e2104d9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1942#discussion_r3397707933 -> d2e87590c8aca82cc9c1725eeff3e2ae8e2104d9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1942#discussion_r3397707940 -> d2e87590c8aca82cc9c1725eeff3e2ae8e2104d9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1942#pullrequestreview-4478873734 -> d2e87590c8aca82cc9c1725eeff3e2ae8e2104d9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1942#discussion_r3397721876 -> d2e87590c8aca82cc9c1725eeff3e2ae8e2104d9

## External Review Availability Notes

External bot capacity or availability notices are not treated as code-actionable
findings or approval. This PR still waits for current-head CI, strict
merge-readiness, and the mandatory wait-window before any merge claim.

## Merge Readiness

- [ ] Current-head CI terminal success confirmed.
- [ ] Required checks complete with no pending jobs.
- [ ] Bot review/governance completed with no unmapped actionable comments.
- [ ] Strict review-thread disposition passes with auth.
- [ ] Strict merge-readiness guard passes with auth.
- [ ] Mandatory wait-window after latest bot/review activity completed.
