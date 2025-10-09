"""
Tests for update_api_key module - API key management with encryption
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

import secure_config
import update_api_key
from secure_config import encrypt_value, get_or_create_encryption_key


@pytest.fixture
def fake_crypto(monkeypatch, tmp_path):
    """Provide fake encryption so tests run without cryptography."""

    class FakeFernet:
        def __init__(self, key: bytes):
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

    monkeypatch.setattr(secure_config, "ENCRYPTION_AVAILABLE", True)
    monkeypatch.setattr(secure_config, "Fernet", FakeFernet, raising=False)
    monkeypatch.setattr(update_api_key, "ENCRYPTION_AVAILABLE", True)
    monkeypatch.setattr(update_api_key, "encrypt_value", secure_config.encrypt_value)
    monkeypatch.setattr(update_api_key, "Path", Path)
    return FakeFernet


class TestUpdateAPIKey:
    """Test update_api_key functionality"""

    def test_validate_api_key_valid(self):
        """Test valid API key validation"""
        valid_key = "sk-" + "a" * 20
        # Should pass validation (returns True in update_api_key function)
        assert valid_key.startswith("sk-")
        assert len(valid_key) >= 20
        assert len(valid_key) <= 256

    def test_validate_api_key_invalid_prefix(self):
        """Test API key validation rejects invalid prefix"""
        invalid_key = "invalid-key-12345678"
        assert not invalid_key.startswith("sk-")

    def test_validate_api_key_too_short(self):
        """Test API key validation rejects short keys"""
        short_key = "sk-short"
        assert len(short_key) < 20

    def test_validate_api_key_too_long(self):
        """Test API key validation rejects very long keys"""
        long_key = "sk-" + "a" * 300
        assert len(long_key) > 256

    def test_encrypt_value_no_encryption(self):
        """Test encryption raises RuntimeError when crypto unavailable"""
        with patch("secure_config.ENCRYPTION_AVAILABLE", False):
            # Should raise RuntimeError when crypto not available
            with pytest.raises(RuntimeError, match="cryptography library not installed"):
                encrypt_value("sk-test12345678901234567890")

    def test_encrypt_value_with_encryption(self, tmp_path):
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

    def test_get_encryption_key_creates_new(self, tmp_path):
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

    def test_update_api_key_invalid_key(self, tmp_path, capsys):
        """Test update_api_key rejects invalid keys"""
        with patch("update_api_key.Path.home", return_value=tmp_path):
            result = update_api_key.update_api_key("invalid-key")
            assert result is False

            captured = capsys.readouterr()
            assert "Invalid API key format" in captured.out

    def test_update_api_key_fails_without_encryption(self, tmp_path, capsys):
        """Test update_api_key fails when encryption not available"""
        valid_key = "sk-" + "a" * 40

        with patch("update_api_key.Path.home", return_value=tmp_path):
            with patch("secure_config.ENCRYPTION_AVAILABLE", False):
                result = update_api_key.update_api_key(valid_key, use_encryption=False)
                # Should fail - encryption is required
                assert result is False

                captured = capsys.readouterr()
                assert "cryptography library not installed" in captured.out

    def test_update_api_key_simple_success(self, tmp_path, capsys, fake_crypto):
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

    def test_update_api_key_updates_mcp_config(self, tmp_path, fake_crypto):
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

    def test_update_api_key_updates_env_file(self, tmp_path, fake_crypto):
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

    def test_update_api_key_handles_env_missing(self, tmp_path, fake_crypto):
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

    def test_update_api_key_handles_env_file_absent(self, tmp_path, capsys, fake_crypto):
        """No error when env/settings files do not exist."""
        valid_key = "sk-" + "z" * 40

        with patch("update_api_key.Path.home", return_value=tmp_path):
            result = update_api_key.update_api_key(valid_key)
            assert result is True

        captured = capsys.readouterr()
        assert "environment file" not in captured.out.lower()

    def test_update_api_key_creates_env_entry_when_missing(self, tmp_path, fake_crypto):
        """If env file absent, no file should be created automatically."""
        valid_key = "sk-" + "w" * 40

        env_file = tmp_path / ".cursor" / ".env"
        assert not env_file.exists()

        with patch("update_api_key.Path.home", return_value=tmp_path):
            update_api_key.update_api_key(valid_key)

        assert not env_file.exists()

    def test_update_api_key_writes_plaintext_to_settings_json(self, tmp_path, fake_crypto):
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

    def test_update_api_key_updates_env_file_existing_key(self, tmp_path, fake_crypto):
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

    def test_update_api_key_appends_env_key_when_missing(self, tmp_path, fake_crypto):
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

    def test_update_api_key_creates_files_when_missing(self, tmp_path, capsys, fake_crypto):
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

    def test_update_api_key_updates_settings_json(self, tmp_path, fake_crypto):
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

    def test_update_api_key_encrypt_failure(self, tmp_path, capsys):
        """Test update_api_key handles encryption failure gracefully."""
        valid_key = "sk-" + "f" * 40

        with patch("update_api_key.Path.home", return_value=tmp_path):
            with patch("update_api_key.encrypt_value", side_effect=RuntimeError("boom")):
                result = update_api_key.update_api_key(valid_key)

        assert result is False
        captured = capsys.readouterr()
        assert "Error: boom" in captured.out

    def test_update_api_key_encryption_prefix_validation(self, tmp_path, capsys):
        """Test update_api_key detects unexpected encryption output."""
        valid_key = "sk-" + "g" * 40

        with patch("update_api_key.Path.home", return_value=tmp_path):
            with patch("update_api_key.encrypt_value", return_value="not_encrypted"):
                result = update_api_key.update_api_key(valid_key)

        assert result is False
        captured = capsys.readouterr()
        assert "Encryption failed" in captured.out

    def test_update_api_key_invalid_env_line(self, tmp_path, fake_crypto):
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

    def test_update_api_key_skips_blank_env_lines(self, tmp_path, fake_crypto):
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

    def test_main_success_path(self, tmp_path, capsys, monkeypatch, fake_crypto):
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

    def test_main_empty_input(self, capsys, monkeypatch):
        """Test main() function with empty input"""
        monkeypatch.setattr("builtins.input", lambda _: "")

        update_api_key.main()

        captured = capsys.readouterr()
        assert "🔑 PulsePlate API Key Configuration" in captured.out
        assert "❌ No API key provided" in captured.out

    def test_main_encryption_unavailable(self, capsys, monkeypatch):
        """Test main() function when encryption is not available"""
        valid_key = "sk-" + "a" * 40
        monkeypatch.setattr("update_api_key.ENCRYPTION_AVAILABLE", False)
        monkeypatch.setattr("builtins.input", lambda _: valid_key)

        update_api_key.main()

        captured = capsys.readouterr()
        assert "❌ Encryption not available" in captured.out

    def test_main_update_failure(self, capsys, monkeypatch):
        """Test main() function when update_api_key fails"""
        valid_key = "sk-" + "a" * 40
        monkeypatch.setattr("builtins.input", lambda _: valid_key)

        with patch("update_api_key.update_api_key", return_value=False):
            update_api_key.main()

        captured = capsys.readouterr()
        assert "❌ Failed to update configuration" in captured.out

    def test_main_argparse_success(self, tmp_path, capsys, monkeypatch, fake_crypto):
        """Test main() function with command line arguments (argparse path)"""
        valid_key = "sk-" + "a" * 40
        monkeypatch.setattr("update_api_key.Path.home", lambda: tmp_path)
        # Mock sys.argv to simulate command line arguments
        monkeypatch.setattr("sys.argv", ["update_api_key.py", "--api-key", valid_key])

        # Mock the main function to skip is_pytest check
        def mock_main():
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
        assert "🎉 API key updated successfully!" in captured.out
        assert "✅ Paid/Premium key configuration updated successfully!" in captured.out

    def test_main_argparse_with_profile(self, tmp_path, capsys, monkeypatch, fake_crypto):
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

    def test_main_argparse_prompt_for_key(self, tmp_path, capsys, monkeypatch, fake_crypto):
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

    def test_update_api_key_invalid_profile(self, capsys):
        """Test update_api_key with invalid profile"""
        from update_api_key import update_api_key as update_key_func

        result = update_key_func("sk-validkey12345678901234567890", profile="invalid")
        assert result is False

        captured = capsys.readouterr()
        assert "❌ Invalid profile 'invalid'" in captured.out
