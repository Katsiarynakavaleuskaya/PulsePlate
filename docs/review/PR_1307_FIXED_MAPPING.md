# PR 1307 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping
Disposition: FIXED
Commit: 4ca59bee7194921b70bf8a442cf4364c18d71578
Evidence: core/compliance/transparency.py:97; docs/compliance/AI_TRANSPARENCY_AND_PROFILING_NOTICE.md:63; docs/legal/Privacy.md:120
Reason: Sourcery asked for the canonical "substance use disorder" phrasing. The blocked regulated-lane example now matches that wording across runtime and synced disclosure docs.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1307#pullrequestreview-4053710418 -> 4ca59bee7194921b70bf8a442cf4364c18d71578
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1307#discussion_r3030876254 -> 4ca59bee7194921b70bf8a442cf4364c18d71578

Disposition: FIXED
Commit: 9b4f01e273172083d4b12b874327d6ef9b650ef8
Evidence: core/compliance/privacy.py:236; tests/test_compliance_control_plane.py:64
Reason: The legacy `llm_processing.endpoints` field remains for backward compatibility, but it now derives from the canonical `ai_generated_wellness_analysis` disclosure so `/api/v1/pro/fitchef/explain` cannot drift out of sync again. The matrix/notice policy date and version stay unchanged because this lane hardens the existing contract rather than publishing a new legal-policy revision.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1307#pullrequestreview-4053717254 -> 9b4f01e273172083d4b12b874327d6ef9b650ef8

## Merge Readiness
- [ ] All required checks pass
- [x] No unresolved review threads (re-checked on current head)
- [x] No actionable bot comments remain unmapped
- [ ] Mandatory wait-window completed
- [x] Pre-commit green
- [x] `make verify` green
- [x] Mandatory post-open bug-hunter pass completed
Notes: PR `#1307` must remain a narrow EU-first compliance control-plane follow-through. Keep scope bounded to runtime/doc sync and deterministic drift detection for current wellness AI surfaces only.
