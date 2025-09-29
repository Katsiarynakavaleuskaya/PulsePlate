#!/usr/bin/env python3
"""
Test script to verify OpenAI Pro access and available models
"""
import openai
import os
from typing import List, Dict


def test_openai_pro_access(api_key: str) -> Dict:
    """Test OpenAI Pro access and list available models"""
    try:
        client = openai.OpenAI(api_key=api_key)

        # Test API access
        models = client.models.list()
        available_models = [model.id for model in models.data]

        # Check for Pro models
        pro_models = {
            "gpt-5": "gpt-5" in available_models,
            "codex": any("codex" in model for model in available_models),
            "gpt-4": "gpt-4" in available_models,
            "gpt-3.5-turbo": "gpt-3.5-turbo" in available_models,
        }

        return {
            "status": "success",
            "available_models": available_models,
            "pro_models": pro_models,
            "total_models": len(available_models),
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "available_models": [],
            "pro_models": {},
            "total_models": 0,
        }


def main():
    """Main function to test OpenAI Pro access"""
    print("🔍 Testing OpenAI Pro Access...")
    print("=" * 50)

    # Get API key from environment or input
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        api_key = input("Enter your OpenAI API key: ").strip()

    if not api_key:
        print("❌ No API key provided")
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
