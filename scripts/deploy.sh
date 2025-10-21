#!/bin/bash
set -euo pipefail

# Deploy script for PulsePlate
# Usage: ./scripts/deploy.sh [staging|production] [version]

ENVIRONMENT=${1:-staging}
VERSION=${2:-latest}
NAMESPACE="pulseplate-${ENVIRONMENT}"

echo "🚀 Deploying PulsePlate to ${ENVIRONMENT} environment"
echo "📦 Version: ${VERSION}"
echo "🏷️  Namespace: ${NAMESPACE}"

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed or not in PATH"
    exit 1
fi

# Check if we're connected to a cluster
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Not connected to a Kubernetes cluster"
    exit 1
fi

# Create namespace if it doesn't exist
kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

# Apply configuration
echo "📋 Applying ${ENVIRONMENT} configuration..."
kubectl apply -f "deploy/${ENVIRONMENT}.yml" -n "${NAMESPACE}"

# Update image if version is specified
if [ "${VERSION}" != "latest" ]; then
    echo "🔄 Updating image to version ${VERSION}..."
    kubectl set image deployment/pulseplate-${ENVIRONMENT} \
        pulseplate=ghcr.io/katsiarynakavaleuskaya/pulseplate:${VERSION} \
        -n "${NAMESPACE}"
fi

# Wait for rollout to complete
echo "⏳ Waiting for deployment to complete..."
kubectl rollout status deployment/pulseplate-${ENVIRONMENT} -n "${NAMESPACE}" --timeout=300s

# Health check
echo "🏥 Running health check..."
kubectl get pods -n "${NAMESPACE}" -l app=pulseplate-${ENVIRONMENT}

# Get service URL
SERVICE_URL=$(kubectl get service pulseplate-${ENVIRONMENT}-service -n "${NAMESPACE}" -o jsonpath='{.spec.clusterIP}')
echo "✅ Deployment completed!"
echo "🌐 Service URL: http://${SERVICE_URL}"
echo "📊 Pods:"
kubectl get pods -n "${NAMESPACE}" -l app=pulseplate-${ENVIRONMENT}

# Optional: Port forward for local testing
if [ "${ENVIRONMENT}" = "staging" ]; then
    echo "🔗 To test locally, run:"
    echo "kubectl port-forward -n ${NAMESPACE} service/pulseplate-${ENVIRONMENT}-service 8000:80"
fi
