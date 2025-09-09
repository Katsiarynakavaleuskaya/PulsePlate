# -*- coding: utf-8 -*-
"""
Pytest configuration for PulsePlate

RU: Глобальная конфигурация тестов
EN: Global test configuration
"""
import os

# Set VIP_MODULE_ENABLED globally for all tests
os.environ["VIP_MODULE_ENABLED"] = "true"
