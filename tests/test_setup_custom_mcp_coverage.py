"""
Test coverage for setup_custom_mcp.py
"""

import json
import os
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Tuple
from unittest.mock import MagicMock, mock_open, patch

import pytest

import setup_custom_mcp


@pytest.fixture
def mcp_setup_mocks() -> Tuple[MagicMock, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock]:
    """Fixture that patches pathlib and builtin functions for setup_custom_mcp tests.

    Yields:
        Tuple containing mocks in order:
        - mock_home: Path.home mock
        - mock_mkdir: Path.mkdir mock
        - mock_file: builtins.open mock
        - mock_json_dump: json.dump mock
        - mock_print: builtins.print mock
        - mock_cwd: Path.cwd mock
    """
    with patch("pathlib.Path.home") as mock_home:
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            with patch("builtins.open", mock_open()) as mock_file:
                with patch("json.dump") as mock_json_dump:
                    with patch("builtins.print") as mock_print:
                        with patch("pathlib.Path.cwd") as mock_cwd:
                            # Configure mocks
                            mock_home.return_value = Path("/fake/home")
                            mock_cwd.return_value = Path("/fake/cwd")

                            yield (
                                mock_home,
                                mock_mkdir,
                                mock_file,
                                mock_json_dump,
                                mock_print,
                                mock_cwd,
                            )


class TestSetupCustomMcpCoverage:
    """Test class to cover setup_custom_mcp.py"""

    def test_setup_custom_mcp_function(
        self,
        mcp_setup_mocks: Tuple[MagicMock, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock],
    ) -> None:
        """Test setup_custom_mcp function"""
        mock_home, mock_mkdir, mock_file, mock_json_dump, mock_print, mock_cwd = mcp_setup_mocks

        # Pass empty argv to avoid pytest argument conflicts
        setup_custom_mcp.setup_custom_mcp(argv=[])

        # Verify directory creation
        mock_mkdir.assert_called_with(exist_ok=True)

        # Verify file operations
        assert mock_file.call_count >= 3  # mcp.json, .env, settings.json

        # Verify JSON dump calls
        assert mock_json_dump.call_count >= 2  # mcp.json and settings.json

        # Verify print statements
        assert mock_print.call_count >= 4

    def test_setup_custom_mcp_with_real_paths(self):
        """Test setup_custom_mcp with real path operations"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            with patch("pathlib.Path.home", return_value=temp_path):
                with patch("pathlib.Path.cwd", return_value=temp_path):
                    self._run_setup_and_verify_files(temp_path)

    def _run_setup_and_verify_files(self, temp_path: Path) -> None:
        setup_custom_mcp.setup_custom_mcp(argv=[])

        # Check that files were created
        cursor_dir = temp_path / ".cursor"
        assert cursor_dir.exists()

        mcp_file = cursor_dir / "mcp.json"
        assert mcp_file.exists()

        env_file = cursor_dir / ".env"
        assert env_file.exists()

        settings_file = cursor_dir / "settings.json"
        assert settings_file.exists()

        # Check MCP configuration content
        with open(mcp_file, "r") as f:
            mcp_config = json.load(f)
            assert "mcpServers" in mcp_config
            assert "pulseplate-chatgpt" in mcp_config["mcpServers"]
            assert mcp_config["mcpServers"]["pulseplate-chatgpt"]["command"] == "python"

        # Check environment file content
        with open(env_file, "r") as f:
            env_content = f.read()
            assert "OPENAI_API_KEY" in env_content
            assert "MCP_ENABLED=true" in env_content

        # Check settings content
        with open(settings_file, "r") as f:
            settings = json.load(f)
            assert settings["cursor.ai.enabled"] is True
            assert settings["mcp.enabled"] is True

    def test_mcp_configuration_structure(self):
        """Test MCP configuration structure"""
        with patch("pathlib.Path.home") as mock_home:
            with patch("pathlib.Path.mkdir"):
                with patch("builtins.open", mock_open()):
                    with patch("json.dump") as mock_json_dump:
                        with patch("builtins.print"):
                            mock_home.return_value = Path("/fake/home")

                            with patch("pathlib.Path.cwd", return_value=Path("/fake/cwd")):
                                self._verify_mcp_config_structure(mock_json_dump)

    # TODO Rename this here and in `test_mcp_configuration_structure`
    def _verify_mcp_config_structure(self, mock_json_dump):
        mcp_call = self._get_json_dump_config_with_key(mock_json_dump, "mcpServers")
        assert "mcpServers" in mcp_call
        assert "pulseplate-chatgpt" in mcp_call["mcpServers"]

        server_config = mcp_call["mcpServers"]["pulseplate-chatgpt"]
        assert server_config["command"] == "python"
        assert "args" in server_config
        assert "env" in server_config
        assert "OPENAI_API_KEY" in server_config["env"]

    def test_cursor_settings_structure(self):
        """Test Cursor settings structure"""
        with patch("pathlib.Path.home") as mock_home:
            with patch("pathlib.Path.mkdir"):
                with patch("builtins.open", mock_open()):
                    with patch("json.dump") as mock_json_dump:
                        with patch("builtins.print"):
                            mock_home.return_value = Path("/fake/home")

                            with patch("pathlib.Path.cwd", return_value=Path("/fake/cwd")):
                                self._verify_cursor_settings_structure(mock_json_dump)

    # TODO Rename this here and in `test_cursor_settings_structure`
    def _verify_cursor_settings_structure(self, mock_json_dump):
        settings_call = self._get_json_dump_config_with_key(mock_json_dump, "cursor.ai.enabled")
        assert settings_call["cursor.ai.enabled"] is True
        assert settings_call["cursor.ai.primaryModel"] == "gpt-4"
        assert settings_call["cursor.ai.secondaryModel"] == "gpt-3.5-turbo"
        assert settings_call["mcp.enabled"] is True
        assert "pulseplate-chatgpt" in settings_call["mcp.servers"]

    # TODO Rename this here and in `_extracted_from_test_mcp_configuration_structure_11` and `_extracted_from_test_cursor_settings_structure_11`
    def _get_json_dump_config_with_key(self, mock_json_dump, config_key):
        setup_custom_mcp.setup_custom_mcp(argv=[])
        result = next(
            (
                call[0][0]
                for call in mock_json_dump.call_args_list
                if len(call[0]) > 0 and isinstance(call[0][0], dict) and config_key in call[0][0]
            ),
            None,
        )
        assert result is not None
        return result

    def test_main_execution(self) -> None:
        """Test main execution when script is run directly"""
        # Test that the function exists and is callable
        assert callable(setup_custom_mcp.setup_custom_mcp)

        # Test that the function can be called with --force to avoid input() prompts
        try:
            # Use --force to skip user prompts in test environment
            setup_custom_mcp.setup_custom_mcp(argv=["--force"])
        except OSError as e:
            pytest.skip(f"insufficient permissions or filesystem error: {e}")
        except Exception as e:
            # Log unexpected errors but don't fail the test
            print(f"Unexpected error during setup_custom_mcp execution: {e}")
            # Re-raise to ensure we catch unexpected issues
            raise

    def test_file_creation_sequence(self) -> None:
        """Test that files are created in the correct sequence"""
        with patch("pathlib.Path.home") as mock_home:
            with patch("pathlib.Path.mkdir"):
                with patch("builtins.open", mock_open()) as mock_file:
                    with patch("json.dump"):
                        with patch("builtins.print"):
                            mock_home.return_value = Path("/fake/home")

                            with patch("pathlib.Path.cwd", return_value=Path("/fake/cwd")):
                                setup_custom_mcp.setup_custom_mcp(argv=[])

                                # Verify that open was called multiple times
                                assert mock_file.call_count >= 3

    def test_error_handling(self) -> None:
        """Test error handling scenarios"""
        with patch("pathlib.Path.home") as mock_home:
            with patch("pathlib.Path.mkdir", side_effect=OSError("Permission denied")):
                with patch("builtins.print") as _:
                    mock_home.return_value = Path("/fake/home")

                    with patch("pathlib.Path.cwd", return_value=Path("/fake/cwd")):
                        # This should raise an exception
                        with pytest.raises(OSError):
                            setup_custom_mcp.setup_custom_mcp(argv=[])

    def test_path_operations(self) -> None:
        """Test path operations"""
        with patch("pathlib.Path.home") as mock_home:
            with patch("pathlib.Path.mkdir"):
                with patch("builtins.open", mock_open()):
                    with patch("json.dump"):
                        with patch("builtins.print"):
                            with patch("pathlib.Path.cwd") as mock_cwd:
                                mock_home.return_value = Path("/fake/home")
                                mock_cwd.return_value = Path("/fake/cwd")

                                setup_custom_mcp.setup_custom_mcp(argv=[])

                                # Verify home directory was accessed
                                mock_home.assert_called_once()

                                # Verify current working directory was accessed
                                mock_cwd.assert_called_once()

    def test_json_serialization(self) -> None:
        """Test JSON serialization of configurations"""
        with patch("pathlib.Path.home") as mock_home:
            with patch("pathlib.Path.mkdir"):
                with patch("builtins.open", mock_open()):
                    with patch("json.dump") as mock_json_dump:
                        with patch("builtins.print"):
                            mock_home.return_value = Path("/fake/home")

                            with patch("pathlib.Path.cwd", return_value=Path("/fake/cwd")):
                                setup_custom_mcp.setup_custom_mcp(argv=[])

                                # Verify json.dump was called with proper arguments
                                assert mock_json_dump.call_count >= 2

                                # Check that indent=2 was used for pretty printing
                                indent_calls = [
                                    call
                                    for call in mock_json_dump.call_args_list
                                    if len(call[1]) > 0 and "indent" in call[1]
                                ]
                                assert any(call[1]["indent"] == 2 for call in indent_calls)
