#!/usr/bin/env python3
# pyright: reportMissingTypeStubs=false
"""
Example usage of the Premium BMR/TDEE API

This script demonstrates how to use the new nutrition API endpoint
for calculating BMR and TDEE using multiple formulas.
"""

import logging
from typing import Any, Dict, Optional

import requests  # type: ignore[import-untyped]
from pydantic import BaseModel, Field, field_validator
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)

from app.schemas.bmr import BMRResponse

logger = logging.getLogger(__name__)


class BMRParams(BaseModel):
    """Pydantic model for BMR calculation parameters with validation."""

    weight_kg: float = Field(gt=0, description="Weight in kilograms")
    height_cm: float = Field(gt=0, description="Height in centimeters")
    age: int = Field(ge=0, le=120, description="Age in years")
    sex: str = Field(description="Biological sex")
    activity: str = Field(description="Activity level")
    lang: str = Field(default="en", description="Language code")

    @field_validator("sex")
    @classmethod
    def validate_sex(cls, v: str) -> str:
        """Validate sex field."""
        if v not in ("male", "female"):
            raise ValueError(f"sex must be 'male' or 'female', got {v}")
        return v

    @field_validator("activity")
    @classmethod
    def validate_activity(cls, v: str) -> str:
        """Validate activity field."""
        valid_activities = ("sedentary", "light", "moderate", "active", "very_active")
        if v not in valid_activities:
            raise ValueError(f"activity must be one of {valid_activities}, got {v}")
        return v

    @field_validator("lang")
    @classmethod
    def validate_lang(cls, v: str) -> str:
        """Validate lang field."""
        if v not in ("en", "ru"):
            raise ValueError(f"lang must be 'en' or 'ru', got {v}")
        return v


def validate_bmr_params(params: Dict[str, Any]) -> BMRParams:
    """
    Validate and convert BMR parameters using Pydantic model.

    Args:
        params: Dictionary containing BMR parameters

    Returns:
        Validated BMRParams instance

    Raises:
        pydantic.ValidationError: If validation fails
    """
    return BMRParams.model_validate(params)


def _should_retry_http_error(exception: BaseException) -> bool:
    """
    Determine if an HTTP error should be retried.

    Retries on 5xx server errors (transient) but not 4xx client errors (permanent).
    """
    if isinstance(exception, requests.exceptions.HTTPError) and exception.response is not None:
        status_code: int = exception.response.status_code
        # Retry on 5xx server errors (transient failures)
        # Don't retry on 4xx client errors (bad request, auth issues, etc.)
        should_retry = 500 <= status_code < 600
        logger.debug(
            "HTTP error %d: %s",
            status_code,
            "retrying transient 5xx" if should_retry else "not retrying 4xx/other",
        )
        return should_retry
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
    api_key: str = "test_key",  # nosec B105  # Example/demo key only
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
        The returned BMRResponse is a Pydantic BaseModel. Use attribute access for
        top-level fields (e.g., result.bmr, result.tdee, result.activity_level).
        Nested fields like bmr/tdee/recommended_intake are dictionaries, so access
        their items via keys (e.g., result.bmr["mifflin"], result.tdee["mifflin"]).

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
    Handle and log error messages for API request exceptions.

    Args:
        exception: The exception that was raised
        lang: Language for error messages ("en" or "ru")
    """
    if isinstance(exception, requests.exceptions.Timeout):
        if lang == "ru":
            logger.error("⏱️ Таймаут: %s", exception, exc_info=True)
        else:
            logger.error("⏱️ Timeout: %s", exception, exc_info=True)
            logger.info(
                "Try increasing timeout (e.g., timeout=10.0) and ensure server responsiveness."
            )
    elif isinstance(exception, requests.exceptions.HTTPError):
        if lang == "ru":
            logger.error("❌ HTTP-ошибка: %s", exception, exc_info=True)
        else:
            logger.error("❌ HTTP error: %s", exception, exc_info=True)
            logger.info("The API returned an error status code. Check server logs.")
    elif isinstance(exception, requests.exceptions.ConnectionError):
        if lang == "ru":
            logger.error("🔌 Ошибка соединения: %s", exception, exc_info=True)
        else:
            logger.error("🔌 Connection error: %s", exception, exc_info=True)
            logger.info("Make sure the API server is running on localhost:8000 and reachable.")
    elif isinstance(exception, requests.exceptions.RequestException):
        if lang == "ru":
            logger.warning("⚠️ Ошибка запроса: %s", exception, exc_info=True)
        else:
            logger.warning("⚠️ Request error: %s", exception, exc_info=True)
    else:
        if lang == "ru":
            logger.error("❌ Непредвиденная ошибка: %s", exception, exc_info=True)
        else:
            logger.error("❌ Unexpected error: %s", exception, exc_info=True)


def handle_request_errors_detailed(exception: Exception) -> None:
    """
    Handle and log detailed error messages for API request exceptions.

    Args:
        exception: The exception that was raised
    """
    if isinstance(exception, requests.exceptions.Timeout):
        logger.error(
            "⏱️ Request timed out. Try increasing timeout (e.g., timeout=10.0).", exc_info=True
        )
        logger.info("Details: %s", exception)
    elif isinstance(exception, requests.exceptions.HTTPError):
        logger.error("❌ HTTP error occurred. Check server response status.", exc_info=True)
        logger.info("Details: %s", exception)
    elif isinstance(exception, requests.exceptions.ConnectionError):
        logger.error("🔌 Connection error. Is the server running and reachable?", exc_info=True)
        logger.info("Details: %s", exception)
    elif isinstance(exception, requests.exceptions.RequestException):
        logger.warning("⚠️ Request error occurred.", exc_info=True)
        logger.info("Details: %s", exception)
    else:
        logger.error("❌ Unexpected error.", exc_info=True)
        logger.info("Details: %s", exception)


def handle_request_errors_inline(exception: Exception, activity: str) -> None:
    """
    Handle and log inline error messages for API request exceptions.

    Args:
        exception: The exception that was raised
        activity: Activity level string for display
    """
    if isinstance(exception, requests.exceptions.Timeout):
        logger.error("%s | Timeout: %s", f"{activity:<15}", exception, exc_info=True)
    elif isinstance(exception, requests.exceptions.HTTPError):
        logger.error("%s | HTTP error: %s", f"{activity:<15}", exception, exc_info=True)
    elif isinstance(exception, requests.exceptions.ConnectionError):
        logger.error("%s | Connection error: %s", f"{activity:<15}", exception, exc_info=True)
    elif isinstance(exception, requests.exceptions.RequestException):
        logger.warning("%s | Request error: %s", f"{activity:<15}", exception, exc_info=True)
    else:
        logger.error("%s | Unexpected error: %s", f"{activity:<15}", exception, exc_info=True)


def main() -> None:
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
    # Base parameters without activity (will be added per iteration)
    base_params_raw: Dict[str, Any] = {
        "weight_kg": 70.0,
        "height_cm": 175.0,
        "age": 30,
        "sex": "male",
        "lang": "en",
    }

    print("Activity Level    | TDEE (Mifflin)")
    print("-" * 35)

    for activity in activities:
        try:
            # Include activity in params and validate
            params_with_activity = {**base_params_raw, "activity": activity}
            validated_params = validate_bmr_params(params_with_activity)
            # Call API by unpacking validated params (Pydantic model supports dict-style access)
            result = call_premium_bmr_api(
                weight_kg=validated_params.weight_kg,
                height_cm=validated_params.height_cm,
                age=validated_params.age,
                sex=validated_params.sex,
                activity=validated_params.activity,
                lang=validated_params.lang,
            )
            tdee = result.tdee["mifflin"]
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
