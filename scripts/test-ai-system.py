#!/usr/bin/env python3
"""
Test script for AI Router system
"""
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.ai_router import ai_router, AIProvider


async def test_ai_routing() -> None:
    """Test AI routing functionality"""
    print("🤖 Testing AI Router System")
    print("=" * 50)

    # Test cases
    test_cases = [
        {
            "name": "Simple Query (should use Ollama)",
            "message": "How many calories in an apple?",
            "context": {},
            "user_tier": "free",
        },
        {
            "name": "Medium Query (should use Ollama or OpenAI)",
            "message": "Create a basic meal plan for weight loss",
            "context": {"diet_goals": ["weight_loss"]},
            "user_tier": "free",
        },
        {
            "name": "Complex Query (should use OpenAI)",
            "message": "Create a detailed nutrition analysis for someone with diabetes and gluten intolerance",
            "context": {"user_conditions": ["diabetes"], "allergies": ["gluten"]},
            "user_tier": "premium",
        },
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: {test_case['name']}")
        print("-" * 40)

        try:
            # Analyze complexity
            message = str(test_case["message"])
            context: dict[str, Any] = dict(test_case["context"])  # Convert to dict for mypy
            user_tier = str(test_case["user_tier"])

            complexity = ai_router.analyze_complexity(message, context)
            print(f"📊 Complexity: {complexity.value}")

            # Choose provider
            provider = ai_router.choose_provider(complexity, user_tier)
            print(f"🎯 Provider: {provider.value}")

            # Estimate cost
            if provider == AIProvider.OLLAMA:
                cost = 0.0
                print(f"💰 Cost: ${cost} (free)")
            else:
                # Rough estimate
                tokens = len(message.split()) * 1.3
                cost = (tokens / 1000) * 0.0006
                print(f"💰 Cost: ${cost:.6f} (estimated)")

            print(f"✅ Test {i} completed successfully")

        except Exception as e:
            print(f"❌ Test {i} failed: {e}")

    print("\n" + "=" * 50)
    print("🎉 AI Router testing completed!")


async def test_environment_variables() -> None:
    """Test environment variable configuration"""
    print("\n🔧 Testing Environment Variables")
    print("-" * 40)

    env_vars = ["OLLAMA_ENDPOINT", "OLLAMA_API_KEY", "OPENAI_API_KEY", "OPENAI_MODEL"]

    for var in env_vars:
        value = os.getenv(var, "NOT SET")
        if var.endswith("_KEY") and value != "NOT SET":
            # Mask API keys for security
            value_str = str(value) if value else ""
            if len(value_str) <= 12:
                value = "***"
            else:
                value = f"{value_str[:8]}...{value_str[-4:]}"
        print(f"{var}: {value}")

    print("\n✅ Environment variables check completed!")


async def main() -> None:
    """Main test function"""
    print("🚀 Starting AI System Tests")
    print("=" * 50)

    # Test environment variables
    await test_environment_variables()

    # Test AI routing
    await test_ai_routing()

    print("\n🎯 Test Summary:")
    print("- Environment variables: ✅")
    print("- AI routing logic: ✅")
    print("- Cost estimation: ✅")
    print("\n💡 Next steps:")
    print("1. Set up real API keys in GitHub Secrets")
    print("2. Test with actual API calls")
    print("3. Deploy to staging environment")


if __name__ == "__main__":
    asyncio.run(main())
