"""
Test coverage for mcp_pulseplate_server.py
"""

import json
import os
import sys
from unittest.mock import MagicMock, mock_open, patch

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mcp_pulseplate_server


@pytest.fixture(autouse=True)
def mock_openai_models_fetch():
    """Automatically mock _fetch_available_models for all MCP server tests.

    This prevents API calls during tests and ensures consistent behavior.
    Tests run in CI without OPENAI_API_KEY will use fallback model list.
    """
    # Mock the class method to always return fallback list
    with patch.object(
        mcp_pulseplate_server.PulsePlateMCPServer,
        "_fetch_available_models",
        return_value=mcp_pulseplate_server.PulsePlateMCPServer.FALLBACK_ALLOWED_MODELS,
    ):
        yield


class TestMcpPulseplateServerCoverage:
    """Test class to cover mcp_pulseplate_server.py"""

    def test_pulseplate_mcp_server_init_success(self):
        """Test PulsePlateMCPServer initialization with valid API key"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client

                server = mcp_pulseplate_server.PulsePlateMCPServer()

                assert server.api_key == "test-key"
                assert server.client == mock_client
                assert server.project_context is not None
                assert "project_name" in server.project_context
                assert server.project_context["project_name"] == "PulsePlate"

    def test_pulseplate_mcp_server_init_no_api_key(self):
        """Test PulsePlateMCPServer initialization without API key"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OPENAI_API_KEY environment variable not set"):
                _ = mcp_pulseplate_server.PulsePlateMCPServer()

    def test_pulseplate_mcp_server_default_model(self) -> None:
        """Test PulsePlateMCPServer uses default model when MCP_OPENAI_MODEL is unset"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            with patch("openai.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client

                server = mcp_pulseplate_server.PulsePlateMCPServer()

                # Verify default model is "gpt-4o" (updated from "gpt-4")
                assert server.model == "gpt-4o"
                assert server.model == mcp_pulseplate_server.PulsePlateMCPServer.DEFAULT_MODEL

    def test_pulseplate_mcp_server_custom_model(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test PulsePlateMCPServer accepts custom model via MCP_OPENAI_MODEL"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("MCP_OPENAI_MODEL", "gpt-4o-mini")

        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            server = mcp_pulseplate_server.PulsePlateMCPServer()

            # Verify custom model is set
            assert server.model == "gpt-4o-mini"

    def test_pulseplate_mcp_server_empty_model_uses_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test PulsePlateMCPServer falls back to DEFAULT_MODEL when empty model string is set.

        Empty string is a valid fallback case that correctly uses DEFAULT_MODEL.
        """
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("MCP_OPENAI_MODEL", "")

        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            server = mcp_pulseplate_server.PulsePlateMCPServer()

            # Empty string should fall back to DEFAULT_MODEL ("gpt-4o")
            assert server.model == "gpt-4o"
            assert server.model == mcp_pulseplate_server.PulsePlateMCPServer.DEFAULT_MODEL

    def test_pulseplate_mcp_server_invalid_model_whitespace(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test PulsePlateMCPServer treats whitespace-only model as fallback to DEFAULT_MODEL"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("MCP_OPENAI_MODEL", "   ")

        with patch("openai.OpenAI"):
            server = mcp_pulseplate_server.PulsePlateMCPServer()
            # Whitespace-only should fallback to DEFAULT_MODEL
            assert server.model == mcp_pulseplate_server.PulsePlateMCPServer.DEFAULT_MODEL

    def test_pulseplate_mcp_server_invalid_model_not_in_whitelist(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test PulsePlateMCPServer raises ValueError for models not in whitelist"""
        invalid_models = [
            "gpt-6",  # Future model not yet released
            "invalid-model",
            "gpt-4-custom",
            "gpt-4-0613",  # Specific dated version not in whitelist
            "claude-3",  # Different provider
        ]

        for invalid_model in invalid_models:
            monkeypatch.setenv("OPENAI_API_KEY", "test-key")
            monkeypatch.setenv("MCP_OPENAI_MODEL", invalid_model)

            with patch("openai.OpenAI"):
                with pytest.raises(ValueError, match=r"Unknown model:.*Available models:"):
                    _ = mcp_pulseplate_server.PulsePlateMCPServer()

            monkeypatch.delenv("MCP_OPENAI_MODEL", raising=False)

    def test_pulseplate_mcp_server_class_constants(self) -> None:
        """Test PulsePlateMCPServer class constants are properly defined"""
        # Verify DEFAULT_MODEL constant
        assert hasattr(mcp_pulseplate_server.PulsePlateMCPServer, "DEFAULT_MODEL")
        assert mcp_pulseplate_server.PulsePlateMCPServer.DEFAULT_MODEL == "gpt-4o"
        assert isinstance(mcp_pulseplate_server.PulsePlateMCPServer.DEFAULT_MODEL, str)

        # Verify FALLBACK_ALLOWED_MODELS constant
        assert hasattr(mcp_pulseplate_server.PulsePlateMCPServer, "FALLBACK_ALLOWED_MODELS")
        allowed = mcp_pulseplate_server.PulsePlateMCPServer.FALLBACK_ALLOWED_MODELS
        assert isinstance(allowed, set)
        assert len(allowed) > 0

        # Verify default model is in allowed models
        assert mcp_pulseplate_server.PulsePlateMCPServer.DEFAULT_MODEL in allowed

        # Verify expected models are in whitelist
        expected_models = {
            "gpt-4o",
            "gpt-4o-mini",
            "o1",
            "o3",
            "o3-mini",
        }
        assert expected_models.issubset(allowed)

    def test_pulseplate_mcp_server_whitelist_validation_message(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that whitelist validation provides helpful error messages"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("MCP_OPENAI_MODEL", "invalid-model-xyz")

        # Mock _fetch_available_models to return fallback list
        with patch.object(
            mcp_pulseplate_server.PulsePlateMCPServer,
            "_fetch_available_models",
            return_value=mcp_pulseplate_server.PulsePlateMCPServer.FALLBACK_ALLOWED_MODELS,
        ):
            with patch("openai.OpenAI"):
                with pytest.raises(ValueError) as exc_info:
                    _ = mcp_pulseplate_server.PulsePlateMCPServer()

                error_message = str(exc_info.value)
                # Verify error message contains helpful information
                assert "Unknown model" in error_message
                assert "invalid-model-xyz" in error_message
                assert "Available models" in error_message
                # Verify at least one allowed model is mentioned
                assert any(
                    model in error_message
                    for model in mcp_pulseplate_server.PulsePlateMCPServer.FALLBACK_ALLOWED_MODELS
                )

    def test_pulseplate_mcp_server_valid_custom_models(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test PulsePlateMCPServer accepts various valid custom model names from whitelist"""
        # Test models from the FALLBACK_ALLOWED_MODELS whitelist
        valid_models = ["gpt-4o", "gpt-4o-mini", "o1", "o3", "o3-mini"]

        for model_name in valid_models:
            monkeypatch.setenv("OPENAI_API_KEY", "test-key")
            monkeypatch.setenv("MCP_OPENAI_MODEL", model_name)

            # Mock _fetch_available_models to return fallback list
            with patch.object(
                mcp_pulseplate_server.PulsePlateMCPServer,
                "_fetch_available_models",
                return_value=mcp_pulseplate_server.PulsePlateMCPServer.FALLBACK_ALLOWED_MODELS,
            ):
                with patch("openai.OpenAI") as mock_openai:
                    mock_client = MagicMock()
                    mock_openai.return_value = mock_client

                    server = mcp_pulseplate_server.PulsePlateMCPServer()

                    # Verify each custom model is accepted
                    assert server.model == model_name
                    # Verify model is in whitelist
                    assert (
                        model_name
                        in mcp_pulseplate_server.PulsePlateMCPServer.FALLBACK_ALLOWED_MODELS
                    )

            # Clean up for next iteration
            monkeypatch.delenv("MCP_OPENAI_MODEL", raising=False)

    @pytest.mark.asyncio
    async def test_custom_model_passed_to_api(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that custom model is passed to OpenAI API calls"""
        custom_model = "gpt-4o-mini"  # Use valid model from whitelist
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("MCP_OPENAI_MODEL", custom_model)

        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Test response"
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            server = mcp_pulseplate_server.PulsePlateMCPServer()

            # Call a method that uses the model
            args = {"query": "test query", "context": "test context"}
            await server._chatgpt_query(args)

            # Verify the custom model was passed to the API
            call_args = mock_client.chat.completions.create.call_args
            assert call_args[1]["model"] == custom_model

    def test_load_project_context(self) -> None:
        """Test _load_project_context method"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI"):
                server = mcp_pulseplate_server.PulsePlateMCPServer()
                context = server._load_project_context()  # noqa: SLF001

                assert isinstance(context, dict)
                assert context["project_name"] == "PulsePlate"
                assert "description" in context
                assert "tech_stack" in context
                assert "key_features" in context
                assert "architecture" in context
                assert isinstance(context["key_features"], list)
                assert len(context["key_features"]) > 0

    @pytest.mark.asyncio
    async def test_handle_request_tools_list(self) -> None:
        """Test handle_request with tools/list method"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI"):
                server = mcp_pulseplate_server.PulsePlateMCPServer()

                request = {"method": "tools/list"}
                response = await server.handle_request(request)

                assert "tools" in response
                assert isinstance(response["tools"], list)
                assert len(response["tools"]) > 0

    @pytest.mark.asyncio
    async def test_handle_request_tools_call(self):
        """Test handle_request with tools/call method"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI"):
                server = mcp_pulseplate_server.PulsePlateMCPServer()

                request = {
                    "method": "tools/call",
                    "params": {"name": "chatgpt_query", "arguments": {"query": "test query"}},
                }

                with patch.object(server, "_call_tool") as mock_call_tool:
                    mock_call_tool.return_value = {"result": "test"}
                    _ = await server.handle_request(request)

                    mock_call_tool.assert_called_once_with(request["params"])

    @pytest.mark.asyncio
    async def test_handle_request_unknown_method(self):
        """Test handle_request with unknown method"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI"):
                server = mcp_pulseplate_server.PulsePlateMCPServer()

                request = {"method": "unknown_method"}
                response = await server.handle_request(request)

                assert "error" in response
                assert "Unknown method: unknown_method" in response["error"]

    @pytest.mark.asyncio
    async def test_handle_request_exception(self):
        """Test handle_request with exception"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI"):
                server = mcp_pulseplate_server.PulsePlateMCPServer()

                # Mock a method that raises an exception
                with patch.object(server, "_list_tools", side_effect=Exception("Test error")):
                    request = {"method": "tools/list"}
                    response = await server.handle_request(request)

                    assert "error" in response
                    assert "Test error" in response["error"]

    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test _list_tools method"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI"):
                server = mcp_pulseplate_server.PulsePlateMCPServer()

                response = await server._list_tools()

                assert "tools" in response
                assert isinstance(response["tools"], list)
                assert len(response["tools"]) >= 3  # chatgpt_query, code_review, generate_code

                # Check tool structure
                for tool in response["tools"]:
                    assert "name" in tool
                    assert "description" in tool
                    assert "inputSchema" in tool

    @pytest.mark.asyncio
    async def test_call_tool_chatgpt_query(self):
        """Test _call_tool with chatgpt_query"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI"):
                server = mcp_pulseplate_server.PulsePlateMCPServer()

                params = {
                    "name": "chatgpt_query",
                    "arguments": {"query": "test query", "context": "test context"},
                }

                with patch.object(server, "_chatgpt_query") as mock_chatgpt:
                    mock_chatgpt.return_value = {"result": "test response"}
                    _ = await server._call_tool(params)

                    mock_chatgpt.assert_called_once_with(params["arguments"])

    @pytest.mark.asyncio
    async def test_call_tool_code_review(self):
        """Test _call_tool with code_review"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI"):
                server = mcp_pulseplate_server.PulsePlateMCPServer()

                params = {
                    "name": "code_review",
                    "arguments": {"code": "print('hello')", "language": "python"},
                }

                with patch.object(server, "_code_review") as mock_review:
                    mock_review.return_value = {"result": "review response"}
                    _ = await server._call_tool(params)

                    mock_review.assert_called_once_with(params["arguments"])

    @pytest.mark.asyncio
    async def test_call_tool_generate_code(self):
        """Test _call_tool with generate_code"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI"):
                server = mcp_pulseplate_server.PulsePlateMCPServer()

                params = {
                    "name": "generate_code",
                    "arguments": {"description": "create a function", "language": "python"},
                }

                with patch.object(server, "_generate_code") as mock_generate:
                    mock_generate.return_value = {"result": "generated code"}
                    _ = await server._call_tool(params)

                    mock_generate.assert_called_once_with(params["arguments"])

    @pytest.mark.asyncio
    async def test_call_tool_unknown_tool(self):
        """Test _call_tool with unknown tool"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI"):
                server = mcp_pulseplate_server.PulsePlateMCPServer()

                params = {"name": "unknown_tool", "arguments": {}}

                response = await server._call_tool(params)

                assert "error" in response
                assert "Unknown tool: unknown_tool" in response["error"]

    @pytest.mark.asyncio
    async def test_chatgpt_query_success(self):
        """Test _chatgpt_query with successful API call"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "Test response"
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client

                server = mcp_pulseplate_server.PulsePlateMCPServer()

                args = {"query": "test query", "context": "test context"}
                response = await server._chatgpt_query(args)

                assert "content" in response
                assert isinstance(response["content"], list)
                assert response["content"][0]["type"] == "text"
                assert response["content"][0]["text"] == "Test response"

    @pytest.mark.asyncio
    async def test_chatgpt_query_error(self):
        """Test _chatgpt_query with API error"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_client.chat.completions.create.side_effect = Exception("API Error")
                mock_openai.return_value = mock_client

                server = mcp_pulseplate_server.PulsePlateMCPServer()

                args = {"query": "test query"}
                response = await server._chatgpt_query(args)

                assert "error" in response
                assert "ChatGPT query failed: API Error" in response["error"]

    @pytest.mark.asyncio
    async def test_code_review_success(self):
        """Test _code_review with successful API call"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "Code review response"
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client

                server = mcp_pulseplate_server.PulsePlateMCPServer()

                args = {"code": "print('hello')", "language": "python"}
                response = await server._code_review(args)

                assert "content" in response
                assert response["content"][0]["text"] == "Code review response"

    @pytest.mark.asyncio
    async def test_code_review_error(self):
        """Test _code_review with API error"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_client.chat.completions.create.side_effect = Exception("API Error")
                mock_openai.return_value = mock_client

                server = mcp_pulseplate_server.PulsePlateMCPServer()

                args = {"code": "print('hello')"}
                response = await server._code_review(args)

                assert "error" in response
                assert "Code review failed: API Error" in response["error"]

    @pytest.mark.asyncio
    async def test_generate_code_success(self):
        """Test _generate_code with successful API call"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "Generated code"
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client

                server = mcp_pulseplate_server.PulsePlateMCPServer()

                args = {"description": "create a function", "language": "python"}
                response = await server._generate_code(args)

                assert "content" in response
                assert response["content"][0]["text"] == "Generated code"

    @pytest.mark.asyncio
    async def test_generate_code_error(self):
        """Test _generate_code with API error"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_client.chat.completions.create.side_effect = Exception("API Error")
                mock_openai.return_value = mock_client

                server = mcp_pulseplate_server.PulsePlateMCPServer()

                args = {"description": "create a function"}
                response = await server._generate_code(args)

                assert "error" in response
                assert "Code generation failed: API Error" in response["error"]

    @pytest.mark.asyncio
    async def test_main_function_success(self):
        """Test main function with successful request"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI"):
                with patch("sys.stdin.readline") as mock_readline:
                    with patch("builtins.print") as mock_print:
                        with patch("sys.stdout.flush") as mock_flush:
                            mock_readline.side_effect = [
                                '{"method": "tools/list"}\n',
                                "",  # Empty line to break the loop
                            ]

                            await mcp_pulseplate_server.main()

                            mock_print.assert_called()
                            mock_flush.assert_called()

    @pytest.mark.asyncio
    async def test_main_function_json_error(self):
        """Test main function with JSON parsing error"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI"):
                with patch("sys.stdin.readline") as mock_readline:
                    with patch("builtins.print") as mock_print:
                        with patch("sys.stdout.flush") as mock_flush:
                            mock_readline.side_effect = [
                                "invalid json\n",
                                "",  # Empty line to break the loop
                            ]

                            await mcp_pulseplate_server.main()

                            # Should print error response
                            mock_print.assert_called()
                            mock_flush.assert_called()

    @pytest.mark.asyncio
    async def test_main_function_exception(self):
        """Test main function with general exception"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI"):
                with patch("sys.stdin.readline") as mock_readline:
                    with patch("builtins.print") as mock_print:
                        with patch("sys.stdout.flush") as mock_flush:
                            mock_readline.side_effect = [
                                '{"method": "tools/list"}\n',
                                "",  # Empty line to break the loop
                            ]

                            # Mock handle_request to raise exception
                            with patch.object(
                                mcp_pulseplate_server.PulsePlateMCPServer,
                                "handle_request",
                                side_effect=Exception("Test error"),
                            ):
                                await mcp_pulseplate_server.main()

                                mock_print.assert_called()
                                mock_flush.assert_called()

    def test_main_execution(self):
        """Test main execution when script is run directly"""
        # Test that main function exists and is callable
        assert callable(mcp_pulseplate_server.main)

        # Test that main function is async
        import asyncio

        assert asyncio.iscoroutinefunction(mcp_pulseplate_server.main)

    def test_project_context_structure(self):
        """Test project context structure and content"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI"):
                server = mcp_pulseplate_server.PulsePlateMCPServer()
                context = server.project_context

                # Test required fields
                assert "project_name" in context
                assert "description" in context
                assert "tech_stack" in context
                assert "key_features" in context
                assert "architecture" in context

                # Test tech_stack structure
                tech_stack = context["tech_stack"]
                assert "backend" in tech_stack
                assert "frontend" in tech_stack
                assert "testing" in tech_stack

                # Test key_features
                features = context["key_features"]
                assert isinstance(features, list)
                assert len(features) > 0
                assert any("BMI" in feature for feature in features)

                # Test architecture
                architecture = context["architecture"]
                assert "backend" in architecture
                assert "frontend" in architecture
                assert "database" in architecture
                assert "integrations" in architecture

    @pytest.mark.asyncio
    async def test_chatgpt_query_prompt_building(self) -> None:
        """Test ChatGPT query prompt building"""
        with patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "test-key", "MCP_OPENAI_MODEL": ""},
            clear=True,
        ):
            with patch("openai.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "Test response"
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client

                server = mcp_pulseplate_server.PulsePlateMCPServer()

                args = {"query": "How to implement BMI calculation?", "context": "FastAPI backend"}
                await server._chatgpt_query(args)

                # Verify the API was called with proper parameters
                mock_client.chat.completions.create.assert_called_once()
                call_args = mock_client.chat.completions.create.call_args

                assert (
                    call_args[1]["model"] == mcp_pulseplate_server.PulsePlateMCPServer.DEFAULT_MODEL
                )
                assert call_args[1]["max_tokens"] == 1000
                assert call_args[1]["temperature"] == 0.7
                assert len(call_args[1]["messages"]) == 2
                assert call_args[1]["messages"][0]["role"] == "system"
                assert call_args[1]["messages"][1]["role"] == "user"

    @pytest.mark.asyncio
    async def test_code_review_prompt_building(self) -> None:
        """Test code review prompt building"""
        with patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "test-key", "MCP_OPENAI_MODEL": ""},
            clear=True,
        ):
            with patch("openai.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "Review response"
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client

                server = mcp_pulseplate_server.PulsePlateMCPServer()

                args = {
                    "code": "def calculate_bmi(weight, height): return weight / (height ** 2)",
                    "language": "python",
                }
                await server._code_review(args)

                # Verify the API was called with proper parameters
                call_args = mock_client.chat.completions.create.call_args
                assert (
                    call_args[1]["model"] == mcp_pulseplate_server.PulsePlateMCPServer.DEFAULT_MODEL
                )
                assert call_args[1]["max_tokens"] == 1500
                assert call_args[1]["temperature"] == 0.3

    @pytest.mark.asyncio
    async def test_generate_code_prompt_building(self) -> None:
        """Test code generation prompt building"""
        with patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "test-key", "MCP_OPENAI_MODEL": ""},
            clear=True,
        ):
            with patch("openai.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "Generated code"
                mock_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_client

                server = mcp_pulseplate_server.PulsePlateMCPServer()

                args = {"description": "Create a BMI calculation function", "language": "python"}
                await server._generate_code(args)

                # Verify the API was called with proper parameters
                call_args = mock_client.chat.completions.create.call_args
                assert (
                    call_args[1]["model"] == mcp_pulseplate_server.PulsePlateMCPServer.DEFAULT_MODEL
                )
                assert call_args[1]["max_tokens"] == 2000
                assert call_args[1]["temperature"] == 0.5
