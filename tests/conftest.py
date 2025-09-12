# -*- coding: utf-8 -*-
"""
Pytest configuration for PulsePlate

RU: Глобальная конфигурация тестов
EN: Global test configuration
"""
import os

# Set VIP_MODULE_ENABLED globally for all tests
os.environ["VIP_MODULE_ENABLED"] = "true"

# Configure Hypothesis defaults to avoid flaky deadline-based failures on CI or
# slower local machines.
try:  # pragma: no cover - test helper config
    from hypothesis import HealthCheck, settings

    settings.register_profile(
        "ci",
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    settings.load_profile("ci")
except Exception:
    pass
