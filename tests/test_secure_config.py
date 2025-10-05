"""
Tests for secure_config module - encryption/decryption of API keys
"""

import base64
import os
from pathlib import Path
from unittest.mock import patch

import pytest

import secure_config
from secure_config import (
    InvalidToken,
    decrypt_value,
    encrypt_value,
    get_api_key_from_env,
    get_encryption_key,
    get_or_create_encryption_key,
)


@pytest.fixture
def fake_crypto(monkeypatch):
    """Provide a fake Fernet implementation when cryptography is unavailable."""

    class FakeFernet:
        _RAW_KEY: bytes = b"01234567890123456789012345678901"
        _KEY: bytes = base64.urlsafe_b64encode(_RAW_KEY)

        def __init__(self, key: bytes):
            if key != self._KEY:
                raise InvalidToken("invalid key")
            self._key = key

        @staticmethod
        def generate_key() -> bytes:
            return FakeFernet._KEY

        def encrypt(self, data: bytes) -> bytes:
            cipher = data[::-1]
            return base64.urlsafe_b64encode(cipher)

        def decrypt(self, token: bytes) -> bytes:
            try:
                decoded = base64.urlsafe_b64decode(token)
            except Exception as exc:  # pragma: no cover - defensive
                raise InvalidToken(str(exc)) from exc
            return decoded[::-1]

    monkeypatch.setattr(secure_config, "ENCRYPTION_AVAILABLE", True)
    monkeypatch.setattr(secure_config, "Fernet", FakeFernet, raising=False)
    return FakeFernet


class TestSecureConfig:
    """Test secure configuration encryption/decryption"""

    def test_decrypt_plain_text_value(self):
        """Test decrypting a plain text value returns it unchanged"""
        plain_value = "sk-test12345678901234567890"
        result = decrypt_value(plain_value)
        assert result == plain_value

    def test_decrypt_empty_value(self):
        """Test decrypting empty value"""
        result = decrypt_value("")
        assert result == ""

    def test_decrypt_none_value(self):
        """Test decrypting None returns empty string"""
        # decrypt_value handles None gracefully (returns it)
        result = decrypt_value(None)
        assert result is None or result == ""

    def test_decrypt_without_cryptography(self):
        """Test decrypt when cryptography not available"""
        with patch("secure_config.ENCRYPTION_AVAILABLE", False):
            encrypted_value = "encrypted:gAAAABxxxxxxx"
            result = decrypt_value(encrypted_value)
            # Should return unchanged when crypto not available
            assert result == encrypted_value

    def test_encrypt_decrypt_roundtrip(self, tmp_path, fake_crypto):
        """Test full encryption/decryption cycle"""
        key_file = tmp_path / ".cursor" / ".key"
        key_file.parent.mkdir(parents=True, exist_ok=True)
        test_key = fake_crypto.generate_key()
        key_file.write_bytes(test_key)

        with patch("secure_config.Path.home", return_value=tmp_path):
            original = "sk-test12345678901234567890"
            fernet = fake_crypto(test_key)
            encrypted = f"encrypted:{fernet.encrypt(original.encode()).decode()}"

            decrypted = decrypt_value(encrypted)
            assert decrypted == original

    def test_get_encryption_key_missing(self, tmp_path):
        """Test that get_encryption_key returns None when key doesn't exist"""
        with patch("secure_config.Path.home", return_value=tmp_path):
            key = get_encryption_key()
            assert key is None

    def test_get_encryption_key_reuses_existing(self, tmp_path):
        """Test that existing encryption key is reused"""
        key_file = tmp_path / ".cursor" / ".key"
        key_file.parent.mkdir(parents=True, exist_ok=True)

        test_key = b"test_encryption_key_12345678901234567890"
        key_file.write_bytes(test_key)

        with patch("secure_config.Path.home", return_value=tmp_path):
            key = get_encryption_key()
            assert key == test_key

    def test_get_api_key_from_env_plain(self):
        """Test getting plain text API key from environment"""
        with patch.dict(os.environ, {"TEST_KEY": "sk-plain12345678901234567890"}):
            result = get_api_key_from_env("TEST_KEY")
            assert result == "sk-plain12345678901234567890"

    def test_get_api_key_from_env_not_set(self):
        """Test getting API key when env var not set"""
        result = get_api_key_from_env("NONEXISTENT_KEY_12345")
        assert result is None

    def test_get_api_key_from_env_encrypted(self, tmp_path, fake_crypto):
        """Test getting encrypted API key from environment"""
        key_file = tmp_path / ".cursor" / ".key"
        key_file.parent.mkdir(parents=True, exist_ok=True)
        test_key = fake_crypto.generate_key()
        key_file.write_bytes(test_key)

        original = "sk-test12345678901234567890"
        fernet = fake_crypto(test_key)
        encrypted = f"encrypted:{fernet.encrypt(original.encode()).decode()}"

        with patch("secure_config.Path.home", return_value=tmp_path):
            with patch.dict(os.environ, {"TEST_KEY": encrypted}):
                result = get_api_key_from_env("TEST_KEY")
                assert result == original

    def test_decrypt_with_missing_key_file(self, tmp_path, fake_crypto):
        """Test decrypt when key file is missing"""
        encrypted_value = "encrypted:gAAAABxxxxxxx"

        with patch("secure_config.Path.home", return_value=tmp_path):
            # Key file doesn't exist
            result = decrypt_value(encrypted_value)
            # Should return unchanged when key missing
            assert result == encrypted_value

    def test_decrypt_with_invalid_encrypted_data(self, tmp_path, fake_crypto):
        """Test decrypt with corrupted encrypted data"""
        key_file = tmp_path / ".cursor" / ".key"
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_bytes(fake_crypto.generate_key())

        invalid_encrypted = "encrypted:INVALID_DATA_HERE"

        with patch("secure_config.Path.home", return_value=tmp_path):
            result = decrypt_value(invalid_encrypted)
            assert result == invalid_encrypted

    def test_get_or_create_encryption_key_creates_new(self, tmp_path, fake_crypto):
        """Test that get_or_create_encryption_key creates new key if none exists"""
        with patch("secure_config.Path.home", return_value=tmp_path):
            key = get_or_create_encryption_key()

            assert key is not None
            assert isinstance(key, bytes)
            key_file = tmp_path / ".cursor" / ".key"
            assert key_file.exists()

            fernet = secure_config.Fernet(key)
            test_message = b"test"
            encrypted = fernet.encrypt(test_message)
            decrypted = fernet.decrypt(encrypted)
            assert decrypted == test_message

    def test_get_or_create_encryption_key_reuses_existing(self, tmp_path, fake_crypto):
        """Test that get_or_create_encryption_key reuses existing key"""
        key_file = tmp_path / ".cursor" / ".key"
        key_file.parent.mkdir(parents=True, exist_ok=True)
        test_key = fake_crypto.generate_key()
        key_file.write_bytes(test_key)

        with patch("secure_config.Path.home", return_value=tmp_path):
            key = get_or_create_encryption_key()

        assert key == test_key

    def test_get_or_create_encryption_key_existing_read_error(self, tmp_path, fake_crypto):
        """Read errors on existing key should raise OSError (RU/EN)."""
        key_file = tmp_path / ".cursor" / ".key"
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_bytes(fake_crypto.generate_key())

        with (
            patch("secure_config.Path.home", return_value=tmp_path),
            patch("secure_config.open", side_effect=OSError("io error")),
        ):
            with pytest.raises(OSError, match="Failed to read encryption key file"):
                get_or_create_encryption_key()

    def test_get_encryption_key_returns_none_for_empty_file(self, tmp_path):
        """Empty key files should be treated as missing (RU/EN)."""
        key_file = tmp_path / ".cursor" / ".key"
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_bytes(b"")

        with patch("secure_config.Path.home", return_value=tmp_path):
            assert get_encryption_key() is None

    def test_get_or_create_encryption_key_replace_failure_cleans_temp(self, tmp_path, fake_crypto):
        """Atomic replace failure removes temp file (RU/EN)."""
        temp_file = tmp_path / ".cursor" / ".key.tmp"

        with (
            patch("secure_config.Path.home", return_value=tmp_path),
            patch("secure_config.Fernet.generate_key", return_value=fake_crypto.generate_key()),
            patch("secure_config.os.replace", side_effect=OSError("replace failed")),
        ):
            with pytest.raises(OSError, match="Failed to write encryption key"):
                get_or_create_encryption_key()

        assert not temp_file.exists()

    def test_encrypt_value(self, tmp_path, fake_crypto):
        """Test encrypting a value"""
        with patch("secure_config.Path.home", return_value=tmp_path):
            original = "sk-test12345678901234567890"
            encrypted = encrypt_value(original)

        assert encrypted.startswith("encrypted:")

        with patch("secure_config.Path.home", return_value=tmp_path):
            assert decrypt_value(encrypted) == original

    def test_encrypt_value_without_cryptography(self):
        """Test encrypt_value raises RuntimeError when cryptography not available"""
        with patch("secure_config.ENCRYPTION_AVAILABLE", False):
            original = "sk-test12345678901234567890"
            # Should raise RuntimeError when crypto not available
            with pytest.raises(RuntimeError, match="cryptography library not installed"):
                encrypt_value(original)

    def test_encrypt_decrypt_roundtrip_with_moved_functions(self, tmp_path):
        """Test that encrypt/decrypt work correctly after being moved to secure_config"""
        try:
            from cryptography.fernet import Fernet

            with patch("secure_config.Path.home", return_value=tmp_path):
                original = "sk-test12345678901234567890"

                # Encrypt
                encrypted = encrypt_value(original)
                assert encrypted.startswith("encrypted:")
                assert encrypted != original

                # Decrypt
                decrypted = decrypt_value(encrypted)
                assert decrypted == original

                # Verify key was created
                key_file = tmp_path / ".cursor" / ".key"
                assert key_file.exists()

        except ImportError:
            pytest.skip("cryptography not installed")

    def test_get_encryption_key_read_error(self, tmp_path, caplog):
        """Test read errors when loading existing key are handled gracefully."""
        key_file = tmp_path / ".cursor" / ".key"
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_bytes(b"dummy-key")

        with patch("secure_config.Path.home", return_value=tmp_path), caplog.at_level("ERROR"):
            with patch("secure_config.open", side_effect=OSError("boom")):
                key = get_encryption_key()

        assert key is None
        assert "Failed to read encryption key" in caplog.text

    def test_get_encryption_key_permission_error(self, tmp_path, caplog):
        """PermissionError при чтении ключа обрабатывается и возвращает None (RU/EN)."""
        key_file = tmp_path / ".cursor" / ".key"
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_bytes(b"dummy-key")

        with patch("secure_config.Path.home", return_value=tmp_path), caplog.at_level("ERROR"):
            with patch("secure_config.open", side_effect=PermissionError("denied")):
                key = get_encryption_key()

        assert key is None
        assert "Failed to read encryption key" in caplog.text

    def test_get_encryption_key_directory_error(self, tmp_path, caplog):
        """IsADirectoryError обрабатывается как OSError и возвращает None (RU/EN)."""
        key_file = tmp_path / ".cursor" / ".key"
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_bytes(b"dummy-key")

        with patch("secure_config.Path.home", return_value=tmp_path), caplog.at_level("ERROR"):
            with patch("secure_config.open", side_effect=IsADirectoryError("is dir")):
                key = get_encryption_key()

        assert key is None
        assert "Failed to read encryption key" in caplog.text

    def test_decrypt_value_exception_branch_returns_encrypted(self, tmp_path, fake_crypto):
        """When Fernet.decrypt raises, decrypt_value should return the original encrypted string."""
        # Prepare valid key file
        key_file = tmp_path / ".cursor" / ".key"
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_bytes(fake_crypto.generate_key())

        original = "sk-exception-path-1234567890"
        with patch("secure_config.Path.home", return_value=tmp_path):
            encrypted = encrypt_value(original)

        # Patch Fernet to raise ValueError on decrypt to hit exception branch
        class RaisingFernet:
            def __init__(self, key: bytes):  # noqa: D401 - simple init
                self._key = key

            def decrypt(self, token: bytes) -> bytes:  # noqa: D401 - simple stub
                raise ValueError("bad token")

        with patch("secure_config.Fernet", RaisingFernet):
            with patch("secure_config.Path.home", return_value=tmp_path):
                result = decrypt_value(encrypted)

        assert result == encrypted  # unchanged on decrypt failure

    def test_get_or_create_encryption_key_without_crypto(self):
        """Test that get_or_create_encryption_key raises when crypto unavailable."""
        with patch("secure_config.ENCRYPTION_AVAILABLE", False):
            with pytest.raises(ImportError, match="cryptography package is required"):
                get_or_create_encryption_key()

    def test_get_or_create_encryption_key_mkdir_failure(self, tmp_path, fake_crypto):
        """Test directory creation failure surfaces as OSError."""
        from secure_config import ENCRYPTION_AVAILABLE  # local import to capture runtime value

        if not ENCRYPTION_AVAILABLE:
            pytest.skip("cryptography not installed")

        with (
            patch("secure_config.Path.home", return_value=tmp_path),
            patch("secure_config.Fernet.generate_key", return_value=b"forced-key"),
        ):
            with patch("pathlib.Path.mkdir", side_effect=OSError("mkdir failed")):
                with pytest.raises(OSError, match="Failed to create directory"):
                    get_or_create_encryption_key()

    def test_get_or_create_encryption_key_replace_failure(self, tmp_path, fake_crypto):
        """Test atomic replace failure cleans up temp file and raises."""
        temp_file = tmp_path / ".cursor" / ".key.tmp"

        from secure_config import ENCRYPTION_AVAILABLE

        if not ENCRYPTION_AVAILABLE:
            pytest.skip("cryptography not installed")

        with (
            patch("secure_config.Path.home", return_value=tmp_path),
            patch("secure_config.Fernet.generate_key", return_value=b"forced-key"),
        ):
            with patch("secure_config.os.replace", side_effect=OSError("replace failed")):
                with pytest.raises(OSError, match="Failed to write encryption key"):
                    get_or_create_encryption_key()

        assert not temp_file.exists(), "Temp key file should be removed after failure"

    def test_get_or_create_encryption_key_replace_failure_best_effort_cleanup(
        self, tmp_path, fake_crypto
    ):
        """Temp unlink failures are swallowed but original error surfaces."""

        from secure_config import ENCRYPTION_AVAILABLE

        if not ENCRYPTION_AVAILABLE:
            pytest.skip("cryptography not installed")

        # Ensure we're operating in the temp directory used by secure_config
        temp_dir = tmp_path / ".cursor"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_file = temp_dir / ".key.tmp"

        unlink_called = False

        def _tracking_unlink(self):
            nonlocal unlink_called
            unlink_called = True
            raise RuntimeError("unlink boom")

        with (
            patch("secure_config.Path.home", return_value=tmp_path),
            patch("secure_config.Fernet.generate_key", return_value=b"forced-key"),
            patch("secure_config.os.replace", side_effect=OSError("replace failed")),
            patch.object(secure_config.Path, "unlink", _tracking_unlink),
        ):
            with pytest.raises(OSError, match="Failed to write encryption key"):
                get_or_create_encryption_key()

        assert unlink_called
        if temp_file.exists():
            temp_file.unlink()

    def test_get_or_create_encryption_key_chmod_warning(self, tmp_path, caplog, fake_crypto):
        """Test chmod failure logs warning but still returns key."""
        from secure_config import ENCRYPTION_AVAILABLE

        if not ENCRYPTION_AVAILABLE:
            pytest.skip("cryptography not installed")

        with (
            patch("secure_config.Path.home", return_value=tmp_path),
            patch("secure_config.Fernet.generate_key", return_value=b"forced-key"),
            caplog.at_level("WARNING"),
        ):
            with patch("secure_config.os.chmod", side_effect=OSError("chmod failed")):
                key = get_or_create_encryption_key()

        assert key is not None
        assert "Failed to set secure permissions" in caplog.text

    def test_get_or_create_encryption_key_windows_permission_warning(
        self, tmp_path, fake_crypto, caplog, monkeypatch
    ):
        """Windows chmod limitation emits warning when os.name == 'nt'."""

        from secure_config import ENCRYPTION_AVAILABLE

        if not ENCRYPTION_AVAILABLE:
            pytest.skip("cryptography not installed")

        with (
            patch("secure_config.Path.home", return_value=tmp_path),
            patch("secure_config.Fernet.generate_key", return_value=b"forced-key"),
            caplog.at_level("WARNING"),
        ):
            monkeypatch.setattr(secure_config.os, "name", "nt", raising=False)
            key = get_or_create_encryption_key()

        assert key is not None
        assert "Windows" in caplog.text

    def test_get_or_create_encryption_key_replace_failure_no_temp_cleanup(
        self, tmp_path, fake_crypto
    ):
        """If the temp file never materializes, cleanup branch is skipped."""

        from secure_config import ENCRYPTION_AVAILABLE

        if not ENCRYPTION_AVAILABLE:
            pytest.skip("cryptography not installed")

        original_exists = secure_config.Path.exists

        def fake_exists(path_obj):
            return False if path_obj.name == ".key.tmp" else original_exists(path_obj)

        with (
            patch("secure_config.Path.home", return_value=tmp_path),
            patch("secure_config.Fernet.generate_key", return_value=b"forced-key"),
            patch.object(secure_config.Path, "exists", fake_exists),
            patch("secure_config.os.replace", side_effect=OSError("replace failed")),
        ):
            with pytest.raises(OSError, match="Failed to write encryption key"):
                get_or_create_encryption_key()

    def test_encrypt_value_logs_and_raises_on_failure(self, tmp_path, caplog, fake_crypto):
        """Test encrypt_value logs error and raises when Fernet fails."""

        class FailingFernet:
            generate_key = staticmethod(fake_crypto.generate_key)

            def __init__(self, key):
                self._key = key

            def encrypt(self, data: bytes):
                raise ValueError("encrypt failed")

        with patch("secure_config.Fernet", FailingFernet), caplog.at_level("ERROR"):
            with patch("secure_config.Path.home", return_value=tmp_path):
                with pytest.raises(RuntimeError, match="Failed to encrypt value"):
                    encrypt_value("sk-test12345678901234567890")

        assert "Encryption failed" in caplog.text

    def test_decrypt_value_success(self, tmp_path, fake_crypto):
        """Test decrypt_value round-trip covers encrypted path."""
        key_file = tmp_path / ".cursor" / ".key"
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_bytes(fake_crypto.generate_key())

        with patch("secure_config.Path.home", return_value=tmp_path):
            encrypted = encrypt_value("sk-secret-value-12345")
            assert decrypt_value(encrypted) == "sk-secret-value-12345"
