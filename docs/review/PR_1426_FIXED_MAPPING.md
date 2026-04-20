<!-- markdownlint-disable MD034 -->
# PR 1426 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Bot and human review threads must be dispositioned here before they are resolved on GitHub.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1426#discussion_r3080134887
Disposition: FIXED
Commit: ec813602a
Evidence: `tests/test_install_locked_python_requirements.py:317`, `tests/test_install_locked_python_requirements.py:348`, and `tests/test_install_locked_python_requirements.py:374` now assert original-constraints path reuse and symmetric `install_from_wheelhouse` coverage for the testing gap Sourcery flagged.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1426#discussion_r3080134896
Disposition: FIXED
Commit: ec813602a
Evidence: `docs/review/PR_1426_FIXED_MAPPING.md:24` now uses the grammatically complete merge-readiness wording `Current-head CI is green for PR branch head`, matching the review request.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1426#pullrequestreview-4106659425
Disposition: FIXED
Commit: ec813602a
Evidence: `tests/test_install_locked_python_requirements.py:317`, `tests/test_install_locked_python_requirements.py:348`, `tests/test_install_locked_python_requirements.py:374`, and `docs/review/PR_1426_FIXED_MAPPING.md:24` cover the actionable Sourcery review items summarized in this review.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1426#discussion_r3080145564
Disposition: FIXED
Commit: 1d2ad1244
Evidence: `scripts/ci/install_locked_python_requirements.py:623` now creates the effective constraints file beside the original constraints file, and `tests/test_install_locked_python_requirements.py:254` verifies relative include paths remain resolvable.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1426#discussion_r3080175001
Disposition: FIXED
Commit: 1d2ad1244
Evidence: `scripts/ci/install_locked_python_requirements.py:623` and `tests/test_install_locked_python_requirements.py:254` implement and verify the relative-include-safe effective constraints rewrite requested in the CodeRabbit thread.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1426#pullrequestreview-4106703810
Disposition: FIXED
Commit: 1d2ad1244
Evidence: `scripts/ci/install_locked_python_requirements.py:623` and `tests/test_install_locked_python_requirements.py:254` address the actionable CodeRabbit review summary by preserving sibling include resolution in the rewritten constraints file and covering it with a regression test.

## Merge Readiness

- [ ] Current-head CI is green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
<!-- markdownlint-enable MD034 -->
