from signed_links import sign, verify


def test_hmac_sign_verify_ok() -> None:
    secret = "test-secret"  # nosec B105
    path = "/api/v1/plan/week/export.csv"
    exp = 9_999_999_999
    sig = sign(secret, path, exp)
    assert verify(secret, path, exp, sig, now_ts=0)


def test_hmac_verify_expired() -> None:
    secret = "x"  # nosec B105
    path = "/api/x"
    exp = 100
    sig = sign(secret, path, exp)
    assert not verify(secret, path, exp, sig, now_ts=exp + 1)


def test_hmac_verify_wrong_signature() -> None:
    secret = "y"  # nosec B105
    path = "/api/y"
    exp = 200
    # Test that an invalid signature fails verification
    assert not verify(secret, path, exp, "invalid", now_ts=0)


def test_hmac_verify_type_error_handled() -> None:
    secret = "secret"  # nosec B105
    path = "/api/z"
    exp = 300
    assert not verify(secret, path, exp, None)  # type: ignore[arg-type]
