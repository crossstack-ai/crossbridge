#!/usr/bin/env bash
#
# CrossBridge Universal Wrapper Installation Script
# Installs crossbridge-run command for zero-touch test monitoring
#
# Usage:
#   curl -sSL https://crossbridge.io/install.sh | bash
#   # or
#   wget -qO- https://crossbridge.io/install.sh | bash
#

set -e

# Configuration
INSTALL_DIR="${CROSSBRIDGE_INSTALL_DIR:-/usr/local/bin}"
WRAPPER_URL="${CROSSBRIDGE_WRAPPER_URL:-https://raw.githubusercontent.com/crossbridge/crossbridge/main/bin/crossbridge-run}"
WRAPPER_NAME="crossbridge-run"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[CrossBridge Install]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[CrossBridge Install]${NC} $1"
}

log_error() {
    echo -e "${RED}[CrossBridge Install]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    local missing_deps=()
    
    if ! command -v curl &> /dev/null; then
        missing_deps+=("curl")
    fi
    
    if ! command -v tar &> /dev/null; then
        missing_deps+=("tar")
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        log_error "Please install them and try again"
        exit 1
    fi
}

# Detect OS and architecture
detect_platform() {
    local os=$(uname -s | tr '[:upper:]' '[:lower:]')
    local arch=$(uname -m)
    
    case "$os" in
        linux|darwin)
            log_info "Detected OS: $os"
            ;;
        *)
            log_error "Unsupported OS: $os"
            exit 1
            ;;
    esac
    
    case "$arch" in
        x86_64|amd64)
            log_info "Detected architecture: x86_64"
            ;;
        arm64|aarch64)
            log_info "Detected architecture: arm64"
            ;;
        *)
            log_warn "Unknown architecture: $arch (continuing anyway)"
            ;;
    esac
}

# Check if running with sufficient privileges
check_privileges() {
    if [[ ! -w "$INSTALL_DIR" ]]; then
        log_error "No write permission to $INSTALL_DIR"
        log_info "Please run with sudo or choose a different installation directory:"
        log_info "  export CROSSBRIDGE_INSTALL_DIR=~/.local/bin"
        log_info "  curl -sSL https://crossbridge.io/install.sh | bash"
        exit 1
    fi
}

# Download and install wrapper
install_wrapper() {
    local temp_file=$(mktemp)
    
    log_info "Downloading CrossBridge wrapper..."
    
    if curl -fsSL "$WRAPPER_URL" -o "$temp_file"; then
        chmod +x "$temp_file"
        mv "$temp_file" "$INSTALL_DIR/$WRAPPER_NAME"
        log_info "✅ Installed $WRAPPER_NAME to $INSTALL_DIR"
    else
        log_error "Failed to download wrapper from $WRAPPER_URL"
        rm -f "$temp_file"
        exit 1
    fi
}

# Verify installation
verify_installation() {
    if command -v crossbridge-run &> /dev/null; then
        log_info "✅ Installation verified"
        log_info ""
        log_info "CrossBridge is ready to use!"
        log_info ""
        log_info "Usage examples:"
        log_info "  crossbridge-run robot tests/"
        log_info "  crossbridge-run pytest tests/"
        log_info "  crossbridge-run jest tests/"
        log_info ""
        log_info "Configuration (set before running tests):"
        log_info "  export CROSSBRIDGE_API_HOST=your-sidecar-host"
        log_info "  export CROSSBRIDGE_API_PORT=8765"
        log_info "  export CROSSBRIDGE_ENABLED=true"
        return 0
    else
        log_warn "Installation successful but command not found in PATH"
        log_warn "Add $INSTALL_DIR to your PATH:"
        log_warn "  export PATH=\"$INSTALL_DIR:\$PATH\""
        log_warn "Add this line to ~/.bashrc or ~/.zshrc to make it permanent"
        return 1
    fi
}

# Main installation
main() {
    echo ""
    log_info "CrossBridge Universal Wrapper Installation"
    echo ""
    
    check_prerequisites
    detect_platform
    
    log_info "Installation directory: $INSTALL_DIR"
    check_privileges
    
    install_wrapper
    
    echo ""
    verify_installation
    echo ""
}

main "$@"
