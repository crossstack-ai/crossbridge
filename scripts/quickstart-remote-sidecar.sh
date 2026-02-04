#!/bin/bash

# CrossBridge Remote Sidecar - Quick Start Script
# This script demonstrates remote sidecar setup and testing

set -e

echo "=================================="
echo "CrossBridge Remote Sidecar Setup"
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SIDECAR_HOST=${CROSSBRIDGE_SIDECAR_HOST:-localhost}
SIDECAR_PORT=${CROSSBRIDGE_SIDECAR_PORT:-8765}
MODE=${1:-local}  # local, docker, or remote

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if sidecar is running
check_sidecar() {
    print_info "Checking sidecar health at $SIDECAR_HOST:$SIDECAR_PORT..."
    
    if curl -f -s "http://$SIDECAR_HOST:$SIDECAR_PORT/health" > /dev/null 2>&1; then
        print_info "✅ Sidecar is running and healthy"
        return 0
    else
        print_warn "⚠️ Sidecar is not responding"
        return 1
    fi
}

# Function to start sidecar locally
start_sidecar_local() {
    print_info "Starting sidecar locally in background..."
    
    # Check if already running
    if check_sidecar; then
        print_info "Sidecar already running"
        return 0
    fi
    
    # Start sidecar in background
    python -m crossbridge sidecar start \
        --mode observer \
        --host 0.0.0.0 \
        --port $SIDECAR_PORT \
        --background &
    
    SIDECAR_PID=$!
    echo $SIDECAR_PID > /tmp/crossbridge-sidecar.pid
    
    # Wait for startup
    print_info "Waiting for sidecar to start..."
    for i in {1..30}; do
        sleep 1
        if check_sidecar; then
            print_info "✅ Sidecar started successfully (PID: $SIDECAR_PID)"
            return 0
        fi
    done
    
    print_error "Failed to start sidecar"
    return 1
}

# Function to start sidecar with Docker Compose
start_sidecar_docker() {
    print_info "Starting sidecar with Docker Compose..."
    
    if ! command -v docker-compose &> /dev/null && ! command -v docker &> /dev/null; then
        print_error "Docker or docker-compose not found"
        return 1
    fi
    
    # Detect docker compose command
    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
    elif docker-compose version &> /dev/null; then
        DOCKER_COMPOSE="docker-compose"
    else
        print_error "Docker compose not available"
        return 1
    fi
    
    # Start services
    $DOCKER_COMPOSE -f docker-compose-remote-sidecar.yml up -d
    
    # Wait for startup
    print_info "Waiting for sidecar to start..."
    for i in {1..30}; do
        sleep 1
        if check_sidecar; then
            print_info "✅ Sidecar started successfully with Docker"
            return 0
        fi
    done
    
    print_error "Failed to start sidecar with Docker"
    return 1
}

# Function to stop sidecar
stop_sidecar() {
    print_info "Stopping sidecar..."
    
    if [ -f /tmp/crossbridge-sidecar.pid ]; then
        PID=$(cat /tmp/crossbridge-sidecar.pid)
        if ps -p $PID > /dev/null 2>&1; then
            kill $PID
            rm /tmp/crossbridge-sidecar.pid
            print_info "✅ Sidecar stopped (PID: $PID)"
        fi
    fi
    
    # Also try docker if running
    if command -v docker &> /dev/null; then
        if docker compose version &> /dev/null; then
            docker compose -f docker-compose-remote-sidecar.yml down 2>/dev/null || true
        elif docker-compose version &> /dev/null; then
            docker-compose -f docker-compose-remote-sidecar.yml down 2>/dev/null || true
        fi
    fi
}

# Function to run example tests
run_example_tests() {
    print_info "Running example tests with remote sidecar..."
    
    # Check sidecar is running
    if ! check_sidecar; then
        print_error "Sidecar is not running. Start it first."
        return 1
    fi
    
    # Export environment variables
    export CROSSBRIDGE_ENABLED=true
    export CROSSBRIDGE_SIDECAR_HOST=$SIDECAR_HOST
    export CROSSBRIDGE_SIDECAR_PORT=$SIDECAR_PORT
    
    # Run Robot Framework tests if available
    if [ -d "examples/robot" ]; then
        print_info "Running Robot Framework example..."
        export PYTHONPATH=$PYTHONPATH:$(pwd)/adapters/robot
        export ROBOT_LISTENER=crossbridge_listener.CrossBridgeListener
        robot examples/robot/ || true
    fi
    
    # Run Pytest tests if available
    if [ -d "examples/pytest" ]; then
        print_info "Running Pytest example..."
        export PYTHONPATH=$PYTHONPATH:$(pwd)/adapters/pytest
        export PYTEST_PLUGINS=crossbridge_plugin
        pytest examples/pytest/ || true
    fi
    
    print_info "✅ Example tests completed"
}

# Function to show sidecar stats
show_stats() {
    print_info "Fetching sidecar statistics..."
    
    if ! check_sidecar; then
        print_error "Sidecar is not running"
        return 1
    fi
    
    curl -s "http://$SIDECAR_HOST:$SIDECAR_PORT/stats" | python -m json.tool
}

# Main menu
show_menu() {
    echo ""
    echo "Select an option:"
    echo "  1) Start sidecar locally"
    echo "  2) Start sidecar with Docker Compose"
    echo "  3) Check sidecar status"
    echo "  4) Run example tests"
    echo "  5) Show statistics"
    echo "  6) Stop sidecar"
    echo "  7) Exit"
    echo ""
}

# Main script
case "$MODE" in
    local)
        start_sidecar_local
        ;;
    docker)
        start_sidecar_docker
        ;;
    remote)
        print_info "Using remote sidecar at $SIDECAR_HOST:$SIDECAR_PORT"
        check_sidecar
        ;;
    interactive)
        while true; do
            show_menu
            read -p "Enter choice [1-7]: " choice
            case $choice in
                1) start_sidecar_local ;;
                2) start_sidecar_docker ;;
                3) check_sidecar ;;
                4) run_example_tests ;;
                5) show_stats ;;
                6) stop_sidecar ;;
                7) echo "Goodbye!"; exit 0 ;;
                *) print_error "Invalid option" ;;
            esac
        done
        ;;
    *)
        echo "Usage: $0 [local|docker|remote|interactive]"
        echo ""
        echo "Examples:"
        echo "  $0 local       - Start sidecar locally"
        echo "  $0 docker      - Start sidecar with Docker Compose"
        echo "  $0 remote      - Test connection to remote sidecar"
        echo "  $0 interactive - Interactive menu"
        echo ""
        echo "Environment variables:"
        echo "  CROSSBRIDGE_SIDECAR_HOST - Sidecar hostname (default: localhost)"
        echo "  CROSSBRIDGE_SIDECAR_PORT - Sidecar port (default: 8765)"
        exit 1
        ;;
esac
