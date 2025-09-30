#!/usr/bin/env python3
"""
Test script to verify OpenAI Pro access and available models
"""

# Import FastAPI app from the main module
try:
    from ..app import app
except ImportError:
    # Fallback for direct execution
    import sys
    import os

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # Import from the main app.py file directly
    import importlib.util

    spec = importlib.util.spec_from_file_location("app_module", "app.py")
    if spec is None or spec.loader is None:
        app = None
    else:
        app_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(app_module)
        app = app_module.app

import contextlib
import openai
import os
from typing import Any, Dict

# Define exception class aliases compatible with type checking
# Predeclare temporary holders with explicit types for static checkers
_TMP_AUTH_ERROR_CLS: type[BaseException]
_TMP_API_ERROR_CLS: type[BaseException]
try:
    # Prefer importing specific OpenAI exceptions if available
    from openai import AuthenticationError as _AuthenticationError, APIError as _APIError

    _TMP_AUTH_ERROR_CLS = _AuthenticationError
    _TMP_API_ERROR_CLS = _APIError
except ImportError:  # pragma: no cover - fallback for older clients
    # Define fallback classes to keep static types consistent
    class _AuthenticationErrorFallback(Exception):
        pass

    class _APIErrorFallback(Exception):
        pass

    _TMP_AUTH_ERROR_CLS = _AuthenticationErrorFallback
    _TMP_API_ERROR_CLS = _APIErrorFallback

# Final, single assignments (avoid redefinition warnings)
AUTH_ERROR_CLS: type[BaseException] = _TMP_AUTH_ERROR_CLS
API_ERROR_CLS: type[BaseException] = _TMP_API_ERROR_CLS


def test_openai_pro_access(api_key: str) -> Dict[str, Any]:
    """Test OpenAI Pro access and list available models"""
    try:
        client = openai.OpenAI(api_key=api_key)

        # Test API access
        models = client.models.list()
        available_models = [model.id for model in models.data]

        # Check for Pro models
        pro_models = {
            "gpt-5": "gpt-5" in available_models,
            "codex": any(
                model.startswith("code-davinci") or model.startswith("codex")
                for model in available_models
            ),
            "gpt-4": "gpt-4" in available_models,
            "gpt-3.5-turbo": "gpt-3.5-turbo" in available_models,
        }

        return {
            "status": "success",
            "available_models": available_models,
            "pro_models": pro_models,
            "total_models": len(available_models),
        }

    except AUTH_ERROR_CLS as e:  # auth-related failures
        return {
            "status": "error",
            "error": f"Authentication error: {e}",
            "available_models": [],
            "pro_models": {},
            "total_models": 0,
        }
    except API_ERROR_CLS as e:  # API failures (rate limits, server errors, etc.)
        return {
            "status": "error",
            "error": f"API error: {e}",
            "available_models": [],
            "pro_models": {},
            "total_models": 0,
        }
    except Exception as e:
        # Unexpected failure — log and return minimal safe payload
        # Note: logging module may not be configured in this context
        with contextlib.suppress(Exception):
            import logging

            logging.getLogger(__name__).exception("Unexpected OpenAI error")
        return {
            "status": "error",
            "error": f"Unexpected error: {e}",
            "available_models": [],
            "pro_models": {},
            "total_models": 0,
        }


def _is_valid_api_key(api_key: str) -> bool:
    """Validate the format of an API key."""
    return api_key.startswith("sk-") and 48 <= len(api_key) <= 51


def main():
    """Main function to test OpenAI Pro access"""
    print("🔍 Testing OpenAI Pro Access...")
    print("=" * 50)

    # Get API key from environment or input
    api_key = os.getenv("OPENAI_API_KEY") or input("Enter your OpenAI API key: ").strip()

    if not api_key:
        print("❌ No API key provided")
        return

    # Validate API key format
    if not _is_valid_api_key(api_key):
        print("❌ Invalid API key format")
        return

    # Test access
    result = test_openai_pro_access(api_key)

    print(f"Status: {result['status']}")
    print(f"Total models available: {result['total_models']}")

    if result["status"] == "success":
        print("\n✅ Pro Models Status:")
        for model, available in result["pro_models"].items():
            status = "✅ Available" if available else "❌ Not Available"
            print(f"  {model}: {status}")

        print(f"\n📋 All available models ({len(result['available_models'])}):")
        for model in sorted(result["available_models"]):
            print(f"  - {model}")
    else:
        print(f"❌ Error: {result['error']}")


if __name__ == "__main__":
    main()
