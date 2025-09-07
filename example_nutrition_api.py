#!/usr/bin/env python3
"""
Example usage of the Premium BMR/TDEE API

This script demonstrates how to use the new nutrition API endpoint
for calculating BMR and TDEE using multiple formulas.
"""

from typing import Any, Dict, Optional

import requests


def call_premium_bmr_api(
    weight_kg: float,
    height_cm: float,
    age: int,
    sex: str,
    activity: str,
    bodyfat: Optional[float] = None,
    lang: str = "en",
    api_key: str = "test_key",
    base_url: str = "http://localhost:8000",
) -> Dict[str, Any]:
    """
    Call the Premium BMR API endpoint.

    Args:
        weight_kg: Weight in kilograms
        height_cm: Height in centimeters
        age: Age in years
        sex: Biological sex ("male" or "female")
        activity: Activity level ("sedentary", "light", "moderate", "active", "very_active")
        bodyfat: Optional body fat percentage (for Katch-McArdle formula)
        lang: Response language ("en" or "ru")
        api_key: API key for authentication
        base_url: Base URL of the API server

    Returns:
        API response as dictionary
    """
    url = f"{base_url}/api/v1/premium/bmr"

    payload = {
        "weight_kg": weight_kg,
        "height_cm": height_cm,
        "age": age,
        "sex": sex,
        "activity": activity,
        "lang": lang,
    }

    if bodyfat is not None:
        payload["bodyfat"] = bodyfat

    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()

    return response.json()


def main():
    """
    Example usage scenarios.
    """
    print("🧬 Premium BMR/TDEE API Examples\n")

    # Example 1: Basic male calculation
    print("📊 Example 1: 30-year-old active male")
    print("-" * 40)

    try:
        result = call_premium_bmr_api(
            weight_kg=75,
            height_cm=180,
            age=30,
            sex="male",
            activity="active",
            lang="en",
        )

        print(f"BMR (Mifflin): {result['bmr']['mifflin']} kcal/day")
        print(f"BMR (Harris): {result['bmr']['harris']} kcal/day")
        print(f"TDEE (Mifflin): {result['tdee']['mifflin']} kcal/day")
        print(f"Activity: {result['activity_description']}")
        print(
            f"Maintenance calories: {result['recommended_intake']['maintenance']} kcal/day"
        )
        print(
            f"Weight loss calories: {result['recommended_intake']['weight_loss']} kcal/day"
        )
        print()

    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure the API server is running on localhost:8000\n")

    # Example 2: Female with body fat percentage
    print("📊 Example 2: 25-year-old female athlete with known body fat")
    print("-" * 55)

    try:
        result = call_premium_bmr_api(
            weight_kg=60,
            height_cm=165,
            age=25,
            sex="female",
            activity="very_active",
            bodyfat=18,  # Athletic female body fat
            lang="en",
        )

        print(f"BMR (Mifflin): {result['bmr']['mifflin']} kcal/day")
        print(f"BMR (Harris): {result['bmr']['harris']} kcal/day")
        print(f"BMR (Katch): {result['bmr']['katch']} kcal/day")
        print(f"TDEE (Katch): {result['tdee']['katch']} kcal/day")
        print(f"Activity: {result['activity_description']}")
        print()

    except Exception as e:
        print(f"❌ Error: {e}\n")

    # Example 3: Russian language response
    print("📊 Example 3: Response in Russian")
    print("-" * 30)

    try:
        result = call_premium_bmr_api(
            weight_kg=70,
            height_cm=175,
            age=35,
            sex="male",
            activity="moderate",
            lang="ru",
        )

        print(f"Описание активности: {result['activity_description']}")
        print(f"Рекомендации: {result['recommended_intake']['description']}")
        print(
            f"Поддержание веса: {result['recommended_intake']['maintenance']} ккал/день"
        )
        print()

    except Exception as e:
        print(f"❌ Error: {e}\n")

    # Example 4: Compare all activity levels
    print("📊 Example 4: Activity level comparison")
    print("-" * 35)

    activities = ["sedentary", "light", "moderate", "active", "very_active"]
    base_params = {
        "weight_kg": 70,
        "height_cm": 175,
        "age": 30,
        "sex": "male",
        "lang": "en",
    }

    print("Activity Level    | TDEE (Mifflin)")
    print("-" * 35)

    for activity in activities:
        try:
            result = call_premium_bmr_api(activity=activity, **base_params)
            tdee = result["tdee"]["mifflin"]
            print(f"{activity:<15} | {tdee} kcal/day")
        except Exception as e:
            print(f"{activity:<15} | Error: {e}")

    print("\n✨ Premium BMR/TDEE API provides comprehensive metabolic calculations!")
    print("💡 Use different formulas for different populations:")
    print("   • Mifflin-St Jeor: Most accurate for general population")
    print("   • Harris-Benedict: Traditional formula")
    print("   • Katch-McArdle: Best for athletes with known body fat %")


if __name__ == "__main__":
    main()
