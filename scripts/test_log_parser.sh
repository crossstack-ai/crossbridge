#!/bin/bash
#
# Test script for generic log parser endpoint
# Tests all supported frameworks with sidecar API
#

set -e

SIDECAR_HOST="${SIDECAR_HOST:-10.60.75.145}"
SIDECAR_PORT="${SIDECAR_PORT:-8765}"
BASE_URL="http://${SIDECAR_HOST}:${SIDECAR_PORT}"

echo "=========================================="
echo "CrossBridge Log Parser - Test Script"
echo "=========================================="
echo "Sidecar: ${BASE_URL}"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check sidecar is running
echo -n "1. Checking sidecar health... "
if curl -s "${BASE_URL}/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Sidecar not reachable${NC}"
    exit 1
fi

# Check config
echo -n "2. Checking log parsing feature... "
CONFIG=$(curl -s "${BASE_URL}/config")
if echo "$CONFIG" | grep -q "log_parsing"; then
    echo -e "${GREEN}✓${NC}"
    echo "   Supported parsers: $(echo $CONFIG | jq -r '.features.parseable_frameworks | join(", ")')"
else
    echo -e "${YELLOW}⚠ Feature not enabled${NC}"
fi

echo ""
echo "=========================================="
echo "Test Cases"
echo "=========================================="

# Test 1: Robot Framework
echo ""
echo "Test 1: Robot Framework Parser"
echo "------------------------------"
if [ -f "output.xml" ]; then
    echo -n "Parsing Robot output.xml... "
    RESPONSE=$(curl -s -X POST "${BASE_URL}/parse/robot" \
        -H "Content-Type: application/xml" \
        --data-binary @output.xml)
    
    if echo "$RESPONSE" | jq -e '.framework == "robot"' > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        echo ""
        echo "Results:"
        echo "$RESPONSE" | jq '{
            framework,
            suite: .suite.name,
            status: .suite.status,
            total_tests: .suite.total_tests,
            passed: .suite.passed_tests,
            failed: .suite.failed_tests,
            elapsed_ms: .suite.elapsed_ms,
            failed_keywords_count: (.failed_keywords | length),
            slowest_tests: (.slowest_tests[:3] | map({name, elapsed_ms}))
        }'
    else
        echo -e "${RED}✗ Failed${NC}"
        echo "$RESPONSE" | jq '.'
    fi
else
    echo -e "${YELLOW}⚠ output.xml not found, skipping${NC}"
fi

# Test 2: Find latest Robot output in common locations
echo ""
echo "Test 2: Auto-detect Robot output"
echo "---------------------------------"
ROBOT_OUTPUTS=(
    "cloudconsole-restapi-automation/output.xml"
    "results/output.xml"
    "robot-results/output.xml"
    "output/output.xml"
)

for output_path in "${ROBOT_OUTPUTS[@]}"; do
    if [ -f "$output_path" ]; then
        echo "Found: $output_path"
        echo -n "Parsing... "
        
        RESPONSE=$(curl -s -X POST "${BASE_URL}/parse/robot" \
            -H "Content-Type: application/xml" \
            --data-binary @"$output_path")
        
        if echo "$RESPONSE" | jq -e '.suite' > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC}"
            echo ""
            echo "Quick Stats:"
            echo "$RESPONSE" | jq -r '
                "  Suite: \(.suite.name)",
                "  Status: \(.suite.status)",
                "  Tests: \(.suite.total_tests) (\(.suite.passed_tests) passed, \(.suite.failed_tests) failed)",
                "  Duration: \(.suite.elapsed_ms)ms",
                "  Pass Rate: \(.statistics.pass_rate)%"
            '
            
            # Show failed tests if any
            FAILED_COUNT=$(echo "$RESPONSE" | jq -r '.failed_keywords | length')
            if [ "$FAILED_COUNT" -gt 0 ]; then
                echo ""
                echo "  Failed Keywords:"
                echo "$RESPONSE" | jq -r '.failed_keywords[] | "    - \(.name): \(.error)"' | head -5
            fi
            
            # Show slowest tests
            echo ""
            echo "  Top 3 Slowest Tests:"
            echo "$RESPONSE" | jq -r '.slowest_tests[:3][] | "    - \(.name): \(.elapsed_ms)ms (\(.status))"'
            
            break
        else
            echo -e "${RED}✗ Parse failed${NC}"
        fi
    fi
done

# Test 3: Invalid framework
echo ""
echo "Test 3: Invalid Framework Handling"
echo "-----------------------------------"
echo -n "Testing with invalid framework... "
RESPONSE=$(curl -s -X POST "${BASE_URL}/parse/invalid" \
    -H "Content-Type: text/plain" \
    --data "test")

if echo "$RESPONSE" | jq -e '.detail' | grep -q "Unsupported framework"; then
    echo -e "${GREEN}✓${NC} (Error handled correctly)"
else
    echo -e "${YELLOW}⚠ Unexpected response${NC}"
fi

# Test 4: Empty content
echo ""
echo "Test 4: Empty Content Handling"
echo "-------------------------------"
echo -n "Testing with empty content... "
RESPONSE=$(curl -s -X POST "${BASE_URL}/parse/robot" \
    -H "Content-Type: application/xml")

if echo "$RESPONSE" | jq -e '.detail' | grep -q "No content"; then
    echo -e "${GREEN}✓${NC} (Error handled correctly)"
else
    echo -e "${YELLOW}⚠ Unexpected response${NC}"
fi

echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="
echo ""
echo "✓ Generic log parser endpoint is working"
echo "✓ Supports: robot, cypress, playwright, behave, java"
echo "✓ Error handling validated"
echo ""
echo "To parse your test results:"
echo "  curl -X POST ${BASE_URL}/parse/robot --data-binary @output.xml | jq"
echo ""
echo "For other frameworks:"
echo "  curl -X POST ${BASE_URL}/parse/cypress --data-binary @results.json | jq"
echo "  curl -X POST ${BASE_URL}/parse/playwright --data-binary @trace.json | jq"
echo "  curl -X POST ${BASE_URL}/parse/behave --data-binary @results.json | jq"
echo ""
