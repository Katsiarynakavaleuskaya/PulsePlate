import os

import pytest

from core import fingerprint_security as fingerprint


def test_get_fingerprint_salt_returns_env_value(monkeypatch):
    monkeypatch.setenv("CLIENT_FINGERPRINT_SALT", "fixed-salt")
    monkeypatch.delenv("APP_ENV", raising=False)
    assert fingerprint.get_fingerprint_salt() == "fixed-salt"


def test_get_fingerprint_salt_allows_production_during_tests(monkeypatch):
    monkeypatch.delenv("CLIENT_FINGERPRINT_SALT", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "fingerprint-test")
    assert fingerprint.get_fingerprint_salt() == ""


def test_get_fingerprint_salt_errors_in_real_production(monkeypatch):
    monkeypatch.delenv("CLIENT_FINGERPRINT_SALT", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    with pytest.raises(RuntimeError):
        fingerprint.get_fingerprint_salt()


def test_get_fingerprint_salt_decrypts_encrypted_values(monkeypatch):
    decrypted_value = "decrypted-salt"
    monkeypatch.setenv("CLIENT_FINGERPRINT_SALT", "encrypted:abcdef")
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setattr(fingerprint, "decrypt_value", lambda value: decrypted_value)
    assert fingerprint.get_fingerprint_salt() == decrypted_value


def test_compute_fingerprint_is_deterministic(monkeypatch):
    monkeypatch.setenv("CLIENT_FINGERPRINT_SALT", "abcd")
    first = fingerprint.compute_fingerprint("203.0.113.9")
    second = fingerprint.compute_fingerprint("203.0.113.9")
    assert first == second
    assert len(first) == 12
