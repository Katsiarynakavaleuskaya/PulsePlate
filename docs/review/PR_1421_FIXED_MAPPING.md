# PR #1421 — Fixed in Commit Mapping (SoT)

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Bot and human review threads must be dispositioned here before they are resolved on GitHub.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: d5ec0b1fd
Evidence: `scripts/orchestration/skill_router.py:563`, `scripts/install_codex_skills.sh:16`, `docs/orchestration/CODEX_SKILLS_ALIGNMENT_MATRIX.md:103`, `tests/test_skill_router.py:822`, `tests/test_install_codex_skills.py:84`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1421#pullrequestreview-4102192873 -> d5ec0b1fd
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1421#pullrequestreview-4102217284 -> d5ec0b1fd
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1421#discussion_r3076053210 -> d5ec0b1fd
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1421#discussion_r3076053217 -> d5ec0b1fd
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1421#discussion_r3076074163 -> d5ec0b1fd

Disposition: FIXED
Commit: a28d0eb51
Evidence: `scripts/install_codex_skills.sh:15`, `docs/dev/CODEX_SKILLS.md:33`, `tests/test_install_codex_skills.py:15`, `tests/test_install_codex_skills.py:117`, `tests/test_install_codex_skills.py:221`, `tests/test_install_codex_skills.py:253`, `scripts/orchestration/skill_router.py:658`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1421#pullrequestreview-4102437752 -> a28d0eb51
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1421#discussion_r3076053213 -> a28d0eb51
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1421#discussion_r3076074484 -> a28d0eb51
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1421#discussion_r3076277772 -> a28d0eb51
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1421#discussion_r3076277776 -> a28d0eb51
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1421#discussion_r3076277777 -> a28d0eb51
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1421#discussion_r3076295408 -> a28d0eb51
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1421#discussion_r3076295411 -> a28d0eb51
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1421#discussion_r3076295425 -> a28d0eb51

Disposition: FIXED
Commit: cec72f9ad
Evidence: `scripts/orchestration/skill_router.py:623`, `tests/test_skill_router.py:863`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1421#discussion_r3076288592 -> cec72f9ad

Disposition: FIXED
Commit: 0e9de55bf
Evidence: `docs/roadmap/BACKLOG_LEDGER.md:4528`, `docs/dev/CODEX_SKILLS.md:33`, `tests/test_install_codex_skills.py:253`, `scripts/orchestration/skill_router.py:658`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1421#pullrequestreview-4102455229 -> 0e9de55bf
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1421#discussion_r3076295432 -> 0e9de55bf

Disposition: FIXED
Commit: 6eaa74b5e
Evidence: `.cursor/rules/cybersecurity-skills-index.md:31`, `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md:194`, `docs/orchestration/CODEX_SKILLS_ALIGNMENT_MATRIX.md:71`, `docs/roadmap/BACKLOG_LEDGER.md:4527`, `docs/roadmap/BACKLOG_LEDGER.md:8987`, `scripts/orchestration/skill_router.py:644`, `tests/test_skill_router.py:691`, `tests/test_install_codex_skills.py:182`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1421#discussion_r3080428419 -> 6eaa74b5e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1421#discussion_r3080428435 -> 6eaa74b5e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1421#discussion_r3080428444 -> 6eaa74b5e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1421#pullrequestreview-4106992423 -> 6eaa74b5e

Disposition: NOT-A-BUG
Reason: `pillow==12.2.0` is published on PyPI and resolvable; lockfiles were regenerated with `python -m piptools compile` and pre-push `pip-audit` passes on the branch.
Evidence: `requirements-lock.txt:329`, `requirements.txt:161`, `requirements-ci-lite.txt:228`; local `python -m pip index versions pillow` lists `12.2.0` among available versions; dependency bump landed in `713528388` (`build(deps): raise pillow security floor`).
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1421#discussion_r3080428440

## Merge Readiness

- [ ] Current-head CI green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [x] Pre-commit green on latest pushed head
- [ ] `make verify` green on latest pushed head
