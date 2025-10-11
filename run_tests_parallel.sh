#!/bin/bash
# Fast parallel test runner using pytest-xdist (blast)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Running tests with pytest-xdist (blast) for maximum speed${NC}"

# Detect number of CPU cores
CORES=$(python -c "import os; print(os.cpu_count() or 1)")
echo -e "${YELLOW}📊 Detected ${CORES} CPU cores${NC}"

# Default to using all cores, but allow override
WORKERS=${1:-$CORES}
if ! [[ "$WORKERS" =~ ^[0-9]+$ ]] || [ "$WORKERS" -lt 1 ]; then
  echo -e "${RED}Invalid worker count '$WORKERS'; defaulting to 1${NC}"
  WORKERS=1
fi

echo -e "${YELLOW}⚡ Using ${WORKERS} parallel workers${NC}"

# Run tests with parallel execution
echo -e "${GREEN}🏃 Starting parallel test execution...${NC}"

# Use pytest-xdist with worksteal distribution for optimal load balancing
python -m pytest \
    --dist=worksteal \
    -n "${WORKERS}" \
    --cov=core \
    --cov=app \
    --cov-report=term-missing \
    --cov-report=xml \
    --cov-fail-under=97 \
    -v \
    --tb=short \
    --maxfail=10 \
    --durations=10 \
    tests/

echo -e "${GREEN}✅ Parallel test execution completed!${NC}"
