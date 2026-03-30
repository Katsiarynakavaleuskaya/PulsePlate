# PR 1275 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 57e679d7078dd7843b2c2833a3511db8ea6cc6cd
Evidence: `requirements.txt:41` restores `cuda-bindings` Linux/x86_64 marker; `requirements.txt:298` restores `triton` marker; matching `requirements-lock.txt` lines mirror `origin/main` platform constraints while keeping `transformers==5.4.0`.
Reason: Dependabot/pip-compile regeneration dropped PEP 508 platform markers for CUDA wheels; restored markers so non-Linux installs stay viable while retaining the transformers bump.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1275#pullrequestreview-4026302684 -> 57e679d7078dd7843b2c2833a3511db8ea6cc6cd
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1275#discussion_r3005650400 -> 57e679d7078dd7843b2c2833a3511db8ea6cc6cd
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1275#discussion_r3005650402 -> 57e679d7078dd7843b2c2833a3511db8ea6cc6cd

Disposition: FIXED
Commit: 248db9a28ad1810e4c561f738ff59497c0b943d9
Evidence: `requirements.txt` / `requirements-lock.txt` keep `transformers==5.4.0` but pin `sentence-transformers==5.3.0` because CI installs from `pulseplate-staging.duckdns.org`, which does not publish `sentence-transformers==5.4.0` yet. `sentence-transformers` 5.3.0 allows `transformers<6,>=4.41` per PyPI.
Reason: unblock locked `pip install` in `test-pr` without downgrading `transformers`.

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
- [ ] `make verify` green
- Dependabot dependency bump PR (`transformers` 5.3.0 → 5.4.0); governance artifact for Phase 2 / merge-readiness gates.
