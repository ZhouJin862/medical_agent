#!/bin/bash
# Docker run script for Medical Agent

set -e

# Configuration
IMAGE_NAME="${IMAGE_NAME:-medical-agent}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
CONTAINER_NAME="${CONTAINER_NAME:-medical-agent}"
PORT="${PORT:-8000}"
ENV_FILE="${ENV_FILE:-.env}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    log_warn ".env file not found. Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        log_warn "Please edit .env with your configuration before running."
    else
        log_warn "No .env.example found. Using default environment."
    fi
fi

# Stop and remove existing container
if [ "$(docker ps -aq -f name=${CONTAINER_NAME})" ]; then
    log_info "Stopping existing container..."
    docker stop "${CONTAINER_NAME}" 2>/dev/null || true
    docker rm "${CONTAINER_NAME}" 2>/dev/null || true
fi

# Build image name
FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"

# Run container
log_info "Starting container: ${CONTAINER_NAME}"
log_info "Image: ${FULL_IMAGE_NAME}"
log_info "Port: ${PORT}"

docker run -d \
    --name "${CONTAINER_NAME}" \
    --restart unless-stopped \
    -p "${PORT}:8000" \
    --env-file "${ENV_FILE}" \
    -v "$(pwd)/logs:/app/logs" \
    -v "$(pwd)/data:/app/data" \
    "${FULL_IMAGE_NAME}"

# Wait for container to be healthy
log_info "Waiting for container to be healthy..."
for i in {1..30}; do
    if docker ps --filter "name=${CONTAINER_NAME}" --filter "status=running" | grep -q ${CONTAINER_NAME}; then
        # Check if healthy
        if curl -sf "http://localhost:${PORT}/health" > /dev/null 2>&1; then
            log_info "Container is healthy!"
            break
        fi
    fi
    sleep 1
done

# Show logs
log_info "Container logs:"
docker logs "${CONTAINER_NAME}" --tail 20

log_info "Container started successfully!"
log_info "API available at: http://localhost:${PORT}"
log_info ""
log_info "Useful commands:"
log_info "  View logs: docker logs -f ${CONTAINER_NAME}"
log_info "  Stop: docker stop ${CONTAINER_NAME}"
log_info "  Restart: docker restart ${CONTAINER_NAME}"
log_info "  Shell: docker exec -it ${CONTAINER_NAME} /bin/bash"
