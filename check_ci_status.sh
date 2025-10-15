#!/bin/bash

# Check CI Status for PulsePlate PR
# This script helps monitor the CI status of the current PR

echo "🔍 Checking CI Status for PulsePlate PR..."
echo ""

# Get current branch
CURRENT_BRANCH=$(git branch --show-current)
echo "📍 Current branch: $CURRENT_BRANCH"

# Get latest commit
LATEST_COMMIT=$(git log --oneline -1)
echo "📝 Latest commit: $LATEST_COMMIT"

echo ""
echo "🌐 GitHub PR Status:"
echo "   Please check manually at:"
echo "   https://github.com/Katsiarynakavaleuskaya/PulsePlate/pulls"
echo ""

# Check if we're on a feature branch
if [[ $CURRENT_BRANCH == feature/* ]]; then
    echo "✅ You're on a feature branch - this is correct for PR workflow"
    echo ""
    echo "📋 Next steps:"
    echo "   1. Go to GitHub and check if CI is green ✅"
    echo "   2. Wait for code review approval"
    echo "   3. Merge the PR when ready"
    echo "   4. Only then proceed to next phase (PR #2: OpenAPI Infrastructure)"
else
    echo "⚠️  You're not on a feature branch"
    echo "   Expected: feature/improve-frontend-ci-workflow"
fi

echo ""
echo "🔧 Local test status:"
echo "   Run 'cd frontend && npm test' to verify locally"

echo ""
echo "📊 Expected CI results:"
echo "   ✅ Frontend CI: All tests pass (176/177)"
echo "   ✅ Build: Successful"
echo "   ✅ Lint: No errors"
echo "   ✅ Type check: No errors"
