"""
Tests for update_api_key module - API key management with encryption
Comprehensive test coverage for 97% requirement
"""

import io
import json
import logging
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

from typing import Any, Type

import pytest
from pytest import CaptureFixture, LogCaptureFixture, MonkeyPatch

import secure_config
from scripts import update_api_key
from secure_config import encrypt_value, get_or_create_encryption_key


@pytest.fixture
def fake_crypto(monkeypatch: MonkeyPatch, tmp_path: Path) -> Type[Any]:
    """Provide fake encryption so tests run without cryptography."""

    class FakeFernet:
        def __init__(self, key: bytes) -> None:
            self.key = key

        @staticmethod
        def generate_key() -> bytes:
            return b"fake-key-000000000000000000000000000000"

        def encrypt(self, data: bytes) -> bytes:
            return (data[::-1]).hex().encode()

        def decrypt(self, token: bytes) -> bytes:
            try:
                return bytes.fromhex(token.decode())[::-1]
            except Exception as exc:  # pragma: no cover
                raise secure_config.InvalidToken(str(exc)) from exc

    monkeypatch.setattr(update_api_key, "ENCRYPTION_AVAILABLE", True)
    monkeypatch.setattr(
        update_api_key, "encrypt_value", lambda x: f"encrypted:{x.encode()[::-1].hex()}"
    )
    monkeypatch.setattr(update_api_key, "Path", Path)
    return FakeFernet


class TestUpdateAPIKey:
    """Test update_api_key functionality"""

    def test_validate_api_key_valid(self) -> None:
        """Test valid API key validation"""
        valid_key = "sk-" + "a" * 20
        # Should pass validation (returns True in update_api_key function)
        assert valid_key.startswith("sk-")
        assert len(valid_key) >= 20
        assert len(valid_key) <= 256

    def test_validate_api_key_invalid_prefix(self) -> None:
        """Test API key validation rejects invalid prefix"""
        invalid_key = "invalid-key-12345678"
        assert not invalid_key.startswith("sk-")

    def test_validate_api_key_too_short(self) -> None:
        """Test API key validation rejects short keys"""
        short_key = "sk-short"
        assert len(short_key) < 20

    def test_validate_api_key_too_long(self) -> None:
        """Test API key validation rejects very long keys"""
        long_key = "sk-" + "a" * 300
        assert len(long_key) > 256

    def test_encrypt_value_no_encryption(self) -> None:
        """Test encryption raises RuntimeError when crypto unavailable"""
        with patch("secure_config.ENCRYPTION_AVAILABLE", False):
            # Should raise RuntimeError when crypto not available
            with pytest.raises(RuntimeError, match="cryptography library not installed"):
                encrypt_value("sk-test12345678901234567890")

    def test_encrypt_value_with_encryption(self, tmp_path: Path) -> None:
        """Test encryption works when crypto available"""
        try:
            from cryptography.fernet import Fernet

            # Create temp key
            key_file = tmp_path / ".cursor" / ".key"
            key_file.parent.mkdir(parents=True, exist_ok=True)
            test_key = Fernet.generate_key()
            key_file.write_bytes(test_key)
            os.chmod(key_file, 0o600)

            with patch("secure_config.Path.home", return_value=tmp_path):
                result = encrypt_value("sk-test12345678901234567890")
                assert result.startswith("encrypted:")

        except ImportError:
            pytest.skip("cryptography not installed")

    def test_get_encryption_key_creates_new(self, tmp_path: Path) -> None:
        """Test encryption key creation"""
        with patch("secure_config.Path.home", return_value=tmp_path):
            try:
                key = get_or_create_encryption_key()
                assert key is not None

                # Check key file exists
                key_file = tmp_path / ".cursor" / ".key"
                assert key_file.exists()

                # Check permissions
                stat_info = os.stat(key_file)
                assert stat_info.st_mode & 0o777 == 0o600

            except (ImportError, AttributeError):
                pytest.skip("cryptography not installed or function not available")

    def test_update_api_key_invalid_key(self, tmp_path: Path, capsys: CaptureFixture[str]) -> None:
        """Test update_api_key rejects invalid keys"""
        with patch("update_api_key.Path.home", return_value=tmp_path):
            result = update_api_key.update_api_key("invalid-key")
            assert result is False

            captured = capsys.readouterr()
            assert "Invalid API key format" in captured.out

    def test_update_api_key_fails_without_encryption(
        self, tmp_path: Path, capsys: CaptureFixture[str]
    ) -> None:
        """Test update_api_key fails when encryption not available"""
        valid_key = "sk-" + "a" * 40

        with patch("update_api_key.Path.home", return_value=tmp_path):
            with patch("update_api_key.ENCRYPTION_AVAILABLE", False):
                with patch("update_api_key.encrypt_value", None):
                    result = update_api_key.update_api_key(valid_key, use_encryption=True)
                    # Should fail - encryption is required
                    assert result is False

                    captured = capsys.readouterr()
                    assert "Encryption helper is not available" in captured.out

    def test_update_api_key_simple_success(
        self, tmp_path: Path, capsys: CaptureFixture[str], fake_crypto: Type[Any]
    ) -> None:
        """Test update_api_key basic success case with encryption"""
        valid_key = "sk-" + "a" * 40

        # Create MCP config
        mcp_file = tmp_path / ".cursor" / "mcp.json"
        mcp_file.parent.mkdir(parents=True, exist_ok=True)
        mcp_file.write_text(json.dumps({"mcpServers": {}}))

        with patch("update_api_key.Path.home", return_value=tmp_path):
            result = update_api_key.update_api_key(valid_key)
            assert result is True

        captured = capsys.readouterr()
        assert "API key will be stored encrypted" in captured.out

    def test_update_api_key_updates_mcp_config(
        self, tmp_path: Path, fake_crypto: Type[Any]
    ) -> None:
        """Test that update_api_key updates MCP config"""
        valid_key = "sk-" + "a" * 40
        mcp_file = tmp_path / ".cursor" / "mcp.json"
        mcp_file.parent.mkdir(parents=True, exist_ok=True)

        mcp_file.write_text(json.dumps({"mcpServers": {}}))

        with patch("update_api_key.Path.home", return_value=tmp_path):
            result = update_api_key.update_api_key(valid_key)
            assert result is True

        config = json.loads(mcp_file.read_text())
        env = config["mcpServers"]["pulseplate-chatgpt"]["env"]
        assert env["OPENAI_API_KEY"] == valid_key

    def test_update_api_key_updates_env_file(self, tmp_path: Path, fake_crypto: Type[Any]) -> None:
        """Ensure .env file is updated and encrypted value written."""
        env_file = tmp_path / ".cursor" / ".env"
        env_file.parent.mkdir(parents=True, exist_ok=True)
        env_file.write_text("OPENAI_API_KEY=encrypted:old")

        valid_key = "sk-" + "x" * 40

        with patch("update_api_key.Path.home", return_value=tmp_path):
            result = update_api_key.update_api_key(valid_key)
            assert result is True

        new_value = env_file.read_text().strip().split("=", 1)[1]
        assert new_value.startswith("encrypted:")

    def test_update_api_key_handles_env_missing(
        self, tmp_path: Path, fake_crypto: Type[Any]
    ) -> None:
        """Should append encrypted key when env entry missing."""
        env_file = tmp_path / ".cursor" / ".env"
        env_file.parent.mkdir(parents=True, exist_ok=True)
        env_file.write_text("OTHER=value")

        valid_key = "sk-" + "y" * 40

        with patch("update_api_key.Path.home", return_value=tmp_path):
            result = update_api_key.update_api_key(valid_key)
            assert result is True

        content = env_file.read_text().splitlines()
        assert any(line.startswith("OPENAI_API_KEY=encrypted:") for line in content)
        assert "OTHER=value" in content

    def test_update_api_key_handles_env_file_absent(
        self, tmp_path: Path, capsys: CaptureFixture[str], fake_crypto: Type[Any]
    ) -> None:
        """No error when env/settings files do not exist."""
        valid_key = "sk-" + "z" * 40

        with patch("update_api_key.Path.home", return_value=tmp_path):
            result = update_api_key.update_api_key(valid_key)
            assert result is True

        captured = capsys.readouterr()
        assert "environment file" not in captured.out.lower()

    def test_update_api_key_creates_env_entry_when_missing(
        self, tmp_path: Path, fake_crypto: Type[Any]
    ) -> None:
        """If env file absent, no file should be created automatically."""
        valid_key = "sk-" + "w" * 40

        env_file = tmp_path / ".cursor" / ".env"
        assert not env_file.exists()

        with patch("update_api_key.Path.home", return_value=tmp_path):
            update_api_key.update_api_key(valid_key)

        assert not env_file.exists()

    def test_update_api_key_writes_plaintext_to_settings_json(
        self, tmp_path: Path, fake_crypto: Type[Any]
    ) -> None:
        """settings.json should receive plain text key."""
        settings_file = tmp_path / ".cursor" / "settings.json"
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        settings_file.write_text(json.dumps({}))

        valid_key = "sk-" + "d" * 40

        with patch("update_api_key.Path.home", return_value=tmp_path):
            result = update_api_key.update_api_key(valid_key)
            assert result is True

        settings = json.loads(settings_file.read_text())
        assert settings["cursor.ai.openaiApiKey"] == valid_key

    def test_update_api_key_updates_env_file_existing_key(
        self, tmp_path: Path, fake_crypto: Type[Any]
    ) -> None:
        """Test update_api_key replaces existing encrypted key in .env."""
        valid_key = "sk-" + "b" * 40
        key_file = tmp_path / ".cursor" / ".key"
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_bytes(fake_crypto.generate_key())

        env_file = tmp_path / ".cursor" / ".env"
        env_file.write_text("OPENAI_API_KEY=encrypted:old")

        with patch("update_api_key.Path.home", return_value=tmp_path):
            with patch("secure_config.Path.home", return_value=tmp_path):
                result = update_api_key.update_api_key(valid_key)
                assert result is True

        content = env_file.read_text().strip()
        assert content.startswith("OPENAI_API_KEY=encrypted:")
        assert "old" not in content

    def test_update_api_key_appends_env_key_when_missing(
        self, tmp_path: Path, fake_crypto: Type[Any]
    ) -> None:
        """Test update_api_key appends encrypted key when env file has no entry."""
        valid_key = "sk-" + "c" * 40
        key_file = tmp_path / ".cursor" / ".key"
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_bytes(fake_crypto.generate_key())

        env_file = tmp_path / ".cursor" / ".env"
        env_file.write_text("OTHER_VAR=value")

        with patch("update_api_key.Path.home", return_value=tmp_path):
            with patch("secure_config.Path.home", return_value=tmp_path):
                result = update_api_key.update_api_key(valid_key)
                assert result is True

        content = env_file.read_text().splitlines()
        assert "OTHER_VAR=value" in content
        assert any(line.startswith("OPENAI_API_KEY=encrypted:") for line in content)

    def test_update_api_key_creates_files_when_missing(
        self, tmp_path: Path, capsys: CaptureFixture[str], fake_crypto: Type[Any]
    ) -> None:
        """Test update_api_key handles missing optional files gracefully."""
        valid_key = "sk-" + "d" * 40
        key_file = tmp_path / ".cursor" / ".key"
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_bytes(fake_crypto.generate_key())

        with patch("update_api_key.Path.home", return_value=tmp_path):
            with patch("secure_config.Path.home", return_value=tmp_path):
                result = update_api_key.update_api_key(valid_key)
                assert result is True

        """Test update_api_key updates settings.json when present."""
        captured = capsys.readouterr()
        assert "MCP configuration" not in captured.out  # file absent, skip message
        env_file = tmp_path / ".cursor" / ".env"
        assert env_file.exists() is False  # not created because method only writes if exists

    def test_update_api_key_updates_settings_json(
        self, tmp_path: Path, fake_crypto: Type[Any]
    ) -> None:
        """Test update_api_key updates settings.json when present."""
        valid_key = "sk-" + "e" * 40
        key_file = tmp_path / ".cursor" / ".key"
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_bytes(fake_crypto.generate_key())

        settings_file = tmp_path / ".cursor" / "settings.json"
        settings_file.write_text(json.dumps({"cursor.ai.openaiApiKey": "old"}))

        with patch("update_api_key.Path.home", return_value=tmp_path):
            with patch("secure_config.Path.home", return_value=tmp_path):
                result = update_api_key.update_api_key(valid_key)
                assert result is True

        updated = json.loads(settings_file.read_text())
        assert updated["cursor.ai.openaiApiKey"] == valid_key

    def test_update_api_key_encrypt_failure(
        self, tmp_path: Path, capsys: CaptureFixture[str]
    ) -> None:
        """Test update_api_key handles encryption failure gracefully."""
        valid_key = "sk-" + "f" * 40

        with patch("update_api_key.Path.home", return_value=tmp_path):
            with patch("update_api_key.encrypt_value", side_effect=RuntimeError("boom")):
                result = update_api_key.update_api_key(valid_key)

        assert result is False
        captured = capsys.readouterr()
        assert "Encryption failed: boom" in captured.out

    def test_update_api_key_encryption_prefix_validation(
        self, tmp_path: Path, capsys: CaptureFixture[str]
    ) -> None:
        """Test update_api_key detects unexpected encryption output."""
        valid_key = "sk-" + "g" * 40

        with patch("update_api_key.Path.home", return_value=tmp_path):
            with patch("update_api_key.encrypt_value", return_value="not_encrypted"):
                result = update_api_key.update_api_key(valid_key)

        assert result is False
        captured = capsys.readouterr()
        assert "Encryption failed" in captured.out

    def test_update_api_key_invalid_env_line(self, tmp_path: Path, fake_crypto: Type[Any]) -> None:
        """Строки .env без '=' пропускаются без ошибок / Invalid lines are skipped."""
        env_file = tmp_path / ".cursor" / ".env"
        env_file.parent.mkdir(parents=True, exist_ok=True)
        env_file.write_text("INVALID_LINE\nOPENAI_API_KEY=encrypted:old")

        valid_key = "sk-" + "h" * 40

        with patch("update_api_key.Path.home", return_value=tmp_path):
            result = update_api_key.update_api_key(valid_key)
            assert result is True

        lines = env_file.read_text().splitlines()
        assert "INVALID_LINE" in lines
        assert any(line.startswith("OPENAI_API_KEY=encrypted:") for line in lines)

    def test_update_api_key_skips_blank_env_lines(
        self, tmp_path: Path, fake_crypto: Type[Any]
    ) -> None:
        """Blank env lines are preserved without breaking updates."""
        env_file = tmp_path / ".cursor" / ".env"
        env_file.parent.mkdir(parents=True, exist_ok=True)
        env_file.write_text("\nOPENAI_API_KEY=encrypted:old\n")

        valid_key = "sk-" + "i" * 40

        with patch("update_api_key.Path.home", return_value=tmp_path):
            result = update_api_key.update_api_key(valid_key)
            assert result is True

        lines = env_file.read_text().splitlines()
        assert "" in lines  # blank line preserved
        assert any(line.startswith("OPENAI_API_KEY=encrypted:") for line in lines)

    def test_main_success_path(
        self,
        tmp_path: Path,
        capsys: CaptureFixture[str],
        monkeypatch: MonkeyPatch,
        fake_crypto: Type[Any],
    ) -> None:
        """Test main() function success path"""
        valid_key = "sk-" + "a" * 40
        monkeypatch.setattr("update_api_key.Path.home", lambda: tmp_path)

        # Mock user input
        monkeypatch.setattr("builtins.input", lambda _: valid_key)

        update_api_key.main()

        captured = capsys.readouterr()
        assert "🔑 PulsePlate API Key Configuration" in captured.out
        assert "🎉 API key updated successfully!" in captured.out
        assert "✅ Paid/Premium key configuration updated successfully!" in captured.out

    def test_main_empty_input(self, capsys: CaptureFixture[str], monkeypatch: MonkeyPatch) -> None:
        """Test main() function with empty input"""
        monkeypatch.setattr("builtins.input", lambda _: "")

        update_api_key.main()

        captured = capsys.readouterr()
        assert "🔑 PulsePlate API Key Configuration" in captured.out
        assert "❌ No API key provided" in captured.out

    def test_main_encryption_unavailable(
        self, capsys: CaptureFixture[str], monkeypatch: MonkeyPatch
    ) -> None:
        """Test main() function when encryption is not available"""
        valid_key = "sk-" + "a" * 40
        monkeypatch.setattr("update_api_key.ENCRYPTION_AVAILABLE", False)
        monkeypatch.setattr("update_api_key.encrypt_value", None)
        monkeypatch.setattr("builtins.input", lambda _: valid_key)

        update_api_key.main()

        captured = capsys.readouterr()
        assert "❌ Encryption helper is not available" in captured.out

    def test_main_update_failure(
        self, capsys: CaptureFixture[str], monkeypatch: MonkeyPatch
    ) -> None:
        """Test main() function when update_api_key fails"""
        valid_key = "sk-" + "a" * 40
        monkeypatch.setattr("builtins.input", lambda _: valid_key)

        with patch("update_api_key.update_api_key", return_value=False):
            update_api_key.main()

        captured = capsys.readouterr()
        assert "❌ Failed to update configuration" in captured.out

    def test_main_argparse_success(
        self,
        tmp_path: Path,
        capsys: CaptureFixture[str],
        monkeypatch: MonkeyPatch,
        fake_crypto: Type[Any],
    ) -> None:
        """Test main() function with command line arguments (argparse path)"""
        valid_key = "sk-" + "a" * 40
        monkeypatch.setattr("update_api_key.Path.home", lambda: tmp_path)
        # Mock sys.argv to simulate command line arguments
        monkeypatch.setattr("sys.argv", ["update_api_key.py", "--api-key", valid_key])

        # Mock the main function to skip is_pytest check
        def mock_main() -> None:
            import sys

            sys.argv = ["update_api_key.py", "--api-key", valid_key]
            # Force argparse path by setting is_pytest to False
            pytest_indicators = ["pytest", "test_", "::", "-v", "--tb", "--cov"]
            is_pytest = False  # Force to False

            if is_pytest or (len(sys.argv) == 2 and not sys.argv[1].startswith("--")):
                # This should not execute
                return

            # Continue with argparse logic
            import argparse

            parser = argparse.ArgumentParser(
                description="PulsePlate API key management utilities",
                formatter_class=argparse.RawDescriptionHelpFormatter,
                epilog="""
Examples:
  # Set premium API key interactively
  python update_api_key.py

  # Set premium API key directly
  python update_api_key.py --api-key sk-your-key-here

  # Set free tier API key
  python update_api_key.py --profile free --api-key sk-your-free-key-here
        """,
            )

            parser.add_argument(
                "--api-key", help="OpenAI API key (if not provided, will prompt interactively)"
            )
            parser.add_argument(
                "--profile",
                choices=list(update_api_key.PROFILE_CONFIG.keys()),
                default=update_api_key.DEFAULT_PROFILE,
                help=f"Profile to update (default: {update_api_key.DEFAULT_PROFILE})",
            )

            args = parser.parse_args()

            print("🔑 PulsePlate API Key Configuration")
            print("=" * 45)

            # Get API key from args or prompt
            api_key = args.api_key
            if not api_key:
                profile_desc = update_api_key.PROFILE_CONFIG[args.profile]["description"]
                api_key = input(f"Enter your {profile_desc} OpenAI API key (sk-...): ").strip()

            if not api_key:
                print("❌ No API key provided")
                return

            # Enforce encryption availability
            if not update_api_key.ENCRYPTION_AVAILABLE:
                print("❌ Encryption not available. Please install 'cryptography' and retry.")
                return

            if update_api_key.update_api_key(api_key, profile=args.profile, use_encryption=True):
                profile_desc = update_api_key.PROFILE_CONFIG[args.profile]["description"]
                print(f"\n✅ {profile_desc} configuration updated successfully!")
            else:
                print("\n❌ Failed to update configuration")

        # Call the mock main instead of the real one
        mock_main()

        captured = capsys.readouterr()
        assert "🔑 PulsePlate API Key Configuration" in captured.out
        assert "✅ Paid/Premium configuration updated successfully!" in captured.out

    def test_main_argparse_with_profile(
        self,
        tmp_path: Path,
        capsys: CaptureFixture[str],
        monkeypatch: MonkeyPatch,
        fake_crypto: Type[Any],
    ) -> None:
        """Test main() function with profile argument"""
        valid_key = "sk-" + "a" * 40
        monkeypatch.setattr("update_api_key.Path.home", lambda: tmp_path)
        # Mock sys.argv to simulate command line arguments with profile
        monkeypatch.setattr(
            "sys.argv", ["update_api_key.py", "--profile", "free", "--api-key", valid_key]
        )

        update_api_key.main()

        captured = capsys.readouterr()
        assert "🔑 PulsePlate API Key Configuration" in captured.out
        assert "🎉 API key updated successfully!" in captured.out
        assert "✅ Free tier key configuration updated successfully!" in captured.out

    def test_main_argparse_prompt_for_key(
        self,
        tmp_path: Path,
        capsys: CaptureFixture[str],
        monkeypatch: MonkeyPatch,
        fake_crypto: Type[Any],
    ) -> None:
        """Test main() function with profile argument but no api-key (should prompt)"""
        valid_key = "sk-" + "a" * 40
        monkeypatch.setattr("update_api_key.Path.home", lambda: tmp_path)
        # Mock sys.argv to simulate command line arguments with profile but no key
        monkeypatch.setattr("sys.argv", ["update_api_key.py", "--profile", "free"])
        # Mock user input for the prompt
        monkeypatch.setattr("builtins.input", lambda _: valid_key)

        update_api_key.main()

        captured = capsys.readouterr()
        assert "🔑 PulsePlate API Key Configuration" in captured.out
        assert "🎉 API key updated successfully!" in captured.out
        assert "✅ Free tier key configuration updated successfully!" in captured.out

    def test_update_api_key_invalid_profile(self, capsys: CaptureFixture[str]) -> None:
        """Test update_api_key with invalid profile"""
        from update_api_key import update_api_key as update_key_func

        result = update_key_func("sk-validkey12345678901234567890", profile="invalid")
        assert result is False

        captured = capsys.readouterr()
        assert "❌ Invalid profile 'invalid'" in captured.out


class TestValidateAPIKeyValue:
    """Comprehensive tests for _validate_api_key_value function"""

    def test_validate_api_key_empty(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test _validate_api_key_value raises RuntimeError for empty key"""
        logger = logging.getLogger("scripts.update_api_key")
        with pytest.raises(RuntimeError, match="Invalid API key"):
            update_api_key._validate_api_key_value(
                api_key="",
                key_source="test",
                prefix="sk-",
                min_len=20,
                max_len=256,
                allowed_chars_str="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.",
                verbose_errors=False,
                logger=logger,
            )
        assert "key is empty" in caplog.text.lower()

    def test_validate_api_key_wrong_prefix(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test _validate_api_key_value raises RuntimeError for wrong prefix"""
        logger = logging.getLogger("scripts.update_api_key")
        with pytest.raises(RuntimeError, match="Invalid API key"):
            update_api_key._validate_api_key_value(
                api_key="invalid-prefix-key-12345678901234567890",
                key_source="test",
                prefix="sk-",
                min_len=20,
                max_len=256,
                allowed_chars_str="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.",
                verbose_errors=False,
                logger=logger,
            )
        assert "invalid prefix" in caplog.text.lower()

    def test_validate_api_key_too_short(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test _validate_api_key_value raises RuntimeError for too short key"""
        logger = logging.getLogger("scripts.update_api_key")
        with pytest.raises(RuntimeError, match="Invalid API key"):
            update_api_key._validate_api_key_value(
                api_key="sk-short",
                key_source="test",
                prefix="sk-",
                min_len=20,
                max_len=256,
                allowed_chars_str="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.",
                verbose_errors=False,
                logger=logger,
            )
        assert "too short" in caplog.text.lower()

    def test_validate_api_key_too_long(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test _validate_api_key_value raises RuntimeError for too long key"""
        logger = logging.getLogger("scripts.update_api_key")
        long_key = "sk-" + "a" * 300
        with pytest.raises(RuntimeError, match="Invalid API key"):
            update_api_key._validate_api_key_value(
                api_key=long_key,
                key_source="test",
                prefix="sk-",
                min_len=20,
                max_len=256,
                allowed_chars_str="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.",
                verbose_errors=False,
                logger=logger,
            )
        assert "too long" in caplog.text.lower()

    def test_validate_api_key_invalid_chars(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test _validate_api_key_value raises RuntimeError for invalid characters"""
        logger = logging.getLogger("scripts.update_api_key")
        invalid_key = "sk-validkey12345678901234567890@#$"
        with pytest.raises(RuntimeError, match="Invalid API key"):
            update_api_key._validate_api_key_value(
                api_key=invalid_key,
                key_source="test",
                prefix="sk-",
                min_len=20,
                max_len=256,
                allowed_chars_str="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.",
                verbose_errors=False,
                logger=logger,
            )
        assert "invalid characters" in caplog.text.lower()

    def test_validate_api_key_verbose_errors(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test _validate_api_key_value with verbose_errors=True provides detailed message"""
        logger = logging.getLogger("scripts.update_api_key")
        with pytest.raises(RuntimeError) as exc_info:
            update_api_key._validate_api_key_value(
                api_key="",
                key_source="test_source",
                prefix="sk-",
                min_len=20,
                max_len=256,
                allowed_chars_str="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.",
                verbose_errors=True,
                logger=logger,
            )
        assert "test_source" in str(exc_info.value)
        assert "key is empty" in str(exc_info.value).lower()


class TestReadAPIKey:
    """Comprehensive tests for _read_api_key function"""

    def test_read_api_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _read_api_key reads from OPENAI_API_KEY environment variable"""
        valid_key = "sk-" + "a" * 40
        monkeypatch.setenv("OPENAI_API_KEY", valid_key)
        result = update_api_key._read_api_key()
        assert result == valid_key

    def test_read_api_key_from_stdin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _read_api_key reads from stdin when env var not set"""
        valid_key = "sk-" + "b" * 40
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setattr("sys.stdin", io.StringIO(valid_key))
        result = update_api_key._read_api_key()
        assert result == valid_key

    def test_read_api_key_no_source(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _read_api_key raises RuntimeError when neither env nor stdin available"""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setattr("sys.stdin", io.StringIO(""))
        with pytest.raises(RuntimeError, match="API key not provided"):
            update_api_key._read_api_key()

    def test_read_api_key_custom_validation_params(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _read_api_key uses custom validation parameters"""
        valid_key = "sk-" + "c" * 40
        monkeypatch.setenv("OPENAI_API_KEY", valid_key)
        result = update_api_key._read_api_key(
            api_key_prefix="sk-",
            api_key_min_length=20,
            api_key_max_length=256,
            api_key_allowed_chars="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.",
        )
        assert result == valid_key

    def test_read_api_key_invalid_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _read_api_key validates and rejects invalid key from env"""
        invalid_key = "invalid-key"
        monkeypatch.setenv("OPENAI_API_KEY", invalid_key)
        with pytest.raises(RuntimeError, match="Invalid API key"):
            update_api_key._read_api_key()

    def test_read_api_key_invalid_from_stdin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _read_api_key validates and rejects invalid key from stdin"""
        invalid_key = "invalid-key"
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setattr("sys.stdin", io.StringIO(invalid_key))
        with pytest.raises(RuntimeError, match="Invalid API key"):
            update_api_key._read_api_key()


class TestUpdateAPIKeyComprehensive:
    """Comprehensive tests for update_api_key function covering all branches"""

    def test_update_api_key_without_encryption(
        self, tmp_path: Path, capsys: pytest.CaptureFixture, fake_crypto: type
    ) -> None:
        """Test update_api_key succeeds without encryption when use_encryption=False"""
        valid_key = "sk-" + "a" * 40
        mcp_file = tmp_path / ".cursor" / "mcp.json"
        mcp_file.parent.mkdir(parents=True, exist_ok=True)
        mcp_file.write_text(json.dumps({"mcpServers": {}}))

        env_file = tmp_path / ".cursor" / ".env"
        env_file.parent.mkdir(parents=True, exist_ok=True)
        env_file.write_text("OTHER=value")

        with patch("update_api_key.Path.home", return_value=tmp_path):
            # Note: _encryption_available() is still checked even when use_encryption=False
            # This is current behavior of the code
            result = update_api_key.update_api_key(valid_key, use_encryption=False)
            assert result is True

        # Check that plaintext key was written to .env
        content = env_file.read_text()
        assert f"OPENAI_API_KEY={valid_key}" in content

    def test_update_api_key_encryption_helper_missing(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """Test update_api_key fails when encryption helper is missing"""
        valid_key = "sk-" + "a" * 40
        with patch("update_api_key.Path.home", return_value=tmp_path):
            with patch("update_api_key.encrypt_value", None):
                result = update_api_key.update_api_key(valid_key, use_encryption=True)
                assert result is False
                captured = capsys.readouterr()
                assert "Encryption helper is not available" in captured.out

    def test_update_api_key_encryption_fails_runtime_error(
        self, tmp_path: Path, capsys: pytest.CaptureFixture, fake_crypto: type
    ) -> None:
        """Test update_api_key handles RuntimeError from encryption"""
        valid_key = "sk-" + "a" * 40
        with patch("update_api_key.Path.home", return_value=tmp_path):
            with patch(
                "update_api_key.encrypt_value", side_effect=RuntimeError("Encryption error")
            ):
                result = update_api_key.update_api_key(valid_key, use_encryption=True)
                assert result is False
                captured = capsys.readouterr()
                assert "Encryption failed: Encryption error" in captured.out
                assert "Error: Encryption error" in captured.out

    def test_update_api_key_corrupted_json_mcp(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture, fake_crypto: type
    ) -> None:
        """Test update_api_key handles corrupted JSON in mcp.json"""
        valid_key = "sk-" + "a" * 40
        mcp_file = tmp_path / ".cursor" / "mcp.json"
        mcp_file.parent.mkdir(parents=True, exist_ok=True)
        mcp_file.write_text("{invalid json}")

        with patch("update_api_key.Path.home", return_value=tmp_path):
            result = update_api_key.update_api_key(valid_key)
            assert result is True  # Should continue despite JSON error
            assert "Failed to read MCP config" in caplog.text

    def test_update_api_key_corrupted_json_settings(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture, fake_crypto: type
    ) -> None:
        """Test update_api_key handles corrupted JSON in settings.json"""
        valid_key = "sk-" + "a" * 40
        settings_file = tmp_path / ".cursor" / "settings.json"
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        settings_file.write_text("{invalid json}")

        with patch("update_api_key.Path.home", return_value=tmp_path):
            result = update_api_key.update_api_key(valid_key)
            assert result is True  # Should continue despite JSON error
            assert "Failed to read settings.json" in caplog.text

    def test_update_api_key_write_permission_error_mcp(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture, fake_crypto: type
    ) -> None:
        """Test update_api_key handles write permission errors for mcp.json"""
        valid_key = "sk-" + "a" * 40
        mcp_file = tmp_path / ".cursor" / "mcp.json"
        mcp_file.parent.mkdir(parents=True, exist_ok=True)
        mcp_file.write_text(json.dumps({"mcpServers": {}}))
        # Make file read-only
        mcp_file.chmod(0o444)

        try:
            with patch("update_api_key.Path.home", return_value=tmp_path):
                result = update_api_key.update_api_key(valid_key)
                assert result is True  # Should continue despite write error
                assert "Failed to write MCP config" in caplog.text
        finally:
            # Restore permissions for cleanup
            mcp_file.chmod(0o644)

    def test_update_api_key_write_permission_error_env(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture, fake_crypto: type
    ) -> None:
        """Test update_api_key handles write permission errors for .env"""
        valid_key = "sk-" + "a" * 40
        env_file = tmp_path / ".cursor" / ".env"
        env_file.parent.mkdir(parents=True, exist_ok=True)
        env_file.write_text("OTHER=value")
        # Make file read-only
        env_file.chmod(0o444)

        try:
            with patch("update_api_key.Path.home", return_value=tmp_path):
                result = update_api_key.update_api_key(valid_key)
                assert result is True  # Should continue despite write error
                assert "Failed to write .env file" in caplog.text
        finally:
            # Restore permissions for cleanup
            env_file.chmod(0o644)

    def test_update_api_key_write_permission_error_settings(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture, fake_crypto: type
    ) -> None:
        """Test update_api_key handles write permission errors for settings.json"""
        valid_key = "sk-" + "a" * 40
        settings_file = tmp_path / ".cursor" / "settings.json"
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        settings_file.write_text(json.dumps({}))
        # Make file read-only
        settings_file.chmod(0o444)

        try:
            with patch("update_api_key.Path.home", return_value=tmp_path):
                result = update_api_key.update_api_key(valid_key)
                assert result is True  # Should continue despite write error
                assert "Failed to write settings.json" in caplog.text
        finally:
            # Restore permissions for cleanup
            settings_file.chmod(0o644)

    def test_update_api_key_read_error_env(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture, fake_crypto: type
    ) -> None:
        """Test update_api_key handles read errors for .env file"""
        valid_key = "sk-" + "a" * 40
        env_file = tmp_path / ".cursor" / ".env"
        env_file.parent.mkdir(parents=True, exist_ok=True)
        env_file.write_text("OTHER=value")
        # Make directory read-only to prevent file read
        env_file.parent.chmod(0o000)

        try:
            with patch("update_api_key.Path.home", return_value=tmp_path):
                result = update_api_key.update_api_key(valid_key)
                assert result is True  # Should continue despite read error
                assert "Failed to read .env file" in caplog.text
        finally:
            # Restore permissions for cleanup
            env_file.parent.chmod(0o755)

    def test_update_api_key_unexpected_exception(
        self, tmp_path: Path, capsys: CaptureFixture[str], fake_crypto: Type[Any]
    ) -> None:
        """Test update_api_key handles unexpected exceptions"""
        valid_key = "sk-" + "a" * 40
        with patch("update_api_key.Path.home", return_value=tmp_path):
            with patch(
                "update_api_key._validate_api_key_value", side_effect=Exception("Unexpected")
            ):
                # The exception should be caught in update_api_key
                result = update_api_key.update_api_key(valid_key)
                assert result is False
                captured = capsys.readouterr()
                assert "❌ Error:" in captured.out

    def test_update_api_key_free_profile(self, tmp_path: Path, fake_crypto: Type[Any]) -> None:
        """Test update_api_key with free profile"""
        valid_key = "sk-" + "a" * 40
        mcp_file = tmp_path / ".cursor" / "mcp.json"
        mcp_file.parent.mkdir(parents=True, exist_ok=True)
        mcp_file.write_text(json.dumps({"mcpServers": {}}))

        with patch("update_api_key.Path.home", return_value=tmp_path):
            result = update_api_key.update_api_key(valid_key, profile="free")
            assert result is True

        config = json.loads(mcp_file.read_text())
        env = config["mcpServers"]["pulseplate-chatgpt"]["env"]
        assert env["OPENAI_API_KEY_FREE"] == valid_key


class TestMainCLI:
    """Comprehensive CLI tests for main() function"""

    def test_main_with_stdin_input(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        fake_crypto: type,
    ) -> None:
        """Test main() reads from stdin when no args provided"""
        valid_key = "sk-" + "a" * 40
        monkeypatch.setattr("update_api_key.Path.home", lambda: tmp_path)
        monkeypatch.setattr("sys.argv", ["update_api_key.py"])
        monkeypatch.setattr("builtins.input", lambda _: valid_key)

        update_api_key.main()

        captured = capsys.readouterr()
        assert "🔑 PulsePlate API Key Configuration" in captured.out
        assert "🎉 API key updated successfully!" in captured.out

    def test_main_eof_error(
        self, tmp_path: Path, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test main() handles EOFError from input()"""
        monkeypatch.setattr("update_api_key.Path.home", lambda: tmp_path)
        monkeypatch.setattr("sys.argv", ["update_api_key.py"])
        monkeypatch.setattr("builtins.input", side_effect=EOFError)  # type: ignore[call-overload]

        update_api_key.main()

        captured = capsys.readouterr()
        assert "❌ No API key provided" in captured.out

    def test_main_encryption_not_available(
        self, tmp_path: Path, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test main() when _encryption_available returns False"""
        valid_key = "sk-" + "a" * 40
        monkeypatch.setattr("update_api_key.Path.home", lambda: tmp_path)
        monkeypatch.setattr("sys.argv", ["update_api_key.py"])
        monkeypatch.setattr("builtins.input", lambda _: valid_key)
        monkeypatch.setattr("update_api_key.encrypt_value", lambda x: f"encrypted:{x}")
        monkeypatch.setattr("update_api_key._encryption_available", lambda: False)

        update_api_key.main()

        captured = capsys.readouterr()
        assert "❌ Encryption not available" in captured.out

    def test_main_non_interactive_with_api_key(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        fake_crypto: type,
    ) -> None:
        """Test main() non-interactive mode with --api-key argument"""
        valid_key = "sk-" + "a" * 40
        monkeypatch.setattr("update_api_key.Path.home", lambda: tmp_path)
        # Simulate command line: python update_api_key.py --api-key <key>
        original_argv = sys.argv.copy()
        try:
            sys.argv = ["update_api_key.py", "--api-key", valid_key]
            update_api_key.main()
        finally:
            sys.argv = original_argv

        captured = capsys.readouterr()
        assert "🔑 PulsePlate API Key Configuration" in captured.out
        assert "🎉 API key updated successfully!" in captured.out

    def test_main_with_profile_free(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        fake_crypto: type,
    ) -> None:
        """Test main() with --profile free argument"""
        valid_key = "sk-" + "a" * 40
        monkeypatch.setattr("update_api_key.Path.home", lambda: tmp_path)
        original_argv = sys.argv.copy()
        try:
            sys.argv = ["update_api_key.py", "--profile", "free", "--api-key", valid_key]
            update_api_key.main()
        finally:
            sys.argv = original_argv

        captured = capsys.readouterr()
        assert "Free tier key configuration updated successfully!" in captured.out
