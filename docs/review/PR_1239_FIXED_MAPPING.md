# PR 1239 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: 77dd3558
Evidence: scripts/ci/check_pygments_exception_guard.py:44; scripts/ci/check_pygments_exception_guard.py:151; scripts/ci/check_pygments_exception_guard.py:182; scripts/ci/check_pygments_exception_guard.py:231; tests/test_check_pygments_exception_guard.py:138; tests/test_check_pygments_exception_guard.py:167; docs/security/GHSA-5239-wwwm-4pmq-pygments.md:40

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1239#pullrequestreview-4011711126 -> 77dd3558
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1239#discussion_r2992728990 -> 77dd3558
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1239#discussion_r2992728992 -> 77dd3558
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1239#discussion_r2992737981 -> 77dd3558
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1239#discussion_r2992737983 -> 77dd3558
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1239#pullrequestreview-4011724760 -> 77dd3558
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1239#discussion_r2992742048 -> 77dd3558
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1239#pullrequestreview-4011748005 -> 77dd3558
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1239#discussion_r2992765400 -> 77dd3558
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1239#discussion_r2992765404 -> 77dd3558
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1239#discussion_r2992765412 -> 77dd3558
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1239#discussion_r2992765418 -> 77dd3558

Disposition: FIXED
Commit: 41bb6bc9
Evidence: scripts/ci/check_pygments_exception_guard.py:19; scripts/ci/check_pygments_exception_guard.py:36; scripts/ci/check_pygments_exception_guard.py:156; scripts/ci/check_pygments_exception_guard.py:195; tests/test_check_pygments_exception_guard.py:171; tests/test_check_pygments_exception_guard.py:181; tests/test_check_pygments_exception_guard.py:220
Reason: The guard no longer depends on `packaging` at runtime, the seam matcher now tolerates quoted/commented YAML list items, and the review-requested typing and regression coverage were added in the guard test module.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1239#pullrequestreview-4011831424 -> 41bb6bc9
