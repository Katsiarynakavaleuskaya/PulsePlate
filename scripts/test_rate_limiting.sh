#!/bin/bash

# Rate Limiting Test Script
# Tests rate limiting functionality with proper authentication and valid payloads

set -e

# Configuration
BASE_URL="${BASE_URL:-https://pulseplate.app}"
TEST_API_KEY="${TEST_API_KEY:-your-test-api-key-here}"
REQUESTS_COUNT="${REQUESTS_COUNT:-15}"

echo "================================================"
echo "Rate Limiting Test Suite"
echo "================================================"
echo "Base URL: $BASE_URL"
echo "Requests to send: $REQUESTS_COUNT"
echo ""

# Function to test authenticated admin endpoint
test_admin_endpoint() {
    echo "Testing Admin Endpoint with Authentication"
    echo "-------------------------------------------"

    for i in $(seq 1 $REQUESTS_COUNT); do
        printf "Request %2d: " "$i"

        response=$(curl -s -o /dev/null -w "%{http_code}" \
            -X POST \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer ${TEST_API_KEY}" \
            -d "{\"action\": \"get_status\", \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" \
            "${BASE_URL}/api/v1/admin/status")

        if [ "$response" = "429" ]; then
            echo "HTTP $response - Rate limited! ✓"
        elif [ "$response" = "200" ] || [ "$response" = "201" ]; then
            echo "HTTP $response - Success"
        elif [ "$response" = "401" ] || [ "$response" = "403" ]; then
            echo "HTTP $response - Auth failed (check API key)"
        else
            echo "HTTP $response - Unexpected response"
        fi

        # Small delay to make output readable
        sleep 0.1
    done
    echo ""
}

# Function to test public endpoint (BMI calculator)
test_public_endpoint() {
    echo "Testing Public Endpoint (BMI Calculator)"
    echo "-----------------------------------------"

    for i in $(seq 1 $REQUESTS_COUNT); do
        printf "Request %2d: " "$i"

        response=$(curl -s -o /dev/null -w "%{http_code}" \
            -X POST \
            -H "Content-Type: application/json" \
            -d "{\"weight\": 70, \"height\": 175, \"age\": 30, \"sex\": \"male\"}" \
            "${BASE_URL}/api/v1/bmi/calculate")

        if [ "$response" = "429" ]; then
            echo "HTTP $response - Rate limited! ✓"
        elif [ "$response" = "200" ] || [ "$response" = "201" ]; then
            echo "HTTP $response - Success"
        else
            echo "HTTP $response - Unexpected response"
        fi

        sleep 0.1
    done
    echo ""
}

# Function to test dedicated test endpoint
test_rate_limit_endpoint() {
    echo "Testing Dedicated Rate Limit Endpoint"
    echo "--------------------------------------"

    for i in $(seq 1 $REQUESTS_COUNT); do
        printf "Request %2d: " "$i"

        response_body=$(curl -s -w "\n---STATUS:%{http_code}---" \
            -X POST \
            "${BASE_URL}/api/v1/test/rate-limit" 2>/dev/null)

        status_code=$(echo "$response_body" | grep -o "STATUS:[0-9]*" | cut -d: -f2)

        if [ "$status_code" = "429" ]; then
            echo "HTTP $status_code - Rate limited! ✓"
        elif [ "$status_code" = "200" ]; then
            # Extract message from JSON response
            message=$(echo "$response_body" | grep -o '"message":"[^"]*"' | cut -d'"' -f4)
            echo "HTTP $status_code - ${message:-Success}"
        elif [ "$status_code" = "404" ]; then
            echo "HTTP $status_code - Test endpoint not available (production environment?)"
            return 1
        else
            echo "HTTP ${status_code:-unknown} - Unexpected response"
        fi

        sleep 0.1
    done
    echo ""
}

# Function to check rate limit headers
check_rate_limit_headers() {
    echo "Checking Rate Limit Headers"
    echo "----------------------------"

    headers=$(curl -I -s -X POST \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${TEST_API_KEY}" \
        -d '{"action": "get_status"}' \
        "${BASE_URL}/api/v1/admin/status" 2>/dev/null)

    # Check for rate limit headers
    echo "$headers" | grep -i "x-ratelimit" || echo "No rate limit headers found"
    echo "$headers" | grep -i "retry-after" || echo "No retry-after header found"
    echo ""
}

# Main execution
main() {
    echo "Starting rate limit tests..."
    echo ""

    # Test 1: Check headers
    check_rate_limit_headers

    # Test 2: Test dedicated endpoint (if available)
    if test_rate_limit_endpoint; then
        echo "✓ Test endpoint is available"
    else
        echo "⚠ Test endpoint not available, skipping..."
    fi

    # Test 3: Test public endpoint
    test_public_endpoint

    # Test 4: Test admin endpoint (if API key is set)
    if [ "$TEST_API_KEY" != "your-test-api-key-here" ]; then
        test_admin_endpoint
    else
        echo "⚠ Skipping admin endpoint test (no API key configured)"
        echo "  Set TEST_API_KEY environment variable to test authenticated endpoints"
        echo ""
    fi

    echo "================================================"
    echo "Rate limiting tests completed!"
    echo "================================================"
}

# Run main function
main
