#!/bin/bash
# Swift Tools Script for PulsePlate - SwiftLint + SwiftFormat

set -e

# Enable globstar for recursive glob patterns
shopt -s globstar

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project paths - configurable via environment variable
IOS_DIR="${IOS_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}"
cd "$IOS_DIR" || exit 1
SWIFT_FILES="PulsePlate/**/*.swift"

echo -e "${BLUE}🚀 PulsePlate Swift Tools${NC}"
echo "================================"

# Function to check if tools are installed
check_tools() {
    if ! command -v swiftlint &> /dev/null; then
        echo -e "${RED}❌ SwiftLint not found. Please run: ./install_swift_tools.sh${NC}"
        exit 1
    fi

    if ! command -v swiftformat &> /dev/null; then
        echo -e "${RED}❌ SwiftFormat not found. Please run: ./install_swift_tools.sh${NC}"
        exit 1
    fi
}

# Function to run SwiftLint
run_lint() {
    echo -e "${BLUE}🔍 Running SwiftLint...${NC}"
    swiftlint lint --config "$PROJECT_ROOT/.swiftlint.yml" --reporter xcode
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ SwiftLint passed!${NC}"
    else
        echo -e "${RED}❌ SwiftLint found issues${NC}"
    fi

    return $exit_code
}

# Function to run SwiftFormat
run_format() {
    echo -e "${BLUE}🎨 Running SwiftFormat...${NC}"
    # shellcheck disable=SC2086
    swiftformat --config "$PROJECT_ROOT/.swiftformat" --inplace $SWIFT_FILES
    echo -e "${GREEN}✅ SwiftFormat complete!${NC}"
}

# Function to run SwiftFormat in check mode
check_format() {
    # shellcheck disable=SC2086
    swiftformat --config "$PROJECT_ROOT/.swiftformat" --lint $SWIFT_FILES
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ SwiftFormat check passed!${NC}"
    else
        echo -e "${RED}❌ SwiftFormat found formatting issues${NC}"
    fi

    return $exit_code
}

# Function to run both tools
run_all() {
    echo -e "${BLUE}🔄 Running all Swift tools...${NC}"

    check_tools

    # Run format first
    run_format

    # Then run lint
    run_lint
}

# Function to show help
show_help() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  lint        Run SwiftLint only"
    echo "  format      Run SwiftFormat only"
    echo "  check       Check formatting without changes"
    echo "  all         Run both tools (format + lint)"
    echo "  install     Install tools via Homebrew"
    echo "  help        Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 lint     # Check code quality"
    echo "  $0 format   # Format code"
    echo "  $0 all      # Format and lint"
}

# Main script logic
case "${1:-help}" in
    "lint")
        check_tools
        run_lint
        ;;
    "format")
        check_tools
        run_format
        ;;
    "check")
        check_tools
        check_format
        ;;
    "all")
        run_all
        ;;
    "install")
        if [ -x "./install_swift_tools.sh" ]; then
            ./install_swift_tools.sh
        else
            echo -e "${RED}❌ install_swift_tools.sh not found or not executable${NC}"
            exit 1
        fi
        ;;
    "help"|*)
        show_help
        ;;
esac
