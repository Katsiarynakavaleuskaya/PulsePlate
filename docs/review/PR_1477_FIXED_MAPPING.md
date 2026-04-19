<!-- markdownlint-disable MD034 -->
# PR 1477 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Bot and human review threads must be dispositioned below; resolve conversations on GitHub after mapping.

## Fixed in Commit Mapping

- No actionable review comments

## Merge Readiness

- [ ] Current-head CI green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`

### Local validation evidence

- [x] `pre-commit run --all-files`
- [x] `make lint`
- [x] `make typecheck`
- [x] `make test-fast`
- [x] Targeted telemetry and supply-chain tests
- [x] Accelerated full-suite coverage plus `diff-cover` equivalent completed
- [ ] Canonical local `make verify`
  Evidence: single-process `make diff-cov` still receives external `SIGTERM` in this environment during the full coverage run; do not mark merge-ready on that basis until current-head CI proves green.
<!-- markdownlint-enable MD034 -->
