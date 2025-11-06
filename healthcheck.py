#!/usr/bin/env python3
"""Docker healthcheck script for PulsePlate application.

Checks if the application is responding to HTTP requests on the /health endpoint.
Uses Python's built-in urllib to avoid curl dependency (CVE-2025-11563).
"""
import sys
import urllib.request
import urllib.error

try:
    # Try to fetch health endpoint with timeout
    response = urllib.request.urlopen("http://localhost:8000/health", timeout=5)
    status_code = response.getcode()

    # Exit with success if status is 200
    if status_code == 200:
        sys.exit(0)
    else:
        print(f"Healthcheck failed: HTTP {status_code}", file=sys.stderr)
        sys.exit(1)

except urllib.error.URLError as e:
    print(f"Healthcheck error: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Unexpected healthcheck error: {e}", file=sys.stderr)
    sys.exit(1)
