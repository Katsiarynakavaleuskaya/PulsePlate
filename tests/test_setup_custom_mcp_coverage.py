"""
Test coverage for setup_custom_mcp.py
"""

import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import mock_open, patch

import pytest

import setup_custom_mcp


class TestSetupCustomMcpCoverage:
    """Test class to cover setup_custom_mcp.py"""

    def test_setup_custom_mcp_function(self):
        """Test setup_custom_mcp function"""
        with patch("pathlib.Path.home") as mock_home:
            with patch("pathlib.Path.mkdir") as mock_mkdir:
                with patch("builtins.open", mock_open()) as mock_file:
                    with patch("json.dump") as mock_json_dump:
                        with patch("builtins.print") as mock_print:
                            # Mock home directory
                            mock_home.return_value = Path("/fake/home")

                            # Mock Path.cwd()
                            with patch("pathlib.Path.cwd", return_value=Path("/fake/cwd")):
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

    def _run_setup_and_verify_files(self, temp_path):
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
            assert mcp_config["mcpServers"]["pulseplate-chatgpt"]["command"] == sys.executable
            assert mcp_config["mcpServers"]["pulseplate-chatgpt"]["args"] == [
                str(setup_custom_mcp.MCP_SERVER_PATH)
            ]

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
        assert server_config["command"] == sys.executable
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

    def test_main_execution(self):
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

    def test_file_creation_sequence(self):
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

    def test_error_handling(self):
        """Test error handling scenarios"""
        with patch("pathlib.Path.home") as mock_home:
            with patch("pathlib.Path.mkdir", side_effect=OSError("Permission denied")):
                with patch("builtins.print") as _:
                    mock_home.return_value = Path("/fake/home")

                    with patch("pathlib.Path.cwd", return_value=Path("/fake/cwd")):
                        # This should raise an exception
                        with pytest.raises(OSError):
                            setup_custom_mcp.setup_custom_mcp(argv=[])

    def test_path_operations(self):
        """Test path operations"""
        with patch("pathlib.Path.home") as mock_home:
            with patch("pathlib.Path.mkdir"):
                with patch("builtins.open", mock_open()):
                    with patch("json.dump"):
                        with patch("builtins.print"):
                            mock_home.return_value = Path("/fake/home")

                            setup_custom_mcp.setup_custom_mcp(argv=[])

                            # Verify home directory was accessed
                            mock_home.assert_called_once()

    def test_json_serialization(self):
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

    def test_setup_custom_mcp_preserves_existing_mcp_servers_and_settings(self):
        """Existing MCP servers and unrelated settings must survive setup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            cursor_dir = temp_path / ".cursor"
            cursor_dir.mkdir(parents=True, exist_ok=True)

            (cursor_dir / "mcp.json").write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "figma": {"url": "https://mcp.figma.com/mcp"},
                        }
                    }
                )
            )
            (cursor_dir / "settings.json").write_text(
                json.dumps(
                    {
                        "mcp.servers": ["figma"],
                        "editor.formatOnSave": True,
                    }
                )
            )

            with patch("pathlib.Path.home", return_value=temp_path):
                with patch("pathlib.Path.cwd", return_value=temp_path):
                    setup_custom_mcp.setup_custom_mcp(argv=["--force"])

            mcp_config = json.loads((cursor_dir / "mcp.json").read_text())
            assert "figma" in mcp_config["mcpServers"]
            assert "pulseplate-chatgpt" in mcp_config["mcpServers"]

            settings = json.loads((cursor_dir / "settings.json").read_text())
            assert settings["editor.formatOnSave"] is True
            assert "figma" in settings["mcp.servers"]
            assert "pulseplate-chatgpt" in settings["mcp.servers"]

    def test_setup_custom_mcp_preserves_existing_env_entries(self):
        """Existing .env values should survive setup without runtime key promotion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            cursor_dir = temp_path / ".cursor"
            cursor_dir.mkdir(parents=True, exist_ok=True)
            (cursor_dir / ".env").write_text("OTHER=value\nOPENAI_API_KEY=keepme\n")

            with patch("pathlib.Path.home", return_value=temp_path):
                with patch("pathlib.Path.cwd", return_value=temp_path):
                    setup_custom_mcp.setup_custom_mcp(argv=["--force"])

            env_lines = (cursor_dir / ".env").read_text().splitlines()
            assert "OTHER=value" in env_lines
            assert "OPENAI_API_KEY=keepme" in env_lines
            assert "MCP_ENABLED=true" in env_lines

            mcp_config = json.loads((cursor_dir / "mcp.json").read_text())
            pulseplate_server = mcp_config["mcpServers"]["pulseplate-chatgpt"]
            assert (
                pulseplate_server["env"]["OPENAI_API_KEY"] == setup_custom_mcp.PLACEHOLDER_API_KEY
            )

            settings = json.loads((cursor_dir / "settings.json").read_text())
            assert settings["cursor.ai.openaiApiKey"] == setup_custom_mcp.PLACEHOLDER_API_KEY

    def test_setup_custom_mcp_upserts_env_keys_with_extra_whitespace(self):
        """Whitespace around .env keys should not create duplicate managed entries."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            cursor_dir = temp_path / ".cursor"
            cursor_dir.mkdir(parents=True, exist_ok=True)
            (cursor_dir / ".env").write_text(
                "OTHER=value\n  OPENAI_API_KEY = keepme\nMCP_ENABLED = false\n"
            )

            with patch("pathlib.Path.home", return_value=temp_path):
                with patch("pathlib.Path.cwd", return_value=temp_path):
                    setup_custom_mcp.setup_custom_mcp(argv=["--force"])

            env_lines = (cursor_dir / ".env").read_text().splitlines()
            assert env_lines.count("OPENAI_API_KEY=keepme") == 1
            assert env_lines.count("MCP_ENABLED=true") == 1
            assert not any(line.startswith("  OPENAI_API_KEY") for line in env_lines)
            assert not any(line.startswith("MCP_ENABLED =") for line in env_lines)
            assert "OTHER=value" in env_lines

    def test_setup_custom_mcp_uses_repo_server_path_not_cwd(self):
        """The generated MCP command path must stay anchored to the repo script."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            cursor_dir = temp_path / ".cursor"
            cursor_dir.mkdir(parents=True, exist_ok=True)
            off_repo_cwd = temp_path / "outside-repo"
            off_repo_cwd.mkdir()

            with patch("pathlib.Path.home", return_value=temp_path):
                with patch("pathlib.Path.cwd", return_value=off_repo_cwd):
                    setup_custom_mcp.setup_custom_mcp(argv=["--force"])

            mcp_config = json.loads((cursor_dir / "mcp.json").read_text())
            pulseplate_server = mcp_config["mcpServers"]["pulseplate-chatgpt"]
            assert pulseplate_server["args"] == [str(setup_custom_mcp.MCP_SERVER_PATH)]

    def test_setup_custom_mcp_preserves_existing_api_key_across_managed_surfaces(self):
        """A configured key must survive reruns across mcp.json, .env, and settings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            cursor_dir = temp_path / ".cursor"
            cursor_dir.mkdir(parents=True, exist_ok=True)
            existing_key = "keepme"

            (cursor_dir / "mcp.json").write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "pulseplate-chatgpt": {
                                "command": "/old/python",
                                "args": ["/old/path/mcp_pulseplate_server.py"],
                                "env": {"OPENAI_API_KEY": existing_key},
                            }
                        }
                    }
                )
            )
            (cursor_dir / ".env").write_text(
                f"OPENAI_API_KEY={existing_key}\nMCP_ENABLED=false\nOTHER=value\n"
            )
            (cursor_dir / "settings.json").write_text(
                json.dumps(
                    {
                        "cursor.ai.openaiApiKey": existing_key,
                        "mcp.servers": ["pulseplate-chatgpt"],
                    }
                )
            )

            with patch("pathlib.Path.home", return_value=temp_path):
                with patch("pathlib.Path.cwd", return_value=temp_path / "outside-repo"):
                    setup_custom_mcp.setup_custom_mcp(argv=["--force"])

            mcp_config = json.loads((cursor_dir / "mcp.json").read_text())
            pulseplate_server = mcp_config["mcpServers"]["pulseplate-chatgpt"]
            assert pulseplate_server["env"]["OPENAI_API_KEY"] == existing_key
            assert pulseplate_server["args"] == [str(setup_custom_mcp.MCP_SERVER_PATH)]

            env_lines = (cursor_dir / ".env").read_text().splitlines()
            assert f"OPENAI_API_KEY={existing_key}" in env_lines
            assert "MCP_ENABLED=true" in env_lines
            assert "OTHER=value" in env_lines

            settings = json.loads((cursor_dir / "settings.json").read_text())
            assert settings["cursor.ai.openaiApiKey"] == existing_key

    def test_setup_custom_mcp_does_not_promote_encrypted_env_key_to_runtime_configs(self):
        """Encrypted .env storage must not be copied into runtime MCP/settings surfaces."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            cursor_dir = temp_path / ".cursor"
            cursor_dir.mkdir(parents=True, exist_ok=True)
            encrypted_key = "encrypted:gAAAABexample"

            (cursor_dir / ".env").write_text(
                f"OPENAI_API_KEY={encrypted_key}\nMCP_ENABLED=false\nOTHER=value\n"
            )

            with patch("pathlib.Path.home", return_value=temp_path):
                with patch("pathlib.Path.cwd", return_value=temp_path / "outside-repo"):
                    setup_custom_mcp.setup_custom_mcp(argv=["--force"])

            mcp_config = json.loads((cursor_dir / "mcp.json").read_text())
            pulseplate_server = mcp_config["mcpServers"]["pulseplate-chatgpt"]
            assert (
                pulseplate_server["env"]["OPENAI_API_KEY"] == setup_custom_mcp.PLACEHOLDER_API_KEY
            )

            env_lines = (cursor_dir / ".env").read_text().splitlines()
            assert f"OPENAI_API_KEY={encrypted_key}" in env_lines
            assert "MCP_ENABLED=true" in env_lines
            assert "OTHER=value" in env_lines

            settings = json.loads((cursor_dir / "settings.json").read_text())
            assert settings["cursor.ai.openaiApiKey"] == setup_custom_mcp.PLACEHOLDER_API_KEY
