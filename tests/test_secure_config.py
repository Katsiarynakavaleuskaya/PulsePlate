"""
Tests for secure_config module - encryption/decryption of API keys
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from secure_config import (
    decrypt_value,
    encrypt_value,
    get_api_key_from_env,
    get_encryption_key,
    get_or_create_encryption_key,
)


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

    def test_encrypt_decrypt_roundtrip(self, tmp_path):
        """Test full encryption/decryption cycle"""
        try:
            from cryptography.fernet import Fernet

            # Set up temp key file
            key_file = tmp_path / ".cursor" / ".key"
            key_file.parent.mkdir(parents=True, exist_ok=True)
            test_key = Fernet.generate_key()
            key_file.write_bytes(test_key)

            with patch("secure_config.Path.home", return_value=tmp_path):
                # Encrypt a value manually
                original = "sk-test12345678901234567890"
                fernet = Fernet(test_key)
                encrypted = f"encrypted:{fernet.encrypt(original.encode()).decode()}"

                # Decrypt it back
                decrypted = decrypt_value(encrypted)
                assert decrypted == original

        except ImportError:
            pytest.skip("cryptography not installed")

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

    def test_get_api_key_from_env_encrypted(self, tmp_path):
        """Test getting encrypted API key from environment"""
        # This test requires cryptography to be installed
        try:
            from cryptography.fernet import Fernet

            # Create a test key
            key_file = tmp_path / ".cursor" / ".key"
            key_file.parent.mkdir(parents=True, exist_ok=True)
            test_key = Fernet.generate_key()
            key_file.write_bytes(test_key)

            # Encrypt a value
            original = "sk-test12345678901234567890"
            fernet = Fernet(test_key)
            encrypted = f"encrypted:{fernet.encrypt(original.encode()).decode()}"

            with patch("secure_config.Path.home", return_value=tmp_path):
                with patch.dict(os.environ, {"TEST_KEY": encrypted}):
                    result = get_api_key_from_env("TEST_KEY")
                    assert result == original

        except ImportError:
            pytest.skip("cryptography not installed")

    def test_decrypt_with_missing_key_file(self, tmp_path):
        """Test decrypt when key file is missing"""
        encrypted_value = "encrypted:gAAAABxxxxxxx"

        with patch("secure_config.Path.home", return_value=tmp_path):
            # Key file doesn't exist
            result = decrypt_value(encrypted_value)
            # Should return unchanged when key missing
            assert result == encrypted_value

    def test_decrypt_with_invalid_encrypted_data(self, tmp_path):
        """Test decrypt with corrupted encrypted data"""
        try:
            from cryptography.fernet import Fernet

            # Create valid key
            key_file = tmp_path / ".cursor" / ".key"
            key_file.parent.mkdir(parents=True, exist_ok=True)
            test_key = Fernet.generate_key()
            key_file.write_bytes(test_key)

            # Invalid encrypted data
            invalid_encrypted = "encrypted:INVALID_DATA_HERE"

            with patch("secure_config.Path.home", return_value=tmp_path):
                result = decrypt_value(invalid_encrypted)
                # Should return unchanged when decryption fails
                assert result == invalid_encrypted

        except ImportError:
            pytest.skip("cryptography not installed")

    def test_get_or_create_encryption_key_creates_new(self, tmp_path):
        """Test that get_or_create_encryption_key creates new key if none exists"""
        try:
            from cryptography.fernet import Fernet

            with patch("secure_config.Path.home", return_value=tmp_path):
                key = get_or_create_encryption_key()

                # Verify key was created
                assert key is not None
                assert isinstance(key, bytes)
                assert len(key) > 0

                # Verify key file exists
                key_file = tmp_path / ".cursor" / ".key"
                assert key_file.exists()

                # Verify key is valid Fernet key
                fernet = Fernet(key)
                test_message = b"test"
                encrypted = fernet.encrypt(test_message)
                decrypted = fernet.decrypt(encrypted)
                assert decrypted == test_message

        except ImportError:
            pytest.skip("cryptography not installed")

    def test_get_or_create_encryption_key_reuses_existing(self, tmp_path):
        """Test that get_or_create_encryption_key reuses existing key"""
        try:
            from cryptography.fernet import Fernet

            # Create a key file first
            key_file = tmp_path / ".cursor" / ".key"
            key_file.parent.mkdir(parents=True, exist_ok=True)
            test_key = Fernet.generate_key()
            key_file.write_bytes(test_key)

            with patch("secure_config.Path.home", return_value=tmp_path):
                key = get_or_create_encryption_key()

                # Should return same key
                assert key == test_key

        except ImportError:
            pytest.skip("cryptography not installed")

    def test_encrypt_value(self, tmp_path):
        """Test encrypting a value"""
        try:
            from cryptography.fernet import Fernet

            with patch("secure_config.Path.home", return_value=tmp_path):
                original = "sk-test12345678901234567890"
                encrypted = encrypt_value(original)

                # Should be prefixed with "encrypted:"
                assert encrypted.startswith("encrypted:")

                # Should be able to decrypt back
                decrypted = decrypt_value(encrypted)
                assert decrypted == original

        except ImportError:
            pytest.skip("cryptography not installed")

    def test_encrypt_value_without_cryptography(self):
        """Test encrypt_value falls back to plain text when cryptography not available"""
        with patch("secure_config.ENCRYPTION_AVAILABLE", False):
            original = "sk-test12345678901234567890"
            result = encrypt_value(original)
            # Should return unchanged when crypto not available
            assert result == original

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
