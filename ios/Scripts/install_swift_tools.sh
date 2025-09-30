#!/bin/bash
# Swift Tools Installation Script for PulsePlate

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Installing Swift Tools for PulsePlate${NC}"
echo "=============================================="

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo -e "${RED}❌ Homebrew not found. Please install Homebrew first:${NC}"
    echo "Visit: https://brew.sh"
    exit 1
fi

echo -e "${YELLOW}📦 Installing SwiftLint...${NC}"
brew install swiftlint

echo -e "${YELLOW}📦 Installing SwiftFormat...${NC}"
brew install swiftformat

# Verify installation
echo -e "${BLUE}🔍 Verifying installation...${NC}"

if command -v swiftlint &> /dev/null; then
    SWIFTLINT_VERSION=$(swiftlint version)
    echo -e "${GREEN}✅ SwiftLint installed: $SWIFTLINT_VERSION${NC}"
else
    echo -e "${RED}❌ SwiftLint installation failed${NC}"
    exit 1
fi

if command -v swiftformat &> /dev/null; then
    SWIFTFORMAT_VERSION=$(swiftformat --version)
    echo -e "${GREEN}✅ SwiftFormat installed: $SWIFTFORMAT_VERSION${NC}"
else
    echo -e "${RED}❌ SwiftFormat installation failed${NC}"
    exit 1
fi

echo -e "${GREEN}🎉 Swift Tools installation completed successfully!${NC}"
echo ""
echo "Next steps:"
echo "1. Run: ./ios/Scripts/swift_tools.sh build"
echo "2. Run: ./ios/Scripts/swift_tools.sh all"
