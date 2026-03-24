## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: NOT-A-BUG
Evidence: `.github/workflows/build.yml` — `publish` builds and pushes the image before `trivy image`; failing late does not roll back GHCR. Unconditional `upload-sarif` failed `main` when SARIF was absent (CodeQL “Path does not exist”). Conditional upload plus `--exit-code 0`, `continue-on-error` on the scan step, and a `::warning::` step when SARIF is missing preserve publish while surfacing outages; filesystem Trivy remains in job `security-scan`.
Reason: Intentional resilience vs. upload-sarif hard-fail; observability via logs and workflow warning, not job failure after push.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1232#discussion_r2983561400

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (per disposition evidence)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] `pre-commit run --all-files` green on latest head
