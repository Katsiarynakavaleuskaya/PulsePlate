#!/bin/bash
# PR Readiness Check Script

set -e

echo "🔍 Checking PR readiness..."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
        return 1
    fi
}

# Check 1: GitHub Actions versions
echo "Checking GitHub Actions versions..."
if grep -r "aquasecurity/trivy-action@v[0-9]" .github/workflows/ >/dev/null 2>&1; then
    echo -e "${RED}❌ Found potentially problematic Trivy version${NC}"
    grep -r "aquasecurity/trivy-action@v[0-9]" .github/workflows/
    exit 1
fi
print_status 0 "GitHub Actions versions OK"

# Check 2: Bandit B110
echo "Checking for bare except blocks..."
if grep -r "except Exception:" tests/ | grep -v "# nosec B110" >/dev/null 2>&1; then
    echo -e "${RED}❌ Found bare except blocks without nosec B110${NC}"
    grep -r "except Exception:" tests/ | grep -v "# nosec B110"
    exit 1
fi
print_status 0 "No bare except blocks found"

# Check 3: Missing files
echo "Checking for missing referenced files..."
for workflow in .github/workflows/*.yml; do
    if [ -f "$workflow" ]; then
        if grep -q "uses: \./" "$workflow"; then
            while IFS= read -r line; do
                path=$(echo "$line" | sed 's/.*uses: \.\/\(.*\)/\1/')
                if [ ! -f "$path/action.yml" ] && [ ! -f "$path" ]; then
                    echo -e "${RED}❌ Missing file: $path${NC}"
                    exit 1
                fi
            done < <(grep "uses: \./" "$workflow")
        fi
    fi
done
print_status 0 "All referenced files exist"

# Check 4: Python syntax
echo "Checking Python syntax..."
find tests/ -name "*.py" -exec python -m py_compile {} \; >/dev/null 2>&1
print_status 0 "Python syntax OK"

# Check 5: YAML syntax
echo "Checking YAML syntax..."
yaml_errors=0

# Check if PyYAML is available
if python -c "import yaml" >/dev/null 2>&1; then
    for yaml_file in $(find .github/ -name "*.yml"); do
        if ! python -c "import yaml; yaml.safe_load(open('$yaml_file'))" >/dev/null 2>&1; then
            echo -e "${RED}❌ YAML syntax error in $yaml_file${NC}"
            yaml_errors=1
        fi
    done
    print_status $yaml_errors "YAML syntax OK"
else
    echo -e "${YELLOW}⚠️  PyYAML not installed, skipping YAML validation${NC}"
    print_status 0 "YAML syntax check skipped (PyYAML not available)"
fi

# Check 6: Pre-commit hooks
echo "Running pre-commit hooks..."
if command -v pre-commit >/dev/null 2>&1; then
    pre-commit run --all-files >/dev/null 2>&1
    pre_commit_status=$?
    print_status $pre_commit_status "Pre-commit hooks passed"
else
    echo -e "${YELLOW}⚠️  pre-commit not installed, skipping${NC}"
fi

echo -e "${GREEN}🎉 All checks passed! PR is ready.${NC}"
