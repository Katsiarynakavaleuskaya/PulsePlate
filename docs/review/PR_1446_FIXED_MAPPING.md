# PR 1446 - Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1446#pullrequestreview-4131508244
Disposition: NOT-A-BUG
Evidence: `app/security/web_session.py:120-132`
Reason: PBKDF2 uses the secret HMAC key as the password and `_SESSION_ENCRYPTION_CONTEXT` as the salt label; this matches the documented Fernet key derivation contract and is not an accidental inversion.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1446#pullrequestreview-4131533282 -> 3b30ba25b82557aefe97781665bda0f328da7f28
Disposition: FIXED
Evidence: `app/security/web_session.py:254-277`
Reason: cubic review summary tracked the legacy plaintext `api_key` read path; implementation and tests landed in `3b30ba25b82557aefe97781665bda0f328da7f28`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1446#discussion_r3102758886 -> 3b30ba25b82557aefe97781665bda0f328da7f28
Disposition: FIXED
Evidence: `app/security/web_session.py:254-277`
Reason: Inline cubic thread matches the legacy `api_key` compatibility path addressed in `3b30ba25b82557aefe97781665bda0f328da7f28`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1446#discussion_r3109659002 -> 3f0195bae6a45b0ec4e23098befa8714504c1adf
Disposition: FIXED
Evidence: `app/security/web_session.py:236-244`
Reason: CodeRabbit asked for operator-visible signal when crypto signing cannot run; warning log before `return None` is in `3f0195bae6a45b0ec4e23098befa8714504c1adf`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1446#discussion_r3109659008
Disposition: NOT-A-BUG
Evidence: `requirements.txt:35`; `constraints.txt:55`; `requirements-dev.txt:44`; `requirements-lock.txt:76`
Reason: Repository requirement surfaces already pin or floor `cryptography` at `46.0.7`; the bot’s stale `46.0.5` reference does not match the current tree.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1446#pullrequestreview-4138856164 -> 3f0195bae6a45b0ec4e23098befa8714504c1adf
Disposition: FIXED
Evidence: `app/security/web_session.py:236-244`; `tests/test_web_session_security.py:303-316`
Reason: CodeRabbit batch review included the signing misconfiguration signal; warning logging plus regression test close the actionable thread in `3f0195bae6a45b0ec4e23098befa8714504c1adf`. Remaining test-order notes reflect intentional fail-closed ordering (invalid `enc_api_key` rejects before tier checks).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1446#pullrequestreview-4138894330 -> 3f0195bae6a45b0ec4e23098befa8714504c1adf
Disposition: FIXED
Evidence: `app/security/web_session.py:236-244`
Reason: cubic P2 asked to log before swallowing `RuntimeError` during signature verification; addressed in `3f0195bae6a45b0ec4e23098befa8714504c1adf`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1446#discussion_r3109695186 -> 3f0195bae6a45b0ec4e23098befa8714504c1adf
Disposition: FIXED
Evidence: `app/security/web_session.py:236-244`; `tests/test_web_session_security.py:303-316`
Reason: Inline cubic comment matches the same signing-path logging fix in `3f0195bae6a45b0ec4e23098befa8714504c1adf`.

## Merge Readiness
- [x] Scope tied to PR objective
- [x] Docs/runtime changes applied
- [x] Verification completed
- [ ] Required GitHub checks PASS with no pending required jobs
- [ ] CodeRabbit PASS / no-actionables
- [ ] Sourcery PASS / no-actionables
- [ ] Cubic PASS / no-actionables
- [ ] No unresolved review threads or actionable bot comments remain
- [ ] Review wait-window completed
