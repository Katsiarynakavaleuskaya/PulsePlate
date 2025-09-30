"""
Test coverage for update_api_key.py to reach 97%
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
import update_api_key


class TestUpdateApiKeyCoverage97:
    """Test class to boost update_api_key.py coverage to 97%"""

    def test_update_api_key_invalid_format(self):
        """Test update_api_key with invalid API key format"""
        # Test empty API key
        result = update_api_key.update_api_key("")
        assert result is False

        # Test None API key
        result = update_api_key.update_api_key(None)
        assert result is False

        # Test API key without sk- prefix
        result = update_api_key.update_api_key("invalid-key")
        assert result is False

    def test_update_api_key_valid_format(self):
        """Test update_api_key with valid API key format"""
        with patch("pathlib.Path.home") as mock_home:
            # Create temporary directory for testing
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                mock_home.return_value = temp_path

                # Create test MCP config
                mcp_file = temp_path / ".cursor" / "mcp.json"
                mcp_file.parent.mkdir(parents=True, exist_ok=True)

                test_config = {
                    "mcpServers": {"pulseplate-chatgpt": {"env": {"OPENAI_API_KEY": "old-key"}}}
                }

                with open(mcp_file, "w") as f:
                    json.dump(test_config, f)

                # Create test .env file
                env_file = temp_path / ".cursor" / ".env"
                with open(env_file, "w") as f:
                    f.write("OPENAI_API_KEY=old-key\nOTHER_VAR=value")

                # Create test settings file
                settings_file = temp_path / ".cursor" / "settings.json"
                test_settings = {"cursor.ai.openaiApiKey": "old-key"}
                with open(settings_file, "w") as f:
                    json.dump(test_settings, f)

                # Test update_api_key
                result = update_api_key.update_api_key("sk-test12345678901234567890")

                # Verify result
                assert result is True

                # Verify MCP config was updated
                with open(mcp_file, "r") as f:
                    updated_config = json.load(f)
                assert (
                    updated_config["mcpServers"]["pulseplate-chatgpt"]["env"]["OPENAI_API_KEY"]
                    == "sk-test12345678901234567890"
                )

                # Verify .env file was updated
                with open(env_file, "r") as f:
                    env_content = f.read()
                assert "OPENAI_API_KEY=sk-test12345678901234567890" in env_content

                # Verify settings file was updated
                with open(settings_file, "r") as f:
                    updated_settings = json.load(f)
                assert updated_settings["cursor.ai.openaiApiKey"] == "sk-test12345678901234567890"

    def test_update_api_key_missing_files(self):
        """Test update_api_key when files don't exist"""
        with patch("pathlib.Path.home") as mock_home:
            # Create temporary directory for testing
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                mock_home.return_value = temp_path

                # Don't create any files - test when files don't exist
                result = update_api_key.update_api_key("sk-test12345678901234567890")

                # Should still return True even if files don't exist
                assert result is True

    def test_update_api_key_mcp_config_missing_pulseplate(self):
        """Test update_api_key when MCP config exists but doesn't have pulseplate-chatgpt"""
        with patch("pathlib.Path.home") as mock_home:
            # Create temporary directory for testing
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                mock_home.return_value = temp_path

                # Create test MCP config without pulseplate-chatgpt
                mcp_file = temp_path / ".cursor" / "mcp.json"
                mcp_file.parent.mkdir(parents=True, exist_ok=True)

                test_config = {"mcpServers": {"other-server": {"env": {"SOME_KEY": "value"}}}}

                with open(mcp_file, "w") as f:
                    json.dump(test_config, f)

                result = update_api_key.update_api_key("sk-test12345678901234567890")
                assert result is True

    def test_update_api_key_env_file_no_openai_key(self):
        """Test update_api_key when .env file exists but has no OPENAI_API_KEY"""
        with patch("pathlib.Path.home") as mock_home:
            # Create temporary directory for testing
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                mock_home.return_value = temp_path

                # Create .cursor directory
                cursor_dir = temp_path / ".cursor"
                cursor_dir.mkdir(parents=True, exist_ok=True)

                # Create test .env file without OPENAI_API_KEY
                env_file = cursor_dir / ".env"
                with open(env_file, "w") as f:
                    f.write("OTHER_VAR=value\nANOTHER_VAR=another_value")

                result = update_api_key.update_api_key("sk-test12345678901234567890")
                assert result is True

    def test_main_function_with_valid_input(self):
        """Test main function with valid input"""
        with patch("builtins.input", return_value="sk-test123"):
            with patch("update_api_key.update_api_key", return_value=True) as mock_update:
                # Capture print output
                with patch("builtins.print") as mock_print:
                    update_api_key.main()

                    # Verify update_api_key was called
                    mock_update.assert_called_once_with("sk-test123")

    def test_main_function_with_empty_input(self):
        """Test main function with empty input"""
        with patch("builtins.input", return_value=""):
            with patch("builtins.print") as mock_print:
                update_api_key.main()

                # Verify error message was printed
                mock_print.assert_any_call("❌ No API key provided")

    def test_main_function_with_whitespace_input(self):
        """Test main function with whitespace-only input"""
        with patch("builtins.input", return_value="   "):
            with patch("builtins.print") as mock_print:
                update_api_key.main()

                # Verify error message was printed
                mock_print.assert_any_call("❌ No API key provided")

    def test_main_function_update_failure(self):
        """Test main function when update_api_key returns False"""
        with patch("builtins.input", return_value="sk-test123"):
            with patch("update_api_key.update_api_key", return_value=False) as mock_update:
                with patch("builtins.print") as mock_print:
                    update_api_key.main()

                    # Verify failure message was printed
                    mock_print.assert_any_call("\n❌ Failed to update configuration")

    def test_main_function_update_success(self):
        """Test main function when update_api_key returns True"""
        with patch("builtins.input", return_value="sk-test123"):
            with patch("update_api_key.update_api_key", return_value=True) as mock_update:
                with patch("builtins.print") as mock_print:
                    update_api_key.main()

                    # Verify success message was printed
                    mock_print.assert_any_call("\n✅ Configuration updated successfully!")

    def test_update_api_key_additional_coverage(self):
        """Test additional coverage scenarios"""
        # Test with different API key formats
        result = update_api_key.update_api_key("sk-")
        # This should return False because "sk-" is too short
        assert result is False

        # Test with valid API key format
        result = update_api_key.update_api_key("sk-12345678901234567890")
        # This should return True because it's a valid format
        assert result is True

        # Test with valid API key but no files exist
        with patch("pathlib.Path.home") as mock_home:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                mock_home.return_value = temp_path

                result = update_api_key.update_api_key("sk-valid12345678901234567890")
                assert result is True
