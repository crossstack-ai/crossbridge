#!/bin/bash
# ============================================================================
# CrossBridge Docker Build Script
# ============================================================================
# Builds CrossBridge Docker image with versioning
# Usage: ./build-docker.sh [version] [--no-cache] [--push]
# ============================================================================

set -e  # Exit on error

# ============================================================================
# CONFIGURATION
# ============================================================================

# Default version (override with first argument)
VERSION="${1:-0.2.0}"

# Image name
IMAGE_NAME="crossbridge/crossbridge"

# Registry (customize for your registry)
REGISTRY="${DOCKER_REGISTRY:-}"

# Build arguments
BUILD_ARGS=""
NO_CACHE=""
PUSH_IMAGE=false

# ============================================================================
# PARSE ARGUMENTS
# ============================================================================

for arg in "$@"; do
    case $arg in
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        --push)
            PUSH_IMAGE=true
            shift
            ;;
    esac
done

# ============================================================================
# FUNCTIONS
# ============================================================================

log_info() {
    echo -e "\033[1;34m[INFO]\033[0m $1"
}

log_success() {
    echo -e "\033[1;32m[SUCCESS]\033[0m $1"
}

log_error() {
    echo -e "\033[1;31m[ERROR]\033[0m $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    # Check Dockerfile exists
    if [ ! -f "Dockerfile" ]; then
        log_error "Dockerfile not found"
        exit 1
    fi
    
    log_success "Prerequisites OK"
}

build_image() {
    local version=$1
    local image_tag="${IMAGE_NAME}:${version}"
    local latest_tag="${IMAGE_NAME}:latest"
    
    log_info "Building CrossBridge Docker image..."
    log_info "Version: ${version}"
    log_info "Image: ${image_tag}"
    
    # Build with version tag
    docker build \
        ${NO_CACHE} \
        --tag "${image_tag}" \
        --tag "${latest_tag}" \
        --build-arg VERSION="${version}" \
        --label "version=${version}" \
        --label "build-date=$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
        --label "vcs-ref=$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')" \
        ${BUILD_ARGS} \
        .
    
    if [ $? -eq 0 ]; then
        log_success "Build completed successfully"
        log_success "Image: ${image_tag}"
    else
        log_error "Build failed"
        exit 1
    fi
}

tag_image() {
    local version=$1
    local major_version=$(echo ${version} | cut -d. -f1)
    local minor_version=$(echo ${version} | cut -d. -f1,2)
    
    log_info "Tagging image..."
    
    # Tag with major version (e.g., 1)
    docker tag "${IMAGE_NAME}:${version}" "${IMAGE_NAME}:${major_version}"
    
    # Tag with minor version (e.g., 1.0)
    docker tag "${IMAGE_NAME}:${version}" "${IMAGE_NAME}:${minor_version}"
    
    log_success "Tagged: ${IMAGE_NAME}:${major_version}"
    log_success "Tagged: ${IMAGE_NAME}:${minor_version}"
}

push_image() {
    local version=$1
    
    if [ "${PUSH_IMAGE}" = false ]; then
        log_info "Skipping push (use --push to enable)"
        return
    fi
    
    log_info "Pushing images to registry..."
    
    # Push all tags
    docker push "${IMAGE_NAME}:${version}"
    docker push "${IMAGE_NAME}:latest"
    
    local major_version=$(echo ${version} | cut -d. -f1)
    local minor_version=$(echo ${version} | cut -d. -f1,2)
    
    docker push "${IMAGE_NAME}:${major_version}"
    docker push "${IMAGE_NAME}:${minor_version}"
    
    log_success "Images pushed successfully"
}

print_summary() {
    local version=$1
    
    echo ""
    echo "============================================================================"
    echo "  CrossBridge Docker Build Summary"
    echo "============================================================================"
    echo ""
    echo "  Version:       ${version}"
    echo "  Image:         ${IMAGE_NAME}"
    echo ""
    echo "  Available tags:"
    echo "    - ${IMAGE_NAME}:${version}"
    echo "    - ${IMAGE_NAME}:latest"
    echo "    - ${IMAGE_NAME}:$(echo ${version} | cut -d. -f1)"
    echo "    - ${IMAGE_NAME}:$(echo ${version} | cut -d. -f1,2)"
    echo ""
    echo "  Size:          $(docker images ${IMAGE_NAME}:${version} --format "{{.Size}}")"
    echo ""
    echo "============================================================================"
    echo ""
    echo "  Usage:"
    echo ""
    echo "    # Run help"
    echo "    docker run --rm ${IMAGE_NAME}:${version}"
    echo ""
    echo "    # Run smoke tests"
    echo "    docker run --rm \\"
    echo "      -v \$(pwd)/test-repo:/workspace \\"
    echo "      -v \$(pwd)/crossbridge-data/logs:/data/logs \\"
    echo "      -v \$(pwd)/crossbridge-data/reports:/data/reports \\"
    echo "      ${IMAGE_NAME}:${version} exec run --framework pytest --strategy smoke"
    echo ""
    echo "    # With docker-compose"
    echo "    docker-compose up"
    echo ""
    echo "============================================================================"
    echo ""
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    log_info "Starting CrossBridge Docker build"
    log_info "Version: ${VERSION}"
    
    # Run checks
    check_prerequisites
    
    # Build image
    build_image "${VERSION}"
    
    # Tag image with major and minor versions
    tag_image "${VERSION}"
    
    # Push if requested
    push_image "${VERSION}"
    
    # Print summary
    print_summary "${VERSION}"
}

# Run main
main
