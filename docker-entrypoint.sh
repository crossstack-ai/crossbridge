#!/bin/bash
set -e

# CrossBridge Docker Entrypoint
# Handles volume permission issues automatically

echo "=== CrossBridge Container Starting ==="

# Check if running as root
if [ "$(id -u)" = "0" ]; then
    echo "Running as root - fixing volume permissions..."
    
    # Check if data directories exist and fix permissions if needed
    for dir in /data/logs /data/reports /data/cache; do
        if [ -d "$dir" ]; then
            echo "  Fixing permissions for $dir"
            chown -R 1000:1000 "$dir" 2>/dev/null || echo "  ⚠️  Could not change ownership (volume may be read-only)"
            chmod -R 755 "$dir" 2>/dev/null || true
        else
            echo "  Creating $dir"
            mkdir -p "$dir"
            chown -R 1000:1000 "$dir" 2>/dev/null || true
            chmod -R 755 "$dir" 2>/dev/null || true
        fi
    done
    
    echo "  ✅ Permissions fixed"
    echo "  Switching to crossbridge user (UID 1000)..."
    echo "=== Starting CrossBridge CLI ==="
    echo ""
    
    # Drop privileges and run as crossbridge user
    exec gosu crossbridge "$@"
else
    echo "Running as user $(id -u):$(id -g)"
    
    # Check if data directories are writable
    for dir in /data/logs /data/reports /data/cache; do
        if [ -d "$dir" ] && [ ! -w "$dir" ]; then
            echo "  ⚠️  Warning: $dir is not writable - logs will use /tmp"
        fi
    done
    
    echo "=== Starting CrossBridge CLI ==="
    echo ""
    
    # Execute the main command
    exec "$@"
fi
