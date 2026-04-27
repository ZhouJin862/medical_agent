# Multi-stage Dockerfile for Medical Agent
# Stage 1: Builder
FROM python:3.11-slim as builder

# Set build arguments
ARG VERSION=0.1.0
ARG BUILD_DATE
ARG VCS_REF

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /build

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libpq-dev \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Python build dependencies
COPY requirements.txt .
RUN pip install --user --upgrade pip && \
    pip install --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim as runtime

# Set build-time labels
LABEL maintainer="Medical Agent Team" \
      version=$VERSION \
      org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.vcs-url="https://github.com/your-org/medical-agent" \
      org.label-schema.schema-version="1.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/root/.local/bin:$PATH \
    APP_HOME=/app \
    PORT=8000

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Set working directory
WORKDIR $APP_HOME

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs /app/tmp && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Expose port
EXPOSE $PORT

# Run application
CMD ["uvicorn", "src.interface.api.main:app", "--host", "0.0.0.0", "--port", "$PORT"]
