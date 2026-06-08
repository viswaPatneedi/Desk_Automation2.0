#!/bin/bash

# Docker Setup Validation Script for Raspberry Pi
# Verifies all components are working correctly

set +e  # Don't exit on errors, we want to check all components

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

passed=0
failed=0

# Helper functions
print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}\n"
}

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((passed++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((failed++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# 1. Check Docker Installation
print_header "Checking Docker Installation"

if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    check_pass "Docker installed: $DOCKER_VERSION"
else
    check_fail "Docker is not installed"
fi

if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker compose version | head -1)
    check_pass "Docker Compose installed: $COMPOSE_VERSION"
else
    check_fail "Docker Compose is not installed"
fi

# 2. Check Docker Daemon
print_header "Checking Docker Daemon"

if docker ps &> /dev/null; then
    check_pass "Docker daemon is running"
else
    check_fail "Docker daemon is not running"
fi

# 3. Check Configuration Files
print_header "Checking Configuration Files"

if [ -f "Dockerfile.rpi" ]; then
    check_pass "Dockerfile.rpi exists"
    LINES=$(wc -l < Dockerfile.rpi)
    check_warn "  Dockerfile.rpi: $LINES lines"
else
    check_fail "Dockerfile.rpi not found"
fi

if [ -f "docker-compose.rpi.yml" ]; then
    check_pass "docker-compose.rpi.yml exists"
else
    check_fail "docker-compose.rpi.yml not found"
fi

if [ -f ".env" ]; then
    check_pass ".env configuration file exists"
    if grep -q "SENDER_PASSWORD=" .env; then
        if grep -q "SENDER_PASSWORD=.*[a-zA-Z0-9]" .env; then
            check_pass "Email password appears to be configured"
        else
            check_warn "Email password not configured (may cause email issues)"
        fi
    fi
else
    check_warn ".env file not found (will use defaults)"
fi

if [ -f ".dockerignore" ]; then
    check_pass ".dockerignore exists"
else
    check_warn ".dockerignore not found (build may be slower)"
fi

# 4. Check Docker Image
print_header "Checking Docker Image"

if docker image inspect rdk-middleware:pi &> /dev/null; then
    IMAGE_SIZE=$(docker image inspect rdk-middleware:pi --format='{{.Size}}' | numfmt --to=iec-i --suffix=B 2>/dev/null || echo "unknown")
    check_pass "Docker image 'rdk-middleware:pi' exists (size: $IMAGE_SIZE)"
    
    IMAGE_DATE=$(docker image inspect rdk-middleware:pi --format='{{.Created}}' | cut -d'T' -f1)
    check_warn "  Image created: $IMAGE_DATE"
else
    check_warn "Docker image 'rdk-middleware:pi' not found (run: docker compose -f docker-compose.rpi.yml build)"
fi

# 5. Check Container Status
print_header "Checking Container"

if [ "$(docker ps -q -f name=rdk-middleware)" ]; then
    check_pass "Container 'rdk-middleware' is running"
    
    # Get container stats
    CONTAINER_ID=$(docker ps -q -f name=rdk-middleware)
    MEMORY=$(docker stats --no-stream $CONTAINER_ID --format='{{.MemUsage}}')
    CPU=$(docker stats --no-stream $CONTAINER_ID --format='{{.CPUPerc}}')
    check_warn "  Memory: $MEMORY | CPU: $CPU"
    
    # Check health
    HEALTH=$(docker inspect --format='{{.State.Health.Status}}' $CONTAINER_ID 2>/dev/null)
    if [ "$HEALTH" = "healthy" ]; then
        check_pass "Container health status: $HEALTH"
    elif [ "$HEALTH" = "starting" ]; then
        check_warn "Container health: $HEALTH (still starting)"
    else
        check_fail "Container health status: $HEALTH"
    fi
else
    check_warn "Container 'rdk-middleware' is not running (run: docker compose -f docker-compose.rpi.yml up -d)"
fi

# 6. Check Port Configuration
print_header "Checking Port Configuration"

if lsof -Pi :11078 -sTCP:LISTEN -t >/dev/null 2>&1; then
    check_pass "Port 11078 is listening"
    PORT_PROCESS=$(lsof -Pi :11078 -sTCP:LISTEN -t | xargs -I {} sh -c 'ps -p {} -o comm=')
    check_warn "  Process: $PORT_PROCESS"
else
    check_warn "Port 11078 is not listening (container may not be running)"
fi

# 7. Check Network Connectivity
print_header "Checking Network Connectivity"

if [ "$(docker ps -q -f name=rdk-middleware)" ]; then
    if curl -f http://localhost:11078/health &> /dev/null; then
        check_pass "Health endpoint responds (http://localhost:11078/health)"
    else
        check_fail "Health endpoint not responding"
    fi
    
    # Get container IP
    CONTAINER_ID=$(docker ps -q -f name=rdk-middleware)
    CONTAINER_IP=$(docker inspect --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $CONTAINER_ID)
    if [ ! -z "$CONTAINER_IP" ]; then
        check_warn "  Container IP: $CONTAINER_IP"
    fi
else
    check_warn "Container not running - cannot check connectivity"
fi

# 8. Check System Resources
print_header "Checking System Resources"

# Memory
TOTAL_MEM=$(free -h | grep "^Mem:" | awk '{print $2}')
AVAIL_MEM=$(free -h | grep "^Mem:" | awk '{print $7}')
check_warn "System Memory: Total=$TOTAL_MEM, Available=$AVAIL_MEM"

if (( $(echo "$AVAIL_MEM" | grep -oP '^\d+(?=G)' || echo 0) >= 500 )); then
    check_pass "Sufficient memory available for Docker"
else
    check_fail "Low memory - may cause performance issues"
fi

# Disk Space
DISK_TOTAL=$(df -h / | tail -1 | awk '{print $2}')
DISK_AVAIL=$(df -h / | tail -1 | awk '{print $4}')
DISK_PERCENT=$(df -h / | tail -1 | awk '{print $5}')
check_warn "Disk Space: Total=$DISK_TOTAL, Available=$DISK_AVAIL (${DISK_PERCENT}% used)"

if (( $(echo "$DISK_AVAIL" | grep -oP '^\d+(?=G)' || echo 0) >= 5 )); then
    check_pass "Sufficient disk space available"
else
    check_fail "Low disk space - may cause issues"
fi

# 9. Check Data Files
print_header "Checking Data Files"

if [ -f "devices.json" ]; then
    DEVICE_COUNT=$(grep -c '"ip"' devices.json || echo "0")
    check_pass "devices.json exists ($DEVICE_COUNT devices)"
else
    check_warn "devices.json not found - no devices registered"
fi

if [ -f "jobs.json" ]; then
    check_pass "jobs.json exists"
else
    check_warn "jobs.json not found"
fi

if [ -d "iteration_logs" ]; then
    LOG_COUNT=$(find iteration_logs -type f | wc -l)
    check_pass "iteration_logs directory exists ($LOG_COUNT log files)"
else
    check_warn "iteration_logs directory not found"
fi

if [ -d "screenshots" ]; then
    SCREENSHOT_COUNT=$(find screenshots -type f | wc -l)
    check_pass "screenshots directory exists ($SCREENSHOT_COUNT screenshots)"
else
    check_warn "screenshots directory not found"
fi

# 10. Check Documentation
print_header "Checking Documentation"

for doc in "DOCKER_RPI_SETUP.md" "DOCKER_RPI_SUMMARY.md" "DOCKER_RPI_QUICKREF.md" "Makefile.rpi" "docker-rpi-quickstart.sh"; do
    if [ -f "$doc" ]; then
        check_pass "$doc found"
    else
        check_warn "$doc not found"
    fi
done

# 11. Platform Detection
print_header "Platform Information"

if [ -f /sys/firmware/devicetree/base/model ]; then
    PI_MODEL=$(cat /sys/firmware/devicetree/base/model)
    check_pass "Detected: $PI_MODEL"
fi

UNAME=$(uname -m)
check_warn "Architecture: $UNAME"

# 12. Summary
print_header "Validation Summary"

TOTAL=$((passed + failed))
SUCCESS_RATE=$((passed * 100 / (passed + failed)))

echo "Passed: $passed/$TOTAL (${SUCCESS_RATE}%)"
if [ $failed -gt 0 ]; then
    echo -e "Failed: ${RED}$failed/$TOTAL${NC}"
fi

if [ $failed -eq 0 ]; then
    echo -e "\n${GREEN}✓ All checks passed! Docker is properly configured.${NC}\n"
    echo "Next steps:"
    echo "  1. Access web UI: http://localhost:11078"
    echo "  2. Add devices in Device Management"
    echo "  3. Create test sequences"
    echo "  4. Execute tests and monitor progress"
    exit 0
else
    echo -e "\n${RED}✗ Some checks failed. Review the issues above.${NC}\n"
    echo "Next steps:"
    echo "  1. Fix the failed items listed above"
    echo "  2. Check logs: docker logs rdk-middleware"
    echo "  3. Restart container: docker compose -f docker-compose.rpi.yml restart"
    echo "  4. Re-run this script to verify"
    exit 1
fi
