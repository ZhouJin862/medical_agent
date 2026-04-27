#!/bin/bash
# Kubernetes deployment script for Medical Agent

set -e

# Configuration
NAMESPACE="${NAMESPACE:-medical-agent}"
K8S_DIR="${K8S_DIR:-./k8s}"
IMAGE_REGISTRY="${IMAGE_REGISTRY:-}"
IMAGE_NAME="${IMAGE_NAME:-medical-agent}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
ENV="${ENV:-dev}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check kubectl
if ! command -v kubectl &> /dev/null; then
    log_error "kubectl not found. Please install kubectl."
    exit 1
fi

# Check cluster connection
if ! kubectl cluster-info &> /dev/null; then
    log_error "Cannot connect to Kubernetes cluster."
    exit 1
fi

# Parse arguments
DRY_RUN=false
APPLY_SECRETS=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --with-secrets)
            APPLY_SECRETS=true
            shift
            ;;
        --namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --image)
            FULL_IMAGE="$2"
            shift 2
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Build full image name
FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"
if [ -n "$IMAGE_REGISTRY" ]; then
    FULL_IMAGE="${IMAGE_REGISTRY}/${FULL_IMAGE}"
fi

log_info "Deploying Medical Agent to Kubernetes"
log_info "Namespace: ${NAMESPACE}"
log_info "Image: ${FULL_IMAGE}"
log_info "Environment: ${ENV}"

# Create namespace
log_info "Creating namespace..."
kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

# Apply ServiceAccount and RBAC
log_info "Applying ServiceAccount and RBAC..."
kubectl apply -f "${K8S_DIR}/serviceaccount.yaml"

# Apply ConfigMap
log_info "Applying ConfigMap..."
kubectl apply -f "${K8S_DIR}/configmap.yaml"

# Apply Secrets (if requested)
if [ "$APPLY_SECRETS" = true ]; then
    log_warn "Applying Secrets (ensure values are correct)..."
    kubectl apply -f "${K8S_DIR}/secret.yaml"
else
    log_warn "Skipping Secrets. Use --with-secrets to apply."
    log_warn "Ensure Secrets exist or deployment will fail."
fi

# Update deployment with new image
log_info "Updating Deployment with image: ${FULL_IMAGE}"
if [ "$DRY_RUN" = true ]; then
    kubectl set image deployment/medical-agent \
        medical-agent="${FULL_IMAGE}" \
        --namespace="${NAMESPACE}" \
        --dry-run=server
else
    kubectl set image deployment/medical-agent \
        medical-agent="${FULL_IMAGE}" \
        --namespace="${NAMESPACE}"
fi

# Apply Deployment, Service, HPA, Ingress
log_info "Applying Deployment..."
kubectl apply -f "${K8S_DIR}/deployment.yaml"

log_info "Applying Service..."
kubectl apply -f "${K8S_DIR}/service.yaml"

log_info "Applying HPA..."
kubectl apply -f "${K8S_DIR}/hpa.yaml"

log_info "Applying Ingress..."
kubectl apply -f "${K8S_DIR}/ingress.yaml"

# Wait for rollout
if [ "$DRY_RUN" = false ]; then
    log_info "Waiting for deployment rollout..."
    kubectl rollout status deployment/medical-agent --namespace="${NAMESPACE}" --timeout=5m

    # Show pod status
    log_info "Pod status:"
    kubectl get pods -n "${NAMESPACE}" -l app=medical-agent

    # Show service
    log_info "Service:"
    kubectl get svc -n "${NAMESPACE}" medical-agent

    log_info "Deployment completed successfully!"
    log_info ""
    log_info "Useful commands:"
    log_info "  View logs: kubectl logs -f deployment/medical-agent -n ${NAMESPACE}"
    log_info "  Get pods: kubectl get pods -n ${NAMESPACE}"
    log_info "  Port forward: kubectl port-forward svc/medical-agent 8000:80 -n ${NAMESPACE}"
    log_info "  Describe deployment: kubectl describe deployment medical-agent -n ${NAMESPACE}"
else
    log_info "Dry run completed. No changes were made."
fi
