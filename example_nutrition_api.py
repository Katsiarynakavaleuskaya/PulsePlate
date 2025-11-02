#!/usr/bin/env python3
# pyright: reportMissingTypeStubs=false
"""
Example usage of the Premium BMR/TDEE API

This script demonstrates how to use the new nutrition API endpoint
for calculating BMR and TDEE using multiple formulas.
"""

from typing import Any, Dict, Optional

import requests  # type: ignore

from app import BMRResponse
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)


def _should_retry_http_error(exception: BaseException) -> bool:
    """
    Determine if an HTTP error should be retried.

    Retries on 5xx server errors (transient) but not 4xx client errors (permanent).
    """
    if isinstance(exception, requests.exceptions.HTTPError) and exception.response is not None:
        status_code = exception.response.status_code
        # Retry on 5xx server errors (transient failures)
        # Don't retry on 4xx client errors (bad request, auth issues, etc.)
        return isinstance(status_code, int) and 500 <= status_code < 600
    return False


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=(
        retry_if_exception_type(
            (
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
                requests.exceptions.ConnectTimeout,
                requests.exceptions.ReadTimeout,
            )
        )
        | retry_if_exception(_should_retry_http_error)
    ),
    reraise=True,
)
def _make_post_request(
    url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: float
) -> requests.Response:
    """
    Make a POST request with retry logic for transient failures.

    This function handles:
    - Timeouts (ConnectionTimeout, ReadTimeout)
    - Connection errors (network failures, DNS issues)
    - HTTP 5xx server errors (transient server failures)

    Args:
        url: Target URL
        payload: JSON payload to send
        headers: HTTP headers
        timeout: Request timeout in seconds

    Returns:
        Response object

    Raises:
        requests.exceptions.Timeout: If all retry attempts timeout
        requests.exceptions.ConnectionError: If all retry attempts fail to connect
        requests.exceptions.HTTPError: If API returns a non-retryable error or all retries exhausted
    """
    response = requests.post(url, json=payload, headers=headers, timeout=timeout)
    # raise_for_status will raise HTTPError for 4xx/5xx, which triggers retry logic for 5xx
    response.raise_for_status()
    return response


def call_premium_bmr_api(
    weight_kg: float,
    height_cm: float,
    age: int,
    sex: str,
    activity: str,
    bodyfat: Optional[float] = None,
    lang: str = "en",
    api_key: str = "test_key",  # nosec B105  # Test key for example/demo purposes only
    base_url: str = "http://localhost:8000",
    timeout: float = 10.0,
) -> BMRResponse:
    """
    Call the Premium BMR API endpoint with automatic retry for transient failures.

    Automatically retries on:
    - Timeout errors (with exponential backoff: 1s, 2s, 4s, up to 10s max)
    - Connection errors (network failures, DNS issues)
    - HTTP 5xx server errors (transient server failures)

    Up to 3 attempts total (initial + 2 retries) with exponential backoff between attempts.

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
        timeout: Request timeout in seconds per attempt

    Returns:
        Validated BMRResponse model instance with BMR, TDEE, and recommendations

    Note:
        The returned BMRResponse is a Pydantic BaseModel. Use attribute access
        (result.bmr, result.tdee, result.activity_level) instead of dict-style indexing.

    Raises:
        requests.exceptions.Timeout: If all retry attempts timeout
        requests.exceptions.HTTPError: If the API returns a non-retryable error (4xx) or all retries exhausted
        requests.exceptions.ConnectionError: If all retry attempts fail to connect
        requests.exceptions.RequestException: Base class for other request-related errors from requests
    """
    url = f"{base_url}/api/v1/premium/bmr"

    payload: Dict[str, Any] = {
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

    response = _make_post_request(url, payload, headers, timeout)

    # Validate and parse JSON response using Pydantic model
    return BMRResponse.model_validate(response.json())


def handle_request_errors(exception: Exception, lang: str = "en") -> None:
    """
    Handle and print error messages for API request exceptions.

    Args:
        exception: The exception that was raised
        lang: Language for error messages ("en" or "ru")
    """
    if isinstance(exception, requests.exceptions.Timeout):
        if lang == "ru":
            print(f"⏱️ Таймаут: {exception}\n")
        else:
            print(f"⏱️ Timeout: {exception}")
            print("Try increasing timeout (e.g., timeout=10.0) and ensure server responsiveness.\n")
    elif isinstance(exception, requests.exceptions.HTTPError):
        if lang == "ru":
            print(f"❌ HTTP-ошибка: {exception}\n")
        else:
            print(f"❌ HTTP error: {exception}")
            print("The API returned an error status code. Check server logs.\n")
    elif isinstance(exception, requests.exceptions.ConnectionError):
        if lang == "ru":
            print(f"🔌 Ошибка соединения: {exception}\n")
        else:
            print(f"🔌 Connection error: {exception}")
            print("Make sure the API server is running on localhost:8000 and reachable.\n")
    elif isinstance(exception, requests.exceptions.RequestException):
        if lang == "ru":
            print(f"⚠️ Ошибка запроса: {exception}\n")
        else:
            print(f"⚠️ Request error: {exception}\n")
    else:
        if lang == "ru":
            print(f"❌ Непредвиденная ошибка: {exception}\n")
        else:
            print(f"❌ Unexpected error: {exception}\n")


def handle_request_errors_detailed(exception: Exception) -> None:
    """
    Handle and print detailed error messages for API request exceptions.

    Args:
        exception: The exception that was raised
    """
    if isinstance(exception, requests.exceptions.Timeout):
        print("⏱️ Request timed out. Try increasing timeout (e.g., timeout=10.0).")
        print(f"Details: {exception}\n")
    elif isinstance(exception, requests.exceptions.HTTPError):
        print("❌ HTTP error occurred. Check server response status.")
        print(f"Details: {exception}\n")
    elif isinstance(exception, requests.exceptions.ConnectionError):
        print("🔌 Connection error. Is the server running and reachable?")
        print(f"Details: {exception}\n")
    elif isinstance(exception, requests.exceptions.RequestException):
        print("⚠️ Request error occurred.")
        print(f"Details: {exception}\n")
    else:
        print("❌ Unexpected error.")
        print(f"Details: {exception}\n")


def handle_request_errors_inline(exception: Exception, activity: str) -> None:
    """
    Handle and print inline error messages for API request exceptions.

    Args:
        exception: The exception that was raised
        activity: Activity level string for display
    """
    if isinstance(exception, requests.exceptions.Timeout):
        print(f"{activity:<15} | Timeout: {exception}")
    elif isinstance(exception, requests.exceptions.HTTPError):
        print(f"{activity:<15} | HTTP error: {exception}")
    elif isinstance(exception, requests.exceptions.ConnectionError):
        print(f"{activity:<15} | Connection error: {exception}")
    elif isinstance(exception, requests.exceptions.RequestException):
        print(f"{activity:<15} | Request error: {exception}")
    else:
        print(f"{activity:<15} | Unexpected error: {exception}")


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

        print(f"BMR (Mifflin): {result.bmr['mifflin']} kcal/day")
        print(f"BMR (Harris): {result.bmr['harris']} kcal/day")
        print(f"TDEE (Mifflin): {result.tdee['mifflin']} kcal/day")
        print(f"Activity: {result.activity_level}")
        print(f"Maintenance calories: {result.recommended_intake['maintenance']} kcal/day")
        print(f"Weight loss calories: {result.recommended_intake['weight_loss']} kcal/day")
        print()

    except Exception as e:
        handle_request_errors(e, lang="en")

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

        print(f"BMR (Mifflin): {result.bmr['mifflin']} kcal/day")
        print(f"BMR (Harris): {result.bmr['harris']} kcal/day")
        print(f"BMR (Katch): {result.bmr['katch']} kcal/day")
        print(f"TDEE (Katch): {result.tdee['katch']} kcal/day")
        print(f"Activity: {result.activity_level}")
        print()

    except Exception as e:
        handle_request_errors(e, lang="en")

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

        print(f"Описание активности: {result.activity_level}")
        print(f"Поддержание веса: {result.recommended_intake['maintenance']} ккал/день")
        print(f"Похудение: {result.recommended_intake['weight_loss']} ккал/день")
        print()

    except Exception as e:
        handle_request_errors(e, lang="ru")

    # Example 4: Timeout handling demonstration
    print("📊 Example 4: Timeout handling (timeout=5.0)")
    print("-" * 45)

    try:
        # EN: Demonstrate passing a custom timeout for the request
        # RU: Пример передачи пользовательского таймаута запроса
        result = call_premium_bmr_api(
            weight_kg=75,
            height_cm=180,
            age=30,
            sex="male",
            activity="active",
            lang="en",
            timeout=5.0,
        )

        print("Request completed within timeout.")
        print(f"BMR (Mifflin): {result.bmr['mifflin']} kcal/day")
        print(f"TDEE (Mifflin): {result.tdee['mifflin']} kcal/day\n")

    except Exception as e:
        # EN: Friendly timeout/error message so users see how to handle it
        # RU: Дружелюбное сообщение при таймауте/ошибке, чтобы показать обработку
        handle_request_errors_detailed(e)

    # Example 5: Compare all activity levels
    print("📊 Example 5: Activity level comparison")
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
            handle_request_errors_inline(e, activity)

    print("\n✨ Premium BMR/TDEE API provides comprehensive metabolic calculations!")
    print("💡 Use different formulas for different populations:")
    print("   • Mifflin-St Jeor: Most accurate for general population")
    print("   • Harris-Benedict: Traditional formula")
    print("   • Katch-McArdle: Best for athletes with known body fat %")


if __name__ == "__main__":
    main()
