# PR 1251 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1251#pullrequestreview-4017422306 -> 4fa6745d
Disposition: FIXED
Commit: 4fa6745d
Evidence: scripts/ci/install_locked_python_requirements.py:190

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1251#pullrequestreview-4017441804 -> 4fa6745d
Disposition: FIXED
Commit: 4fa6745d
Evidence: .env.example:34

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1251#pullrequestreview-4017449532 -> 4fa6745d
Disposition: FIXED
Commit: 4fa6745d
Evidence: .github/workflows/build.yml:39

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1251#discussion_r2997610174 -> 0e91b1d6
Disposition: FIXED
Commit: 0e91b1d6
Evidence: tests/test_python_supply_chain_controls.py:118

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1251#discussion_r2997722390 -> a49f3328
Disposition: FIXED
Commit: a49f3328
Evidence: tests/test_python_supply_chain_controls.py:105

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1251#discussion_r2997739890 -> 4fa6745d
Disposition: FIXED
Commit: 4fa6745d
Evidence: scripts/ci/install_locked_python_requirements.py:190

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1251#discussion_r2997739896 -> 4fa6745d
Disposition: FIXED
Commit: 4fa6745d
Evidence: tests/test_python_supply_chain_controls.py:144

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1251#discussion_r2997745153 -> 4fa6745d
Disposition: FIXED
Commit: 4fa6745d
Evidence: scripts/ci/check_python_startup_hooks.py:113

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1251#discussion_r2997745159 -> 4fa6745d
Disposition: FIXED
Commit: 4fa6745d
Evidence: .github/workflows/cd.yml:265

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1251#discussion_r2997745162 -> 4fa6745d
Disposition: FIXED
Commit: 4fa6745d
Evidence: scripts/ci/check_python_startup_hooks.py:78

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1251#discussion_r2997757524 -> 4fa6745d
Disposition: FIXED
Commit: 4fa6745d
Evidence: .github/workflows/cd.yml:265

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1251#discussion_r2997757530 -> 4fa6745d
Disposition: FIXED
Commit: 4fa6745d
Evidence: .env.example:34

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1251#discussion_r2997757538 -> 4fa6745d
Disposition: FIXED
Commit: 4fa6745d
Evidence: docs/roadmap/BACKLOG_LEDGER.md:7729

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1251#discussion_r2997757547
Disposition: NOT-A-BUG
Evidence: tests/test_install_locked_python_requirements.py:91
Reason: `validate_private_proxy_url()` still raises `RuntimeError`, and local `pytest -q tests/test_install_locked_python_requirements.py` plus `make verify` passed on current head with the existing test contract.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1251#discussion_r2997765481 -> 4fa6745d
Disposition: FIXED
Commit: 4fa6745d
Evidence: scripts/ci/install_locked_python_requirements.py:196

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1251#discussion_r2997765489 -> 4fa6745d
Disposition: FIXED
Commit: 4fa6745d
Evidence: .github/workflows/build.yml:16

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1251#discussion_r2997765493 -> 4fa6745d
Disposition: FIXED
Commit: 4fa6745d
Evidence: .github/workflows/cd.yml:265

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1251#discussion_r2997765495 -> 4fa6745d
Disposition: FIXED
Commit: 4fa6745d
Evidence: tests/test_python_supply_chain_controls.py:144

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1251#discussion_r2997765499 -> 4fa6745d
Disposition: FIXED
Commit: 4fa6745d
Evidence: scripts/ci/check_python_startup_hooks.py:103

## Merge Readiness
- [x] Local `python -m pre_commit run --all-files` passed on current head
- [x] Local `make verify` passed on current head
- [ ] Required CI checks are green on current head
- [ ] GitHub approved proxy provisioning is present for `PULSEPLATE_PYTHON_INDEX_URL`
- [ ] Mandatory wait-window completed after the latest bot/review activity
