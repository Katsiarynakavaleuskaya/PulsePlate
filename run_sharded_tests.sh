#!/bin/bash
# Tenant-based test sharding runner for PulsePlate
# Prevents memory errors by running shards sequentially or with limited parallelism

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

TOTAL_SHARDS=6
COVERAGE_THRESHOLD=97

# Parse arguments
MODE="sequential"  # sequential, parallel-2, parallel-3, all-at-once
COVERAGE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --parallel-2)
            MODE="parallel-2"
            shift
            ;;
        --parallel-3)
            MODE="parallel-3"
            shift
            ;;
        --all-at-once)
            MODE="all-at-once"
            shift
            ;;
        --cov|--coverage)
            COVERAGE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --parallel-2     Run 2 shards in parallel (memory-safe)"
            echo "  --parallel-3     Run 3 shards in parallel (may cause memory issues)"
            echo "  --all-at-once    Run all shards simultaneously (high memory risk)"
            echo "  --cov           Enable coverage reporting with --cov-append"
            echo "  --help          Show this help message"
            echo ""
            echo "Default: Run shards sequentially (safest, slowest)"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}PulsePlate Tenant-Based Test Sharding${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Mode: ${YELLOW}$MODE${NC}"
echo -e "Coverage: ${YELLOW}$COVERAGE${NC}"
echo ""

# Build pytest command (returns array elements as string for eval)
build_cmd() {
    local shard=$1
    local cmd="python -m pytest --shard-id=$shard tests/ -q"
    if [ "$COVERAGE" = true ]; then
        # Scope coverage to source directories only (not entire repo)
        cmd="$cmd --cov=core --cov=app --cov-report=term --cov-append"
    fi
    echo "$cmd"
}

# Clean old coverage data
if [ "$COVERAGE" = true ]; then
    rm -f .coverage .coverage.*
    echo -e "${YELLOW}Cleaned old coverage data${NC}\n"
fi

case $MODE in
    sequential)
        echo -e "${GREEN}Running shards sequentially (memory-safe)${NC}\n"
        for shard in $(seq 1 $TOTAL_SHARDS); do
            echo -e "${BLUE}▶ Running Shard $shard/$TOTAL_SHARDS...${NC}"
            cmd=$(build_cmd $shard)
            if ! eval $cmd; then
                echo -e "${RED}✗ Shard $shard failed${NC}"
                exit 1
            fi
            echo -e "${GREEN}✓ Shard $shard completed${NC}\n"
        done
        ;;

    parallel-2)
        echo -e "${GREEN}Running 2 shards in parallel (memory-safe)${NC}\n"
        for batch in $(seq 0 2 $((TOTAL_SHARDS-1))); do
            shard1=$((batch+1))
            shard2=$((batch+2))

            if [ $shard1 -le $TOTAL_SHARDS ]; then
                echo -e "${BLUE}▶ Running Shards $shard1 and $shard2 in parallel...${NC}"
                cmd1=$(build_cmd $shard1)
                cmd2=$(build_cmd $shard2)

                # Run in background and wait for each individually
                eval "$cmd1 &"
                pid1=$!
                if [ $shard2 -le $TOTAL_SHARDS ]; then
                    eval "$cmd2 &"
                    pid2=$!
                    # Wait for each PID individually and capture exit codes
                    wait $pid1
                    rc1=$?
                    wait $pid2
                    rc2=$?
                    # Fail if any exit code is non-zero
                    if [ $rc1 -ne 0 ] || [ $rc2 -ne 0 ]; then
                        echo -e "${RED}✗ Parallel batch failed (rc1=$rc1, rc2=$rc2)${NC}"
                        exit 1
                    fi
                else
                    # Only one shard - wait and capture its exit code
                    wait $pid1
                    rc1=$?
                    if [ $rc1 -ne 0 ]; then
                        echo -e "${RED}✗ Batch failed (rc1=$rc1)${NC}"
                        exit 1
                    fi
                fi
                echo -e "${GREEN}✓ Batch completed${NC}\n"
            fi
        done
        ;;

    parallel-3)
        echo -e "${YELLOW}⚠ Running 3 shards in parallel (may cause memory issues)${NC}\n"
        for batch in $(seq 0 3 $((TOTAL_SHARDS-1))); do
            shard1=$((batch+1))
            shard2=$((batch+2))
            shard3=$((batch+3))

            if [ $shard1 -le $TOTAL_SHARDS ]; then
                echo -e "${BLUE}▶ Running Shards $shard1, $shard2, $shard3 in parallel...${NC}"

                pids=()
                cmd1=$(build_cmd $shard1)
                eval "$cmd1 &"
                pids+=($!)

                if [ $shard2 -le $TOTAL_SHARDS ]; then
                    cmd2=$(build_cmd $shard2)
                    eval "$cmd2 &"
                    pids+=($!)
                fi

                if [ $shard3 -le $TOTAL_SHARDS ]; then
                    cmd3=$(build_cmd $shard3)
                    eval "$cmd3 &"
                    pids+=($!)
                fi
                
                failed=0
                for pid in "${pids[@]}"; do
                    wait $pid || failed=1
                done
                if [ $failed -ne 0 ]; then
                    echo -e "${RED}✗ Parallel batch failed${NC}"
                    exit 1
                fi
                echo -e "${GREEN}✓ Batch completed${NC}\n"
            fi
        done
        ;;

    all-at-once)
        echo -e "${RED}⚠⚠ Running ALL shards simultaneously (HIGH MEMORY RISK)${NC}\n"
        pids=()
        failed=0
        for pid in "${pids[@]}"; do
            wait $pid || failed=1
        done
        if [ $failed -ne 0 ]; then
            echo -e "${RED}✗ Parallel execution failed${NC}"
            exit 1
        fi
            pids+=($!)
        done
        for pid in "${pids[@]}"; do
            wait $pid || { echo -e "${RED}✗ Parallel execution failed${NC}"; exit 1; }
        done
        ;;
esac

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ All shards completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"

if [ "$COVERAGE" = true ]; then
    echo -e "\n${BLUE}Generating coverage report...${NC}"
    python -m coverage report --fail-under=$COVERAGE_THRESHOLD
    echo -e "${GREEN}Coverage threshold: $COVERAGE_THRESHOLD%${NC}"
fi
