#!/bin/bash

# ============================================================================
# Docker Verification Script
# ============================================================================
# Verifies that the Docker setup is correct and ready for deployment
# ============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASSED=0
FAILED=0

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         Docker Setup Verification Script                      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================================
# CHECK FUNCTIONS
# ============================================================================

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $1 (MISSING)"
        ((FAILED++))
    fi
}

check_command() {
    if command -v "$1" &> /dev/null; then
        VERSION=$("$1" --version 2>&1 | head -n1)
        echo -e "${GREEN}✓${NC} $1 - $VERSION"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $1 (NOT INSTALLED)"
        ((FAILED++))
    fi
}

# ============================================================================
# VERIFICATION CHECKS
# ============================================================================

echo -e "${BLUE}[CHECK 1]${NC} Required Files"
check_file "app.py"
check_file "requirements.txt"
check_file "Dockerfile.rpi.clean"
check_file "docker-compose.rpi.clean.yml"
check_file "docker-entrypoint.sh"
check_file "log_patterns.json"
check_file "config_commands.py"
check_file "config_ir_blaster.py"
echo ""

echo -e "${BLUE}[CHECK 2]${NC} Application Files"
check_file "templates/index.html"
check_file "templates/dashboard.html"
check_file "static/"
check_file "models/"
check_file "controllers/"
check_file "services/"
echo ""

echo -e "${BLUE}[CHECK 3]${NC} Docker Installation"
check_command "docker"
check_command "docker-compose"
echo ""

echo -e "${BLUE}[CHECK 4]${NC} Python & Dependencies"
check_command "python3"
check_command "pip3"
echo ""

# ============================================================================
# CONTENT VERIFICATION
# ============================================================================

echo -e "${BLUE}[CHECK 5]${NC} Dockerfile Validity"
if docker build -f Dockerfile.rpi.clean --dry-run . &> /dev/null; then
    echo -e "${GREEN}✓${NC} Dockerfile.rpi.clean syntax is valid"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Dockerfile.rpi.clean has syntax errors"
    ((FAILED++))
fi
echo ""

echo -e "${BLUE}[CHECK 6]${NC} Docker Compose Configuration"
if docker-compose -f docker-compose.rpi.clean.yml config > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} docker-compose.rpi.clean.yml is valid"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} docker-compose.rpi.clean.yml has errors"
    ((FAILED++))
fi
echo ""

echo -e "${BLUE}[CHECK 7]${NC} Entrypoint Script"
if [ -x "docker-entrypoint.sh" ]; then
    echo -e "${GREEN}✓${NC} docker-entrypoint.sh is executable"
    ((PASSED++))
else
    chmod +x docker-entrypoint.sh
    echo -e "${YELLOW}⚠${NC} Made docker-entrypoint.sh executable"
fi
echo ""

# ============================================================================
# REQUIREMENTS VERIFICATION
# ============================================================================

echo -e "${BLUE}[CHECK 8]${NC} Python Dependencies (from requirements.txt)"
echo "  Core packages required:"

REQUIRED_PACKAGES=(
    "Flask"
    "Flask-Login"
    "paramiko"
    "requests"
    "gunicorn"
    "gevent"
)

for package in "${REQUIRED_PACKAGES[@]}"; do
    if grep -q "^$package" requirements.txt; then
        echo -e "    ${GREEN}✓${NC} $package"
        ((PASSED++))
    else
        echo -e "    ${RED}✗${NC} $package"
        ((FAILED++))
    fi
done
echo ""

# ============================================================================
# LOG PATTERNS VERIFICATION
# ============================================================================

echo -e "${BLUE}[CHECK 9]${NC} Log Patterns Configuration"
if [ -f "log_patterns.json" ]; then
    if python3 -c "import json; json.load(open('log_patterns.json'))" 2>/dev/null; then
        PATTERNS_COUNT=$(python3 -c "import json; data=json.load(open('log_patterns.json')); print(len(data.get('LOG_PATTERNS', {})))")
        COMMANDS_COUNT=$(python3 -c "import json; data=json.load(open('log_patterns.json')); print(len(data.get('SYSTEM_COMMAND_PATTERNS', {})))")
        echo -e "${GREEN}✓${NC} log_patterns.json is valid JSON"
        echo -e "    • LOG_PATTERNS: $PATTERNS_COUNT patterns"
        echo -e "    • SYSTEM_COMMAND_PATTERNS: $COMMANDS_COUNT commands"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} log_patterns.json has invalid JSON"
        ((FAILED++))
    fi
else
    echo -e "${RED}✗${NC} log_patterns.json not found"
    ((FAILED++))
fi
echo ""

# ============================================================================
# SYSTEM REQUIREMENTS
# ============================================================================

echo -e "${BLUE}[CHECK 10]${NC} System Requirements"
echo "  Hardware:"
echo -e "    RAM: $(free -h | awk 'NR==2 {print $2}')"
echo -e "    CPU Cores: $(nproc)"
echo -e "    Disk Free: $(df -h / | awk 'NR==2 {print $4}')"

RAM_GB=$(free -g | awk 'NR==2 {print $2}')
if [ "$RAM_GB" -ge 4 ]; then
    echo -e "    ${GREEN}✓${NC} Sufficient RAM (${RAM_GB}GB) - meets minimum requirement"
    ((PASSED++))
else
    echo -e "    ${YELLOW}⚠${NC} Limited RAM (${RAM_GB}GB) - minimum is 4GB"
fi

DISK_GB=$(df / | awk 'NR==2 {printf "%.0f", $4/1024/1024}')
if [ "$DISK_GB" -ge 20 ]; then
    echo -e "    ${GREEN}✓${NC} Sufficient disk space (${DISK_GB}GB)"
    ((PASSED++))
else
    echo -e "    ${YELLOW}⚠${NC} Limited disk space (${DISK_GB}GB) - consider 64GB+ for logs"
fi
echo ""

# ============================================================================
# SUMMARY
# ============================================================================

TOTAL=$((PASSED + FAILED))

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                     VERIFICATION SUMMARY                      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  Total Checks: $TOTAL"
echo -e "  ${GREEN}Passed: $PASSED${NC}"
echo -e "  ${RED}Failed: $FAILED${NC}"
echo ""

if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed! Your Docker setup is ready.${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Run setup: ./rpi4-setup-complete.sh"
    echo "  OR"
    echo "  2. Build image: docker build -f Dockerfile.rpi.clean -t rdk-middleware-dashboard:rpi4-clean ."
    echo "  3. Start service: docker-compose -f docker-compose.rpi.clean.yml up -d"
    exit 0
else
    echo -e "${RED}✗ Some checks failed. Please review the errors above.${NC}"
    exit 1
fi
