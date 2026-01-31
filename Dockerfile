# ============================================================================
# CrossBridge Docker Image
# ============================================================================
# Stateless execution orchestrator for framework-agnostic test execution
# Philosophy: Tool container, not app server. Sidecar, not replacement.
# ============================================================================

FROM python:3.11-slim

# ============================================================================
# METADATA
# ============================================================================
LABEL org.opencontainers.image.title="crossbridge"
LABEL org.opencontainers.image.description="Framework-agnostic test execution orchestrator with 12+ framework support"
LABEL org.opencontainers.image.version="0.2.0"
LABEL org.opencontainers.image.vendor="CrossStack AI"
LABEL org.opencontainers.image.source="https://github.com/crossstack-ai/crossbridge"
LABEL org.opencontainers.image.documentation="https://github.com/crossstack-ai/crossbridge/blob/main/docs/DOCKER_GUIDE.md"
LABEL org.opencontainers.image.licenses="Proprietary"

# Maintainer
LABEL maintainer="CrossStack AI Team <support@crossstack.ai>"

# ============================================================================
# ENVIRONMENT SETUP
# ============================================================================

# Prevent Python from writing pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Prevent Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1

# Set UTF-8 encoding
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# CrossBridge home directory (for volumes)
ENV CROSSBRIDGE_HOME=/data

# Volume paths (externalized)
ENV CROSSBRIDGE_LOG_DIR=/data/logs
ENV CROSSBRIDGE_REPORT_DIR=/data/reports
ENV CROSSBRIDGE_CACHE_DIR=/data/cache

# Workspace (mounted test repository)
ENV CROSSBRIDGE_WORKSPACE=/workspace

# Default execution mode
ENV CROSSBRIDGE_MODE=observer
ENV CROSSBRIDGE_LOG_LEVEL=INFO

# ============================================================================
# SYSTEM DEPENDENCIES
# ============================================================================

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ============================================================================
# WORKING DIRECTORY
# ============================================================================

# Set working directory
WORKDIR /opt/crossbridge

# ============================================================================
# PYTHON DEPENDENCIES
# ============================================================================

# Copy dependency files
COPY requirements.txt ./
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# ============================================================================
# APPLICATION CODE
# ============================================================================

# Copy CrossBridge source code
COPY cli/ ./cli/
COPY core/ ./core/
COPY adapters/ ./adapters/
COPY hooks/ ./hooks/
COPY services/ ./services/
COPY persistence/ ./persistence/
COPY grafana/ ./grafana/
COPY memory/ ./memory/
COPY search/ ./search/
COPY migration/ ./migration/

# Copy configuration examples
COPY crossbridge.yml.example ./crossbridge.yml.example
COPY .env.example ./.env.example

# Copy entry point script
COPY run_cli.py ./run_cli.py

# Make CLI executable
RUN chmod +x run_cli.py

# ============================================================================
# VOLUME DIRECTORIES
# ============================================================================

# Create volume mount points
# These will be externalized via docker-compose or -v flags
RUN mkdir -p /data/logs \
             /data/reports \
             /data/cache \
             /workspace

# ============================================================================
# HEALTHCHECK
# ============================================================================

# Healthcheck to verify CrossBridge is operational
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python run_cli.py --version || exit 1

# ============================================================================
# USER (Security)
# ============================================================================

# Create non-root user for security
RUN groupadd -r crossbridge && \
    useradd -r -g crossbridge -u 1000 -m -s /bin/bash crossbridge

# Set ownership
RUN chown -R crossbridge:crossbridge /opt/crossbridge /data

# Switch to non-root user
USER crossbridge

# ============================================================================
# VOLUMES
# ============================================================================

# Declare volumes (externalized state)
# These should be mounted at runtime for persistence
VOLUME ["/data/logs", "/data/reports", "/data/cache", "/workspace"]

# ============================================================================
# ENTRYPOINT & CMD
# ============================================================================

# Use Python CLI as entrypoint
# This makes the container behave like a CLI tool
ENTRYPOINT ["python", "run_cli.py"]

# Default command (show help)
# Override with actual commands: exec run, exec plan, etc.
CMD ["--help"]

# ============================================================================
# USAGE EXAMPLES
# ============================================================================
# 
# Build:
#   docker build -t crossbridge/crossbridge:0.2.0 .
#
# Run help:
#   docker run --rm crossbridge/crossbridge:0.2.0
#
# Run smoke tests:
#   docker run --rm \
#     -v $(pwd)/test-repo:/workspace \
#     -v $(pwd)/crossbridge-data/logs:/data/logs \
#     -v $(pwd)/crossbridge-data/reports:/data/reports \
#     crossbridge/crossbridge:0.2.0 exec run --framework pytest --strategy smoke
#
# Sidecar Observer Mode (Java Selenium BDD):
#   docker run -d \
#     --name crossbridge-observer \
#     -e CROSSBRIDGE_MODE=observer \
#     -e CROSSBRIDGE_DB_HOST=10.55.12.99 \
#     -e PRODUCT_NAME=MyJavaApp \
#     -e APP_VERSION=v2.0.0 \
#     -v $(pwd)/crossbridge-data:/data \
#     --network bridge \
#     crossbridge/crossbridge:0.2.0
#
# Sidecar Observer Mode (Robot Framework):
#   docker run -d \
#     --name crossbridge-observer \
#     -e CROSSBRIDGE_MODE=observer \
#     -e CROSSBRIDGE_DB_HOST=10.55.12.99 \
#     -e PRODUCT_NAME=MyRobotApp \
#     -e APP_VERSION=v2.0.0 \
#     -e CROSSBRIDGE_HOOKS_ENABLED=true \
#     -v $(pwd)/crossbridge-data:/data \
#     --network bridge \
#     crossbridge/crossbridge:0.2.0
#
# With docker-compose:
#   docker-compose up
#
# ============================================================================
