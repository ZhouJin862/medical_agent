#!/bin/bash
# Docker build script for Medical Agent

set -e

# Configuration
IMAGE_NAME="${IMAGE_NAME:-medical-agent}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
REGISTRY="${REGISTRY:-}"
VERSION="${VERSION:-0.1.0}"
BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
VCS_REF="$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Parse arguments
SKIP_TESTS=false
PUSH=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --push)
            PUSH=true
            shift
            ;;
        --tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        --version)
            VERSION="$2"
            shift 2
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Build image name
FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"
if [ -n "$REGISTRY" ]; then
    FULL_IMAGE_NAME="${REGISTRY}/${FULL_IMAGE_NAME}"
fi

log_info "Building Docker image: ${FULL_IMAGE_NAME}"
log_info "Version: ${VERSION}"
log_info "Build Date: ${BUILD_DATE}"
log_info "VCS Ref: ${VCS_REF}"

# Run tests if not skipped
if [ "$SKIP_TESTS" = false ]; then
    log_info "Running tests before build..."
    if ! pytest -xvs tests/unit/; then
        log_error "Tests failed. Aborting build."
        log_warn "Use --skip-tests to bypass this check."
        exit 1
    fi
    log_info "Tests passed."
fi

# Build arguments
BUILD_ARGS=(
    --build-arg "VERSION=${VERSION}"
    --build-arg "BUILD_DATE=${BUILD_DATE}"
    --build-arg "VCS_REF=${VCS_REF}"
    --tag "${FULL_IMAGE_NAME}"
)

# Add version tag
if [ "${IMAGE_TAG}" != "${VERSION}" ]; then
    VERSION_TAG="${IMAGE_NAME}:${VERSION}"
    if [ -n "$REGISTRY" ]; then
        VERSION_TAG="${REGISTRY}/${VERSION_TAG}"
    fi
    BUILD_ARGS+=(--tag "${VERSION_TAG}")
fi

# Build latest tag
if [ "${IMAGE_TAG}" != "latest" ]; then
    LATEST_TAG="${IMAGE_NAME}:latest"
    if [ -n "$REGISTRY" ]; then
        LATEST_TAG="${REGISTRY}/${LATEST_TAG}"
    fi
    BUILD_ARGS+=(--tag "${LATEST_TAG}")
fi

# Build image
log_info "Executing docker build..."
docker build "${BUILD_ARGS[@]}" -f Dockerfile .

if [ $? -eq 0 ]; then
    log_info "Build successful!"

    # Show image info
    log_info "Image details:"
    docker images "${IMAGE_NAME}" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

    # Push if requested
    if [ "$PUSH" = true ]; then
        log_info "Pushing image to registry..."
        docker push "${FULL_IMAGE_NAME}"

        if [ "${IMAGE_TAG}" != "${VERSION}" ]; then
            docker push "${VERSION_TAG}"
        fi

        if [ "${IMAGE_TAG}" != "latest" ]; then
            docker push "${LATEST_TAG}"
        fi

        log_info "Push completed."
    fi
else
    log_error "Build failed!"
    exit 1
fi

log_info "Done! Image: ${FULL_IMAGE_NAME}"
