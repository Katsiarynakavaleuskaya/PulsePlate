# PR #1621 — Fixed in Commit Mapping (SoT)

> Canonical review artifact for PR #1621
> `docs(release): add App Store release notes template and claim policy`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1621#discussion_r3176403877 -> ea360a796
  Disposition: FIXED
  Evidence: `docs/release/APPSTORE_RELEASE_NOTES_TEMPLATE.md:161` — moved `pulseplate-allow:blocker-example` marker above table, removed inline markers from table rows (MD055/MD056 fix)

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1621#pullrequestreview-4214752979
  Disposition: FIXED (2 items)
  Evidence:
  - Sourcery comment #1 (healthkit/nutrition independence): `docs/release/APPSTORE_RELEASE_NOTES_TEMPLATE.md:305` and `:321` — added explicit release-enablement vs screenshot-readiness independence notes with SoT references
  - Sourcery comment #2 (line number drift): `docs/release/APPSTORE_RELEASE_NOTES_TEMPLATE.md:345` — added drift reminder blockquote to Reviewer Notes Dependency Matrix
  Commit: ea360a796

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1621#discussion_r3176405959
  Disposition: FIXED
  Evidence: `docs/release/APPSTORE_RELEASE_NOTES_TEMPLATE.md:100` — added exception clause to classification rule #1 for screenshot-scope-only blockers where the underlying capability is independently release-enabled
  Commit: e831bba61
