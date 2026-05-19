<!-- markdownlint-disable MD013 MD034 -->
# PR #1770 Premortem - idna 3.15 Dependabot security alerts

## Summary

Plan: fix Dependabot alerts #145-#151 by raising the exact `idna` pins from
`3.11` to `3.15` across the seven repo-managed Python requirement profiles, and
record Ruby `jwt` alert #142 as blocked/deferred because Fastlane still
constrains `jwt < 3`.

Failure frame: it is 48 hours from now; this hotfix made the dependency/security
state worse, and we are looking backward to understand why.

## Most likely failure

The most likely failure is a partial alert fix: one requirements profile stays
on `idna==3.11`, so Dependabot keeps reopening one of the Python alerts even
though the PR body claims the alert set is fixed.

Disposition: FIXED by adding a regression test that checks all seven alert
surfaces pin `idna==3.15` and do not pin `idna==3.11`.

## Most dangerous failure

The most dangerous failure is falsely claiming Ruby `jwt` alert #142 as fixed.
Forcing `jwt >= 3.2.0` would violate the current Fastlane dependency graph and
could break privileged App Store release tooling.

Disposition: DEFERRED. Existing backlog:
`docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-remove-trivy-suppression-jwt-cve-2026-45363`.
Resolver evidence was rechecked on 2026-05-19 and still shows Fastlane
`2.234.0` requiring `jwt >= 2.1.0, < 3`.

## Hidden assumption

The hidden assumption is that Dependabot's failed update means `idna 3.15` is
not installable. Local evidence shows the approved private Python index exposes
`idna 3.15`; the Dependabot updater failed while attempting broad resolver work,
not because the exact patched wheel is unavailable.

Disposition: NOT-A-BUG. This PR intentionally uses exact line edits rather than
broad `pip-compile` regeneration.

## Revised Plan

- Keep the diff to exact `idna==3.15` pins in the seven alert surfaces.
- Do not edit `requirements*.in`, `constraints.txt`, or `requirements-all.txt`
  because `idna` is not a direct declared requirement there.
- Do not add an emergency `idna` wheel; the approved private index already
  serves the patched version.
- Keep Ruby `jwt` #142 as DEFERRED with the existing backlog and Trivy policy
  evidence.
- Use current-head CI as the heavy signal under the machine-heavy exception
  after local narrow gates pass.

## Pre-merge Checklist

- [x] All seven Python alert surfaces pin `idna==3.15`.
- [x] No repo-managed Python requirement profile pins `idna==3.11`.
- [x] No `idna` emergency wheel entry was added.
- [x] Bundler resolver evidence still records Fastlane's `jwt < 3` blocker.
- [x] Fixed mapping and PR body both classify #145-#151 as FIXED and #142 as
      DEFERRED.
- [ ] CodeRabbit, Sourcery, Cubic, review threads, and strict governance gates
      have no unresolved actionables before merge-readiness.

## Decision

Proceed with changes.
