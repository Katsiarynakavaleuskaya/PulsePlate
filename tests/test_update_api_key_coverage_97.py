"""Tests to boost coverage for update_api_key.py to 97%."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
import pytest

from update_api_key import update_api_key, main


class TestUpdateApiKeyCoverage97:
    """Test class to achieve 97% coverage for update_api_key.py."""

    def test_update_api_key_invalid_format(self):
        """Test update_api_key with invalid API key format."""
        result = update_api_key("invalid-key")
        assert result is False

    def test_update_api_key_empty_string(self):
        """Test update_api_key with empty string."""
        result = update_api_key("")
        assert result is False

    def test_update_api_key_none(self):
        """Test update_api_key with None."""
        result = update_api_key(None)
        assert result is False

    def test_update_api_key_no_sk_prefix(self):
        """Test update_api_key without sk- prefix."""
        result = update_api_key("ak-1234567890")
        assert result is False

    @patch("update_api_key.Path.home")
    def test_update_api_key_mcp_file_exists(self, mock_home):
        """Test update_api_key when MCP file exists."""
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_home.return_value = Path(temp_dir)

            # Create MCP file
            mcp_file = Path(temp_dir) / ".cursor" / "mcp.json"
            mcp_file.parent.mkdir(parents=True, exist_ok=True)

            # Create existing MCP config
            existing_config = {
                "mcpServers": {"existing-server": {"command": "python", "args": ["script.py"]}}
            }

            with open(mcp_file, "w") as f:
                json.dump(existing_config, f)

            # Mock file operations
            with patch("builtins.open", mock_open()) as mock_file:
                with patch("json.load", return_value=existing_config):
                    with patch("json.dump"):
                        result = update_api_key("sk-1234567890")
                        assert result is True

    @patch("update_api_key.Path.home")
    def test_update_api_key_mcp_file_not_exists(self, mock_home):
        """Test update_api_key when MCP file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_home.return_value = Path(temp_dir)

            # Don't create MCP file
            result = update_api_key("sk-1234567890")
            assert result is True

    @patch("update_api_key.Path.home")
    def test_update_api_key_env_file_exists(self, mock_home):
        """Test update_api_key when env file exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_home.return_value = Path(temp_dir)

            # Create env file
            env_file = Path(temp_dir) / ".cursor" / ".env"
            env_file.parent.mkdir(parents=True, exist_ok=True)

            # Create existing env content
            existing_content = "SOME_VAR=value\nOTHER_VAR=other_value"

            with open(env_file, "w") as f:
                f.write(existing_content)

            # Mock file operations
            with patch("builtins.open", mock_open(read_data=existing_content)) as mock_file:
                result = update_api_key("sk-1234567890")
                assert result is True

    @patch("update_api_key.Path.home")
    def test_update_api_key_env_file_not_exists(self, mock_home):
        """Test update_api_key when env file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_home.return_value = Path(temp_dir)

            # Don't create env file
            result = update_api_key("sk-1234567890")
            assert result is True

    @patch("update_api_key.Path.home")
    def test_update_api_key_settings_file_exists(self, mock_home):
        """Test update_api_key when settings file exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_home.return_value = Path(temp_dir)

            # Create settings file
            settings_file = Path(temp_dir) / ".cursor" / "settings.json"
            settings_file.parent.mkdir(parents=True, exist_ok=True)

            # Create existing settings
            existing_settings = {
                "cursor.ai.primaryModel": "gpt-4",
                "cursor.ai.secondaryModel": "gpt-3.5-turbo",
            }

            with open(settings_file, "w") as f:
                json.dump(existing_settings, f)

            # Mock file operations
            with patch("builtins.open", mock_open()) as mock_file:
                with patch("json.load", return_value=existing_settings):
                    with patch("json.dump"):
                        result = update_api_key("sk-1234567890")
                        assert result is True

    @patch("update_api_key.Path.home")
    def test_update_api_key_settings_file_not_exists(self, mock_home):
        """Test update_api_key when settings file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_home.return_value = Path(temp_dir)

            # Don't create settings file
            result = update_api_key("sk-1234567890")
            assert result is True

    @patch("update_api_key.Path.home")
    def test_update_api_key_all_files_exist(self, mock_home):
        """Test update_api_key when all files exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_home.return_value = Path(temp_dir)

            # Create all files
            cursor_dir = Path(temp_dir) / ".cursor"
            cursor_dir.mkdir(parents=True, exist_ok=True)

            # MCP file
            mcp_file = cursor_dir / "mcp.json"
            mcp_config = {"mcpServers": {}}
            with open(mcp_file, "w") as f:
                json.dump(mcp_config, f)

            # Env file
            env_file = cursor_dir / ".env"
            with open(env_file, "w") as f:
                f.write("EXISTING_VAR=value")

            # Settings file
            settings_file = cursor_dir / "settings.json"
            settings_config = {"cursor.ai.primaryModel": "gpt-4"}
            with open(settings_file, "w") as f:
                json.dump(settings_config, f)

            # Mock file operations
            with patch("builtins.open", mock_open()) as mock_file:
                with patch("json.load", side_effect=[mcp_config, settings_config]):
                    with patch("json.dump"):
                        result = update_api_key("sk-1234567890")
                        assert result is True

    @patch("update_api_key.Path.home")
    def test_update_api_key_env_file_key_replacement(self, mock_home):
        """Test update_api_key with existing API key in env file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_home.return_value = Path(temp_dir)

            # Create env file with existing API key
            env_file = Path(temp_dir) / ".cursor" / ".env"
            env_file.parent.mkdir(parents=True, exist_ok=True)

            existing_content = "OPENAI_API_KEY=sk-old-key\nOTHER_VAR=value"

            with open(env_file, "w") as f:
                f.write(existing_content)

            # Mock file operations
            with patch("builtins.open", mock_open(read_data=existing_content)) as mock_file:
                result = update_api_key("sk-1234567890")
                assert result is True

    @patch("update_api_key.Path.home")
    def test_update_api_key_env_file_no_existing_key(self, mock_home):
        """Test update_api_key with no existing API key in env file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_home.return_value = Path(temp_dir)

            # Create env file without API key
            env_file = Path(temp_dir) / ".cursor" / ".env"
            env_file.parent.mkdir(parents=True, exist_ok=True)

            existing_content = "OTHER_VAR=value\nANOTHER_VAR=another_value"

            with open(env_file, "w") as f:
                f.write(existing_content)

            # Mock file operations
            with patch("builtins.open", mock_open(read_data=existing_content)) as mock_file:
                result = update_api_key("sk-1234567890")
                assert result is True

    @patch("update_api_key.input")
    @patch("update_api_key.update_api_key")
    def test_main_with_valid_key(self, mock_update, mock_input):
        """Test main function with valid API key."""
        mock_input.return_value = "sk-1234567890"
        mock_update.return_value = True

        main()

        mock_update.assert_called_once_with("sk-1234567890")

    @patch("update_api_key.input")
    @patch("update_api_key.update_api_key")
    def test_main_with_invalid_key(self, mock_update, mock_input):
        """Test main function with invalid API key."""
        mock_input.return_value = "invalid-key"
        mock_update.return_value = False

        main()

        mock_update.assert_called_once_with("invalid-key")

    @patch("update_api_key.input")
    @patch("update_api_key.update_api_key")
    def test_main_with_empty_key(self, mock_update, mock_input):
        """Test main function with empty API key."""
        mock_input.return_value = ""
        mock_update.return_value = False

        main()

        # Should not call update_api_key for empty input
        mock_update.assert_not_called()

    @patch("update_api_key.input")
    @patch("update_api_key.update_api_key")
    def test_main_with_whitespace_key(self, mock_update, mock_input):
        """Test main function with whitespace-only API key."""
        mock_input.return_value = "   "
        mock_update.return_value = False

        main()

        # Should not call update_api_key for whitespace-only input
        mock_update.assert_not_called()

    @patch("update_api_key.Path.home")
    def test_update_api_key_file_permission_error(self, mock_home):
        """Test update_api_key when file operations fail due to permissions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_home.return_value = Path(temp_dir)

            # Mock file operations to raise permission error
            with patch("builtins.open", side_effect=PermissionError("Permission denied")):
                result = update_api_key("sk-1234567890")
                # Should still return True as other operations continue
                assert result is True

    @patch("update_api_key.Path.home")
    def test_update_api_key_io_error(self, mock_home):
        """Test update_api_key when file operations fail due to IO error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_home.return_value = Path(temp_dir)

            # Mock file operations to raise IO error
            with patch("builtins.open", side_effect=IOError("IO Error")):
                result = update_api_key("sk-1234567890")
                # Should still return True as other operations continue
                assert result is True

    def test_update_api_key_valid_key_format(self):
        """Test update_api_key with valid key format."""
        with patch("update_api_key.Path.home") as mock_home:
            with tempfile.TemporaryDirectory() as temp_dir:
                mock_home.return_value = Path(temp_dir)

                # Mock all file operations
                with patch("builtins.open", mock_open()):
                    with patch("json.load", return_value={}):
                        with patch("json.dump"):
                            result = update_api_key("sk-1234567890abcdef")
                            assert result is True

    def test_update_api_key_very_long_key(self):
        """Test update_api_key with very long API key."""
        long_key = "sk-" + "a" * 1000

        with patch("update_api_key.Path.home") as mock_home:
            with tempfile.TemporaryDirectory() as temp_dir:
                mock_home.return_value = Path(temp_dir)

                # Mock all file operations
                with patch("builtins.open", mock_open()):
                    with patch("json.load", return_value={}):
                        with patch("json.dump"):
                            result = update_api_key(long_key)
                            assert result is True

    def test_update_api_key_unicode_key(self):
        """Test update_api_key with unicode characters in key."""
        unicode_key = "sk-测试-1234567890"

        with patch("update_api_key.Path.home") as mock_home:
            with tempfile.TemporaryDirectory() as temp_dir:
                mock_home.return_value = Path(temp_dir)

                # Mock all file operations
                with patch("builtins.open", mock_open()):
                    with patch("json.load", return_value={}):
                        with patch("json.dump"):
                            result = update_api_key(unicode_key)
                            assert result is True
