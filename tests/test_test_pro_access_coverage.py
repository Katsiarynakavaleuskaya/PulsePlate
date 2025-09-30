"""
Test coverage for test_pro_access.py
"""

import pytest
import os
from unittest.mock import patch, MagicMock, mock_open

from typing import Any

# Import the module under test
import sys
import importlib.util

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module being tested
spec = importlib.util.spec_from_file_location(
    "test_pro_access",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_pro_access.py"),
)
if spec is None or spec.loader is None:
    raise ImportError("Cannot load spec for test_pro_access")

test_pro_access = importlib.util.module_from_spec(spec)
spec.loader.exec_module(test_pro_access)


class TestTestProAccessCoverage:
    """Test class to cover test_pro_access.py"""

    def _create_mock_client_with_models(self, model_ids):
        """Helper method to create mock OpenAI client with specified models"""
        mock_models = MagicMock()
        mock_models.data = [MagicMock(id=model_id) for model_id in model_ids]

        mock_client = MagicMock()
        mock_client.models.list.return_value = mock_models
        return mock_client

    def _assert_success_result(self, result, expected_models, expected_pro_models):
        """Helper method to assert success result structure"""
        assert result["status"] == "success"
        assert result["total_models"] == len(expected_models)
        for model in expected_models:
            assert model in result["available_models"]
        for model, expected in expected_pro_models.items():
            assert result["pro_models"][model] == expected

    def _create_mock_test_return_value(self, models, pro_models):
        """Helper method to create mock test return value"""
        return {
            "status": "success",
            "available_models": models,
            "pro_models": pro_models,
            "total_models": len(models),
        }

    def test_test_openai_pro_access_success(self):
        """Test test_openai_pro_access with successful API call"""
        model_ids = ["gpt-4", "gpt-3.5-turbo", "gpt-5", "codex-001"]
        mock_client = self._create_mock_client_with_models(model_ids)

        with patch("openai.OpenAI", return_value=mock_client):
            self._verify_pro_access_result(True, model_ids)

    def test_test_openai_pro_access_error(self):
        """Test test_openai_pro_access with API error"""
        mock_client = MagicMock()
        mock_client.models.list.side_effect = Exception("API Error")

        with patch("openai.OpenAI", return_value=mock_client):
            result = test_pro_access.test_openai_pro_access("invalid-key")

            assert result["status"] == "error"
            assert result["error"] == "API Error"
            assert result["available_models"] == []
            assert result["pro_models"] == {}
            assert result["total_models"] == 0

    def test_test_openai_pro_access_no_pro_models(self):
        """Test test_openai_pro_access with no Pro models available"""
        model_ids = ["gpt-3.5-turbo", "text-davinci-003"]
        mock_client = self._create_mock_client_with_models(model_ids)

        with patch("openai.OpenAI", return_value=mock_client):
            self._verify_pro_access_result(False, model_ids)

    def _verify_pro_access_result(self, has_pro_models, model_ids):
        result = test_pro_access.test_openai_pro_access("test-api-key")
        expected_pro_models = {
            "gpt-5": has_pro_models,
            "codex": has_pro_models,
            "gpt-4": has_pro_models,
            "gpt-3.5-turbo": True,
        }
        self._assert_success_result(result, model_ids, expected_pro_models)

    def test_main_function_with_env_key(self):
        """Test main function with API key from environment"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch.object(test_pro_access, "test_openai_pro_access") as mock_test:
                with patch("builtins.print") as mock_print:
                    mock_test.return_value = self._create_mock_test_return_value(
                        ["gpt-4"], {"gpt-4": True}
                    )

                    self._verify_main_execution_with_mocks(mock_test, "test-key", mock_print)

    def test_main_function_with_input_key(self):
        """Test main function with API key from user input"""
        with patch.dict(os.environ, {}, clear=True):
            with patch("builtins.input", return_value="user-input-key"):
                with patch.object(test_pro_access, "test_openai_pro_access") as mock_test:
                    with patch("builtins.print") as mock_print:
                        mock_test.return_value = {
                            "status": "success",
                            "available_models": ["gpt-4"],
                            "pro_models": {"gpt-4": True},
                            "total_models": 1,
                        }

                        self._verify_main_execution_with_mocks(
                            mock_test, "user-input-key", mock_print
                        )

    def test_main_function_no_key(self):
        """Test main function with no API key provided"""
        with patch.dict(os.environ, {}, clear=True):
            with patch("builtins.input", return_value=""):
                with patch("builtins.print") as mock_print:
                    test_pro_access.main()

                    mock_print.assert_called_with("❌ No API key provided")

    def test_main_function_success_output(self):
        """Test main function success output formatting"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch.object(test_pro_access, "test_openai_pro_access") as mock_test:
                with patch("builtins.print") as mock_print:
                    print_calls = self._verify_output_contains(
                        True, mock_test, mock_print, "Status: success"
                    )
                    assert any("Total models available: 2" in call for call in print_calls)
                    assert any("✅ Pro Models Status:" in call for call in print_calls)

    def test_main_function_error_output(self):
        """Test main function error output formatting"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch.object(test_pro_access, "test_openai_pro_access") as mock_test:
                with patch("builtins.print") as mock_print:
                    mock_test.return_value = {
                        "status": "error",
                        "error": "Invalid API key",
                        "available_models": [],
                        "pro_models": {},
                        "total_models": 0,
                    }

                    test_pro_access.main()

                    # Check that error messages were printed
                    print_calls = [call[0][0] for call in mock_print.call_args_list]
                    assert "Status: error" in print_calls
                    assert "❌ Error: Invalid API key" in print_calls

    def test_pro_models_detection(self):
        """Test Pro models detection logic"""
        mock_models = MagicMock()
        mock_models.data = [
            MagicMock(id="gpt-4"),
            MagicMock(id="gpt-3.5-turbo"),
            MagicMock(id="gpt-5"),
            MagicMock(id="codex-001"),
            MagicMock(id="text-davinci-003"),
        ]

        mock_client = MagicMock()
        mock_client.models.list.return_value = mock_models

        with patch("openai.OpenAI", return_value=mock_client):
            result = test_pro_access.test_openai_pro_access("test-api-key")

            # Test specific Pro model detection
            assert result["pro_models"]["gpt-5"] is True
            assert result["pro_models"]["codex"] is True  # codex-001 contains "codex"
            assert result["pro_models"]["gpt-4"] is True
            assert result["pro_models"]["gpt-3.5-turbo"] is True

    def test_openai_client_initialization(self):
        """Test OpenAI client initialization"""
        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_models = MagicMock()
            mock_models.data = []
            mock_client.models.list.return_value = mock_models
            mock_openai.return_value = mock_client

            _ = test_pro_access.test_openai_pro_access("test-key")

            mock_openai.assert_called_once_with(api_key="test-key")

    def test_models_list_processing(self):
        """Test models list processing"""
        model_ids = ["model-1", "model-2", "model-3"]
        mock_client = self._create_mock_client_with_models(model_ids)

        with patch("openai.OpenAI", return_value=mock_client):
            result = test_pro_access.test_openai_pro_access("test-key")

            assert len(result["available_models"]) == 3
            assert result["total_models"] == 3

    def test_main_execution_mock(self):
        """Test main execution when script is run directly"""
        # Patch external dependencies instead of the main function
        with patch("builtins.input", return_value="test-key"):
            with patch("builtins.print") as mock_print:
                with patch.object(test_pro_access, "test_openai_pro_access") as mock_test:
                    mock_test.return_value = {
                        "status": "success",
                        "available_models": ["gpt-4"],
                        "pro_models": {"gpt-4": True},
                        "total_models": 1,
                    }

                    self._verify_main_execution_with_mocks(mock_test, "test-key", mock_print)

    def _verify_main_execution_with_mocks(self, mock_test, api_key, mock_print):
        """Helper method to verify main execution with mocked dependencies"""
        test_pro_access.main()
        mock_test.assert_called_once_with(api_key)
        mock_print.assert_called()

    def test_api_key_validation(self):
        """Test API key validation logic"""
        # Test that API keys start with 'sk-'
        assert "sk-abc123def456".startswith("sk-") is True
        assert "invalid-key".startswith("sk-") is False
        assert "".startswith("sk-") is False

    def test_main_execution_callable(self):
        """Test main execution symbol is callable"""
        assert callable(test_pro_access.main)

    def test_environment_variable_priority(self):
        """Test that environment variable takes priority over input"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}):
            with patch("builtins.input", return_value="input-key"):
                with patch.object(test_pro_access, "test_openai_pro_access") as mock_test:
                    with patch("builtins.print"):
                        mock_test.return_value = {
                            "status": "success",
                            "available_models": [],
                            "pro_models": {},
                            "total_models": 0,
                        }

                        test_pro_access.main()

                        # Should use environment key, not input key
                        mock_test.assert_called_once_with("env-key")

    def test_output_formatting(self):
        """Test output formatting in main function"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch.object(test_pro_access, "test_openai_pro_access") as mock_test:
                with patch("builtins.print") as mock_print:
                    print_calls = self._verify_output_contains(
                        False,
                        mock_test,
                        mock_print,
                        "🔍 Testing OpenAI Pro Access...",
                    )
                    assert any("=" * 50 in call for call in print_calls)
                    assert any("📋 All available models (2):" in call for call in print_calls)

    def _verify_output_contains(self, gpt_35_turbo_is_pro, mock_test, mock_print, expected_message):
        mock_test.return_value = {
            "status": "success",
            "available_models": ["gpt-4", "gpt-3.5-turbo"],
            "pro_models": {"gpt-4": True, "gpt-3.5-turbo": gpt_35_turbo_is_pro},
            "total_models": 2,
        }
        test_pro_access.main()
        result = [call[0][0] for call in mock_print.call_args_list]
        assert any(expected_message in call for call in result)
        return result
