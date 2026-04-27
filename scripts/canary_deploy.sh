#!/bin/bash
# Canary deployment script for Medical Agent
# Implements gradual traffic shifting between primary and canary deployments

set -e

# Configuration
NAMESPACE="${NAMESPACE:-medical-agent}"
CANARY_IMAGE="${CANARY_IMAGE:-medical-agent:1.1.0}"
PRIMARY_IMAGE="${PRIMARY_IMAGE:-medical-agent:1.0.0}"
TRAFFIC_SPLIT="${TRAFFIC_SPLIT:-10}"  # Initial canary traffic percentage

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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found"
        exit 1
    fi

    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_error "Namespace $NAMESPACE not found"
        exit 1
    fi

    log_info "Prerequisites check passed"
}

# Deploy canary
deploy_canary() {
    local image=$1
    log_info "Deploying canary version: $image"

    # Update canary deployment image
    kubectl set image deployment/medical-agent-canary \
        medical-agent="$image" \
        --namespace="$NAMESPACE"

    # Wait for canary to be ready
    log_info "Waiting for canary to be ready..."
    kubectl rollout status deployment/medical-agent-canary --namespace="$NAMESPACE" --timeout=5m

    # Scale canary to initial size
    kubectl scale deployment/medical-agent-canary --replicas=1 --namespace="$NAMESPACE"

    log_info "Canary deployed successfully"
}

# Set traffic split
set_traffic_split() {
    local canary_percent=$1
    log_info "Setting traffic split: ${canary_percent}% canary, $((100 - canary_percent))% primary"

    # This would typically use a service mesh like Istio or Linkerd
    # For simplicity, we'll use replica-based weight approximation

    # Calculate replicas based on desired traffic split
    local total_replicas=4
    local canary_replicas=$((total_replicas * canary_percent / 100))
    local primary_replicas=$((total_replicas - canary_replicas))

    # Ensure at least 1 replica each
    [ $canary_replicas -lt 1 ] && canary_replicas=1
    [ $primary_replicas -lt 1 ] && primary_replicas=1

    log_info "Scaling: primary=$primary_replicas, canary=$canary_replicas"

    kubectl scale deployment/medical-agent-primary --replicas=$primary_replicas --namespace="$NAMESPACE"
    kubectl scale deployment/medical-agent-canary --replicas=$canary_replicas --namespace="$NAMESPACE"
}

# Check canary health
check_canary_health() {
    log_info "Checking canary health..."

    # Check if canary pods are running
    local canary_ready=$(kubectl get deployment/medical-agent-canary \
        --namespace="$NAMESPACE" \
        -o jsonpath='{.status.readyReplicas}')

    if [ "$canary_ready" -lt 1 ]; then
        log_error "Canary pods are not ready"
        return 1
    fi

    # Check error rate (would use Prometheus in production)
    # For now, just check pod status
    local canary_pods=$(kubectl get pods \
        --namespace="$NAMESPACE" \
        -l variant=canary \
        -o jsonpath='{.items[*].metadata.name}')

    for pod in $canary_pods; do
        local pod_status=$(kubectl get pod "$pod" \
            --namespace="$NAMESPACE" \
            -o jsonpath='{.status.phase}')

        if [ "$pod_status" != "Running" ]; then
            log_error "Canary pod $pod is $pod_status"
            return 1
        fi
    done

    log_info "Canary health check passed"
    return 0
}

# Check canary metrics
check_canary_metrics() {
    log_info "Checking canary metrics..."

    # This would query Prometheus for:
    # - Error rate comparison (canary vs primary)
    # - Response time comparison
    # - Resource usage comparison

    # Placeholder implementation
    log_warn "Metric checking requires Prometheus integration"
    log_info "Run manually: kubectl top pods -n $NAMESPACE -l app=medical-agent"
}

# Promote canary to primary
promote_canary() {
    local canary_image=$1
    log_info "Promoting canary to primary..."

    # Update primary deployment
    kubectl set image deployment/medical-agent-primary \
        medical-agent="$canary_image" \
        --namespace="$NAMESPACE"

    # Wait for rollout
    kubectl rollout status deployment/medical-agent-primary --namespace="$NAMESPACE" --timeout=5m

    # Scale down canary
    kubectl scale deployment/medical-agent-canary --replicas=0 --namespace="$NAMESPACE"

    log_info "Canary promoted successfully"
}

# Rollback canary
rollback_canary() {
    log_info "Rolling back canary..."

    # Scale canary to 0
    kubectl scale deployment/medical-agent-canary --replicas=0 --namespace="$NAMESPACE"

    # Ensure primary is at full capacity
    kubectl scale deployment/medical-agent-primary --replicas=3 --namespace="$NAMESPACE"

    log_info "Canary rolled back"
}

# Main canary deployment workflow
canary_workflow() {
    log_info "Starting canary deployment workflow"
    log_info "====================================="

    # Step 1: Deploy canary
    log_info "Step 1: Deploy canary version"
    deploy_canary "$CANARY_IMAGE"

    # Step 2: Initial traffic split (10%)
    log_info "Step 2: Initial traffic split (10%)"
    set_traffic_split 10
    sleep 30

    # Step 3: Health check
    log_info "Step 3: Health check"
    if ! check_canary_health; then
        log_error "Canary health check failed. Rolling back."
        rollback_canary
        exit 1
    fi

    # Step 4: Gradual traffic increase
    log_info "Step 4: Gradual traffic increase"

    for traffic_percent in 25 50 75; do
        log_info "Increasing canary traffic to ${traffic_percent}%"
        set_traffic_split $traffic_percent

        # Wait and monitor
        log_info "Monitoring for 60 seconds..."
        sleep 60

        if ! check_canary_health; then
            log_error "Health check failed at ${traffic_percent}% traffic. Rolling back."
            rollback_canary
            exit 1
        fi

        check_canary_metrics
    done

    # Step 5: Promote canary
    log_info "Step 5: Promoting canary to primary"
    promote_canary "$CANARY_IMAGE"

    log_info "====================================="
    log_info "Canary deployment completed successfully!"
}

# Interactive mode
interactive_mode() {
    log_info "Interactive canary deployment"
    log_info "Current setup:"
    kubectl get deployments -n "$NAMESPACE" -l app=medical-agent

    echo ""
    echo "Options:"
    echo "  1. Deploy new canary"
    echo "  2. Adjust traffic split"
    echo "  3. Check canary health"
    echo "  4. Promote canary"
    echo "  5. Rollback canary"
    echo "  6. Full workflow (automated)"
    echo "  0. Exit"

    read -p "Select option: " choice

    case $choice in
        1)
            read -p "Enter canary image: " img
            deploy_canary "$img"
            ;;
        2)
            read -p "Enter canary traffic percentage (0-100): " pct
            set_traffic_split "$pct"
            ;;
        3)
            check_canary_health
            check_canary_metrics
            ;;
        4)
            read -p "Enter canary image to promote: " img
            promote_canary "$img"
            ;;
        5)
            rollback_canary
            ;;
        6)
            canary_workflow
            ;;
        0)
            log_info "Exiting"
            exit 0
            ;;
        *)
            log_error "Invalid option"
            exit 1
            ;;
    esac
}

# Parse arguments
INTERACTIVE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --interactive)
            INTERACTIVE=true
            shift
            ;;
        --image)
            CANARY_IMAGE="$2"
            shift 2
            ;;
        --traffic)
            TRAFFIC_SPLIT="$2"
            shift 2
            ;;
        --promote)
            PROMOTE_ONLY=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Main execution
check_prerequisites

if [ "$INTERACTIVE" = true ]; then
    interactive_mode
elif [ "$PROMOTE_ONLY" = true ]; then
    promote_canary "$CANARY_IMAGE"
else
    canary_workflow
fi
